# SD-2 Implementation Spec — Subjectivity kernel

Phase **SD-2** of `docs/SOUL_DEEPENING_SPEC.md` (§4). **Owner: `[Claude]`-class
(touches schema + memory + behavior).** Claude wrote this spec → Cursor implements →
Claude reviews → checkpoint. Prereq: **SD-1 landed** (`signals.appraisal` /
`signals.relationship` are already parsed and waiting at the parse sites).

## Goal (one sentence)

Give Boxi a **persistent, deterministic-local** inner state split into **fast
emotion** (`mood_state`, decays) and **slow relationship** (new `relationship_state`,
rarely decays), evolved each turn by clamped **local math** fed by SD-1's LLM
appraisal — and feed both back into the reply (context blocks + tone).

## The split (recap — DECIDED in SOUL_DEEPENING_SPEC §4.1)

- **`trust` MOVES** to the new `relationship_state` table (source of truth).
- **`loneliness` STAYS** in `mood_state` as an emotion, but is **re-sourced** from
  `closeness` + time-since-contact.
- New relationship dims: `closeness`, `familiarity`, `tension`.
- The LLM **suggests** deltas; the **kernel clamps and decides** (`|delta| ≤ 0.1`).
  Zero extra LLM call — appraisal rides SD-1's piggyback (Tier ①); the math is local
  (Tier ③).

## Scope — what SD-2 does NOT do

- Does **not** write `signals.memory[]` — that is SD-3.
- Does **not** form the impression narrative text — that is SD-4 (background). SD-2
  only builds the `[Impression]` *rendering* (reads a `relationship_state` memory if
  one exists; renders nothing until SD-4 writes it).
- Does **not** add the background reflection layer (SD-4) or config knobs for it.

---

## Task 1 — Schema + records + store (`memory/schema.py`, `database.py`, `store.py`)

### 1a. New table (`memory/schema.py`, additive — NO `mood_state` ALTER/DROP)
```sql
CREATE TABLE IF NOT EXISTS relationship_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  trust REAL NOT NULL DEFAULT 0.5,
  closeness REAL NOT NULL DEFAULT 0.2,
  familiarity REAL NOT NULL DEFAULT 0.0,
  tension REAL NOT NULL DEFAULT 0.0,
  last_meaningful_interaction_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
```
Leave `mood_state` DDL exactly as-is (the now-unused `trust` column stays, harmless).
Bump `SCHEMA_VERSION` to `2` (documentation only; there's still no migration runner —
see 1c).

### 1b. Record + row mapper (`database.py`)
Add `RelationshipStateRecord` (mirror `MoodStateRecord`): `updated_at, trust,
closeness, familiarity, tension, last_meaningful_interaction_at: str | None,
metadata`. Add `_row_to_relationship(row)` (mirror `_row_to_mood`).

### 1c. Seed + optional back-fill (`database.py:init_database`)
After the existing `INSERT OR IGNORE INTO mood_state (id) VALUES (1)`:
```python
connection.execute("INSERT OR IGNORE INTO relationship_state (id) VALUES (1)")
```
**Optional one-time trust back-fill** (recommended): if the relationship row was just
created (no prior `updated_at` beyond default), copy the existing `mood_state.trust`
into `relationship_state.trust` so the local DB keeps accumulated trust. Implement as:
read `mood_state.trust`; if relationship row's `trust` is still the seeded default and
mood trust differs, `UPDATE relationship_state SET trust = ?`. Keep it idempotent and
guarded so it runs at most once. Acceptable to skip (state re-accumulates), but do it.

### 1d. Store methods (`store.py`, mirror `get_mood_state`/`update_mood_state`)
- `get_relationship_state() -> RelationshipStateRecord`
- `update_relationship_state(*, trust=None, closeness=None, familiarity=None,
  tension=None, last_meaningful_interaction_at=None, metadata=None)
  -> RelationshipStateRecord` — partial update, fills unset from current, writes
  `updated_at = utc_now_iso()`.

---

## Task 2 — The kernel math (`behavior/mood.py` + a new `behavior/kernel.py`)

All values clamped to `[0.0, 1.0]`; all incoming LLM deltas clamped to `[-0.1, 0.1]`
before use. Coefficients below are **starting values — tune in implementation.**

### 2a. Stop `mood_state` owning relationship (`behavior/mood.py`)
- `apply_user_message_mood_delta(...)` — **remove the `trust` mutations** (trust now
  lives in `relationship_state`). Keep `loneliness` for now (re-sourced in 2c), keep
  annoyance/boredom/worry logic. The function should no longer return a `trust` it
  computed; `update_mood_state` calls in `engine.py` stop passing `trust`.
