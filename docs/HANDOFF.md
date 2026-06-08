# Handoff For Claude Code And Cursor

## Current State

This repository has a large uncommitted MVP batch on top of baseline commit `d7d225f`.

Implemented in the working tree:

- Phase 2 pixel character UI and avatar state animations.
- Phase 3 provider abstraction with mock, DeepSeek, OpenAI placeholder, and local placeholder.
- Phase 4 SQLite memory schema and CRUD.
- Phase 5 compact memory retrieval and summary policy.
- Phase 6 behavior engine with local reply/silent/refuse/interrupt/proactive decisions.
- Phase 7 file permission gateway for explicit allowed folders only.
- Phase 8 text MVP integration: backend chat route, persisted messages, compact context, avatar state, usage/cost metadata.
- Phase 9 push-to-talk STT mock flow and cloud placeholder gated by config/budget.
- Phase 10 selective TTS mock flow and cloud placeholder gated by config/budget.

Latest verified checks:

```bash
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

Both passed after Session 23. Backend tests: 68 passing; frontend `tsc --noEmit` and Vite 6.4.x production build pass. `npm audit` reports 0 vulnerabilities (dev and prod).

`node scripts/ui_verify.mjs` has a passing API section, but full browser smoke needs Playwright browser binaries installed locally. Do not install/download browsers unless the user approves.

## Ownership Model

Cursor should own about 80-90% of routine implementation:

- UI polish.
- CSS and animation timing.
- Small frontend components.
- Narrow integration wiring.
- Focused bug fixes with tests.

Claude Code should act mainly as reviewer and critic:

- Architecture review.
- Security review.
- Memory quality review.
- Behavior/personality review.
- Complex bug investigation.

Claude Code should not rewrite broad modules unless the user explicitly asks. Convert accepted Claude review findings into concrete `docs/TODO.md` items before Cursor implements them.

## First Thing To Do

Before new feature work, stabilize the current uncommitted batch.

Recommended order:

1. Inspect `git status`.
2. Read `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/cyber-companion.mdc`, `docs/CURSOR_PHASE_PLAYBOOK.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`, and this file.
3. Run:

```bash
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

4. If the checks still pass, create a checkpoint commit for the current Phase 2-10 MVP batch.
5. Only after the checkpoint, continue with small slices.

## Recommended Claude Code Prompt

```text
请先阅读 AGENTS.md、CLAUDE.md、docs/HANDOFF.md、docs/TODO.md、docs/SESSION_LOG.md、docs/OPEN_SOURCE_REUSE.md。

本次只做 review，不要改代码。
重点审查当前未提交的 Phase 2-10 MVP batch：
1. provider abstraction 是否保持后端-only、密钥不进前端；
2. memory/context 是否没有发送 full history；
3. behavior engine 是否没有把 Boxi 写成 generic polite assistant；
4. file gateway 是否没有 broad filesystem access 或 symlink escape；
5. STT/TTS 是否 mock-first、cloud-gated、没有连续云监听；
6. 前端 chat/avatar/voice 状态是否有明显卡死或竞态；
7. docs/TODO/session log/open-source reuse 是否和实现一致。

输出格式：
Findings:
Open questions:
Suggested next actions:

不要大改，不要提交。
```

## Recommended Cursor Prompt

```text
请先阅读 AGENTS.md、.cursor/rules/cyber-companion.mdc、docs/CURSOR_PHASE_PLAYBOOK.md、docs/HANDOFF.md、docs/TODO.md、docs/SESSION_LOG.md、docs/OPEN_SOURCE_REUSE.md。

先检查 git status，尊重当前未提交改动。
本次只做一个小切片，不开硬件阶段，不接云 STT/TTS，不改 provider abstraction、memory schema、behavior contract、file permission policy。

如果还没有 checkpoint commit，先不要继续堆功能。只运行检查并汇报：
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend

如果已经 checkpoint，可从 docs/HANDOFF.md 的 Next Small Slices 选一个任务。
完成后更新 docs/SESSION_LOG.md；只有 TODO 状态真的变化才改 docs/TODO.md。
```

## Next Small Slices

Do these only after the current uncommitted batch is checkpointed or the user explicitly asks to continue without a checkpoint.

- Expand backend CORS config if the frontend is routinely run on non-5173 ports. Keep it explicit, not wildcard.
- Install Playwright browser binaries only with user approval, then run full `node scripts/ui_verify.mjs`.
- Add a manual verification note for the latest browser smoke state.
- Wire real cloud STT/TTS only if `allow_cloud_stt` / `allow_cloud_tts` are true and keys are configured.

## Boundaries

- Do not start hardware work unless the user explicitly asks.
- Do not let frontend call LLM providers directly.
- Do not put API keys in source or docs.
- Do not grant broad filesystem access.
- Do not send full conversation history to providers.
- Do not let LLM output execute file operations or shell commands.
- Do not make Boxi a generic polite assistant.
- Do not have Claude Code and Cursor edit the same module at the same time.

