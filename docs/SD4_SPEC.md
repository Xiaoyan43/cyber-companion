# SD-4 Implementation Spec — Background reflection layer ("dreaming")

Phase **SD-4** of `docs/SOUL_DEEPENING_SPEC.md` (§6). **Owner: `[Claude]`-class
(memory + summary + new module).** Claude wrote this spec → Cursor implements →
Claude reviews → checkpoint. Prereq: **SD-1/2/3 landed.** This is the biggest slice;
read the whole spec before starting.

## Goal (one sentence)

After a reply is already sent, run **heavy LLM passes off the response path** (Tier
②) that consolidate memory, evolve Boxi's **impression** of the user (fills the
`[Impression]` block SD-2 already renders), and produce an **LLM conversation
summary** — every N turns, single-flight, and **never able to break a chat turn.**

## The three non-negotiables

1. **Off the response path.** Reflection runs in a background task that starts
   *after* the HTTP response (or stream) is finished. The user never waits for it.
2. **Single-flight.** Two turns can never run reflection concurrently — guarded by a
   `reflecting` flag claimed in one SQLite transaction.
3. **Failure-isolated.** Every job is wrapped; any exception is swallowed and logged.
   Reflection is best-effort enrichment, never a correctness dependency. The
   `reflecting` flag is always released (try/finally).

## Scope — what SD-4 does NOT do

- No schema/DDL change. State lives in the **existing `schema_meta`** key/value table
  (`turns_since_reflection`, `reflecting`, `last_reflected_message_id`).
- No cross-type linking / `memory_links` table / top-down retrieval — that is SD-5.
- No memory *merging* in consolidation (fuzzy/risky) — SD-4 consolidation is
  **archive + deprioritize only**. Merging is deferred (note it as future).

---

## Architecture

```
turn finishes ─► (LLM turn?) note_llm_turn(store)         # cheap, sync, in-request
HTTP response sent ─► background: run_reflection_if_due(store, budget)
                          └─ enable_reflection? claim_reflection(threshold)?
                               └─ try:  job1 consolidate
                                        job2 impression
                                        job3 llm_summary
                                  finally: release_reflection(); bump last_reflected_message_id
```

- **Counter** (`turns_since_reflection`) increments **only on real LLM turns**
  (not silent/mutter/budget-block).
- **Trigger** fires when counter ≥ `reflection_every_n_turns`.
- **Background execution:** `/chat/complete` uses FastAPI `BackgroundTasks`;
  `/chat/stream` uses `StreamingResponse(background=BackgroundTask(...))` so it runs
  after the stream closes.

---

## Task 1 — `schema_meta` accessors + atomic claim (`memory/store.py`)

No DDL change (`schema_meta(key TEXT PRIMARY KEY, value TEXT)` already exists). Add:

```python
def get_meta(self, key: str, default: str | None = None) -> str | None: ...
def set_meta(self, key: str, value: str) -> None:   # upsert via ON CONFLICT
    ...

def note_llm_turn(self) -> int:
    """Increment turns_since_reflection in one transaction; return the new count."""

def claim_reflection(self, threshold: int) -> bool:
    """ONE transaction: read turns_since_reflection + reflecting.
    If reflecting != '1' AND turns >= threshold:
        set reflecting='1', turns_since_reflection='0'; return True
    else: return False."""

def release_reflection(self) -> None:   # set reflecting='0'
    ...
```
`claim_reflection` MUST do the read-modify-write inside a single `connect()`
transaction (the `connect` context manager commits on exit) so two concurrent
background tasks cannot both claim. (Single-user app → races are unlikely, but the
flag is cheap insurance and keeps the invariant honest.)

---

## Task 2 — Config knobs (`memory/budget.py` + `config/budget*.json`) `[Cursor-ok]`

Add to `BudgetConfig` + `load_budget_config` + **both** `budget.json` files:
- `enable_reflection: bool = True`
- `reflection_every_n_turns: int = 6`
- `llm_summary: bool = True`

(Missing keys → defaults; old configs keep working. These are the remaining 3 of the
4 soul knobs; `llm_memory_extraction` already shipped in SD-3.)

---

## Task 3 — Reflection package (`backend/app/reflection/`)

New package: `__init__.py`, `runner.py`, `jobs.py`.

### `runner.py`
```python
def run_reflection_if_due(store, budget) -> None:
    if not budget.enable_reflection:
        return
    if not store.claim_reflection(budget.reflection_every_n_turns):
        return
    try:
        from backend.app.reflection.jobs import (
            consolidate_memories, form_impression, summarize_conversation_llm,
        )
        for job in (consolidate_memories, form_impression, summarize_conversation_llm):
            try:
                job(store, budget)
            except Exception:
                pass            # each job isolated
        _bump_last_reflected(store)
    finally:
        store.release_reflection()   # ALWAYS released
```
- `run_reflection_if_due` itself is the background entry point; it must **never
  raise** into the task runner (wrap the body defensively too).
