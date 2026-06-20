# Fish Audio Reference

> 内部参考文档，整理自 Fish Audio 官方文档站（docs.fish.audio）+ 官方博客（fish.audio/blog）+
> 开源仓库 README（github.com/fishaudio/fish-speech），交叉验证产出（2026-06-20，第三十轮）。
> 目标：不用每次现场重新解析 Fish 官方资料，直接查这份文档回答"这个场景该用哪个标签、放哪、会不会出声"。
> 范围：项目实际使用 **S2-Pro** 模型，本文档以 S2-Pro 为主，S1 仅作背景对比。
> 原始抓取缓存：`.firecrawl/docs.fish.audio-*.md`、`.firecrawl/fish.audio-blog-*.md`、`.firecrawl/github.com-fishaudio-fish-speech.md`。
> **状态**：定稿（P0 文档盘点 + P1 标签系统 + P2 phoneme/生成参数 全部完成，2026-06-20）。
> **2026-06-20 追加（同一 session，文字聊天 TTS 播放中断排查时）**：新增第 9 节「Realtime Streaming 架构」——
> 用户直接点名要求读 `features/realtime-streaming`、`developer-guide/best-practices/real-time-streaming`、
> cookbook `realtime-llm-to-speech`/`voice-agent-loop`、`api-reference/endpoint/websocket/tts-live` 这几篇，
> 补齐了"HTTP streaming vs WebSocket 到底该怎么选"的官方权威答案。

---

## 1. 先决条件：模型选择决定标签语法

Fish Audio 当前有两代 TTS 模型，**语法完全不同、不可混用**：

| | S2-Pro（项目当前使用） | S1（前代，未弃用） |
|---|---|---|
| 标签语法 | `[方括号]`，**自由文本描述**，无固定词表 | `(圆括号)`，**固定 64 个标签**（4 类，见下） |
| 发布时间 | 2026年3月 | 2025年6月 |
| 多说话人对话 | 支持（S2-Pro 专属） | 不支持 |
| 语言数 | 80+（自动检测，质量分层见下） | 13 |
| 标签可放位置 | 句首/句中/句尾均可，影响其后文字直到下一个标签或句末 | 官方示例集中在句首 |

**关键边界**：直连 API 时两套语法不能混用——`model=s2-pro` 时圆括号会被当成普通文本朗读出来，不会被解析成标签。Fish 网页版 UI 会自动把 `()` 转成 `[]`，但**直连 API 没有这层自动转换**，必须自己保证语法跟模型匹配。
（来源：`models-overview`、"词级控制"博客 FAQ）

S1 没有被弃用（被弃用的是更早的 `speech-1.5`/`speech-1.6`），但官方现在统一推荐新项目用 S2-Pro。⚠️ 注意：`models-pricing/deprecations` 页文案前后矛盾——先列"S2 (Recommended)"，下一句又写"强烈推荐 S1"，明显是没同步更新的旧文案，**应以 `models-overview` 页为准**（S2-Pro 是当前推荐）。

S1 的 64 个固定标签作为背景参考列在文末「附录」，本文档主体只讲 S2-Pro。

**语言质量分层**（来自 GitHub README，docs 站未提及此分层）：
- **Tier 1**（最佳质量）：日语、英语、**中文**
- **Tier 2**：韩语、西班牙语、葡萄牙语、阿拉伯语、俄语、法语、德语
- 其余 60+ 语言：覆盖但非重点优化

项目主要面向中文用户——中文恰好在 Tier 1，是个好消息。

---

## 2. S2-Pro 标签分类

S2-Pro 最大的特点：标签不是查表选择，而是**自由的自然语言描述**——可以写一句完整的演绎指导（例如"像值了一整晚夜班、累到说话都没力气的语气"），模型会尝试理解并演绎。不限于预设词汇，这是和 S1 最本质的区别。

官方文档 + 博客给出一份"久经测试、效果稳定"的种子词表，可以分成 6 类：

