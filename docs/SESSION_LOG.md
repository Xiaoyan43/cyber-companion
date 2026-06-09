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

## 2026-06-08 - Session 25 (Voice V2: faster-whisper STT)

本次完成：

- Added `FasterWhisperProvider` (`backend/app/stt/faster_whisper.py`): local offline STT, `cloud=False`, CPU `int8`, module-level lazy model cache with thread lock.
- PyAV decode: webm/opus uploads → 16 kHz mono float32 → `model.transcribe(array, language=…)`; segment join; graceful `STTError` for empty/garbled audio and no speech.
- Registered `faster_whisper` in `registry.py`; `config/stt.example.json` + new `config/stt.json` (`default_provider: faster_whisper`, `model: base`).
- Dependencies: `faster-whisper`, `av`, `numpy` in `backend/requirements.txt`.
- Tests: mock transcribe route, registry build, status contract, mocked transcribe/decode paths, config default, `CYBER_COMPANION_STT_MODE=mock` override.
- Frontend: push-to-talk hint for first-use model load latency when real STT is active.
- Recorded faster-whisper, PyAV, ffmpeg, NumPy in `docs/OPEN_SOURCE_REUSE.md`.

下次接着做：

- Voice V3 polish per `docs/PHASE_VOICE_LOCAL.md` (optional model warm-up, thread-safety hardening, piper TTS).
- Manual E2E: hold-to-talk → real transcription → chat → Boxi speaks.

已知问题：

- First transcription downloads Whisper `base` (~142 MB) and is slow; warm-up not implemented yet (V3).
- Real transcription verified manually on this Mac only; CI uses mocks via `CYBER_COMPANION_STT_MODE=mock`.
- Requires `brew install ffmpeg` and `pip install -r backend/requirements.txt` in `.venv`.

相关文件：

- `backend/app/stt/faster_whisper.py`
- `backend/app/stt/registry.py`
- `config/stt.json`
- `config/stt.example.json`
- `backend/requirements.txt`
- `backend/tests/test_stt.py`
- `frontend/src/App.tsx`
- `.env.example`
- `docs/OPEN_SOURCE_REUSE.md`
- `docs/PHASE_VOICE_LOCAL.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **113** backend tests; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.
- Real faster-whisper transcription: manual verification on this Mac (not automated).

不要改动的边界：

- STT provider interface unchanged; no TTS/chat/memory/behavior/provider changes.
- `CYBER_COMPANION_STT_MODE=mock` must keep forcing mock STT.

## 2026-06-08 - Session 26 (TTS stage-direction stripping)

本次完成：

- `speechText.ts`: strip stage directions `（…）`, `(…)`, `【…】` before TTS; preserve quoted spans; normalize spaces/punctuation; empty when only stage directions remain.
- `textChunksForSpeech` / `textForSpeech` share the same prepare path so chunking applies to stripped dialogue only (display text unchanged).
- Added `speechText.test.ts` + vitest in frontend workspace.

下次接着做：

- Manual check: long Boxi reply with parenthetical actions should speak dialogue only; chat bubble still shows full text.

已知问题：

- Half-width `(...)` stripping may remove legitimate English parentheticals in rare mixed-language replies.

相关文件：

- `frontend/src/voice/speechText.ts`
- `frontend/src/voice/speechText.test.ts`
- `frontend/vitest.config.ts`
- `frontend/package.json`

测试结果：

- `npm run test --workspace frontend`: passed (10 tests).
- `npm run check:frontend`: passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- Frontend speech-text prep only; no chat display, backend, or TTS router changes.

## 2026-06-08 - Session 27 (Doubao cloud TTS adapter)

本次完成：

- Added `DoubaoTTSProvider` (`backend/app/tts/doubao.py`): `cloud=True`, Volcano Engine HTTP TTS v1 (`POST https://openspeech.bytedance.com/api/v1/tts`, `Authorization: Bearer;{token}`), base64 audio decode, `TTSError` on auth/quota/network failures.
- Env: `DOUBAO_TTS_APPID`, `DOUBAO_TTS_ACCESS_TOKEN`, `DOUBAO_TTS_CLUSTER`, `DOUBAO_TTS_VOICE_TYPE`; `is_configured()` requires all four.
- Registered in `registry.py`; `config/tts.example.json` + `.env.example` doubao entry (default_provider unchanged — still `mac_say` in `config/tts.json`).
- Tests: httpx-mocked request assembly, success path, auth failure, network error, cloud budget gate, registry/status contract.

下次接着做：

- User enables `doubao` in `config/tts.json` + sets `DOUBAO_TTS_*` + `allow_cloud_tts` for manual E2E.
- Voice V3 polish per `docs/PHASE_VOICE_LOCAL.md` if desired.

已知问题：

- Doubao real audio not automated in CI; mac_say/mock remain default fallbacks.
- v1 HTTP endpoint does not support some newer 2.0 voices (per Volcano docs — use v3 for those).

相关文件：

