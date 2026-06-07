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
