# HANDOFF — 上下文交接（2026-06-25，第六十一轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**语音 Pipecat 路径的表达质量打磨。** 本轮一口气真机定位并修掉三个独立的语音体验 bug
（省略号怪声残留 → 自我回声 → 偏长回复被砍在半句），全部真机验证 PASS 并已 commit。
下一步主线 = **标签器质量（task 2，本轮已诊断+攒了新数据，未开工）**。

## 本轮已完成（2026-06-25，第六十一轮，**三个 commit 全部真机 PASS**）

### ✅ commit `a922465` · 省略号怪声修复（上一轮代码，本轮真机确认后 commit）
- 真根因 = 流式断句器把「…」当句子终止符 → 喂 Fish 语法残缺半句 → 怪声。
- 修复 = `expression_tagger_processor.SENTENCE_TERMINATORS` 与 `tag_stats._TERMINATORS` 解耦并排除「…」
  + 两个 guard（连续终止符合并、`_schedule` 丢无内容碎片）+ `expression_tagger._strip_dangling_trailing_tags`
  + `config/tts.json` 音色嘉岚。真机「好了不少」。

### ✅ commit `c40efda` · 自我回声抑制（新建 `self_echo_filter.py`）
- **真根因（代码级实锤）**：half-duplex 闸门在 `BotStoppedSpeakingFrame` 解除静音，但音箱仍在放 Boxi
  最后一句的缓冲尾音（~200ms 输出缓冲 + 设备延迟领先于真实播放完成）。外接音箱 + 无 AEC → 麦克风采回
  尾音 → Doubao ASR ~800ms 后才出 final，落在 resume guard（=800ms）之外 → 逃过抑制 → brain 回应 Boxi
  自己（真机：Boxi 把自己结尾的「我都在」当成用户输入，自问自答）。
- **修复（内容级兜底）**：`SelfEchoGate` + 捕获/过滤双处理器（镜像 half-duplex 模式）。用户 final 转写若
  「在 bot 停说后窗口内（默认 4s）」且「是 Boxi 上句回复的**尾巴**（精确或同音字级模糊 ≥0.8）」→ 直接丢弃，
  不进 brain/字幕。**只认尾巴不认句中词** → 不误杀复用 Boxi 词的真实接话；每轮最多压一次。
- 真机 PASS：日志 `🔇 self-echo suppressed (Boxi heard herself): '来一个。'`，正常多轮对话未被误杀。
- config 开关：`CYBER_COMPANION_VOICE_SELF_ECHO_FILTER`（默认 on，仅 half-duplex 下生效）+ `..._WINDOW_MS`（默认 4000）。

### ✅ commit `6087d31` · 偏长回复被砍时落在完整句（不再念半句）
- **根因**：语音 `max_tokens=200` 把 LLM 生成硬砍在半句（finish_reason=length），而
  `ExpressionTaggerProcessor` 收尾 flush 不加区分地把没有终止符的残尾也送 TTS 念出来（真机：故事停在
  「进来坐」「emo碎碎念」等半句）。
- **修复（区分「被砍」vs「自然说完」）**：`VoiceTurnOutcome` 加 `truncated` 字段，`stream_turn` 用
  `output_tokens >= max_tokens` 判定（**无需穿透 provider 层的 finish_reason**——StreamChunk 里没有，但
  usage 已在手）；processor 把 `truncated` 挂到 `LLMFullResponseEndFrame`；tagger processor 在 End flush 时
  `truncated` → 丢残尾（停在上一句完整话），自然结束 → 保留结尾（哪怕无句尾标点）。
- 真机 PASS：日志 `✂️  dropped truncated tail fragment (output-token cap): '”'`，停在完整句。
- **不强制超长**——保持动态长度，只让偏长被砍时落在完整句（用户明确需求）。

### 测试
- 自回声单测 12 passed；本轮各阶段 `-k "tagger or brain or realtime or voice or echo or half_duplex"` 均绿
  （最后一次 132 passed）；`py_compile` OK。**本轮没跑全量 `npm run check`**——建议让 Cursor 收尾跑全量门禁。

## 已修改文件（本轮）
- **已 commit**（三个 commit，见上）：`self_echo_filter.py`(新) + `test_self_echo_filter.py`(新) +
  `voice_config.py` + `companion_brain.py` + `companion_brain_processor.py` + `expression_tagger_processor.py` +
  `test_companion_brain.py` + `test_expression_tagger_processor.py` + `config/tts.json` + `expression_tagger.py`
  + `run_voice.py`（**仅自回声接线那 ~23 行**已提交）。
- **未提交（工作区保留）**：`run_voice.py` 仅剩历史遗留的 `_LatencySpikeLogger`（+44，用户要求保留、commit 时
  照惯例排除——本轮 commit 自回声/截断时已用「临时移除 spike → 提交 → 字节级还原」处理过，零残留）。