| 分类 | 标签 |
|---|---|
| 呼吸与生理反应 | `[sigh]` `[inhale]` `[exhale]` `[gasp]` `[panting]` `[clears throat]` `[breathing]` |
| 嗓音/发声类 | `[laughing]` `[chuckling]` `[giggle]` `[sobbing]` `[crying]` `[groan]` `[moaning]` |
| 节奏类 | `[pause]` `[short pause]` `[long pause]` |
| 音色风格类 | `[whispering]` `[soft voice]` `[low voice]` `[loud voice]` `[shouting]` |
| 情绪类 | `[excited]` `[angry]` `[sad]`（官方示范只给这 3 个，情绪类标签可自由扩展，如 `[surprised]` `[delighted]` 等口语化描述同样有效） |
| 其他 | `[emphasis]`（重读紧跟其后的词）`[rustling sound]`（背景环境音） |

**扩展词表**（来自 GitHub README，覆盖面更宽，可作补充参考）：
`[tsk]` `[singing]` `[laughing tone]` `[interrupting]` `[excited tone]` `[volume up]` `[volume down]` `[echo]` `[loud]` `[delight]` `[audience laughter]` `[with strong accent]` `[shocked]`

**标签语言不限英文**——S2-Pro 能理解多语言的标签描述，可以直接用中文写标签（如 `[低声说]` `[叹气]`），保持跟脚本语言一致即可。

> ⚠️ **更正现有认知**：HANDOFF 之前记录"标签必须英文，中文标签未验证生效"——这条已被官方"词级控制"博客的多语言示例（日语/中文/西语/韩语标签全部给了实例）证伪，需要更正为"标签语言建议跟脚本语言一致，不限英文"。

---

## 3. 触发"真实声音事件" vs "仅影响演绎风格"

这个区分对应项目第二十九轮真机验证发现的核心问题——不是所有标签都一样，存在两种本质不同的类型：

**A 类：触发真实可听见的声音事件**（音效/生理反应类）
`[sigh]` `[gasp]` `[panting]` `[laughing]` `[chuckling]` `[sobbing]` `[crying]` `[groan]` `[moaning]` `[clears throat]` `[rustling sound]` 等——这些标签让模型合成一段**真实的非语言声音**本身（一声叹气、一次喘息、笑声），不是"换个语气说话"，是"在这个位置发出一个声音事件"。

**B 类：只影响演绎风格，不产生独立声音事件**
`[whispering]` `[soft voice]` `[low voice]` `[loud voice]` `[shouting]`（音色风格类）、`[excited]` `[angry]` `[sad]`（情绪类）、`[pause]` `[short pause]` `[long pause]`（节奏类，本身"无声"但改变停顿时长）——这些标签调整的是"接下来这段话怎么说"，不会插入一个独立可分离的声音事件。

这个区分直接决定下一节的位置精度要求。

---

## 4. 标签位置规则——最容易踩坑的部分

### 4.1 核心机制

标签影响**其后的文字**，直到遇到下一个标签或句子结束。同一个标签放在不同位置，效果范围完全不同——**位置即语义**：

- 标签放句首 → 整句都按这个标签演绎
- 标签放句中某个词前面 → 只有从那个词开始往后才按标签演绎，之前的部分不受影响

官方给的对比示意：
- 标签紧贴转折点：`"我以为一切都好。[whispering] 然后我听到了那个声音。"` —— 只有后半句被压低声音说，效果符合预期
- 标签放在句首但本意只想影响后半句：`"[whispering] 我以为一切都好。然后我听到了那个声音。"` —— 整段话都被压低声音说，包括"一切都好"那句也变成耳语，通常不是想要的效果

### 4.2 按标签类型分别要求位置精度（项目实测 + 官方资料交叉验证）

- **A 类（音效/生理反应类）标签对位置精度要求高**：必须紧贴该效果真正发生的词/句。放错位置，听到的是一声突兀的叹气/喘息/笑声出现在不该出现的地方，这不是"语气没对上"的程度，是"这里突然冒出一个奇怪的声音"，违和感明显。
- **B 类（语气/情绪/节奏类）标签位置容错更高**：因为它们影响的是"演绎风格"而非插入独立声音事件，位置即使不是最精确，效果也只是影响一整段的说话方式，不会产生"冒出不该有的声音"那种违和感。

