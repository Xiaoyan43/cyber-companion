# HANDOFF — 上下文交接（2026-06-16，第四轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。新方向：**信笺 UI**（用打字节奏/字重/透明度传递 Boxi 情绪，
作为新增可切换模式，不删旧 UI）已确定并开始落地，见下方"本轮已完成"。语音情绪/长期记忆改造
（`docs/VOICE_EMOTION_MEMORY_PLAN.md`）仍是另一条并行线，本轮未推进。

## 本轮已完成（本 session）
- **R12 完成并 commit (`6127000`)**：DeepSeek 文本聊天对"之前没提过的问题"会编造答案的问题已修复。
  [context_builder.py:76-82](backend/app/memory/context_builder.py:76) 新增 `_ANTI_FABRICATION_NOTE`，
  append 到 `system_sections`（[context_builder.py:189](backend/app/memory/context_builder.py:189)）。
  `pytest backend/tests/test_context_builder.py` 15 passed + 真机验证 PASS。
- **信笺 UI 方向确定**：用户在两个前端参考（① 信笺打字机 prototype；② 橙色渐变 Chat/Voice 双模式截图）
  之间选择了①，并决定"信笺视觉语言 + ②的双模式交互结构"，**替换现有 UI**（实际策略 = 新增可切换模式，
  不删旧 UI，见 TASK_QUEUE）。
- **信笺 UI · P0 完成并 commit (`481d0ee`, `4858125`)**：
  - `481d0ee`：把 prototype 原样拷入 `experiments/letter-typography-spike-2026-06/`（独立 HTML，可直接浏览器打开）；
    新增 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md`（mood↔`tone.py` `ToneProjection` 映射草案 + 3 个开放问题，未回答）。
  - `4858125`：把该 prototype 的 typewriter 引擎 + 4 个 mood（calm/hesitant/excited/fragile）React 化，
    新增 `frontend/src/letter/`（`LetterView.tsx` + `useTypewriter.ts` + `scripts.ts` + `LetterView.css`，
    样式全部加 `.letter-spike` 前缀隔离）。**未接入 `App.tsx`**（按 P0 scope，独立组件）。
    `tsc --noEmit` 通过；临时改 `main.tsx` 渲染验证（已 revert），vite dev 截图确认 4 个 mood 切换/
    打字机/sketch 表情/淡入淡出均正常，无 console 错误。

## 已修改文件 + 改动摘要（本轮）
- `backend/app/memory/context_builder.py` — R12，已 commit (`6127000`)。
- `experiments/letter-typography-spike-2026-06/`（index.html + README.md）— 已 commit (`481d0ee`)。
- `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` — 已 commit (`481d0ee`)。
- `frontend/src/letter/`（LetterView.tsx/css, useTypewriter.ts, scripts.ts）— 已 commit (`4858125`)。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — 本轮交接更新。

**测试/验证结果**：`pytest backend/tests/test_context_builder.py` 15 passed；前端 `tsc --noEmit` 通过；
信笺 React 组件 vite dev 截图验证 PASS。

## 当前未完成（产品侧）
- **信笺 UI · P1（下一个最小任务）**：把 `LetterView` 接入 `App.tsx`，加 `uiMode: 'classic'|'letter'`
  toggle（默认 classic），mood 先用 `mood_state.mood` 做最简映射。详见 TASK_QUEUE「信笺 UI 方向」。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现，依赖用户回答
  `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个开放问题（real_sharp/lonely 无对应 mood 等）。
- **R11（仍搁置，等待用户可访问 VikingDB）**：纯 E2E 长期记忆部分失忆——Boxi 忘记用户在新西兰，
  疑似写入侧从未存入。详见 TASK_QUEUE R11。
- **VE-1 收尾**：playful 听感待 `relationship.closeness≥0.67` 自然达成后补测（被动等待）。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞中，需用户先补文档 `6348/2386107`。
- 其它（均可选，未变）：VM-7 (`get_context` 评估)、延迟旋钮、O2.0 persona 收尾、API Key 轮换（R8）。

## 已知 bug / 风险
- **R2（仍存在）**：本地 master 仍 ahead of origin by 4 commits（含 `481d0ee`/`4858125`），未 push。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——**不要继续开发它**。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 若做**信笺 UI · P1**：读 `frontend/src/App.tsx`（找 Chat 区域渲染位置）+ `frontend/src/letter/LetterView.tsx`。
- 若做 R11-A：读 `frontend/src/voice/` + `backend/app/rtc/routes.py:306-345`。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块。

## 推荐下一个最小任务
**信笺 UI · P1**：把 `frontend/src/letter/LetterView` 接入 `App.tsx`，加 `uiMode: 'classic'|'letter'`
toggle（默认 classic，不影响现有用户），mood 先用 `mood_state.mood` 做最简映射。
其次 R11-A（需用户先能访问 VikingDB）。
