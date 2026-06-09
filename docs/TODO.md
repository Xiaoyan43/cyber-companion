# TODO

## Soul Deepening (Claude spec 2026-06-09 → Cursor implements → Claude reviews)

Spec: `docs/SOUL_DEEPENING_SPEC.md`. Incremental on the working app, **no rebuild**.
Latency-smart: ① piggyback (same reply call) ② background reflection ③ local math.
Order: SD-1 → SD-2 → SD-3 → SD-4; SD-5 later. One phase = one checkpoint.

- [x] **SD-1 — Piggyback signal contract `[Claude→Cursor]`.** Extend
  `StructuredAssistantResponse` with optional `signals` + tolerant parse
  (`behavior/parser.py`); streaming sentinel-strip (`main.py`); output-protocol
  section to persona (`memory/persona.py`). Done: `signals` parsed when present,
  **never leaks** to `content`/TTS/stream deltas; absent/malformed → today's behavior.
  Tests in `test_behavior.py` (parser + `SignalStreamFilter`).
- [x] **SD-2 — Subjectivity kernel `[Claude]`.** New `relationship_state` singleton
  table (trust/closeness/familiarity/tension/last_meaningful_interaction_at); `trust`
  **moves** here (source of truth), `loneliness` **stays** in mood_state but is
  re-sourced from closeness/time-since-contact; appraisal-driven local math + decay;
  `[Relationship]`/`[Impression]` context blocks; tone factors relationship.
  **Additive table only — no `mood_state` ALTER/DROP** (no migration framework
  exists); seed singleton via `INSERT OR IGNORE`; optional one-time `trust` back-fill.
  **Update `docs/MEMORY_DESIGN.md`.**
- [x] **SD-2-UI — "Boxi 怎么看你" panel `[Cursor-ok]`.** Read-only panel showing
  relationship state (trust/closeness/familiarity/tension) + impression narrative.
  Numbers land with SD-2; impression text fills in after SD-4. Frontend-only.
- [x] **SD-3 — LLM memory extraction (M3) `[Claude]`.** Route `signals.memory[]`
  through existing dedup pipeline (`write_memories_from_signals` +
  `record_turn_memories` orchestrator); keep regex M2 as fallback; `writer="llm"`
  tag; `llm_memory_extraction` knob. Cross-type linking moved to SD-5. Spec:
  `docs/SD3_SPEC.md`.
- [x] **SD-4 — Background reflection layer `[Claude]`.** Turn-counter trigger
  (`reflection_every_n_turns`); jobs: memory consolidation/evolution, impression
  formation (`relationship_state` memory type), LLM conversation summary. Run via
  `BackgroundTasks` off the response path; single-flight; config-gated
  (`enable_reflection`); failure-isolated. Spec: `docs/SD4_SPEC.md`.
- [x] **SD-1b — Make the model actually emit the signals trailer `[Claude]`.**
  Real-DeepSeek smoke (Session 27) found the trailer is rarely emitted in the chat
  path (~0–1/3) → signals don't flow (trust/closeness frozen, memories fall to regex
  M2). Fix (validated live, raises emission to 4/5): mandatory `OUTPUT_PROTOCOL` +
  one-shot example, drop the "omit" escape (`persona.py`); position protocol LAST in
  the system message (`context_builder.py`); raise `max_output_tokens_per_turn`
  300→600 so the trailer isn't truncated. **Spec: `docs/SD1b_SPEC.md`.** Highest
  priority — without it SD-2/SD-3's live value is dormant.
- [x] **SD-1c — Trailer reminder on the current user turn `[Claude]`.** SD-1b
  re-smoke found the strengthened protocol still emits 0 in the real chat path: we
  replay trailer-stripped assistant history, so the model mimics "no trailer" and
  ignores the system instruction. Validated fix (0/5→3/5): append a short
  mandatory-trailer reminder to the **current user message** (provider-only, never
  persisted/replayed) in `context_builder.build_provider_context`. A trailing system
  message does NOT work. **Spec: `docs/SD1c_SPEC.md`.** Highest priority (pairs with
  SD-1b to actually make signals flow).