这条结论跟第二十九轮真机验证记录的发现完全一致，现在有了官方资料佐证，不只是项目自己的猜测。

### 4.3 组合使用建议（官方实测经验）

- **物理反应类标签建议配一个情绪标签一起用**：单独的 `[panting]` 效果可能显得"平"，配上情绪标签才有情绪根基（官方示例：`[panting] [tired] 我跑了二十分钟了。`）
- **描述性标签后面必须跟文字**：标签是"指导接下来怎么说"，不能让标签后面是空的或紧跟句子结束，否则效果不可预期
- **不要堆叠太多标签**：官方建议从简单开始——一个放对位置的 `[sigh]` 或 `[long pause]` 就能改变整句感觉，效果不够才加更多，标签堆太多会互相打架。
  > ⚠️ 这条跟项目之前"路径A精简版"里"强制 ≥3 句正文必须出现非开头标签"的硬性数量要求方向相反，P8 重新设计表达层 prompt 时应纳入考虑，避免为了凑数量而过度堆标签。

---

## 5. 已知的文档/工程不一致（写 prompt 时要避开的坑）

1. **官方文档自己也有"标签焊句首"的反例**：`developer-guide/best-practices/real-time-streaming` 页给的示例代码固定用 `(emotion) 文本` 模式——圆括号、固定焊句首，跟 S2-Pro 的方括号自由位置语义矛盾，疑似是没跟上 S2 发布节奏的旧示例。**不要把这个示例当作 S2-Pro 的标准用法**，应以"词级控制"博客 + `models-overview` 页的说明为准。
2. **`models-pricing/deprecations` 页文案前后矛盾**：见第 1 节。
3. **项目自己的实测发现**（第二十九轮真机验证，非官方资料，记录在 HANDOFF）：现有 prompt 下，标签表现得像是"抄当前 mood 的持续快照"，而不是"逐句现场判断该配什么标签"——连续多条回复经常带同样的情绪标签组合，跟该句实际语气不符。**本文档只负责把"标签本身怎么用"讲清楚**；"什么时候该用哪个标签"仍然要靠 LLM 临场判断，代码层面强制不了——这正是 P8 两阶段表达层架构要解决的问题。

---

## 6. Phoneme 发音控制语法

语法统一用 `<|phoneme_start|>...<|phoneme_end|>` 包裹，按语言不同，替换范围和内容格式不同：

### 6.1 英文（CMU Arpabet）
- **替换范围**：一个单词
- **格式**：CMU Arpabet，空格分隔的大写符号，元音可带重音数字（`0`=无重音 `1`=主重音 `2`=次重音）；IPA 不支持，需先转换成 CMU Arpabet
- **例**：`I am an <|phoneme_start|>EH1 N JH AH0 N IH1 R<|phoneme_end|>.`（engineer 的标准读法）
- **典型用途**：异形同音词（`read` 现在时/过去时发音不同）、专有名词、技术术语缩写（Kubernetes、SQL）
- **生成工具**：Python `cmudict` 包，`cmudict.dict()[word.lower()]`

### 6.2 中文（声调数字拼音）
- **替换范围**：一个字/音节；多字词要给每个字单独包一个标签，按原文顺序排列
- **格式**：小写拼音 + 声调数字后缀（`1`=高平 `2`=升 `3`=降升 `4`=降 `5`=轻声）
- **例**：`我是一个<|phoneme_start|>gong1<|phoneme_end|><|phoneme_start|>cheng2<|phoneme_end|><|phoneme_start|>shi1<|phoneme_end|>。`（工程师）
- **典型用途**：多音字（重庆 `chong2qing4` vs 重要 `zhong4yao4`；银行 `yin2hang2` vs 行走 `xing2zou3`）、人名
- **生成工具**：Python `pypinyin` 包的 tone3 转换

### 6.3 日语（背景参考，项目不需要）
替换范围为一个短词/短语，格式是 OpenJTalk 风格罗马字 + 音高重音数字标记。