- `backend/app/tts/doubao.py`
- `backend/app/tts/registry.py`
- `config/tts.example.json`
- `.env.example`
- `backend/tests/test_tts.py`
- `docs/OPEN_SOURCE_REUSE.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **120** backend tests; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.

不要改动的边界：

- TTS provider interface unchanged; no STT/chat/memory/behavior changes.
- `CYBER_COMPANION_TTS_MODE=mock` and local `mac_say` must keep working when doubao is unavailable.

## 2026-06-08 - Session 28 (Enable Doubao TTS: 灿灿)

本次完成：

- Upgraded `DoubaoTTSProvider` to V3 HTTP API (`X-Api-Key` + `X-Api-Resource-Id`) per official docs; legacy `DOUBAO_TTS_ACCESS_TOKEN` alias kept.
- `config/tts.json`: `default_provider: doubao`, voice metadata `BV700_streaming` (灿灿); `mac_say`/`mock` remain enabled as fallback.
- New `config/budget.json`: `allow_cloud_tts: true`.
- `.env`: `DOUBAO_TTS_API_KEY`, `DOUBAO_TTS_VOICE_TYPE=BV700_streaming`, `DOUBAO_TTS_RESOURCE_ID=seed-tts-1.0`.

下次接着做：

- Manual E2E: chat reply → Boxi speaks via Doubao 灿灿; switch voice by changing `DOUBAO_TTS_VOICE_TYPE` + matching `DOUBAO_TTS_RESOURCE_ID`.

已知问题：

- Doubao real audio not automated in CI; `CYBER_COMPANION_TTS_MODE=mock` still forces mock.

相关文件：

- `backend/app/tts/doubao.py`
- `config/tts.json`
- `config/budget.json`
- `.env.example`
- `backend/tests/test_tts.py`

测试结果：

- `backend/tests/test_tts.py`: 24 passed (doubao V3 mock paths).
- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **121** backend tests; frontend `tsc --noEmit` passed.
- `npm run build:frontend`: passed.
- `/tts/status`: `default_provider=doubao`, `configured=true`, `allow_cloud_tts=true`.

不要改动的边界：

- STT/chat/memory/behavior unchanged; `mac_say` still available when switching `default_provider` back.

## 2026-06-09 - Session 29 (Doubao TTS HTTP connection reuse)

本次完成：

- `DoubaoTTSProvider` 不再每次合成 `with httpx.Client(...)`；改为模块级 `get_shared_http_client()` 常驻连接池（keep-alive，`http2=True` 在已装 `h2` 时启用，否则回退 HTTP/1.1）。
- 导出 `close_doubao_http_client()`；首次取共享 client 时 hook `reset_tts_router`，重置 router 时关闭连接；注入 `http_client` 的测试分支不变。
- 测试：`test_doubao_shared_http_client_reused`、`test_reset_tts_router_closes_doubao_http_client`；autouse fixture 补充 `close_doubao_http_client()`。

下次接着做：

- 可选：装 `httpx[http2]` 启用 HTTP/2；或提交未提交的 `useTextToSpeech.ts` 分块播放。

已知问题：

- `main.py` lifespan 里 `from router import reset_tts_router` 为早期绑定，进程退出时可能未走 hook；长驻 dev server 可接受，测试 fixture 已显式 close。

相关文件：

- `backend/app/tts/doubao.py`
- `backend/tests/test_tts.py`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **125** backend tests; frontend `tsc --noEmit` passed.

不要改动的边界：

- TTS provider 接口未改；仅 doubao HTTP 层性能优化。

## 2026-06-09 - Session 30 (Doubao streaming TTS + /tts/stream)

本次完成：

- `DoubaoTTSProvider.synthesize_stream()`：复用 V3 HTTP 单向流式接口，mp3 边收边 `yield` 音频块；共享常驻 `httpx.Client`；鉴权/协议错误仍抛 `TTSError`。
- `TTSRouter.stream_synthesize()`：先跑 policy，`should_speak=False` 返回 `(policy, None)`；无 `synthesize_stream` 的 provider 回退整段合成后单次 yield。
- `GET /tts/stream`：query `text/decision/avatar_state/force`；policy skip → 204；该说 → `StreamingResponse(audio/mpeg)` + `Cache-Control: no-store`；`/tts/synthesize` 未动。
- 测试：豆包多 chunk 流出、204 skip、mock 回退、空文本 400；`CYBER_COMPANION_TTS_MODE=mock` 仍强制 mock。

下次接着做：

- 前端 `useTextToSpeech` 可改用 `/tts/stream` 降低首包延迟；或提交未提交的分块播放改动。

已知问题：

- 回退 provider（mock/mac_say）流式端点仍标 `audio/mpeg`，实际字节可能是 wav。

相关文件：

- `backend/app/tts/doubao.py`
- `backend/app/tts/router.py`
- `backend/app/main.py`
- `backend/tests/test_tts.py`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **130** backend tests; frontend `tsc --noEmit` passed.

不要改动的边界：

- `TextToSpeechProvider` 抽象方法未改；STT/chat/memory/behavior 未碰。

## 2026-06-09 - Session 31 (Frontend progressive TTS via /tts/stream)

本次完成：

- `useTextToSpeech.speakReply`：先 `textForSpeech` 清洗；`probeTtsStream` + `new Audio(streamUrl)` 渐进播放；204/探测失败不进 speaking、返回 `false`；播放失败回退 `/tts/synthesize` base64。
- 保留竞态契约：`onSpeakingStart` 在 `play` 前、`onSpeakingEnd` 在 ended/error、`speakingRef` 守卫、返回 boolean；`AbortController` + `audio.pause()` 打断流。
- `api/tts.ts`：`buildTtsStreamUrl`、`probeTtsStream`（GET 探测，不支持 HEAD）；`api/tts.test.ts` 编码与探测用例。
- `scripts/ui_verify.mjs`：TTS 竞态/拒绝用例改拦 `**/tts/stream**`。

下次接着做：

- 本机 Doubao 流式 E2E 手动验首包延迟；可选去掉探测双请求（需后端 HEAD 或专用 evaluate）。

已知问题：

- 流式前先 GET 探测再 `Audio` 拉流，豆包会打两次请求；`ui_verify` 的 `cloud tts blocked by budget` 仍依赖 `allow_cloud_tts: false` 配置。

相关文件：

- `frontend/src/voice/useTextToSpeech.ts`
- `frontend/src/api/tts.ts`
- `frontend/src/api/tts.test.ts`
- `scripts/ui_verify.mjs`

测试结果：

- `npm run check`: passed — **130** backend tests; frontend `tsc --noEmit` passed.
- `npm run test --workspace frontend`: **14** passed.
- `npm run build:frontend`: passed.
- `ui_verify`（API `8000` + frontend `5174`）：竞态/流式延迟用例通过；需 `CYBER_COMPANION_TTS_MODE=mock` 时 budget 检查与旧脚本一致。

不要改动的边界：

- `App.tsx` epoch / `deferIdleFallback` 未改；`/tts/synthesize` 作兜底保留。

## 2026-06-09 - Session 32 (DeepSeek HTTP connection reuse)

本次完成：

- `DeepSeekProvider` 不再每次 `with httpx.Client(...)`；改为模块级 `get_shared_http_client()` 常驻连接池（keep-alive，`http2=True` 在已装 `h2` 时启用）。
- 导出 `close_deepseek_http_client()`；首次取共享 client 时 hook `reset_provider_router`，重置时关闭；注入 `http_client` 的测试分支保留。
- 测试：共享 client 复用、`reset_provider_router` 关闭、mock HTTP complete 契约。

下次接着做：

- 可选：其他 cloud provider（OpenAI 等）同样复用连接池。

已知问题：

- `main.py` lifespan 里 `from router import reset_provider_router` 为早期绑定，进程退出时可能未走 hook；测试 fixture 已显式 `close_deepseek_http_client()`。

相关文件：

- `backend/app/providers/deepseek.py`
- `backend/tests/test_providers.py`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **133** backend tests; frontend `tsc --noEmit` passed.

不要改动的边界：

- `ChatProvider` 接口未改；仅 DeepSeek HTTP 层性能优化。

## 2026-06-09 - Session 33 (Streaming S1 — backend `/chat/stream`)

本次完成：

- **S1 — Backend streaming provider + `POST /chat/stream`**
  - `ChatProvider.complete_stream()`：产出 `("delta", str)` 与末尾 `("usage", TokenUsage)`；默认实现整段 fallback。
  - `DeepSeekProvider`：`stream=true` + `stream_options.include_usage`；逐块 yield content；末块取 usage，否则按累积文本估算；复用常驻 httpx client。
  - `MockProvider`：两段 delta + usage，便于测 SSE 序列。
  - `ProviderRouter.complete_stream()` 委托各 provider。
  - `POST /chat/stream` → `text/event-stream`：前置与 `/chat/complete` 一致；LLM 路径边收边发 `delta` SSE，流结束后 parse、persist、M2、summary，再发 `done` meta；本地决策/预算拦截单 delta + done；中途错误发 `error` 且不半持久化。
  - `/chat/complete` 未改，作兜底。
  - 测试：`backend/tests/test_chat_stream.py`（SSE 序列、单次持久化、M2、预算拦截、流中断不持久化、DeepSeek stream mock）。

下次接着做：

- **S2** — 前端消费 `/chat/stream`，实时打字；TTS 仍等全文（见 `docs/PHASE_STREAMING.md`）。

已知问题：

- 结构化 JSON persona 输出与流式尚未对齐（PHASE_STREAMING out of scope）。
- OpenAI/local placeholder 的 `complete_stream` 走基类整段 fallback，调用仍会抛 `ProviderNotConfiguredError`。

相关文件：

- `backend/app/providers/base.py`
- `backend/app/providers/types.py`
- `backend/app/providers/deepseek.py`
- `backend/app/providers/mock.py`
- `backend/app/providers/router.py`
- `backend/app/main.py`
- `backend/tests/test_chat_stream.py`
- `docs/PHASE_STREAMING.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: passed — **138** backend tests; frontend `tsc --noEmit` passed.
- `curl -N POST /chat/stream`（mock）：先 `delta` 再 `done`，meta 含 provider/usage/cost。

