# HANDOFF — 上下文交接（2026-06-17，第六轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。**信笺 UI** 方向持续推进：P0（React 骨架）已完成，
P1（接入 App.tsx 可切换模式）已完成，**P1-B（backend mood 接入 LetterView）本轮完成，未 commit**。
Provider 替换计划（Venice AI + Fish Audio）已列入 P5 任务队列。

## 本轮已完成（本 session）
- **信笺 UI · P1-B 完成（未 commit）**：
  - `frontend/src/letter/LetterView.tsx`：新增 `Props { mood?: LetterMood }`，`externalMood` 参数，
    `activeMood = externalMood ?? mood`。有外部 prop 时隐藏内部 picker（nav 包裹在条件渲染中），
    `emotion-sketch`、`writingClassName`、footer meta 均改用 `activeMood`。（diff ~18 行）
  - `frontend/src/App.tsx`：新增 import（`LetterMood`、`fetchMoodState`）、`letterMood: LetterMood | undefined`
    state、`useEffect` 监听 `uiMode === 'letter'`（切入时 one-shot fetch `GET /memory/mood`，按映射表
    设 state，失败时静默降级）、`<LetterView mood={letterMood} />` 传 prop。（diff ~32 行）
  - 映射：`sad|worried|angry→fragile`，`happy→excited`，`annoyed→hesitant`，其余→`calm`（标 TODO 注释）。
  - `tsc --noEmit` 零错误；preview 验证：picker 隐藏、mood 正确映射（idle→calm 显示）、console 零错误。

- **架构知识确认（本轮讨论，非代码改动）**：
  - 文字聊天（DeepSeek）链路只连 SQLite，Viking 仅在 RTC 语音挂断写入，两条链路完全独立。
  - SQLite 短期记忆文字↔语音**互通**（已用户实机验证：文字聊天说的事，E2E 语音能召回）。
  - 文字聊天有长期记忆：`context_builder` 做 SQLite 语义检索，VM-6 跨会话召回已 PASS。
  - 敏感内容：文字聊天侧完全本地（SQLite），Volcengine 不可见；语音挂断写 Viking 时经过云端。
  - Venice AI 替换不影响记忆架构（SQLite 层无关 LLM 供应商）。

- **P5 Provider 替换计划已列入 TASK_QUEUE**：P5-A（LLM→Venice AI）、P5-B（TTS→Fish Audio）。

## 已修改文件 + 改动摘要（本轮，均未 commit）
- `frontend/src/letter/LetterView.tsx` — P1-B-1：新增可选 mood prop + activeMood + 条件 picker 隐藏。
- `frontend/src/App.tsx` — P1-B-2：新增 letterMood state + useEffect fetch + 映射 + prop 传入。
- `docs/HANDOFF.md` — 本轮整体覆盖更新。
- `docs/TASK_QUEUE.md` — 标记 P1-B 完成，新增 P5-A/P5-B，更新优先级。

**验证结果**：`tsc --noEmit` 通过（零错误）；preview Network 可见 `/memory/mood` 在切换 letter 模式时触发；
picker 隐藏；activeMood 正确映射；console 零错误。

## 当前未完成（产品侧）
- **信笺 UI · P1-C（下一个最小任务）**：把最新一条 Boxi 回复文本传给 LetterView，驱动打字机替代 demo scripts。
  需给 `useTypewriter.ts` 加受控文本 prop；`LetterView` 加 `text?: string` prop。
  要读：`frontend/src/letter/useTypewriter.ts` + `LetterView.tsx` + `App.tsx`（messages state）。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现（依赖用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题）。
- **P5-A · LLM → Venice AI**：provider 层替换，无记忆改动，可随时开始。
- **P5-B · TTS → Fish Audio**：等用户提供 Fish Audio API 文档（用户确认会提供）。
- **R11（搁置，等待 VikingDB 访问）**：纯 E2E 长期记忆部分失忆（Boxi 忘记用户在新西兰）。
- **VE-1 收尾**：playful 听感待 `relationship.closeness≥0.67` 自然达成后补测（被动等待）。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞中，需用户补文档 `6348/2386107`。
- 其它（均可选）：VM-7、延迟旋钮、O2.0 persona 收尾、API Key 轮换（R8）。

## 已知 bug / 风险
- **R2（仍存在）**：本地 master ahead of origin by 6 commits（含本轮未 commit 的 4 个文件），未 push。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——**不要继续开发它**。
- **pre-existing：`/memory/mood` 高频轮询**：`useMoodRest` hook 持续 poll，本地 backend 能承受，
  但若未来迁移远程 API 需优化。记录为 P4 可选项，现在不动。
- **letter 模式无法发消息**：设计决策，DeepSeek 链路在 letter 模式不可触发。P1-C 需解决"如何把 Boxi 回复展示在 LetterView"。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 若做 **P1-C**：读 `frontend/src/letter/useTypewriter.ts` + `frontend/src/letter/LetterView.tsx` + `frontend/src/App.tsx`（messages state）。
- 若做 **P5-A**（Venice AI）：读 `backend/app/providers/` 目录（确认现有 provider 接口）+ `config/providers.json`。
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`（参考接口）。
- 若做 **R11-A**：读 `frontend/src/voice/` + `backend/app/rtc/routes.py:306-345`。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块。

## 推荐下一个最小任务
**信笺 UI · P1-C**：把最新 Boxi 回复文本传给 LetterView 驱动打字机（替换 demo scripts）。diff 预计 small-medium。
其次 **P5-A**（Venice AI，无依赖，可随时开始），或等用户提供 Fish Audio 文档后做 **P5-B**。