### 6.4 与 `normalize` 参数的关系
phoneme 标签**不受 `normalize` 参数影响**——它只处理数字/日期等通用文本规整，phoneme 标签本身会被完整保留。只有当你想阻止 normalize 改写标签**周围**的数字/日期/URL 文本时才需要设 `normalize: false`（代价：那部分文本朗读稳定性下降）。

### 6.5 不适用于 S2-Pro 的部分：圆括号特效（重要排除）
官方 fine-grained-control 总览页还提到一套圆括号特效——`(break)` `(long-break)` `(breath)` `(laugh)` `(cough)` `(lip-smacking)` `(sigh)`——但官方标注这些是**"V1.6 Control Model 专属 + Experimental"**，是 Playground 里另一个独立模型变体的功能，跟项目用的 S2-Pro 方括号语法不是一套。**不要在 S2-Pro 请求里使用这套圆括号特效**，第 2 节的方括号标签已经覆盖了同等效果（如 `[pause]`/`[sigh]`）。
（沿用 HANDOFF 已有结论，本次用官方资料确认了出处）

### 6.6 停顿词（非正式标签，附带技巧）
官方还提到一个不算"标签"的技巧：直接在文本里写停顿词本身（"um"、"uh"、"嗯"、"啊"）也能调节语音节奏，跟 `[pause]` 标签是互补关系，不是替代。

---

## 7. 生成参数完整清单

来源：`/v1/tts` 官方 OpenAPI schema（HTTP 与 WebSocket 共用同一套参数定义）。

### 7.1 表达力/采样参数
| 参数 | 类型 | 范围 | 默认值 | 作用 |
|---|---|---|---|---|
| `temperature` | number | 0–1 | **0.7** | 控制表达力：越高越多变/越有表现力，越低越一致/越保守 |
| `top_p` | number | 0–1 | **0.7** | nucleus sampling 控制多样性：越高候选越宽，越低越保险 |
| `repetition_penalty` | number | 不限 | **1.2** | 抑制重复音模式，>1.0 才生效 |
| `max_new_tokens` | integer | 不限 | **1024** | 单个文本分段最多生成多少音频 token |
| `early_stop_threshold` | number | 0–1 | **1** | 批处理场景的提前停止阈值（项目目前不涉及批处理） |

### 7.2 分段/流式参数
| 参数 | 类型 | 范围 | 默认值 | 作用 |
|---|---|---|---|---|
| `chunk_length` | integer | 100–300 | **300**（⚠️见下方不一致说明） | 文本处理的分段大小，越小启动越快、越大越省请求 |
| `min_chunk_length` | integer | 0–100 | **50** | 分段前最少要攒够多少字符，避免切得太碎 |
| `condition_on_previous_chunks` | boolean | — | **true** | 是否用前一分段的音频做上下文，保持音色/韵律连贯 |
| `latency` | enum | `low`/`normal`/`balanced` | **normal** | 延迟-质量权衡：**normal=最佳质量，balanced=降低延迟，low=最低延迟** |

> ⚠️ **官方文档内部不一致**：`chunk_length` 默认值，`features/text-to-speech` 页文字说明写的是"默认 200"，但 OpenAPI schema（机器可读、更贴近服务端实际行为）写的是 `default: 300`。**以 OpenAPI schema 为准**，正式调参前建议用真实请求验证线上实际默认值。
> 🆕 **`latency=low` 这一档容易被漏看**：博客和 prose 文档（`best-practices/real-time-streaming`、`features/text-to-speech`）都只提到 `normal`/`balanced` 两档，`low`（最低延迟）这一档只在 OpenAPI schema 里出现，对 P8「延迟杠杆」讨论是个新增候选项，但效果未实测。

### 7.3 音质/格式参数
| 参数 | 类型 | 范围 | 默认值 | 作用 |
|---|---|---|---|---|
| `format` | enum | `wav`/`pcm`/`mp3`/`opus` | **mp3** | 输出音频格式（项目当前用 `opus`） |
| `sample_rate` | integer\|null | — | **null**（按格式取默认：多数 44100Hz，opus 为 48000Hz） | 采样率 |
| `mp3_bitrate` | enum | `64`/`128`/`192` | **128** | 仅 `format=mp3` 时生效 |
| `opus_bitrate` | enum | `-1000`(自动)/`24000`/`32000`/`48000`/`64000` | **-1000** | 仅 `format=opus` 时生效 |

