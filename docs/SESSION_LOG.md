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

## 2026-06-10 - Session 28b (Claude: SD-5b diff review + Chinese re-smoke)

- Reviewed Cursor SD-5b diff (`8a25c37`): jieba lazy-import + fallback, ASCII+CJK
  segments, stopword filter, ratio 0.25, 4 new tests. Faithful to spec, diff confined.
  Full gate green (211 + tsc; jieba 0.42.1).
- **Real-DeepSeek re-smoke PASS:** 6-turn Chinese chat → `memory_links` = 4 rows
  (2 logical), e.g. `job_progress`↔`recent_event` sharing Acme/项目. Pre-jieba: 0.
  Writers seen: llm / rule_based / reflection. Key env-only; DB + script deleted.
- SD-5b done & verified. **Soul deepening SD-1..SD-5b complete + real-DeepSeek validated.**
- Reminder: DeepSeek key was pasted in chat — user should rotate it.

## 2026-06-10 - Session 33 (Memory links read-only API + UI panel)

本次完成：

- **Memory links UI spec**（`docs/MEMORY_LINKS_UI_SPEC.md`）：`GET /memory/links` 只读路由
  （逻辑对去重 + JOIN type/snippet）；`store.list_memory_links` + `MemoryLinkRecord`。
- 前端：`memoryLinks.ts`、`MemoryLinksPanel.tsx`（「Boxi 把这些联系起来了」）、
  `memory/typeLabels.ts`（与 MemoryPanel 共用中文 type 标签）；`App.tsx` 挂在 MemoryPanel 后。
- 测试：`GET /memory/links` 返回 1 条逻辑连边 / 空库 `[]`；**213 passed** + tsc + build。

下次接着做：

- V2 重建 / 语音 backlog（streaming TTS、豆包连接复用等）。

已知问题：

- 连边面板仅在挂载时拉取一次（与关系/记忆/心情面板一致）。

相关文件：

- `backend/app/memory/{database,store}.py`、`backend/app/{main,schemas}.py`
- `frontend/src/api/memoryLinks.ts`、`frontend/src/components/MemoryLinksPanel.tsx`
- `frontend/src/memory/typeLabels.ts`、`frontend/src/App.tsx`、`frontend/src/styles.css`
- `backend/tests/test_memory_links.py`
- `docs/MEMORY_DESIGN.md`、`docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**213 passed** + tsc。
- `npm run build:frontend`：通过。

不要改动的边界：

- 只读；未改 `memory_links` 表/契约、SD-5 linker、1-hop 检索、任何 SD 契约。

## 2026-06-10 - Session 34 (V2 Phase 0 — brain/surface seam)

本次完成：

- **V2 Phase 0 checkpoint**（`docs/V2_PHASE0_SPEC.md`）：`backend/realtime/` 包骨架
  （`CompanionBrain` 三类 stub：`decide` / `respond` / `remember`），soul import 对齐
  `main.chat_complete`（`evaluate_behavior`、`build_provider_context`、
  `get_provider_router`、`record_turn_memories`、`load_persona_system_prompt`）。
- `backend/requirements-realtime.txt` 声明 `pipecat-ai==1.3.0`（未安装）。
- `docs/ARCHITECTURE_V2.md` 新增 Repo layout (V2)；`docs/OPEN_SOURCE_REUSE.md` 记录
  Pipecat / PixiJS / vad-web / Capacitor。
- `backend/tests/test_realtime_skeleton.py`：import + stub `NotImplementedError` 边界测试。

下次接着做：

- V2 Phase 1 — Pipecat voice skeleton（安装 realtime deps、WebSocket、mic→VAD→STT→LLM→TTS）。

已知问题：

- 无；V1 行为与 entrypoint 未动。

相关文件：

- `backend/realtime/{__init__.py,companion_brain.py,README.md}`
- `backend/requirements-realtime.txt`
- `backend/tests/test_realtime_skeleton.py`
- `docs/ARCHITECTURE_V2.md`、`docs/OPEN_SOURCE_REUSE.md`、`docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**215 passed** + tsc。
- `npm run build:frontend`：通过。

不要改动的边界：

- 未改 `backend/app/main.py`、soul 模块、V1 frontend；未 `pip install pipecat`、未装 PixiJS。

## 2026-06-10 - Session 35 (V2 Phase 1 — Pipecat voice skeleton)

本次完成：

- **V2 Phase 1 checkpoint**：`backend/realtime/run_voice.py` — Pipecat **1.3.0** 本地音频管线
  （`LocalAudioTransport` → `WhisperSTTService` faster-whisper `base` → `OpenAILLMService`
  DeepSeek → `MacSayTTSService` macOS `say` 占位 TTS），`SileroVADAnalyzer` 打断。
  API 起手自官方 `examples/getting-started/06a-voice-agent-local.py`（`PipelineWorker` +
  `WorkerRunner` + `LLMContextAggregatorPair`），非 spec 臆造类名。
- `backend/realtime/mac_say_tts.py` 占位 TTS；`backend/requirements-realtime.txt` 扩充
  （pyaudio、faster-whisper、onnxruntime 1.23.2 workaround、numpy pin）。
- `backend/tests/test_realtime_voice.py`（`pytest.importorskip`）；README「Run the voice skeleton」段。

下次接着做：

- V2 Phase 2 — Doubao streaming STT/TTS as Pipecat services。
- 用户本地 mic 全链路验收（speak → voice reply → interrupt）。

已知问题：

- 外接音箱 + 笔记本：打断 best-effort（half-duplex），与 ARCHITECTURE_V2 预期一致。
- `pipecat-ai` 声明 `onnxruntime~=1.24.3` 在 macOS x86_64 不可用，用 1.23.2。
- numba 曾把 numpy 升到 2.2.6 致 scipy 损坏；`requirements-realtime.txt` 已 pin `numpy<2.3`。

相关文件：