- [x] **SD-3b — M2 fallback when M3 writes nothing + valid memory types `[Claude]` (done @ Session 28).**
  Code + tests + gate landed (195 tests + tsc); **Done criterion #2 PASSED on real
  DeepSeek** (Session 28, 7-turn smoke): zero-leak ✅, signals flowed
  (trust 0.50→0.52 / closeness 0.20→0.22 / familiarity 0→0.07 / tension 0→0.17),
  **7 factual memories persisted with `writer="llm"`** (M3 validated — profile/project/
  job_progress/reminder), SD-4 impression written, reflection fired. The vanished-facts
  regression is fixed.
  SD-1c payoff smoke: signals now flow (trust 0.5→0.63, closeness 0.2→0.36 ✅) but
  factual memories vanished — `record_turn_memories` committed to M3 when `memory[]` is
  non-empty and never fell back to M2, so LLM items that fail validation (type ∉
  whitelist) dropped the turn's write. Fix: M3 empty → fall through to regex M2
  (`write_policy.py`); enumerate the 8 allowed memory types in `OUTPUT_PROTOCOL`
  (`persona.py`); `MEMORY_DESIGN.md` Auto-Write note updated. **Spec: `docs/SD3b_SPEC.md`.**
- [x] **SD-5 (optional) — Memory links + top-down retrieval `[Claude]` (done @ Session 28).**
  Additive `memory_links` table (`SCHEMA_VERSION=3`, bidirectional + idempotent +
  `ON DELETE CASCADE`); deterministic cross-type linker in reflection (after
  consolidate, no LLM); 1-hop retrieval expansion (additive, capped, expired-skipped);
  consolidation candidate set restricted to `FACTUAL_MEMORY_TYPES`. `docs/MEMORY_DESIGN.md`
  updated. 207 backend tests + tsc green (+12 `test_memory_links.py`). Spec:
  `docs/SD5_SPEC.md`.
- [x] **SD-5b — CJK-aware tokenizer for linker + retrieval `[Claude]` (done @ this commit).**
  jieba segmentation in `retrieval.tokenize` (lazy import + fallback); linker ratio
  0.34→0.25; Chinese recall + cross-type link unit tests. **Spec: `docs/SD5b_SPEC.md`.**
  **Claude re-smoke PASS (Session 28b):** Chinese 6-turn smoke now forms 2 logical
  `memory_links` (was 0 pre-jieba) — `job_progress`↔`recent_event` sharing Acme/项目.
- [x] **SD config knobs `[Cursor-ok]`.** `llm_memory_extraction` (SD-3);
  `enable_reflection`, `reflection_every_n_turns`, `llm_summary` (SD-4) in
  `BudgetConfig` + `config/budget*.json`.

## Current Priority

- [x] Create a checkpoint commit for the current Phase 2-10 MVP batch after user approval.
- [x] Have Claude Code do a read-only architecture/security/memory/behavior review of the current MVP batch.
- [x] Create foundational project files and cross-tool rules.
- [x] Add open-source reuse policy.
- [x] Create project scaffold.
- [x] Build local dev scripts.
- [x] Create basic frontend shell.
- [x] Create basic backend health check.

## Review Findings (Claude, 2026-06-08, @ commit 5005731)

Owner tags: `[Claude]` touches restricted layers (cost/provider/memory/behavior
contract) — do not hand to Cursor without explicit approval + doc updates.
`[Cursor-ok]` is safe for Cursor with the usual checks.

- [x] **S3 — Enforce budget caps `[Claude]` (done @ this commit).**
  `monthly_usd_limit` / `daily_llm_turn_limit` / `allow_reasoning_model` are now
  loaded in `load_budget_config` and enforced in `/chat/complete` via
  `backend/app/memory/usage_guard.py` (blocked turns answer locally, cost 0, not
  counted). Documented in `docs/COST_AND_TOKEN_BUDGET.md`; tests in
  `backend/tests/test_usage_guard.py`.
- [x] **A1+A2 — Memory-layer scan + retention `[Claude]` (done @ this commit).**
  `build_provider_context` / `summary_policy` now use SQL boundary queries
  (`count_chat_messages`, `list_recent_chat_messages`, `list_chat_messages_between`);
  `behavior_tick_retention` prunes idle lines after each persisted tick.
- [x] **B3 — Truncate user input before provider call `[Claude]` (done @ this commit).**
  `max_user_input_tokens` clamps the provider-bound user turn; behavior and
  persistence still use the full original text.
- [x] **M1 — Filter expired memories on retrieval (done @ this commit).**
  `is_expired` + context_builder recall filter; `/memory/memories` unchanged.