- The pre-LLM relationship nudges that used to live here (refused → trust↓,
  overwhelmed → trust↑) **move to `engine.py`** as small immediate
  `update_relationship_state` calls (see Task 3), so behavior continuity holds.

### 2b. Appraisal → kernel update (new `behavior/kernel.py`)
A single entry point applied **post-LLM** (Task 3 wires it):
```python
def apply_signals_to_kernel(store, signals: dict | None) -> None:
    """Apply LLM appraisal + relationship deltas to mood_state + relationship_state.
    Deterministic, clamped, best-effort (never raises into the request path)."""
```
Behavior:
- Read `appraisal = signals.get("appraisal")`, `rel = signals.get("relationship")`
  (both optional; missing → light defaults / no-op).
- **Emotion (mood_state):** from appraisal `valence∈[-1,1]`, `arousal∈[0,1]`,
  `goal_relevance∈[0,1]`:
  - negative valence + high goal_relevance → `worry += clamp(-valence * goal_relevance * 0.10)`.
  - positive valence → `worry` relaxes (`*= 0.9`), small `boredom` relaxes.
- **Relationship (relationship_state):**
  - apply `rel` deltas directly (clamped ±0.1): `trust`, `closeness`, `tension`.
  - appraisal-derived: positive valence + goal_relevance →
    `closeness += 0.02`, `trust += 0.01`.
  - `familiarity += 0.01` every real user turn (monotonic, cap 1.0).
  - `tension *= 0.9` each turn (decays toward 0) unless `rel` raised it.
  - **meaningful interaction:** if `goal_relevance ≥ 0.5` or `abs(valence) ≥ 0.5`,
    set `last_meaningful_interaction_at = utc_now_iso()` and drop `loneliness`
    (`mood_state`) by 0.1.
- One `update_mood_state` + one `update_relationship_state` write at the end.

### 2c. Decay (extend `apply_idle_tick_mood_delta` in `behavior/mood.py`)
- Keep existing boredom/loneliness growth + energy drop.
- **Emotion relaxation:** `annoyance *= 0.95`, `worry *= 0.95` toward baseline each
  idle tick.
- **Loneliness re-source:** make idle loneliness growth depend on closeness —
  `loneliness += 0.03 * (1.0 - closeness)` (read closeness from
  `relationship_state`). Low closeness → lonelier faster; high closeness → barely.
  (Pass `relationship` into the function or read it at the call site in `engine.py`.)

---

## Task 3 — Wiring (`behavior/engine.py`, `backend/app/main.py`)

