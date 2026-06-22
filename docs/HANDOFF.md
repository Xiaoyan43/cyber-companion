# HANDOFF — 上下文交接（2026-06-23，第四十八轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**新立项大 epic：P14 · Pipecat 链路最大化**（多 session）。用户想把 Pipecat 链路潜力全榨出来——
全量读 Pipecat + Fish Audio Pipecat 文档 → 审计现有链路配置是否最优/正确 → 批量测试 → 双 LLM
（两阶段标签，原 P8-C 已被吸收进此）决策讨论 → 修 P13。**第四十七轮只做了 epic 拆解 + 落
TASK_QUEUE，未开工**，并预先做了一轮联网研究拿到几个关键事实（见 `docs/TASK_QUEUE.md` P14 节
「关键事实」5 条，新 session 不必重新 derive）。
**第四十八轮已完成 P14 Phase 1 的 P0（文档全量落盘）**。**下一步 = `/clear` 后新 session 做 Phase 1 的
P1（写 `docs/PIPECAT_REFERENCE.md` 综述）**，详见 `docs/TASK_QUEUE.md` P14 节。

> 背景（已完成，无需再动）：第四十六轮用 spike round 2（扩大样本量）确认了语音路径标签退化明显比
> 文字路径差（长篇 60% 退化、多轮 opening_only 33%），这是 P14 要做双 LLM 的数据依据。**P13（Pipecat
> TTS latency=normal 多轮失声）仍待修，排在 P14 Phase 5。**

## 本轮已完成（2026-06-23，第四十八轮）

### P14 Phase 2 · 链路配置审计（紧接 Phase 1，同 session 完成）
- **产出**：`docs/PIPECAT_AUDIT.md`（拓扑评估 + A–F 六项逐项审计：现状/文档建议/判定/改动建议 + 结论汇总；**进 git，未 commit**）。
  读了 `run_voice.py` + 四个 processor/config 文件，逐项对照综述。
- **核心结论：无 🔴 阻断性错误**。
  - ✅ **正确**：拓扑符合官方 cascaded（brain 占 LLM slot、无 context aggregator 是有意设计）；`PipelineParams`
    干净（**没误传已失效的 `allow_interruptions`**，metrics 开，in16k/out44.1k 与 Fish service 一致）；
    VAD `stop_secs=0.4`（>默认 0.2）是真机有意权衡；**文本聚合 = 默认 SENTENCE，即双 LLM 的最优基线**。
  - 🔴 **唯一明确要改**：`run_voice.py:103` 的 `latency` 允许集合含 `low`，但 Fish service 对 `low` 是未定义
    透传（非"被拒"）→ 归 Phase 5。
  - 🟡 **次优/取舍**：Fish 未设 `prosody`/`temperature`（Phase 3 可调）；无 Smart Turn（VAD-only，是取舍，
    改动大不轻动）；half-duplex `resume_guard`(300ms) 基于"bot 逻辑停说"非"音频实际播完"=**抢话根因**
    （与 P13 §5 同一时序鸿沟，Phase 3 真机量化）。
- **🔧 审计中修正了一处综述偏差**：half-duplex **复用了官方 `AlwaysUserMuteStrategy`**（`pipecat.turns.user_mute`），
  是"官方策略 + 自定义装配"而非另起炉灶——已回填修正 `docs/PIPECAT_REFERENCE.md` §7。

### 🗣️ 用户真机反馈（2026-06-23，已并入审计文档，重排 Phase 3 优先级）
- **症状 1：「每次还没说完，pipecat 就开始回话了」** = **判停过早**。→ 审计 §C **从「🟡 取舍」提级为 🔴
  Phase 3 最优先**。**根因已查清（本轮零真机代码核实，写进审计 §C）**：brain 触发于 STT 最终 `TranscriptionFrame`，
  它由 **Doubao STT 服务端 endpointing** 发出（`has_definite`），窗口 = `end_window_size` =
  **`CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS`，默认仅 300ms**——一次换气就超 300ms 被判说完。
  **Silero VAD `stop_secs=0.4` 不是主因**。
  - **✅ 已修复并真机验证**：`DEFAULT_ASR_END_WINDOW_MS` 300→**800**（`voice_config.py` + test 同步，4 passed）。
    用户真机确认"正常说话不再被打断、延迟可接受"。`.env` 实验配置已清理还原（DATA_DIR 改回 `./data`）。
  - **⚠️ 残留（用户认可，归未来 ASR 选型）**：800 是纯静音窗口有天花板——"停顿稍久仍会被切"。根治=**语义判停**。
    查清：火山 **有** `ASRConfig.VADConfig.AIVAD`（LLM 判语义完整性+静音双重判断，限免公测，`reference/14.md:1111`），
    但绑在 **RTC-AIGC/Dialog 产品**上，**不是**我们 BigASR 流式端点（`sauc` 只有纯静音窗口）。
    → **「支持语义判停」= 后续 ASR 选型头号标准**（用户已表示后面换最合适的 ASR）。
