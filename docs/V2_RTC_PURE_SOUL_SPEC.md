# Spec — V2 RTC Pure-Soul: Off-path Turn Analyzer (PS series)

Give the **pure E2E** path (`OutputMode 0`, Doubao S2S black box) the soul's
emotion/relationship kernel + typed memory **without** touching the spoken turn.
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Reuse-first.
**Additive — the pure-E2E voice path and its sub-second latency are untouched.**

Source: discussion 2026-06-11 (pure-E2E soul). Sibling of `docs/SD4_SPEC.md`
(background reflection) — same off-path discipline, but **per turn**, not every N.

## Goal (one sentence)

After each pure-E2E turn, run **one cheap DeepSeek pass off the audio path** that
turns the `(user_text, bot_text)` transcript into the project's existing **signals
JSON**, then feed it through the *unchanged* soul writers
(`apply_signals_to_kernel` + `record_turn_memories`) so trust/closeness/tension and
typed memory move in **SQLite (the source of truth)** — exactly as the hybrid
trailer does today.

## The reframing

In pure mode the soul cannot live *inside* the turn (no token hooks, no guaranteed
`<<<BOXI_SIGNALS>>>` trailer, and TTS would speak it anyway). So the soul becomes a
**between-turns controller**: SENSE (this spec, PS-1/2) → DECIDE/SHAPE (PS-3/4,
later). The analyzer **replaces the lost trailer** — and is *more* reliable than it
ever was, because the analyzer LLM emits **JSON only** (no in-character reply), so
there is zero leak risk and none of the SD-1b/1c "model forgets the trailer" problem.

## Non-negotiables

1. **Off the audio path.** The analyzer never blocks or delays the spoken turn. It
   runs in a FastAPI `BackgroundTask` (like SD-4), triggered after a turn finalizes.
2. **SQLite is the source of truth.** The analyzer writes the local kernel + typed
   memory every turn. Viking stays the cloud retrieval/extraction layer
   (`AddSession` on hangup, VM-3) — unchanged.
3. **Failure-isolated.** Every pass is wrapped; any exception is swallowed + logged.
   A bad/empty analysis turn skips only the kernel update (transcript still persisted), never a correctness dependency.
4. **Soul reused, not edited.** `apply_signals_to_kernel`, `record_turn_memories`,
   `persist_chat_turn`, `evaluate_behavior`, `run_reflection_if_due` are called as-is.
   No kernel math change, no memory-schema change in this spec.
5. **Single-flight per room.** Two overlapping analyses for the same turn can't run
   (reuse the `schema_meta` claim pattern from SD-4).

## Scope — what PS does NOT do

- No change to the Doubao realtime service, the RTC join order, or `OutputMode 0`.
- No kernel coefficient change (EMA smoothing is a *separate, later* `[Claude]` item
  — see "Later" + the eros-engine note). PS feeds the kernel the same shape the
  hybrid trailer feeds it today.
- No new memory type / DDL. `record_turn_memories` already writes SQLite.
- No mid-turn gating (hard silence/refuse) — that's redesigned as steering in PS-4.

## Slices

| Slice | Content | Done when |
|-------|---------|-----------|
| **PS-1** | Analyzer core: transcript → signals JSON → kernel + memory + persist (SQLite) | unit tests green w/ mock provider; kernel + memory move from a canned transcript |
| **PS-2** | Wire to RTC: `POST /rtc/turn` + frontend per-turn post + `BackgroundTask` + reflection | speaking a few turns moves SQLite trust/closeness + writes a memory row, latency unchanged |
| **PS-3** | SHAPE: discretized kernel state (mood+relationship buckets) → Chinese stance block folded into `system_role` at `StartVoiceChat` (join-time, per-call) | new call's `system_role` reflects current mood/relationship; pure fn of the kernel, no API/schema change |
| **PS-4** | Steering: kernel buckets → one Chinese stance *directive* appended to the PS-3 block (terse-sharp / comfort / warmer) | a sustained mood/relationship state visibly shifts Boxi's tone in the next call |