### 7.4 韵律参数（`prosody` 嵌套对象）
| 参数 | 类型 | 范围 | 默认值 | 作用 |
|---|---|---|---|---|
| `prosody.speed` | number | 0.5–2.0 | **1** | 语速倍率，可在不重新生成的情况下调节节奏 |
| `prosody.volume` | number | -20–20 (dB) | **0** | 音量调整 |
| `prosody.normalize_loudness` | boolean | — | **true** | 统一输出响度，**仅 S2-Pro 支持** |

### 7.5 文本规整
`normalize`（boolean，默认 **true**）：规整数字/日期等文本提升朗读稳定性，关掉后这类文本朗读不稳定，但不影响 phoneme 标签（见 6.4）。

### 7.6 多说话人（S2-Pro 专属，项目当前不使用）
通过 `<|speaker:0|>` `<|speaker:1|>` 等标签在 `text` 里标记说话人切换，配合 `reference_id` 传数组（每个说话人一个 voice id）。

### 7.7 WebSocket 流式特有机制（Pipecat 路径相关）
WebSocket（`/v1/tts/live`）复用完全相同的参数 schema，额外多了几个流程控制事件：
- `StartEvent`：开局发一次，带上面所有参数配置，`text` 字段通常留空
- `TextEvent`：后续逐段发文本，服务端按 `chunk_length`/`min_chunk_length` 攒够了才合成
- **`FlushEvent`**：🆕 强制立即合成当前缓冲区里的文本，不等凑够 `chunk_length`——这是没在任何博客/教程里提到的延迟杠杆，追求低延迟的交互场景可以主动调用，不必等自然攒够分段
- `CloseEvent`（事件名实际是 `"stop"` 不是 `"close"`，命名容易踩坑）：发送后服务端合成完剩余缓冲文本，发 `FinishEvent`（`reason: stop`/`error`）后关闭连接

---

## 8. 已知限制 / 未验证点

- **`chunk_length` 默认值矛盾**（见 7.2）：未实测确认线上真实默认值是 200 还是 300。
- **`latency=low` 完全没有 prose 文档描述效果**，只在 schema 里出现一行"lowest latency"，实际音质取舍未验证。
- **`prosody.normalize_loudness` 是本轮新发现的参数**，项目当前 `fish_audio.py` 的 payload 构造是否已设置或依赖其默认值，本文档未核实（按 P0–P2 范围约定不读项目代码，需要 P8 实施阶段单独核对）。
- **`early_stop_threshold`、`min_chunk_length`、`condition_on_previous_chunks`、`FlushEvent` 项目目前完全没用过**，本文档只记录官方定义，调参/调用效果未实测。
- **phoneme 标签未在项目实际请求中验证过效果**（HANDOFF 记录"曾加进 prompt 但路径A精简时移除"）——本节内容来自官方文档，不是项目实测结果。
- **本文档不覆盖 Pipecat 已安装库的实际行为**：HANDOFF 已有方法论备注"Fish 官网 Pipecat 文档滞后于已安装库，配置应优先信任 `pipecat/services/fish/tts.py` 源码"——本文档是官方资料整理，跟实际安装的 Pipecat 版本行为如有冲突，**以已安装库源码为准**。

---

## 9. Realtime Streaming 架构：HTTP streaming vs WebSocket 到底该怎么选

> 来源：`features/realtime-streaming`（官方总览页，**这是回答"该用哪种"的权威页**）+
> `developer-guide/best-practices/real-time-streaming`（调优细节）+ cookbook
> `realtime-llm-to-speech`/`voice-agent-loop`/`streaming-to-file` + `api-reference/endpoint/websocket/tts-live`
> （WebSocket 协议完整 AsyncAPI schema）。触发原因：文字聊天长回复 TTS 播放经常"卡住放不完"，
> 排查 mime-type bug 后用户追问"为什么不用 WebSocket"，官方资料给出了明确、本文档之前没记录的答案。