- **症状 2：「latency 最高音质档用不了」** = **P13**（`normal` 第二轮起失声）。用户确认最高音质暂不可用，
  必须停 `balanced`，等 Phase 5 修。
- ⚠️ **别混淆 C 与 D**：C = **用户说话**被过早判停打断（抢答）；D = **bot 说话**被过早解除静麦（抢话）。两个不同问题。

### P14 Phase 1 · P1 · 写 `docs/PIPECAT_REFERENCE.md` 综述（紧接 P0，同 session 完成）
- **产出**：`docs/PIPECAT_REFERENCE.md`（13 节 + 关键事实复核表 + Phase 2 待查清单，192 行；**进 git，未 commit**）。
  来源 = P0 落盘（llms-full.txt 选择性取段）+ venv 源码交叉验证，全程未把 2.9MB 整份读入。
- **P14 三条关键事实复核结论**：
  - **#1 ✅ 成立且更完整** — TTS 默认 `TextAggregationMode.SENTENCE`；**自定义标签的原生路线 =
    `LLMTextProcessor` + `PatternPairAggregator` + `skip_aggregator_types`**（双 LLM 第二阶段用这个插，
    不是在 `companion_brain.py` 串行调两次 LLM）。
  - **#2 ✅ 成立但措辞要改** — Fish `latency` 是 `str` 不是枚举；只 normal/balanced 被文档/默认祝福，
    传 `low` 会**原样透传给 Fish 服务端**（未定义行为，**不是**"被拒/忽略"）。`run_voice.py:103` 的 low Phase 5 处理。
  - **#3 ✅ 成立并定位根因** — 基类双游标：`_turn_context_id`（轮结束/合成完时清）vs `_playing_context_id`
    （音频播完才清）；`latency=normal` 节奏下音频帧晚于 turn context 清理 → "no context ID" → 第二轮起失声。
- **🔑 额外关键发现（影响整个 epic 的框架前提）**：**本机装的是 `pipecat-ai 1.3.0`，`run_voice.py` 已经在用
  1.0 API（`PipelineWorker`/`PipelineParams`），与官方 docs 同代——没有迁移断层**。
  HANDOFF/ARCHITECTURE_SNAPSHOT 里残留的 "PipelineTask/PipelineRunner" 说法**已过期**，以综述 §0 为准。
  另外两个易踩坑点：1.x `PipelineParams` 已无 `allow_interruptions`；官方 `user_mute_strategies`（开场/函数防打断）
  ≠ 我们的 `half_duplex_mute_processor`（bot 说话静麦）——两者别混（综述 §7/§9）。

### P14 Phase 1 · P0 · 文档全量落盘（`/architect` 把 Phase 1 拆成 P0 落盘 + P1 综述）
- **全部产出 gitignored 在 `reference/pipecat/`（未进 git，7.4MB）**：
  1. **`docs.pipecat.ai/llms-full.txt`（2.9MB）** = 官方文档站**全站 433 页正文**，每段带 `Source:` URL；
     `llms.txt`（73KB）= TOC 索引。**免 firecrawl 额度**——curl 直取 Mintlify 的 llms 导出，比逐页抓更干净。
  2. **`reference-server.pipecat.ai/`** = Sphinx Python API autodoc **全量 104 页**（firecrawl download，每页 `index.md`）。
     KEY 页已在 manifest 标注（`tts_service.html` ← P13 根因、`frame_processor.html` ← 双 LLM 插点、
     `transports/local/audio.html` ← LocalAudioTransport、`base_output.html` ← 抢话根因 等）。
  3. **`fish.audio/`** 2 页（Fish→Pipecat 集成指南 + AI companion 博客，从既有 `.firecrawl/` 缓存复制，
     抓于 06-19/06-20，⚠️时效见 manifest，P1 若与官方矛盾以 docs.pipecat.ai 为准）。
  4. **`reference/pipecat/_MANIFEST.md`** = URL↔文件导航 + KEY 页清单 + 给 P1 综述的复核指引（**P1 先读这份**）。
