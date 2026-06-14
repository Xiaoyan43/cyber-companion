# 语音情绪 + 记忆：现状 / 改造方案 / TODO 切片

来源：火山引擎/豆包官方文档全量通读（`reference/01–15.md`，提取见 `reference/SYNTHESIS.md`，仅本地）。
本文是面向实现的结论与计划，可公开（不含密钥/接口原文）。Claude 出方案 → Cursor 实现 → Claude review。

## 0. 一句话结论

> **逐句情绪、压"夸张"、情绪强度调节，只有 cascaded（我们自管 TTS）路径能做；纯 E2E(O2.0) 只能靠
> `speaking_style` 粗调，且我们现在塞给纯 E2E 的 `TTSConfig`/`SetTTSContext` 很可能被平台忽略。**
> 记忆侧：火山有更省事的 `streaming_write`+`get_context`，以及自定义 schema（算子/权重/衰减）的完整能力，
> 当前 VM 系列只用了最浅的一层。

## 1. 三条语音路径现状（已对代码核实）

| 路径 | 代码 | 情绪控制现状 | 记忆 |
|---|---|---|---|
| **纯 E2E RTC（O2.0，线上默认）** | `rtc/voice_chat.py`(OutputMode 0 + `TTSConfig.Context{TagParse,QuoteUserQuestion}`)、`rtc/routes.py`(每轮 `SetTTSContext`)、`rtc/state_block.py`(PS-5 speaking_style / PS-6 emotion tag) | speaking_style 生效；**PS-6 的 SetTTSContext/TagParse 在 OutputMode 0 下大概率 no-op**（见 §2） | Viking `MemoryConfig` 注入 system_role（VM 系列）；off-path `analyze_turn` 写 SQLite |
| **cascaded（文字聊天云 TTS）** | `app/tts/doubao.py`：`audio_params` **只发 format+sample_rate** | **完全没有情绪参数**（无 emotion / context_texts / speech_rate） | 走 SQLite soul + context_builder |
| **V2 Pipecat 语音** | `realtime/doubao_tts_service.py`、`doubao_realtime_*` | TTSSettings 基本为空 | CompanionBrain 复用 soul |

前端 `voice/speechText.ts` 已会剥离括号舞台提示（喂 TTS 前）。

## 2. 关键结论（来自文档，附出处）

1. **纯端到端(OutputMode 0) 与 混合编排(OutputMode 1) 都忽略 `TTSConfig`**（`reference/12.md` 使用限制）。
   情绪标签机制（`TagParse`/`QuoteUserQuestion`/`SetTTSContext` 的支持模型表）**只含 TTS 模块模型，不含端到端模型**。
   → 我们 `voice_chat.py`/`routes.py` 给 pure 体塞的 TTSConfig.Context + SetTTSContext **很可能无效**，
   与项目里 PS-4/PS-6「设备 A/B 一直没确认跟随语气」吻合。**需一次设备确认即可定论。**
2. **cascaded 才能逐句情绪**（`reference/15.md` TTS API）：
   - `audio_params.emotion`（24 个枚举，见 `reference/09.md`）+ `emotion_scale`(1–5，**非线性**，默认 4) —— 精确情绪 + **强度旋钮（压"夸张"的关键）**，但**仅"多情感"音色支持**（`*_emo_v2_*`，每个音色一个子集）。
   - `additions.context_texts`（自然语言，如「用伤心的语气」）—— **2.0 音色可直接用**，维度更广、强度不可量化。
   - markdown/emoji 默认会被读出（`disable_markdown_filter` 默认 false，2.0 音色又不让设 true）→ **送 TTS 前必须我们清**。
3. **O2.0 纯 E2E 只有 4 个精品音色**（vv/小何/云舟/小天，`reference/09.md`），无现成"毒舌"音色；
   Boxi 当前最接近 = **云舟/小天**（沉稳磁性）+ speaking_style 调拽。更贴只能 SC2.0 saturn(已否决) 或自复刻。
4. **记忆侧有更省事/更强的能力**（`reference/06.md`）：
   - `streaming_write`+`get_context`：平台「写后异步抽取、读时拼好 `context_str`」，比手动 `SearchMemory` 简单。
   - 自定义 schema：`CustomEventTypeSchemas/CustomProfileTypeSchemas` + 算子(MAX/AVG/SUM/COUNT/LLM_MERGE) +
     `AggregateExpression` + 自定义事件权重 + 分数融合(向量×w + 时间衰减×w + 自定义×w) + 无衰减期。
