# TODO

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

### Documentation

- [ ] Update docs after each milestone.
- [x] Add developer setup once scaffold exists.
- [x] Add manual verification checklist.
- [x] Evaluate open-source candidates before building major modules from scratch.

### Maintenance

- [x] Review FastAPI TestClient/httpx2 deprecation warning.