- **过程坑（已解决）**：docs.pipecat.ai 整站 firecrawl download **因额度不足失败**（需 435 credits 仅剩 355），
  当场改用 `llms-full.txt` 免额度方案——结果反而更优（单文件含全部页 + 来源标注）。refserver（104 页）额度够，正常抓完。
- **验收 ✅**：`git status reference/` 为空（gitignored 第 56 行 `reference/` 生效）；三来源落盘齐全；manifest 成形。
  **抓取全程未把正文读进对话上下文**（只读元信息/页数），context 未爆。

## 上一轮已完成（2026-06-23，第四十七轮）

### P14 epic 立项 + 一轮联网研究（未写任何代码）
- **拆解 + 落 TASK_QUEUE**：把用户的"读全量 Pipecat/Fish 文档 → 审计链路 → 批量测试 → 双 LLM
  讨论 → 修 P13"拆成 P14 五个 phase，写进 `docs/TASK_QUEUE.md` P14 节。每个 phase 一个干净 session。
- **联网研究预拿的关键事实**（已写进 P14 节「关键事实」5 条，最重要的两条）：
  1. Pipecat 两阶段标签的正确形态 = **FrameProcessor 插在 brain↔tts 之间**（Pipecat 原生，TTS 默认
     按整句聚合），不是在 `companion_brain.py` 串行调两次 LLM。
  2. **Pipecat 官方 `FishAudioTTSService` latency 只支持 `normal`/`balanced`，没有 `low`**——但
     [run_voice.py:103](../backend/realtime/run_voice.py:103) 却允许传 `low`（传进去会被拒/忽略）。
- **未决定的事**：双 LLM 具体形态、链路配置是否最优——都要等 Phase 1 文档落盘 + Phase 2 审计后才有依据。
- **用户决定**：写进 TASK_QUEUE 后 `/clear`，新 session 从 Phase 1（文档全量落盘）开始。

## 上一轮已完成（2026-06-22，第四十六轮）

### P8-C spike round 2 — 扩大样本量，结论反转
- **动机**：第四十五轮 spike 只用 4 个孤立单轮 fixture、N=8，"不比文字路径差"的结论置信度不够
  （场景窄+样本小）。本轮设计 3 个新场景补盲点，并把样本量提到统计量级。
- **新增 fixture**（[backend/scripts/companion_brain_tag_eval.py](../backend/scripts/companion_brain_tag_eval.py)）：
  - `multi_turn_softening`：3 轮真实对话历史（赌气→服软），用 `brain.remember()` 持久化前两轮，
    只对最后一轮算 `tag_stats`——测真实多轮上下文（而非孤立单轮）下标签是否依然达标。
  - `long_narrative`：诱导讲长故事，测长回复下标签密度/位置规则是否撑得住（P5-F 去掉长度上限后
    从未测过这个维度）。
  - `emotional_turn`：单轮内委屈→讽刺的语气转折，测转折点是否真补了新标签。
  - 脚本新增 `--extended` 开关 + 独立的 `--repeats-long-narrative`（默认10）/`--repeats-multi-turn`
    （默认15）——长篇/多轮场景每次调用成本明显更高（sanity check 时 long_narrative 单次就生成了
    81 句故事），不能和短 fixture 用同一个 N。
- **结果**（真实计费 API 调用，临时 `MemoryStore`，未碰生产库）：

  | fixture | N | repeat 堆叠退化 | opening_only 退化 | tagged_sentence_ratio |
  |---|---|---|---|---|
  | 原 4 个孤立单轮 | 25 | 0/25 | 16%–24% | 0.70–0.80 |
  | emotional_turn | 25 | 0/25 | 0/25 | 0.65 |
  | **long_narrative** | 10 | **60%（6/10）** | 0/10 | **0.16** |
  | **multi_turn_softening** | 15 | 0/15 | **33%（5/15）** | 0.61 |

- **结论（推翻第四十五轮）**：
  1. 原 4 个 fixture 在 N=25 下 opening_only 退化率 16%–24%，比 N=8 测出的 12.5% 高近一倍，也明显
     高于文字路径基线（4%–12%）——小样本低估了退化率。
  2. **长篇展开是新发现的严重盲点**：60% 样本出现同标签重复堆叠，整篇平均仅 16% 句子带标签。
  3. 真实多轮历史场景 opening_only 退化率（33%）比孤立单轮场景还高。
  - **语音路径标签退化明显比文字路径差，长篇/多轮场景下更严重**——这是真实问题，不是"暂不紧急"。