5. **`IgnoreBracketText`**（`reference/14.md`）：Boxi 把动作/情绪写进括号 → TTS 不读、随字幕下发前端 →
   驱动 avatar/UI。**这是 Direction C「felt 内心 → 画面」缺的桥**（需补 `6348/2386107` 全文）。
6. **延迟旋钮**（`reference/13/14.md`）：`LLMConfig.ThinkingType="disabled"`、`Prefill`、`ASRConfig.VADConfig.AIVAD`、
   `ExpireTime`、`InterruptConfig.InterruptSpeechDuration`、二遍识别。多为混合编排/模块化才有的字段。

## 3. 改造方案（按主题）

### A. 情绪（核心诉求：有层次、不夸张）
- **真正落点 = cascaded TTS**。扩展 `project_tone` 的输出，让 kernel →（a）`emotion`+`emotion_scale` 或（b）`context_texts` 短语；
  在 `app/tts/doubao.py`（及 Pipecat TTS）的 `audio_params`/`additions` 里下发；首句留纯文本降首帧延迟。
- **压"夸张" = `emotion_scale` 调低 + 选"情感平稳"音色 + `speech_rate` 控速**。
- **markdown/emoji 清洗**下沉到后端 TTS 入口（前端 `speechText.ts` 的逻辑搬一份到后端）。
- **纯 E2E** 维持 speaking_style 作为唯一情绪杠杆；若 §2.1 确认 SetTTSContext 无效 → 从 pure 体移除 TTSConfig.Context + 停发 SetTTSContext（省请求、去误导），把 felt/register 全压进 speaking_style。

### B. 记忆
- **VikingDB 自定义 schema**（TODO 既有项）：定义 Boxi 对齐的事件规则（用户进展/情绪触发/求职事件）+ 画像规则（性格/偏好/求职档案）+ 权重表达式（"重要记忆"加权）+ 时间衰减。Claude 出 spec，用户在火山 console 应用。
- **（可选）迁移到 `get_context`**：用一次调用替代 VM 的手动 `SearchMemory` 拼接；SQLite 仍是 source of truth，Viking 只喂 RTC `system_role`。

### C. Avatar 桥（Direction C，UI 在用户定方向前暂缓）
- `IgnoreBracketText`：Boxi 输出 `（挑眉）` 类括号 → 不读、随字幕给前端 → 喂 felt-shown / 未来 avatar。
  现在可先做"括号→前端情绪 cue 信号"（不依赖最终画面）。需补 `6348/2386107`。

### D. 延迟（并入既有 V2_VOICE_LATENCY 后续）
- 混合编排/模块化时：`ThinkingType=disabled`、`Prefill`、`AIVAD`、`SilenceTime`/`InterruptSpeechDuration` 调优。

## 4. TODO 切片（建议顺序）

- [ ] **VE-1 cascaded 逐句情绪 `[Claude spec → Cursor]`**（最高，直接解决"情绪+夸张"）。
  kernel→emotion/emotion_scale 或 context_texts；`app/tts/doubao.py` + Pipecat TTS 下发；后端 markdown/emoji 清洗；
  选定 Boxi 音色（先 云舟/小天）。**依赖**：确认走 cascaded 的触发场景。
- [ ] **VE-2 纯 E2E 情绪通道核实 + 收尾 `[Claude]`**。一次设备 A/B 确认 SetTTSContext 在 OutputMode 0 是否生效；
  无效则移除 pure 体 TTSConfig.Context + 停发 SetTTSContext，speaking_style 收口。**依赖**：用户设备。
- [ ] **VM-6 VikingDB 自定义 schema spec `[Claude spec → 用户 console 应用]`**。事件/画像规则 + 算子 + 权重 + 衰减。
- [ ] **VE-3 IgnoreBracketText → 前端情绪 cue `[Claude spec → Cursor]`**（later）。需补 `6348/2386107`；与 UI 方向解耦先做信号层。
- [ ] **（可选）VM-7 get_context 迁移评估 `[Claude]`**。
- [ ] **（可选）延迟旋钮**并入 V2_VOICE_LATENCY 后续。

## 5. 边界
- 低 GPU：不做实时 shader/重 WebFGL（见记忆 `dev-machine-specs`）；avatar 桥只做信号层，画面待用户定。
- SC2.0 已否决（音色固定）；O2.0 默认不变。
- 不把密钥/个人数据写进 tracked 文件；`reference/` 保持 gitignore。
- 不改 soul kernel 数值含义 / memory schema（SQLite 仍 source of truth）。