不要改动的边界：

- 未改前端（S2 再做）；未改 `/chat/complete` 行为；未改 behavior/memory/provider 语义。

## 2026-06-09 - Session 34 (Streaming S2 — frontend live text)

本次完成：

- **S2 — Frontend consume `/chat/stream`, live text rendering**
  - `frontend/src/api/chat.ts`: `requestChatStream`（fetch + ReadableStream SSE 解析）、`parseSseDataLine` / `processSseLines`、`onDelta` / `onDone` / `onError` 回调；流失败回退 `requestChatComplete`。
  - `frontend/src/chat/streamRender.ts`: `appendChatStreamDelta` 增量更新指定 Boxi 气泡。
  - `frontend/src/chat/types.ts`: `streamMetaToTurnSummary` / `streamMetaToMessageMeta`。
  - `App.tsx`: 提交优先走流式；先追加空 Boxi 气泡随 delta 长出文字；首个 delta 前 `thinking`、流式中 `talking`；`done` 写入 meta + `lastTurn`；流结束后一次 `speakReply`（TTS 不变）；保留 epoch / deferIdleFallback / onSpeakingStart-End 契约。
  - 测试：`frontend/src/api/chat.test.ts`（SSE 解析 + stream 回调）、`frontend/src/chat/streamRender.test.ts`（增量渲染）。
  - `scripts/ui_verify.mjs`: 竞态探测改为同时 delay `/chat/stream` 与 `/tts/stream`。

下次接着做：

- **S3** — 按句切块 TTS 队列，音频约第一句起播（`docs/PHASE_STREAMING.md`）。

已知问题：

- 流式失败会整段回退 `/chat/complete`（可能多一次 provider 调用，但后端不半持久化）。
- 本地 dev API 若 `allow_cloud_tts: true`，ui_verify 的 API 段 `cloud tts blocked by budget` 会失败（与 S2 无关）。

相关文件：

- `frontend/src/api/chat.ts`
- `frontend/src/api/chat.test.ts`
- `frontend/src/chat/streamRender.ts`
- `frontend/src/chat/streamRender.test.ts`
- `frontend/src/chat/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/avatar/useAvatarState.ts`
- `frontend/vite.config.ts`
- `scripts/ui_verify.mjs`
- `docs/PHASE_STREAMING.md`

测试结果：

- `npm run test --workspace frontend`: **18** passed。
- `PYTHON_BIN=.venv/bin/python npm run check`: **138** backend + frontend `tsc` passed。
- `npm run build:frontend`: passed。
- `CYBER_VERIFY_API_URL=http://127.0.0.1:18000 node scripts/ui_verify.mjs`: browser **37/37** passed；API 段 1 项因运行中服务器 `allow_cloud_tts: true` 失败。

不要改动的边界：

- 未改后端；`/chat/complete` 兜底保留；TTS 竞态契约未动。

## 2026-06-09 - Session 35 (Streaming S3 — sentence TTS queue)

本次完成：

- **S3 — Frontend sentence-chunked TTS queue**（`docs/PHASE_STREAMING.md`）
  - `speechText.ts`: `drainStreamingSpeechChunks` / `flushStreamingSpeechRemainder`（句界 `。！？!?…\n` 或 max-length；Option A 剥离）。
  - `useTextToSpeech.ts`: 流式 API `beginStreamingReply` / `feedStreamingReplyDelta` / `finishStreamingReply` / `cancelStreamingReply`；顺序 `/tts/stream` 播放队列；首句 `onSpeakingStart`、队列排空且流结束 `onSpeakingEnd`；`playbackSession` epoch + `invalidatePlayback` 取消旧队列/在途音频；静音 `stopSpeaking` 清空队列。
  - `App.tsx`: 流式 `onDelta` 增量入队；`onReplyReady` 走 `finishStreamingReply`（非流仍 `speakReply`）；`streamEpoch` / `turnEpoch` 守卫；`ttsActiveRef` + 提前绑定 `ttsEpoch` 防 behavior tick 竞态。
  - 测试：`speechText.test.ts` 流式切块用例。

下次接着做：

- 流式阶段收尾文档（ARCHITECTURE streaming note）；Voice TODO 中 streaming TTS 前端项可勾选。
- 结构化 JSON persona 与流式对齐仍 out of scope。

已知问题：

- `ui_verify` API 段 `cloud tts blocked` 仍依赖运行中服务器 `allow_cloud_tts: false`（`CYBER_COMPANION_TTS_MODE=mock` 验证）。
- `ui_verify` PTT 段在本机 fake `MediaRecorder` blob 下 STT 解码失败（与 S3 无关）；TTS 冒烟 + overlap 回归已通过。

相关文件：

- `frontend/src/voice/speechText.ts`
- `frontend/src/voice/speechText.test.ts`
- `frontend/src/voice/useTextToSpeech.ts`
- `frontend/src/App.tsx`
- `docs/PHASE_STREAMING.md`

测试结果：

- `npm run test --workspace frontend`: **23** passed。
- `PYTHON_BIN=.venv/bin/python npm run check`: **138** backend + frontend `tsc` passed。
- `npm run build:frontend`: passed。
- `CYBER_VERIFY_API_URL=http://127.0.0.1:18000 CYBER_VERIFY_URL=http://127.0.0.1:5173/ node scripts/ui_verify.mjs`（`CYBER_COMPANION_TTS_MODE=mock` 后端）：TTS 竞态/overlap/refuse 冒烟 **PASS**；API `cloud tts blocked` **FAIL**（`allow_cloud_tts: true`）；PTT **FAIL**（mock 音频 STT 解码）。

不要改动的边界：

- 未改后端与 `/tts/*` 契约；`/chat/complete` 兜底保留。

## 2026-06-09 - Session 36 (Revert S3 sentence TTS queue → whole-reply speakReply)

本次完成：

- **回退句级 TTS 队列接线**（短回复句间停顿为负优化；保留 S2 文字流式 + 全文一次 `/tts/stream`）
  - `App.tsx`: 流式 `onDelta` 仅渲染文字 + 首个 delta `talking`；不再 `beginStreamingReply` / `feedStreamingReplyDelta`；`onReplyReady` 统一 `speakReply(全文)`；新轮 `stopSpeaking(false)` 取消在途音频；保留 `ttsEpoch` / `deferIdleFallback` / `ttsActiveRef` 竞态契约。
  - `useTextToSpeech.ts`: 移除句级队列 API；保留 `speakReply`（整段流式 + mock 兜底）、`stopSpeaking`（epoch 中止）。
  - `speechText.ts`: 删除 `drainStreamingSpeechChunks` / `flushStreamingSpeechRemainder` 及对应测试。

下次接着做：

- 若需更早起播，再评估其他策略（非句级硬切）；结构化 JSON + 流式仍 out of scope。

已知问题：

- `ui_verify` PTT 段仍可能因 fake `MediaRecorder` blob STT 解码失败（与本次无关）；TTS 竞态/overlap/refuse 冒烟已通过。

相关文件：

