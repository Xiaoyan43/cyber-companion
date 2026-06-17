# HANDOFF — 上下文交接（2026-06-17，第十四轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P6 全面完成。** Pipecat cascaded 语音链路就绪：
- WebSocket 双向流 TTS（P6-D）✅
- 流式 ASR 2.0 + DDC 口语过滤（P6-A + P6-F）✅
- TTS 语音指令 `[#...]` 情绪控制（P6-E）✅ — 已实机验证

下一步候选：信笺 UI P2、R11（VikingDB 记忆失忆排查）、P5-B（Fish Audio）。

## 本轮已完成（2026-06-17，第十四轮）

- **P6-E 实机验证 PASS**（commit `9de50fe`）：
  - 运行 `python -m backend.realtime.run_voice`（standalone Pipecat pipeline）
  - 日志确认 LLM 按 `VOICE_MODE_INSTRUCTION` 格式输出 `[#...]`，TTS 正确提取传入 `context_texts`
  - 实测指令样例：`[带点调侃的语气]`、`[带着笑意的语气]`、`[叹气但不算太凶的语气]`、`[带点无奈的笑]`、`[轻快带笑意的语气]`
  - 新增 INFO 日志：`[P6-E] voice instruction extracted: [...]`，便于后续调试

- **RTC hybrid 路径说明**（非 bug，是配置门槛）：
  - `/rtc/status` 返回 `hybrid_ready: false`，缺 `SOUL_LLM_PUBLIC_URL` + `SOUL_LLM_API_KEY`
  - 这两个变量是火山 RTC bot 回调用的，和 standalone `run_voice.py` 无关
  - standalone Pipecat pipeline 不需要这两个变量，直接跑即可

## 已修改文件 + 改动摘要（本轮）

| 文件 | commit | 说明 |
|---|---|---|
| `backend/realtime/doubao_streaming_tts_service.py` | `9de50fe` | 新增 P6-E 验证 INFO log（instruction 提取成功/失败均有日志） |

> P6-E 核心功能（prompt + 提取逻辑 + 单测）已在上轮 commit `4609b3b` 完成。

## 当前未完成（产品侧）

- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题
- **R11（搁置）**：纯 E2E 长期记忆部分失忆。等用户可访问 VikingDB 控制台
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档

## 已知 bug / 风险

- **R2**：本地 master ahead of origin **8 个 commit**，未 push
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它
- **TIMING 日志**：`[TIMING]` 和 `[P6-E]` 日志目前是 INFO 级别，生产前可降为 DEBUG

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **P2**（信笺 UI）：读 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` + `frontend/src/letter/LetterView.tsx`
- 若做 **R11**（记忆失忆）：读 `frontend/src/voice/`（确认 `/rtc/memory/session` 调用链）+ `backend/app/rtc/routes.py:306-345`
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；已全量读完）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**git push**（R2）：8 个 commit 未同步到远端，建议先 push。然后视用户意向：
- 若 VikingDB 控制台可访问 → 做 R11-A（前端 `/rtc/memory/session` 调用链确认）
- 若不可访问 → 做信笺 UI P2（需先回答 `LETTER_UI_MOOD_MAPPING_DRAFT.md` 的问题）
