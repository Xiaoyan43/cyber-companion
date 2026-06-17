# HANDOFF — 上下文交接（2026-06-17，第十五轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P7 完成。** 三种说话方式均可从前端使用：
- 文字聊天（原有）✅
- 纯 E2E 语音（Volcengine RTC-AIGC）✅
- Pipecat 本地语音（前端按钮开关）✅ — 已实机验证 PASS

## 本轮已完成（2026-06-17，第十五轮）

- **P7 · Pipecat 前端入口**（commits `9a7a278` → `dc4ce4e`）：
  - 新建 `backend/realtime/pipeline_router.py`：`POST /realtime/start`、`POST /realtime/stop`、`GET /realtime/status`
  - `backend/app/main.py` 注册 router
  - 前端 `App.tsx` header 加「Pipecat」切换按钮，含 loading/error 状态 + useRef 防止 stale closure
  - 实机验证：点按钮启动后，STT→LLM→TTS 全链路正常，`half_duplex=on`，first_audio ~0.4s
  - 两个声音问题根因：旧进程未退出导致两个 pipeline 同时跑；杀旧进程后正常

- **中途废弃的 WS 方案**（已撤销）：
  - 原计划用 `FastAPIWebsocketTransport` 把音频流搬进浏览器，实现远程访问
  - 因当前只有本地使用需求，改为更简单的 start/stop HTTP 端点（`LocalAudioTransport` 不变）

## 已修改文件 + 改动摘要（本轮）

| 文件 | commit | 说明 |
|---|---|---|
| `backend/realtime/pipeline_router.py` | `9a7a278` | 新建，start/stop/status 端点 |
| `backend/app/main.py` | `9a7a278` | 注册 pipecat_router |
| `frontend/src/App.tsx` | `9a7a278` + `7282476` + `dc4ce4e` | Pipecat 按钮，apiBaseUrl 修复，stale closure 修复 |

## 当前未完成（产品侧）

- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题
- **R11（搁置）**：纯 E2E 长期记忆部分失忆。等用户可访问 VikingDB 控制台
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档

## 已知 bug / 风险

- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它
- **TIMING 日志**：`[TIMING]` 和 `[P6-E]` 日志目前是 INFO 级别，生产前可降为 DEBUG
- **Pipecat 记忆写回**：`CompanionBrain` 写入 SQLite（文字+记忆），但语音轮次的 off-path 反思（`analyze_turn`）未确认是否与 RTC 路径等价。如发现记忆遗漏，查 `companion_brain.py` 的 `persist_chat_turn` 调用链

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **P2**（信笺 UI）：读 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` + `frontend/src/letter/LetterView.tsx`
- 若做 **R11**（记忆失忆）：读 `frontend/src/voice/`（确认 `/rtc/memory/session` 调用链）+ `backend/app/rtc/routes.py:306-345`
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`
- 若做 **Pipecat 记忆核查**：读 `backend/realtime/companion_brain.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

视用户意向：
- 若 VikingDB 控制台可访问 → 做 R11-A（前端语音记忆调用链确认）
- 若不可访问 → 回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题后做信笺 UI P2
- 若想确认 Pipecat 记忆是否完整 → 读 `backend/realtime/companion_brain.py` 确认写回路径
