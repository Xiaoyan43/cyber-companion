# HANDOFF — 上下文交接（2026-06-24，第五十七轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P14 Phase 4（双 LLM 两阶段语音标签）已 commit 落地（含首音延迟修复 + 并发预贴标），但真机暴露一个
独立的「破音 / 音频欠载」听感问题未解**。标签效果（逐句出标签、不堆开头）真机 PASS；首音延迟修复
真机 PASS（4.9s→~2.5s）。**下一步 = 先用「关标签器听破音是否还在」一刀切分清破音责任**（A 任务），
再修标签器质量（B 任务）。本轮两个 commit：`a1232b4` + `d153991`。

## 本轮已完成（2026-06-24，第五十七轮）

### 根因坐实：首音延迟卡点是 TTS 的 SimpleTextAggregator lookahead，不是上轮猜的 AggregatedFrameSequencer ✅
- 上轮（第五十六轮）怀疑首音延迟卡在 Pipecat `AggregatedFrameSequencer` 的帧排序机制。本轮**读源码坐实
  是错的**——`AggregatedFrameSequencer`（`pipecat/utils/context/aggregated_frame_sequencer.py`）只管
  「skip 类型帧」（如代码块）排队，与正文逐句流程无关。
- **真正卡点 = TTS 自带的 `SimpleTextAggregator`**（`pipecat/services/tts_service.py:286` 的 `_text_aggregator`，
  `pipecat/utils/text/simple_text_aggregator.py:78-121`）：它对每个 `TextFrame` 逐字符检测句末，遇到句末
  标点后**置 `_needs_lookahead=True`、不立即判定**，必须等**下一个非空白字符**到达才调 NLTK 确认边界。
  在我们的链路里这个「下一个字符」只能来自**第 2 句**——所以第 1 句被晾在 TTS 缓冲区，直到第 2 句的标签
  调用完成、文本流入，才确认第 1 句句末→开始合成。精确解释了上轮「首音跟第 2 句标签完成时刻强相关」。

### P14 Phase 4 land + 首音延迟修复 ✅ 已 commit `a1232b4`（真机 PASS）
- **修复**（外部高手建议 + 本机 1.3.0 源码逐条核实）：`ExpressionTaggerProcessor` 推下游的帧从
  `LLMTextFrame` 改成 **`AggregatedTextFrame(tagged, AggregationType.SENTENCE, raw_text=sentence)`**。
  `tts_service.py:683-684` 对 `AggregatedTextFrame` **直接进 `_push_tts_frames`、跳过内置
  `SimpleTextAggregator` 的 lookahead**——等于让我们的 processor 成为唯一的句子边界权威。
  （`raw_text` 传纯句，TTS 内部 context/word-timestamp 看不到 `[标签]`。）
- **这个 commit 含整套 P14 Phase 4（P0+P1+P2）**：`expression_tagger.py`（逐句标签函数 + 三重保真护栏）、
  `expression_tagger_processor.py`（新建）、`run_voice.py`（管线装配 + tagger 门控）、`companion_brain.py`
  （brain 不再自贴标）、`voice_config.py`（开关）+ 测试。**提交时排除了 `_LatencySpikeLogger`**（见下）。
- **真机验证 PASS**：标签效果（逐句出标签、不堆开头、保真护栏拦改词）+ 首音延迟均值从上轮 ON 的
  **4.90s 降到 ~2.5s**（2.17–2.73s，接近 tagger-OFF 基线）。机制坐实：首音早于「第 2 句标签完成」时刻。
- 提交前 45 个相关测试绿（`test_expression_tagger` / `test_expression_tagger_processor` / `test_companion_brain`）。

### P14 Phase 4 并发预贴标 ✅ 已 commit `d153991`（真机：延迟未退化、按序、中断正常）
- `ExpressionTaggerProcessor` 逐句调度从**串行**（每句 `await tag` 后才处理下一句）改成**并发**：每句断好
  即 `asyncio.create_task` 立刻发起标签调用（一个回复内所有句子并行在飞），单个 per-turn 排空协程
  `_drain` 按句序 `await` 各 task 并推下游，保证 `Start → 所有标签句 → End` 顺序。`prior_context` 在断句
  时即构建（不依赖标签完成）。中断 `_abort_turn` bump `_turn_id` + 取消在飞 task + 排空协程，drainer 推
  前校验 turn_id 丢弃 stale。`LLMFullResponseEnd` 投哨兵 + 等排空协程 flush 完才放行 End。
