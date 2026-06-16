# HANDOFF — 上下文交接（2026-06-17，第五轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。**信笺 UI** 方向持续推进：P0（React 骨架）已完成，
P1（接入 App.tsx 作为可切换模式）**本轮完成**，见下方。语音情绪/长期记忆改造
（`docs/VOICE_EMOTION_MEMORY_PLAN.md`）仍是另一条并行线，本轮未推进。

## 本轮已完成（本 session）
- **信笺 UI · P1 完成（未 commit，待本 session 结束后 commit）**：
  - `frontend/src/App.tsx` 新增 `uiMode: 'classic' | 'letter'` state（默认 `'classic'`）。
  - chat-header 新增 toggle 按钮（`.letter-toggle-button`），点击在两模式间切换，按钮文案随模式变化（"对话"/"信笺"）。
  - letter 模式下：渲染 `<LetterView />`（替换 `.message-list` + `.chat-form`）；输入框隐藏。
  - classic 模式下：原有消息列表 + 表单完整保留，切换后 `messages` state 不丢失。
  - Mood/Relationship/Memory 面板两种模式均保持不变（未动）。
  - LetterView 内部 mood picker 按钮自管理（P1 scope 未接 backend mood）。
  - `tsc --noEmit` 零错误；vite dev 截图验证切换 PASS；console 零报错。

## 已修改文件 + 改动摘要（本轮）
- `frontend/src/App.tsx` — P1：新增 `uiMode` state + toggle 按钮 + 条件渲染（LetterView vs 消息列表/表单）。
  diff 规模：+92 / -76（主要是条件渲染嵌套，逻辑无变化）。**未 commit**。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — 本轮交接更新。
- `.claude/launch.json` — 新增 `frontend`（vite dev, port 5173）配置项，供 preview 工具使用。

**测试/验证结果**：`tsc --noEmit` 通过；vite dev preview 截图：classic↔letter 两模式切换正常，
letter 模式显示 LetterView（打字机动画、mood picker、sketch 表情），切回 classic 消息历史完整还原，console 零错误。

## 当前未完成（产品侧）
- **信笺 UI · P1-B（下一个最小任务）**：给 `LetterView` 加可选 `mood?: LetterMood` prop，
  在 App.tsx 轻量 fetch backend mood（复用 MoodPanel 用的 endpoint），做最简映射后传入。
  需先读 `frontend/src/components/MoodPanel.tsx` 确认 API endpoint 名称。标 TODO 注释。
- **信笺 UI · P1-C（P1-B 之后）**：把最新 Boxi 回复文本传给 LetterView 驱动打字机（替换 demo scripts）。
  需给 `useTypewriter` 加受控文本 prop。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现，依赖用户回答
  `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个开放问题。
- **R11（仍搁置，等待用户可访问 VikingDB）**：纯 E2E 长期记忆部分失忆——Boxi 忘记用户在新西兰。
  详见 TASK_QUEUE R11。
- **VE-1 收尾**：playful 听感待 `relationship.closeness≥0.67` 自然达成后补测（被动等待）。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞中，需用户先补文档 `6348/2386107`。
- 其它（均可选，未变）：VM-7 (`get_context` 评估)、延迟旋钮、O2.0 persona 收尾、API Key 轮换（R8）。

## 已知 bug / 风险
- **R2（仍存在）**：本地 master ahead of origin by 5 commits（含本轮未 commit 的 App.tsx），未 push。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——**不要继续开发它**。
- **letter 模式无法发消息**：letter 模式隐藏输入框（用户决策），DeepSeek 链路在该模式下不可触发。
  P1-C 需要解决"如何把 Boxi 回复展示在 LetterView 里"的问题。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 若做**信笺 UI · P1-B**：读 `frontend/src/components/MoodPanel.tsx`（确认 mood API endpoint）+
  `frontend/src/letter/LetterView.tsx`（加 mood prop）+ `frontend/src/App.tsx`（加 fetch + 映射）。
- 若做 **P1-C**：读 `frontend/src/letter/useTypewriter.ts`（加受控文本 prop）+
  `frontend/src/letter/LetterView.tsx` + `frontend/src/App.tsx`（传最新 Boxi 消息）。
- 若做 R11-A：读 `frontend/src/voice/` + `backend/app/rtc/routes.py:306-345`。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块。

## 推荐下一个最小任务
**信笺 UI · P1-B**：给 `LetterView` 加可选 `mood` prop，App.tsx 轻量 fetch backend mood 后映射传入。
diff 预计 small（~30 行）。其次 P1-C（让 LetterView 显示真实 Boxi 消息），或 R11-A（需 VikingDB 访问）。