- **docs/HANDOFF.md + docs/TASK_QUEUE.md**：本次交接更新。

## 当前未完成

### 🔴 task 2 · 标签器（Gemini）放置质量（下一步主线，本轮已诊断+攒新数据，未开工）
- **本轮真机新观察到的具体症状**：
  - 畸形标签带内部空格：`[ sighing ]`（Fish 很可能不识别）。
  - `[break]`/`[long-break]` 句中滥用 + 紧贴标点冗余：`想让我[break]再卖个关子，` / `影子从来不说话[whispering]，`。
  - 分句开头标签堆叠：`[calm] [bored]` / `[curious] [whispering]` / `[soft tone] [sighing]`。
  - （历史）词中插标签：`那[sighing]股`、`造出来的[sighing]`。
- **历史结论**：P0（喂数值）、P1（喂自然语言）两种 **prompt 方案都失败过**，被判「结构性、纯 prompt 治不好」。
- **已工作、别动**：wording-change guard（标签器改字即回退纯文本，本轮日志多次正确触发）、
  `_strip_dangling_trailing_tags`、`_has_taggable_content`（丢空碎片）。
- **推荐方向 = 代码级后处理「位置/格式守卫」**（符合架构边界「代码只强制标签格式/位置合法性，情绪恰当性靠 LLM」）：
  ① 畸形标签归一化（`[ sighing ]`→`[sighing]` 或剥除）；② `[break]`/`[long-break]` 紧贴标点冗余时剥除 + 密度上限；
  ③ 词中插标签检测（标签两侧皆 CJK、无标点/空格边界）→ 移到最近边界或剥除；④ 分句标签堆叠数上限。
  避开「prompt 治不好」的泥潭，small diff + 可单测。

### 🟡 OPEN 决策 · 是否把 `DEFAULT_VOICE_MAX_TOKENS` 从 200 抬进代码
- 截断 fix 已让 200 下「被砍也落在完整句」，所以抬 cap 现在是**可选项、与 fix 正交**。用户本轮试改 `.env`
  `CYBER_COMPANION_VOICE_MAX_TOKENS=512` 但**没生效**（日志一直 200，疑似 .env 没写对/没重启到位）。
  若以后想让长故事讲更完整，抬高即可（不影响首音延迟，流式从第一句就放），但用户表态不追求超长，**默认维持 200**。

### 沿用未完成项
- P12（Hume prosody 立项）、P9-P2-C（素材源真联网）、P9-D（投递层，暂缓）、日语音色清单未接后端按语言切换。

## 已知 bug / 风险
- **🆕 标签器放置质量**：见上 task 2（畸形标签/`[break]` 滥用/堆叠/词中插）。
- **沿用 · Fish WebSocket 空闲断连**：轮次间隔 >15s 时 Fish 服务端主动断，随后自动重连成功、下一轮正常。功能不受影响。
- **沿用 · `s2.1-pro-free` 在省略号场景回归**：已锁 `s2-pro`，别再随手换（memory 已记）。
- **架构认知（durable，写给未来做 barge-in 的 session）**：barge-in（打断 Boxi）的拦路虎是 **AEC（回声消除），
  不是换 ASR**。Pipecat 有 VAD+interruption（我们已有 SileroVAD，half-duplex 故意关掉了），但现装 Pipecat 的音频
  滤镜全是降噪（krisp_viva/aic/rnnoise/koala），**没有一个是 AEC**；本地 PyAudio 路径没接参考信号。AEC 的现实
  来源 = 浏览器/WebRTC 传输（`getUserMedia echoCancellation` 白送，前端本就是 web）或耳机。**barge-in = 独立 epic，
  挂在「产品上 web/WebRTC」节点**；届时 half-duplex + 自回声从主力降级为残余回声兜底，但不白写。
- **沿用**：破音修复的 ~200ms 首音延迟代价（commit `8d5b2fb`，已闭环勿重查）；P13 normal 失声（won't fix，
  锁 balanced）；`run_voice.py` `load_dotenv(override=True)` 改 `.env` 须重启 dev:backend；cost 模块不认 openrouter。

## 下一步只需读取（按任务挑）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **task 2 标签器位置守卫（推荐）**：读 `backend/app/tts/expression_tagger.py`（tagger prompt + guards）+
  `backend/realtime/expression_tagger_processor.py`（已含断句/丢碎片/截断逻辑）+ `docs/FISH_AUDIO_REFERENCE.md`
  （合法标签词表 + 位置规则）。先 `/architect` 拆。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（Pipecat/Fish 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开破音 / P13 normal / 跨轮次 context 竞态 / 省略号 / 自回声 / 截断（均已结案 PASS）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **task 2 · 标签器位置/格式守卫**：先 `/architect` 把「畸形标签归一化 + `[break]` 冗余/密度 + 词中插检测 +
  堆叠上限」拆成最小可测切片（走代码后处理，不碰 prompt），再实现。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
