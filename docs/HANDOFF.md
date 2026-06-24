# HANDOFF — 上下文交接（2026-06-24，第五十八轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P0「破音 / 音频欠载」已彻底定位根因并修复、真机双路径 PASS、已 commit `8d5b2fb`。** 破音与标签器、
Phase 4、Fish 采样率全部无关，根因是 pipecat `LocalAudioOutputTransport` 的 PyAudio 输出流缓冲欠载
（underrun）。**下一步主线 = B 标签器质量（P1）**：省略号幻觉、标签位置错位、停顿标签滥用——这些在本轮
真机里确认依旧存在（与破音是两码事，本轮未动）。

## 本轮已完成（2026-06-24，第五十八轮）

### 🎯 破音 P0 全链路定位 + 修复，已 commit `8d5b2fb`（真机 Fish + Doubao 双路径 PASS）
- **方法 = 真机隔离 + 静态代码排除，逐项证伪（不再凭日志猜，吸取前两轮连错教训）**。排除矩阵：

  | 嫌疑 | 怎么排除 | 结果 |
  |---|---|---|
  | Phase 4 / 双 LLM / 标签器 | 真机 `EXPRESSION_TAGGER=0`（=单 LLM）照样破 | ❌ |
  | Fish service / opus 解码 | 真机切 Doubao TTS 也破 | ❌ |
  | 采样率 44.1k | Doubao 24k 也破 | ❌ |
  | P15 字幕 tap | 静态：`put_nowait` 非阻塞、不碰音频帧 | ❌ |
  | `_LatencySpikeLogger` | 静态：每帧仅 isinstance、无 IO | ❌ |
  | 06-20 后所有 realtime commit | 没一个改音频输出路径 | ❌ |
  | 用户内置扬声器 / 蓝牙 | 用户确认一直用 MacBook 内置扬声器、设备没变 | ❌ |
  | **`LocalAudioOutputTransport` 输出缓冲** | **加 200ms 缓冲后破音消失** | ✅ **根因** |

- **根因（代码硬证据）**：pipecat `LocalAudioOutputTransport.start()`
  （`.venv/.../pipecat/transports/local/audio.py:155`）创建 PyAudio **输出**流时**没传 `frames_per_buffer`**
  （注意：那个 `int(sample_rate/100)*2 = 20ms` 是 **input** 流的，line 80/86，不是 output）。输出用
  PortAudio 默认小缓冲；输出是 **blocking write**（`run_in_executor` 里 `out_stream.write`，line 184），
  靠 event loop 持续及时喂帧。这台 2019 低配 MacBook 的 event loop 偶发停顿（SileroVAD onnx 推理 / jieba /
  网络回调）超过缓冲深度 → 供帧出 gap → underrun → 「耳机没插好」式破音。
- **修复**：`run_voice.py` 的 `_main_pipeline` 里新增 `_BufferedLocalAudioOutputTransport`（subclass，override
  `start()`：跳过父类 `LocalAudioOutputTransport.start`、走祖父 `BaseOutputTransport.start`，再自己 open 一个
  显式 `frames_per_buffer=int(sample_rate*0.2)`≈**200ms** 的输出流）+ `_BufferedLocalAudioTransport`（`output()`
  返回它），transport 装配改用 buffered 版本。**只动 `_main_pipeline` 真机路径，`_main_realtime`（Doubao S2S
  端到端，当前不走）未碰。**
- **真机验证 PASS**：先在 Doubao 下确认破音消失，再还原 Fish 确认 Fish 路径也不破——**修复在 transport 层、
  对所有 TTS 通用**。代价：输出缓冲变大，首音延迟理论上最多 +200ms（真机未觉明显；如嫌慢可把 `0.2` 调小到 `0.1`）。
- **8 个 realtime 测试绿**（`test_realtime_voice.py`），`py_compile` OK。

### memory 更新：豆包 TTS 质量信号 → TTS 选型重新打开
- 破音排查时为隔离 Fish，临时把语音 TTS 切到 Doubao（`CYBER_COMPANION_VOICE_TTS=doubao`）。用户顺带听感：
  **Doubao 音色不如 Fish 丰富，但「质量 / 自然度」感觉更高**。用户明确**不是现在换**，但标记 TTS 选型为后续
  要重新考虑的事。
- 已更新 memory `future-provider-swap-candidates`（把「TTS engine settled, Fish stays」软化为「Doubao 重新
  成为后续候选，质量维度」）+ MEMORY.md 索引行。注明破音不是 Fish 的问题、别混淆。

## 已修改文件（本轮）
- **commit `8d5b2fb`**：`backend/realtime/run_voice.py`——破音修复（import 加 `LocalAudioOutputTransport`；
  新增 `_BufferedLocalAudioOutputTransport` + `_BufferedLocalAudioTransport`；transport 装配改用 buffered 版本）。
  提交时照惯例**排除了 `_LatencySpikeLogger`**（临时删→commit→编辑加回工作区）。