### 9.1 官方定义的两种模式——选择标准只看一件事："文本是不是已经全部拿到手了"

官方原文（`features/realtime-streaming`）把模式选择讲得非常直接，不是"哪个更好"，是"看场景"：

- **HTTP streaming（`tts.stream`）——"你已经有完整的文本，想要低首字节延迟。最简单的选项。"**
  适用：文本已经完整生成好（比如聊天回复已经写完、已经过完表达层标签器），只是想尽快听到声音、
  不想等整段音频生成完才能开始播放。
- **WebSocket（`tts.stream_websocket`）——"文本还在被生成中（LLM 输出、实时字幕）。可以在整句话讲完之前就开始说话。"**
  适用：文本是逐 token / 逐字蹦出来的，TTS 要跟着"边吐边说"，不能等一整句攒完。

官方 `voice-agent-loop`（ASR→自有 LLM→TTS）cookbook 给的标准范式是单次
`client.tts.stream(text=完整回复, reference_id=...)`——**整段回复文本一次性传入，不是切碎成多个请求**；
只有在追求更极限的延迟、想让 TTS 跟着 LLM 逐 token 同步开口时，才会进一步换成 `stream_websocket()`
直接喂 LLM 的 token 生成器。HTTP streaming 内部本来就会按服务端的 `chunk_length`/`min_chunk_length`
自动分段、边合成边吐音频块回来给同一个请求——**客户端不需要、也不应该自己先把长文本切成多份再分别发起多次请求**。

### 9.2 跟项目当前实现对照

| | 项目现状 | 官方建议 |
|---|---|---|
| 文字聊天 TTS（`/tts/stream` + `useTextToSpeech.ts`） | 前端 `textChunksForSpeech()` 按 `max_speech_chars`(120 字) 把长回复切成多段，**逐段分别发起 HTTP 请求**，`await` 完一段的 `<audio>` `ended` 再发下一段 | 文本已经全部拿到手（聊天回复+标签都已经生成完）→ 属于 9.1 的 HTTP streaming 场景，应该**整段一次性发起一个 `/tts/stream` 请求**，让 Fish Audio 服务端用 `chunk_length` 内部分段、在同一个响应里连续吐音频块 |
| Pipecat 语音（`FishAudioTTSService`，WebSocket） | 文本是 LLM 流式吐出的（真正逐 token），用 WebSocket | 与 9.1 的 WebSocket 场景完全匹配——**这条路径的选型本来就是对的**，不是 Pipecat"运气好没撞上 bug"，是它用对了模式 |

**结论**：文字聊天路径"长回复放不完"的根因，除了已修复的 mime-type 不一致，更可能的主因是**前端不必要的客户端预切段**——
把一次本该是单个 HTTP streaming 请求的任务，拆成了 N 个独立请求顺序执行，每个请求边界都是一个新的失败点。
按官方模式，这条路径**不需要 WebSocket**，只需要**不要自己切段**，交给 Fish Audio 服务端的单请求内部分段机制。

### 9.3 WebSocket 协议细节（给 Pipecat 路径/P8-C 备查，权威 schema 来源 `api-reference/endpoint/websocket/tts-live`）

连接：`wss://api.fish.audio/v1/tts/live`，header 需要 `Authorization: Bearer <key>` + `model: s2-pro`（或 `s1`）。
全部消息走 `application/msgpack` 序列化（不是 JSON——直连协议时需要用 `ormsgpack` 之类的库打包）。

客户端发送（按顺序）：
1. **`StartEvent`**（必须最先发一次）：携带跟 HTTP `/v1/tts` 完全相同的参数（`request` 字段），`text` 通常留空
2. **`TextEvent`**（可发多次）：`{"event": "text", "text": "..."}`，服务端按 `StartEvent` 里的 `chunk_length` 自动攒够了才合成
3. **`FlushEvent`**（可选）：`{"event": "flush"}`，强制立即合成当前缓冲区，不等自然攒够 `chunk_length`——用于"这句问完了，别等了，现在就说"这种轮次边界
4. **`CloseEvent`**：`{"event": "stop"}`（事件名是 `"stop"` 不是 `"close"`，命名容易踩坑）——发完后服务端合成剩余缓冲文本，再发 `FinishEvent`，然后关闭连接

