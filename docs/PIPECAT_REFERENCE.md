# Pipecat Reference（P14 Phase 1 · P1 综述）

> 仿 `docs/FISH_AUDIO_REFERENCE.md` 结构。来源 = `reference/pipecat/`（gitignored 落盘，P0 抓取于
> 2026-06-23）：`docs.pipecat.ai/llms-full.txt`（官方文档站全站 433 页）+ `reference-server.pipecat.ai/`
> （Sphinx API autodoc 104 页）+ Fish→Pipecat 页 + 本机 `.venv/.../pipecat/` 源码交叉验证。
> 每节标注 `Source:` 便于回溯。**本综述聚焦我们用到的 cascaded 本地音频链路**，其余 vendor service 只索引。
>
> **结论先行（P14「关键事实」复核）**：#1 ✅ 成立并更完整；#2 ✅ 成立但需修正措辞；#3 ✅ 成立并定位到双游标根因。详见 §10。

---

## 0. 版本与适用范围（最重要的前置事实）

- **本机安装 `pipecat-ai 1.3.0`**（`.venv`）。`run_voice.py` 已使用 **1.0 API**：`PipelineWorker` +
  `PipelineParams`（`backend/realtime/run_voice.py:126/160/237/297`）。
- **docs.pipecat.ai 与 reference-server.pipecat.ai 描述的就是 1.0+ 架构**——和我们安装的 1.3.0 **同代，无迁移断层**。
  （HANDOFF/ARCHITECTURE_SNAPSHOT 里残留的 "PipelineTask/PipelineRunner" 说法已过期，应以本节为准。）
- 影响：旧资料里的 `PipelineParams(allow_interruptions=...)`、`PipelineTask` 等在 1.x 已变（见 §9、§10）。
  写 Phase 2 审计时**一律以 1.3.0 API 为准**。
- Source: `https://docs.pipecat.ai/pipecat/migration/migration-1.0`，本机 `importlib.metadata.version('pipecat-ai')=1.3.0`。

## 1. 核心架构：Pipeline / Frame / FrameProcessor

- **Pipeline** = 把一串 FrameProcessor 按顺序连起来的编排组件；帧在其中单向（可双向）逐级流动。
- 我们这类 cascaded 语音 agent 的标准拓扑（官方示例，与我们一致）：
  ```python
  Pipeline([
    transport.input(),               # 麦克风音频帧
    stt,                             # 语音→文本
    context_aggregator.user(),       # 收集用户轮
    llm,                             # 生成 LLMTextFrame
    tts,                             # 文本→TTSAudioRawFrame
    transport.output(),             # 音频→扬声器
    context_aggregator.assistant(), # 把"实际说出的文本"写回上下文
  ])
  ```
- **Frame** = 流经管道的数据包（带唯一 id/name 如 `TranscriptionFrame#1`，便于 debug）。
- **FrameProcessor** = 管道里的"工人"：收帧→处理→产新帧→`push_frame` 传给下一级。**模块化可替换**
  （换 STT/LLM/TTS 不动其余）。
- Source: `pipecat/learn/pipeline`、`pipecat/learn/overview`。

## 2. 自定义 FrameProcessor（= 双 LLM 两阶段标签的原生插点）

- 写法：继承 `FrameProcessor`，覆写 `async def process_frame(self, frame, direction)`：
  ```python
  class MyProc(FrameProcessor):
      async def process_frame(self, frame, direction):
          await super().process_frame(frame, direction)   # 必须先调父类
          if isinstance(frame, TargetFrame):
              ... # 处理
          await self.push_frame(frame, direction)          # ⚠️ 永远转发每一个帧
  ```
- **铁律**：`process_frame` 里**必须对每个帧调用 `push_frame`**（漏转会断流）。官方原话 "SUPER IMPORTANT: always push every frame!"
- 这正是 P14「关键事实 #1」所指：**双 LLM 第二阶段标签器应做成插在 `brain_processor`↔`tts` 之间的自定义
  FrameProcessor**，而不是在 `companion_brain.py` 里串行调两次 LLM。我们已有 `companion_brain_processor.py`
  /`half_duplex_mute_processor.py`/`vad_processor.py` 等自定义 processor，模式现成。
- Source: `pipecat/fundamentals/custom-frame-processor`。

## 3. TTS 文本聚合 + "自定义标签"机制（双 LLM 形态的关键依据）

- **默认 `TextAggregationMode.SENTENCE`**：TTS 把流式 LLM token **聚合成整句**再合成（藏 TTS 请求开销）。
- 可设 `text_aggregation_mode=TextAggregationMode.TOKEN`：逐 token 直送，**更低延迟**（端到端常 <200ms），
  但牺牲整句韵律。
