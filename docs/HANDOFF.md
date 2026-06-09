# Handoff For Claude Code And Cursor

## ⚠️ DIRECTION CHANGED — Session 26 (read this first)

The project pivoted to a **V2 rebuild** with a clear vision. New source-of-truth:
**`docs/ARCHITECTURE_V2.md`** + **`docs/REBUILD_ROADMAP.md`**. See `docs/SESSION_LOG.md`
Session 26 for the full reasoning. TL;DR:

- **Two cores:** ① full-duplex real-time voice (on memory + personality) ② "person
  in a box" = a 2.5D PixiJS pixel room. Hardware end-goal: old **iPhone SE2 + 3D
  shell** as the box (iPhone = surface; brain runs on the Mac; cloud only for
  DeepSeek/Doubao).
- **Base decision:** Pipecat (voice) + KEEP our Python soul + PixiJS pixel room.
  AIRI / Open-LLM-VTuber / OpenAvatarChat = references only, not forks. Steal:
  Capacitor-iOS, `@ricky0123/vad-web`, Open-LLM-VTuber's echo-cancellation,
  emotion→expression mapping.
- **PRIORITY = SOUL FIRST** (user's 80/20: memory + proactive + emotion = ~80% of
  emotional value; real-time voice = ~20%). The whole VTuber field skips the soul;
  we already have its scaffolding. So deepen memory/proactive/emotion on the
  current working app FIRST; voice/box rebuild comes after.
- **Budget walls are OFF** (`config/budget.json`: monthly=0, daily=0,
  reasoning=true). Extra LLM calls for the soul are welcome, but place them
  latency-smart: sync = piggyback structured signals on the one reply call; heavy
  reflection = background; trivial = local.

**NEXT TASK (new window starts here):** deep-dive memU + the "subjectivity kernel"
(persistent emotion + relationship dynamics) + awesome-affective-computing, then
write a **soul-deepening spec** (LLM-driven memory extraction / emotion+relationship
state / a background reflection layer), incremental on the working app — no rebuild
yet. Then Claude spec → Cursor implements → Claude reviews.

> There is uncommitted work (the V2 docs, budget walls off, S3 TTS revert). Run
> `git status` and checkpoint as appropriate before new work.

---

## Current State (pre-pivot reference)

Baseline checkpoint: commit `5005731` (Phase 2–10 MVP batch including behavior ticks, CORS, Vite 6, tick persistence). **Policy: one slice → one checkpoint commit; do not accumulate uncommitted work.**

Implemented through Session 23:

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

Both passed after Session 23. Backend tests: 70 passing; frontend `tsc --noEmit` and Vite 6.4.x production build pass. `npm audit` reports 0 vulnerabilities (dev and prod).

`node scripts/ui_verify.mjs`: **37/37 passed** after Session 25 (Playwright 1.60 + Chromium installed). API section passes without browsers; full browser smoke needs `npx playwright install chromium`.

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

1. Inspect `git status` — working tree should be clean after each slice commit.
2. Read project docs (`AGENTS.md`, `docs/HANDOFF.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`).
3. Run `PYTHON_BIN=.venv/bin/python npm run check` and `npm run build:frontend`.
4. Pick one slice from **Next Small Slices**, implement, verify, **commit immediately**, update `docs/SESSION_LOG.md`.

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

- Fix or extend `scripts/ui_verify.mjs` (Playwright browsers installed; re-run after UI changes).
- Have Claude Code do read-only MVP batch review (see prompt below).
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

