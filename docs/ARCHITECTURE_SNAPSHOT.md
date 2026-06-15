# ARCHITECTURE_SNAPSHOT（2026-06-15）

> 当前架构速览，给新 session 快速建立心智模型。基于本轮上下文，非全仓库扫描——标「⚠️待确认」处勿当定论。

## 技术栈
- **后端**：Python + FastAPI（`backend/app`）。本地记忆 = stdlib `sqlite3`（非 ORM）。测试 = pytest。
- **前端**：React + TypeScript + Vite（`frontend/src`）。类型门禁 = `tsc --noEmit`。
- **LLM（文本魂）**：DeepSeek（provider 抽象，密钥仅 env）。
- **语音**：火山引擎/豆包。两条路径——① **纯 E2E** = Volcengine RTC-AIGC `StartVoiceChat`（端到端 O2.0 模型，`backend/app/rtc/`）；② **cascaded** = 我们自管的豆包 HTTP TTS（`backend/app/tts/doubao.py`）。另有 V2 Pipecat 语音骨架（`backend/realtime/`，非默认）。
- **长期记忆（语音侧）**：火山 Viking 记忆库（`backend/app/rtc/viking_memory.py`），仅给 RTC `system_role` 注入。
- **门禁**：`PYTHON_BIN=.venv/bin/python npm run check`（后端 compile+pytest + 前端 tsc）。当前 411 backend 绿。

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

**语音（纯 E2E）**：前端 RTC ↔ Volcengine RTC-AIGC（`StartVoiceChat` 注入 `system_role`/`speaking_style`/`MemoryConfig`/welcome）。每轮字幕 → `POST /rtc/turn` → `analyze_turn`（off-path）→ `evaluate_behavior`(推进连击) + DeepSeek 信号 → kernel + `persist_chat_turn` + 记忆写入 + 反思。挂断 → `/rtc/memory/session` → Viking `AddSession`。

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
- **U4**：默认语音路径 = 纯 E2E（O2.0）；cascaded 是否设为主线（Direction C 倾向 cascaded）仍是产品决定，未切换。
- **U5**：`backend/realtime/`（V2 Pipecat）与 `backend/app/rtc/`（RTC-AIGC）是两套并存路径；当前以 `app/rtc` 为线上。