- **自定义聚合 / 跳过朗读**（原生支持自定义标签的官方机制）：在 TTS **之前**插一个
  `LLMTextProcessor(text_aggregator=...)`，用 `PatternPairAggregator` 注册 `start_pattern`/`end_pattern`
  把文本切成逻辑单元（如 `<code>...</code>`、URL、**或我们的情绪标签**）；再用 TTS 的
  `skip_aggregator_types=[...]` 跳过某类不朗读。
  ```python
  agg = PatternPairAggregator()
  agg.add_pattern(type="code", start_pattern="<code>", end_pattern="</code>", action=MatchAction.AGGREGATE)
  tts = SomeTTS(..., skip_aggregator_types=["code"])
  ```
- **对 P14 Phase 4 的意义**：要给 Fish 注入"逐句标签"，原生路线 = 一个产出带标签文本的处理器 +
  `PatternPairAggregator` 识别标签边界 + TTS 整句聚合——比串行二次 LLM 调用更贴合框架。具体形态留 Phase 4 定。
- 两类输出帧：`TTSAudioRawFrame`（音频）、`TTSTextFrame`（实际说出的文本，回写上下文）；
  边界帧 `TTSStartedFrame`/`TTSStoppedFrame`。
- Source: `pipecat/learn/text-to-speech`、`api-reference/server/utilities/frame/llm-text-processor`、
  `api-reference/server/utilities/text/pattern-pair-aggregator`。

## 4. Fish Audio TTS service 装配（复核关键事实 #2）

- 类 `FishAudioTTSService`（WebSocket 流式）。**v0.0.105 起**：构造参数 `reference_id`/`model`/`params` 已弃用，
  改用 `settings=FishAudioTTSService.Settings(...)`。
- `Settings` 字段（**可运行时改**，见 §8）：`model` / `voice` / `language` / `latency` / `normalize` /
  `temperature` / `top_p` / `prosody_speed` / `prosody_volume`。
- 输出格式：`pcm` / `opus` / `mp3` / `wav`；`sample_rate=None` 时用 pipeline 的 `audio_out_sample_rate`。
- **关键事实 #2 复核（成立，但措辞要修正）**：
  - venv 源码 `pipecat/services/fish/tts.py` 三处一致：`latency: Latency mode ("normal" or "balanced")`，
    `Settings.latency` 默认 `"normal"`（`InputParams` 路径默认 `"balanced"`）。
  - 但 `latency` 类型是 `str | None`（**不是严格 Literal/枚举**），合成时原样塞进 payload（源码第 290 行
    `"latency": self._settings.latency`）。所以传 `"low"` **不会被 Pipecat 报错或拒绝**，而是**原样转发给
    Fish 服务端**——是否生效取决于 Fish API。
  - ⚠️ 修正后的准确表述：**Pipecat 只"祝福"`normal`/`balanced` 两档（文档/默认），`low` 属未定义行为
    （透传，行为未知）**。原 HANDOFF "会被拒/忽略" 不够准确。`run_voice.py:103` 允许传 `low` 这件事
    要在 Phase 5 一并处理（要么删 `low` 选项，要么实测 Fish 服务端对 `low` 的反应）。
- Source: `api-reference/server/services/tts/fish`、venv `pipecat/services/fish/tts.py`。

## 5. TTS 基类 + audio-context 生命周期（复核关键事实 #3 / P13 根因）

- Fish service 继承的基类（`pipecat/services/tts_service.py`，对应落盘
  `reference-server.../_modules/pipecat/services/tts_service.html`）实现了 **per-turn audio context** 机制，
  用来在中断/多轮时把"哪段音频属于哪一轮"对上。
- **双游标设计（源码注释明确）**——这是 P13 的根因面：
  - `_turn_context_id`：LLM 轮结束（合成完成）时清除。
  - `_playing_context_id`：**播放侧游标**，一直保留到音频真正播完；中断时由 `reset_active_audio_context()` 清除。
  - 两者"在不同时刻清除"：turn 结束 ≠ 播放结束。`get_active_audio_context_id()`/`has_active_audio_context()`
    读的是播放侧游标。
  - 还有 `reuse_context_id_within_turn: bool = True`（同一轮内复用 context id）。
- **P13 机理（"no context ID provided"）**：`latency=normal` 档生成节奏使**音频帧到达时，对应的 turn
  context 已在上一轮结束时被清理**，新音频对不上活动 context → 被静默丢弃 → 第二轮起失声。
  `balanced` 档节奏不同，竞态不触发。**疑似库级时序竞态，非我们调用代码的 bug**。
