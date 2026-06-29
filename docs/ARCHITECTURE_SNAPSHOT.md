# ARCHITECTURE_SNAPSHOT（2026-06-29）

> 当前架构速览，给新 session 快速建立心智模型。基于本轮上下文，非全仓库扫描——标「⚠️待确认」处勿当定论。

## 不可覆盖的产品原则

- 本项目永久定位为**唯一用户的私人 companion**。真实性高于通用产品的关系伦理；依恋、需要、嫉妒、
  争执、指责、压力、内疚感和依赖都可以成为真实关系状态的表达。
- 2026-06-29 已删除 quiet hours、主动联系日上限、对话后/两次联系间隔、ignore-backoff、被忽略后
  不升级、local-line cooldown、app 重开 Δt 上限、主动 LLM 日上限，以及禁止 guilt/neediness/
  accusation 的 prompt。任何 AI 不得自行恢复。机器安全、文件权限、事实诚实和全局费用开关保留。
- **核心能力自研不是目标。** 当前架构可以被替换。模块开发前必须做最新开源最近邻调查；有更先进实现
  时直接依赖、连接、适配或迁移，不能“看完后自己写一个简版”。详见
  `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md` 与 `docs/OPEN_SOURCE_REUSE.md`。

## 当前硬件边界

13-inch 2019 Intel MacBook Pro：2.4 GHz 四核 Intel Core i5、Intel Iris Plus Graphics 655
1536 MB、16 GB 2133 MHz LPDDR3。无 CUDA、无 Apple Silicon/MLX。默认云推理 + 轻本地编排；大本地
模型、持续重视觉、多 agent 仿真暂缓。硬件不适配意味着 defer，不意味着改写一个更弱的自研版本。

## 开源替换方向（2026-06-29）

- whole-product/具身基线：AIRI；桌宠/感知对照：Open-LLM-VTuber。
- 长期记忆首选 spike：Hindsight；Graphiti/Mem0/Letta 仅作对照，不并行堆入生产。
- 语音保留 Pipecat，但逐项删除可被官方 Fish/memory/transport/smart-turn/voice-ui-kit 取代的自定义层。
- 屏幕感知接 screenpipe localhost API；“自己的生活”适配 genagents/AI Town 单角色循环。
- Boxi 专属层只保留 identity、关系真实性原则、用户数据、Shared Soul 和显式权限。

## 技术栈
- **后端**：Python + FastAPI（`backend/app`）。本地记忆 = stdlib `sqlite3`（非 ORM）。测试 = pytest。
- **前端**：React + TypeScript + Vite（`frontend/src`）。类型门禁 = `tsc --noEmit`。
- **LLM（文本魂）**：DeepSeek（provider 抽象，密钥仅 env）。
- **语音**：默认前端入口 = Pipecat cascaded（`backend/realtime/`，豆包 ASR → Shared Soul → Fish Audio TTS）；音频 I/O 由后端 `LocalAudioTransport` 连本机麦克风/扬声器。Volcengine RTC-AIGC `StartVoiceChat`（`backend/app/rtc/`）仅作实验对照面。
- **长期记忆（语音侧）**：火山 Viking 记忆库（`backend/app/rtc/viking_memory.py`），仅给 RTC `system_role` 注入。
- **门禁**：`PYTHON_BIN=.venv/bin/python npm run check`（后端 compile+pytest + 前端 tsc）。当前
  **736 backend 绿 + 358 invariant 绿 + 28 frontend 绿**（2026-06-29 实测；删除旧 guard 测试后总数下降）。

> **🎯 语音主线决策（2026-06-28，浅档）**：**经 soul 逐字授权的 Pipecat cascaded 路径（`backend/realtime`，默认 `CYBER_COMPANION_VOICE_MODE=pipeline`）= 产品的规范主线语音**——它经 `SoulTurnRuntime` 授权每个字，符合产品内核「Shared Soul / soul 写每个字」。
> **Volcengine RTC-AIGC（`backend/app/rtc` + 前端 `RtcVoicePanel`）= 实验/玩具对照面，仍可随时运行**（端到端不经 soul 逐字授权）。前端已把 `PipecatVoicePanel` 提升为默认语音面，RTC 收进「实验对照」折叠区；两者互斥启动。