PS-1 + PS-2 shipped (commits c0cbd6d/90fdfea/899e8e1/bfa9f06). PS-3 + PS-4 are
specced in full below — **join-time injection** (`UpdateVoiceChat` can't update
`system_role` mid-session; see PS-3 "Why join-time").

## Architecture

```
pure-E2E turn finalizes (user_text, bot_text)
        │  (frontend already parses RTC subtitles → it owns the turn boundary)
        ▼
POST /rtc/turn  ──►  BackgroundTask: analyze_turn(store, user_text, bot_text, budget)
                          1. evaluate_behavior(user_text)      # local mood delta (reused)
                          2. signals = llm_analyze(user_text, bot_text)   # 1 DeepSeek call → JSON
                          3. apply_signals_to_kernel(store, signals)      # trust/closeness/tension
                          4. persist_chat_turn(...) → user_msg_id         # voice turn enters SQLite
                          5. record_turn_memories(store, signals=..., source_message_id=user_msg_id)
                          6. note_llm_turn(); run_reflection_if_due(store, budget)   # SD-4 reused
        ▲
        └─ Viking AddSession on hangup (VM-3) stays as-is — cloud layer, untouched
```

---

## PS-1 — Analyzer core (`backend/app/reflection/turn_analyzer.py`) `[Claude]`

New module beside `runner.py` / `jobs.py` (it's the **per-turn** sibling of the
every-N reflection). One public function:

```python
def analyze_turn(
    store: MemoryStore,
    *,
    user_text: str,
    bot_text: str,
    budget: BudgetConfig | None = None,
) -> None:
    """Off-path: transcript -> signals -> kernel + memory (SQLite). Never raises."""
```

Behavior:

