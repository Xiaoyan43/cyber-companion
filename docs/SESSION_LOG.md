# Session Log

## 2026-06-08 - Session 0

本次完成：

- Created foundational project rules and documentation.
- Defined the project brief, architecture, memory design, persona behavior, security boundaries, cost policy, roadmap, and TODO list.
- Added cross-tool responsibilities for Codex, Claude Code, and Cursor.
- Added open-source reuse as a default development strategy, with license checks and source tracking.
- Adjusted open-source policy for private personal-use: prioritize speed and experimentation, while keeping source/license notes for awareness and future cleanup.

下次接着做：

- Create the initial project scaffold.
- Recommended next task: set up frontend/backend directory structure, dev scripts, config examples, and a backend health check.

已知问题：

- No runnable code exists yet.
- Exact framework choices are recommended but not locked by implementation.
- Provider API keys and real pricing checks are not configured yet.

相关文件：

- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/rules/cyber-companion.mdc`
- `README.md`
- `docs/PROJECT_BRIEF.md`
- `docs/ARCHITECTURE.md`
- `docs/MEMORY_DESIGN.md`
- `docs/PERSONA_AND_BEHAVIOR.md`
- `docs/COST_AND_TOKEN_BUDGET.md`
- `docs/SECURITY_AND_PERMISSIONS.md`
- `docs/SESSION_PROTOCOL.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/MVP_ROADMAP.md`
- `docs/TODO.md`
- `docs/SESSION_LOG.md`

测试结果：

- Not applicable. Documentation-only foundation step.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not grant broad filesystem access.
- Do not make the character a generic polite assistant.
- Do not let unclear-license or restrictive open-source code become hard to replace without recording the source and tradeoff.

## 2026-06-08 - Session 1

本次完成：

- Reviewed `AGENTS.md`, project protocol/docs, current TODO/log, and open-source reuse policy before editing.
- Audited the existing scaffold instead of overwriting it.
- Kept the React + TypeScript frontend shell and added a local API health status indicator.
- Kept the FastAPI backend shell and verified `/health` returns the expected payload.
- Added `npm run health`, `npm run build:frontend`, executable shell scripts, and a reload toggle for restricted environments: `CYBER_COMPANION_API_RELOAD=0`.
- Updated `scripts/dev.sh` so frontend `VITE_API_BASE_URL` follows `CYBER_COMPANION_API_HOST` and `CYBER_COMPANION_API_PORT`.
- Fixed `scripts/check.sh` so npm workspace installs at root `node_modules/` are detected correctly.
- Installed local dev dependencies into `.venv/` and `node_modules/`; generated `package-lock.json`.
- Updated TODO status for Phase 1 scaffold tasks and recorded accepted open-source dependencies/tradeoffs.

下次接着做：

- Start Phase 2: pixel character renderer/state animation cleanup, then chat panel integration.
- Add a manual verification checklist after the first visible UI pass.
- Review the Vite/esbuild dev-server advisory before exposing the dev server beyond localhost or upgrading Vite across a major version.

已知问题：

- `npm audit` reports 2 moderate dev-dependency findings through Vite 5.x/esbuild; `npm audit --omit=dev` reports 0 production vulnerabilities.
- Backend tests pass but show a FastAPI/Starlette TestClient deprecation warning about `httpx`/`httpx2`.
- Port `8000` was already used by another local project during verification, so the real health check used `CYBER_COMPANION_API_PORT=18000`.

相关文件：

- `package.json`
- `package-lock.json`
- `scripts/dev.sh`
- `scripts/dev_backend.sh`
- `scripts/check.sh`
- `scripts/health.sh`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/tests/test_health.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `README.md`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python bash scripts/check.sh`: backend compile passed; `backend/tests/test_health.py` passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning.
- `bash -n scripts/dev.sh scripts/dev_backend.sh scripts/check.sh scripts/health.sh`: passed.
- `PYTHON_BIN=.venv/bin/python npm run check`: passed; same TestClient deprecation warning.
- `npm run build:frontend`: passed; Vite production build completed.
- `CYBER_COMPANION_API_PORT=18000 npm run health`: passed against a running local FastAPI server; returned `{"service":"cyber-companion-api","status":"ok","version":"0.1.0"}`.
- Browser smoke test at `http://127.0.0.1:5173/`: page loaded, API badge showed `ok v0.1.0`, one chat submit appended user and Boxi messages, console error/warn logs were empty, and 390px mobile viewport had no horizontal overflow.
- `npm audit --omit=dev`: 0 vulnerabilities.
- `npm audit`: 2 moderate dev-dependency findings in Vite/esbuild; no forced major upgrade applied.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not grant broad filesystem access; future agent file access must go through explicit allowed folders.
- Do not send full conversation history to the LLM by default.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 2

本次完成：

- Read `AGENTS.md`, `.cursor/rules/cyber-companion.mdc`, `docs/TODO.md`, `docs/SESSION_LOG.md`, and `docs/OPEN_SOURCE_REUSE.md` before editing.
- Evaluated pixel renderer/animation open-source options (PixiJS, react-spring, CSS sprite-state patterns) and kept the existing CSS/DOM approach to avoid architecture churn.
- Extracted `PixelCharacter` into `frontend/src/components/PixelCharacter.tsx` with base layout CSS.
- Centralized avatar state types/lines in `frontend/src/avatar/types.ts`.
- Moved all per-state face shapes and motion into `frontend/src/avatar/stateAnimations.css` with distinct idle, happy, sad, angry, sleepy, thinking, talking, worried, annoyed, and silent animations.
- Slimmed `frontend/src/App.tsx` and `frontend/src/styles.css` so the companion shell only wires state controls and chat shell to the renderer.

下次接着做：

- Wire chat submit to temporary talking/thinking state timing instead of leaving `talking` stuck after send.
- Add trapped-in-box idle behaviors beyond the current sway loop.
- Start provider abstraction only after the visible UI pass feels stable.

已知问题：

- Avatar state debug buttons remain dev-only controls; they should later move behind a debug flag or dev panel.
- `talking` state persists after chat send until the user clicks another state.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `frontend/src/App.tsx`
- `frontend/src/avatar/types.ts`
- `frontend/src/avatar/stateAnimations.css`
- `frontend/src/components/PixelCharacter.tsx`
- `frontend/src/components/PixelCharacter.css`
- `frontend/src/styles.css`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; backend compile and health test passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not start provider abstraction, SQLite memory, or file permission gateway in this UI-only pass.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 3

本次完成：

