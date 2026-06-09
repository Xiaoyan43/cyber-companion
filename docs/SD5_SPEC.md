# SD-5 Implementation Spec — Memory links + top-down retrieval (optional)

Phase **SD-5** of `docs/SOUL_DEEPENING_SPEC.md` (§8, optional). **Owner: `[Claude]`.**
Claude wrote this spec → Cursor implements → Claude reviews → checkpoint. Prereq:
SD-1..SD-4 landed. This is the last, optional soul slice (memU-style cross-links so
retrieval can pull in *related* memories, not just keyword-matched ones).

## Goal (one sentence)

Let memories **link to related memories** (deterministically, no extra LLM), and let
retrieval **follow one hop of links** so a relevant memory drags in its connected
context — closing the memU "category → linked items" gap.

## Design choices (deliberate)

- **Linker is deterministic** (cross-type token overlap), *not* an LLM call. Linking
  is about retrieval quality; nondeterministic LLM links + another reflection call
  aren't worth it. Runs inside the existing reflection pass (Tier ②, off-path).
- **Retrieval expansion is 1-hop, capped, additive** — it never *removes* a memory,
  only pulls in a few linked ones; bounded by the existing token packer.
- **Additive table** (no migration runner; same pattern as SD-2's `relationship_state`).

## Scope — what SD-5 does NOT do

- No multi-hop graph walk; no embeddings; no LLM-proposed links.
- No change to the SD-1..SD-4 contracts.

---

## Task 1 — Schema (`memory/schema.py`, additive)
```sql
CREATE TABLE IF NOT EXISTS memory_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  memory_id INTEGER NOT NULL,
  related_memory_id INTEGER NOT NULL,
  relation TEXT NOT NULL DEFAULT 'related',
  FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
  FOREIGN KEY (related_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
  UNIQUE (memory_id, related_memory_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_links_memory_id ON memory_links(memory_id);
```
Bump `SCHEMA_VERSION` to `3` (doc only; no migration runner). Store links
**bidirectionally** (insert both (a,b) and (b,a)) so a single-direction lookup
suffices at read time. `ON DELETE CASCADE` keeps links clean when a memory is deleted
(note: `delete_memory` uses raw DELETE; cascade requires `PRAGMA foreign_keys=ON`,
which `connect()` already sets).

## Task 2 — Store methods (`memory/store.py`)
- `add_memory_link(memory_id, related_memory_id, relation="related") -> None` —
  inserts both directions, `INSERT OR IGNORE` (idempotent via the UNIQUE constraint);
  no self-links (`a != b`).
- `get_linked_memory_ids(memory_id) -> list[int]` — `SELECT related_memory_id ...
  WHERE memory_id = ?`.
- `count_memory_links() -> int` (test/inspection helper).

## Task 3 — Deterministic linker (in reflection, `reflection/jobs.py`)
Add `link_related_memories(store, budget)` to the reflection job list **after**
`consolidate_memories` (so it links the post-consolidation set). Logic:
- Candidates: factual memories only — `stable_profile`, `project`, `job_progress`,
  `recent_event`, `reminder`, `behavior_preference` (exclude `relationship_state`,
  `conversation_summary`, `emotion_state`). Cap at ~40.
- For each **cross-type** pair (different `type`), compute token overlap with the
  existing `retrieval.tokenize`: `overlap = tokens(a) & tokens(b)`. Link when
  `len(overlap) >= 2` AND `overlap / min(len(a_tokens), len(b_tokens)) >= 0.34`
  (reuse the `_is_similar_content` spirit but require *cross-type* + a real shared
  noun, e.g. a company name shared by a `project` and a `job_progress`).
- Cap total new links per pass (e.g. 20) to avoid a one-time flood.
- Each link via `store.add_memory_link(a.id, b.id)`. Deterministic, no LLM.

## Task 4 — Retrieval expansion (`memory/context_builder.py`)
In `build_provider_context`, after `selected_memories` is chosen (the top
`max_memories_per_turn`):
- Collect 1-hop linked ids of the selected memories (`get_linked_memory_ids`).
- Pull those linked memories (from the already-loaded `active_memories`, skipping
  expired + already-selected), append up to a small extra cap
  (e.g. `max_memories_per_turn // 2`, min 2) — they ride the existing `_pack_sections`
  token budget, so over-budget extras are dropped automatically.
- Mark/expose them in `included_memory_ids` like the rest. Keep ranking otherwise
  unchanged. (This is the "top-down → follow links" behavior, bounded.)

## Task 5 — Consolidation candidate polish (`reflection/jobs.py`)
Fold in the SD-4 review note: in `consolidate_memories`, restrict the candidate set
to **factual types** (same exclusion list as Task 3) so the impression
(`relationship_state`) and summaries can never be archived/deprioritized.

## Task 6 — Tests (`backend/tests/`, extend test_reflection / new test_memory_links)
- `add_memory_link` idempotent + bidirectional; no self-link; `get_linked_memory_ids`.
- linker: two cross-type memories sharing a strong token (e.g. "Acme") get linked;
  same-type pair or weak overlap does NOT; cap respected.
- retrieval: a selected memory's linked memory is pulled into context even if it
  wouldn't rank on its own; cap respected; expired links excluded.
- consolidation polish: a `relationship_state`/`conversation_summary` memory is never
  in the consolidate candidate set.
- regression: SD-1..SD-4 suites still green.

## Task 7 — Docs (`docs/MEMORY_DESIGN.md`, MANDATORY)
- Add the `memory_links` table (fields, bidirectional, cascade).
- Note the deterministic linker (cross-type token overlap, in reflection) and 1-hop
  retrieval expansion in the Retrieval Policy.

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` green.
2. Links created deterministically in reflection; bidirectional + idempotent.
3. Retrieval pulls 1-hop linked memories, capped, additive (never drops a
   would-be-selected memory), within the token budget.
4. Consolidation never touches non-factual memories.
5. No LLM call added; no SD-1..SD-4 behavior change. Diff confined to
   `memory/schema.py`, `memory/store.py`, `reflection/jobs.py`,
   `memory/context_builder.py`, tests, `docs/MEMORY_DESIGN.md`.

## Boundaries (SD-5)
- Additive table only; deterministic linker (no LLM); 1-hop, capped, additive
  retrieval; factual-types-only for both linking and consolidation.
- Don't break the brain/surface split or any soul contract; don't send full history.
