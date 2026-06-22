# Pipecat 链路配置审计（P14 Phase 2）

> 2026-06-23（第四十八轮）。拿 `docs/PIPECAT_REFERENCE.md`（§11 坑 + §12 待查）逐项对照现有链路。
> **本 phase 只审计出报告，零代码改动。** 每项：现状 / 文档建议 / 判定（✅正确 / 🟡次优 / 🔴错误）/ 改动建议。
> 审计范围 = `run_voice.py`、`companion_brain_processor.py`、`half_duplex_mute_processor.py`、
> `vad_processor.py`、`voice_config.py`（本机 `pipecat-ai 1.3.0`）。

## 链路拓扑（half_duplex=on，默认）

```
transport.input()
  → HalfDuplexMuteProcessor(input)      # 静麦 + 屏蔽 VAD/turn 帧（bot 说话时）
  → SileroVADProcessor(stop_secs=0.4)   # 自定义 VAD step（无 LLMUserAggregator）
  → stt (doubao_stream 默认)
  → HalfDuplexMuteProcessor(stt_out)    # 屏蔽转写帧 + resume_guard
  → CompanionBrainProcessor             # 占 LLM slot，流式吐 LLMTextFrame
  → tts (fish_audio 默认, s2-pro)
  → _LatencySpikeLogger                 # spike 工具（用户要求保留）
  → transport.output()
```
- **判定 ✅**：顺序符合官方 cascaded 拓扑（input→stt→llm→tts→output）。brain 占 LLM slot、自定义 VAD
  顶替 `LLMUserAggregator` 的 VAD 职责，是有意的"无 Pipecat context"设计（brain 自管记忆/上下文）。
- **注**：因此**无 `context_aggregator.user()/assistant()`**——`TTSTextFrame`（实际说出文本）不回灌 Pipecat
  上下文，由 brain 侧记忆系统负责。对我们的架构正确，但意味着 Pipecat 自带的"按词时间戳精确回写上下文/字幕"
  能力用不上（我们也不需要）。

---

## A. PipelineParams 实参核对（综述 §9/§12-1）
- **现状**（`run_voice.py:162/299`）：`enable_metrics=True`、`enable_usage_metrics=True`、
  `audio_in_sample_rate=16000`、`audio_out_sample_rate=output_sample_rate`（Fish=44100）。
- **文档建议**：1.x `PipelineParams` 字段见综述 §9；`allow_interruptions` 已不存在；`audio_out_sample_rate`
  走 PipelineParam 统一优于在 service 单独设。
- **判定 ✅ 正确**：无任何已失效字段（没误传 `allow_interruptions`）；metrics 已开；采样率走 PipelineParam，
  且与 Fish service 的 `sample_rate=44100` 一致（一致，无冲突）。
- **改动建议**：无。可选——`report_only_initial_ttfb=True` 能减少稳态 TTFB 日志噪音（纯日志偏好，非必要）。

## B. Fish service Settings 装配（综述 §4/§8/§12-2）
- **现状**（`run_voice.py:105-114`）：`Settings(voice=<config voice>, model="s2-pro", latency=<env>)`，
  `output_format="pcm"`、`sample_rate=44100`。**未设** `prosody_speed`/`prosody_volume`/`temperature`/
  `top_p`/`normalize`。`latency` 来自 `CYBER_COMPANION_VOICE_TTS_LATENCY`，默认 `"balanced"`。
- **文档建议**：`latency` 只 normal/balanced 被祝福；prosody/temperature 等可调表达力（`FISH_AUDIO_REFERENCE.md`
  §7）；这些字段 WebSocket 下只在 `start` 设一次、不可逐句热更（综述 §8）。
- **判定**：
  - latency 默认 `balanced` → ✅ **正确且安全**（避开 P13 的 normal 失声）。
  - 未设 prosody/temperature/normalize → 🟡 **次优**：走 Fish 默认（temperature≈0.7、normalize≈True）。
    我们文字路径曾试 temperature=0.85，语音路径没跟上；音质/表达力还有调参空间。
- **改动建议**：
  1. 🔴 **优先**：`latency` 允许集合含 `low`（`run_voice.py:103`），但 Fish service 对 `low` 是未定义透传
     （综述 §4）。Phase 5 处理——要么从允许集合删 `low`，要么实测 Fish 服务端对 `low` 的反应后再决定。
  2. 🟡 Phase 3 可对照 `FISH_AUDIO_REFERENCE.md` §7 试 `temperature`/`prosody_speed`，但记住 WebSocket
     start-once 限制，调参=改默认而非运行时热更。