- Read `AGENTS.md`, `.cursor/rules/cyber-companion.mdc`, `docs/CURSOR_PHASE_PLAYBOOK.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`, and `docs/OPEN_SOURCE_REUSE.md` before editing; inspected git status and kept existing uncommitted Phase 2 work intact.
- Advanced **Phase 2 slice**: chat-driven avatar timing, trapped-in-box idle behaviors, and dev-only debug controls.
- Added `useAvatarState` + `timing.ts` so chat submit runs `thinking` → `talking` → `idle`, empty submit briefly shows `annoyed`, and timers clean up on manual debug override.
- Delayed shell Boxi reply until the talking phase starts; message list now auto-scrolls to the latest bubble.
- Replaced simple idle sway with trapped-in-box idle motion: wall presses, slump/peek cycle, arm reactions, and subtle box flicker.
- Moved avatar state buttons into a dev-only `<details>` panel (`import.meta.env.DEV` or `VITE_SHOW_AVATAR_DEBUG=1`).
- Added `docs/MANUAL_VERIFICATION.md` for Phase 2 UI checks.

下次接着做：

- Start Phase 3 provider abstraction on the backend only; keep frontend chat wired to local API endpoints instead of hardcoded shell replies.
- Later connect behavior engine output to avatar state instead of frontend timers once Phase 6 exists.

已知问题：

- Chat replies are still hardcoded shell text; provider integration is intentionally not started in this slice.
- Avatar timing is frontend-only and will need replacement by behavior engine decisions in a later phase.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `frontend/src/App.tsx`
- `frontend/src/avatar/timing.ts`
- `frontend/src/avatar/useAvatarState.ts`
- `frontend/src/avatar/stateAnimations.css`
- `frontend/src/components/PixelCharacter.css`
- `frontend/src/styles.css`
- `docs/MANUAL_VERIFICATION.md`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; backend compile and health test passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not start provider abstraction, SQLite memory, or file permission gateway in this UI-only pass.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 4

本次完成：

- Continued from Session 3 and implemented **Phase 3 - Provider Abstraction** while respecting existing uncommitted Phase 2 frontend work.
- Added backend provider interface, router, config loader, token/cost estimation, and adapters for `mock`, `deepseek`, plus `openai`/`local` placeholders.
- Added `GET /providers/status` and `POST /chat/complete`; mock mode works without API keys via `CYBER_COMPANION_PROVIDER_MODE=mock`.
- DeepSeek adapter uses env-only `DEEPSEEK_API_KEY`, returns structured usage/cost metadata, and emits clear 503/502 errors when misconfigured.
- Wired frontend chat to `/chat/complete` through `frontend/src/api/chat.ts`; avatar now stays in `thinking` while the backend request runs.
- Added provider tests in `backend/tests/test_providers.py`; updated `config/providers.example.json`, `.env.example`, and `scripts/dev_backend.sh` to load `.env`.

下次接着做：

- Start Phase 4 SQLite memory schema/init and message persistence.
- Later replace frontend timing-only avatar decisions with behavior engine output in Phase 6/8.

已知问题：

- OpenAI and local provider adapters are placeholders only.
- Default config still prefers DeepSeek, so real calls require `DEEPSEEK_API_KEY` and `CYBER_COMPANION_PROVIDER_MODE` unset; local dev should keep mock mode unless testing live keys.
- No memory retrieval, behavior engine, or dialogue controller yet; chat sends only the latest user turn.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/providers/`
- `backend/tests/test_providers.py`
- `backend/requirements.txt`
- `config/providers.example.json`
- `.env.example`
- `scripts/dev_backend.sh`
- `frontend/src/App.tsx`
- `frontend/src/api/chat.ts`
- `frontend/src/avatar/useAvatarState.ts`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 6 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not add memory retrieval or behavior engine logic in the provider-only phase.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 5

本次完成：

- Implemented **Phase 4 - SQLite Memory** with schema/init/CRUD aligned to `docs/MEMORY_DESIGN.md`.
- Added `backend/app/memory/` with tables for messages, conversation_summaries, memories, mood_state, reminders, and file_access_log.
- Added `MemoryStore` CRUD helpers plus `/memory/messages`, `/memory/memories`, and `/memory/mood` API routes.
- Wired `/chat/complete` to persist user/assistant turns into SQLite with provider usage/cost metadata on assistant messages.
- Added isolated memory tests in `backend/tests/test_memory.py`; database path uses `CYBER_COMPANION_DATA_DIR` and stays out of git.
- Evaluated SQLAlchemy and kept stdlib `sqlite3` to avoid extra dependency weight.

下次接着做：

- Start Phase 5 memory retrieval and summary assembly so provider calls stop relying on single-turn input only.
- Later add behavior engine and dialogue controller before full text MVP integration.

已知问题：

- Retrieval policy and summary policy are not implemented yet; memories are stored but not injected into provider context.
- Frontend still keeps chat history only in React state; it does not reload from `/memory/messages` yet.
- Conversation summary creation helpers exist in the store but no summary update job/policy yet.

相关文件：

- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/memory/`
- `backend/tests/test_memory.py`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 13 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not send retrieved memory to providers yet beyond stored CRUD/message persistence.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 6

本次完成：

- Implemented **Phase 5 - Memory Retrieval And Summaries**.
- Added compact context assembly in `backend/app/memory/context_builder.py` with persona, mood, relevant memories, recent summary, and only the last few raw turns.
- Added deterministic retrieval scoring in `backend/app/memory/retrieval.py` by memory type, tags, importance, confidence, and query keywords.
- Added rule-based summary batching in `backend/app/memory/summary_policy.py` and budget knobs in `config/budget.example.json`.
- Wired `/chat/complete` to build provider context from SQLite instead of trusting full client history; added `GET /memory/context/preview` for debugging.
- Added deterministic tests in `backend/tests/test_context_builder.py`, including proof that full transcript is not sent by default.

下次接着做：

- Start Phase 6 behavior engine: reply/silent/refuse/interrupt/proactive decisions and local mood transitions.
- Later integrate behavior output into context assembly and avatar state instead of frontend-only timing.

已知问题：

- Conversation summaries are rule-based recaps, not LLM-generated summaries yet.
- Retrieval is keyword/type based; no embeddings or vector DB yet.
- Frontend still does not reload stored chat history from `/memory/messages`.

相关文件：

- `backend/app/main.py`
- `backend/app/memory/budget.py`
- `backend/app/memory/context_builder.py`
- `backend/app/memory/retrieval.py`
- `backend/app/memory/summary_policy.py`
- `backend/app/memory/persona.py`
- `backend/app/memory/store.py`
- `backend/tests/test_context_builder.py`
- `config/budget.example.json`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 19 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not add cloud vector DBs or embedding retrieval in this simple-retrieval pass.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 7

本次完成：

