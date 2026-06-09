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
- [ ] **SD-2 — Subjectivity kernel `[Claude]`.** New `relationship_state` singleton
  table (trust/closeness/familiarity/tension/last_meaningful_interaction_at); `trust`
  **moves** here (source of truth), `loneliness` **stays** in mood_state but is
  re-sourced from closeness/time-since-contact; appraisal-driven local math + decay;
  `[Relationship]`/`[Impression]` context blocks; tone factors relationship.
  **Additive table only — no `mood_state` ALTER/DROP** (no migration framework
  exists); seed singleton via `INSERT OR IGNORE`; optional one-time `trust` back-fill.
  **Update `docs/MEMORY_DESIGN.md`.**
- [ ] **SD-2-UI — "Boxi 怎么看你" panel `[Cursor-ok]`.** Read-only panel showing
  relationship state (trust/closeness/familiarity/tension) + impression narrative.
  Numbers land with SD-2; impression text fills in after SD-4. Frontend-only.
- [ ] **SD-3 — LLM memory extraction (M3) `[Claude]`.** Route `signals.memory[]`
  through existing dedup pipeline (`write_memories_from_signals`); keep regex M2 as
  fallback; `writer="llm"` tag; lightweight metadata links.
- [ ] **SD-4 — Background reflection layer `[Claude]`.** Turn-counter trigger
  (`reflection_every_n_turns`); jobs: memory consolidation/evolution, impression
  formation (`relationship_state` memory type), LLM conversation summary. Run via
  `BackgroundTasks` off the response path; single-flight; config-gated
  (`enable_reflection`); failure-isolated.
- [ ] **SD-5 (optional) — Memory links + top-down retrieval `[Claude]`.**
  `memory_links` table + category-first retrieval. **Update `docs/MEMORY_DESIGN.md`.**
- [ ] **SD config knobs `[Cursor-ok]`.** Add `llm_memory_extraction`,
  `enable_reflection`, `reflection_every_n_turns`, `llm_summary` to
  `BudgetConfig` + `config/budget*.json` with safe defaults.

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
- [ ] Voice output: strip stage-direction parentheticals from spoken text (Option A, `textForSpeech`) `[Cursor]`.
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