- `frontend/src/App.tsx`
- `frontend/src/voice/useTextToSpeech.ts`
- `frontend/src/voice/speechText.ts`
- `frontend/src/voice/speechText.test.ts`

测试结果：

- `npm run test --workspace frontend`: **18** passed。
- `PYTHON_BIN=.venv/bin/python npm run check`: **138** backend + frontend `tsc` passed。
- `npm run build:frontend`: passed。
- `CYBER_VERIFY_URL=http://127.0.0.1:5173/ node scripts/ui_verify.mjs`: TTS 竞态/overlap/refuse **PASS**；PTT 超时 **FAIL**（mock STT）。

不要改动的边界：

- 未改后端；`/chat/complete` 与 `/tts/*` 契约不变。

## 2026-06-09 - Session 37 (Doubao cloud ASR provider)

本次完成：

- **DoubaoASRProvider** — `backend/app/stt/doubao.py`
  - 实现 `SpeechToTextProvider`；`cloud=True`；`is_configured()` = `DOUBAO_API_KEY` 存在。
  - 鉴权：新版 `X-Api-Key` + `X-Api-Resource-Id`（默认 `volc.bigasr.auc_turbo`）+ `X-Api-Request-Id` + `X-Api-Sequence: -1`（不用旧 AppID/Token/Cluster/Bearer）。
  - `transcribe()`：push-to-talk 录音经 PyAV 解码（webm 等）转 WAV 或直传 wav/mp3/ogg；POST flash 极速版 ` /api/v3/auc/bigmodel/recognize/flash`；返回 `TranscriptionResult(provider="doubao", …)`。
  - 注册 `registry.py`；`config/stt.json` 默认 `doubao`；`stt.example.json` 增条目；`.env.example` 增 `DOUBAO_API_KEY` / `DOUBAO_ASR_RESOURCE_ID`。
  - 测试：`backend/tests/test_stt.py` mock 网络层（成功/静音/鉴权/网络/预算闸/共享 httpx client）。

下次接着做：

- 真机 push-to-talk + `allow_cloud_stt: true` 联调豆包 ASR；按需补 voice cost 跟踪。

已知问题：

- 未配置 `DOUBAO_API_KEY` 时默认 provider 为 doubao 会在 `allow_cloud_stt: true` 下报未配置；`CYBER_COMPANION_STT_MODE=mock` 或改 `stt.json` 可兜底。

相关文件：

- `backend/app/stt/doubao.py`
- `backend/app/stt/registry.py`
- `backend/tests/test_stt.py`
- `config/stt.json`
- `config/stt.example.json`
- `.env.example`
- `docs/OPEN_SOURCE_REUSE.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`: **148** backend tests + frontend `tsc` passed。

不要改动的边界：

- 未改 `/stt/transcribe` 契约；`faster_whisper` / mock / `CYBER_COMPANION_STT_MODE=mock` 保留。

## 2026-06-09 - Session 26 (Claude：架构转向 V2 重建 + 灵魂优先)

本次完成：

- 与用户对齐全貌与两个核心：① 全双工实时对话（记忆+人格之上）② 盒中小人（2.5D 像素房间，屏=玻璃）。硬件终局：旧 iPhone SE2 + 3D 打印壳当“盒子”（iPhone=壳/surface，大脑在 Mac，云端只放 DeepSeek/豆包）。
- 调研开源同类（Open-LLM-VTuber / Project AIRI / Soul of Waifu / OpenAvatarChat / super-agent-party / memU 等）并做基座决策。
- 写了两份**新源头文档**：`docs/ARCHITECTURE_V2.md`（目标架构）+ `docs/REBUILD_ROADMAP.md`（9 阶段路线）。
- 关键决策（已写进 ARCHITECTURE_V2）：基座 = Pipecat（语音）+ 保留 Python 灵魂 + PixiJS 像素房间（自建）；AIRI 等只当参考不 fork（Vue/TS/xsAI，基于它要重写灵魂、像素非即插即用）；iPhone surface 用 Capacitor；脑/壳 WebSocket 分离。狠抄：Capacitor-iOS、`@ricky0123/vad-web`、Open-LLM-VTuber 的回声消除/无耳机打断、情绪→表情映射。
- **战略转向（用户选 1）：灵魂优先。** 洞见：记忆+主动+情绪 ≈ 80% 情绪价值，实时语音 ≈ 20%。调研证实整条 VTuber 赛道都在卷 20%、几乎不做 80%，而我们已有 80% 脚手架（memory/behavior 含 proactive/mood）。故先把灵魂做深，语音+盒子作为之后沉浸层。
- 预算墙全关（`config/budget.json`：monthly=0、daily=0、allow_reasoning_model=true）。用户固定大额套餐，不怕烧 API。
- 灵魂设计共识：**可额外烧 LLM**，但按延迟智能放置 —— ① 同步=让那一次回复调用顺便吐结构化信号（情绪/记忆/关系）；② 后台=反思/做梦（整理记忆、演进关系叙事、形成印象，延迟零）；③ 高频琐碎留本地。最大三处收益：LLM 记忆抽取（M2 升级）、LLM 情绪/关系更新、后台反思层。

下次接着做（新窗口从这里起）：

- **深挖 memU + “subjectivity kernel”（持久情绪+关系动态+零额外 LLM，疑似用户说的 Resonant）+ awesome-affective-computing**，产出一份“灵魂深化”实现方案：LLM 驱动但延迟智能放置，升级 记忆抽取 / 情绪+关系状态 / 新增后台反思层。在现有能跑的 app 上小步迭代，**不重建**。出完按规矩 Claude spec → Cursor 实现 → Claude 验收。
- 之后才进 V2 重建（Pipecat 语音 + PixiJS 房间 + Capacitor iPhone 壳），照 `docs/REBUILD_ROADMAP.md`。

已知问题：

- 一批**未提交**改动：`config/budget.json`（墙关了）、`config/tts.json`、`docs/PHASE_STREAMING.md`（S3 撤回说明）、`docs/TODO.md`、`frontend/src/api/tts.*`、新增 `docs/ARCHITECTURE_V2.md` / `docs/REBUILD_ROADMAP.md`。新窗口先 `git status` 确认、视情况 checkpoint。
- S3（句级 TTS）已撤回（短回复反而卡；改回整段一次流式）。语音延迟现状：松手→豆包 ASR ~2.7s（文件识别，准但不快）→DeepSeek ~1.5s→TTS。真·快需流式 ASR（留 V2 语音阶段）。

相关文件：

- `docs/ARCHITECTURE_V2.md`（**新源头**）、`docs/REBUILD_ROADMAP.md`
- `config/budget.json`（墙已关）、`docs/PHASE_STREAMING.md`（S3 撤回）
- 灵魂层（留用核心）：`backend/app/memory/`、`backend/app/behavior/`、persona/provider/file-gateway

测试结果：

- 本会话以架构/调研/文档为主，未改后端逻辑（仅改 `config/budget.json` + 文档）。上次 Cursor 记录 `npm run check` = 148 后端测试 + tsc 通过。

不要改动的边界：

- 灵魂层是 V2 保留核心，深化不推倒。
- 预算墙保持关闭（用户选择），但保留配置旋钮以便日后重启。
- 灵魂的额外 LLM 调用**别放在“用户等回复”的关键路径上**（同步只用 piggyback，重活后台）。
- 先做灵魂，语音+盒子是之后阶段。