- **Phase 5 待定**：改调用方式（如保持 context、或调 `reuse_context_id_within_turn`）/ subclass 覆写 /
  上报上游。本综述只定位，不修。
- Source: 落盘 `_modules/pipecat/services/tts_service.html`、venv `pipecat/services/tts_service.py`。

## 6. 语音输入与轮次检测（VAD / endpointing / turn strategies）

- 1.x 用 **user turn strategies** 决定轮次起止（`api-reference/.../turn-management/user-turn-strategies`）：
  - **轮次开始**：VAD（检测到语音）/ 转写兜底（有转写但 VAD 没触发）/ 最小词数。
  - **轮次结束（默认 Smart Turn 模型）**：AI 判断"用户是否说完一个完整意思"；或 speech timeout（转写后静音超时）。
- **VAD = Silero**（本地 CPU，30ms+ 块 <1ms，单线程）。参数 `VADParams`：`confidence`(0.7) / `start_secs`(0.2) /
  `stop_secs`(0.2) / `min_volume`(0.6)。装在 `LLMContextAggregatorPair` 的 `user_params` 上。
  官方建议：默认值通常够用，非特殊音频别动。
- **对照我们的链路**：我们有自定义 `vad_processor.py`；Phase 2 要核对我们用的是 Silero 默认参数还是自调，
  以及是否启用了 Smart Turn（影响判停延迟，与 P6 的 ASR 判停优化相关）。
- Source: `pipecat/learn/speech-input`。

## 7. 中断 / 抢话语义（区分官方两套机制 vs 我们的 half-duplex）

- **帧的中断语义**（核心）：`DataFrame`/`ControlFrame` 在用户中断时**会被取消丢弃**；`SystemFrame`
  **优先级更高、中断时永不丢**（中断信号、用户输入、错误、生命周期都是 SystemFrame）。
  需要保命的 Data/Control 帧可加 `UninterruptibleFrame` mixin 免于被取消。
- **`InterruptionFrame`**：由 "请求中断" 转换而来，驱动 barge-in。
- **官方 user mute strategies**（`pipecat/fundamentals/user-input-muting`）：app 级"暂时屏蔽用户输入"——
  `FirstSpeech` / `MuteUntilFirstBotComplete` / `FunctionCall` / `Always`。muted 时丢 VAD/中断/原始音频/转写帧。
  **与我们的 `half_duplex_mute_processor.py` 关系**（Phase 2 审计已核实并修正此处）：我们**复用了官方
  `AlwaysUserMuteStrategy`（`pipecat.turns.user_mute`）做 mute 决策**，只是因无 `LLMUserAggregator` 而
  手动接线 + 自实现帧抑制（镜像 `LLMUserAggregator._maybe_mute_frame`）。即"官方策略 + 自定义装配"，
  非另起炉灶。详见 `docs/PIPECAT_AUDIT.md` D 项。
- ⚠️ **与我们的"抢话"已知问题的关系**（HANDOFF 第四十五轮诊断）：half-duplex 解除静音按 `TTSStoppedFrame`
  （TTS 逻辑生成完毕）触发，而非音箱实际播放完毕——`resume_guard_ms`(300ms) 缓冲在长回复下不够。
  这条根因与 §5 的"turn 结束 ≠ 播放结束"是**同一时序鸿沟的两个面**，Phase 2/3 要一起审。
- Source: `api-reference/server/frames/system-frames`、`pipecat/fundamentals/user-input-muting`、llms-full §SystemFrame。

## 8. 运行时设置更新（`*UpdateSettingsFrame`）

- 每个 service 暴露 `Settings` 类，两种用法：① 构造时 `settings=`；② 运行中 push `*UpdateSettingsFrame`
  （TTS 即 `TTSUpdateSettingsFrame`）改设置。
- ⚠️ **对 Fish WebSocket 的限制**（结合 `FISH_AUDIO_REFERENCE.md` §7.5/7.7）：`prosody.speed` 等只能在
  WebSocket `start` 事件设一次，**逐句改需断连重连**——所以"运行时改 Fish 设置"在我们路径上受协议限制，
  不是所有字段都能热更。这与第二十八轮"Pipecat 放弃逐句数值语速"的决定一致。
- Source: `pipecat/fundamentals/service-settings`。

## 9. PipelineParams 完整清单 + Metrics