- Implemented **Phase 6 - Behavior Engine** with a local decision contract and mood transitions.
- Added `backend/app/behavior/` for rules, mood deltas, local responses, structured parser placeholder, and provider/local completion routing.
- Wired `/chat/complete` to evaluate behavior before provider calls; `silent` / `mutter` / `refuse` / `proactive` now return local lines without LLM usage.
- Added comfort/tease tone hints into compact context assembly for `reply` / `interrupt` turns.
- Added `POST /behavior/evaluate` and extended chat responses with `avatar_state`, `decision`, and `should_call_llm`.
- Updated frontend chat flow to honor backend `avatar_state` during reply animation.
- Added behavior tests covering empty input, rambling interrupt, refusal, stale job proactive nudges, comfort tone, and JSON parser fallback.

下次接着做：

- Start Phase 7 file permission gateway or Phase 8 text MVP integration wiring, depending on priority.
- Replace frontend-only empty-submit handling with backend behavior evaluation for consistency.

已知问题：

- Behavior rules are heuristic and still need Codex/product review before broad tuning.
- `observe` / `mutter` tick events and idle/proactive timers are not scheduled yet.
- Structured LLM parser accepts JSON payloads but providers are not yet prompted to emit them by default.

相关文件：

- `backend/app/behavior/`
- `backend/app/main.py`
- `backend/app/memory/context_builder.py`
- `backend/app/schemas.py`
- `backend/tests/test_behavior.py`
- `frontend/src/api/chat.ts`
- `frontend/src/App.tsx`
- `frontend/src/avatar/useAvatarState.ts`
- `docs/TODO.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 26 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not make the character abusive or manipulative; keep sharp-but-not-cruel boundaries.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 8

本次完成：

- Read `AGENTS.md`, `.cursor/rules/cyber-companion.mdc`, `docs/CURSOR_PHASE_PLAYBOOK.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`, and `docs/OPEN_SOURCE_REUSE.md` before editing; inspected git status and kept existing uncommitted work intact.
- Implemented **Phase 7 - File Permission Gateway** with config loading from `config/permissions.json` / `permissions.example.json`.
- Added `backend/app/files/` gateway module: absolute-path resolution, `..` traversal rejection, symlink escape detection, read/write folder permissions, and SQLite audit logging via existing `file_access_log`.
- Added API routes `GET /files/permissions/status`, `POST /files/check`, and `GET /files/access-log`.
- Added `list_file_access_logs()` to the memory store and deterministic tests in `backend/tests/test_file_gateway.py` for allowed paths, traversal, symlink escape, operation permissions, and route wiring.

下次接着做：

- Start Phase 8 text MVP integration: reload chat history from `/memory/messages`, surface cost/usage metadata in UI, and replace remaining frontend-only avatar timing gaps with backend behavior where appropriate.
- Later wire actual file read/write operations through the gateway once a file tool feature is assigned.

已知问题：

- Gateway currently validates/checks paths only; no file read/write executor is wired to chat or providers yet.
- Default example allowlist points at `./sandbox`; users must create `config/permissions.json` and a real sandbox folder before enabling file features.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `backend/app/files/`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/memory/store.py`
- `backend/tests/test_file_gateway.py`
- `config/permissions.example.json`
- `docs/TODO.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 38 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not send local files to providers without explicit user approval and gateway checks.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 9

本次完成：

- Continued from Session 8 and implemented **Phase 8 - Text MVP Integration** while respecting existing uncommitted work.
- Added `frontend/src/api/messages.ts` and `frontend/src/chat/types.ts` to reload stored chat history from `/memory/messages` on startup.
- Removed hardcoded welcome bubble; empty history now shows a lightweight empty-state prompt instead of fake shell text.
- Surfaced last-turn provider/model/token/cost/decision metadata in the chat panel and per-assistant-message meta lines.
- Routed empty submit through `/chat/complete` so backend behavior drives `silent`/local replies and avatar timing; kept frontend-only annoyed fallback only when API is offline.
- Improved avatar timing with state-aware durations for `silent`, `annoyed`, `angry`, and `worried`.
- Persisted `decision` and `avatar_state` into assistant message metadata during chat persistence for reloadable turn context.

下次接着做：

- Start Phase 9 push-to-talk STT only after manual verification of the text MVP feels stable.
- Optionally add proactive/idle behavior ticks and richer frontend reload of mood/provider status.
- Later wire actual file read/write operations through the Phase 7 gateway once a file tool feature is assigned.

已知问题：

- Empty submits still persist blank user rows in SQLite even though the UI hides them on reload.
- `lastTurn` cost strip resets on page refresh until the next chat turn completes.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `frontend/src/App.tsx`
- `frontend/src/api/messages.ts`
- `frontend/src/chat/types.ts`
- `frontend/src/avatar/timing.ts`
- `frontend/src/avatar/useAvatarState.ts`
- `frontend/src/styles.css`
- `backend/app/main.py`
- `backend/app/memory/chat_persistence.py`
- `docs/TODO.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 38 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not implement STT/TTS before the text MVP architecture is working.
- Do not send local files to providers without explicit user approval and gateway checks.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 10

本次完成：

- Ran text MVP manual verification before voice work: API checklist passed 16/16 (`health`, chat/behavior/memory/context/files); automated checks passed; browser smoke script added at `scripts/ui_verify.mjs`.
- Implemented **Phase 9 - Push-To-Talk STT** with backend adapter interface, mock provider, OpenAI Whisper placeholder, and budget/config gates for cloud STT.
- Added `config/stt.example.json`, `GET /stt/status`, and `POST /stt/transcribe` (multipart audio upload).
- Added frontend hold-to-talk button, recording/transcribing indicators, `MediaRecorder` capture, and normal chat-path submission after mock/cloud transcription.
- Extended budget loader with `allow_cloud_stt`; added STT tests in `backend/tests/test_stt.py`.

下次接着做：

- Manually verify push-to-talk in a real browser with microphone permission (mock STT is enough for first pass).
- Start Phase 10 selective TTS output, or polish text MVP issues (blank user rows on empty submit, persist last-turn cost across refresh).
- Wire cloud Whisper adapter only if `allow_cloud_stt=true` and keys are configured.

已知问题：

- Cloud Whisper adapter is still a placeholder; only mock STT is usable end-to-end without further wiring.
- Browser UI verification had timing/environment sensitivity in the sandbox; rely on `scripts/ui_verify.mjs` plus local browser checks for final sign-off.
- Empty submits still persist blank user rows in SQLite even though the UI hides them on reload.

相关文件：