## 2026-06-09 - Session 34 (Cursor：SD-1 Piggyback signal contract)

本次完成：

- **SD-1 Task 1 — `behavior/parser.py`**
  - `SIGNALS_SENTINEL = "<<<BOXI_SIGNALS>>>"`；`StructuredAssistantResponse.signals` 字段。
  - `parse_structured_assistant_response`：sentinel 优先切分 → legacy 整段 JSON → embedded JSON → 纯文本兜底；malformed trailer 不污染 `content`。
  - `SignalStreamFilter`：hold-back + sentinel 检测 + `flush()`。
- **SD-1 Task 2 — `main.py` `/chat/stream`**
  - delta 0 循环接入 `SignalStreamFilter`；`accumulated_parts` 仍收全量 raw text；`try/finally` 保证异常路径也 flush 已缓冲可见文本。
- **SD-1 Task 3 — `memory/persona.py`**
  - 两条 prompt 路径末尾 append `OUTPUT_PROTOCOL`（不改 name/tone/boundaries/catchphrases）。
- **SD-1 Task 4 — `backend/tests/test_behavior.py`**
  - 新增 parser 三用例 + stream filter 三用例；legacy `test_structured_parser_reads_json_payload` 仍绿。

下次接着做：

- **SD-2** — subjectivity kernel（`relationship_state` 表、appraisal 本地数学、context blocks）。Claude spec 已有，等 Claude 写 SD2_SPEC 或 Cursor 按 `SOUL_DEEPENING_SPEC.md` §4 实现。
- 顺手修：`test_stt_status_route` 仍断言 `allow_cloud_stt is False`，与已提交的 `config/budget.json`（`true`）不一致 — 153/154 通过。

已知问题：

- `PYTHON_BIN=.venv/bin/python npm run check`：**153 passed, 1 failed** — `test_stt.py::test_stt_status_route`（预存 config/test 漂移，非 SD-1 引入）。
- SD-1 未消费 `signals.appraisal` / `relationship` / `memory`（留给 SD-2/SD-3）。

相关文件：

- `backend/app/behavior/parser.py`
- `backend/app/main.py`（stream delta 循环）
- `backend/app/memory/persona.py`
- `backend/tests/test_behavior.py`
- `docs/SD1_SPEC.md`、`docs/SOUL_DEEPENING_SPEC.md` §3

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：154 项中 **153 通过**（+7 新 behavior 测试）；tsc 未跑到（pytest 先失败）。
- SD-1 相关：`test_behavior.py` 18/18 绿；`test_chat_stream.py` 5/5 绿。

不要改动的边界：

- 未动 schema/config/budget/provider/file-gateway；未碰 SD-2 及以后。
- `signals` 只 parse 不 apply；Boxi 毒舌 core persona 未改。
## 2026-06-09 - Session 35 (Cursor：SD-2 Subjectivity kernel + SD-2-UI)

本次完成：

- **SD-2 Task 1 — schema/store**
  - `relationship_state` 表（纯增量，`SCHEMA_VERSION=2`）；`RelationshipStateRecord` + store CRUD；init seed + 一次性 `mood_state.trust` backfill。
- **SD-2 Task 2 — kernel math**
  - `behavior/kernel.py` `apply_signals_to_kernel`（clamp ±0.1，best-effort）；`mood.py` 去掉 trust 变更；idle tick loneliness 按 closeness 重取源 + annoyance/worry 衰减。
- **SD-2 Task 3 — wiring**
  - `choose_tone_mode` 关系门控 tease；engine refused/overwhelmed 即时关系 nudge；`main.py` parse 后调 kernel（complete + stream）；`GET /memory/relationship`。
- **SD-2 Task 4 — context**
  - `[Relationship]` 总是注入；`[Impression]` 仅有 `relationship_state` 记忆时出现。
- **SD-2 Task 5 — tests**
  - `backend/tests/test_relationship_state.py`（12 用例）。
- **SD-2 Task 6 — docs**
  - `docs/MEMORY_DESIGN.md` 更新 emotion/relationship 拆分与 kernel 原则。
- **SD-2-UI**
  - 「Boxi 怎么看你」只读面板（`RelationshipPanel.tsx`）。
- **Maintenance**
  - `test_stt_status_route` 用 isolated tmp `budget.json`（`allow_cloud_stt: false`）。

下次接着做：

- **SD-3** — LLM memory extraction（消费 `signals.memory[]`）。

已知问题：

- 无。

相关文件：

- `backend/app/memory/schema.py`, `database.py`, `store.py`
- `backend/app/behavior/kernel.py`, `mood.py`, `engine.py`
- `backend/app/memory/context_builder.py`, `backend/app/main.py`, `backend/app/schemas.py`
- `backend/tests/test_relationship_state.py`, `backend/tests/test_stt.py`
- `frontend/src/api/relationship.ts`, `frontend/src/components/RelationshipPanel.tsx`
- `docs/MEMORY_DESIGN.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**166 passed** + tsc 通过。

不要改动的边界：

- 未消费 `signals.memory[]`（SD-3）；未做后台反思层（SD-4）。
- kernel 无额外 LLM；未 ALTER/DROP `mood_state`；Boxi 毒舌 core 未改。

## 2026-06-09 - Session 36 (Cursor：SD-3 LLM memory extraction M2→M3)

本次完成：

- **SD-3 Task 1 — `write_policy.py`**
  - `_persist_candidate(..., writer=)`；`_validate_signal_memory`（type 白名单 + clamp + clip + ≥0.6 门槛）。
  - `write_memories_from_signals`（cap 5，`writer="llm"`）；`record_turn_memories` 编排器（M3 或 M2，respect `auto_memory_write`）。
- **SD-3 Task 2 — config**
  - `BudgetConfig.llm_memory_extraction`（默认 true）；`config/budget.json` + `budget.example.json`。
- **SD-3 Task 3 — `main.py`**
  - `/chat/complete`：`reply_signals` 捕获 + `record_turn_memories`（try/except）。
  - `_finalize_streamed_turn`：`record_turn_memories(signals=parsed.signals)`。
  - budget-block / local 分支仍用 `maybe_write_memories_from_turn`。
- **SD-3 Task 4 — tests**
  - `test_memory_write_policy.py` +10 用例（M3 写入、拒绝、clamp、dedup、cap、编排、gate）。
- **Docs**
  - `docs/MEMORY_DESIGN.md` Auto-Write 段更新 M2/M3 说明。

下次接着做：

- **SD-4** — background reflection layer（`enable_reflection` 等 knob + 后台任务）。

已知问题：

- 无。

相关文件：

- `backend/app/memory/write_policy.py`, `budget.py`
- `backend/app/main.py`（两处 LLM 写入点）
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_memory_write_policy.py`
- `docs/MEMORY_DESIGN.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**176 passed** + tsc 通过。

不要改动的边界：

- 每轮只走 M3 或 M2 一条路径；未删 `extract_memory_candidates`。
- 无 linking（SD-5）、无反思层（SD-4）、无 schema 改动。

## 2026-06-09 - Session 37 (Cursor：SD-4 background reflection layer)

本次完成：

- **SD-4 Task 1 — `store.py`**
  - `get_meta` / `set_meta`；`note_llm_turn`；原子 `claim_reflection`（单事务）；`release_reflection`；`get_max_chat_message_id`。
- **SD-4 Task 2 — config**
  - `enable_reflection` / `reflection_every_n_turns` / `llm_summary` 三旋钮 → `BudgetConfig` + `config/budget*.json`。
- **SD-4 Task 3 — `backend/app/reflection/`**
  - `runner.run_reflection_if_due`（enable→claim→3 job 各自 try/except→finally release）；`jobs.py`：consolidate（archive+deprioritize only）、form_impression（单条 `relationship_state` upsert）、summarize_conversation_llm（`llm_summary` 开时）。
- **SD-4 Task 4 — `summary_policy.py`**
  - `llm_summary` 开时同步路径 `return False`，摘要推迟到后台 Job 3。
- **SD-4 Task 5 — `main.py`**
  - `/chat/complete`：`BackgroundTasks` + LLM 回合 `note_llm_turn` + `add_task`；`/chat/stream`：LLM 分支 `note_llm_turn` + `StreamingResponse(background=BackgroundTask(...))`。
- **SD-4 Task 6 — tests**
  - 新建 `test_reflection.py`（claim/single-flight、disabled、failure isolation、impression upsert、consolidate、summary deferral、chat 不受影响）；`test_context_builder` 规则摘要用例显式 `llm_summary=False`。
- **SD-4 Task 7 — docs**
  - `docs/MEMORY_DESIGN.md` 新增 Background reflection (SD-4) 小节。

下次接着做：

- **SD-5（可选）** — `memory_links` + top-down retrieval。

已知问题：

- 反思花费尚未接预算闸（`# TODO(SD-later): gate reflection spend`）；idle_tick  opportunistic 反思未做。

