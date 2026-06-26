# HANDOFF — 上下文交接（2026-06-26，第六十七轮 · 标签密度双向攻坚）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 第六十七轮已完成（2026-06-26，**未 commit，工作树有改动**）

### ✅ 方向一：Rule 3 重写（Haiku-friendly 明确判断协议）
- `TAGGER_INSTRUCTION_TEMPLATE` Rule 3 从"软倾向不加"改成"明确条件判断"：
  - **默认不加标签**；只有满足"条件 A（情绪切换）"或"条件 B（开头突出情绪）"才加一个标签。
  - 两条 `禁止` 语句针对 Haiku 最常见的两种违规模式（按句分配/循环轮换）。
  - 旧版 Gemini 可用的"软倾向"措辞已被替换——新措辞对两个模型都有效。
- 对应测试：`test_tagger_instruction_contains_core_rules` 里的 `"逐句重新判断"` 更新为
  `"每句话默认不加标签"`。

### ✅ 方向二：代码护栏 `suppress_repeated_leading_tags`
- 新常量 `_SOUND_EFFECT_TAG_INNERS`（12 个声音事件标签，免疫去重）+
  `_DEDUP_EXEMPT_TAG_INNERS = _SOUND_EFFECT_TAG_INNERS | _BREAK_TAG_INNERS`。
- 新导出函数 `suppress_repeated_leading_tags(tagged: str) -> str`（`expression_tagger.py`）：
  - 分句后，对每句话找第一个非 exempt 标签；
  - 若与上一句的第一个非 exempt 标签完全相同 → 删除（"继续基调"非新切换，白加）；
  - 无标签句 → 重置基线（下一次同标签视为新起点，不压制）；
  - 音效/break 标签不受影响。
- 接入 `apply_expression_tags`（全文路径，在现有 placement guard 之后）。
- 接入 `main.py` `_tag_reply_by_sentence`（逐句并发后 join，再过一遍护栏）。
- 新增 10 个单测（`test_expression_tagger_guards.py`）：去重/链式/不同标签不压/音效豁免/
  break 豁免/空白间隙重置/单句/无标签/音效跳过找非exempt/wiring 测试。
- **69 个 tagger 相关测试全绿**（=39 prompt + 30 guard tests，相比上轮 +10）。

### 注意
- `test_expression_tagger_processor.py` 和 `test_main_tag_reply_by_sentence.py` 等涉及
  pipecat / FastAPI 的测试文件在本机遇到 numpy macOS `_mac_os_check` 崩溃，与本轮改动无关
  （预存在环境问题，旧 session 同样无法运行这批测试）。
- 效果待用 `experiments/tagger_ab.py` 量化验证：分别测 Haiku 和 Gemini，
  对比 Rule 3 改写前后 `tagged_sentence_ratio` 变化。

## ⚠️ 本次交接特殊说明（给 Cursor / Codex）
- **背景**：Claude Code 本周额度即将用完。从现在到下周一额度重置前，开发交给 **Cursor 或 Codex**；
  重置后用户会回到 Claude Code 继续。本次 session **没有任何新代码改动**——第六十五轮的工作（下文）
  已在 commit `111c70c` 落地，工作树现在是干净的「已交付」状态，只剩两类**故意不提交**的残留物。
- **当前 git 工作树状态（交接基线 = HEAD `111c70c`）**：
  - `backend/realtime/run_voice.py`（+44 行，**未提交，故意保留**）：`_LatencySpikeLogger`——P8-C
    前置的临时延迟探针（量「用户停说→第一帧 TTS 音频」），跨多轮一直按用户要求留在工作区不提交。
    **不要 commit 它**；继续开发时按需保留或本地临时禁用即可。
  - untracked 文件（`.mcp.json`、`experiments/*`、`data/ja_voice_audition/`、`data/tagger_eval/`）：
    全是**故意不提交**的实验脚本 / A-B 音频 / MCP 配置。`.mcp.json` 是 Fish Audio 官方文档 MCP
    （project scope，Claude Code 专用；Cursor/Codex 不一定能用这个 server，可忽略）。
