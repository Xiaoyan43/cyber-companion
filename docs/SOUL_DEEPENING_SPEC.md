# Soul-Deepening Spec (灵魂深化)

Status: **Claude spec — awaiting user approval, then Cursor implements, then Claude
reviews.** Incremental on the current working app. **No rebuild.** Driven by the
Session 26 pivot (`docs/HANDOFF.md`, `docs/SESSION_LOG.md` Session 26): *soul first*
— memory + proactive + emotion ≈ 80% of the emotional value.

This spec deepens the **kept soul** (`backend/app/memory/`, `backend/app/behavior/`).
It does **not** touch the V2 voice/box rebuild (`docs/ARCHITECTURE_V2.md`,
`docs/REBUILD_ROADMAP.md`) — that comes after.

---

## 0. Guiding principle — latency-smart placement of LLM work

The whole point: we may burn extra LLM calls (budget walls are off), but **never on
the path where the user is waiting for a reply.** Three tiers:

| Tier | When | What runs there | Cost to user-perceived latency |
|---|---|---|---|
| **① Sync — piggyback** | the one reply call | the reply *also* returns structured signals (emotion appraisal / memory candidates / relationship deltas) in its JSON | **zero** (same call) |
| **② Background — reflection / "dreaming"** | after the reply is sent; every N turns or on idle | heavy LLM passes: consolidate + link memories, evolve the impression, LLM summary | **zero** (off the response path) |
| **③ Local — high-frequency math** | every turn / idle tick | the subjectivity-kernel deltas + decay; behavior decision | **zero** (no LLM) |

Everything below maps to exactly one tier. If a feature can't be placed in ① or ③
cheaply, it goes in ②.

---

## 1. What we steal (research grounding)

**memU** (`NevaMind-AI/memU`, Apache-2.0 — reference, do not fork). Worth stealing:
- **3-layer model:** Resource (raw turn) → Memory Item (extracted fact) → Category
  (a living, organized grouping). We have Resource→Item (`messages`→`memories`); we
  lack the *Category-as-living-document* layer and **cross-links** between items.
- **LLM-driven extraction at write time** (replaces our regex `write_policy`).
- **Background "evolution"** — memory updates/links/archival happen continuously,
  off the request path. This is exactly our Tier ②.
- **Top-down retrieval** (category first, then items) and optional non-embedding
  direct read. Our retrieval is keyword-rank only; a category layer improves it.

**Subjectivity kernel / "Resonant"-style affect** (persistent emotion + relationship
dynamics, **zero extra LLM**). Worth stealing:
- A **deterministic math layer** that holds emotional + relational state *stable
  across sessions* and *actually changes behavior* (tone, avatar, proactivity).
- The clean split between **momentary emotion** (fast, decays) and **slow
  relationship state** (trust/closeness/familiarity — rarely decays). We currently
  **mix** these into one `mood_state` row.

**awesome-affective-computing** (`NEU-DataMining`, reference). Worth stealing:
- **Appraisal theory (OCC):** an event is *appraised* on a few dimensions →
  emotion follows. Dimensions we can actually use: **valence** (good/bad for the
  user), **arousal** (intensity), **goal-relevance** (does it touch the user's
  projects/job), **novelty/expectedness**. We already do a crude version
  (`empty`/`low_value`/`rambling`/`overwhelmed`/`refused` → deltas in
  `behavior/mood.py`). The upgrade: let the LLM piggyback a *richer appraisal*,
  while the **state update stays deterministic local math.**
- **PAD/dimensional model** validates keeping numeric affect dims (we have 7).

Net: the kernel is **local + deterministic** (Tier ③); the LLM only *supplies
appraisal/extraction signals*, via piggyback (Tier ①) or background (Tier ②). This
is the cheapest possible way to make the soul deeper.

---

## 2. Current flow (what exists today)

`POST /chat/complete` (`backend/app/main.py:577`):

1. `evaluate_behavior(...)` → local mood delta + decision (`behavior/engine.py`).
2. If `should_call_llm`: `build_provider_context(...)` → `router.complete(...)` →
   `parse_structured_assistant_response(...)` → `{content, avatar_state, decision}`
   (`behavior/parser.py`).
3. `persist_chat_turn(...)`.
4. `maybe_write_memories_from_turn(...)` → **regex** M2 (`memory/write_policy.py`).
5. `maybe_update_conversation_summary(...)` → **rule-based** recap
   (`memory/summary_policy.py`).