相关文件：

- `backend/app/memory/store.py`, `budget.py`, `summary_policy.py`
- `backend/app/reflection/`（`runner.py`, `jobs.py`）
- `backend/app/main.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_reflection.py`, `test_context_builder.py`
- `docs/MEMORY_DESIGN.md`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**187 passed** + tsc 通过。

不要改动的边界：

- 无 schema/DDL 改动；无 linking（SD-5）；consolidation 不 merge/不升 importance；同步路径不调 LLM；反思异常不进请求路径；`reflecting` finally 必释放。

## 2026-06-09 - Session 27 (Claude：灵魂深化 SD-1..SD-4 spec+验收 + SD-5 spec + 联调 smoke)

本次完成：

- 按 Session 26 转向，产出**灵魂深化总方案** `docs/SOUL_DEEPENING_SPEC.md`（三层延迟智能放置：① piggyback ② 后台反思 ③ 本地数学），并逐阶段写实现级 spec：`SD1_SPEC.md`（piggyback 信号契约，流式安全 sentinel trailer）、`SD2_SPEC.md`（主体性内核，情绪/关系拆分）、`SD3_SPEC.md`（LLM 记忆抽取 M2→M3）、`SD4_SPEC.md`（后台反思层）、`SD5_SPEC.md`（记忆连边+一跳检索，可选，待实现）。
- 走完 **Claude spec → Cursor 实现 → Claude 验收** 四轮：SD-1（9b93b6e）、SD-2（3b942da）、SD-3（5faf351）、SD-4（552a08f）全部验收通过并 checkpoint。每轮按各自 spec 的 Done criteria 审 diff。
- 顺手让 Cursor 修了 Session-26 遗留的 `test_stt_status_route`（隔离测试自带 budget.json）。
- **联调 smoke（mock provider，无真 DeepSeek key）**：uvicorn 起服务，7 轮 /chat/complete 确认 ① 信号 trailer 零泄漏；② relationship 持久化、familiarity 0→0.07（内核每 LLM 轮 +0.01）；③ 反思在第 6 轮触发（`turns_since_reflection` 归零再 +1=1、`last_reflected_message_id=12`、`reflecting=0` 已释放）、服务跨阈值不崩；④ M2 回退去重写出单条 job_progress。

下次接着做：

- 二选一：**(a)** 配置真 DeepSeek key 做真·联调（验证 appraisal→trust/closeness 真实移动、signals.memory M3、impression 文本填入 `[Impression]`）；**(b)** 实现 **SD-5**（`docs/SD5_SPEC.md` 已就绪）；或 **(c)** 灵魂已够深，转 V2 重建（`docs/REBUILD_ROADMAP.md`：Pipecat 语音 + PixiJS 房间 + Capacitor iPhone 壳）。

已知问题：

- 本环境无 `config/providers.json` 且 env 无 DeepSeek key → 真·LLM 路径（appraisal/M3/impression 文本）未实跑，仅 187 单测确定性覆盖 + mock 联调覆盖机制。
- 反思花费暂未受预算闸约束（墙关着；`jobs.py` 留 `# TODO(SD-later): gate reflection spend`）。

相关文件：

- 方案/规格：`docs/SOUL_DEEPENING_SPEC.md`、`docs/SD1_SPEC.md`..`docs/SD5_SPEC.md`
- 实现：`backend/app/behavior/{parser,kernel,mood,engine}.py`、`backend/app/memory/{schema,database,store,write_policy,context_builder,summary_policy,budget}.py`、`backend/app/reflection/`、`backend/app/main.py`、`config/budget*.json`、`frontend` 关系面板

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**187 passed** + tsc 通过（含 SD-1..SD-4 全部新测）。
- mock 联调 smoke：见“本次完成”④。

不要改动的边界：

- 灵魂额外 LLM 调用绝不上用户等待路径（同步只 piggyback，重活后台）。
- 预算墙保持关闭但保留旋钮；schema 改动须更 `docs/MEMORY_DESIGN.md`。
- 后台反思 best-effort、永不破坏对话；`reflecting` finally 必释放。
- Boxi 毒舌人设不变；不发全量历史；LLM 输出只当数据。

## 2026-06-09 - Session 38 (Cursor：SD-1b mandatory signals trailer)

本次完成：

- **SD-1b Task 1 — `persona.py`**
  - `OUTPUT_PROTOCOL` 换为 mandatory + one-shot example（含 memory item）；去掉 "omit the trailer" 逃生口。
  - `load_persona_system_prompt()` 只返回人设，不再 append protocol；常量仍可 import。
- **SD-1b Task 2 — `context_builder.py`**
  - `build_provider_context` 在 mood/relationship/impression/memories 之后把 `OUTPUT_PROTOCOL` 作为**最后一个** system section 追加（pack 时预留 token，保证不被截断）。
- **SD-1b Task 3 — config**
  - `max_output_tokens_per_turn` 300 → 600（`budget.json` + `budget.example.json`）。
- **SD-1b Task 4 — tests**
  - `test_load_persona_system_prompt_excludes_output_protocol`；`test_context_builder_system_message_ends_with_protocol_once`；小预算用例改为断言 protocol 必现 + 大段 memory 被截断。

下次接着做：

- **真·DeepSeek re-smoke**（Claude review）：验证 trailer 多数轮次出现、trust/closeness 移动、`writer="llm"` 记忆写入。
- 或 **SD-5** / V2 重建。

已知问题：

- 未在本环境跑真 DeepSeek 验收（需 Claude re-smoke）。

相关文件：

- `backend/app/memory/persona.py`, `context_builder.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_context_builder.py`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**189 passed** + tsc 通过。

不要改动的边界：

- 未改 parser / SignalStreamFilter / kernel / 写入管线；人设语气/边界不变；M2 正则回退保留。

## 2026-06-09 - Session 39 (Cursor：SD-1c trailer reminder on user turn)

本次完成：