- **用户决定**：确认推进 P8-C 两阶段拆分。`docs/TASK_QUEUE.md` P8-C 节已更新为"已确认推进"，
  下一步先选延迟杠杆，且要优先确保长回复路径也能稳定走两阶段。

## 上一轮已完成（2026-06-22，第四十五轮）

### 1. P8-C 前置 spike — Pipecat 端到端延迟基线 + 标签退化率统计
- **新建** [backend/scripts/companion_brain_tag_eval.py](../backend/scripts/companion_brain_tag_eval.py)：
  仿照 `tagger_eval.py` 模式，用固定文字 fixture 直接驱动 `CompanionBrain.stream_turn()`（绕开 STT/麦克风），
  跑 Pipecat 单阶段标签架构（`companion_brain.py` 的 `VOICE_MODE_INSTRUCTION` 仍未接两阶段标签器）的
  退化率统计。**用临时 `MemoryStore(db_path=tempfile...)`，天生隔离，不碰生产库**。
  - N=8 结果：`opening_only` 退化 1/8（3/4 fixture）、`max_repeat>1` 全部 0/8，跟文字路径 P10-P1
    基线（4%–12%）同量级，**没有明显比文字路径更差**——反直觉的发现，原以为单阶段架构会更糟。
- **真机延迟基线重测**：在 `run_voice.py` 临时加了 `_LatencySpikeLogger`（FrameProcessor，插在
  `tts`→`transport.output()` 之间，量 `VADUserStoppedSpeakingFrame`→首个 `TTSAudioRawFrame` 耗时，
  **用户已要求保留**，标注清楚是 spike 工具非生产代码）。跑了 10 轮真实对话（grok-4.20 + Fish Audio
  WebSocket 新配置）：稳态中位数 **~2.19s**（排除一次 11.7s 冷启动 + 一次 0.18s 疑似伪迹）。
  **对比旧基线（P6-C, DeepSeek+Doubao streaming, ~2.3s）基本没变**——两次 provider 切换，延迟既没
  改善也没退化。

### 2. 真机排查"容易抢话"——只读代码，未改任何逻辑
- 根因定位（读 Pipecat 库 `transports/base_output.py` 确认）：half-duplex 解除静音是按
  **`TTSStoppedFrame`（TTS 逻辑生成完毕）**触发，**不是按音箱实际播放完成**触发——音频帧从生成到
  真正经 PyAudio 写完设备之间天然有滞后，`resume_guard_ms`（默认 300ms，[voice_config.py:24](../backend/realtime/voice_config.py:24)）
  只是个很短的缓冲。P5-F 去掉回复长度上限后，回复变长，这个"逻辑结束"和"实际放完"的差距被放大，
  300ms 缓冲没跟着调——这很可能是用户感觉到"容易抢话"的根因。**未修复，仅诊断**（用户明确要求先不改代码）。

### 3. 🐛 发现新 bug（P13，已记入 TASK_QUEUE，高优先级，未修）
- 测试 latency=normal 时：Pipecat 真机会话**第一轮正常出声，第二轮起 TTS 完全失声**（文字侧
  STT→LLM 全程正常）。DEBUG 日志确认根因：`FishAudioTTSService#0 unable to append audio to
  context: no context ID provided`——Fish Audio 确实把音频传回来了（`TTFB` 日志证明），但 Pipecat
  本地 audio-context 在上一轮 `TTSStoppedFrame` 时已被清理，新音频对不上 context id，被静默丢弃。
  `latency=balanced` 跑 10 轮全部正常，怀疑是 `normal` 档生成节奏放大了 context 清理与音频到达的
  竞态。**已把 Pipecat 侧 latency 退回 `balanced`（确认稳定）；未继续测 `low`**——先搞清楚根因更
  划算。详见 `docs/TASK_QUEUE.md` 「P13」节。

### 4. ⚠️ 生产数据库污染事故 + 清理（已完整还原）
- 两次"隔离"真机测试**都失败了**——以为 `CYBER_COMPANION_DATA_DIR=/tmp/...` 命令行环境变量能隔离，
  实际上 `run_voice.py:32` 的 `load_dotenv(override=True)` 会用 `.env` 里的 `CYBER_COMPANION_DATA_DIR=./data`
  覆盖掉命令行传的值——两次测试的 40 条 messages + 1 条 memory 全部真实写进了生产库
  `data/cyber_companion.db`，mood_state/relationship_state 也被测试对话的情绪信号污染。