- `_bump_last_reflected(store)`: set `last_reflected_message_id` to the current max
  chat message id (so jobs can scope to new material next time).

### `jobs.py` — one LLM call each, all tolerant
Shared helper: call the provider via `get_provider_router().complete(
ChatCompletionRequest(messages=[...], max_output_tokens=...))` (default provider),
parse a single JSON object from the reply; on `ProviderError` / parse failure →
return without changes. Keep prompts compact and **English-internal** (not shown to
the user). Coefficients/wording below are starting values — tune in implementation.

**Job 1 — `consolidate_memories(store, budget)` (archive + deprioritize only).**
- Gather a bounded candidate set: e.g. `store.list_memories(limit=40)` (recent +
  highest-importance mix is fine; keep it small).
- Prompt: "Here are stored memories `(id, type, content, importance, updated_at)`.
  Return JSON: `{\"archive\":[ids of stale/dead facts], \"deprioritize\":[{\"id\",
  \"importance\"}]}`. Only archive clearly outdated job_progress/recent_event;
  deprioritize means LOWER importance only."
- Apply with validation: id must exist; `archive` → `store.update_memory(id,
  expires_at=utc_now_iso())`; `deprioritize` → `update_memory(id,
  importance=clamp(min(existing, new)))` (**never raise importance** — safety).
  Ignore unknown ids/fields. (Merging deferred — do NOT delete/merge content in SD-4.)

**Job 2 — `form_impression(store, budget)` (the high-value one).**
- Inputs: `store.get_relationship_state()` numbers, top relevant memories
  (`stable_profile`/`project`/`job_progress`, a handful), latest summary.
- Prompt: "In Boxi's voice, write a 2–4 sentence internal impression: who this person
  is to you and where you two stand. Honest, a little毒舌, not user-facing. Return
  JSON `{\"impression\": \"...\"}`."
- Persist as a **single** `relationship_state`-type memory (upsert): find the existing
  one (`list_memories(type="relationship_state", limit=1)`); if present
  `update_memory(id, content=impression, metadata={...,"writer":"reflection"})`, else
  `create_memory(type="relationship_state", content=impression, importance=0.6,
  confidence=0.6, tags=["impression"], metadata={"writer":"reflection"})`. This is
  exactly what `context_builder._format_impression_block` reads → `[Impression]`
  starts appearing after the first reflection.

**Job 3 — `summarize_conversation_llm(store, budget)` (replaces rule-based when on).**
- Only when `budget.llm_summary` is True (else this job is a no-op; the synchronous
  rule-based path handles summaries — see Task 4).
- Reuse the existing due-check shape from `summary_policy.maybe_update_conversation_summary`
  (count_chat_messages, window lower bound, covered-until, batch). If a batch is due,
  fetch it (`list_chat_messages_between`) and ask the LLM for a compact summary +
  keywords: `{\"summary\":\"...\",\"keywords\":[...]}`; persist via
  `store.create_conversation_summary(range_start_message_id, range_end_message_id,
  summary, keywords)`. On failure, skip (the next reflection retries).

> Budget note: reflection makes up to 3 extra LLM calls per fire. Budget walls are
> OFF (Session 26), so this is intended. When walls are re-enabled later, reflection
> spend is **not** yet gated — leave a `# TODO(SD-later): gate reflection spend`
> marker; do not wire `evaluate_llm_budget_gate` into reflection in SD-4.

---

## Task 4 — Make the synchronous summary defer to reflection (`memory/summary_policy.py`)

`maybe_update_conversation_summary` runs **synchronously every turn** (in the
response path). It must stay cheap. Add at its top:
```python
config = budget or BudgetConfig()
if config.llm_summary:
    return False        # defer to background reflection (Job 3); never call an LLM here
# else: existing rule-based path unchanged
```
This guarantees **exactly one** summary producer: reflection (LLM) when `llm_summary`
is on, the synchronous rule-based path when off. No inline LLM call ever lands on the
response path.

---

## Task 5 — Wiring (`backend/app/main.py`)

Import: `from backend.app.reflection.runner import run_reflection_if_due`,
`from starlette.background import BackgroundTask`.

### `/chat/complete`
- Add `background_tasks: BackgroundTasks` to the signature (FastAPI injects it;
  `from fastapi import BackgroundTasks`).