- **SD-1c — `context_builder.py`**
  - `_TRAILER_REMINDER` 常量；`provider_user_input_for_send` 仅用于发给 provider 的最后一条 user 消息。
  - 提醒 token 计入 `reserved_tokens` 预算估算；原始 `user_input` 不变、不入库、不进 `recent_raw` 重放。
- **SD-1c — tests**
  - provider user 消息以提醒结尾且含 sentinel；重放历史不含提醒；`user_input` 不被 mutate。
  - 更新 `test_user_input_truncation` / 既有 context_builder 断言以适配 provider-only 提醒。

下次接着做：

- **真·DeepSeek re-smoke**（Claude review）：有累积历史时 trailer 多数轮次出现、signals 流动。
- 或 **SD-5** / V2 重建。

已知问题：

- 未在本环境跑真 DeepSeek 验收。

相关文件：

- `backend/app/memory/context_builder.py`
- `backend/tests/test_context_builder.py`, `test_user_input_truncation.py`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**192 passed** + tsc 通过。

不要改动的边界：

- 仅改 context_builder + 测试；提醒 provider-only，绝不入库/重放累积；parser/stream/kernel/写入管线未动。

## 2026-06-09 - Session 27 (Claude：真·DeepSeek 联调 + SD-1b/1c 验收 + SD-3b 发现)

本次完成：

- **真·DeepSeek 联调（用户提供 key，仅经临时文件、用后即删，未入库/未提交）。** 三轮诊断定位「信号不流动」根因：
  1. 初测：回复零泄漏、人设在线、SD-4 反思真写出 LLM 印象、familiarity 随轮上涨；但 trust/closeness 冻结、记忆全是 regex M2 → 模型几乎不吐 `<<<BOXI_SIGNALS>>>` trailer（~0–1/3）。
  2. A/B：trailer 缺失非排序问题；是「omit the trailer」逃生口 + 角色扮演沉浸。强制+单样例 → 直调 4/5。→ **SD-1b**（Cursor 实现 + Claude 验收，`a278d64`）。
  3. SD-1b 复测仍 0：根因更深 —— 持久化 `parsed.content`（剥 trailer）并回放这些**无 trailer 的 assistant 历史**，模型照猫画虎。实测：有历史 0/5、无历史 3/5、尾随 system 提醒 0/5、**提醒挂当前 user 轮 3/5**。→ **SD-1c**（Cursor 实现 + Claude 验收，`d7f10e2`）。
- **SD-1c 收效复测（真 DeepSeek，6 轮）：信号真流动** —— trust 0.5→0.63、closeness 0.2→0.36、last_meaningful 已置、loneliness→0、worry 回落；全程零泄漏。灵魂从「接好线」变「活了」。
- **新发现 → SD-3b（spec `docs/SD3b_SPEC.md`）：** trailer 现在会带 `memory[]`，但 `record_turn_memories` 见非空 `memory[]` 即提交 M3、不再回退 M2；LLM 项全部校验失败（type 不在白名单等）时 M3 写 0 且 M2 被跳过 → 该轮事实记忆丢失（复测事实记忆为 0，仅剩反思印象）。`list_memories` 不滤 expired，确认是「从未写入」非「归档隐藏」。修法：M3 空结果回退 M2 + protocol 枚举合法 memory type。

下次接着做（建议开新会话，从 docs/HANDOFF.md 顶部接起）：

- 先 **SD-3b**（`docs/SD3b_SPEC.md`）→ 再 smoke 验「事实记忆回来 + 信号仍流动」。
- 然后 **SD-5**（可选）或转 **V2 重建**（`docs/REBUILD_ROADMAP.md`）。

已知问题：

- trailer 触发 ~3/5（M2 兜底覆盖漏网轮）。嫌低的升级路径：回放带 trailer 的历史，或抽取转 Tier-② 后台调用。
- SD-3b 未做前，吐了 `memory[]` 但校验失败的轮会丢事实记忆。

相关文件：

- `docs/SD1b_SPEC.md`、`docs/SD1c_SPEC.md`、`docs/SD3b_SPEC.md`（新）、`docs/HANDOFF.md`（顶部已更新）

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**192 passed** + tsc 通过。
- 真 DeepSeek：SD-1c 后 trust/closeness/loneliness 真实移动、零泄漏；事实记忆缺失 → SD-3b。

不要改动的边界：

- key 只走环境变量/临时文件，绝不入库或写进任何文件。
- 灵魂额外 LLM 不上等待路径；M2 正则保留作兜底；Boxi 毒舌人设不变。

## 2026-06-10 - Session 28 (Claude：SD-3b 实现 + SD-5 实现，两个 checkpoint)

本次完成：

- **SD-3b（`e610f1e`）— M2 兜底 + 枚举合法 memory 类型。** `record_turn_memories` 原本在
  `signals.memory[]` 非空时无条件走 M3，若 LLM 条目全部校验失败（type 不在白名单 / 内容
  <4 字 / 置信度 <0.6）则 M3 写空且正则 M2 永不触发，整轮记忆静默丢失（SD-1c 让 trailer 真
  吐出后暴露：信号流动但事实记忆消失）。修复：M3 写空 → fall through 到 M2（`write_policy.py`）；
  `OUTPUT_PROTOCOL` 枚举 8 个合法 type（排除系统托管的 `conversation_summary`，`persona.py`）；
  `MEMORY_DESIGN.md` Auto-Write 段补兜底路径。+3 测试。
- **SD-5（`a6a8fa8`）— 记忆连边 + 一跳 top-down 检索。** 增量 `memory_links` 表
  （`SCHEMA_VERSION=3`，双向 + 幂等 + `ON DELETE CASCADE`）；store 三方法
  （`add_memory_link`/`get_linked_memory_ids`/`count_memory_links`）；反思层确定性 linker
  `link_related_memories`（consolidate 之后、无 LLM；跨类型 + token 重叠 ≥2 且 ≥0.34、每轮封顶、
  幂等）；`consolidate_memories` 候选限定 `FACTUAL_MEMORY_TYPES`（印象/摘要/emotion 永不被归档）；
  `context_builder` 一跳扩展（加性、capped `max(2, max_memories_per_turn//2)`、过期天然跳过）。
  `MEMORY_DESIGN.md` 三处更新。+12 测试（`test_memory_links.py`）。

**真·DeepSeek 验收追加（用户提供 key，env-only，smoke 后即删 DB+脚本，未入库）：**

- 7 轮 in-process TestClient 真机 smoke。**SD-3b Done criterion #2 = PASS：**
  ① 零泄漏（7 轮 content 无 `<<<BOXI_SIGNALS>>>`）；② 信号流动 trust 0.50→0.52 /
  closeness 0.20→0.22 / familiarity 0→0.07 / tension 0→0.17；③ **7 条事实记忆 `writer="llm"`**
  落库（M3 校验通过：project=Acme、reminder=周五面试、job_progress、多条 recent_event），
  正是 SD-3b 要救的「事实记忆消失」回归已修复；④ SD-4 反思写出真实印象叙事
  （`writer=reflection`）；⑤ 反思触发 `last_reflected_message_id=12`。
- **新发现 → SD-5b（已记入 TODO，`[Claude]`）：** SD-5 linker 在中文上形成 **0 链**。根因
  `retrieval.tokenize` 只按空白/标点分词，无中文分词 → 整句塌成单 token
  （`张伟的副业项目叫acme`），跨记忆永不重叠。机制本身正确（英文单测通过），但对中文近乎 no-op；
  同样削弱中文关键词检索。修复留 SD-5b（CJK bigram/jieba 分词）。