## C. VAD / 轮次检测（综述 §6/§12-3）
- **现状**：`SileroVADProcessor(stop_secs=load_vad_stop_secs())`，默认 `DEFAULT_VAD_STOP_SECS=0.4`
  （`voice_config.py:23`）。**只覆写 `stop_secs`**，`start_secs`/`confidence`/`min_volume` 用 `VADParams` 默认。
  **无 Smart Turn**（`run_voice.py:325` 明确 "smart_turn=off — VAD-only endpointing"）。
- **文档建议**：默认 `stop_secs=0.2`；1.x 默认轮次结束策略 = Smart Turn 模型（语义判停）；VAD 参数默认通常够用。
- **判定**：
  - `stop_secs=0.4`（>默认 0.2）→ ✅ **正确（有意）**：注释写明"conservative，clip 了再 dial back"，
    我们 P6 调过判停，0.4 是真机权衡值。
  - 其余 VAD 参数用默认 → ✅ 正确。
  - 无 Smart Turn → 🟡 **次优（设计取舍）**：纯 VAD 静音超时判停，缺"用户是否说完一个完整意思"的语义判停；
    长停顿会被当轮次结束（早切）或 stop_secs 拉大后整体变慢。
- **⚠️ 用户真机反馈（2026-06-23，提级）**：用户报告"**每次还没说完，pipecat 就开始回话了**"——判停过早是
  **已确认的真实体验 bug，不是可接受的取舍**。本项从「🟡 取舍/不轻动」**提级为 Phase 3 优先项**。
- **🔍 已查清根因（2026-06-23，零真机代码核实）**：触发回话的是 STT 最终 `TranscriptionFrame`
  （`companion_brain_processor.py:44`）。它由 `doubao_streaming_stt_service.py:234` 在
  `response.has_definite or response.is_last` 时发出；`has_definite` =
  `any(u.definite for u in utterances)`（`doubao_streaming_protocol.py:121`）= **Doubao 服务端判定语句"已结束"**，
  由 `end_window_size` 控制（STT service line 109）= **`CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS`，默认仅 300ms**。
  → **抢答主因 = Doubao STT 服务端 endpointing 的 300ms 静音窗口太短**（一次正常换气/停顿就超 300ms 被判说完）。
  **Silero VAD `stop_secs=0.4` 不是主因**（它只喂 half-duplex 的 speaking 帧，不直接触发 brain）。
- **⚠️ 设计耦合（同一个旋钮管两件事）**：`CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS` **同时**接进
  ① Doubao STT `end_window_size`（`stt_service.py:80`）和 ② half-duplex `resume_guard_ms`（`run_voice.py:282`）。
  调大它会**同时**影响抢答(C) 和 抢话(D) 的窗口——方向一致（都想要更长）但理想值未必相同。
- **改动建议**：
  1. **便宜旋钮（Phase 3 真机，纯 env 零代码）**：把 `CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS` 从 300ms 调大
     （试 700–1200ms），真机听抢答是否消失、响应延迟是否可接受。
  2. **小重构（视真机结果）**：若 C/D 理想值冲突，把这个 env 拆成两个（Doubao endpointing 一个、resume_guard 一个），
     解开耦合后各自调。
  3. **稳健（大改，暂不做）**：接 Smart Turn 语义判停，需引入 aggregator，与"无 Pipecat context"设计冲突。

## D. half-duplex 静麦（综述 §5/§7/§12-4）
- **现状**（`half_duplex_mute_processor.py`）：**复用 Pipecat 官方 `AlwaysUserMuteStrategy`
  （`pipecat.turns.user_mute`）** 做 mute 决策，但因无 `LLMUserAggregator` 而手动接线（standalone），
  并镜像 `LLMUserAggregator._maybe_mute_frame` 的帧抑制。`input` 角色静麦 + 屏蔽 VAD/turn 帧；`stt_out`
  角色屏蔽转写帧 + `resume_guard`（= `asr_end_window_ms`，默认 300ms）。静麦时给 STT 喂静音 PCM
  （不饿死 Doubao WebSocket）。
- **文档建议**：官方 mute strategies 正常经 `LLMUserAggregatorParams` 接线（综述 §7）。
- **判定**：
  - 复用官方 strategy + 手动接线 → ✅ **正确**：**比综述 §7 说的"我们的 half-duplex ≠ 官方 mute"更接近官方**——
    mute *决策* 用官方 `AlwaysUserMuteStrategy`，只是 *接线/帧抑制* 因无 aggregator 而自实现。**（本审计据此修正
    综述 §7 的措辞偏差：不是另起炉灶，而是官方策略 + 自定义装配。）**
  - resume_guard 基于 *bot 逻辑停说*（strategy 看 bot speaking 状态，源于 `TTSStoppedFrame` 链）→ 🟡 **次优**：
    与综述 §5 的"turn 结束 ≠ 播放结束"同源——300ms guard 在长回复下不足，是"抢话"根因。