- **已发现并完整清理**：备份当前状态到
  `data/backups/cyber_companion_pre_p8c_cleanup_20260622_220247.db`，删除全部污染的
  messages（id 4849–4888）+ memory（id 473），mood_state/relationship_state 还原到污染前
  （当天 08:28 备份）的值。验证：生产库最大消息 id 已回到 4848，与备份一致，无残留改动。
- **建立了强制隔离规范**（记入 `docs/TASK_QUEUE.md`）：以后任何 Pipecat 真机测试，**必须直接临时
  改 `.env` 文件里的 `CYBER_COMPANION_DATA_DIR` 这一行**，不能用命令行 `VAR=value` 覆盖（会被
  `load_dotenv(override=True)` 吃掉，不生效）。`companion_brain_tag_eval.py` 不受影响（它直接传
  `db_path` 给 `MemoryStore`，绕开了这个问题）。
- `.gitignore` 新增 `data/pipecat_spike/`，作为以后隔离测试数据的统一存放位置。
- **用户已确认**：项目完工后这类测试数据要整体删除从零开始，不用现在维护长期归档。

### 5. 文字路径 latency: `balanced` → `normal`（用户明确要求，与 Pipecat 无关）
- [fish_audio.py:137](../backend/app/tts/fish_audio.py:137)：文字聊天路径的 Fish Audio TTS payload
  latency 改为 `"normal"`（最佳音质档）。同步更新 [test_tts.py:947](../backend/tests/test_tts.py:947)
  断言。**注意**：Pipecat 侧（`run_voice.py`）没有跟着改，仍是 `balanced` 默认（见上方 P13）——
  两条路径的 latency 配置现在是分开的，不要混淆。

### 6. P12 · 情绪识别旁路（Hume prosody）正式立项
- 之前只在 HANDOFF 里一句话带过，本轮在 `docs/TASK_QUEUE.md` 正式建了任务节，写清楚已拍板的结论
  （只取测量 API 当传感器、off-path 喂 kernel、第二档先 spike）、scope、验收标准。**仍未开工**。

### 7. P11 范围收紧 + 新增需求记录
- 用户拍板：P11（回复语言切换）**仅限文字路径**，语音路径不做。**新增需求**：不是单纯切换输出
  语言——每次回复要**同时展示中文译文**，比原计划复杂（多一步翻译 + UI 需双语呈现）。已记入
  `docs/TASK_QUEUE.md`，scope 待后续 `/architect` 时重新评估，**本轮未实施**。

## 上一轮已完成（2026-06-22，第四十四轮）
生产素材池 `config/idle_material_pool.json`（8条真实素材）+ P9-P2-B 真机验证 PASS（share intent
端到端验证通过，反重复指纹 FIFO 正确轮换）。完整报告见 `docs/P9_P2B_VERIFICATION.md`。

## 已修改文件（本轮，第四十八轮）
- **`reference/pipecat/`（全部 gitignored，不进 git）**：新增 `docs.pipecat.ai/`（llms-full.txt + llms.txt）、
  `reference-server.pipecat.ai/`（104 页）、`fish.audio/`（2 页）、`_MANIFEST.md`、`_maps/`（map JSON + 下载日志）。
- **[docs/PIPECAT_REFERENCE.md](PIPECAT_REFERENCE.md)（新增，进 git，未 commit）**：P1 综述，13 节；本轮 §7 回填了 Phase 2 的修正。
- **[docs/PIPECAT_AUDIT.md](PIPECAT_AUDIT.md)（新增，进 git，未 commit）**：Phase 2 审计报告，A–F 六项 + 结论汇总。
- [docs/TASK_QUEUE.md](TASK_QUEUE.md)：Phase 1（P0+P1）+ Phase 2 均标 ✅ 完成；Phase 3 抢答项 ✅ 已修。
- [docs/HANDOFF.md](HANDOFF.md)：滚到第四十八轮，Phase 1+2 完成 + Phase 3 抢答修复。
- **（已 commit `29d46a2`：上述 4 份 doc 的 Phase 1+2 版本）**
- **本轮 commit 之后的新改动（未 commit）**：`backend/realtime/voice_config.py`（`DEFAULT_ASR_END_WINDOW_MS`
  300→800，抢答修复）+ `backend/tests/test_voice_config.py`（断言 300→800，4 passed）+ 本批 doc 再更新
  （audit/handoff/taskqueue 记录 Phase 3 抢答结论）。`.env` 实验配置已还原（不进 git）。