- **PipelineParams 字段（1.x）**：`audio_in_sample_rate` / `audio_out_sample_rate` / `enable_heartbeats` /
  `heartbeats_period_secs` / `heartbeats_monitor_secs` / `enable_metrics` / `enable_usage_metrics` /
  `report_only_initial_ttfb` / `send_initial_empty_metrics` / `start_metadata`。
  - ⚠️ **1.x 的 `PipelineParams` 已无 `allow_interruptions`**（旧版有）——中断现由 SystemFrame + turn
    strategies 默认处理。Phase 2 核对 `run_voice.py` 的 `PipelineParams(...)` 是否还在传已失效字段。
  - 设 `audio_out_sample_rate` 优于在 TTS service 单独设（统一全管道输出采样率；单独设会覆盖 PipelineParam）。
- **Metrics**（`enable_metrics=True`）：`TTFB`（首字节秒）/ `Processing Time` / `Text Aggregation`
  （首个 LLM token→首个完整句，仅 TTS）。`report_only_initial_ttfb` 只取每个 service 的首个 TTFB。
  - 我们的 `_LatencySpikeLogger`（自定义 FrameProcessor，量 VADUserStoppedSpeaking→首个 TTSAudioRawFrame）
    与官方 metrics 互补——Phase 3 可同时开 `enable_metrics` 拿框架自带的分段 TTFB。
- Source: `pipecat/fundamentals/metrics`、llms-full §PipelineParams。

## 10. P14「关键事实」复核结论表

| # | 原始陈述 | 复核结论 | 依据 |
|---|---|---|---|
| 1 | 两阶段=插在 brain↔tts 间的 FrameProcessor；TTS 默认按整句聚合 | ✅ **成立且更完整**：默认 `TextAggregationMode.SENTENCE`；自定义标签的原生路线 = `LLMTextProcessor`+`PatternPairAggregator`+`skip_aggregator_types` | §2、§3 |
| 2 | `FishAudioTTSService` latency 只有 normal/balanced 无 low；传 low 会被拒/忽略 | ✅ **成立，但措辞修正**：只 normal/balanced 被文档/默认祝福；`latency` 是 `str` 非枚举，`low` **原样透传给 Fish**（未定义行为，非"拒绝"） | §4 |
| 3 | P13 = audio-context 被销毁后音频到达 → no context ID；normal 放大竞态 | ✅ **成立并定位**：双游标 `_turn_context_id`(轮结束清) vs `_playing_context_id`(播完清)，normal 节奏下音频晚于 turn context 清理 | §5 |
| 4 | 非对称分工（开头标签好/正文烂）→ 双 LLM 流式取舍 | 框架侧无矛盾：§3 的整句聚合 + 自定义聚合器为流式逐句标签提供了原生抓手；句间情绪连贯仍需真人听感（`tag_stats` 测不出） | §3 |
| 5 | `reference/` gitignored，落盘不进公开仓库 | ✅ 已验证（`.gitignore:56`，P0 `git status reference/` 为空） | P0 manifest |

## 11. 已知不一致 / 版本注意（写 Phase 2 审计前必看）

- **文档版本**：docs 站持续更新到 1.x；个别页面示例混用 `PipelineWorker`(新) 与历史 `PipelineTask`(旧)。
  我们装的是 1.3.0，**一律以 venv 源码 + 1.0 迁移指南为准**。
- **Fish service 的 Sphinx autodoc 页**（`reference-server.../pipecat.services.fish.tts.html`）**未在 P0 落盘**
  （不在 map 出的 104 页内）；本综述 §4/§5 的 Fish/基类事实改用 **venv 源码**验证，权威性更高。
- **`latency` 非枚举**（§4）、**`PipelineParams` 无 `allow_interruptions`**（§9）、**官方 mute ≠ 我们的
  half-duplex**（§7）——三处最容易在审计时想当然，已逐一标注。

## 12. 给 Phase 2（链路审计）的待查清单（不在本 phase 解决）

1. `run_voice.py` 的 `PipelineParams(...)` 实参逐字段核对：采样率是否走 PipelineParam 统一、是否还传失效的 `allow_interruptions`、是否开 `enable_metrics`。
2. Fish `Settings` 装配：`latency` 当前值、`run_voice.py:103` 的 `low` 选项去留、`prosody_speed`/`temperature` 是否按 `FISH_AUDIO_REFERENCE.md` 最优。
3. VAD/turn：我们用 Silero 默认参数还是自调？是否启用 Smart Turn？与判停延迟基线（P6-C/P8-C spike）对照。
4. half-duplex（§5+§7 的同一时序鸿沟）：`resume_guard_ms` 是否该按"播放完成"而非 `TTSStoppedFrame` 触发。
5. 文本聚合模式：当前是默认 SENTENCE 还是 TOKEN？这直接影响 Phase 4 双 LLM 的插法与延迟。
6. P13（§5）：定位是改调用、subclass 还是上报上游——放 Phase 5。