- **目的**：把后续句子的标签往返藏进前句播放时间里、避免句间 gap。
- **新增 2 个并发回归测试**（绕过 pipecat 帧管线、直接驱动调度方法，不脆）：乱序完成仍按句序释放 /
  中断丢弃在飞句。**47 个相关测试全绿**。
- **真机结果**：首音延迟未退化（~2.5–2.8s），标签按序、中断不串句。**但绵密度问题没改善**——见下方
  「破音」节（破音不是时序问题，并发预贴标治不了它，但它本身正确独立、该留）。

## 本轮真机暴露的两个独立新问题（关键，下一步主线）

### A.「破音 / 音频欠载」——与标签器、与本轮改动都无关，音频管线层（P0 调查）
- **现象**（用户原话）：破音**在没有任何标签的地方也出现**，整体听感像「带耳机听歌但耳机没插好」。
  **与「标签贴错」是两回事**——标签贴错是能听到错误标签声音；破音是音频本身的丢帧/断续。
- **判断**：「耳机没插好」≈ 实时音频**输出缓冲欠载（buffer underrun）**的典型症状。**并发预贴标已消除
  了「等标签」的时序依赖、破音却照旧 → 破音不是时序问题，是音频流层面的问题。**（本轮我连错两次方向：
  先猜「缓冲余量」、再猜「mid-sentence 标签碎音」，都被真机听感否掉。不要再凭日志瞎猜，必须真机隔离。）
- **下一步该做的隔离实验（P0，按信息量排序）**：
  1. **关标签器（`.env` `CYBER_COMPANION_VOICE_EXPRESSION_TAGGER=0`）长聊、仔细听**：破音**照样在**→ 与整个
     Phase 4 两阶段无关，是更底层（Fish 输出采样率/opus 解码/transport 输出/本机音频环境），其实一直都在；
     破音**消失**→ 才是两阶段 per-sentence 合成路径引入的。**这一步能一刀切分清责任，必须先做。**
  2. 视 #1 结果，再查 Fish 每句独立合成的音频边界（`tts_service.py:_stream_audio_frames_from_iterator`
     的重采样/字节对齐）或输出 transport 缓冲。
- ⚠️ 测完记得把 `.env` 改回 `=1`（同上轮那个坑）。

### B. 标签器质量——位置错位 + 停顿标签滥用 + 省略号幻觉（P1）
- **位置错位**：标签该放在所修饰跨度的**开头**（Fish「位置即语义」染色其后的字），但标签器把标签贴在
  **标点前/句尾/逗号前**——真机能听到错误标签。实例：`你想听哪部分细讲？ [curious]`、`大多数人已经爽得
  太习惯[sighing]，`、`你真想天天找我[curious]，…试探我[curious]？`（`[curious]` 还重复了两次）。
- **停顿标签滥用**：`[break]`/`[long-break]` 被塞在句中（`不让算法继续喂你开始[long-break]，可你看[break]`）。
- **省略号幻觉**：`…` 结尾句被追加 `[break] [long-break] [a little worried]` 等尾部裸标签 + `…` 被切成独立
  碎片单独送 Fish → Fish 对「光一个 `…` + 尾部标签」**幻觉合成出原文没有的声音/话**。同 HANDOFF 旧记
  「bug 1 幻觉填充」一类，可能两阶段一直存在。
- **修复方向（未动手）**：标签器 prompt 强调位置 + 加位置/停顿标签护栏 + 省略号/尾部裸标签护栏。架构边界：
  「位置合法性」可代码强制，「情绪恰当性」靠 LLM。

## 已修改文件（本轮）
- **commit `a1232b4`**：`backend/app/tts/expression_tagger.py`、`backend/realtime/companion_brain.py`、
  `backend/realtime/run_voice.py`（仅 Phase 4 装配，排除 `_LatencySpikeLogger`）、
  `backend/realtime/voice_config.py`、`backend/realtime/expression_tagger_processor.py`（新建）、
  `backend/tests/test_companion_brain.py`、`backend/tests/test_expression_tagger.py`、
  `backend/tests/test_expression_tagger_processor.py`（新建）。