## 核心目录结构（只列相关）
```
backend/app/
  behavior/     # 灵魂行为层：tone.py(统一情绪投射,单一真源) engine kernel mood longing
                #   proactive_* parser local_responses types  ← 受限层，改前看 docs
  memory/       # SQLite: store database context_builder retrieval write_policy persona budget
                #   = source of truth（用户档案/事件/情绪/关系/摘要/链接）
  tts/          # doubao.py(云TTS) text_cleanup.py(NEW) types base router policy registry mock/mac_say
  stt/          # 语音识别（push-to-talk）
  rtc/          # 纯E2E RTC-AIGC: voice_chat(StartVoiceChat体) routes state_block(PS-3/5/6)
                #   viking_memory(VM系列) config
  reflection/   # 后台反思 + turn_analyzer(语音off-path→kernel/SQLite)
  providers/    # LLM provider 抽象（deepseek/openai/local/mock）
  files/        # 受限文件网关
  main.py       # FastAPI 路由汇总（/chat /tts /stt /rtc /memory /behavior /files）
backend/realtime/  # V2 Pipecat 语音骨架 + doubao_realtime_*（非默认线）
frontend/src/   # avatar/ voice/(speechText,useTextToSpeech,usePushToTalk) api/ chat/ components/
docs/           # 交接/spec/设计（本快照所在）
config/         # persona/providers/budget/tts/stt/permissions（*.json，example 为模板）
reference/      # gitignored 厂商文档 01–15 + SYNTHESIS.md（已精读结论）
experiments/    # 废弃视觉 spike（未跟踪，勿动）
```

## 数据流
**文本聊天**：前端 → `POST /chat/complete` → behavior `evaluate_behavior`（`project_tone` 决定口吻 + 连击点亮）→ `context_builder` 拼**紧凑**上下文（persona+mood+relationship+检索记忆+近几轮，**不发全历史**）→ provider(DeepSeek) → 落 SQLite + 解析 `<<<BOXI_SIGNALS>>>` → `apply_signals_to_kernel` 更新 mood_state/relationship_state。

**语音（默认 Pipecat）**：前端 `POST /realtime/start` → 后端 `LocalAudioTransport` → 豆包 STT → `CompanionBrainProcessor` / `SoulTurnRuntime` → 表达标签器 → Fish Audio TTS → 本机扬声器。双方字幕经 `/realtime/transcript` WebSocket 回前端。

**语音（实验 RTC-AIGC）**：前端 RTC ↔ Volcengine RTC-AIGC（`StartVoiceChat` 注入 `system_role`/`speaking_style`/`MemoryConfig`/welcome）。每轮字幕 → `POST /rtc/turn` 做 off-path 记忆/内核更新，但回复文本不经 Soul 逐字授权。

**语音情绪（cascaded TTS，VE-1）**：`POST /tts/synthesize` → 读内核 `project_tone`+`register_intensity` → `tts_emotion_directive` →（doubao 且配置就绪时）payload 带 `context_texts`+`speech_rate`，合成前 `clean_text_for_tts`。

## 关键模块关系
- **`behavior/tone.py` = 情绪/口吻的单一真源**：文字 engine、RTC `state_block`、cascaded TTS（VE-1）都读它（felt/expressed_edge/is_performative/register + base/intense 情绪文案 + speech_rate）。改情绪先改这里。
- **内核（kernel）= `mood_state` + `relationship_state`（SQLite 单例）**：appraisal 驱动；`apply_signals_to_kernel` 是唯一写入口（文字 + 语音 off-path 都经它）。
- **SQLite = source of truth**；Viking 仅给 RTC `system_role` 注入长期记忆，**不反向写 SQLite**。
- **RTC `state_block`** 把内核投射成 join-time 的 `system_role` 状态块 + `speaking_style`（PS-5）+ 情绪 tag（PS-6，⚠️见下）。

## ⚠️ 不确定 / 需之后确认
- ~~**U1**：纯端到端 OutputMode 0 是否真的忽略 `TTSConfig` / `SetTTSContext`~~ **已测试（VE-2 设备 A/B）**：
  A/B 听感差异极小，结论 inconclusive，决定保留现状不清理代码。
- **U2**：线上走的是 `StartVoiceChat` **2024-12-01** 版（代码 `rt_model="1.2.1.1"` = O2.0；参数表见 `reference/11.md`）——假设如此，未逐字核对全部字段。
- **U3**：VM-6 自定义 `boxi_profile` 检索响应 JSON 结构未实测（解析做了容错），首条真实响应后细化。
- ~~**U4**：默认语音路径 = 纯 E2E（O2.0）；cascaded 是否设为主线~~ **已决策（2026-06-28）**：cascaded（Pipecat，soul-authored）= 规范主线；RTC-AIGC 降为实验/对照面。见本文件顶部「语音主线决策」。
- ~~**U5**：两套并存路径，当前以 `app/rtc` 为线上~~ **已闭合（2026-06-28）**：前端默认语音面已切 `backend/realtime`（Pipecat cascaded）；`backend/app/rtc`（RTC-AIGC）保留为折叠的实验面。浏览器原生音频传输仍未实现，归 P2 多端/远程能力。