- **改动建议**：抢话修复候选——让 resume 以"音频实际播完"（如 `BotStoppedSpeakingFrame` 经 transport 实测播放
  完成）为准，或把 `resume_guard_ms` 调大/做成自适应。与 P13（§5）是同一时序鸿沟的两面，**建议 Phase 3 真机量化
  后一起在后续 phase 修**，本 phase 不改。

## E. TTS 文本聚合模式（综述 §3/§12-5）
- **现状**：`run_voice.py` 构造 `FishAudioTTSService` **未传 `text_aggregation_mode`** → 用基类默认
  `TextAggregationMode.SENTENCE`。
- **文档建议**：默认 SENTENCE（整句合成，藏请求开销）；TOKEN 更低延迟但牺牲整句韵律；自定义标签走
  `LLMTextProcessor`+`PatternPairAggregator`（综述 §3）。
- **判定 ✅ 正确**：SENTENCE 对"整句情绪标签 + 韵律"最友好，是双 LLM 标签方案的良好基线（不是 TOKEN）。
- **改动建议**：无（现状即最优基线）。**Phase 4 双 LLM 设计时**，第二阶段标签器应做成插在 brain↔tts 间的自定义
  FrameProcessor + 可能配 `PatternPairAggregator` 识别标签边界，**保持 SENTENCE 聚合**——本项是 Phase 4 的输入，不在此改。

## F. P13（latency=normal 多轮失声，综述 §5/§12-6）
- **⚠️ 用户真机确认（2026-06-23）**：用户报告"**latency 的最高音质档位用不了**"——即 `normal`（最佳音质档）
  实际不可用，正是 P13 的失声现象。**最高音质暂时拿不到**，必须停在 `balanced` 直到 Phase 5 修复。
- **判定**：根因已在综述 §5 定位（基类双游标 `_turn_context_id` vs `_playing_context_id` 竞态）。
  当前默认 `balanced` 已规避（见 B）。
- **改动建议**：放 **Phase 5**——确认是改调用方式 / subclass 覆写 / 上报上游；与 B-1（`low` 选项）一起处理。

---

## 审计结论汇总

| 项 | 判定 | 一句话 |
|---|---|---|
| 拓扑 | ✅ | 符合官方 cascaded，brain 占 LLM slot，无 context aggregator 是有意设计 |
| A PipelineParams | ✅ | 干净，无失效字段，metrics 开，采样率一致 |
| B Fish Settings | 🟡+🔴 | latency 默认 balanced 安全；`low` 选项是透传风险（Phase 5）；prosody/temp 可调（Phase 3） |
| C VAD/turn | ✅+🔴 | **用户真机确认"还没说完就抢答"=判停过早，已提级 Phase 3 优先**；先查 Silero VAD vs Doubao STT 谁先 finalize |
| D half-duplex | ✅+🟡 | 复用官方 strategy（修正综述 §7）；resume_guard 基于逻辑停说=抢话根因 |
| E 文本聚合 | ✅ | 默认 SENTENCE 即最优基线，Phase 4 双 LLM 沿用 |
| F P13 | — | 根因已定位，Phase 5 修 |

**没有发现 🔴 阻断性错误**；唯一明确要改的是 `latency` 允许集合里的 `low`（B-1，Phase 5）。其余是 🟡 次优/取舍，
分别归入 Phase 3（调参/真机量化抢话）、Phase 4（双 LLM）、Phase 5（P13+low）。

## 给后续 phase 的交接
- **Phase 3（批量测试）**——优先级按用户真机反馈重排：
  - **🔴 最优先：判停过早（C，用户"每次还没说完就抢答"）**。**根因已查清（见 §C）= Doubao STT 服务端
    `end_window_size=300ms` 太短**。真机第一步 = 把 `CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS` 调到 700–1200ms 听效果。
    注意它与 half-duplex resume_guard 共用一个 env（§C 耦合说明）。
  - ② 抢话（D）——测 bot 逻辑停说→实际播完间隔，看 `resume_guard_ms` 该多大（注意：与 C 是两回事，C 是
    用户说话被打断、D 是 bot 说话被打断）。
  - ③ 对照 `FISH_AUDIO_REFERENCE.md` §7 试 temperature/prosody（B-2）；④ 复用 `_LatencySpikeLogger` + `enable_metrics`。
  - 做真机测试前必读「Pipecat 真机测试隔离规范」（改 `.env`，不能用命令行环境变量）。
- **Phase 4（双 LLM）**：基线 = SENTENCE 聚合（E）+ brain↔tts 间自定义 FrameProcessor（综述 §2/§3）。
- **Phase 5**：P13（F）+ `low` 选项（B-1）一起修。
- **修正项**：本审计 D 修正了综述 §7 的措辞（half-duplex 是"官方策略+自定义装配"，非另起炉灶）。