- `backend/app/stt/`
- `backend/app/main.py`
- `backend/app/memory/budget.py`
- `backend/app/schemas.py`
- `backend/tests/test_stt.py`
- `config/stt.example.json`
- `frontend/src/api/stt.ts`
- `frontend/src/voice/usePushToTalk.ts`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `scripts/ui_verify.mjs`
- `.env.example`
- `docs/TODO.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- Text MVP API manual verification: 16 passed, 0 failed.
- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 43 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not stream continuous microphone audio to cloud; push-to-talk only.
- Do not add TTS in the same pass unless explicitly assigned.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 11

本次完成：

- Continued from Session 10 and implemented **Phase 10 - TTS Output** with backend adapter interface, mock provider, OpenAI TTS placeholder, and budget/config gates for cloud TTS.
- Added selective speech policy: short `reply` lines plus `proactive` / `interrupt` / `refuse`; skips `silent` / `mutter` / `observe`, long text, and muted avatar states.
- Added `config/tts.example.json`, `GET /tts/status`, `POST /tts/evaluate`, and `POST /tts/synthesize` (returns base64 WAV for mock playback).
- Added frontend `useTextToSpeech` hook with mute toggle (localStorage), audio playback, and avatar `talking` sync during speech.
- Added TTS tests in `backend/tests/test_tts.py`.

下次接着做：

- Manually verify TTS mute toggle and mock playback in a real browser.
- Polish text MVP issues (blank user rows on empty submit, persist last-turn cost across refresh).
- Wire cloud OpenAI TTS adapter only if `allow_cloud_tts=true` and keys are configured.
- Consider Phase 11 hardware preparation docs when explicitly assigned.

已知问题：

- Cloud OpenAI TTS adapter is still a placeholder; mock TTS returns silent WAV timed to text length, not real speech.
- Empty submits still persist blank user rows in SQLite even though the UI hides them on reload.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `backend/app/tts/`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/tests/test_tts.py`
- `config/tts.example.json`
- `frontend/src/api/tts.ts`
- `frontend/src/voice/useTextToSpeech.ts`
- `frontend/src/App.tsx`
- `frontend/src/avatar/useAvatarState.ts`
- `frontend/src/styles.css`
- `.env.example`
- `docs/TODO.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 52 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite production build completed.

不要改动的边界：

- Do not start hardware integration before the software MVP is stable.
- Do not speak every long message by default; keep selective TTS policy.
- Do not stream continuous microphone audio to cloud; push-to-talk only for STT.
- Do not make Boxi a generic polite assistant; keep the default "毒舌被困小人 + low-dose companionship" direction.

## 2026-06-08 - Session 12

本次完成：

- Ran **Phase 10 TTS / Voice manual verification** per `docs/MANUAL_VERIFICATION.md` Voice + TTS sections; extended `scripts/ui_verify.mjs` to cover API policy checks, mute/localStorage persistence, mock TTS playback + avatar `talking` sync, long-reply skip, and mock STT chat-path flow.
- Browser smoke via Playwright on `http://127.0.0.1:5173/` + API on `18000`: **34/34 passed**.
- Fixed blocking voice issues in allowed frontend files:
  - `useTextToSpeech`: audio unlock on first user gesture; handle `audio.play()` failures without leaving avatar stuck in `speaking`.
  - `usePushToTalk`: mouse-event fallback for hold-to-talk when pointer-only automation/browsers differ; guard missing `MediaRecorder.isTypeSupported`.
- Added root devDependency `playwright` so `scripts/ui_verify.mjs` can run reproducibly.

下次接着做：

- Polish text MVP issues (blank user rows on empty submit, persist last-turn cost across refresh).
- Wire cloud OpenAI TTS/STT only if budget flags and keys are configured.
- Consider expanding backend CORS allowlist if frontend dev is routinely run on non-5173 ports.

已知问题：

- Backend CORS currently allows only `5173`; running Vite on another port (e.g. `5174`) makes API/STT/TTS UI appear offline until port matches or CORS is updated.
- Mock TTS still returns silent WAV timed to text length, not real speech.
- Empty submits still persist blank user rows in SQLite even though the UI hides them on reload.
- Existing Vite/esbuild dev-server audit and FastAPI TestClient deprecation warnings are unchanged.

相关文件：

- `frontend/src/voice/useTextToSpeech.ts`
- `frontend/src/voice/usePushToTalk.ts`
- `frontend/src/App.tsx`
- `scripts/ui_verify.mjs`
- `package.json`
- `package-lock.json`
- `docs/SESSION_LOG.md`

测试结果：

- `node scripts/ui_verify.mjs`: 34 passed, 0 failed (Voice + TTS browser smoke on port 5173).
- API checks: STT/TTS enabled, cloud STT/TTS blocked, selective policy for long/silent/short text, mock synthesize returns audio.
- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 52 backend tests passed; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 13

本次完成：

- **Text MVP polish** (no new phase): fixed empty submit persisting blank user rows in SQLite by skipping whitespace-only user messages in `persist_chat_turn`.
- Restored **last-turn token/cost metadata** after page refresh: bootstrap now scans reloaded assistant messages and rebuilds `lastTurn`; assistant metadata now also stores `should_call_llm` for accurate local/LLM labeling.
- Added backend test `test_chat_complete_empty_submit_skips_blank_user_row`.
- Evaluated maintenance advisories without dependency churn:
  - **Vite/esbuild (GHSA-67mh-4wv8-2f99)**: dev-server-only; fix requires Vite 8.x breaking upgrade. Acceptable while dev server stays on `127.0.0.1:5173` only.
  - **TestClient/httpx2**: Starlette deprecation warning from `fastapi.testclient`; harmless for now; migrate to `httpx2` when Starlette drops legacy path.

下次接着做：

- Wire cloud OpenAI TTS/STT only if budget flags and keys are configured.
- Consider expanding backend CORS allowlist if frontend dev is routinely run on non-5173 ports.
- Upgrade Vite to 6+/8+ in a dedicated maintenance pass if dev server exposure changes.

已知问题：

- Backend CORS currently allows only `5173`; running Vite on another port (e.g. `5174`) makes API/STT/TTS UI appear offline until port matches or CORS is updated.
- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.
- FastAPI TestClient `httpx` → `httpx2` deprecation warning remains; no functional impact today.

相关文件：

- `backend/app/memory/chat_persistence.py`
- `backend/app/main.py`
- `backend/tests/test_memory.py`
- `frontend/src/chat/types.ts`
- `frontend/src/App.tsx`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 53 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite 5.4.21 production build completed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.
- Did not bump Vite/esbuild or add `httpx2` in this pass.

## 2026-06-08 - Session 14

本次完成：

- Fixed Codex acceptance **TTS mute interrupt**: `stopSpeaking(true)` now fires `onSpeakingEnd` only when playback was active; pre-play cleanup and unmount still use the silent path to avoid duplicate callbacks.
- Fixed **context_builder NameError**: imported `BudgetConfig` in `backend/app/memory/context_builder.py`; added `test_context_builder_uses_default_budget_when_omitted`.
- Recorded **Playwright** in `docs/OPEN_SOURCE_REUSE.md` as accepted devDependency for `scripts/ui_verify.mjs`.

下次接着做：