Structured response today carries only `content / avatar_state / decision`. Mood is
one `mood_state` row mixing emotion + relationship. Memories have no links. Summary
is a string concat, not an LLM summary. These are the four things we deepen.

---

## 3. The piggyback contract (sentinel-delimited trailer)

> **Why not a JSON wrapper.** `/chat/stream` (`main.py:745`, `:905`) forwards deltas
> to live text + TTS *as they arrive*. Wrapping the reply in `{"content": ...}` would
> stream raw JSON tokens into the UI and the speaker. So the reply is emitted as
> **plain text first**, then a **single-line signals trailer** after a fixed
> sentinel. `content` is never inside JSON — it's the text before the sentinel.

**Format the model emits:**
```
行吧，被拒一次而已，又不是世界末日。简历那段我们再砍两句。
<<<BOXI_SIGNALS>>>
{"avatar_state":"worried","decision":"reply","appraisal":{"valence":-0.4,"arousal":0.5,"goal_relevance":0.8,"note":"rejected by a company, frustrated"},"relationship":{"trust":0.04,"closeness":0.03,"tension":-0.02},"memory":[{"type":"job_progress","content":"Rejected by Company X on 2026-06-09","importance":0.7,"confidence":0.9,"tags":["job-search"]}]}
```

- **`content`** = everything *before* the sentinel (trimmed). The only user-facing
  field — displayed, persisted, spoken.
- **Trailer** = sentinel line + exactly one **single-line** JSON object. Fields
  `avatar_state`, `decision`, `appraisal`, `relationship`, `memory` — **all optional**.
- **Sentinel** = `<<<BOXI_SIGNALS>>>` (ASCII; reliably reproduced; never occurs in a
  natural reply). Define once as `SIGNALS_SENTINEL`.

