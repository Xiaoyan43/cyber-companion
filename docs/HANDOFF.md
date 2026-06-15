# HANDOFF — 上下文交接（2026-06-16，第三轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。当前阶段 = **让语音有真实的情绪层次 + 让长期记忆更贴人设**
（语音情绪/记忆改造，见 `docs/VOICE_EMOTION_MEMORY_PLAN.md`）。UI/视觉**暂缓**（见下方"本轮新增讨论"）。

## 本轮已完成（本 session）
- **R12 完成并 commit**：DeepSeek 文本聊天对"之前没提过的问题"会编造答案的问题已修复。
  根因 = `context_builder.py` 拼的 system prompt 里没有"信息缺失=不知道"的约束。
  修复 = [context_builder.py:76-82](backend/app/memory/context_builder.py:76) 新增
  `_ANTI_FABRICATION_NOTE` 常量，append 到 `system_sections`（[context_builder.py:189](backend/app/memory/context_builder.py:189)）。
  `pytest backend/tests/test_context_builder.py` 15 passed + 真机验证 PASS。已 commit (`6127000`)。
- **产品方向讨论（未落地，纯讨论）**：
  - 用户分享了两个前端参考：① 信笺打字机 prototype（`~/Documents/Codex/2026-06-13/ui/.../her-letter-typography/index.html`，
    纯 CSS/JS，mood→打字节奏/字重/透明度，无 WebGL，低 GPU 友好）；② 一张橙色渐变 Chat/Voice 双模式截图。
  - 用户设想：新前端用"文字动画传递 Boxi 情绪"（沿用信笺 prototype 的 mood 映射思路），
    Chat/Voice 双模式对应当前实时语音与打字两种模式。
  - 用户提到未来人设想往"复杂+暧昧陪伴"靠拢（**项目成熟后再做**，与既有记忆
    `persona-direction-complex-intimate` 一致，本轮未改 persona.json）。
  - 建议：前端 mood→视觉映射表设计时留余量，避免与当前"毒舌"人设词汇绑死太紧，
    免得未来人设转向时要重写映射表。

## 已修改文件 + 改动摘要（本轮）
- `backend/app/memory/context_builder.py` — 新增 `_ANTI_FABRICATION_NOTE`，追加到 system prompt 拼接。已 commit (`6127000`)。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — 本轮交接更新。

**测试/验证结果**：`pytest backend/tests/test_context_builder.py` 15 passed + 真机验证 PASS。

## 当前未完成（产品侧）
- **R11（仍搁置，等待用户可访问 VikingDB）**：纯 E2E 长期记忆部分失忆——Boxi 忘记用户在新西兰，
  疑似写入侧从未存入。详见 TASK_QUEUE R11。
- **VE-1 收尾**：playful 听感待 `relationship.closeness≥0.67` 自然达成后补测（被动等待）。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞中，需用户先补文档 `6348/2386107`。
- **新前端方向（纯讨论，未排期）**：信笺式打字机 UI + 暧昧人设方向，待用户决定是否/何时启动 spike。
- 其它（均可选，未变）：VM-7 (`get_context` 评估)、延迟旋钮、O2.0 persona 收尾、API Key 轮换（R8）。

## 已知 bug / 风险
- **R2（仍存在）**：本地 master 仍 ahead of origin by 2 commits（含 `6127000`），未 push。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——**不要继续开发它**。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 若做 R11-A：读 `frontend/src/voice/` + `backend/app/rtc/routes.py:306-345`。
- 若讨论新前端方向：读信笺 prototype（路径见上）+ `docs/VOICE_EMOTION_MEMORY_PLAN.md`，**先讨论不动代码**。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块。

## 推荐下一个最小任务
R12 已完成。下一个候选是 **R11-A**（前端语音结束后是否触发 `/rtc/memory/session` 链路确认），
但需用户先能访问 VikingDB 控制台核实记忆库内容。若用户当前没有新的明确目标，本 session 到此结束。