- After the response is built, on **LLM turns only**:
  ```python
  if called_llm:
      store.note_llm_turn()
      background_tasks.add_task(run_reflection_if_due, store, budget)
  ```
  (Place after `maybe_update_conversation_summary(...)`, before `return`.)

### `/chat/stream`
- In the **LLM branch** of `event_generator`, right after `called_llm = True`
  (post-`_finalize_streamed_turn`), call `store.note_llm_turn()`.
- Build the response with a background task:
  ```python
  return StreamingResponse(
      event_generator(), media_type="text/event-stream",
      background=BackgroundTask(run_reflection_if_due, store, budget),
  )
  ```
  (Background runs after the stream closes. On non-LLM turns the counter wasn't
  incremented, so `claim_reflection` won't fire — the background call is a cheap
  no-op. That's fine.)

> Keep `store`/`budget` the same instances passed to the background callable. The
> store opens a fresh SQLite connection per op, so background access is safe alongside
> the (already-returned) request.

---

## Task 6 — Tests (`backend/tests/test_reflection.py`, new)

Drive jobs with the **mock provider** (set `CYBER_COMPANION_PROVIDER_MODE=mock`) or by
monkeypatching the router's `complete` to return canned JSON — do NOT hit a real LLM.
- **trigger/claim:** `note_llm_turn` increments; `claim_reflection` returns True only
  at threshold and flips `reflecting`; a second immediate `claim_reflection` returns
  False (single-flight); `release_reflection` clears it.
- **not due:** below threshold → `run_reflection_if_due` does nothing (no jobs run).
- **disabled:** `enable_reflection=false` → no claim, no jobs.
- **failure isolation:** monkeypatch one job to raise → the other jobs still run AND
  `reflecting` is released afterward (claimable again).
- **impression:** with canned `{"impression": "..."}`, a `relationship_state` memory
  is created (writer="reflection"); a second run **updates in place** (still one such
  memory). `context_builder` then renders `[Impression]`.
- **consolidate:** canned `{"archive":[id]}` sets `expires_at`; `{"deprioritize":
  [{"id","importance":0.1}]}` lowers importance; a deprioritize trying to RAISE
  importance is ignored; unknown id ignored.
- **summary deferral:** with `llm_summary=true`, `maybe_update_conversation_summary`
  returns False (no rule-based write); the reflection summary job writes the
  conversation summary instead. With `llm_summary=false`, rule-based path unchanged.
- **response-path safety (integration):** a chat turn whose reflection job is forced
  to raise still returns a normal `ChatCompleteResponse` (reflection runs after the
  response anyway; assert the endpoint is unaffected).

---

## Task 7 — Docs (`docs/MEMORY_DESIGN.md`, MANDATORY)

- Add a "Background reflection (SD-4)" subsection: the 3 jobs, the `schema_meta` keys
  (`turns_since_reflection`/`reflecting`/`last_reflected_message_id`), single-flight,
  off-path execution, `enable_reflection`/`reflection_every_n_turns`/`llm_summary`.
- Update the Auto-Write / summary notes: LLM summary supersedes rule-based when
  `llm_summary` is on; the `[Impression]` block is now populated by reflection.

---

## Done criteria (how Claude will review)

1. `PYTHON_BIN=.venv/bin/python npm run check` green.
2. Reply latency unchanged — reflection provably runs after the response (it's a
   background task; no LLM call added to the synchronous path — verify
   `maybe_update_conversation_summary` no longer can call an LLM inline).
3. Single-flight holds (concurrent claim test); `reflecting` always released even
   when a job raises.
4. A forced job exception does **not** break `/chat/complete` or `/chat/stream`.
5. `[Impression]` block appears in built context after a reflection writes the
   `relationship_state` memory, and updates in place on later reflections.
6. Counter increments only on LLM turns; reflection fires every
   `reflection_every_n_turns`; `enable_reflection=false` disables the whole layer.
7. Diff confined to: `memory/store.py` (meta/claim), `memory/budget.py` +
   `config/budget*.json`, new `backend/app/reflection/`, `memory/summary_policy.py`
   (defer guard), `backend/app/main.py` (wiring), tests, `docs/MEMORY_DESIGN.md`.
   **No SD-5 work; no schema/DDL change.**

## Boundaries (SD-4)

- Reflection is best-effort: never raises into the request/task path; flag always
  released; jobs individually isolated.
- No LLM call on the synchronous response path (summary defers to background).
- Consolidation is archive + deprioritize only (no merge/delete-of-content; never
  raises importance). LLM reflection output is **data only** — validated, ids checked,
  values clamped.
- No schema change; no linking (SD-5); don't gate reflection spend yet (walls off).
- Keep Boxi's voice: the impression is internal,毒舌-consistent, never user-facing
  text injected as a reply.