### Parsing rules (tolerant — chat must NEVER break)
- **No sentinel** → whole text is `content`, no signals (today's behavior exactly).
- **Sentinel + valid JSON** → `content` = pre-sentinel text; populate `signals`.
- **Sentinel + malformed/partial JSON** → `content` = pre-sentinel text; drop
  signals. Never show the sentinel or JSON to the user.
- **Bounded deltas.** kernel clamps `relationship.*` / emotion deltas (`|delta| ≤
  0.1`) — the LLM *suggests*, the kernel *decides*. It cannot yank trust to 1.0.

### Streaming (critical — the live-text/TTS leak)
- Keep a tail buffer the length of the sentinel; only forward text that can no longer
  be the *start of a forming* sentinel.
- On sentinel detection, **stop forwarding deltas**; keep accumulating into
  `accumulated_text` for the final parse, emit nothing more to the client.
- After stream end, parse `accumulated_text`; `content` (pre-sentinel) matches what
  was streamed. Frontend live text + TTS therefore never see the trailer.

### Code shape
- Extend `StructuredAssistantResponse` (`behavior/parser.py`) with optional
  `signals: dict | None`; switch the parser to sentinel-split (keep the legacy
  whole-string-JSON branch as a secondary fallback so old behavior still parses).
- Add the persona **output-protocol** section: "reply naturally; then on a new line
  emit `<<<BOXI_SIGNALS>>>` and one single-line JSON with these fields; never put the
  sentinel elsewhere; text before the sentinel is what the user sees." Keep it short.

> Q1 fallback: if the model is unreliable at the trailer, demote extraction to a
> Tier ② background call; the tolerant parser already degrades gracefully.

---

## 4. The subjectivity kernel (Tier ③ local + Tier ① appraisal)

### 4.1 Split emotion from relationship (DECIDED — Q2)

Today `mood_state` (singleton id=1) mixes both. Reframe. **`trust` and `loneliness`
are NOT the same kind of thing** — affective computing separates slow *sentiment*
from the fast *emotion* it causes:

- **`trust` is genuinely relational → it MOVES to the new table.** ✅
- **`loneliness` is a momentary emotion → it STAYS in `mood_state`**, but is
  *re-sourced*: its idle growth/decay is now **driven by** `closeness` +
  time-since-contact instead of being a free-floating counter. (Don't move it —
  re-wire it.)

So:
- **`mood_state` = momentary EMOTION** (fast, decays toward baseline): `mood` label,
  `energy`, `annoyance`, `boredom`, `worry`, `loneliness`. *How Boxi feels right now.*
  Its DDL is **left untouched** (the vestigial `trust` column just stops being read).
- **New `relationship_state` singleton table = SLOW relationship** (rarely decays):
  `trust`, `closeness`, `familiarity`, `tension`, `last_meaningful_interaction_at`.
  *How Boxi feels about the user, accumulated over time.* This table is the **source
  of truth for `trust`** from now on.

`familiarity` is roughly monotonic (grows with interaction count, never resets).
`tension` decays toward 0 over time. `trust`/`closeness` move slowly both ways.

**Migration (important — there is NO migration framework).** `init_database`
(`memory/database.py:42`) only runs `CREATE TABLE IF NOT EXISTS` + upserts
`schema_version`; there is no ALTER/versioned-migration path. Therefore:
- The new `relationship_state` table is **additive and auto-created**; seed its row
  with `INSERT OR IGNORE INTO relationship_state (id) VALUES (1)` in `init_database`
  (mirror the existing `mood_state` seed).
- **Do not ALTER/DROP `mood_state`** — leave its DDL exactly as-is; the now-unused
  `trust` column is harmless and avoids any migration of the existing local DB.
- **Optional 5-line back-fill:** on first creation of `relationship_state`, copy the
  current `mood_state.trust` value into `relationship_state.trust` so the existing
  ~352KB local DB doesn't reset accumulated trust to the 0.5 default. Acceptable to
  skip for a personal, gitignored DB — it just re-accumulates from baseline. Recommend
  doing the back-fill; it's cheap.

**Updating `docs/MEMORY_DESIGN.md` is mandatory in this phase** (per `CLAUDE.md`
restricted-work rule).

### 4.2 Appraisal-driven update

Per turn, the kernel computes deltas from two sources and applies them
deterministically:
- **Local heuristics** (today's signals: empty/low_value/rambling/overwhelmed/
  refused) — always available, zero LLM.
- **LLM appraisal** (`signals.appraisal`, when present) — richer: valence/arousal/
  goal_relevance map to emotion + relationship deltas via a fixed function. E.g.
  high `goal_relevance` + positive `valence` → `trust`/`closeness` up; user shares
  something vulnerable → `closeness` up; user dismissive/`refused` → `tension` up.

All deltas **clamped and decayed** by local math. Decay: emotion relaxes toward
baseline each turn/idle tick (extend `apply_idle_tick_mood_delta`); `tension` decays
slowly; `familiarity` only grows.

### 4.3 Feed both into reply + avatar

- `context_builder._format_mood_block` → add a `[Relationship]` block (trust /
  closeness / familiarity / tension) next to `[Current mood]`.
- `behavior/mood.choose_tone_mode` → factor relationship in: high `familiarity` +
  `trust` unlocks warmer teasing; high `tension` pulls back sarcasm; low `closeness`
  keeps distance. (Keeps Boxi from being a generic polite assistant — boundary held.)
- Optional: relationship can gate **proactivity** (Boxi nudges more when closeness is
  high) — wire into `behavior/engine._evaluate_proactive_check`.

---

## 5. LLM memory extraction (Tier ①, upgrades M2 → M3)

Route `signals.memory[]` through the **existing** dedup/write pipeline
(`write_policy._persist_candidate` already does similarity-dedup + in-place update —
reuse it). Changes:
- New entry point `write_memories_from_signals(store, candidates, source_message_id)`
  that validates LLM candidates (type ∈ `MEMORY_TYPES`, clamp importance/confidence,
  clip content) and calls `_persist_candidate`.
- **Keep regex M2 as fallback** when `signals.memory` is absent (don't delete
  `extract_memory_candidates`; it's the safety net).
- Tag LLM-written memories `metadata.writer="llm"` (vs `"rule_based"`) for auditing.
- **Cross-type linking moved entirely to SD-5.** (A throwaway `metadata.links` array
  in SD-3 would just be reworked into the real `memory_links` table in SD-5 — so
  SD-3 stays a tight "extraction only" slice; SD-5 owns all linking.)

This is the user's "记忆抽取升级" and it adds **zero latency** (same reply call).
Detailed brief: `docs/SD3_SPEC.md`.

---

## 6. Background reflection layer (Tier ②, the "dreaming")

A worker that runs heavy LLM passes **after the reply is already returned**, so the
user never waits. This is the new layer the user asked for.

### 6.1 Trigger
- A turn counter in `schema_meta` (`turns_since_reflection`); when it reaches
  `reflection_every_n_turns` (config, default 6) → enqueue a reflection job.
- Also opportunistic on `idle_tick` when there's new un-reflected material and Boxi
  is otherwise idle (cheap to piggyback the cron we already tick).
- Track progress with `last_reflected_message_id` in `schema_meta`.

### 6.2 Jobs (each isolated; a failure must never affect chat)
1. **Memory consolidation / evolution** (memU-style): over recently written
   memories — dedupe/merge near-duplicates, decay stale `importance`, archive
   (`expires_at`) dead `job_progress`/`recent_event`, and add cross-links. One LLM
   call over a compact candidate set, not the whole DB.
2. **Impression formation:** maintain a short evolving narrative — "who is this
   person to me, and where do we stand" — stored as a **`relationship_state` memory
   type** (already in `MEMORY_TYPES`, currently unused). Injected into context as a
   `[Impression]` block. This is what makes Boxi feel like it *knows* you, not just
   recalls facts.
3. **LLM conversation summary:** replace `build_rule_based_summary`'s string concat
   with an LLM summary (same `conversation_summaries` table, same trigger in
   `maybe_update_conversation_summary`; just swap the summary builder, gated by
   config so the rule-based path stays as fallback).

### 6.3 Implementation shape
- Start simplest: **FastAPI `BackgroundTasks`** kicked off at the end of
  `/chat/complete` after the response is built — runs in-process, after the response
  is sent, no new infra. (If we later want it fully decoupled, swap to an asyncio
  queue / worker thread; keep the trigger logic separate from the execution so this
  swap is local.)
- **Concurrency:** single-flight (a `reflecting` flag in `schema_meta`) so two turns
  can't reflect at once; SQLite writes stay serialized through `MemoryStore`.
- **Config-gated:** `enable_reflection` (default true). Off → system behaves exactly
  as today.
- **Failure-isolated:** wrap every job in try/except; log and move on. Reflection is
  best-effort enrichment, never a correctness dependency.

---

## 7. Config knobs (additive to `config/budget.json`)

Budget walls stay **off** (Session 26), but keep knobs so the soul is tunable:
```jsonc
{
  "llm_memory_extraction": true,      // §5 piggyback memory; false → regex M2 only
  "enable_reflection": true,          // §6 background layer; false → today's behavior
  "reflection_every_n_turns": 6,      // §6.1 trigger cadence
  "llm_summary": true                 // §6.2.3 LLM summary; false → rule-based
}
```
Load in `memory/budget.py` `BudgetConfig` with safe defaults so missing keys don't
break older configs.

---

## 8. Phasing — each phase is independently verifiable (Claude spec → Cursor → Claude review → checkpoint)

| Phase | Scope | Touches restricted layer? | "Done when" |
|---|---|---|---|
| **SD-1** | Extend structured contract + tolerant parser (`signals` optional) + persona output-protocol section. Parse only — wire nothing yet beyond existing avatar/decision. | parser/persona `[Claude→Cursor]` | `signals` parsed when present; **never leaks** to `content`/TTS; absent/malformed → today's behavior exactly. Tests for all three cases. |
| **SD-2** | Subjectivity kernel: new `relationship_state` table + appraisal-driven local math + decay; `[Relationship]`/`[Impression]` context blocks; tone factors relationship. **Update `docs/MEMORY_DESIGN.md`.** | schema + memory + behavior `[Claude]` | Relationship state persists across turns/restart, moves slowly, decays correctly; tone shifts with trust/tension; regression: emotion still responds per turn. |
| **SD-3** | LLM memory extraction (M3): route `signals.memory` through dedup pipeline; regex fallback; `writer` tag; metadata links. | memory `[Claude]` | LLM-emitted facts persist + dedup against existing; regex still fires when `signals` absent; no dup explosion. |
| **SD-4** | Background reflection layer: turn-counter trigger, consolidation + impression + LLM summary, `BackgroundTasks`, single-flight, config-gated, failure-isolated. | memory + summary `[Claude]` | Reflection runs off the response path (reply latency unchanged); impression appears in context and evolves; a forced reflection failure does **not** break `/chat/complete`. |
| **SD-5** *(optional)* | `memory_links` table + top-down (category-first) retrieval upgrade. **Update `docs/MEMORY_DESIGN.md`.** | schema + memory `[Claude]` | Retrieval can follow links; measurable recall improvement on a seeded scenario. |

Recommended order: **SD-1 → SD-2 → SD-3 → SD-4**, SD-5 later. SD-1 is the keystone
(everything piggybacks on the contract) and is low-risk (parse-only).

---

## 9. Boundaries honored (cross-check against `AGENTS.md` / `CLAUDE.md` / Session 26)

- ✅ **No extra LLM on the user-waiting path** — Tier ① is the same call; Tier ② is
  after the response is sent.
- ✅ **No full conversation history** to the provider — piggyback adds none; context
  stays compact (`build_provider_context` discipline preserved).
- ✅ **LLM output is data, never executed** — `signals` are parsed values clamped by
  local math; no file/shell access.
- ✅ **Schema changes update `docs/MEMORY_DESIGN.md`** — flagged mandatory in SD-2 and
  SD-5.
- ✅ **Budget knobs kept** even though walls are off.
- ✅ **Boxi stays毒舌, not a polite assistant** — relationship gates *amount* of
  sarcasm/warmth; persona core unchanged; `cruelty_limit` boundary intact.
- ✅ **Soul deepened, not rebuilt** — additive on `memory/` + `behavior/`; voice/box
  V2 untouched.
- ✅ **Claude specs, Cursor builds** — this doc is the spec; Cursor implements per
  phase; Claude reviews each before checkpoint.

---

## 10. Decisions (resolved by user 2026-06-09)

- **Q1 — JSON reliability → DECIDED: piggyback accepted.** Every reply emits the
  `signals` wrapper (Tier ①). Parser stays tolerant + regex/heuristic fallback
  (§3); keep the code path swappable to a background extraction call if reliability
  ever degrades.
- **Q2 — Relationship migration → DECIDED: clean split, with the loneliness nuance.**
  `trust` moves to the new `relationship_state` table (source of truth);
  `loneliness` stays in `mood_state` as an emotion but is re-sourced from
  `closeness`/time-since-contact. New table is additive (no `mood_state` ALTER/DROP);
  optional back-fill of the existing `trust` value. See §4.1.
- **Q3 — Reflection cadence → DECIDED: every 6 turns for now.**
  `reflection_every_n_turns = 6`. Revisit "idle-only dreaming" during SD-4 debugging
  (keep the trigger logic isolated so the switch is local).
- **Q4 — Impression visibility → DECIDED: build the UI panel.** A "Boxi 怎么看你"
  panel surfacing the relationship state (trust/closeness/familiarity/tension) + the
  evolving impression narrative. Read-only; reads existing/ new memory + relationship
  endpoints. Frontend-only → `[Cursor-ok]`. Lands with SD-2 (relationship numbers)
  and fills in the impression text after SD-4.

---

## 11. Concrete file touch-list (for Cursor, per phase)

- **SD-1:** `behavior/parser.py` (sentinel split + `signals` field +
  `SIGNALS_SENTINEL`), `memory/persona.py` (output-protocol section),
  `backend/app/main.py` (streaming sentinel-strip in the `/chat/stream` delta loop;
  `/chat/complete` already rebuilds content from `parsed.content`), tests in
  `backend/tests/test_behavior.py`. Detailed brief: `docs/SD1_SPEC.md`.
- **SD-2:** `memory/schema.py` (+`relationship_state` table), `memory/database.py`
  (+`RelationshipStateRecord` + seed/back-fill), `memory/store.py` (get/update
  relationship), `behavior/mood.py` (split + decay) + new `behavior/kernel.py`
  (`apply_signals_to_kernel`), `behavior/engine.py` (tone + relationship nudges),
  `backend/app/main.py` (kernel wiring + `GET /memory/relationship`), `schemas.py`
  (+`RelationshipStateSchema`), `memory/context_builder.py`
  (`[Relationship]`/`[Impression]` blocks), frontend "Boxi 怎么看你" panel, tests,
  `docs/MEMORY_DESIGN.md`. Detailed brief: `docs/SD2_SPEC.md`.
- **SD-3:** `memory/write_policy.py` (+`write_memories_from_signals` +
  `record_turn_memories` orchestrator, keep regex M2 fallback, `writer` param),
  `memory/budget.py` + `config/budget*.json` (`llm_memory_extraction` knob),
  `backend/app/main.py` (orchestrator at the two LLM write sites only), tests,
  `docs/MEMORY_DESIGN.md` (M3 note). Detailed brief: `docs/SD3_SPEC.md`.
- **SD-4:** new `backend/app/reflection/` module (trigger + jobs),
  `memory/summary_policy.py` (LLM summary builder behind `llm_summary`),
  `backend/app/main.py` (enqueue `BackgroundTasks`), `memory/budget.py` (knobs),
  `config/budget.json` + `config/budget.example.json`.
- **SD-5:** `memory/schema.py` (+`memory_links`), `memory/retrieval.py` (top-down),
  `docs/MEMORY_DESIGN.md`.

---

*End of spec. On approval, the SD-1…SD-4 items are mirrored into `docs/TODO.md`
(done) and handed to Cursor one phase at a time; Claude reviews each phase's diff
before checkpoint.*
