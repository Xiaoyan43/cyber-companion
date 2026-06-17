# HANDOFF — 上下文交接（2026-06-17，第十一轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。**信笺 UI** 方向 P0～P1-C 全部完成并已 commit。
**P6-D（TTS WebSocket 双向流式）已完成**，`DoubaoStreamingTTSService` 建好，待 pipeline 接入实机验收。
下一步：P6-D-3（pipeline 切换一行 + 实机验收）→ P6-F（ASR `enable_ddc`，5 分钟）→ P6-E（TTS 语音指令 `[#...]`）。

## 本轮已完成（2026-06-17，第十一轮）

- **reference/ 全量通读完成**（本轮补完 `流式.md`、`02.md`、`08.md`）：
  - `流式.md`：ASR bigmodel_async 协议文档，`enable_ddc` / `enable_emotion_detection` 参数确认
  - `02.md`：TTS 语音指令 `[#...]` 详细示例；嵌在文本里，P6-E 时 `clean_text_for_tts` 不能 strip 它
  - `08.md`：TTS 2.0 standard 支持 `context_texts`；嵌入指令 `[#...]` 需切 expressive 子版本；O2.0 支持声音复刻 v3（未来 Boxi 专属音色方向）

- **commit `9885550`（P6-A/B/C 补 commit）**：
  - ASR 2.0 升级：`doubao_streaming_stt_service.py` 切 `bigmodel_async` + `volc.seedasr.sauc.duration`
  - TTS 句间上下文：`doubao_tts_service.py` 加 `context_texts` accumulation
  - `test_doubao_streaming.py` 断言同步更新

- **commit `cc3aed1`（P6-D）**：
  - 新建 `backend/realtime/doubao_bidirection_tts_protocol.py` — TTS 2.0 bidirection 协议层（pure stdlib，帧构建 + 解析，13 单测全绿）
  - 新建 `backend/realtime/doubao_streaming_tts_service.py` — `DoubaoStreamingTTSService`（持久 WebSocket + `section_id` 跨句韵律，每句独立 session）
  - 新建 `backend/tests/test_doubao_bidirection_tts_protocol.py` — 13 离线单测

**验证结果**：428 pytest passed，tsc 零错误。实机 TTS 双向流式尚未接入 pipeline（P6-D-3 待做）。

## 已修改文件 + 改动摘要（本轮新增 commit）

| commit | 文件 | 说明 |
|---|---|---|
| `9885550` | `backend/realtime/doubao_streaming_stt_service.py` | ASR 2.0：切 bigmodel_async + volc.seedasr.sauc.duration |
| `9885550` | `backend/realtime/doubao_tts_service.py` | TTS 句间上下文：context_texts accumulation |
| `9885550` | `backend/tests/test_doubao_streaming.py` | 断言更新 |
| `cc3aed1` | `backend/realtime/doubao_bidirection_tts_protocol.py` | **新建** TTS 2.0 bidirection 协议层 |
| `cc3aed1` | `backend/realtime/doubao_streaming_tts_service.py` | **新建** DoubaoStreamingTTSService |
| `cc3aed1` | `backend/tests/test_doubao_bidirection_tts_protocol.py` | **新建** 13 单测 |

## 当前未完成（产品侧）

- **P6-D-3（验收，下一步）**：在 Pipecat pipeline 入口把 `DoubaoTTSService` 替换为 `DoubaoStreamingTTSService`（一行改动），实机听多句 Boxi 回复，验收：语气自然衔接，无割裂感
- **P6-F（5 分钟小改）**：`doubao_streaming_stt_service.py` 的 `_request_params` 加 `"enable_ddc": True`，过滤口语填充词
- **P6-E**：TTS 语音指令 `[#...]`——切换到 `seed-tts-2.0-expressive`；LLM system prompt 加指令要求；`clean_text_for_tts` 不能 strip `[#...]`
- **P5-B**：TTS → Fish Audio。**阻塞：** 用户已购买，需提供 Fish Audio API 文档
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题
- **R11（搁置）**：纯 E2E 长期记忆部分失忆。等用户可访问 VikingDB 控制台
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107

## 已知 bug / 风险

- **R2**：本地 master ahead of origin 4 个 commit，未 push
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它
- **P6-D-3 未验收**：`DoubaoStreamingTTSService` 协议层单测全绿，但实机 WebSocket 行为未验证（连接成功/音频正常/section_id 韵律效果）

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **P6-D-3**（pipeline 切换）：找 Pipecat pipeline 入口文件（grep `DoubaoTTSService`），读 `backend/realtime/doubao_streaming_tts_service.py`
- 若做 **P6-F**（enable_ddc）：只读 `backend/realtime/doubao_streaming_stt_service.py`
- 若做 **P6-E**（语音指令）：读 `reference/02.md`（已读，可跳过）+ `backend/app/tts/text_cleanup.py` + `backend/app/behavior/tone.py`
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；本轮已全量读完）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**P6-D-3**：grep `DoubaoTTSService` 找 pipeline 入口，改一行 import + 一行实例化，启动 pipeline 实机验收多句语气连续性。如果 WebSocket 连接有问题，优先检查 `_ensure_connected` 里 ConnectionStarted 的 frame 解析。

其次 **P6-F**（`enable_ddc: True`，5 分钟，不需要实机验证协议）。
