# SD-3 Implementation Spec — LLM memory extraction (M2 → M3)

Phase **SD-3** of `docs/SOUL_DEEPENING_SPEC.md` (§5). **Owner: `[Claude]`-class
(touches the memory write path).** Claude wrote this spec → Cursor implements →
Claude reviews → checkpoint. Prereq: **SD-1 + SD-2 landed** (`signals.memory[]` is
already parsed and reaching the two LLM-reply write sites).

## Goal (one sentence)

Let Boxi persist the **LLM's own extracted facts** (`signals.memory[]`, piggybacked
on the reply — Tier ①, zero extra call) through the **existing dedup/write
pipeline**, with the **regex M2 kept as fallback** when the model emits no memory.

## Scope — what SD-3 does NOT do

- **No cross-type linking** — moved to SD-5 (it needs the real `memory_links` table;
  a throwaway `metadata.links` array now would just be reworked there). SD-3 only
  tags provenance (`writer="llm"`).
- No background reflection / consolidation (SD-4).
- No schema change (memories table already has `metadata_json`).

## Where signals already arrive (verified)

Only **two** sites carry an LLM reply with `signals`:
1. **`/chat/complete`** — `parsed = parse_structured_assistant_response(...)`
   (`main.py:633`), single memory-write site at `main.py:685`.
2. **`_finalize_streamed_turn`** — `parsed` at `main.py:769`, memory-write at
   `main.py:794`.

The other two write sites — the streaming **budget-block** branch (`main.py:866`)
and the **local-response** branches (`main.py:685` else-path / `:958`) — have no LLM
signals; they keep calling regex M2 unchanged.

---

## Task 1 — `write_policy.py`: validate + persist LLM candidates

### 1a. Parameterize the writer tag
`_persist_candidate(...)` currently hardcodes `metadata={"writer": "rule_based"}`.
Add a `writer: str = "rule_based"` parameter; use it in both the create and update
metadata (`{"writer": writer, ...}`). Existing callers unchanged (default holds).

### 1b. Validate one LLM memory item
```python
_MAX_SIGNAL_MEMORIES_PER_TURN = 5

def _validate_signal_memory(raw: object) -> MemoryWriteCandidate | None:
    if not isinstance(raw, dict):
        return None
    mem_type = raw.get("type")
    if mem_type not in MEMORY_TYPES:          # import from memory.schema; reject unknowns
        return None
    content = _clip_content(str(raw.get("content", "")))   # reuse existing clip (≤200)
    if len(content) < 4:
        return None
    importance = _clamp01(_as_float(raw.get("importance"), 0.5))
    confidence = _clamp01(_as_float(raw.get("confidence"), 0.5))
    tags = tuple(str(t) for t in raw.get("tags", []) if isinstance(t, (str,)))[:6]
    return MemoryWriteCandidate(
        type=mem_type, content=content,
        importance=importance, confidence=confidence, tags=tags,
    )
```
- `_clamp01` / `_as_float`: small local helpers (or import the kernel's — but prefer
  a local copy to avoid a behavior→memory import edge; keep `write_policy` free of
  behavior deps).
- Reuse the existing `_MIN_WRITE_CONFIDENCE = 0.6` floor: drop validated candidates
  with `confidence < _MIN_WRITE_CONFIDENCE` (same bar as regex M2 — no low-confidence
  guesses).

### 1c. Write from signals
```python
def write_memories_from_signals(
    store, signal_memories: list, *, source_message_id, budget=None
) -> list[MemoryRecord]:
    config = budget or BudgetConfig()
    if not config.auto_memory_write:          # master gate still respected
        return []
    written = []
    for raw in signal_memories[:_MAX_SIGNAL_MEMORIES_PER_TURN]:
        candidate = _validate_signal_memory(raw)
        if candidate is None or candidate.confidence < _MIN_WRITE_CONFIDENCE:
            continue
        written.append(
            _persist_candidate(store, candidate, source_message_id=source_message_id, writer="llm")
        )
    return written
```
This reuses `_persist_candidate` → so **same-type dedup / in-place update** (the
`_find_similar_memory` logic) applies to LLM writes exactly as to regex writes.

### 1d. One orchestrator (picks M3 vs M2 per turn)
```python
def record_turn_memories(
    store, *, user_input: str, signals: dict | None, source_message_id, budget=None
) -> list[MemoryRecord]:
    config = budget or BudgetConfig()
    if not config.auto_memory_write:
        return []
    if config.llm_memory_extraction and isinstance(signals, dict):
        sig_mem = signals.get("memory")
        if isinstance(sig_mem, list) and sig_mem:
            return write_memories_from_signals(
                store, sig_mem, source_message_id=source_message_id, budget=config
            )
    # fallback: regex M2 (signals absent/empty, or knob off)
    return maybe_write_memories_from_turn(
        store, user_input=user_input, source_message_id=source_message_id, budget=config
    )
```
Per-turn it's **one or the other** (no double-write): if the model gave a non-empty
memory list and the knob is on → M3; else → regex M2. (Dedup would catch most
overlaps anyway, but choosing one path per turn is cleaner.)