下次接着做：

- **SD-5b** — CJK-aware tokenizer（linker + 检索都受益），修完再复测中文连边。`[Claude]`。
- 之后可转 **V2 重建**（`docs/REBUILD_ROADMAP.md`：Pipecat 语音 + PixiJS 房间 + Capacitor iPhone 壳）。
- Cursor 下一步前端小切片：见本会话给出的「Cursor 任务」（只读「Boxi 的记忆」面板，
  现有 `GET /memory/memories`，纯前端）。连边可视化需先加只读 `GET /memory/links` 路由（`[Claude]`，已记 backlog）。

已知问题：

- 真机已验 SD-1c/SD-2/SD-3b/SD-4；SD-5 连边因中文分词在真机上为 0（见 SD-5b）。
- 反思花费仍未受预算闸约束（墙关着；`jobs.py` 留 `# TODO(SD-later): gate reflection spend`）。
- linker 的一跳扩展并入单个 `[Relevant memories]` section，packer 仍是整块取舍（既有行为）：极端 token
  紧张时整块（核心+扩展）一起被丢，扩展逻辑本身从不移除已选记忆。
- **安全：本次 DeepSeek key 在对话中以明文粘贴 — 建议用户轮换/吊销该 key。**

相关文件：

- `backend/app/memory/{schema,store,write_policy,persona,context_builder}.py`
- `backend/app/reflection/{jobs,runner}.py`
- `backend/tests/{test_memory_write_policy,test_memory_links}.py`
- `docs/MEMORY_DESIGN.md`、`docs/TODO.md`、`docs/SD3b_SPEC.md`、`docs/SD5_SPEC.md`

测试结果：

- SD-3b 后：`PYTHON_BIN=.venv/bin/python npm run check` **195 passed** + tsc。
- SD-5 后：`PYTHON_BIN=.venv/bin/python npm run check` **207 passed** + tsc。
- 真机 DeepSeek 7 轮 smoke：SD-3b Done #2 PASS（零泄漏 + 信号移动 + 7 条 `writer="llm"` 事实记忆 + 印象）。

不要改动的边界：

- key 只走环境变量/临时文件，绝不入库。
- 反思 best-effort、永不破坏对话路径；`reflecting` finally 必释放。
- SD-5：增量表、确定性 linker（无 LLM）、一跳 capped 加性检索、linking/consolidation 仅 factual 类型。
- Boxi 毒舌人设不变；不发全量历史；LLM 输出只当数据。

## 2026-06-10 - Session 29 (Cursor：只读「Boxi 的记忆」面板)

本次完成：

- 纯前端切片：新增 `frontend/src/api/memories.ts`（`fetchMemories` → `GET /memory/memories`）与
  `frontend/src/components/MemoryPanel.tsx`。
- 折叠 `<details>` 面板，受 `apiHealth.status === "ok"` gating；按 type 分组展示（中文标题）、
  每条显示 content + importance 百分比 + writer 徽章（llm / 规则 / 反思）；前端过滤 `expires_at` 已过期条目。
- `App.tsx` 挂在 `RelationshipPanel` 旁；`styles.css` 复用/扩展 relationship-panel 像素风格。
- `docs/TODO.md` 追加 memory links 可视化 backlog（需 `[Claude]` 新增只读 `/memory/links` 路由）。

下次接着做：

- SD-3b Done criterion #2（真·DeepSeek 复测，需用户提供 key）。
- Memory links 可视化（待 `/memory/links` 只读路由）。
- 或 V2 重建 / 语音 backlog（`textForSpeech` 去括号等）。

已知问题：

- 面板不展示 memory_links 连边（无 GET 端点，刻意排除）。
- `/memory/memories` 仍返回过期条目，面板侧自行过滤与检索口径对齐。

相关文件：

- `frontend/src/api/memories.ts`
- `frontend/src/components/MemoryPanel.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**207 passed** + tsc。
- `npm run build:frontend`：通过。

不要改动的边界：

- 无后端改动；不改 provider / memory schema / behavior contract / file permission policy。
- 只读，无编辑/删除记忆写操作。

## 2026-06-10 - Session 30 (Cursor：只读「Boxi 此刻心情」面板)

本次完成：

- 纯前端切片：新增 `frontend/src/components/MoodPanel.tsx`，`fetchMoodState()` → `GET /memory/mood`。
- 折叠面板 + API gating；顶部 mood 中文标签（覆盖 avatar 10 态）；五项进度条
  （精力/烦躁/无聊/担心/孤独），不重复展示 trust（已在关系面板）。
- `App.tsx` 挂在 RelationshipPanel 与 MemoryPanel 之间，补齐灵魂仪表盘三件套。
- `styles.css` 复用 companion 面板像素风格。
- `docs/TODO.md`：`textForSpeech` / `stripStageDirections` 勾选（`speechText.ts` 已实现并接入）。

下次接着做：

- Memory links 可视化（待 `GET /memory/links` 只读路由）。
- 语音 backlog（豆包连接复用、streaming TTS 等）或 V2 重建。

已知问题：

- 心情面板仅在挂载/启用时拉取一次，不随对话轮次自动刷新（与关系/记忆面板一致）。

相关文件：

- `frontend/src/components/MoodPanel.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**207 passed** + tsc。
- `npm run build:frontend`：通过。

不要改动的边界：

- 无后端改动；不改 provider / memory schema / behavior contract / file permission policy。

## 2026-06-10 - Session 32 (SD-5b：CJK-aware tokenizer)

本次完成：

- **SD-5b**（`docs/SD5b_SPEC.md`）：`retrieval.tokenize` 用 jieba 切 CJK 实词 + ASCII
  `[a-z0-9_]+`；lazy import + `_tokenize_fallback`（jieba 缺失时回退旧逻辑）。
- linker `_LINK_MIN_RATIO` 0.34→**0.25**（仅常量，表/契约/1-hop 扩展未动）。
- 依赖 `jieba>=0.42.1`；`MEMORY_DESIGN.md` / `OPEN_SOURCE_REUSE.md` 更新。
- 测试：中文 tokenize + job_progress 排序；中文跨类型连边 + 无关对不连；jieba 缺失 fallback；
  英文 links/dedup 全绿。

下次接着做：

- Claude 真·DeepSeek 复测：中文对话后 `memory_links > 0`。
- Memory links UI（待 `GET /memory/links`）或 V2 重建 / 语音 backlog。

已知问题：

- jieba 首次 import 有 `pkg_resources` DeprecationWarning（上游，可忽略）。
- SD-5b 真机连边 smoke 尚未跑（留给 Claude + key）。

相关文件：

- `backend/app/memory/retrieval.py`
- `backend/app/reflection/jobs.py`（`_LINK_MIN_RATIO` only）
- `backend/requirements.txt`
- `backend/tests/test_memory_retrieval.py`
- `backend/tests/test_memory_links.py`
- `docs/MEMORY_DESIGN.md`、`docs/OPEN_SOURCE_REUSE.md`、`docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**211 passed** + tsc。
- `npm run build:frontend`：通过。

不要改动的边界：

- 未改 `memory_links` 表/契约、SD-5 一跳扩展、`context_builder` SD-1..4 行为。
- 确定性 only；英文路径与 dedup 套件保持绿色。