1. **Guard / config.** Return early if `not budget.enable_turn_analyzer`, or both
   `user_text` and `bot_text` are blank. Wrap the whole body in try/except → log +
   return (non-negotiable #3).
2. **Local appraisal (reused).** `evaluate_behavior(store, BehaviorEvent(
   event_type="user_message", user_input=user_text))` — this already applies the
   deterministic mood delta from the user's words (same as the hybrid pre-LLM step).
   Keep its `BehaviorDecision` for PS-4; PS-1 only needs the side-effect.
3. **LLM analysis pass (the new bit).** One `get_provider_router().complete(
   ChatCompletionRequest(messages=[...], max_output_tokens=~220))` call (default
   provider = DeepSeek), **English-internal** instruction, transcript as input,
   **JSON-only** output. The JSON keys MUST match the existing signals schema
   (single source of truth: `persona.OUTPUT_PROTOCOL`) so the existing consumers
   accept it verbatim:
   ```json
   {"appraisal":{"valence":-1..1,"arousal":0..1,"goal_relevance":0..1,"note":"..."},
    "relationship":{"trust":-0.1..0.1,"closeness":-0.1..0.1,"tension":-0.1..0.1},
    "memory":[{"type":"<one of the 8 whitelisted>","content":"...","importance":0..1,
               "confidence":0..1,"tags":[]}]}
   ```
   Parse one JSON object (reuse the tolerant parse helper pattern from
   `reflection/jobs.py`); on `ProviderError` / parse failure → `signals = None`; **still persist the
   transcript + run regex memory** (history stays complete) — skip only the kernel. **Note:** the analyzer prompt is *analysis*
   ("rate this exchange"), not the *generation* trailer — it never produces a reply,
   so it can't leak.
4. **Kernel (reused, unchanged).** `apply_signals_to_kernel(store, signals)` — it
   already clamps deltas to ±0.1, decays tension, bumps familiarity, etc.
5. **Persist the spoken turn (so SQLite owns voice too).** Build a minimal
   `ChatCompletionResult(provider="doubao_realtime", model=<rt model or "doubao-rt">,
   content=bot_text, usage=<zero>, cost=0.0, mock=False)` and
   `persist_chat_turn(store, [ChatMessageSchema(role="user", content=user_text)],
   result, decision="reply", avatar_state=signals.avatar_state or "talking",
   should_call_llm=True)`. Capture `user_message_id = saved_ids[0]`. This makes voice
   turns first-class in SQLite → summaries + reflection now cover voice, not just text.
6. **Typed memory (reused, unchanged → SQLite).** `record_turn_memories(store,
   user_input=user_text, signals=signals, source_message_id=user_message_id,
   budget=budget)`. With `llm_memory_extraction` on + `signals.memory[]` present →
   `write_memories_from_signals` (writer="llm"); empty/all-rejected → regex M2
   fallback (SD-3b). **This is the "update SQLite, not just Viking" requirement —
   satisfied by reusing the existing writer; no new code path.**
7. **Reflection (reused).** `store.note_llm_turn()` then
   `run_reflection_if_due(store, budget)` so the SD-4 dreaming layer (consolidation,
   impression, summary) now also fires from voice.

### Config knobs (`memory/budget.py` + both `config/budget*.json`) `[Cursor-ok]`

- `enable_turn_analyzer: bool = True`
- `analyze_every_n_turns: int = 1`  (default per-turn; raise to batch if cost matters)

Reuse the existing `auto_memory_write`, `llm_memory_extraction`, `enable_reflection`,
`reflection_every_n_turns` knobs unchanged. Missing keys → defaults (old configs work).

> `analyze_every_n_turns` > 1: keep a per-room counter in `schema_meta`
> (`turns_since_analysis`) and only run the LLM pass when due; still persist the turn
> + run local appraisal every turn (those are cheap), batch only the LLM analysis.

---

## PS-2 — Wire to RTC (`backend/app/rtc/routes.py` + `frontend/src/rtc/**`)

**Backend:** new `POST /rtc/turn` (schema in `backend/app/schemas.py`:
`{room_id, user_id, user_text, bot_text}`). Handler validates non-empty, then
`background_tasks.add_task(analyze_turn, store, user_text=..., bot_text=...,
budget=load_budget_config())` and returns `{"status":"ok"}` immediately. Reuse
`get_memory_store()` like the other RTC routes. Single-flight: claim per-room in
`schema_meta` so a slow analysis can't overlap the next turn's.

**Frontend:** the subtitle stream already yields per-turn user/bot text
(`frontend/src/rtc/rtcMessages.ts`, rendered by `RtcSubtitleList`). When a bot turn
finalizes (a completed user→bot exchange), POST it to `/rtc/turn`
(`frontend/src/rtc/api.ts` + the hook in `useRtcVoice.ts`). Fire-and-forget; a failed
post must never disturb the call. The existing hangup→`/rtc/memory/session` (Viking)
flow stays.

> Alternative (more robust, later): consume Doubao/RTC **server-side**
> conversation-state / subtitle callbacks (`EnableConversationStateCallback` is
> already on) so analysis survives the browser closing. Out of scope for PS-2; note it.

---

## PS-3 — Join-time state injection (kernel → stance block) `[Claude→Cursor]`

### Goal (one sentence)
At each `StartVoiceChat`, fold a **compact, discretized Chinese stance block** (from
`mood_state` + `relationship_state`) into `system_role`, so the pure-E2E agent opens
each call carrying Boxi's current cross-session mood + relationship — extending VM-4's
join-time memory injection.

### Why join-time (not mid-session)
`UpdateVoiceChat` supports only `Interrupt` / `ExternalTextToSpeech` /
`FunctionCallResult` — **no mid-session `system_role`/config update** (config changes
need Stop+Start; verified against the Volcengine + EMQX API refs, 2026-06-11). So state
shapes the agent **once per call, at join**. That is sufficient: the kernel moves
slowly (±0.1/turn, bucketed slower), calls are bounded, and **within a call Doubao
keeps its own conversational/emotional context** — the kernel's real job is carrying
*cross-session* stance, which join-time injection does well. (Mid-session would need the
Doubao Dialog-WS transport, not the RTC OpenAPI path — out of scope.)

### Mechanism — `backend/app/rtc/state_block.py` (new)
Pure functions of the store (self-fetch like `sqlite_memory.load_sqlite_memory_context()`):

```python
def build_rtc_state_block(store: MemoryStore | None = None) -> str:
    """Discretized Chinese stance block from the kernel. '' when fully neutral."""
```
- Read `store.get_mood_state()` + `store.get_relationship_state()`.
- **Discretize to buckets** (qualitative reads better than floats + keeps it short):
  low `<0.34` / mid `<0.67` / high `≥0.67`.
- Render (`情绪` only when notable; `关系` always — it's the cross-session value):
  ```
  【你此刻的状态】
  情绪：有点烦躁
  和这个用户：信任中、亲近中、有点别扭
  ```
  - 情绪 — first match else omit: `annoyance≥.5→"有点烦躁"`, `worry≥.5→"有点担心ta"`,
    `loneliness≥.5→"有点想找人说话"`, `boredom≥.5→"有点无聊"`, `energy≤.3→"没什么精神"`.
  - 关系 — `信任{低/中/高}、亲近{低/中/高}`, append `、有点别扭` only when `tension≥.4`.
- Return `""` when 情绪 omitted AND trust/closeness both mid AND tension low (nothing
  worth saying). Coefficients/wording are **starting values — tune in implementation**.

### Wiring — `backend/app/rtc/routes.py`
In `_load_rtc_memory_context`, prepend the stance ahead of recalled memory:
```python
return _merge_memory_context(
    build_rtc_state_block(), build_rtc_steering_directive(),  # PS-3, PS-4
    sqlite_context, viking_context,
)
```
`_merge_memory_context` already drops empty parts; `voice_chat.build_voice_chat_body`
already appends `memory_context` to `system_role`. **No change to `voice_chat.py`.**

---

## PS-4 — Join-time steering directive (kernel → stance imperative) `[Claude→Cursor]`

### Goal (one sentence)
Turn PS-3's *described* state into **one imperative Chinese directive** appended to the
block, so a sustained mood/relationship state actively steers Boxi's tone next call —
**state-as-persona, not stage-direction.**

### Mechanism — same `state_block.py`
```python
def build_rtc_steering_directive(store: MemoryStore | None = None) -> str:
    """One Chinese stance directive from the kernel buckets. '' for the default persona."""
```
Derived purely from kernel buckets — **no behavior-engine call, no `schema_meta`, no
PS-1 edit** (fully additive in the rtc layer). First match wins; else `""`:

| Condition (kernel) | Directive (appended after the PS-3 block) |
|---|---|
| `worry≥.5` | `用户最近不太好，收一收毒舌，话短一点、稳一点。` |
| `annoyance≥.5` or `tension≥.4` | `你对最近的互动有点不耐烦，可以更冲、更短，但别真羞辱用户。` |
| `closeness≥.67` and `tension<.3` | `你和ta挺熟了，可以更随意、更贴一点，毒舌底色别丢。` |
| else | `""` (default persona governs) |

**Principle:** describe stance + a constraint, never literal actions —
`你现在没耐心，话更短更冲` ✅ vs `叹口气然后转移话题` ❌ (risks literal narration / stilted
delivery). Hard silence/refuse are **not** reproduced (dead air after the user speaks is
broken voice UX); they degrade to terseness via the annoyance directive.

### Done criteria (PS-3 + PS-4)
1. `PYTHON_BIN=.venv/bin/python npm run check` green; pure-E2E path + V1 untouched.
2. `backend/tests/test_rtc_state_block.py`: canned `mood_state`/`relationship_state` →
   expected block + directive lines; fully-neutral kernel → both return `""`; each
   steering branch fires on its bucket.
3. Wiring test: with a non-neutral kernel the join-time `system_role` (assert on
   `build_voice_chat_body` output or the merged context) contains the stance block.
4. Diff confined to: `backend/app/rtc/state_block.py` (new), `backend/app/rtc/routes.py`
   (one merge line), tests, `docs/SESSION_LOG.md`, `docs/TODO.md`. **No soul edits, no
   new API, no `schema_meta`, no `UpdateVoiceChat`.**

### Boundaries
- **Join-time only** (per call). NOT mid-session. A long single call won't refresh
  stance mid-way (accepted; Doubao handles in-call continuity).
- Pure, read-only on the store; never raise into the join path (wrap; `''` on any error).
- Chinese for all injected text; keep the whole block ~2–4 short lines.
- Proactive (Boxi initiating mid-call via `ExternalTextToSpeech`) + revive-companion
  timing are a **separate later item**, not PS-3/PS-4.

---

## Done criteria (PS-1 + PS-2)

1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; the
   pure-E2E voice path + V1 untouched; analyzer tests use the **mock provider** (no
   real LLM).
2. From a canned `(user_text, bot_text)`, `analyze_turn` moves `relationship_state`
   (trust/closeness/tension) and writes ≥1 typed memory **in SQLite**; a forced
   provider/parse failure **still persists the transcript** but does NOT move the
   kernel or write `writer="llm"` memory (no raise, no bad-data write).
3. `POST /rtc/turn` returns immediately; analysis runs in the background; **spoken
   latency unchanged** (it's off the audio path).
4. After a few real pure-E2E turns: SQLite shows the voice turns persisted, kernel
   moved, a memory row with `writer="llm"`, and (at threshold) a reflection
   impression — i.e. **voice now feeds the same soul as text**.
5. Diff confined to: `backend/app/reflection/turn_analyzer.py` (new),
   `backend/app/rtc/routes.py` + `backend/app/schemas.py` (endpoint),
   `backend/app/memory/budget.py` + `config/budget*.json` (2 knobs),
   `frontend/src/rtc/**` (per-turn post), tests, `docs/MEMORY_DESIGN.md` (note: voice
   turns now feed `record_turn_memories`/reflection off-path), `docs/SESSION_LOG.md`,
   `docs/TODO.md`, `docs/OPEN_SOURCE_REUSE.md`. **No kernel math change; no DDL; no
   change to the Doubao realtime service or `OutputMode 0`.**

## Boundaries

- Additive: pure-E2E latency + the spoken turn are sacred — analyzer is always
  off-path, fire-and-forget, single-flight, failure-isolated.
- Soul reused, not edited (kernel/writers/reflection called as-is). If hybrid-grade
  fidelity later needs a kernel change (e.g. EMA smoothing of noisy per-turn LLM
  deltas — see eros-engine), stop and flag it `[Claude]` + update `MEMORY_DESIGN.md`.
- Keys/credentials unchanged; nothing new sent to the browser.
- SQLite = source of truth; Viking stays the cloud layer. Do not try to two-way sync
  them in PS (note divergence as future work).

## Open-source reuse (study only — record in `docs/OPEN_SOURCE_REUSE.md` if adopted)

- **etherfunlab/eros-engine** (Rust, **AGPL-3.0 → study only, no code copy**):
  validates this exact design — relationship state as a small **numeric vector** with
  deterministic **EMA smoothing (inertia)** + time decay, structured insight extracted
  **async at session end**, and an **`affinity_scope`** flag that injects *composites*
  (bond/chemistry) instead of raw axes. Two ideas to lift later: EMA on the analyzer's
  per-turn deltas (PS kernel follow-up), and scope-gated injection (PS-3).
- **pearthink123/revive-companion** (Python, **MIT → adoptable**): probabilistic
  **proactive timing** (Poisson "longing" curve P=1−e^(−λt) + Bayesian user-state
  inference + quiet hours). Top candidate for the *proactive* part of the later
  behavior work — maps onto our existing `loneliness` mood var. Not part of PS.