- Wire cloud OpenAI TTS/STT only if budget flags and keys are configured.
- Consider expanding backend CORS allowlist if frontend dev is routinely run on non-5173 ports.
- Upgrade Vite to 6+/8+ in a dedicated maintenance pass if dev server exposure changes.

已知问题：

- Backend CORS currently allows only `5173`; running Vite on another port (e.g. `5174`) makes API/STT/TTS UI appear offline until port matches or CORS is updated.
- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.
- FastAPI TestClient `httpx` → `httpx2` deprecation warning remains; no functional impact today.

相关文件：

- `frontend/src/voice/useTextToSpeech.ts`
- `backend/app/memory/context_builder.py`
- `backend/tests/test_context_builder.py`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 54 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite 5.4.21 production build completed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 15

本次完成：

- Prepared cross-tool handoff for Claude Code + Cursor in `docs/HANDOFF.md`.
- Updated `CLAUDE.md`, `.cursor/rules/cyber-companion.mdc`, and `docs/CURSOR_PHASE_PLAYBOOK.md` so future Claude/Cursor sessions read the handoff note.
- Updated `docs/TODO.md` current priority to favor checkpoint commit and Claude read-only review before new feature work.
- Preserved current ownership model: Cursor handles most routine implementation; Claude Code stays review/architecture/security focused.

下次接着做：

- Create a checkpoint commit for the current Phase 2-10 MVP batch after user approval.
- Ask Claude Code for a read-only architecture/security/memory/behavior review using the prompt in `docs/HANDOFF.md`.
- Let Cursor continue only with one small slice at a time after the checkpoint or explicit user approval.

已知问题：

- Working tree still contains a large uncommitted MVP batch on top of baseline commit `d7d225f`.
- Backend CORS currently allows only `5173`; running Vite on another port can make API/STT/TTS UI appear offline until port matches or CORS is updated.
- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.
- FastAPI TestClient `httpx` -> `httpx2` deprecation warning remains; no functional impact today.
- Full Playwright browser smoke needs browser binaries installed locally; do not download/install without user approval.

相关文件：

- `docs/HANDOFF.md`
- `CLAUDE.md`
- `.cursor/rules/cyber-companion.mdc`
- `docs/CURSOR_PHASE_PLAYBOOK.md`
- `docs/TODO.md`
- `docs/SESSION_LOG.md`

测试结果：

- Not run in this handoff-only pass. Previous acceptance immediately before handoff: `PYTHON_BIN=.venv/bin/python npm run check` passed with 54 backend tests and frontend typecheck; `npm run build:frontend` passed.

不要改动的边界：

- Do not start Phase 11 hardware work without explicit user approval.
- Do not wire cloud STT/TTS unless budget flags and keys are configured and the user asks.
- Do not change provider abstraction, memory schema, behavior contract, or file permission policy without doc updates and review.
- Do not let Claude Code and Cursor edit the same module at the same time.

## 2026-06-08 - Session 16

本次完成：

- Fixed **avatar / TTS state race** (frontend-only slice after checkpoint `dad8cbd`):
  - `runChatFetchSequence` now accepts `{ deferIdleFallback }` from `onReplyReady`; when TTS owns the turn, skip idle fallback timers.
  - `App.tsx` awaits TTS handoff via `speakReplyRef`, uses `chatEpochRef` / `ttsEpochRef` so stale `onSpeakingEnd` does not overwrite a newer round's `thinking`.
  - Added `scheduleReturnToIdle` for non-TTS or skipped-TTS fallback; removed unused `runChatReplySequence`.
- Extended `scripts/ui_verify.mjs` with delayed-synthesis and overlapping-round checks for the race regressions.

下次接着做：

- Run full `node scripts/ui_verify.mjs` with Playwright browsers if user approves install.
- Continue small slices from `docs/HANDOFF.md` (CORS, cloud STT/TTS wiring, maintenance passes).

已知问题：

- Backend CORS currently allows only `5173`; running Vite on another port can make API/STT/TTS UI appear offline until port matches or CORS is updated.
- Mock TTS still returns silent WAV timed to text length, not real speech.
- If a new chat round completes while prior TTS is still playing, the new reply may skip TTS (`speaking` guard) and stay on `thinking` until the next interaction.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.
- FastAPI TestClient `httpx` -> `httpx2` deprecation warning remains; no functional impact today.

相关文件：

- `frontend/src/avatar/useAvatarState.ts`
- `frontend/src/App.tsx`
- `scripts/ui_verify.mjs`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; 54 backend tests passed; frontend `tsc --noEmit` passed; 1 TestClient deprecation warning unchanged.
- `npm run build:frontend`: passed; Vite 5.4.21 production build completed.
- `node scripts/ui_verify.mjs`: not run here (needs local dev servers + Playwright browsers).

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 17

本次完成：

