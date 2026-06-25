# HANDOFF — 上下文交接（2026-06-26，第六十四轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**标签器架构升级——文字聊天路径改成逐句化（对齐语音路径）。** 本轮（第六十四轮）先做了
TTS 模型切换 + 两个 bug 修复（已 commit `982a168`），过程中坐实了文字路径"整段全有或全无"
架构的脆弱性。**下一步主线** = 把文字路径的标签调用也改成逐句切分（复用现成的
`apply_expression_tags_to_sentence`），不再因为单句失败就让整段标签作废。

## 本轮已完成（2026-06-26，第六十四轮，commit `982a168`）

### ✅ Fish Audio 切到 S2.1 Pro Free + 两处 model 配置未接通的 bug
- 用户提供 Fish 官方博客确认：S2.1 Pro 和 S2.1 Pro Free **同一套模型权重**，区别只在 SLA/数据
  保留/商业条款，免费版到 2026-07-24，对真机测试场景无实质风险。`config/tts.json` 的
  `fish_audio.model` 切到 `s2.1-pro-free`。
- **历史阻塞已排除**：第六十轮记录的"`s2.1-pro-free` 省略号场景更差"经用户确认，真根因是断句器
  把「…」当终止符（已修复），跟 S2.1 模型本身无关——不再是切换的阻塞理由。
- **bug①**：[registry.py](backend/app/tts/registry.py) 的 `fish_audio` 分支没把 `entry.model`
  传给 `FishAudioTTSProvider`（对比 mock/openai_tts 分支都传了），文字聊天路径一直用构造函数
  默认值 `s2-pro`，`config/tts.json` 改了不生效。已补传 `model=entry.model`。
- **bug②**：[run_voice.py](backend/realtime/run_voice.py) 语音 Pipecat 路径硬编码
  `model="s2-pro"`，完全没读配置。改成跟 `reference_id` 共用同一份 `config/tts.json` 读取逻辑。
- **真机确认账户扣费排查**：用户反馈切换后仍被扣钱，排查后判断**很可能是 `reference_id`（克隆
  音色）本身的使用费**，跟 model 档位选择是两套独立计费——**未验证，留给用户自行核实**（去 Fish
  网站查那个 voice ID 的计费说明，或换官方默认音色对比）。

### ✅ 标签器 token 预算修正（消除长回复截断）
- 真机复现：长回复标签器调用整段退回纯文本。用日志（先加了 warning 里打印 original/tagged 方便
  对比，见下）实测两次定位到两种不同失败模式：
  1. **截断**：`max_output_tokens = estimate_token_count(stripped) + 128`，而
     `estimate_token_count`（`len // 3`）按英文调校，对中文严重低估——长故事"复述原文+插标签"
     所需 token 远超预算，模型写到一半被掐断，`_preserves_original_wording` 正确拒绝截断结果，
     但代价是整段标签全部作废。**已修复**：新增 `_tagger_output_token_budget()`（按字符数 +256），
     两处调用点（`apply_expression_tags` + `apply_expression_tags_to_sentence`）切过去。真机复测
     确认截断消除（长故事完整复述到结尾）。
  2. **漏句**（修复后新暴露、未修）：截断消除后，仍观察到一次标签器把原文开头一个小句
     （"要听完全不一样的？"）整句吞掉，护栏正确拒绝，整段标签照样作废。**这是"整段全有或全无"
     架构本身的脆弱性**——任何单点失败（漏句/改字/截断）都会让全篇标签归零，跟失败原因本身无关。
     治本方向 = 文字路径逐句化（见「当前未完成」）。
- 同轮给两处 `_preserves_original_wording` 失败的 warning 日志补上 `original=...
  tagged=...`，下次复现可直接对比定位差异（小改动，未受架构升级影响，长期保留有价值）。
- 59 个 `test_expression_tagger*.py` + 124 个相关测试（含 tts/fish_audio_pipecat_tts）全绿。

### ✅ 新增 Fish Audio 官方文档 MCP server（`.mcp.json`，project scope）
- 用户看到 Fish 官方博客介绍 llms.txt/MCP/Agent Skills 三层方案，评估后认为 **MCP 这层对本项目
  有实质帮助**——直接命中本轮反复出现的"文档信息滞后/拼凑出错"问题（model header vs body、
  S2.1 定价区分、token 预算等都是查文档查出来的）。llms.txt 不需要装、按需直接 WebFetch 那个 URL
  即可；Agent Skills 对本项目（已有定制集成代码，非从零生成样板）价值不大，跳过。
- 已执行 `claude mcp add --transport http fish-audio --scope project https://docs.fish.audio/mcp`，
  写入 `.mcp.json`。**状态：Pending approval**——MCP 工具在会话启动时加载，当前 session 批准了也
  用不上，必须**新开一个 session 才能首次批准 + 使用**。下一 session 打开时记得批准。

## 已修改文件（本轮）
- **已 commit `982a168`**：`backend/app/tts/expression_tagger.py`（token 预算函数 + 两处日志）、
  `backend/app/tts/registry.py`（补传 model）、`backend/realtime/run_voice.py`（model 改读配置，
  **只 stage 了这部分**）、`config/tts.json`（model 切 s2.1-pro-free）。
- **未提交（工作区保留，按惯例排除）**：`run_voice.py` 历史遗留的 `_LatencySpikeLogger`（P8-C
  spike 用，用户要求保留，commit 时已用部分 patch 排除）。