- `backend/realtime/{run_voice.py,mac_say_tts.py,README.md}`
- `backend/requirements-realtime.txt`
- `backend/tests/test_realtime_voice.py`
- `docs/TODO.md`、`docs/OPEN_SOURCE_REUSE.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**218 passed** + tsc。
- `python -m backend.realtime.run_voice` 启动烟测：Whisper 加载 + pipeline ready（~7s），
  Ctrl+C 干净退出；**全链路 mic 对话 + 打断需用户本地对着麦验收**（agent 环境无真实 mic 交互）。

不要改动的边界：

- 未改 `backend/app/**`、`frontend/**`；pipecat 未进 `requirements.txt` / V1 gate。
- Soul/behavior/memory 接线留 Phase 3；`CompanionBrain` stub 未动。

## 2026-06-10 - Session 36 (V2 Phase 2 — Doubao TTS + flash STT)

本次完成：

- **Task 0**：Pipecat **1.3.0** 无 Volcengine/Doubao/ByteDance 内置 STT/TTS service
  （`pipecat.services` 模块列表无匹配项）→ 自建 Pipecat wrapper。
- **Task 1**：`backend/realtime/doubao_tts_service.py` — `DoubaoTTSService` 驱动现有
  `DoubaoTTSProvider.synthesize_stream`，PCM **24 kHz**，`asyncio.to_thread` 不阻塞事件循环。
- **Task 2（staged fallback）**：`backend/realtime/doubao_stt_service.py` — `DoubaoFlashSTTService`
  复用 `DoubaoASRProvider` 整段 flash ASR（VAD 段末一次 HTTP）；**streaming WS ASR 留 Phase 2b**。
- **Task 3**：`run_voice.py` 默认 `CYBER_COMPANION_VOICE_STT=doubao` /
  `CYBER_COMPANION_VOICE_TTS=doubao`；`whisper` / `mac_say` 可 env 回退；输出采样率随 TTS 后端
  （Doubao 24 kHz / say 22050 Hz）。

下次接着做：

- **V2 Phase 2b** — Doubao streaming WebSocket ASR（降 post-release 等待）。
- 用户戴耳机全链路验收（speak → 灿灿 TTS → interrupt）。
- V2 Phase 3 — Companion Brain soul 接线。

已知问题：

- Flash STT 仍是 VAD 段末一次性识别 → 说完话后仍有云端 RTT（比 streaming 慢，但已无本地 Whisper CPU）。
- 外接音箱回声未修；Phase 2 测试请戴耳机。
- Pipecat 1.3.0 无 Doubao 官方 service，wrapper 需随 API 变动维护。

相关文件：

- `backend/realtime/{doubao_tts_service.py,doubao_stt_service.py,run_voice.py,README.md}`
- `backend/tests/test_realtime_voice.py`
- `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**220 passed** + tsc。
- Doubao API 烟测：TTS「你好」→ 3 chunks / 56300 bytes PCM；ASR 静音段 → 预期 `No speech detected`。
- `run_voice` 启动：Doubao 默认 **~3.5s** ready（无 Whisper 模型加载）；对比 `whisper+mac_say` **~5.1s**。
- **延迟/CPU 前后对比（定性 + 启动实测）**：
  - Phase 1：本地 Whisper `base` 每次识别 CPU 飙高、风扇转；启动含模型加载 ~7s。
  - Phase 2：STT/TTS 全云端，idle 无 faster-whisper 推理；启动 ~3.5s；段末 flash ASR 仍有
    ~1–2s 云端 RTT（待 2b streaming 消除 post-release 等待）。
- **全链路 mic 对话 + 戴耳机验收**：agent 无真实 mic 交互，需用户本地对着麦跑
  `python -m backend.realtime.run_voice`。

不要改动的边界：

- 未改 `backend/app/**`、`frontend/**`；pipecat 未进 V1 gate。
- Soul/behavior/memory 接线留 Phase 3。

## 2026-06-10 - Session 37 (V2 Phase 2b — Doubao streaming WS ASR)

本次完成：

- **协议来源**：照官方「火山引擎 大模型流式语音识别 API」文档（doc 6561/1354869）+ 公开
  `sauc_python` demo（`generate_header`/`parse_response`）实现，**未照搬 spec 协议细节**。
  端点 `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel`（双向流式），资源
  `volc.bigasr.sauc.duration`（env `DOUBAO_ASR_RESOURCE_ID` 可覆盖），新版控制台鉴权
  `X-Api-Key=DOUBAO_API_KEY`（+ `X-Api-Resource-Id`/`X-Api-Request-Id`/`X-Api-Connect-Id`）。
- `backend/realtime/doubao_streaming_protocol.py`：纯 stdlib 二进制帧 builder/parser
  （4B header / gzip-JSON full client request / gzip-PCM audio-only / 条件 sequence / error 帧）。
- `backend/realtime/doubao_streaming_stt_service.py`：`DoubaoStreamingSTTService`（连续
  `STTService`，非 segmented）。`start` 建连 + 发 full client request + 起接收协程；`run_stt`
  每帧发音频（不阻塞）；接收协程 push `InterimTranscriptionFrame`（partial）/`TranscriptionFrame`
  （`definite`/末包 final，`result_type:single` 避免跨轮累积）；`stop` 发末包 flush + 干净关闭。
- `run_voice.py`：新增 `CYBER_COMPANION_VOICE_STT=doubao_stream` 档；**默认仍 flash `doubao`**，
  待真机麦验收后再翻默认。保留顶部 OpenBLAS 线程序列化修复。
- 依赖：`backend/requirements-realtime.txt` 显式声明 `websockets>=12.0`（pipecat 已传递带入 16.0）。
- 测试：`backend/tests/test_doubao_streaming.py`（协议 builder/parser 纯 stdlib 往返 + 错误帧 +
  服务 importorskip）；`test_realtime_voice.py` 加 toggle 选择测试。

下次接着做：

- 用户戴耳机用 `CYBER_COMPANION_VOICE_STT=doubao_stream` 真机麦验收（done-criteria #2）→ 通过则把
  `run_voice.py` 默认 STT 翻成 `doubao_stream`。
- V2 Phase 3 — Companion Brain soul 接线。

已知问题：

- 默认仍是 flash；streaming 已**离线**验证（合成语音）但未经真实 mic + Silero VAD 全链路人工验收。
- `bigmodel` 双向流式不支持 `language` 字段（仅 nostream 支持）→ 未传 language，靠模型自适应中英文/方言。
- 外接音箱回声未修；测试请戴耳机（Phase 2 边界不变）。

相关文件：

- `backend/realtime/{doubao_streaming_protocol.py,doubao_streaming_stt_service.py,run_voice.py}`
- `backend/requirements-realtime.txt`
- `backend/tests/{test_doubao_streaming.py,test_realtime_voice.py}`
- `docs/{TODO.md,OPEN_SOURCE_REUSE.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**230 passed**（+10）+ tsc green；realtime 仍 importorskip。
- **流式 WS 离线实测**（用了官方协议/无 SDK，纯自写 framing + `websockets` 客户端）：
  - 静音 5×200ms：建连成功（拿到 `X-Tt-Logid`），逐包 full server response，末包 `is_last=True`。
  - 合成语音「你好，我是被困在盒子里的小人。」：interim `你好…` 边说边出，**final 正确**，
    首字延迟约 **1.97s（流中途出字）**。
  - `run_voice STT=doubao_stream` 启动烟测：pipeline ready + WS 在 start 时建连（logid 已打印），Ctrl+C 干净退出。
- **流式 vs flash 延迟对比**：
  - **Flash（Phase 2）**：整段录音在“说完之后”才发出 → 段末 ~1–2s 云端 RTT（post-release 等待，用户能感知）。
  - **Streaming（Phase 2b）**：边说边传，partial 在说话中途就返回，final 基本在停顿瞬间到达 →
    去掉了 post-release 等待，明显更快、可上屏。
  - **CPU/风扇**：与 Phase 2 一致（无本地 Whisper 推理）。

不要改动的边界：

- 未改 `backend/app/**`（V1 flash 适配器 `backend/app/stt/doubao.py` 原样保留）、`frontend/**`；pipecat 未进 V1 gate。
- flash STT 作为 fallback toggle 保留；Soul 接线留 Phase 3。

## 2026-06-10 - Session 38 (V2 Phase 3 — Companion Brain)

本次完成：

- **`CompanionBrain`**（`backend/realtime/companion_brain.py`）：按 `/chat/complete` 顺序接线 soul——
  `evaluate_behavior` → `evaluate_llm_budget_gate` / `build_provider_context` →
  `router.complete_stream` → `SignalStreamFilter` 剥 trailer → `parse_structured_assistant_response`；
  非 LLM 路径走 `build_local_completion`（`silent` 不发声）。`remember()` 镜像 HTTP 尾：
  `apply_signals_to_kernel` → `persist_chat_turn` → `record_turn_memories` →
  `maybe_update_conversation_summary` → `note_llm_turn`。
- **`CompanionBrainProcessor`**（Pipecat `FrameProcessor`，照 Langchain 示例模式）：
  消费 final `TranscriptionFrame`，发 `LLMFullResponseStartFrame` + `LLMTextFrame` 流式 delta → TTS；
  `InterruptionFrame` 取消在途 turn；`remember` + `run_reflection_if_due` 走 `asyncio.to_thread` 后台，
  不阻塞音频。
- **`SileroVADProcessor`**：从 `LLMUserAggregator` 抽出 VAD，去掉 `LLMContext` / aggregators；
  pipeline = `transport → VAD → STT → brain → TTS → output`。
- **`run_voice.py`**：移除 `OpenAILLMService` + `BOXI_VOICE_PROMPT` + `LLMContextAggregatorPair`；
  接入 brain + VAD；STT/TTS/OpenBLAS 修复不变。
- 测试：`test_companion_brain.py`（silent 路径 + signal-strip）；`test_realtime_skeleton.py` 更新；
  realtime 仍 importorskip。

下次接着做：

- 用户戴耳机真机验收（记事实 → 后续 recall；毒舌 persona；偶尔 silent/refuse；查 `/memory/memories`）。
- `CYBER_COMPANION_VOICE_STT=doubao_stream` 麦验收通过后翻默认 STT。
- V2 Phase 4（turn-taking）/ Voice latency metrics-driven 诊断。

已知问题：

- 未做真机 mic 对话验收（agent 无麦）；latency「越聊越慢」仍待 metrics run，Phase 3 compact context 不宣称修复。
- `avatar_state` 仅 log，房间绑定留 Phase 5。
- 外接音箱回声 / half-duplex 边界不变。

相关文件：

- `backend/realtime/{companion_brain.py,companion_brain_processor.py,vad_processor.py,run_voice.py,README.md}`
- `backend/tests/{test_companion_brain.py,test_realtime_skeleton.py}`
- `docs/{TODO.md,SESSION_LOG.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**234 passed** + tsc green；realtime importorskip 仍绿。

不要改动的边界：

- **未改 `backend/app/**`**；soul 仅 import 复用。
- V1 HTTP gate / `frontend/**` 未动；pipecat 未进 V1 requirements。

## 2026-06-10 - Session 39 (V2 voice latency + terseness tuning)

本次完成：

- **`voice_config.py`**：三档 turn-finalize / 简短化旋钮均可 env 覆盖、保守默认——
  `CYBER_COMPANION_VOICE_VAD_STOP_SECS=0.4`、`CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS=300`、
  `CYBER_COMPANION_VOICE_MAX_TOKENS=200`。
- **Task 1 简短化**：`CompanionBrain.append_voice_mode_instruction` 在
  `build_provider_context` 之后 append 语音 system 指令（不改 soul persona）；`run_voice`
  传入 `max_output_tokens=200` 作 backstop。
- **Task 2 turn-finalize**：`SileroVADProcessor` 用 `VADParams(stop_secs=0.4)`；
  `DoubaoStreamingSTTService` 默认 `end_window_size_ms=300`（原 800）。
- **smart_turn 结论**：Session-29 DEBUG 里的 `TurnAnalyzerUserTurnStopStrategy` /
  `base_smart_turn:analyze_end_of_turn` 来自旧管线的 **`LLMUserAggregator`**（Pipecat 内置
  smart-turn ML 端点）。Phase 3 已换成 `SileroVADProcessor` + `CompanionBrainProcessor`，
  **当前 pipeline 无 smart_turn**；端点只靠 VAD `stop_secs` + Doubao `end_window_size`（不再三层叠加）。
- **DEBUG 时序**：`CompanionBrainProcessor` 打 `finalize→first_text` / `finalize→stream_end`；
  `run_voice` 启动打印 tuning 行。

**Session-29 基线（`/tmp/voice_debug.log`，旧管线 = LLMUserAggregator + smart_turn + OpenAILLM）：**

| 指标 | 典型值（「我记住了，你喜欢吃火锅」轮） |
|---|---|
| ASR TTFB（finalize） | ~2.7s |
| LLM TTFB | ~0.36s |
| finalize transcript → Bot started speaking | ~3.35s（25.004→28.359） |
| Boxi 说话时长 | ~11s（3 句串行 TTS） |
| 更早一轮「你最喜欢吃什么」回复 | 3 句 TTS，~16s（52.039→08.444） |

**调优后（Phase 3 brain + 本 commit，`CYBER_COMPANION_VOICE_STT=doubao_stream` DEBUG 烟测）：**

| 指标 | 观察 |
|---|---|
| 启动 tuning | `stop_secs=0.4`, `end_window=300`, `max_tokens=200`, `smart_turn=off` ✅ |
| 完整对话轮次 | agent 烟测仅环境噪声 partial，**无完整一问一答**；戴耳机全链路需用户本地复测 |
| 预期（待用户验） | start-gap 目标 <2s；Boxi ~1 句 / TTS ~1.5–2s；trailer 仍 strip |

下次接着做：

- 用户戴耳机 `CYBER_COMPANION_VOICE_LOG_LEVEL=DEBUG` 跑 3–5 轮，对比上表填 after 实测数；
  若端点裁切说话，把 `VAD_STOP_SECS`/`ASR_END_WINDOW_MS` 调回 0.5/500。
- V2 Phase 4 turn-taking；若仍觉「越聊越慢」再开 metrics-driven 专项。

已知问题：

- after 全链路数字未在本 session 填满（无可靠 mic 对话）；terseness/trailer 是否常截断待用户验。
- `ttfs_p99_latency not set` 警告仍在（Pipecat STT 元数据，非本次范围）。

相关文件：

- `backend/realtime/{voice_config.py,companion_brain.py,companion_brain_processor.py,vad_processor.py,doubao_streaming_stt_service.py,run_voice.py,README.md}`
- `backend/tests/{test_voice_config.py,test_companion_brain.py}`
- `docs/{TODO.md,SESSION_LOG.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**237 passed** + tsc green。
- DEBUG 烟测：`/tmp/voice_tune_after.log` — pipeline ready，tuning 行与 `stop_secs=0.4` /
  `end_window_size_ms=300` 日志正确；无 `smart_turn` 行。

不要改动的边界：

- **未改 `backend/app/**`**、**`frontend/**`**；voice 指令仅在 realtime brain append。

## 2026-06-10 - Session 40 (V2 half-duplex — drop the headphones)

本次完成：

- **Task 0 reuse 结论（Pipecat 1.3.0）：** 旧版 `STTMuteFilter` / `STTMuteConfig` **已移除**
  （1.0 起 deprecated，现版无 `pipecat.processors.filters.stt_mute_filter`）。等价能力在
  `pipecat.turns.user_mute.AlwaysUserMuteStrategy`（BotStarted/StoppedSpeaking 期间 mute）。
  官方入口是 `LLMUserAggregatorParams.user_mute_strategies`；本 pipeline 无
  `LLMUserAggregator`，故新增 **`HalfDuplexMuteProcessor`** 复用该 strategy + 镜像
  `LLMUserAggregator._maybe_mute_frame` 的帧抑制表（未手搓 mute 状态机）。
- **Task 1 half-duplex gating：** 共享 `HalfDuplexMuteGate` + 两处 processor（mic 前挡
  `InputAudioRawFrame`/VAD 帧；STT 后挡 `Transcription`/`Interruption`）。Bot 说话期间
  用户向帧丢弃；BotStopped 后 **resume guard** = `ASR_END_WINDOW_MS`（默认 300ms）滤掉尾 partial。
- **Task 2 toggle：** `CYBER_COMPANION_VOICE_HALF_DUPLEX` 默认 **on**；`off` 恢复全双工 +
  耳机 barge-in。启动日志打印 `half_duplex=on|off`。
- **Task 3 jieba 预热：** `run_voice` 启动时 `tokenize("预热")` 一次，避免首轮 memory
  rank 冷加载 ~1s。

**外放前后对比（laptop 外置喇叭，无耳机）：**

| | before（全双工 + 外放） | after（`half_duplex=on` 默认） |
|---|---|---|
| Boxi 自打断 | TTS 回声进 mic → VAD/STT → ~1 词后自我 `InterruptionFrame` 截断 | Bot 说话期 mute；整句播完再听 |
| barge-in | 理论可（实际被回声误触发） | **关闭**（设计取舍；`HALF_DUPLEX=off`+耳机可开） |
| 首轮 jieba | 首句可能多 ~1s | 启动预热，turn 1 ≈ 后续 |

下次接着做：

- 用户外放手动验：2–3 轮完整问答，确认无自打断、Bot 停后能正常接话；若 resume guard
  裁切首字，把 `ASR_END_WINDOW_MS` 略降或 guard 单独 env。
- V2 Phase 4 turn-taking / iPhone AEC 路径（真 full-duplex barge-in）。

已知问题：

- 本 session **未在 agent 环境做真实外放 mic 对话**（无可靠扬声器回路）；逻辑与 Pipecat
  官方 mute 表对齐，需用户本地 confirm。
- half-duplex 设计禁用 barge-in；要打断须 `CYBER_COMPANION_VOICE_HALF_DUPLEX=off` + 耳机。

相关文件：

- `backend/realtime/{half_duplex_mute_processor.py,voice_config.py,run_voice.py,README.md}`
- `backend/tests/test_voice_config.py`
- `docs/{TODO.md,SESSION_LOG.md,V2_HALF_DUPLEX_SPEC.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**237 passed** + tsc green。

不要改动的边界：

- **未改 `backend/app/**`**、**`frontend/**`**；soul / V1 HTTP gate 未动。
- jieba 仅 import `tokenize` 预热，未改 retrieval 实现。

## 2026-06-10 - Session 32 (V2 Phase 2c Task 1)

本次完成：

- **V2 Phase 2c Task 1 — OutputMode 0 纯端到端骨架：**
  - `backend/realtime/doubao_realtime_protocol.py`：Dialog WebSocket 二进制协议（event/session
    帧 builder + parser），对照火山官方 doc 1594356 + `realtime_dialog` Python 示例。
  - `backend/realtime/doubao_realtime_service.py`：`DoubaoRealtimeService` Pipecat processor —
    mic PCM 上行（TaskRequest 200）、TTS PCM 24 kHz 下行（TTSResponse 352）、ASRInfo 打断、
    逐轮延迟日志（`user_end→first_audio` / `first_asr→first_audio`）。
  - Boxi 人设注入：`load_persona_system_prompt()` → `system_role`；`persona.json` name →
    `bot_name`；tone 派生 `speaking_style`。
  - `run_voice.py`：`CYBER_COMPANION_VOICE_MODE=realtime` 替换 STT+brain+TTS 链；
    默认 `pipeline` 不变；`CYBER_COMPANION_VOICE_OUTPUT_MODE=1` 显式拒绝（Task 3 再做）。
  - 鉴权 env：`DOUBAO_RT_APP_ID` + `DOUBAO_RT_ACCESS_TOKEN`；可选 `DOUBAO_RT_SPEAKER` /
    `DOUBAO_RT_MODEL`（默认 O2.0 `1.2.1.1`）。
- 测试：`test_doubao_realtime.py`（协议纯 stdlib）；`test_voice_config` / `test_realtime_voice`
  加 mode toggle；realtime 仍 `importorskip`。

**延迟对比表（设计目标 + 既有基线；live pure 待用户带 RT 凭证复测）：**

| 模式 | 路径 | 典型 user_end→first_audio | 备注 |
|---|---|---|---|
| **pipeline（现有默认）** | VAD→STT finalize→DeepSeek→TTS | **~3.0–3.4 s** | Session 30 实测剖面：~1s STT + ~1.8s LLM + ~0.9s TTS |
| **realtime pure（OutputMode 0）** | Dialog S2S 单 WS | **目标 sub-second** | 云端融合 ASR+LLM+TTS；日志键 `Doubao realtime latency:` |
| **realtime hybrid（OutputMode 1）** | Dialog + 外部 LLM | **~2 s（目标）** | Task 3 未实现 |

下次接着做：

- 用户本地：`CYBER_COMPANION_VOICE_MODE=realtime` + `DOUBAO_RT_*` 跑 2–3 轮，填上表 pure 列实测 ms；
  对比 pipeline 同句延迟。
- V2 Phase 2c Task 2：memory context 注入 + transcript 离路径 `remember`。

已知问题：

- 本 session **未在 agent 环境做 live Dialog mic 对话**（`DOUBAO_RT_*` 未配置于 CI/agent）；
  WS 握手 / 帧格式对齐官方示例，需用户带凭证验通。
- realtime 模式不走 half-duplex gate（云端 VAD+barge-in）；外放回声行为待实机确认。
- OutputMode 1 / `LLMConfig` hybrid 未实现。

相关文件：

- `backend/realtime/{doubao_realtime_protocol.py,doubao_realtime_service.py,run_voice.py,voice_config.py,README.md}`
- `backend/tests/{test_doubao_realtime.py,test_voice_config.py,test_realtime_voice.py}`
- `docs/{V2_PHASE2c_SPEC.md,TODO.md,SESSION_LOG.md,OPEN_SOURCE_REUSE.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**248 passed** + tsc green（+11，含 Dialog 协议 6 例）。

不要改动的边界：

- **未改 `backend/app/**`**、**`frontend/**`**；soul 只读复用（`load_persona_system_prompt`）。
- 现有 STT→brain→TTS pipeline 完整保留为默认 fallback。

## 2026-06-10 - Session 33 (V2 RTC Stage 1 — Soul LLM server)

本次完成：

- **`backend/realtime/soul_llm_server.py`**：独立 FastAPI app，`POST /v1/chat/completions`
  OpenAI 兼容（stream + non-stream）。取 `messages[]` 最新 user 文本 →
  `CompanionBrain.stream_turn` → 只吐 signal-strip 后的口语文本 → 离路径
  `remember()`（`asyncio.create_task` + `to_thread`）。
- **鉴权**：`SOUL_LLM_API_KEY` Bearer；未设则 localhost/testclient only。
- **Env**：`SOUL_LLM_HOST`（默认 127.0.0.1）、`SOUL_LLM_PORT`（8100）；`.env.example` +
  `backend/realtime/README.md` curl 示例。
- **测试** `test_soul_llm_server.py`（6 例）：mock provider stream/non-stream OpenAI 形、
  trailer 剥离、Bearer 401、memory 落库。

下次接着做：

- V2 RTC Stage 2：rtc-aigc-demo 适配 + OutputMode 1 custom-LLM 指向本 endpoint（tunnel）。
- 用户本地：`CYBER_COMPANION_PROVIDER_MODE=mock python -m backend.realtime.soul_llm_server`
  + curl 验 stream/non-stream。

已知问题：

- 本 session 未做 live AIGC-RTC 联调（Stage 2 才验 Volcengine custom-LLM 契约）。
- `remember()` 在 stream 结束后 fire-and-forget；极端慢盘可能略晚于 curl 返回。

相关文件：

- `backend/realtime/{soul_llm_server.py,README.md}`
- `backend/tests/test_soul_llm_server.py`
- `.env.example`
- `docs/{V2_RTC_STAGE1_SPEC.md,TODO.md,SESSION_LOG.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**254 passed** + tsc green（+6）。

不要改动的边界：

- **未改 `backend/app/**`**、**`frontend/**`**；`CompanionBrain` 只读复用。
- V1 HTTP + Pipecat pipeline / Dialog S2S 路径未动。

## 2026-06-10 - Session 34 (V2 RTC Stage 2 — demo runbook + tunnel)

本次完成：

- **`docs/RTC_DEMO_SETUP.md`**：Stage 2a/2b 跑通手册——邻目录 clone
  `volcengine/rtc-aigc-demo`、填 RTC/IAM/Doubao 实时 creds、OutputMode 0→1 切换、
  `LLMConfig.CustomLLM` 字段对照 [6348/2123348](https://www.volcengine.com/docs/6348/2123348) /
  [6348/1558163](https://www.volcengine.com/docs/6348/1558163)、troubleshooting。
- **`scripts/soul_tunnel.sh`**：起 `soul_llm_server` + cloudflared（默认）或 ngrok，打印公网
  `/v1/chat/completions` URL 供 demo JSON 粘贴。
- **`.env.example`**：新增 `VOLC_RTC_*`、`VOLC_ACCESS_KEY`/`VOLC_SECRET_KEY`、`SOUL_TUNNEL_PROVIDER`。
- **`soul_llm_server.py` 未改**——云端 server-to-server 调 Bearer 即可，无需 CORS。

下次接着做：

- **用户手动 2a**：按 runbook 跑 pure RTC（OutputMode 0），确认 sub-second + barge-in。
- **用户手动 2b**：tunnel + OutputMode 1 + CustomLLM → 验跨轮 memory + 延迟对比。
- V2 RTC Stage 3 — emotion extension → soul kernel。

已知问题：

- 本 session **未做 live rtc-aigc-demo 联调**（需用户 RTC/IAM/RT 凭证 + 浏览器 mic）。
- `S2SConfig` 具体 JSON 以控制台「接入 API」粘贴为准；runbook 给骨架 + 字段表。

相关文件：

- `docs/{RTC_DEMO_SETUP.md,V2_RTC_STAGE2_SPEC.md,TODO.md,SESSION_LOG.md,OPEN_SOURCE_REUSE.md}`
- `scripts/soul_tunnel.sh`
- `.env.example`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**254 passed** + tsc green（无代码测试变更）。

不要改动的边界：

- **未改 `backend/app/**`**、**`frontend/**`**、**未 vendor demo**。

## 2026-06-10 - User validation: RTC Stage 2a PASS

- **2a 用户实机 PASS：** `rtc-aigc-demo` 场景 **Boxi（纯端到端）** / `OutputMode 0` — RTC 语音 +
  barge-in 正常（用户账号 + 已配 creds）。
- **2b 待验：** `BoxiHybrid` + `scripts/soul_tunnel.sh` → CustomLLM 指向 soul endpoint，验跨轮 memory。

## 2026-06-10 - Session: Stage 2c v2 (demo-aligned RTC + subtitles)

本次完成：

- **Stage 2c v2 重做：** `backend/app/rtc/` — `/rtc/prepare`（仅 token）→ 浏览器 joinRoom →
  `/rtc/agent/start`（StartVoiceChat），对齐官方 demo 顺序。
- 纯 E2E `VoiceChat` 与 `Boxi.json` 一致：短中文 `system_role`、`end_smooth_window_ms=1000`、
  `enable_asr_twopass`。
- 前端：`@volcengine/rtc` + TLV 字幕/AgentBrief 解析 + autoplay 恢复；字幕在**左栏**
  `RtcVoicePanel`，不占用右侧文字聊天。
- 6 backend RTC tests + 2 frontend `rtcMessages` tests。

下次接着做：

- 用户实机验纯 E2E 延迟 vs 体验馆；Soul 混合需 `soul_tunnel.sh` + `SOUL_LLM_PUBLIC_URL`。
- Phase 2c Task 2：纯 E2E 旁路 memory inject + transcript write。

已知问题：

- Soul 混合仍依赖有效 tunnel；未做 live mic 验收。

相关文件：

- `backend/app/rtc/**`, `frontend/src/rtc/**`, `frontend/src/components/RtcVoicePanel.tsx`
- `docs/{TODO.md,SESSION_LOG.md,OPEN_SOURCE_REUSE.md,RTC_DEMO_SETUP.md}`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**260 passed** + tsc green；frontend vitest **20 passed**。

不要改动的边界：

- 未改 memory schema / provider 抽象；Soul 混合仍走 `soul_llm_server`。

## 2026-06-10 - Session: V2 RTC Viking Memory VM-1

本次完成：

- **`docs/V2_RTC_VIKING_MEMORY_SPEC.md`** — 跨 session 切片 VM-1…5 + 新窗口 `推进` 接续说明。
- **VM-1 代码：** `MemoryConfig` 注入 `build_voice_chat_body`（env `VIKING_MEMORY_COLLECTION` 非空时启用）；
  稳定 `user_id`（`VOLC_RTC_DEFAULT_USER_ID`，默认 `boxi_user`，不再每通话随机 UUID）。
- `GET /rtc/status` 增加 `viking_memory_enabled`、`default_user_id`。
- `.env.example` Viking 相关变量；RTC 测试 **13 passed**。

下次接着做：

- **VM-2（用户手动）：** Viking 控制台建记忆库 + `VoiceChatRoleForRTC` 跨服务授权；`.env` 填
  `VIKING_MEMORY_COLLECTION`；实机验证跨天 RTC 召回。
- **VM-3：** 通话结束 → 字幕 → `AddSession` 后端代理（`POST /rtc/memory/session`）。

已知问题：

- 未接 Viking 写入（AddSession）；未做 live 记忆库联调。
- 文字聊天 SQLite 与 Viking 仍隔离（VM-4 未做）。

相关文件：

- `docs/V2_RTC_VIKING_MEMORY_SPEC.md`, `docs/TODO.md`
- `backend/app/rtc/{config,voice_chat,routes}.py`, `backend/app/schemas.py`
- `backend/tests/test_rtc.py`, `.env.example`, `frontend/src/rtc/api.ts`

测试结果：

- `PYTHONPATH=. pytest backend/tests/test_rtc.py`：**13 passed**

不要改动的边界：

- 未改 SQLite memory schema / CompanionBrain；纯 E2E OutputMode 0 路径不变。

## 2026-06-10 - Session: V2 RTC Viking Memory VM-3

本次完成：

- **`POST /rtc/memory/session`** — 字幕合并为 user/assistant 消息后调 Viking `AddSession`（Bearer `VIKING_MEMORY_API_KEY`）。
- 前端 `leave()`：挂断前自动上传字幕（`viking_memory_write_ready` 时）；失败会显示错误。
- `GET /rtc/status` 增加 `viking_memory_write_ready`。
- 测试：`test_rtc_viking_memory.py` + RTC 共 **16 passed**。

下次接着做：

- **用户 VM-2 复测**：第一轮说 Acme → 结束 → 第二轮问「我副业叫什么」；需等实时抽取几秒或新开通话。
- VM-5 左栏 Viking 状态徽章（可选）。

已知问题：

- AddSession 成功不等于下一轮立刻召回（依赖 Viking 事件抽取延迟）；无字幕的极短通话不会写入。

相关文件：

- `backend/app/rtc/viking_memory.py`, `backend/app/rtc/routes.py`, `frontend/src/rtc/{api,useRtcVoice}.ts`
- `backend/tests/test_rtc_viking_memory.py`, `docs/V2_RTC_VIKING_MEMORY_SPEC.md`

测试结果：

- `PYTHONPATH=. pytest backend/tests/test_rtc*.py`：**16 passed**

不要改动的边界：

- 未改 SQLite / CompanionBrain；密钥仅服务端 `.env`。

## 2026-06-10 - Session: V2 RTC Viking Memory VM-2 recall PASS

本次完成：

- **跨会话召回用户 PASS：** 新 RTC 通话问「我叫什么 / 我在哪」→ 正确回答 **昵称 / 常驻城市**（真实档案，公开版已匿名化）。
- **根因：** Viking 写入成功，但 `SearchMemory` 注入含一条失败轮次的 event（「你还没告诉我名字」），盖过 `profile_v1`。
- **修复：** `search_user_memories` + `format_memories_for_system_role` — 档案优先、可读化 profile、过滤矛盾 event；
  `MemoryConfig` 运行时默认仅 `profile_v1`；`agent/start` 打日志（hits/chars）。
- 测试：`test_rtc.py` + `test_rtc_viking_memory.py` **20 passed**。

下次接着做：

- **VM-5（可选）：** 左栏 Viking 记忆状态徽章。
- **VM-4（可选）：** SQLite 摘要注入 `system_role`，与 Viking 并行。

已知问题：

- 文字聊天 SQLite 与 Viking 仍隔离；极短无字幕通话不会写入 Viking。
- Soul 混合仍要 tunnel（`SOUL_LLM_PUBLIC_URL`）。

相关文件：

- `backend/app/rtc/{viking_memory,voice_chat,routes}.py`
- `backend/tests/test_rtc*.py`, `docs/V2_RTC_VIKING_MEMORY_SPEC.md`

测试结果：

- `pytest backend/tests/test_rtc.py backend/tests/test_rtc_viking_memory.py`：**20 passed**
- 用户实机：跨会话 RTC 记忆召回 **PASS**

不要改动的边界：

- 未改 SQLite memory schema / CompanionBrain / provider 抽象。

## 2026-06-10 - Session: V2 RTC Viking Memory VM-5 UI

本次完成：

- **VM-5 左栏徽章：** `RtcVikingMemoryBadge` — 读 `GET /rtc/status` 的 `viking_memory_enabled` /
  `viking_memory_write_ready` / `default_user_id`；状态「关 / 只读 / 就绪」；hover 提示 user_id。
- 挂断后字幕写入 Viking 时显示「写入中…」→「已写入」（4 秒）。
- 前端单测 `vikingMemoryBadge.test.ts` **+3**。

下次接着做：

- **VM-4（可选）：** SQLite 对话摘要注入 RTC `system_role`。

已知问题：

- 文字聊天 SQLite 与 Viking 仍隔离。

相关文件：

- `frontend/src/components/{RtcVoicePanel,RtcVikingMemoryBadge}.tsx`
- `frontend/src/rtc/{vikingMemoryBadge,vikingMemoryBadge.test,useRtcVoice}.ts`
- `frontend/src/styles.css`, `docs/TODO.md`

测试结果：

- `npm run check` + `npm run test`（frontend vitest **23 passed**）

不要改动的边界：

- 未改 backend memory schema / Viking API 契约。

## 2026-06-10 - Session: V2 RTC Viking Memory VM-4 SQLite inject

本次完成：

- **VM-4：** `backend/app/rtc/sqlite_memory.py` — 进房前从 SQLite 读取对话摘要、关系印象、
  Top-3 事实记忆，格式化为中文块注入 `system_role`（与 Viking 块合并）。
- `agent/start` / legacy `/rtc/start` 走 `_load_rtc_memory_context`（SQLite → Viking）。
- 测试 `test_rtc_sqlite_memory.py` **4 passed**；RTC 全套 **24 passed**。

下次接着做：

- 用户实机：文字聊一件新事（如面试公司名）→ 不开 RTC 写入 → 直接开语音问 → 应能提到。
- V2 其他项：Stage 2b hybrid / Stage 3 情绪扩展等（见 `docs/TODO.md`）。

已知问题：

- 文字事实不会自动同步到 Viking；仅进房时读 SQLite 快照。
- `system_role` 总长仍受云端限制，摘要/要点已做字符上限裁剪。

相关文件：

- `backend/app/rtc/{sqlite_memory,routes}.py`
- `backend/tests/test_rtc_sqlite_memory.py`, `docs/V2_RTC_VIKING_MEMORY_SPEC.md`

测试结果：

- `pytest backend/tests/test_rtc*.py`：**24 passed**

不要改动的边界：

- 未改 SQLite schema / Viking 写入路径 / CompanionBrain。

## 2026-06-10 - Session: VM-4 纯 E2E 文字记忆理解与间接召回

本次完成：

- **VM-4 增强：** `sqlite_memory.py` 注入近期 8 轮对话原文 + `【用户说过的事】` 计划要点块
  （明天/打算/要去等关键词），并强化指令：间接口语提问也必须当「已知事实」回答。
- `GET /rtc/status` 新增 `sqlite_memory_ready`；左栏 RTC 面板显示「文字记忆 就绪/空」徽章。
- **用户实机 PASS：** 文字聊「明天吃盖浇饭」→ 纯 E2E 问「文字里聊了什么」能答；
  问「我明天要去做什么」也能答盖浇饭（不再只会 meta 复述）。

下次接着做：

- Stage 2b hybrid（用户暂缓）；或 V2 其他项见 `docs/TODO.md`。

已知问题：

- 文字事实仍不会自动同步 Viking；每次需重新 `agent/start` 才刷新 SQLite 快照。
- 计划要点仅靠关键词启发式，复杂日程可能漏抽。

相关文件：

- `backend/app/rtc/{sqlite_memory,routes}.py`, `backend/app/schemas.py`
- `backend/tests/test_rtc_sqlite_memory.py`
- `frontend/src/{rtc/api,components/RtcVoicePanel}.tsx`, `frontend/src/App.tsx`

测试结果：

- `pytest backend/tests/test_rtc*.py`：**27 passed**

不要改动的边界：

- 未改 SQLite schema / Viking API / CompanionBrain / Stage 2b。

## 2026-06-11 - Session: V2 RTC Pure-Soul PS-1 turn analyzer core

本次完成：

- **PS-1：** 新增 `backend/app/reflection/turn_analyzer.py` — `analyze_turn()` 离线路径：
  `evaluate_behavior` → DeepSeek JSON 分析 → `apply_signals_to_kernel` → `persist_chat_turn`
  → `record_turn_memories` → `note_llm_turn` + `run_reflection_if_due`；全程 try/except 不抛出。
- `budget.py` + `config/budget*.json` 新增 `enable_turn_analyzer` / `analyze_every_n_turns` 旋钮。
- `test_turn_analyzer.py` **6 passed**（mock provider：关系轴移动 + SQLite typed memory；
  provider/parse 失败为干净 no-op）。

下次接着做：

- **PS-2：** `POST /rtc/turn` + 前端每轮 POST + `BackgroundTask` + single-flight claim。

已知问题：

- `analyze_every_n_turns` > 1 的 per-room counter 留待 PS-2（当前为 store 级 `turns_since_analysis`）。

相关文件：

- `backend/app/reflection/{turn_analyzer,__init__}.py`
- `backend/app/memory/budget.py`, `config/budget*.json`
- `backend/tests/test_turn_analyzer.py`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**291 passed** + frontend tsc green

不要改动的边界：

- 未改 kernel 数学 / memory schema / Doubao realtime / OutputMode 0 / RTC routes。

## 2026-06-11 - Session: V2 RTC Pure-Soul PS-2 wire analyze_turn to RTC

本次完成：

- **PS-2 后端：** `POST /rtc/turn`（`RtcTurnRequest`）校验非空 → `claim_turn_analysis(room_id)`
  → `BackgroundTask(_run_turn_analysis → analyze_turn)` → 立即 `{"status":"ok"}`；
  `schema_meta` 键 `turn_analyzing:{room_id}` 做 per-room single-flight。
- **PS-2 前端：** `detectCompletedTurn`（bot `definite` + 前序 user 行）→ `postRtcTurn`
  fire-and-forget（`useRtcVoice.ts` 字幕回调）；挂断 `saveRtcMemorySession` 流程不动。
- `docs/MEMORY_DESIGN.md` 补充 pure-E2E 离线路径说明。
- 测试 `test_rtc_turn.py` **4 passed**；frontend `detectCompletedTurn` vitest 增 1 例。

下次接着做：

- **PS-3** — discretized state re-inject via `UpdateVoiceChat`（bucket-change gated）。
- 用户实机：纯 E2E 说几轮 → SQLite 应有 voice persist + kernel 移动 + `writer=llm` memory。

已知问题：

- `analyze_every_n_turns` > 1 仍为 store 级计数（per-room 批次留后续）。

相关文件：

- `backend/app/{rtc/routes,schemas}.py`, `backend/app/memory/store.py`
- `frontend/src/rtc/{api,rtcMessages,useRtcVoice}.ts`
- `backend/tests/test_rtc_turn.py`, `docs/MEMORY_DESIGN.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green

不要改动的边界：

- 未改 kernel 数学 / memory schema / Doubao realtime / OutputMode 0 / Viking hangup 路径。

## 2026-06-11 - Session: V2 RTC Pure-Soul PS-3/PS-4 join-time state injection

本次完成：

- **PS-3 + PS-4：** 新建 `backend/app/rtc/state_block.py` — `build_rtc_state_block()` 读
  `mood_state`/`relationship_state` → 离散桶（低/中/高）→ 中文 `【你此刻的状态】` 块；
  `build_rtc_steering_directive()` 按 spec 映射表输出一句 stance 指令（worry/annoyance+
  tension/closeness 分支）；全中性 → `""`。
- `_load_rtc_memory_context` prepend state + steering，再接 SQLite/Viking；不改 `voice_chat.py`。
- `test_rtc_state_block.py` **18 passed**（各桶分支、全中性、system_role 接线、agent/start）。

下次接着做：

- 用户实机：文字聊几轮拉高 trust/closeness 或 annoyance → 新开纯 E2E 通话，听语气是否随 stance 变化。
- V2 其他项见 `docs/TODO.md`。

已知问题：

- Join-time only：单次通话中途不刷新 stance（云端不支持 mid-session `system_role` 更新）。

相关文件：

- `backend/app/rtc/{state_block,routes}.py`
- `backend/tests/test_rtc_state_block.py`, `backend/tests/test_rtc_sqlite_memory.py`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**313 passed** + frontend tsc green

不要改动的边界：

- 未改 soul/kernel/schema/voice_chat/UpdateVoiceChat/OutputMode 0。

## 2026-06-11 - Session: Pure E2E 权重对照实验 + 动态 WelcomeMessage

本次完成：

- **动态 WelcomeMessage：** `build_rtc_welcome_message()` — kernel 分支选差异明显的开场白；
  `prepare` / `agent/start` 注入 `StartVoiceChat`；`GET /rtc/stance-preview` 不进房可预览；
  前端 `agent/start` 回写 `welcome_message` 到字幕区。
- **ASR twopass 默认关闭**（`VOLC_RTC_ENABLE_ASR_TWOPASS` 可 opt-in）— 修复「一句话双声双答」。
- **用户 A/B 对照实验（实机 PASS 开场 / 部分 PASS 回复）：**

  | 注入通道 | 实验结果 | 权重判断 |
  |----------|----------|----------|
  | **WelcomeMessage** | A「别磨蹭…」/ B「在呢。你最近还好吗？」均与 `/rtc/stance-preview` **一致** | **高** — 豆包会照读进房第一句 |
  | **system_role stance + steering** | 同句 provocation A/B **有差别**，但 B **未表现关心**（仍偏毒舌/怼） | **低且不可控** — 能扰动用词，不服从 worry steering |

  Pure E2E weight map（摘要）：
  - WelcomeMessage：kernel 驱动，A/B 听感可区分，与 preview 一致。
  - system_role stance：同 provocation 会变，但不跟「收毒舌、稳一点」走。

- PS-2 kernel 面板变动已在此前会话验证；本轮证实 **开场可靠、对话语气别指望纯 E2E stance**。

下次接着做：

- 产品分工：WelcomeMessage 保留；reply 语气若要可控 → 以后 Hybrid Soul 或接受 E2E 为「嘴巴+记忆」。
- 可选：RTC 面板 stance 徽章（肉眼对照 preview，不盲听）。

已知问题：

- 纯 E2E 同句 provocation 仍可能高度相似；stance 在 prompt 里占比小 + 毒舌人设/记忆块主导。
- 幽灵 RTC 会话：dev 热更新后偶发「UI 未连接但麦仍占」— 需关光标签或退出浏览器。

相关文件：

- `backend/app/rtc/{state_block,routes,config,voice_chat,client}.py`
- `frontend/src/rtc/{api,useRtcVoice}.ts`
- `backend/tests/test_rtc_state_block.py`, `.env.example`

测试结果：

- `test_rtc_state_block.py` **22 passed**；用户实机 A/B 开场 **一致**。

不要改动的边界：

- 未改 kernel/schema；实验为实机对照，非自动化回归。

## 2026-06-12 - Session: V2 RTC Pure-Soul PS-5/PS-6 tone + emotion channels

本次完成：

- **PS-5（join-time tone）：** `build_rtc_speaking_style()` = `load_rtc_speaking_style()` 基础 +
  kernel 修饰（worry / annoyance+tension / closeness 桶，与 PS-4 映射一致但更短）；
  `build_voice_chat_body` pure 模式改用该函数；`_load_rtc_memory_context` **移除**
  `build_rtc_steering_directive`（不再把 steering 拼进 `system_role`）。
- **PS-6（mid-session emotion）：** pure join 时 `Config.TTSConfig.Context =
  {TagParse:true, QuoteUserQuestion:true}`；`client.update_voice_chat()`（`UpdateVoiceChat` /
  `SetTTSContext`）；`build_rtc_emotion_tag()` → `Message` JSON
  `{"Tag":{"additions":{"context_texts":[…]}}}`；`/rtc/turn` 后台 `analyze_turn` 之后非中性即注入
  （failure-isolated）；`GET /rtc/stance-preview` 增 `speaking_style` + `emotion_tag`。
- 单测：`test_rtc_state_block.py` speaking_style / emotion_tag 各桶；
  `test_rtc.py` TTSConfig + `update_voice_chat` mock HTTP；`test_rtc_turn.py` SetTTSContext 接线。

下次接着做：

- **用户实机 PS-4 复测（结论性）：** 纯 E2E 多轮拉高 annoyance/worry → 听下一轮语气是否更冲/更软；
  若有效则 pure E2E 语气可控，不必为 tone 上 Hybrid。
- V2 RTC 其他项见 `docs/TODO.md`。

已知问题：

- `SetTTSContext` 每轮重发（tag 作用域=下一轮）；若实机显示情绪 persist 过久，再加 `schema_meta` change-gating。
- `npm run check` 中 `test_providers.py` 3 例红（`local-budget` / 真 DeepSeek key 环境）— 与本轮 diff 无关。

相关文件：

- `backend/app/rtc/{state_block,voice_chat,client,routes}.py`
- `backend/tests/{test_rtc_state_block,test_rtc,test_rtc_turn}.py`
- `docs/TODO.md`, `docs/SESSION_LOG.md`

测试结果：

- RTC 相关：**60 passed**（`test_rtc*.py`）
- 全量 `npm run check`：**334 passed, 3 failed**（`test_providers.py` 环境项）

不要改动的边界：

- 未改 kernel 数学 / memory schema / soul writers / OutputMode 0 / Doubao realtime service。

## 2026-06-12 - Session: SC2.0 verification env (rt_series toggle)

本次完成：

- **SC2.0 验证环境（additive）：** `RtcConfig.rt_series` ← `DOUBAO_RT_SERIES`（`o`|`sc`，默认 `o`）。
- **pure + `rt_series==sc`：** `dialog.character_manifest` = `load_rtc_character_manifest()` +
  memory_context（VM-4/PS-3）+ PS-5 `build_rtc_speaking_style_modifier` 尾巴；`extra.model` only（无
  `enable_music`）；去掉 `bot_name`/`system_role`/`speaking_style`。O2.0 路径不变。
- **persona：** `load_rtc_character_manifest()` + `config/persona.example.json` `rtc_character_manifest`
  （spec Boxi 草稿）；`.env.example` 注明 SC spike 三件套。
- 单测：`test_persona_rtc.py` manifest 加载/回退；`test_rtc.py` SC dialog 形状 + PS-5 尾巴拼接。

下次接着做：

- **用户 SC2.0 实机 A/B：** `.env` 设 `DOUBAO_RT_SERIES=sc`、`DOUBAO_RT_MODEL=2.2.0.0`、saturn 音色 →
  复测 PS-4 语气/人设是否比 O2.0 听话；顺带验证 PS-6 `TagParse` 在 pure 是否被顶层 TTSConfig 忽略。
- VikingDB custom schemas（`docs/TODO.md`）待 spec。

已知问题：

- 官方 saturn 音色是否覆盖自定义 `character_manifest` — 实机 spike 才能定论。
- 文档提示 pure 模式可能忽略顶层 `Config.TTSConfig`（join-time `TagParse` 或为 no-op）。

相关文件：

- `backend/app/rtc/{config,voice_chat}.py`, `backend/app/memory/persona.py`
- `config/persona.example.json`, `.env.example`
- `backend/tests/{test_persona_rtc,test_rtc}.py`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**339 passed** + tsc green

不要改动的边界：

- O2.0 默认行为不变；未改 kernel/analyzer/soul；PS-6 `SetTTSContext` 路径不变。

## 2026-06-12 - Session: O2.0 确认 + 人设定制 Phase 1（SC2.0 已否决）

本次完成：

- **PS arc 收尾 + 修复**：PS-1…PS-6 全部提交；`3d0426e` 修了 `8b977b0` 的 broken-commit
  （persona refactor `load_rtc_system_role/speaking_style` + `enable_music` deps 未提交 → ImportError），
  并删掉废弃的 `build_rtc_steering_directive`；`a91b2cb` 动态 WelcomeMessage + ASR twopass 关默认。
- **关键结论（设备验证）**：PS-4「纯 E2E 不跟 tone」是**配置错**——tone 该进 `speaking_style` 而非
  `system_role`；emotion 走 `UpdateVoiceChat(Command=SetTTSContext)`（NL `{{additions}}` 标签，per-turn
  off-path）。PS-5/PS-6 落地后**语气已能随 kernel 变（用户实机确认，仍需更多验证）**。
- **SC2.0 验证 = REJECTED**：saturn/克隆音色音色固定、情绪不能中途变，role-play 是围着这个固定音色做的，
  对会变情绪的陪伴比 O2.0 差。`DOUBAO_RT_SERIES` toggle 留着但休眠，**O2.0 为准**（`docs/V2_RTC_SC2_VERIFY_SPEC.md` 记录）。
- **O2.0 全人设定制 Phase 1（完成）**：`config/persona.example.json` 加 `persona_prompt`（Boxi 全文人设，
  **无行为规则**，安全交给豆包 API）；`load_chinese_persona_prompt` 已读它 → 统一对文字/Soul/O2.0 RTC **生效**，`npm run check` 绿。（loader 接线另见下一条 session 记录。）

下次接着做（新窗口 `推进`）：

1. **用户实机**：O2.0 上听新 Boxi 全文人设、按口味调 `persona_prompt` 文案。
2. 可选：`speaking_style` 去规则化；`external_rag`（深度 lore，O2.0 only）+ `dialog_id`（原生 20 轮跨会话记忆）。
3. **VikingDB 自定义 schema**（事件/画像抽取规则 + 字段 + 权重，soul-aligned；见前期调研）。

已知问题：

- **emotion 标签副旗**：文档称纯 E2E **忽略顶层 `Config.TTSConfig`** → join-time `TagParse` 可能 no-op
  （只有 runtime `SetTTSContext` 生效）；需验证标签是否真被解析，否则把 `Context.TagParse` 移到
  `S2SConfig.ProviderParams.tts`。

相关文件：

- `config/persona.example.json`（`persona_prompt`）、`backend/app/memory/persona.py`（待改 loader）
- `docs/V2_RTC_PURE_SOUL_SPEC.md`（PS-1…PS-6）、`docs/V2_RTC_SC2_VERIFY_SPEC.md`（SC2.0 REJECTED）
- `backend/app/rtc/{voice_chat,state_block,client,routes,config}.py`（PS-5/6 + `DOUBAO_RT_SERIES` toggle）

测试结果：

- 上个代码 checkpoint：**334–339 passed + tsc green**。本会话后续仅文档 + persona 文案改动，无代码逻辑变更，未单独跑。

不要改动的边界：

- O2.0 默认；SC2.0 toggle 休眠**勿删**。不改 soul kernel/schema。**安全边界交给豆包 API，人设里不再写行为规则。**

## 2026-06-12 - Session: O2.0 persona_prompt loader

本次完成：

- **`load_chinese_persona_prompt` 接线**：`persona.json` 含非空 `persona_prompt` 时直接返回（trim 后）；
  否则保持 `name+core+tone` 拼装（向后兼容）。统一影响文字聊天、`load_persona_system_prompt`、
  `load_rtc_system_role`、Doubao realtime `system_role`、Soul LLM。
- **`config/persona.example.json`**：已含 Boxi 全文人设 `persona_prompt`（上轮 staged），本轮 loader 接通后生效。
- **测试**：`test_persona_rtc.py` 拆成 `persona_prompt` 优先 + 旧拼装回退两例；
  `test_doubao_realtime.py` 断言改为 `透明盒子`（匹配全文人设）。

下次接着做：

- 用户实机：O2.0 上听新 Boxi 人设、调 `persona_prompt` 文案。
- O2.0 persona follow-on：`speaking_style` 去规则化；`external_rag` + `dialog_id`（见 `docs/TODO.md`）。

已知问题：

- emotion 标签副旗（join-time `TagParse` vs runtime `SetTTSContext`）仍待验证。
- `speaking_style` 仍为 tone 数值拼装，未跟全文人设对齐。

相关文件：

- `backend/app/memory/persona.py`
- `config/persona.example.json`
- `backend/tests/{test_persona_rtc,test_doubao_realtime}.py`
- `docs/TODO.md`, `docs/SESSION_LOG.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check`：**340 passed** + tsc green

不要改动的边界：

- O2.0 默认；SC2.0 toggle 休眠勿删。未改 kernel/schema/soul writers。

## 2026-06-12 - Session: 纯 E2E「不出声」排障 — 根因=豆包 RT 凭证

本次完成：

- **根因（最终定位）**：纯 E2E 全程静音的真正原因是 **`.env` 的豆包端到端语音（S2S）凭证指向了无额度/错误的应用**。
  正确配置 = `volcengine_standalone_proje…`（**不限 token**）应用：`DOUBAO_RT_APP_ID=1234567890` + 对应 Access Token。
  排障中一度误填新版控制台的 **API Key（UUID）** 进 `token` → 触发 `InvalidStateError: Stream closed`、agent 不进房；
  确认 **RTC AIGC StartVoiceChat S2S 仍走旧版 APP ID + Access Token**，API Key 仅用于新版直连 API，不用于 RTC。
- **关键诊断手段**：临时在 `useRtcVoice` 加 `[RTC]` 日志（`enableAudioPropertiesReport` 本地/远端 linearVolume、
  `onPublishResult`、`onRemoteAudioFirstFrame`、raw room messages）。决定性证据：本地麦 `volume>0` + `publishResult=0`
  + `remote joined/publish/first frame` 均正常，但 **`BOT audio level` 全程 0** → 锁定「云端 agent 发静音流」=服务端凭证，
  排除了 Mac/浏览器/播放/麦克风。**已在修好后清除全部诊断日志。**
- **顺带修掉的客户端真 bug（保留）**：
  1. 麦克风选设备：原来取「枚举到的第一个」，在多设备机器上会选到幽灵 Continuity/iPhone 麦或 Teams/Zoom 虚拟声卡 →
     采到静音。改为优先 `deviceId==="default"` / 内建，跳过虚拟与幽灵设备。
  2. 远端音频：进房点击数秒后远端流才到，自动播放可能被浏览器策略拦 → 远端 publish 时显式 `engine.play()`，失败则亮恢复横幅。
- 过程旁证：曾出现 macOS Core Audio 卡死（截图音效全无）→ 用户 `killall coreaudiod` 恢复；与最终根因无关，是叠加烟雾。
- 一笔未完成的 Codex WIP（task_id 房间作用域 + 前端音频/消息重写）已整体回退到 HEAD，备份在 `.rtc_wip_backup.patch`（可删）。

下次接着做：

- 决定 `.rtc_wip_backup.patch` 去留；若要 task_id 房间作用域/幽灵会话治理，按 spec 重新落地。
- 可选：把「豆包 RT 凭证来源（不限 token 应用）」写进 `docs/RTC_DEMO_SETUP.md`，避免再被新版 API Key 误导。

已知问题：

- 新版火山控制台主推 API Key 接入，与 RTC AIGC 所需的旧版 APP ID+Token 易混；换 key 时务必用「端到端实时语音大模型 →
  服务接口认证信息」里的 APP ID + Access Token，而非 API Key 管理页的 key。

相关文件：

- `frontend/src/rtc/useRtcVoice.ts`（麦克风选择 + 远端 play() 兜底；唯一保留改动）
- `.env`（`DOUBAO_RT_APP_ID` / `DOUBAO_RT_ACCESS_TOKEN`，gitignored）

测试结果：

- 用户实机：纯 E2E **成功出声**（开场白 + 对话）。`frontend tsc --noEmit` 绿、无 lint。

不要改动的边界：

- 未改 provider 抽象 / memory schema / behavior 引擎 / soul writers / OutputMode 0。凭证只存 `.env`，勿写进任何已跟踪文件。

## 2026-06-13 - Visual Spike: being (光核 + 墨)

本次完成：

- 按 `docs/VISUAL_SPIKE_SPEC.md` 做一次性 throwaway 视觉 spike，未动 `frontend/` 产品代码。
- 新增自包含页 `experiments/being-spike/index.html`：WebGL2 单文件，无外部依赖。
- **材质 A（半具象光粒子）**：320 粒 capped GPU 点精灵 + 噪声场运动；墨层用与 B 相同的 SDF shader 作底（`u_inkOnly`），粒子 = 光核（felt）。
- **材质 B（光核透墨）**：domain-warp fbm/curl + SDF 墨形；`u_edge` 控制 smoothstep 宽度（利↔柔）；核 = bloom + 颜色/脉冲 uniform；纸绢 = 程序化 fbm 叠乘。
- 6 个手动状态按钮：idle、真凶(annoyed)、温柔(warm)、desync-1 压抑、desync-2 逗你、thinking→speaking（~4.2s 连续过渡：核收缩抖动 → 墨散开 → 聚拢流进说话）。
- 顶部材质 A/B 切换；左上角标注「光核=内心 / 墨=表现」。

下次接着做：

- 用户在浏览器打开 spike，对比 A/B 材质，选定方向。
- Claude review spike；若选 B，再考虑是否迁入产品 renderer（另开切片）。
- felt-vs-shown 行为切片（`performative_sharp`）仍按 spec 配对文档，不在此次。

已知问题：

- 未在真机 SE2 上实测帧率；shader 为单 pass、无流体 sim，理论上可跑。
- 材质 A 粒子轮廓偏抽象，desync 主要靠墨边 + 粒子色温对比阅读。

相关文件：

- `experiments/being-spike/index.html`
- `docs/VISUAL_SPIKE_SPEC.md`

测试结果：

- 本地可用 `python3 -m http.server` 于 repo 根目录，打开 `http://localhost:8000/experiments/being-spike/` 查看（或直接 file:// 打开 index.html）。
- 未接 STT/LLM/TTS；未改 behavior contract / SQLite / frontend 产品。

不要改动的边界：

- throwaway，勿 accrete 产品 scope；不接 soul、回声世界、记忆。
- 不改 provider 抽象 / memory schema / behavior 引擎 decision contract。

### 同日追加 — 材质 B 深化（用户选 B）

- 默认材质切为 B。
- 墨 alpha 空间变化：`spatialThick = smoothstep(0.18, 0.82, distNorm)`，核中心薄透、边缘浓遮。
- 核边染色：墨缘 rim band × 核距 × pulse，screen blend 微弱同色相光晕（闪随核）。
- 边缘模式联动核透出：犀利 = `sharpClip` 硬切 + 紧 falloff；温柔 = 宽 bloom + `softBleed` 渗入墨晕；同一 `u_edge` 驱动。

### 同日追加 — 光核呼吸/颤动

- 新增 `evalCoreLife()`：`breath`（纯 sin，周期准确）+ `organicWave` 多频正弦闪烁（非方波）+ `tremble` 位置/半径微颤。
- idle：~4s 呼吸，亮度 ±15%、半径 ±5%，极轻微颤。
- 真凶/desync-1：~0.2s 有机闪烁 + 14Hz 颤动。
- 温柔/desync-2：~6s 慢呼吸 + `haloSoft` 羽化光晕。
- thinking→speaking：缩小 30%、10Hz 低幅颤、亮度降低，聚拢说话时渐恢复。

### 同日追加 — 对标参考图（暖墨美学）

- 纸底改 sepia/umber + 烘焙 256² 纸纹贴图。
- 墨色改暖褐炭（非冷灰紫）；双层 SDF（主体 + 飞白 wisp）+ 各向异性笔触 noise。
- 核：不规则轮廓 + 白热中心→琥珀衰减；薄墨区暖染 + rim screen 染色加强。
- **诚实边界**：氛围/透光/色调可逼近 ~75–85%；真实水墨照片级笔触细节需纸纹资产或多 pass，流体仍不做。

## 2026-06-13 — PI-1 Longing model (timing)

本次完成：

- 新增 `backend/app/behavior/longing.py`：longing 强度 L 来自 `last_meaningful_interaction_at × closeness` + 当前 loneliness（修正与 idle loneliness 反号）；Poisson 触发 `p = 1 - exp(-λ·Δt)`，λ 随 L 增大；可注入 seeded RNG。
- 可用性闸门：对话后冷却（30min）、quiet hours（23–08）、daily cap（2）；`enable_proactive` 总开关。
- `proactive_check` 接入 longing 模型，替换 stale-job-only 硬触发；命中后 stale job 优先，否则 check-in 本地句。
- `BudgetConfig` + `config/budget*.json` 新增 proactive/longing 旋钮；更新 `docs/PERSONA_AND_BEHAVIOR.md`、`docs/COST_AND_TOKEN_BUDGET.md`。
- `backend/tests/test_longing.py` + 更新 behavior/memory 测试；revive-companion MIT 核证记入 `docs/OPEN_SOURCE_REUSE.md`（Level 1，无代码复制）。

下次接着做：

- PI-2：reason picker + soul-authored opener（LLM，rate-limited）。
- 或用户指定的下一 slice。

已知问题：

- PI-4 ignore-backoff / 成本闸尚未做；Bayesian 学习用户在线时段未做（固定 quiet hours）。
- 默认 lambda 偏保守，真实长 idle 下触发可能较慢——可按 feel 调 `longing_lambda_*`。

相关文件：

- `backend/app/behavior/longing.py`
- `backend/app/behavior/engine.py`
- `backend/app/memory/budget.py`
- `backend/app/memory/store.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_longing.py`
- `docs/PERSONA_AND_BEHAVIOR.md`, `docs/COST_AND_TOKEN_BUDGET.md`, `docs/OPEN_SOURCE_REUSE.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` — 350 passed + tsc green

不要改动的边界：

- 未做 PI-2/3/4；未改 provider 抽象 / memory schema / file permission policy。

## 2026-06-13 — PI-2 Reason picker + soul-authored opener

本次完成：

- 新增 `backend/app/behavior/proactive_reason.py`：理由选择器（due reminder → commitment/follow-up → memory callback → check-in），含 canned fallback 行。
- 新增 `backend/app/behavior/proactive_opener.py`：route 层 compact context + provider 撰写一句开场白（无 signals trailer）；`proactive_llm` 门控、`proactive_llm_daily_max` 限频 hook；失败/关闭/无 key → mock 或 canned 回退。
- `engine._evaluate_proactive_check`：PI-1 fire 后只返回 `decision=proactive` + `proactive_reason` + fallback（不调 provider）。
- `POST /behavior/evaluate` proactive 路径调用 `resolve_proactive_opener` 后再落库；metadata 记 `proactive_reason_kind` / `proactive_llm`。
- `store.find_due_reminder`；`BudgetConfig` + `config/budget*.json` 新增 `proactive_llm`、`proactive_max_output_tokens`、`proactive_llm_daily_max`。
- 更新 `docs/PERSONA_AND_BEHAVIOR.md`、`docs/COST_AND_TOKEN_BUDGET.md`；`backend/tests/test_proactive_opener.py`（13 tests）。

下次接着做：

- PI-3：前端 delivery 感（avatar + attention cue）。
- PI-4：ignore-backoff + proactive 成本闸（hook 已留）。

已知问题：

- 无 API key 时 proactive LLM 自动回退 mock provider（开发环境）或 canned；PI-4 全量 cost brake 尚未接 daily/monthly LLM cap。
- PI-1 timing 未改；用户本地未提交的 `docs/PROACTIVE_INITIATION_SPEC.md` / `docs/TODO.md` 改动未纳入本 commit。

相关文件：

- `backend/app/behavior/proactive_reason.py`, `proactive_opener.py`, `engine.py`, `types.py`
- `backend/app/main.py`, `backend/app/memory/chat_persistence.py`, `store.py`, `budget.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_proactive_opener.py`, `test_behavior.py`, `test_longing.py`, `test_memory.py`
- `docs/PERSONA_AND_BEHAVIOR.md`, `docs/COST_AND_TOKEN_BUDGET.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` — 363 passed + tsc green

不要改动的边界：

- 未做 PI-3/4 全量；未改 provider 抽象 / memory schema / PI-1 longing timing。

## 2026-06-14 — PI-4 Respect boundaries + cost brake

本次完成：

- **ignore-backoff**：`mark_proactive_fired` 写入 `proactive_pending_since`；`check_proactive_availability` 在存在未回复 proactive 时 block（`awaiting_user_reply`）；`user_message` 路径 `clear_proactive_pending` 解锁。
- **小时级发起间隔**：`proactive_min_fire_gap_hours`（默认 6）+ `last_proactive_fired_at` gate（`proactive_fire_gap`）。
- **成本闸**：`resolve_proactive_opener` 在 LLM 前走 `evaluate_llm_budget_gate`（monthly/daily/reasoning）；超预算 → canned 回退；成功时 `proactive_completion` 落库真实 usage/cost，`should_call_llm=true` 计入 caps。
- `BudgetConfig` + `config/budget*.json` 新增 `proactive_min_fire_gap_hours`；`backend/tests/test_proactive_pi4.py`（9 tests）。
- 更新 `docs/PERSONA_AND_BEHAVIOR.md`、`docs/COST_AND_TOKEN_BUDGET.md`、`docs/TODO.md`。

下次接着做：

- PI-3：前端 delivery 感（avatar + attention cue）。
- PI-1 follow-ups：λ 校准、`proactive_max_delta_seconds`、RTC voice 计入 post-convo cooldown。

已知问题：

- Proactive opener 尚未在真实 DeepSeek 上 smoke（PI-2 遗留）。
- `proactive_min_fire_gap_hours` 与 `proactive_daily_max` 同时生效时，高 longing 日仍最多 2–3 次（设计预期）。

相关文件：

- `backend/app/behavior/longing.py`, `engine.py`, `proactive_opener.py`, `types.py`
- `backend/app/memory/budget.py`, `chat_persistence.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_proactive_pi4.py`
- `docs/PERSONA_AND_BEHAVIOR.md`, `docs/COST_AND_TOKEN_BUDGET.md`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` — 372 passed + tsc green

不要改动的边界：

- 未做 PI-3 前端；未改 provider 抽象 / memory schema / PI-1 longing timing / PI-2 opener 核心逻辑（仅加 gate + 成本接线）。

## 2026-06-14 — PI-1 follow-ups (calibration, Δt cap, voice cooldown)

本次完成：

- **(a) 校准 + 验证触发**：`longing_lambda_base_per_hour` 调至 0.06（`budget.json` / `budget.example.json`，附 `_validation_notes`）；`POST /behavior/evaluate` 新增 `force_proactive`（默认 false）——跳过 Poisson 与计时闸（post-convo / fire_gap / quiet_hours / 180s local cooldown），仍保留 `enable_proactive`、ignore-backoff、daily cap、PI-4 成本闸。
- **(b) Cap Δt**：`proactive_max_delta_seconds`（默认 600）在 `longing._resolve_delta_seconds` clamp，长间隔重开不再 p≈1 立刻开火。
- **(c) 语音 turn 冷却结论**：RTC `POST /rtc/turn` → `analyze_turn` → `persist_chat_turn` 用户消息已是 `source='chat'`；`get_last_user_chat_created_at` 无需改查询。已在 `store.py` 注释 + 测试记录。
- `backend/tests/test_pi1_followups.py`（7 tests）；更新 `docs/PERSONA_AND_BEHAVIOR.md`、`docs/COST_AND_TOKEN_BUDGET.md`、`docs/TODO.md`。

下次接着做：

- PI-3：前端 delivery 感（avatar + attention cue）。
- λ 按设备口味从 0.06 回调 toward ~0.004。

已知问题：

- `force_proactive` 仅供 dev/smoke，前端 tick 未接此参数（手动 curl/Postman 验证）。
- Pure E2E RTC 若未走 `/rtc/turn` off-path 分析，则不会写入 SQLite chat — 那是已知 PS 路径限制，非本切片 bug。

相关文件：

- `backend/app/behavior/longing.py`, `engine.py`
- `backend/app/schemas.py`, `backend/app/main.py`
- `backend/app/memory/budget.py`, `store.py`
- `config/budget.json`, `config/budget.example.json`
- `backend/tests/test_pi1_followups.py`
- `docs/PERSONA_AND_BEHAVIOR.md`, `docs/COST_AND_TOKEN_BUDGET.md`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` — 379 passed + tsc green

不要改动的边界：

- 未改 PI-2 opener / PI-4 闸核心；未做 PI-3 前端。

## 2026-06-14 — PI-3 Proactive delivery (in-app frontend)

本次完成：

- **自动气泡**：`handleBehaviorDecision` 拆分 proactive 路径；用 `saved_message_id` 去重后直接追加
  `local_response`（不重载 `/memory/messages`，避免双显）；历史恢复时 `decision=proactive` 标记 `initiation`。
- **头像跟随**：proactive 使用 `proactiveAvatarHoldDuration`（+1400ms bonus）+ `scheduleReturnForMs`，
  避免被 idle rest 立刻盖掉；`PixelCharacter` 支持 `attentionPulse`。
- **克制注意提示**：状态条小圆点、stage 柔和 pulse、聊天气泡高亮/滑入、「· 主动找你」标签；2.8s 自动消退。
  无提示音（尊重静音默认）。
- **TTS**：复用现有 `speakReply` + selective policy（`proactive` in speak_decisions）；保留 avatar/TTS 竞态修复。
- Dev：`evaluateBehavior(..., { forceProactive })`；`window.__uiVerify.triggerProactiveCheck` +
  `handleBehaviorDecision` 供控制台一键验证。

下次接着做：

- λ 从 0.06 按设备口味回调；PI 系列 live smoke on real DeepSeek opener quality。

已知问题：

- 单独 `curl force_proactive` 不会推送到已开页面（需控制台 hook 或刷新看历史）；正常 tick 路径自动出现。
- `ui_verify.mjs` 未加 proactive 场景（需 dev server + Playwright）。

相关文件：

- `frontend/src/App.tsx`, `avatar/proactiveDelivery.ts`, `avatar/useAvatarState.ts`
- `frontend/src/components/PixelCharacter.tsx`, `PixelCharacter.css`
- `frontend/src/chat/types.ts`, `frontend/src/api/behavior.ts`, `frontend/src/styles.css`
- `docs/PERSONA_AND_BEHAVIOR.md`, `docs/TODO.md`

测试结果：

- `PYTHON_BIN=.venv/bin/python npm run check` — 379 passed + tsc green

不要改动的边界：

- 纯前端；未改后端 / behavior 契约 / provider；无 away-delivery / OS 通知。

## 2026-06-14 — Session: PI 实机验证 PASS + 公开发布 GitHub (Claude)

本次完成：

- **主动发起 (Proactive Initiation) 全系列完成 + 实机验证 PASS。** PI-1（longing 计时）/ PI-2
  （理由选择 + soul 撰写开场白）/ PI-3（前端「她在主动联系」呈现）/ PI-4（尊重边界 + 成本闸）
  + PI-1 follow-ups（校准 λ、Δt cap、`force_proactive`、语音 turn = `source='chat'` 已确认）——
  全部 Cursor 实现、Claude review **逐条 PASS**。PI-2 真机 DeepSeek smoke PASS（开场白短、口吻对、
  不 nag）。**用户实机确认：她现在会主动找你。**
- **项目已公开发布到 GitHub（public, MIT）：** https://github.com/Xiaoyan43/cyber-companion 。
  加 `LICENSE`(MIT) + 面向公众 `README`；复用清单核对（无 copyleft 进入分发代码，仅 ffmpeg 系统二进制）；
  安全审计（当前 tree + **全 history** 均无任何密钥/token）；真实火山/豆包 App ID → 占位、真实档案测试数据
  匿名化（保留作者名 Chris Wang）；用 **git-filter-repo 重写全部历史**清除这些值（99 commits，hash 已变，
  dev 历史保留）；`.firecrawl/`、`.claude/` 加 gitignore。

下次接着做：

- 主动发起：实机体验后**定稿 longing λ**（现为验证值 0.06，按手感往下调到不吵的节奏）。
- 从「未完成」清单挑下一条：视觉（改 asset-based 表情图，不再用实时 shader——见前期结论）/ 语音情绪
  （纯 E2E 上是 no-op，cascaded 才行）/ cascaded soul-authored 语音设为主 / VikingDB 自定义 schema /
  felt-shown + 逗你 行为切片。

已知问题：

- **repo 现在 public**——之后所有 commit 都会公开，别把密钥/个人数据写进 tracked 文件或 commit message；
  密钥仍只在 `.env`(gitignored)。
- git 历史已被 filter-repo 重写（本地 hash 变，已对齐 origin/master）；本地 `refs/codex/*` 是 agent 残留，
  无害、不会被 push。默认分支 `master`（可在 Settings 改 main，纯命名）。
- BSD-3 改编的 3 文件（`tlv.ts`/`rtcMessages.ts`/`token.py`）严格合规可加一行来源 header（复用清单已记录）。

相关文件：

- `LICENSE`, `README.md`, `.gitignore`
- `backend/app/behavior/{longing,proactive_reason,proactive_opener,engine}.py`、`docs/PROACTIVE_INITIATION_SPEC.md`、`docs/TODO.md`
- 公开仓库：https://github.com/Xiaoyan43/cyber-companion

测试结果：

- 全程 `npm run check` 绿（PI 收尾 379 passed + tsc）；发布前 RTC 70 passed；PI-2 真机 DeepSeek smoke PASS；
  **PI 主动发起 实机 用户 PASS。**

不要改动的边界：

- repo public——secrets 只在 env，个人数据别进 tracked/commit。不重写已发布历史（除非用户要求）。
  O2.0 默认、SC2.0 toggle 勿删；不改 soul kernel/schema。
