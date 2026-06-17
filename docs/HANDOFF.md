# HANDOFF — 上下文交接（2026-06-17，第十三轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P6-F 已完成。** Pipecat cascaded 语音链路全面就绪：WebSocket 双向流 TTS（P6-D）+ 流式 ASR 2.0（P6-A）+ DDC 口语填充词过滤（P6-F）均已接入并跑通。
下一步：P6-E（TTS 语音指令 `[#...]`，切 expressive 音色，需实机听感验收）。

## 本轮已完成（2026-06-17，第十三轮）

- **P6-F（未单独 commit，改动在工作区）**：
  - `doubao_streaming_stt_service.py`：`_request_params` 的 `"request"` 子字典加 `"enable_ddc": True`（1 行），过滤"嗯"、"那个"等口语填充词
  - `test_doubao_streaming.py`：新增 `test_request_params_include_enable_ddc`，429 pytest passed

- **P5-A-2 取消**：用户决定不使用 Venice，后续考虑换其他 provider。`docs/TASK_QUEUE.md` 已标注取消。

## 已修改文件 + 改动摘要（本轮，未 commit）

| 文件 | 说明 |
|---|---|
| `backend/realtime/doubao_streaming_stt_service.py` | `_request_params` 加 `"enable_ddc": True` |
| `backend/tests/test_doubao_streaming.py` | 新增 enable_ddc 单测 |
| `docs/HANDOFF.md` | 本文件（第十三轮整体覆盖） |
| `docs/TASK_QUEUE.md` | P6-F 标完成，P5-A-2 标取消 |

## 当前未完成（产品侧）

- **P6-E（下一步）**：TTS 语音指令 `[#...]`——切换到 `seed-tts-2.0-expressive`；LLM system prompt 加指令要求；`clean_text_for_tts` 已预留不 strip `[#...]`。需实机听感验收，expressive 稳定性有波动。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题
- **R11（搁置）**：纯 E2E 长期记忆部分失忆。等用户可访问 VikingDB 控制台
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档

## 已知 bug / 风险

- **R2**：本地 master ahead of origin **7 个 commit**（含本轮工作区未 commit 的 P6-F），未 push
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它
- **TIMING 日志**：`[TIMING]` 日志目前是 INFO 级别，生产前可降为 DEBUG

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **P6-E**（语音指令）：读 `reference/02.md`（语音指令示例）+ `reference/08.md`（expressive vs standard 对比）+ `backend/app/tts/text_cleanup.py` + `backend/app/behavior/tone.py`
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；已全量读完）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**P6-E**：TTS 语音指令——在 CompanionBrain system prompt 里加 `[#语气指令]` 要求，切换 TTS 到 `seed-tts-2.0-expressive`，透传 `[#...]` 不 strip。预计改动 medium，需实机听感验收（expressive 稳定性有波动，需先评估兼容性）。