- **给 Cursor/Codex 的最小上手指引**：
  1. 先读本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`，**不要全仓库扫描**。
  2. 生效配置在 `config/providers.json` 和 `config/tts.json`（**均 gitignored**，不在 git 里）——
     当前 tagger 实际跑 `anthropic/claude-haiku-4.5`（经 OpenRouter），见下文「已知 bug / 风险」。
  3. 主线 = 标签密度问题（Haiku 上未解决），量化工具是 `experiments/tagger_ab.py`，**不要凭感觉调**。
  4. 改动遵循本仓库 small-diff 习惯；测试入口见 `backend/tests/`，TTS 切片 `pytest backend/tests/test_*tag*`。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**标签器架构升级——文字路径逐句化已完成并真机验证；当前主线转向标签质量调优（密度/堆叠/情绪判断）+ TTS 引擎/账号层探索。**
第六十五轮完成了上一轮立项的「文字路径标签器逐句化」（P0+P1），随后围绕标签质量做了多轮真机实测和模型 A/B，并研究了 Fish Audio 的音色克隆/Voice Design 能力——**已在 commit `111c70c` 落地**（含本文件 + TASK_QUEUE 当时版本；`config/providers.json` 因 gitignored 未进 commit，仍是本地生效配置）。

## 第六十五轮已完成（2026-06-26，**已 commit `111c70c`**）

### ✅ P0：分句/拼回工具搬到 `expression_tagger.py`（纯重构）
- `split_complete_sentences()` / `build_prior_context()` / `SENTENCE_TERMINATORS` 从
  `backend/realtime/expression_tagger_processor.py` 原样搬到 `backend/app/tts/expression_tagger.py`，
  `expression_tagger_processor.py` 改为从那里 import。
- 目的：让 `backend/app` 主路径（文字聊天）能复用这套分句逻辑，不需要反向依赖
  `backend/realtime`（标注为非默认/实验线的模块）。
- 行为零变化，纯搬运。

### ✅ P1：`main.py` 两处调用点改「逐句 + 并发」标签
- `chat_complete`（[main.py:807](backend/app/main.py:807) 附近）和 `_finalize_streamed_turn`
  （[main.py:938](backend/app/main.py:938) 附近）的整段 `apply_expression_tags` 调用，
  改成新 helper `_tag_reply_by_sentence()`（[main.py:728](backend/app/main.py:728)）：
  分句 → `ThreadPoolExecutor` 并发逐句调 `apply_expression_tags_to_sentence`（带累积
  `prior_context`）→ 按原序拼回。
- **解决的问题**：旧架构"整段一次性标 + 整段校验"，任何单点失败（截断/漏句/改字）会让全篇标签
  作废，长回复尤其容易撞到。现在单句失败只退化那一句，不影响其余句子。
- 并发而非串行：避免 N 句 = N 倍往返延迟（语音/文字路径标签调用本来就是离线补标，不能指望
  播放时间掩盖延迟，串行会让长回复整体变慢）。
- 新增测试 [test_main_tag_reply_by_sentence.py](backend/tests/test_main_tag_reply_by_sentence.py)
  （5 个：单句失败隔离 / 保真 / 并发乱序仍按原序拼回 / 单句跳过线程池 / 空文本直通）。
- **真机验证 PASS**：语音 Pipecat 路径听感确认长故事/多轮场景标签不再"整段消失"。

### ✅ 标签器密度 prompt 调优（小改，已验证有部分效果）
- `TAGGER_INSTRUCTION_TEMPLATE` 规则3（[expression_tagger.py:171](backend/app/tts/expression_tagger.py:171)）
  增加"默认倾向于不加标签，只在明确情绪转折时才加，平稳叙述大多数句子不需要标签"的措辞。
- 用自建 A/B 脚本（见下）量化验证：**对 Gemini 2.5 Flash Lite 有效**（长故事密度 0.73→0.43，
  短对话 0.33→0.11，堆叠对 1.33→0.67）；**对 Claude Haiku 4.5 几乎无效**（密度 1.00→0.97，
  它对"少做/克制"类指令的遵循度明显弱于格式类规则）。
- 39 个 prompt 相关测试全绿，未引入 `至少一次`/`硬性要求` 等被测试禁止的措辞。

### ✅ 标签器模型 A/B：Gemini 2.5 Flash Lite vs Claude Haiku 4.5 vs MiniMax-M3
- 新建 untracked 脚本 [experiments/tagger_ab.py](experiments/tagger_ab.py)（走逐句生产路径，
  同一文本同一轮里切换 model 真机对比，N=3 重复）+
  [experiments/tagger_listen_haiku.py](experiments/tagger_listen_haiku.py)（单独合成长故事音频
  供耳听）+ [experiments/voice_compare.py](experiments/voice_compare.py)（固定文本/标签、只切
  音色，社区 vs 官方音色对比）。
- **结论**：
  - **MiniMax-M3 出局**——延迟 ~9.5s/句（Gemini 的 ~10倍），密度几乎为 0（基本不执行任务，
    疑似把 token 都花在推理而非按指令插标签），不建议再测。
  - **Gemini vs Haiku 是质量 vs 密度/成本的权衡**：Haiku 情绪判断更准（`[nostalgic]`/`[sad]`/
    `[relieved]` 跟着情节走，未见错标），但密度压不下来 + 延迟更高（~1.7-2.2s vs ~1.0-1.3s）+
    成本更高（~3.5×）。Gemini 偶发音效标签语义错误（`[sighing]`/`[groaning]`/`[panting]`
    贴到心跳声上）。
  - **逐句化（P1）本身已经消除了两个模型的逗号复合标签问题**（`[soft, with a little tease]`
    那类）——证明这不是模型选择问题，是"整段一次性标"架构逼出来的，P1 顺带修复。
- **当前生产配置（`config/providers.json`，gitignored，本地已改、未提交）**：tagger provider
  `"gemini"` 条目的 `model` 已切到 `anthropic/claude-haiku-4.5`（经 OpenRouter，key 不变）。
  这是**质量优先**的临时选择，密度问题仍待解决（见「当前未完成」）。

### ✅ 真机听感复核：嘉岚音色本身没问题，问题在回复内容
- 用户多轮 Pipecat + 文字路径真机测试后判断：**嘉岚音色情绪表现是 OK 的**（能听到不同情绪），
  此前怀疑"克隆音色情绪响应天然偏弱"的猜测**已撤回、无官方依据**（查证 Fish 文档后发现：
  情绪表现力是按音色样本本身的情绪覆盖范围决定的，不是"克隆就弱"）。
- 真正的问题模式：**短对话回复情绪听感好，长叙事/讲故事回复情绪听感差**——根因指向"标签密度
  过高 + 情绪变化太频"，与 Fish 官方排障建议（"space out emotional changes"）吻合。这是
  上面 prompt 调优 + 后续护栏要继续攻的方向，不是音色问题。

### ✅ Fish Audio 克隆 / Voice Design 调研（信息收集，未执行）
- 查清两条路线：**Voice Cloning**（克隆已有人声，instant/persistent 两种，官方强调参考样本
  要覆盖多种情绪 + 逐字稿精确匹配 + 仅可用本人/授权声音）vs **Voice Design**（自然语言描述生成
  候选音色，$0.01/次，候选选中后通常还要再走 Cloning 固化）。
- **关键发现**：用户当前 Fish 账号是 **Free 套餐**，**这两个功能都被锁住**（截图证实
  「✕ 增强音色克隆」「✕ 商业使用」，Voice Design 仅 Plus（$15/月）起可用）。Fish 开发者文档
  只讲 API 按量计费（pay-as-you-go，不需要订阅）这一层，**完全没提网页账号的套餐门槛**——这是
  文档没覆盖、只能从用户实际账号状态确认的事实，之前一轮回答"不需要会员"是不准确的，已纠正。
  详见 memory `fish-voice-creation-plan`。
- **用户决定**：当前仍维持「嘉岚」为主音色，**暂不**执行克隆/设计，记录留作以后参考。

## 已修改文件（第六十五轮，已随 `111c70c` 提交）
- `backend/app/tts/expression_tagger.py`：+分句/拼回工具（P0）+ prompt 规则3密度调优。
- `backend/realtime/expression_tagger_processor.py`：改 import 复用 P0 搬出的工具（P0）。
- `backend/app/main.py`：新增 `_tag_reply_by_sentence()` + 两处调用点改用它（P1）。
- 新增 `backend/tests/test_main_tag_reply_by_sentence.py`（P1 测试）。
- 新增 untracked `experiments/tagger_ab.py` / `tagger_listen_haiku.py` / `voice_compare.py`
  （A/B 测试脚本，按惯例不提交，留作复用）。
- 新增 untracked `data/tagger_eval/`（A/B 测试生成的音频文件，按惯例不提交）。
- `config/providers.json`（**gitignored，不在 git diff 里**）：tagger model 本地已切到
  `anthropic/claude-haiku-4.5`，是当前真实生效配置，但不会出现在 commit 里——下一 session
  如果要复现/调整，直接改这个文件，不需要等 commit。
- `config/tts.json`：本轮中途多次切换 model/voice 做听感测试（s2.1-pro↔s2.1-pro-free、
  嘉岚↔社区/官方音色），**最终已切回跟 HEAD 完全一致的值**（`s2.1-pro-free` + 嘉岚
  `fbe02f8306fc4d3d915e9871722a39d5`），`git diff` 显示无变化，无需处理。

## 已知 bug / 风险
- **🆕 Haiku 密度问题未解决**：prompt 调优对 Gemini 有效，对 Haiku 基本无效——Haiku 长回复
  仍几乎逐句贴标签（tagged_sentence_ratio ~0.97-1.00）。这是质量(Haiku判断准) vs
  密度/延迟/成本(Gemini更优) 的真实权衡，未决定最终选谁，当前生产配置临时停在 Haiku。
- **🆕 标签器 provider 命名名不副实**：provider 条目仍叫 `"gemini"`、
  `DEFAULT_TAGGER_PROVIDER = "gemini"`、env 名 `OPENROUTER_GEMINI_API_KEY`，代码注释/日志里
  也写"Gemini"，但现在实际跑的是 Haiku。不影响功能，是个命名债，留作以后小任务清理。
- **🆕 Fish 账号套餐门槛**：用户 Free 套餐锁住克隆/Voice Design/商用，需升级 Plus（$15/月）
  才能用——这不是代码问题，是产品决定，已记入 memory，暂不阻塞其他工作。
- 沿用：自回声残余（AEC epic，暂缓）、P12（Hume prosody 立项）、P9-P2-C（素材源真联网）、
  P9-D（投递层，暂缓）、日语音色清单未接后端按语言切换、Fish WebSocket 空闲断连（自动重连，
  功能不受影响）。

## 当前未完成

### 🔴 最高优先 · 标签密度问题（第六十七轮已落两层防御，待量化验证）
- **第六十七轮已做**：① Rule 3 重写（明确条件判断，Haiku-friendly）；② 代码护栏
  `suppress_repeated_leading_tags`（连续同标签去重）——两层都**未 commit**，待 `tagger_ab.py`
  量化确认有效后 commit。
- **下一步**：用 `experiments/tagger_ab.py` 量化复核（`python experiments/tagger_ab.py 3`），
  对比 Haiku `tagged_sentence_ratio` 和 `adjacent tag-stack pairs`，看两层防御叠加后密度变化。
  - 若有效（密度明显下降）→ commit 这次改动，结案或继续调优。
  - 若 Rule 3 无效（Haiku 仍不遵从）→ 考虑回退 Gemini 或接受当前 Haiku 密度靠听感判断。
  - 代码护栏不依赖模型，始终保留。
- **剩余选项**（如果两层都不够）：③ 回退 Gemini（密度更优但情绪判断糙）；
  ④ 接受 Haiku 密度，靠真机多轮听感判断"密但准"是否听起来自然。

### 🟡 标签器 provider 命名正名（独立小任务，不紧急）
- 把 `"gemini"` 这个 provider 名字、`DEFAULT_TAGGER_PROVIDER`、`OPENROUTER_GEMINI_API_KEY`
  env 名、相关注释/日志统一改成跟模型无关的中性名（如 `"tagger"`），消除"代码里写 Gemini
  实际跑 Haiku"的误导。涉及 4-5 处 + env 变量改名，small-medium diff。

### 🟢 Fish 音色克隆/设计（产品决定，等用户升级套餐后再启动）
- 不阻塞当前工作，详见 memory `fish-voice-creation-plan`。

### 沿用未完成项
- task 4 自回声残余（归 AEC epic，暂缓）、P12（Hume prosody 立项）、P9-P2-C（素材源真联网）、
  P9-D（投递层，暂缓）、日语音色清单未接后端按语言切换。

## 下一步只需读取（按任务挑）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 做密度调优/护栏：额外读 `backend/app/tts/expression_tagger.py`（`TAGGER_INSTRUCTION_TEMPLATE`
  规则3 + 已有 placement guard 模式）+ `experiments/tagger_ab.py`（直接复用做量化验证）。
- 做 provider 命名正名：额外读 `backend/app/providers/registry.py`（`gemini` 分支）+
  `backend/app/tts/expression_tagger.py`（`DEFAULT_TAGGER_PROVIDER`）+ `.env`/`.env.example`
  （`OPENROUTER_GEMINI_API_KEY`）。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（Pipecat/Fish 文档线已结）
- ❌ `experiments/`（除 `tagger_ab.py`/`tagger_listen_haiku.py`/`voice_compare.py` 外均为废弃 spike，
  故意不提交）
- ❌ 不要重开：P0/P1 逐句化架构本身（已完成并真机验证）、嘉岚音色是否有问题（已确认无问题）、
  MiniMax-M3 标签器（已排除）、Fish Audio 是否需要会员（已查清，需 Plus）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **立即**：用 `python experiments/tagger_ab.py 3` 量化复核第六十七轮的两层防御效果（Rule 3 重写 +
  `suppress_repeated_leading_tags`）。若 Haiku `tagged_sentence_ratio` 有明显下降 → commit
  `backend/app/tts/expression_tagger.py` + `backend/app/main.py` + 两个测试文件。
- **备选小任务**（独立、不紧急）：标签器 provider 命名正名（`"gemini"` → 中性名，消除「代码写 Gemini
  实际跑 Haiku」的误导，见「当前未完成 · 🟡」）。

---

> **给 Cursor/Codex**：本周接手开发，先读本文件顶部「⚠️ 本次交接特殊说明」。
> **给 Claude Code（下周回归）**：执行 `/clear` 或新开 session，只需读取
> `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、`docs/ARCHITECTURE_SNAPSHOT.md`。