- **未 commit（工作区）**：`backend/realtime/run_voice.py` 仅剩 `_LatencySpikeLogger`（用户要求保留不提交，
  44 行 diff）；本次 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` 交接更新（可随时 commit）。
- **`.env`（gitignored）**：本轮多次临时改 `CYBER_COMPANION_VOICE_TTS` / `EXPRESSION_TAGGER` 做隔离，
  **已全部还原到正常配置**（`CYBER_COMPANION_VOICE_TTS` 行已删=默认 fish_audio；`EXPRESSION_TAGGER=1`）。

## 未 commit 的历史遗留（仅剩 1 项，用户要求保留）
- **`backend/realtime/run_voice.py` 里的 `_LatencySpikeLogger`**：P8-C spike 的临时首音延迟探针（终端那行
  `[P8-C spike] user-stopped→first-audio = X` 就是它）。提交 `run_voice.py` 任何后续改动都要选择性 stage
  排除这段（本轮 commit 同样用「临时删→commit→编辑加回工作区」的方式做到的）。

## 当前未完成
- **B. 标签器质量（P1，下一步主线）**——真机确认依旧存在三类问题：
  ①**省略号幻觉**：`…` 结尾句被 Fish 合成出**原文不存在的内容 / 重复之前说过的话**（同旧记「bug 1 幻觉填充」
  一类，两阶段一直存在）；②**标签位置错位**：标签该放在所修饰跨度**开头**（Fish「位置即语义」），但标签器贴在
  标点前/句尾/逗号前，真机能听到错误标签；③**停顿标签滥用**：`[break]`/`[long-break]` 被塞句中。
  修复方向（未动手）：标签器 prompt 强调位置 + 省略号/尾部裸标签护栏 + 停顿标签护栏。架构边界：「位置合法性」
  可代码强制，「情绪恰当性」靠 LLM。
- **抢话 / barge-in**：`half_duplex=on` 默认禁止 Boxi 说话时打断（启动日志「no barge-in」），既有配置非回归。
  真正的抢话量化（审计 D，`resume_guard`）是 Phase 3 独立待办。
- **日语音色清单未接后端**：`fish-audio-ja-voice-shortlist` 只是预选名单。
- **沿用未完成项**：P14 Phase 3 剩余（Fish 调参 temperature/prosody，审计 B-2）、P12（Hume prosody，仅
  立项）、P9-P2-C（素材源真联网）、P9-D（投递层，用户暂缓）。
- **TTS 选型重评（新，低优先）**：用户对 Doubao 质量有兴趣，后续可能重新评估 TTS engine（见 memory）。不是现在。

## 已知 bug / 风险
- **🆕 标签器质量问题（B，P1）**：省略号幻觉 + 位置错位 + 停顿标签滥用，见上方「当前未完成 B」。
- **⚠️ 破音修复的首音延迟代价**：200ms 输出缓冲理论上最多 +200ms 首音延迟（真机未觉明显）。若后续要压首音
  延迟，可把 `run_voice.py` 里 `_BufferedLocalAudioOutputTransport` 的 `int(self._sample_rate * 0.2)` 系数
  调小（如 0.1=100ms）权衡破音容错 vs 延迟。
- **P13（已结案 = won't fix）**：Pipecat `latency=normal` 多轮失声——锁死 `balanced`，勿重开。
- **⚠️ `run_voice.py` 的 `load_dotenv(override=True)` 隔离坑仍在**（模块级、只读一次）：改 `.env` 后**必须整个
  重启 `dev:backend`** 才生效。注意 `EXPRESSION_TAGGER=on/off` 这行日志**不在 dev:backend 启动时打**，而在
  **前端发起语音、Pipecat 管线启动那一刻**才打（`run_voice.py:_main_pipeline`，日志格式
  `Voice tuning: ... CYBER_COMPANION_VOICE_EXPRESSION_TAGGER=on; ...`）。
- **真机隔离纪律（本轮血泪）**：破音根因前两轮连猜连错（先猜「底层固有」、再猜「Fish 采样率」均被证伪）。
  **必须真机隔离 + 静态代码排除，不要凭日志/记忆猜。** `.env` 实验后**务必还原**（本轮已还原）。
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8、R4 等。

## 下一步只需读取（按任务挑一个）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **B. 标签器质量（推荐）**：读 `backend/app/tts/expression_tagger.py`（`apply_expression_tags_to_sentence` +
  现有三重护栏 `_has_taggable_content`/`_preserves_original_wording` + `TAGGER_INSTRUCTION_TEMPLATE`）。
  重点是省略号 `…` 句的幻觉护栏 + 标签位置 prompt 强化。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（含 `reference/pipecat/`，Pipecat 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开 P13 normal 修复（已结案 won't fix）
- ❌ 破音已修复闭环，不要重查破音根因（除非修复回归）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **B. 标签器质量——先治「省略号幻觉」**（最影响听感的一类）：读 `expression_tagger.py`，给 `…` 结尾句加护栏
  （避免裸 `…` + 尾部标签单独送 Fish 触发幻觉合成），并在 prompt 强调标签位置即语义。**先 `/architect` 拆解**，
  small diff + 真机验证。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