- Tightened overlap regression in `scripts/ui_verify.mjs`: after round-two submit, wait up to 12s for avatar `idle` instead of accepting `thinking`/`talking` at 2.5s (guards against stuck-thinking regression after Claude's App.tsx overlap fix).
- Removed redundant post-overlap idle wait/check that duplicated the new assertion.

下次接着做：

- Investigate intermittent `refuse short reply triggers tts speaking label` flake in `ui_verify.mjs` if it recurs.
- Continue small slices from `docs/HANDOFF.md`.

已知问题：

- `refuse short reply triggers tts speaking label` failed once in the 36-check run (talking-state check passed; Speaking label timing may be flaky).
- Backend CORS currently allows only `5173`; running Vite on another port can make API/STT/TTS UI appear offline until port matches or CORS is updated.

相关文件：

- `scripts/ui_verify.mjs`
- `docs/SESSION_LOG.md`

测试结果：

- `node scripts/ui_verify.mjs` (API `18000`, frontend `5173`): **35 passed, 1 failed**.
- Overlap regression: **PASS** — `avatar not pulled idle by stale tts while newer round active | idle`.
- Failed: `refuse short reply triggers tts speaking label` (unrelated to overlap change).

不要改动的边界：

- Only edited `scripts/ui_verify.mjs` and `docs/SESSION_LOG.md`; no commit.

## 2026-06-08 - Session 18

本次完成：

- Stabilized `scripts/ui_verify.mjs` refuse/TTS checks (Session 17 follow-up):
  - Replaced flaky **Speaking** label wait with `/tts/synthesize` request + `spoken === true` response assertion.
  - Added 50ms polling for transient `talking`/`angry` avatar during refuse handoff (headless playback can flash too fast for single `waitForFunction`).
  - Inserted **idle settle** waits between chat steps (browser verification → long reply → refuse → overlap) to reduce cross-test TTS interference.
  - Improved browser verification message wait to require both user + boxi bubbles before assertions.

下次接着做：

- Pick next slice from `docs/HANDOFF.md` (CORS expansion, manual verification note, maintenance passes).
- Consider committing ui_verify hardening if user wants a checkpoint.

已知问题：

- Refuse path may show `angry` (not `talking`) when TTS handoff uses backend refuse avatar before/alongside speech; test accepts both.
- Backend CORS currently allows only `5173`.

相关文件：

- `scripts/ui_verify.mjs`
- `docs/SESSION_LOG.md`

测试结果：

- `node scripts/ui_verify.mjs` (API `18000`, frontend `5173`): **36 passed, 0 failed**.

不要改动的边界：

- Only edited `scripts/ui_verify.mjs` and `docs/SESSION_LOG.md`; no commit.

## 2026-06-08 - Session 19

本次完成：

- **CORS expansion** (HANDOFF next slice): added `backend/app/cors.py` with explicit default dev origins for `5173` and `5174` on `127.0.0.1` / `localhost`; optional `CYBER_COMPANION_CORS_ORIGINS` comma list merges in extra origins and rejects wildcards.
- Wired `load_cors_origins()` into `backend/app/main.py`; documented env in `.env.example`.
- Added `backend/tests/test_cors.py` (6 tests) for config merge, wildcard rejection, and allow/deny behavior.
- Updated `docs/MANUAL_VERIFICATION.md` with CORS port guidance and latest `ui_verify` **36/36** smoke state.

下次接着做：

- Commit pending ui_verify hardening (Sessions 17–18) plus this CORS slice if user wants.
- Continue HANDOFF slices: Vite/esbuild or TestClient/httpx2 maintenance pass, behavior idle/proactive scheduling.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.
- FastAPI TestClient `httpx` -> `httpx2` deprecation warning remains.

相关文件：

- `backend/app/cors.py`
- `backend/app/main.py`
- `backend/tests/test_cors.py`
- `.env.example`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **60** backend tests passed; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 20

本次完成：

- **TestClient/httpx2 maintenance pass** (HANDOFF next slice): added `httpx2>=2.0.0` to `backend/requirements-dev.txt` so Starlette 1.2+ TestClient uses httpx2 instead of deprecated httpx path; production DeepSeek adapter still uses `httpx`.
- Recorded httpx2 in `docs/OPEN_SOURCE_REUSE.md`; marked TODO maintenance item done.
- Pytest warning `StarletteDeprecationWarning: ... install httpx2 instead` is gone (**60 passed, 0 warnings**).

下次接着做：

- Commit pending slices (ui_verify hardening, CORS, httpx2) if user wants a checkpoint.
- Continue HANDOFF: behavior idle/proactive tick scheduling, or Vite/esbuild pass if dev exposure changes.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.

相关文件：

- `backend/requirements-dev.txt`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/TODO.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **60** backend tests passed, **0** pytest warnings; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.
- Did not bump Vite/esbuild production dependencies.

## 2026-06-08 - Session 21

本次完成：

- **Behavior idle/proactive tick scheduling** (HANDOFF next slice):
  - Backend: `idle_tick` handler with mood drift (`apply_idle_tick_mood_delta`), boredom/loneliness `mutter` threshold, `observe`/`sleepy` idle states, and 180s local-line cooldown via `tick_policy.py`.
  - Extended `POST /behavior/evaluate` schema with `idle_tick`; proactive_check now respects the same cooldown.
  - Frontend: `useBehaviorTicks` polls `idle_tick` every 90s and `proactive_check` every 5m (only when tab visible, API ok, not sending/TTS, user quiet ≥2m); tick lines render as local Boxi bubbles with avatar/TTS handoff.
  - Added behavior tests (65 total backend tests).

下次接着做：

- Commit pending slices (ui_verify, CORS, httpx2, behavior ticks) if user wants.
- Vite/esbuild maintenance pass only if dev exposure changes; cloud STT/TTS when explicitly requested.

已知问题：

- Tick-initiated mutter/proactive lines are UI-only (not persisted via `/chat/complete`).
- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.

相关文件：

- `backend/app/behavior/engine.py`
- `backend/app/behavior/mood.py`
- `backend/app/behavior/tick_policy.py`
- `backend/app/schemas.py`
- `backend/tests/test_behavior.py`
- `frontend/src/api/behavior.ts`
- `frontend/src/avatar/useBehaviorTicks.ts`
- `frontend/src/App.tsx`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **65** backend tests passed, 0 warnings; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior decision contract, or file permission policy.

## 2026-06-08 - Session 22

本次完成：

- **Persist tick-initiated local behavior lines** (Session 21 follow-up):
  - Backend: `persist_local_behavior_line` saves `mutter` / `proactive` lines from `idle_tick` and `proactive_check` into SQLite with `source=behavior_tick` and behavior metadata.
  - `/behavior/evaluate` returns `saved_message_id` when a local line is persisted.
  - Frontend uses `saved_message_id` for tick bubbles so reload from `/memory/messages` stays consistent.
  - Added 3 integration tests (**68** backend tests total).

下次接着做：

- Commit pending slices (ui_verify, CORS, httpx2, behavior ticks, tick persistence) if user wants.
- Vite/esbuild maintenance pass only if dev exposure changes; cloud STT/TTS when explicitly requested.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.
- Vite 5.x / esbuild dev-server audit remains open; mitigated by localhost-only dev binding.

相关文件：

- `backend/app/memory/chat_persistence.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/tests/test_memory.py`
- `frontend/src/api/behavior.ts`
- `frontend/src/App.tsx`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **68** backend tests passed, 0 warnings; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior decision contract, or file permission policy.

## 2026-06-08 - Session 23

本次完成：

- **Vite/esbuild dev-server audit maintenance pass** (open Security TODO):
  - Upgraded `vite` 5.4.x → **6.4.3** (clears GHSA-4w7w-66w2-5vf9 path traversal and GHSA-67mh-4wv8-2f99 esbuild dev-server advisories).
  - Upgraded root `playwright` **1.49.x → 1.60.x** (clears GHSA-7mvr-c777-76hp).
  - Hardened `frontend/vite.config.ts`: explicit localhost for dev + preview; documented rule in `docs/SECURITY_AND_PERMISSIONS.md`.
  - Updated `docs/OPEN_SOURCE_REUSE.md`, `docs/MANUAL_VERIFICATION.md`, `docs/HANDOFF.md`; marked Security TODO done.
  - `npm audit` and `npm audit --omit=dev`: **0 vulnerabilities**.

下次接着做：

- Commit pending slices (ui_verify, CORS, httpx2, behavior ticks, tick persistence, Vite upgrade) if user wants.
- Claude Code read-only review of Phase 2–10 MVP batch.
- Cloud STT/TTS when explicitly requested.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.

相关文件：

- `frontend/package.json`
- `frontend/vite.config.ts`
- `package.json`
- `package-lock.json`
- `docs/SECURITY_AND_PERMISSIONS.md`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/TODO.md`
- `docs/HANDOFF.md`
- `docs/MANUAL_VERIFICATION.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **68** backend tests passed, 0 warnings; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed (Vite 6.4.3 production build).
- `npm audit` / `npm audit --omit=dev`: 0 vulnerabilities.

不要改动的边界：

- Did not start Phase 11 hardware work.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior decision contract, or file permission policy.
- Did not expose dev servers beyond localhost.

## 2026-06-08 - Session 24

本次完成：

- **ui_verify refuse/TTS timing hardening** (known flake from bundled commit):
  - After delayed-TTS race check, wait for avatar `idle` before the next chat turn.
  - Refuse smoke: use `waitForResponse` (not parallel request/poll race); wait for refuse bubble before asserting synthesize payload; then wait for `talking`/`angry` avatar.
- Updated `docs/HANDOFF.md` for per-slice checkpoint policy and current baseline `5005731`.
- Marked checkpoint TODO done in `docs/TODO.md`.

下次接着做：

- Run full `node scripts/ui_verify.mjs` after `npx playwright install` (needs user approval for browser download).
- Claude Code read-only MVP batch review.
- Cloud STT/TTS when explicitly requested.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.
- Full browser ui_verify not re-run this session (Playwright 1.60 browsers not installed locally).

相关文件：

- `scripts/ui_verify.mjs`
- `docs/HANDOFF.md`
- `docs/TODO.md`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **70** backend tests passed, 0 warnings; frontend `tsc --noEmit` passed.

不要改动的边界：

- Did not install Playwright browser binaries.
- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 25

本次完成：

- **Playwright browser smoke verification**:
  - Installed Playwright Chromium 1.60 (`npx playwright install chromium`).
  - Ran full `node scripts/ui_verify.mjs` against API `18000` + frontend `5173`: **37/37 passed**.
  - Fixed flaky `history reload after refresh`: compare against persisted tail + last-turn survival (not raw DOM count vs 50-message API limit).
  - Updated `docs/MANUAL_VERIFICATION.md` and `docs/HANDOFF.md` with install/run steps and latest smoke state.

下次接着做：

- Claude Code read-only MVP batch review.
- Cloud STT/TTS when explicitly requested.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.
- `/memory/messages?limit=50` caps reload history; ui_verify now checks last-turn survival instead of full DOM parity.

相关文件：

- `scripts/ui_verify.mjs`
- `docs/MANUAL_VERIFICATION.md`
- `docs/HANDOFF.md`
- `docs/SESSION_LOG.md`

测试结果：

- `CYBER_VERIFY_API_URL=http://127.0.0.1:18000 node scripts/ui_verify.mjs`: **37 passed, 0 failed**.

不要改动的边界：

- Did not wire cloud STT/TTS adapters.
- Did not change provider abstraction, memory schema, behavior contract, or file permission policy.

## 2026-06-08 - Session 26

本次完成：

- **ui_verify refuse Speaking label flake fix** (scope: `scripts/ui_verify.mjs` only):
  - Added in-page `__uiVerify` probe with `MutationObserver` to catch transient `Speaking` on `.tts-toggle` without missing short audio windows.
  - Restored check **`refuse short reply triggers tts speaking label`**: requires synthesize `spoken === true`, then accepts either observed Speaking label **or** avatar `talking`/`angry` handoff (tolerates headless short-audio flash).
  - Removed redundant separate `avatar enters talking during tts` check (folded into speaking-label assertion).

下次接着做：

- Claude Code read-only MVP batch review.
- Cloud STT/TTS when explicitly requested.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.

相关文件：

- `scripts/ui_verify.mjs`
- `docs/SESSION_LOG.md`

测试结果：

- `CYBER_VERIFY_API_URL=http://127.0.0.1:18000 node scripts/ui_verify.mjs`: **37 passed, 0 failed**.

不要改动的边界：

- Only edited `scripts/ui_verify.mjs` and `docs/SESSION_LOG.md`.
- Did not touch backend/provider/memory/behavior/cost.

## 2026-06-08 - Session 27

本次完成：

- **Low-mood avatar visual polish** (frontend-only, no state-machine changes):
  - `idle` / `sleepy` / `annoyed`: one-shot enter keyframes (`pixel-enter-idle|sleepy|annoyed`) chained before loop animations for smoother cross-state handoff.
  - Facial micro-expressions: idle periodic blink; sleepy droopy head + yawn mouth + dim stage; annoyed asymmetric squint, flat mouth, head tilt, counter-weight left arm.
  - Stepped CSS transitions on eyes/mouth/head/body/stage filter so mood shifts read as pixel transitions, not hard swaps.

下次接着做：

- More trapped-in-box idle variety or other high-energy state polish (happy/angry/talking).
- Pick next item from Claude review findings in `docs/TODO.md` (with owner tags).

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.

相关文件：

- `frontend/src/avatar/stateAnimations.css`
- `frontend/src/components/PixelCharacter.css`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **79** backend tests passed; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Only edited frontend CSS + `docs/SESSION_LOG.md`.
- Did not change avatar state machine contract, backend, provider, memory, behavior, or cost.

## 2026-06-08 - Session 28

本次完成：

- **A1 — SQL boundary queries for recent chat / summary batches**
  - `store.py`: `count_chat_messages`, `list_recent_chat_messages`, `list_chat_messages_between`, `get_recent_chat_window_lower_bound_id`.
  - `context_builder` / `summary_policy` no longer call `list_messages(limit=10_000)` + Python `source` filter.
  - `docs/ARCHITECTURE.md` Memory Engine note updated.
- **A2 — `behavior_tick` retention cap**
  - `behavior_tick_retention` in `budget.py` + `config/budget.example.json` (default 200).
  - `prune_behavior_tick_messages` in `store.py`; called from `evaluate_behavior_route` after persist.
  - `docs/MEMORY_DESIGN.md` behavior_tick retention note.
- **B3 — Per-turn user input hard truncate before provider**
  - `max_user_input_tokens` (default 1500); provider context only; persistence unchanged.
  - `docs/COST_AND_TOKEN_BUDGET.md` updated.
- **M1 — Exclude expired memories from context recall**
  - `is_expired` in `retrieval.py`; filtered in `context_builder` before `rank_memories`.
  - `/memory/memories` API unchanged.
  - `docs/MEMORY_DESIGN.md` Retrieval Policy note.

下次接着做：

- **M2** — auto-write memories from conversation (dedicated phase per `docs/MEMORY_DESIGN.md`).
- Other backlog from `docs/TODO.md` as user directs.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.

相关文件：

- `backend/app/memory/store.py`
- `backend/app/memory/context_builder.py`
- `backend/app/memory/summary_policy.py`
- `backend/app/memory/budget.py`
- `backend/app/memory/retrieval.py`
- `backend/app/main.py`
- `config/budget.example.json`
- `backend/tests/test_context_builder.py`
- `backend/tests/test_behavior_tick_retention.py`
- `backend/tests/test_user_input_truncation.py`
- `backend/tests/test_memory_retrieval.py`
- `docs/ARCHITECTURE.md`
- `docs/MEMORY_DESIGN.md`
- `docs/COST_AND_TOKEN_BUDGET.md`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **86** backend tests passed; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not change behavior decision contract, provider abstraction, or file permission policy.
- Did not change `/memory/memories` listing semantics (expired memories still visible there).

## 2026-06-08 - Session 29

本次完成：

- **M2 — Rule-based auto-write memories from conversation (MVP)**
  - `backend/app/memory/write_policy.py`: `extract_memory_candidates` + `maybe_write_memories_from_turn`.
  - Triggers: explicit remember, profile, project, preference, job topic + action verb.
  - Dedup via substring/token overlap update; gated by `auto_memory_write` in budget config.
  - Wired into `/chat/complete` after `persist_chat_turn` (links `source_message_id` to user row).
  - Tests: `backend/tests/test_memory_write_policy.py` (6 cases, incl. chat integration).
  - `docs/MEMORY_DESIGN.md` Auto-Write section; `config/budget.example.json` updated.

下次接着做：

- Optional M2 follow-up: LLM-assisted memory extraction (separate phase, needs cost review).
- `scripts/ui_verify.mjs` extension or other backlog per `docs/HANDOFF.md`.

已知问题：

- Rule-based writer may miss paraphrased facts; LLM extraction not implemented yet.
- Mock TTS still returns silent WAV timed to text length, not real speech.
相关文件：

- `backend/app/memory/write_policy.py`
- `backend/app/memory/budget.py`
- `backend/app/main.py`
- `config/budget.example.json`
- `backend/tests/test_memory_write_policy.py`
- `docs/MEMORY_DESIGN.md`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **92** backend tests passed; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Did not change memory schema, behavior decision contract, provider abstraction, or file permission policy.
- No extra LLM call for memory extraction in this slice.

## 2026-06-08 - Session 30

本次完成：

- **M2 trigger false-positive fixes** (`write_policy.py` only)
  - Profile: dropped loose `我是` / `i am`; kept `我叫` / `我的名字是` / `my name is` / `i'm called`.
  - Preference: imperative anchors only (`请` / `希望你` / sentence-start `别` / `i prefer`).
  - Job progress: store condensed `action: topic` facts via `_build_job_progress_fact`.
  - Confidence gate: inferred `project` at 0.55 (below `_MIN_WRITE_CONFIDENCE=0.6`) is filtered; explicit cues still pass.
  - Tests: profile negatives (`我是说你别拖了`, `我是不是该改简历`, `i am tired`), `我叫张伟` positive, preference/project gates.

下次接着做：

- M2 follow-up or `scripts/ui_verify.mjs` per `docs/HANDOFF.md`.

已知问题：

- Rule-based writer may still miss paraphrased facts; LLM extraction not implemented.

相关文件：

- `backend/app/memory/write_policy.py`
- `backend/tests/test_memory_write_policy.py`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **98** backend tests passed.

不要改动的边界：

- Only touched `write_policy.py`, its tests, and session log; no schema or other modules.

## 2026-06-08 - Session 31

本次完成：

- **Mood-driven rest expressions (frontend-only)**
  - `useMoodRest`: polls `GET /memory/mood` every 75s, skips hidden tabs; `restMood.moodToRestState` maps energy/boredom/loneliness → sleepy/annoyed/worried/idle.
  - `useAvatarState`: all idle fallbacks now call `resolveRestState()`; exposes `returnToRestState` / `applyRestStateIfResting` (rest-only live refresh, no new timers).
  - `App.tsx`: wires mood hook + TTS end uses `returnToRestState`; `__uiVerify` probes for smoke.
  - `PixelCharacter.css`: softer stepped transitions between rest visuals.
  - `scripts/ui_verify.mjs`: neutral mood reset + `low energy mood rest maps to sleepy` check.

下次接着做：

- Optional: shorten poll in dev via `VITE_MOOD_POLL_MS` for manual demos.
- Other backlog per `docs/HANDOFF.md`.

已知问题：

- Mock TTS still returns silent WAV timed to text length, not real speech.

相关文件：

- `frontend/src/api/mood.ts`
- `frontend/src/avatar/restMood.ts`
- `frontend/src/avatar/useMoodRest.ts`
- `frontend/src/avatar/useAvatarState.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/PixelCharacter.css`
- `scripts/ui_verify.mjs`
- `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed; **98** backend tests; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Frontend only; no backend/provider/memory/behavior/cost changes.
- Avatar state machine contract unchanged; rest layer only replaces idle fallback targets.

## 2026-06-08 - Session 24 (Voice V1: macOS say TTS)

本次完成：

- Added `MacSayTTSProvider` (`backend/app/tts/mac_say.py`): local offline TTS via macOS `say`, `cloud=False`, `placeholder=False`.
- `subprocess.run([...], shell=False)` with text as a single argv; WAV via `--file-format=WAVE --data-format=LEI16@22050`; temp file cleanup; clear `TTSError` when `say` is missing or fails.
- `parse_wav_duration_ms` in `wav_utils.py` for duration from WAV header.
- Registered `mac_say` in `registry.py`; `config/tts.example.json` + new `config/tts.json` (`default_provider: mac_say`, voice `Tingting`).
- Tests: mock subprocess path, interface contract, unavailable `say`, config default, `CYBER_COMPANION_TTS_MODE=mock` override.
- Recorded macOS `say` in `docs/OPEN_SOURCE_REUSE.md`.

下次接着做：

- Voice V2: local STT via `faster-whisper` per `docs/PHASE_VOICE_LOCAL.md`.
- Manual E2E: push-to-talk → chat → Boxi speaks with real audio.

已知问题：

- STT still mock; full speak-listen loop not wired to real transcription yet.
- `mac_say` only works on macOS with `say` installed; CI/non-Mac falls back to tests via mocks.

相关文件：

- `backend/app/tts/mac_say.py`
- `backend/app/tts/registry.py`
- `backend/app/tts/wav_utils.py`
- `config/tts.json`
- `config/tts.example.json`
- `backend/tests/test_tts.py`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/PHASE_VOICE_LOCAL.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed (see checkpoint run).
- `npm run build:frontend`: passed (see checkpoint run).
- Real `say` audio: manual verification on this Mac (not automated).

不要改动的边界：

- TTS provider interface unchanged; no STT/chat/memory/behavior/provider changes.
- `CYBER_COMPANION_TTS_MODE=mock` must keep forcing mock TTS.