---

## Task 2 — Config knob (`memory/budget.py` + `config/budget*.json`) `[Cursor-ok]`

- `BudgetConfig`: add `llm_memory_extraction: bool = True`.
- `load_budget_config`: `llm_memory_extraction=bool(payload.get("llm_memory_extraction", True))`.
- `config/budget.json` **and** `config/budget.example.json`: add
  `"llm_memory_extraction": true`. (Missing key → default true, so old configs keep
  working.)

> This is the first of the four SD soul knobs; `enable_reflection` /
> `reflection_every_n_turns` / `llm_summary` arrive with SD-4 — do not add them now.

---

## Task 3 — Wire the orchestrator at the two LLM sites (`main.py`)

Replace the `maybe_write_memories_from_turn(...)` call with `record_turn_memories(...)`
**only** at the two LLM-reply sites; leave the budget-block and local-response sites
calling `maybe_write_memories_from_turn` unchanged.

- **`/chat/complete`** (`main.py:577`): before the `if decision.should_call_llm:`
  block, init `reply_signals: dict | None = None`. In the LLM branch, after
  `parsed = parse_structured_assistant_response(...)` (~`:633`), set
  `reply_signals = parsed.signals`. At the write site (`:685`) call:
  ```python
  record_turn_memories(
      store, user_input=user_input, signals=reply_signals,
      source_message_id=user_message_id, budget=budget,
  )
  ```
  (Budget-block branch leaves `reply_signals=None` → regex fallback, as today.)
- **`_finalize_streamed_turn`** (`main.py:746`): `parsed` is already in scope
  (`:769`). Replace the `maybe_write_memories_from_turn(...)` at `:794` with
  `record_turn_memories(store, user_input=user_input, signals=parsed.signals,
  source_message_id=user_message_id, budget=budget)`.

Import `record_turn_memories` from `memory.write_policy` (alongside the existing
`maybe_write_memories_from_turn` import at `main.py:27`).

> Best-effort: wrap the call in try/except like the kernel call, OR rely on the
> existing behavior (M2 today is not wrapped). Recommend a try/except so a bad LLM
> memory payload can never break the reply turn.

---

## Task 4 — Tests (`backend/tests/test_memory_write_policy.py`, extend)

- **valid signal write:** `write_memories_from_signals` with a good item
  (`type="job_progress"`, conf 0.9) persists one memory with
  `metadata["writer"] == "llm"`.
- **type rejection:** an item with `type="garbage"` is dropped (no write).
- **confidence floor:** item with `confidence=0.4` is dropped (< 0.6).
- **clamp:** `importance=5` / `confidence=2` clamp to ≤ 1.0.
- **dedup reuse:** writing the same-type near-duplicate updates in place (count
  unchanged), via the existing `_persist_candidate` path.
- **cap:** more than 5 items → at most 5 written.
- **orchestrator picks M3:** `record_turn_memories` with a non-empty `signals.memory`
  and `llm_memory_extraction=true` writes from signals (writer="llm"); the regex path
  is **not** used (assert e.g. a fact only present in signals, not derivable by regex
  from `user_input`, gets written).
- **orchestrator falls back to M2:** `signals=None` (or `llm_memory_extraction=false`)
  → regex M2 runs as before.
- **master gate:** `auto_memory_write=false` → no writes on either path.

---

## Done criteria (how Claude will review)

1. `PYTHON_BIN=.venv/bin/python npm run check` green.
2. With a `signals.memory[]` present (+ knob on), facts persist tagged
   `writer="llm"`, deduped against existing memories of the same type.
3. With no signals (or knob off / `auto_memory_write=false`), behavior is **exactly**
   today's regex M2 (or no writes) — no regressions in `test_memory_write_policy`.
4. A malformed/garbage memory payload never breaks `/chat/complete` or `/chat/stream`.
5. Diff confined to: `memory/write_policy.py`, `memory/budget.py`,
   `config/budget*.json`, `backend/app/main.py` (two write sites only),
   `backend/tests/test_memory_write_policy.py`. **No schema/SD-4/SD-5 work.**

## Boundaries (SD-3)

- One write path per turn (M3 or M2, never both); regex M2 stays as the fallback,
  do not delete `extract_memory_candidates`.
- Respect `auto_memory_write` (master) and the `_MIN_WRITE_CONFIDENCE` floor.
- No cross-type linking (SD-5); no reflection (SD-4); no schema change.
- LLM memory output is **data only** — validated, clamped, type-whitelisted; never
  executed, never trusted for importance/confidence beyond the clamps.
- Keep `docs/MEMORY_DESIGN.md`'s "Auto-Write" section honest: add a short note that
  M3 (LLM signal extraction) supersedes M2 per-turn when present, gated by
  `llm_memory_extraction`. (Small doc touch — update it.)