- [x] **M2 — Auto-write memories from conversation (rule-based MVP @ this commit).**
  `write_policy.maybe_write_memories_from_turn` runs after `/chat/complete`;
  conservative regex triggers, dedup update, `auto_memory_write` budget gate.
  LLM-based extraction remains future work.

## Backlog

### UI

- [x] Pixel character renderer.
- [x] State animation definitions.
- [x] Chat panel.
- [x] Avatar state debug controls.
- [x] Trapped-in-box idle behaviors.
- [x] Reload chat history from `/memory/messages`.
- [x] Display last-turn token/cost metadata.
- [x] Route empty submit through backend behavior decisions.
- [x] Memory links visualization in UI `[Claude]→Cursor` — read-only `GET /memory/links`
  route + "Boxi 把这些联系起来了" panel. **Spec: `docs/MEMORY_LINKS_UI_SPEC.md`**.

### Provider Layer

- [x] Define provider interface.
- [x] Add DeepSeek adapter.
- [x] Add OpenAI adapter placeholder.
- [x] Add local model adapter placeholder.
- [x] Add provider config file.
- [x] Add cost estimate metadata.

### Memory

- [x] Define SQLite schema.
- [x] Add database initialization.
- [x] Add message persistence.
- [x] Add memory CRUD.
- [x] Add mood state persistence.
- [x] Add retrieval policy.
- [x] Add summary policy.

### Behavior

- [x] Define behavior decision contract.
- [x] Implement local state variables.
- [x] Implement reply/silent/refuse/interrupt/proactive decisions.
- [x] Add persona prompt.
- [x] Add structured LLM response parser.

### Security

- [x] Add allowed folders config.
- [x] Implement path permission gateway.
- [x] Add file access log.
- [x] Add symlink escape tests.
- [x] Review Vite/esbuild dev-server audit advisory before exposing dev server beyond localhost.

### Text MVP

- [x] Connect frontend chat to backend dialogue endpoint.
- [x] Reload persisted messages on app startup.
- [x] Honor backend `avatar_state` during reply animation.
- [x] Surface basic token/cost metadata in UI.
- [x] Route empty submit through backend behavior instead of frontend-only timing.

### Voice

- [x] Design push-to-talk STT interface.
- [x] Add STT adapter placeholder.
- [x] Add push-to-talk UI and local audio capture flow.
- [x] Add mock STT provider and `/stt/transcribe` route.
- [x] Gate cloud STT behind budget/config flags.
- [x] Add TTS adapter placeholder.
- [x] Define selective speech policy.
- [x] Voice V1: local TTS via macOS `say` (`MacSayTTSProvider`, `config/tts.json`).
- [x] Voice V2: local STT via faster-whisper (`FasterWhisperProvider`, base model, PyAV decode).
- [x] Cloud TTS: 火山/豆包 adapter (`DoubaoTTSProvider`, cloud-gated by `allow_cloud_tts`).
- [x] Voice output: strip stage-direction parentheticals from spoken text (Option A, `textForSpeech`) `[Cursor]`.
- [ ] Latency: reuse 豆包 adapter HTTP connection (persistent httpx client + keep-alive) `[Cursor]`.
- [ ] Latency: streaming TTS backend — 豆包 streaming synth + GET `/tts/stream` (MP3 chunks) `[Claude spec → Cursor]`.
- [ ] Latency: streaming TTS frontend — progressive `<audio>` playback; MUST preserve avatar/TTS race fix `[Cursor]`.
- [ ] Voice cost tracking + per-day/month brake for cloud TTS/STT (parallels S3; not yet covered) `[Claude]`.

### Documentation

- [ ] Update docs after each milestone.
- [x] Add developer setup once scaffold exists.
- [x] Add manual verification checklist.
- [x] Evaluate open-source candidates before building major modules from scratch.

### Maintenance

- [x] Review FastAPI TestClient/httpx2 deprecation warning.
- [x] Fix stale `test_stt_status_route` `[Cursor]` (顺手修). It asserts
  `allow_cloud_stt is False` but Session-26 `config/budget.json` committed it as
  `true` (walls off) → 1 red in `npm run check`. Proper fix: isolate the test's own
  `budget.json` in a tmp `CYBER_COMPANION_CONFIG_DIR` so it's deterministic,
  rather than flipping the assertion to match the mutable live config.