服务端发送：
- **`AudioEvent`**（多次）：`{"event": "audio", "audio": "<bytes>"}`，按 `StartEvent` 里指定的格式（mp3/wav/pcm/opus）
- **`FinishEvent`**（一次，会话结束时）：`{"event": "finish", "reason": "stop"|"error"}`——`stop`=正常完成，`error`=合成中出错，客户端要妥善处理

### 9.4 官方最佳实践清单（`developer-guide/best-practices/real-time-streaming`，主要适用于 WebSocket/LLM-token 场景）

- **文本攒批发送**：发完整单词+空格，用标点制造自然停顿，攒 5-10 个词再发一批；不要逐字符发、不要一次性甩一大段
  （这条是 `TextEvent` 怎么喂的建议，跟"要不要切 HTTP 请求"是两件事，别混)
- **连接管理**：同一个连接尽量复用着发多轮，断线要妥善处理+重试
- **音频播放**：缓冲 2-3 个音频块再开始播、块之间做 crossfade、网络延迟要兜得住
- **延迟/质量参数**：`latency="balanced"`（默认，最低首字节延迟，适合语音助手/实时LLM输出）vs `latency="normal"`
  （稍高延迟，最佳音质，适合不赶时间的旁白场景）——跟第 7.2 节的三档（含 `low`）是同一个参数，
  这页只提到 balanced/normal 两档，`low` 仍然只在 OpenAPI schema 出现，参见第 7.2 节已有的提醒
- **降低延迟的额外手段**：用流式友好的格式（`mp3`/`pcm`）、保持连接热着复用、配合克隆音色

### 9.5 排障对照表（官方原文，适用于真碰到播放问题时按图索骥）

| 现象 | 官方建议方案 |
|---|---|
| Audio Gaps（音频块之间有间隙） | 加大缓冲、用 balanced latency、检查网络连接 |
| Delayed Response（首次响应等太久） | 用 balanced latency、尽快发出第一段文本、减小 chunk 大小 |
| Choppy Playback（断断续续） | 多缓冲几个块再播、检查网络稳定性、**用一致的 chunk 大小**（项目现在的问题恰恰相反——用的是不一致的、人为切出来的 120 字分段） |

---

## 附录：S1 固定标签全集（背景参考，项目未使用 S1）

S1 用 `(圆括号)` 语法，标签是固定的 64 个（4 类）：

**基础情绪（24）**：`(angry)` `(sad)` `(excited)` `(surprised)` `(satisfied)` `(delighted)` `(scared)` `(worried)` `(upset)` `(nervous)` `(frustrated)` `(depressed)` `(empathetic)` `(embarrassed)` `(disgusted)` `(moved)` `(proud)` `(relaxed)` `(grateful)` `(confident)` `(interested)` `(curious)` `(confused)` `(joyful)`

**进阶情绪（25）**：`(disdainful)` `(unhappy)` `(anxious)` `(hysterical)` `(indifferent)` `(impatient)` `(guilty)` `(scornful)` `(panicked)` `(furious)` `(reluctant)` `(keen)` `(disapproving)` `(negative)` `(denying)` `(astonished)` `(serious)` `(sarcastic)` `(conciliative)` `(comforting)` `(sincere)` `(sneering)` `(hesitating)` `(yielding)` `(painful)` `(awkward)` `(amused)`

**音调标记（5）**：`(in a hurry tone)` `(shouting)` `(screaming)` `(whispering)` `(soft tone)`

**音效（10）**：`(laughing)` `(chuckling)` `(sobbing)` `(crying loudly)` `(sighing)` `(panting)` `(groaning)` `(crowd laughing)` `(background laughter)` `(audience laughing)`