- **新增未跟踪**：`.mcp.json`（fish-audio MCP server 配置，project scope，未 gitignore——是否要
  commit 这个文件本轮未讨论，下一 session 可以问用户）。

## 上一轮摘要（2026-06-25，第六十三轮，commit `70d5c7a`）
task 3「标签器音效标签语义闭门」——改 `TAGGER_INSTRUCTION_TEMPLATE` 规则4，A 类音效标签只能在
真实发生时用、不能当软情绪记号；真机验证 A 类标签频率 6+次/轮→~1次/轮，已结案。剩余 2 个语义
边界案例（`[sighing]`/`[crying loudly]`）判定为 LLM 固有灰色地带，不建议重开。

## 当前未完成

### 🔴 最高优先 · 文字路径标签器逐句化（本轮新立项，下一步主线）
- **问题**：`apply_expression_tags()`（文字聊天用）是整段一次性调用 + 整段校验（`_preserves_
  original_wording` 对全文一字不差才通过）。本轮验证证实——**任何单点失败**（截断/漏句/改字，
  原因不限于一种）都会让**全篇标签作废**，回复越长越容易撞到至少一处失败。
- **对比**：语音路径已经是逐句调用（`apply_expression_tags_to_sentence`），单句失败只丢那一句的
  标签，不影响其余句子——这正是要给文字路径补上的粒度。
- **方案方向**：文字路径调用处（`main.py` 的 `/chat/complete` + `/chat/stream`，目前调
  `apply_expression_tags`）改成「分句 → 逐句调 `apply_expression_tags_to_sentence`（带
  `prior_context` 维持语气连续）→ 拼回」，复用语音路径现成的函数和分句逻辑，不需要新写标签规则。
- **要读**：`backend/app/tts/expression_tagger.py`（两个函数已都存在，直接复用）+
  `backend/app/main.py`（两处调用点）+ `backend/realtime/expression_tagger_processor.py`
  （参考语音路径"分句→逐句调用→拼回"的现成实现模式）。
- **下一步**：先 `/architect` 拆 scope，再实施。建议在**新 session**（带着已批准的 fish-audio
  MCP）里做，配额、上下文都更充裕。

### 🟡 待用户核实 · Fish Audio 扣费根因未验证
- 本轮切到 `s2.1-pro-free` 后用户反馈仍被扣钱，怀疑根因 = `reference_id`（克隆音色）本身的使用费，
  跟 model 档位选择是两套独立计费——**这是猜测，未验证**。用户需自行去 Fish 网站查那个 voice ID
  的计费说明，或换官方默认音色测一次对比扣费情况。下一 session 如果用户已有结论，记录进来；
  没有结论也不阻塞其它工作。

### 🟢 task 2 剩余 · P2 词中插 / P3 开头堆叠（已降级，沿用）
- 连续多轮真机未复现，优先级让位给标签器逐句化这条主线。

### 沿用未完成项
- task 4 自回声残余（归 AEC epic，暂缓）、P12（Hume prosody 立项）、P9-P2-C（素材源真联网）、
  P9-D（投递层，暂缓）、日语音色清单未接后端按语言切换。

## 已知 bug / 风险
- **🆕 文字路径标签器"整段全有或全无"架构脆弱**：见上「最高优先」，根因明确，方案明确，待实施。
- **🆕 Fish Audio 扣费根因未验证**：见上，怀疑是音色使用费非 model 档位问题，用户自行核实中。
- **沿用 · task 4 自回声残余**：归 AEC epic，真治靠 AEC（浏览器/WebRTC 白送），本轮不动。
- **沿用 · Fish WebSocket 空闲断连**：轮次间隔 >15s 时 Fish 服务端主动断，自动重连成功，功能不受影响。
- **架构认知（durable，写给未来做 barge-in 的 session）**：barge-in 的拦路虎是 **AEC，不是换 ASR**。
  现装 Pipecat 音频滤镜全是降噪，没有 AEC；本地 PyAudio 路径没接参考信号。AEC 现实来源 = 浏览器/
  WebRTC（`getUserMedia echoCancellation` 白送）或耳机。**挂未来「产品上 web/WebRTC」epic**。
- **沿用**：破音修复的 ~200ms 首音延迟代价（已闭环勿重查）；P13 normal 失声（won't fix，锁
  balanced）；`run_voice.py` `load_dotenv(override=True)` 改 `.env` 须重启 dev:backend；cost
  模块不认 openrouter；OPEN：是否抬 `DEFAULT_VOICE_MAX_TOKENS`（默认维持 200）。

## 下一步只需读取（按任务挑）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 做标签器逐句化：额外读 `backend/app/tts/expression_tagger.py` +
  `backend/realtime/expression_tagger_processor.py` + `backend/app/main.py` 的两处 tts 调用点。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（Pipecat/Fish 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开破音 / P13 normal / 省略号 / 自回声主修 / 截断 / task 2 P0+P1 / task 3 / 本轮已修的
  model 配置 bug（均已结案 / 已 commit `982a168`）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **标签器逐句化是明确主线**：先 `/architect` 拆 scope（改 `main.py` 两处调用点 + 复用现成的
  `apply_expression_tags_to_sentence`），建议在新 session 里做（fish-audio MCP 批准后可用，
  上下文也更充裕）。

---

> 建议执行 `/clear` 或新开 session（**记得批准 fish-audio MCP**）。下一 session 只需读取
> `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、`docs/ARCHITECTURE_SNAPSHOT.md`。