- **commit `d153991`**：`backend/realtime/expression_tagger_processor.py`（串行→并发调度）+
  `backend/tests/test_expression_tagger_processor.py`（+2 并发测试）。
- **未 commit（工作区）**：`backend/realtime/run_voice.py` 仅剩 `_LatencySpikeLogger`（用户要求保留不提交）；
  `docs/HANDOFF.md` + `docs/TASK_QUEUE.md`（本次交接更新，可随时 commit）。

## 未 commit 的历史遗留（仅剩 1 项，用户要求保留）
- **`backend/realtime/run_voice.py` 里的 `_LatencySpikeLogger`**：P8-C spike 的临时首音延迟探针（终端那行
  `[P8-C spike] user-stopped→first-audio = X` 就是它）。提交 `run_voice.py` 任何后续改动都要选择性 stage
  排除这段（本轮 commit 用「临时删→commit→编辑加回工作区」的方式做到的）。

## 当前未完成
- **A. 破音 / 音频欠载调查（P0，下一步主线）**——见上方 A 节，先做隔离实验 #1。
- **B. 标签器质量（P1）**——见上方 B 节（位置 + 停顿标签 + 省略号）。
- **抢话 / barge-in**：`half_duplex=on` 默认禁止 Boxi 说话时打断（启动日志明示「no barge-in」），是既有
  配置非本轮回归。真正的抢话量化（审计 D，`resume_guard`）是 Phase 3 独立待办。
- **日语音色清单未接后端**：`fish-audio-ja-voice-shortlist` 只是预选名单。
- **沿用未完成项**：P14 Phase 3 剩余（Fish 调参 temperature/prosody，审计 B-2）、P12（Hume prosody，仅
  立项）、P9-P2-C（素材源真联网）、P9-D（投递层，用户暂缓）。

## 已知 bug / 风险
- **🆕 破音 / 音频欠载（根因未知）**：见上方 A 节。最高优先调查项。
- **🆕 标签器位置/停顿/省略号质量问题**：见上方 B 节。
- **⚠️ `.env` 的 `CYBER_COMPANION_VOICE_EXPRESSION_TAGGER` 当前是 `=1`（开）**——本轮已从上轮遗留的 `0`
  还原。做 A 的隔离实验 #1 时会临时改 `0`，**测完务必改回 `1`**（`.env` gitignored、不在 diff 里，易忘）。
- **P13（已结案 = won't fix）**：Pipecat `latency=normal` 多轮失声——锁死 `balanced`，勿重开。
- **⚠️ `run_voice.py` 的 `load_dotenv(override=True)` 隔离坑仍在**：命令行环境变量覆盖会被吃掉，**必须直接
  改 `.env` 文件**（见 `docs/TASK_QUEUE.md`「Pipecat 真机测试隔离规范」）。改 `.env` 后要**整个重启
  `dev:backend`** 才生效（看启动日志 `EXPRESSION_TAGGER=on/off` 那行确认）。
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8、R4 等。

## 下一步只需读取（按任务挑一个）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **A. 破音调查**：先做隔离实验（改 `.env` 关标签器、真机听），不需要预读代码；若 #1 指向两阶段路径，
  再读 `.venv/.../pipecat/services/tts_service.py` 的 `_stream_audio_frames_from_iterator` + Fish service
  的 `run_tts`。
- **B. 标签器质量**：读 `backend/app/tts/expression_tagger.py`（`apply_expression_tags_to_sentence` +
  现有三重护栏 `_has_taggable_content`/`_preserves_original_wording`）+ `TAGGER_INSTRUCTION_TEMPLATE`。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（含 `reference/pipecat/`，Pipecat 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开 P13 normal 修复（已结案 won't fix）
- ❌ 不要再凭日志猜破音根因（本轮已证明会连错），必须先做真机隔离实验
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **A. 破音隔离实验 #1**（用户在场，真机）：`.env` 把 `CYBER_COMPANION_VOICE_EXPRESSION_TAGGER` 改 `0`，
  重启 `dev:backend`，长聊一段仔细听破音是否还在。**破音在→与 Phase 4 无关（查底层音频）；破音消失→
  两阶段 per-sentence 路径引入（查 Fish 每句合成的音频边界）。** 这一步定方向，再决定 B 还是深挖 A。
  测完把 `.env` 改回 `1`。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