- **本轮零 `backend/` 代码改动**（纯落盘 + 文档）。working tree 里 `companion_brain_tag_eval.py` 等第四十五/
  四十六轮的改动仍未 commit（沿用既有"未 commit"状态，等用户决定何时一起提交）。

## 当前未完成
- **P14 整个 epic 未开工**——只立项 + 拆 phase。下一步 = Phase 1 文档落盘。
- **P13 修复**（排进 P14 Phase 5）：根因已较清晰（库级 audio-context 竞态，见 P14「关键事实 #3」），
  待 Phase 1/2 把 Pipecat 库吃透后再定是改调用方式还是 subclass/上报上游。
- **双 LLM 两阶段拆分**（原 P8-C，吸收进 P14 Phase 4）——形态待 Phase 2 审计后定。
- **`run_voice.py:103` 允许 `low` 但官方 service 不支持**（P14「关键事实 #2」）——Phase 5 一起处理。
- **"抢话"问题未修复**——只诊断了根因，用户要求暂不改代码。
- **P11 新需求未实施**——scope 待 `/architect`。
- **P12（Hume prosody）未开工**——仅完成立项。
- 沿用未完成项：**P9-P2-C**（素材源真联网）、**P9-D**（投递层 epic，用户已确认暂缓）。

## 已知 bug / 风险
- **🐛 P13（新增，高优先级）**：见上方第3点，Pipecat TTS latency=normal 时多轮对话失声。
- **⚠️ `run_voice.py` 的 `load_dotenv(override=True)` 是个隔离测试的坑**——任何脚本/命令行环境变量
  覆盖 `CYBER_COMPANION_DATA_DIR` 都会被悄悄吃掉，必须直接改 `.env` 文件本身（见上方第4点的强制规范）。
  下次做任何 Pipecat 真机测试前**必须**先确认这一点，否则会再次污染生产库。
- **"抢话"架构性根因未修**（见上方第2点），不是阻断性 bug，但已确认是设计层面的问题，不是偶发。
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8、R4、标签器
  质量基线矛盾等。

## 推荐下一个最小任务
- **P14 Phase 3 · 批量测试**（新 session 第一件事）：跑 `docs/PIPECAT_AUDIT.md`「给后续 phase 的交接」列的三项——
  ① 真机量化"抢话"（测 bot 逻辑停说→实际播完间隔，定 `resume_guard_ms` 该多大）；② 对照
  `FISH_AUDIO_REFERENCE.md` §7 试 `temperature`/`prosody`；③ 复用 `_LatencySpikeLogger` + `enable_metrics`。
  **做真机测试前必读** `docs/TASK_QUEUE.md`「Pipecat 真机测试隔离规范」（**改 `.env` 文件，不能用命令行环境变量**，
  否则污染生产库）。详见 `docs/TASK_QUEUE.md` P14 Phase 3 节。
  **Phase 1（落盘+综述）+ Phase 2（审计）已全部完成。**

## 下一步只需读取
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（**P14 节**，尤其「关键事实」5 条）
- **做 P14 Phase 3（批量测试）**：先读 `docs/PIPECAT_AUDIT.md`「给后续 phase 的交接」+ `docs/TASK_QUEUE.md`
  「Pipecat 真机测试隔离规范」。Phase 1/2 已就绪，**不要重抓文档、不要重写综述/审计**；回溯原文去 `reference/pipecat/`。
- **后续 Phase 5 修 P13 时再读**：`.venv/lib/python3.11/site-packages/pipecat/services/fish/tts.py` +
  `pipecat/services/tts_service.py`（`InterruptibleTTSService` 的 context 生命周期）+ `backend/realtime/run_voice.py`
- **若做真机测试**：先读 `docs/TASK_QUEUE.md` 「Pipecat 真机测试隔离规范」节，确认改 `.env` 而非
  命令行环境变量

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike，确认过故意不提交）
- ❌ 全仓库扫描 / 与当前任务无关的模块
- ❌ 不要重新发起 P9-D 投递层讨论（用户已明确暂缓，除非用户主动提起）
- ❌ 不要在确认隔离规范生效前，再跑一次 Pipecat 真机测试

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