### 3a. Tone factors relationship (`behavior/mood.py` + `engine.py`)
- Change `choose_tone_mode(mood, *, overwhelmed)` →
  `choose_tone_mode(mood, relationship, *, overwhelmed)`:
  - `comfort` if overwhelmed / `mood.worry ≥ 0.65` / mood ∈ {sad,worried} (unchanged).
  - `tease` only if `mood.annoyance ≥ 0.6` **and** `relationship.trust ≥ 0.4`
    **and** `relationship.familiarity ≥ 0.3` (don't tease a near-stranger) **and**
    `relationship.tension < 0.5` (back off when tense).
  - else `normal`.
- `engine._evaluate_user_message`: read `relationship = store.get_relationship_state()`,
  pass to `choose_tone_mode`; stop passing `trust` into `update_mood_state`. For the
  `refused`/`overwhelmed` branches, add small immediate
  `store.update_relationship_state(...)` nudges (refused → `tension += 0.08`,
  `trust -= 0.05`; overwhelmed → `trust += 0.04`, clamp).
- `engine._evaluate_idle_tick`: pass `relationship.closeness` into the idle-tick
  delta (for the re-sourced loneliness).

### 3b. Apply the kernel post-LLM (`main.py`)
Call `apply_signals_to_kernel(store, parsed.signals)` **after** the reply is parsed,
next to `maybe_write_memories_from_turn`:
- `/chat/complete` — after `parsed = parse_structured_assistant_response(...)`
  (~`main.py:633`), before/with the memory write (~`:661`).
- `/chat/stream` — inside `_finalize_streamed_turn` after its parse (~`:745`).
Wrap in try/except (best-effort; a kernel failure must never break the turn).

### 3c. Relationship API + UI panel data
- Add `RelationshipStateSchema` (`schemas.py`, mirror `MoodStateSchema`) and
  `_relationship_to_schema` (`main.py`).
- Add `GET /memory/relationship` → `RelationshipStateSchema`. (No PUT needed for
  SD-2; add later if a debug control is wanted.)
- **SD-2-UI `[Cursor-ok]`:** "Boxi 怎么看你" panel reads `GET /memory/relationship`
  (numbers) + `GET /memory/memories?type=relationship_state` (impression text, empty
  until SD-4). Read-only. Frontend-only; no backend coupling beyond these GETs.

---

## Task 4 — Context blocks (`memory/context_builder.py`)

- Add `_format_relationship_block(rel)`:
  ```
  [Relationship]
  trust=0.54, closeness=0.31, familiarity=0.12, tension=0.05
  ```
- Add `_format_impression_block(store)`: read the latest `relationship_state` *memory*
  (`store.list_memories(type="relationship_state", limit=1)`); if present render
  `[Impression]\n{content}`, else return `None` (omit). SD-4 will write that memory.
- In `build_provider_context`, read `relationship = store.get_relationship_state()`
  and insert the `[Relationship]` block right after the `[Current mood]` block, and
  the `[Impression]` block (when present) after it. These count toward the existing
  `_pack_sections` token budget — no separate budget logic.

---

## Task 5 — Tests (`backend/tests/`)

Add (new file `test_relationship_state.py` or extend `test_memory.py` /
`test_behavior.py` / `test_context_builder.py`):
- **store roundtrip:** relationship row seeded with defaults; partial
  `update_relationship_state` persists and fills unset fields; `updated_at` advances.
- **back-fill:** if implemented — fresh DB with a non-default `mood_state.trust`
  ends up with that trust in `relationship_state` after init.
- **kernel appraisal:** positive valence + goal_relevance raises closeness/trust
  (clamped, ≤ +0.1); negative valence + goal_relevance raises worry; tension decays
  `*0.9` when no rel delta; familiarity is monotonic (+0.01/turn, never decreases);
  meaningful interaction sets `last_meaningful_interaction_at` and drops loneliness.
- **clamp:** an LLM `relationship.trust = 0.9` delta is clamped to ≤ 0.1 applied.
- **tone:** `choose_tone_mode` returns `tease` only when trust ≥ 0.4 AND familiarity
  ≥ 0.3 AND tension < 0.5; returns `comfort`/`normal` per the rules.
- **loneliness re-source:** idle tick grows loneliness more when closeness is low
  than when high.
- **context blocks:** `[Relationship]` always rendered; `[Impression]` only when a
  `relationship_state` memory exists.
- **regression:** existing mood tests still pass after trust moves out (update any
  asserting `mood.trust`); emotion (annoyance/worry/boredom) still responds per turn.

---

## Task 6 — Docs (MANDATORY this phase)

Update **`docs/MEMORY_DESIGN.md`**:
- Add the `relationship_state` table (fields + defaults) under "Suggested Tables".
- Note: `trust` is now owned by `relationship_state` (the `mood_state.trust` column
  is vestigial/unread); `mood_state` = momentary emotion; `loneliness` stays in
  `mood_state` but is re-sourced from `closeness` + time-since-contact.
- Note the emotion-vs-relationship split and the clamped-local-kernel principle
  (LLM appraisal suggests, kernel decides).
- Mention `[Relationship]`/`[Impression]` context blocks in the Retrieval Policy.

---

## Done criteria (how Claude will review)

1. `PYTHON_BIN=.venv/bin/python npm run check` green (modulo the known unrelated STT
   red, ideally fixed by the Cursor maintenance item by then).
2. `relationship_state` persists across restart; trust no longer changes via
   `mood_state`; loneliness responds to closeness.
3. Tone shifts with relationship (tease gated by trust+familiarity+tension); emotion
   still responds per turn (no regression).
4. `[Relationship]` block appears in the built context; `[Impression]` only when a
   relationship_state memory exists; both respect the token budget.
5. `apply_signals_to_kernel` is best-effort — a forced exception in it does not break
   `/chat/complete` or `/chat/stream`.
6. `docs/MEMORY_DESIGN.md` updated. Diff stays within: schema/database/store,
   behavior (mood/kernel/engine), context_builder, schemas/main (relationship GET +
   kernel wiring), tests, frontend panel, MEMORY_DESIGN.md. **No SD-3/SD-4 work.**

## Boundaries (SD-2)

- Additive table only — no `mood_state` ALTER/DROP (no migration runner exists).
- Don't consume `signals.memory[]` (SD-3); don't build the reflection layer (SD-4);
  don't add reflection config knobs.
- Kernel is local + deterministic + clamped — no extra LLM call.
- Keep Boxi毒舌: relationship gates the *amount* of sarcasm/warmth; persona core,
  boundaries, `cruelty_limit` unchanged.
- Don't send full history; don't touch provider/file-gateway/budget enforcement.
