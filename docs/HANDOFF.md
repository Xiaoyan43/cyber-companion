# HANDOFF — 上下文交接（2026-06-20，第三十一轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P8 两阶段表达层架构 · 文字聊天路径（P8-A + P8-B）已实施并真机验证 PASS**。
**下一步**：语音 Pipecat 路径（同样的两阶段拆分，但延迟敏感，需要先选定流水线/条件触发等杠杆）——
按既定计划本轮范围外；也可以先让用户多攒几轮真实对话观察文字聊天路径是否稳定，再决定要不要立刻启动语音路径。

## 🎯 架构决策（第二十九轮讨论产出，第三十一轮已落地到文字聊天路径）

**问题根因**：一次 LLM 生成同时背负 7 大类认知任务（人格/状态投射/记忆/格式纪律/BOXI_SIGNALS/Fish标签/长度），
"创作类"（演 Boxi）挤掉"标注类"（Fish 标签）的注意力——标签退化成"最省力合规"：永远堆在开头，正文中间从不出现。
纯改 prompt（含精简版）已确认无法稳定纠正，是任务结构问题，不是文案问题。

**已落地方案：内容/表达两阶段解耦**
- **决策层** = behavior engine（`evaluate_behavior`）—— 不变，纯代码
- **执行层（内容）** = 主 LLM（Grok-4.20 via OpenRouter）只演 Boxi，输出纯文本 + BOXI_SIGNALS，
  **prompt 不再含任何 Fish 标签规则**（`TEXT_CHAT_TAG_INSTRUCTION` 已删除）
- **表达层（标签器）** = 独立 LLM 调用（`backend/app/tts/expression_tagger.py`，默认 DeepSeek），
  输入 = 主 LLM 已写好的纯文本 + 当前 mood 状态，唯一任务 = 插 Fish 标签，
  prompt 只有标签规则（基于 `docs/FISH_AUDIO_REFERENCE.md` §2-4 的完整词表+位置规则），
  失败/空结果**硬性降级**返回原文，绝不拖垮主对话

**调用顺序**（`/chat/complete`、`/chat/stream` 一致）：
`build_provider_context` → 主 LLM 调用 → `parse_structured_assistant_response` →
`apply_signals_to_kernel`（用解析出的 signals 更新 mood/relationship）→
`apply_expression_tags`（用**更新后**的 mood 给纯文本插标签）→ 最终 content 持久化+返回。

**真机验证证据（第三十一轮，2 轮真实对话）**：
1. 标签分布在全文多处（开头/中段/结尾都有），不再清一色堆在最前面。
2. 同一条回复内不同段落的标签组合不同——不是照搬 mood 做静态快照，是逐句/逐段有差异的选择
   （例如一条回复里前半段配 `[breathing][exhale]` 后半段配 `[low voice]`，再往后是 `[sigh]`）。
3. `[sarcastic]` 精确跟在被引用的讽刺话之后（而不是甩在句首），验证了 A 类/B 类标签位置区分的 prompt 指令确实生效。
4. `/chat/stream` 的逐字 delta 确认保持纯文本无标签；前端 `App.tsx` 现有的 `onDone` 处理器
   （本轮未改动）本来就会用最终 `meta.content`（已带标签）覆盖气泡文字——**两阶段架构不需要任何前端改动**。
5. SQLite 持久化的 assistant 消息确认存的是带标签版本，下游 `/tts/stream` 会拿到带标签文本。

第二十九轮记录的两个根因症状（①标签像抄 mood 快照非逐句判断；②音效类标签位置精度要求更高未被遵守）
在这 2 轮验证里都没再出现，但样本量小，需要用户日常使用中持续观察是否稳定。

**语音 Pipecat 路径待做时的延迟杠杆**（移到这里，文字聊天路径不需要，留给下一次启动语音路径时参考）：
- A. 标签器用快模型（次要优化，文字聊天路径已经在用 DeepSeek）
- B. **句子级流水线重叠**——把标签器调用藏进主 LLM 还在写后续句的时间里（真正的延迟杀手，P6 做过 LLM→TTS 重叠有基础）
- C. 条件触发——代码校验发现"标签全堆开头"才补调标签器，合格回复零额外延迟
- D. Fish API 层手段——`latency="low"` 档、WebSocket `FlushEvent`、连接预热（详见 `docs/FISH_AUDIO_REFERENCE.md` §7.2/7.7）

## 本轮已完成（2026-06-20，第三十一轮 · P8-A + P8-B）

| 任务 | 结果 |
|---|---|
| P8-A 表达层标签器模块 | 新建 `backend/app/tts/expression_tagger.py`：`apply_expression_tags(text, mood, *, router, provider_name="deepseek")`。Prompt 只含标签规则——全量 6 类词表（呼吸生理/嗓音发声/节奏/音色风格/情绪/其他）、A类(音效，位置精确)/B类(语气，位置容错)区分、"逐句重新判断不要照搬 mood"显式要求、**去掉了旧版"≥3句必须有非开头标签"的硬性数量配额**（按 FISH_AUDIO_REFERENCE.md §4.3 官方建议——不要为了凑数量堆标签）。失败/超时/空结果硬性降级返回原文。14 个新单测全绿（mock provider 注入模式，仿 `test_companion_brain.py`）。|
| P8-B 接入 `/chat/complete` + `/chat/stream` | `context_builder.py` 删除 `TEXT_CHAT_TAG_INSTRUCTION` 常量 + `append_text_chat_tag_instruction()`（主 LLM 不再背标签任务）。`main.py` 两处（`chat_complete`、`_finalize_streamed_turn`）在 `apply_signals_to_kernel` 之后插入标签器调用，替换最终 content。493 pytest 全绿（479 + 14 新），tsc --noEmit 零错误（未触碰前端文件）。|
| 真机验证 | 重启本地后端（`npm run dev:backend`），发 2 轮真实对话验证，结论见上方「架构决策」末尾。完成后已停止临时启动的后端进程。|

## 本轮追加 · TTS 长回复播放中断 bug 修复（同一 session，真机测试 P8 时发现）

**用户真机反馈**：文字聊天里长回复（多段、含多个 Fish 标签）经常"无法一口气读完"，Pipecat 语音没这个问题。

**根因确认**：`/tts/stream`（[main.py](backend/app/main.py) 原 591-595 行）硬编码 `media_type="audio/mpeg"`，
但 Fish Audio 实际流式吐出的是 opus（真实 MIME 应为 `audio/ogg; codecs=opus`）。前端
[useTextToSpeech.ts](frontend/src/voice/useTextToSpeech.ts) 把长回复按 `max_speech_chars`（120 字）切成多段，
依次 `await` 每段 `<audio>` 元素的 `ended` 事件再播下一段——某一段如果因为 Content-Type 与实际编码不符
导致浏览器解码卡住（不触发 `ended` 也不触发 `error`），整条 `await` 链就卡死，后面的段永远不会再播。
回复越长、切的段越多，撞上这个问题的概率越高；Pipecat 走的是完全不同的 WebSocket 传输，不受影响。
**跟 P8 无关**——本轮没有改过 `tts_stream`/前端播放代码/`config/tts.json`，是测试 P8 时顺带发现的预先存在的 bug。

**修复**（已实施+测试+真机验证）：
- [base.py](backend/app/tts/base.py) 新增 `stream_mime_type()`，默认返回 `"audio/mpeg"`
- [fish_audio.py](backend/app/tts/fish_audio.py)、[doubao.py](backend/app/tts/doubao.py) 各自覆盖，复用已有的
  `FORMAT_TO_MIME` + `self._audio_format`（跟它们 `synthesize()` 里早就在用的逻辑一致，只是流式路径之前没接上）
- [main.py](backend/app/main.py) 的 `tts_stream` 改用 `provider.stream_mime_type()` 而不是硬编码
- 新增 3 个测试（fish_audio/doubao 的 `stream_mime_type()` 单测 + `/tts/stream` 集成测试断言真实 content-type）
- 真机验证：重启后端，curl 实测 `/tts/stream` 返回头从 `audio/mpeg` 变成 `audio/ogg; codecs=opus`，
  `file` 命令确认实际字节确实是 Ogg/Opus——声明终于跟实际编码一致了
- 496 pytest 全绿（493 + 3 新），tsc 零错误

**追问引出更深的根因**：用户追问"为什么不用 WebSocket"，要求把 `features/realtime-streaming`、
`developer-guide/best-practices/real-time-streaming`、cookbook `realtime-llm-to-speech`/`voice-agent-loop`、
`api-reference/endpoint/websocket/tts-live` 这几篇官方文档全部读完记录（已写入 `docs/FISH_AUDIO_REFERENCE.md`
新增第 9 节）。官方结论：**模式选择只看"文本是否已经全部拿到手"**——文字聊天的文本在调 TTS 前早就生成完
（聊天完成+表达层标签都已经跑完），属于"HTTP streaming"场景，**不需要 WebSocket**；Pipecat 用 WebSocket
是对的，因为它的文本是 LLM 真·逐 token 流出来的。**真正的根因是前端不必要的客户端预切段**：
`useTextToSpeech.ts` 的 `textChunksForSpeech()` 把长回复按 120 字切成多段，逐段发起独立 HTTP 请求顺序
`await`，而官方 cookbook 的标准写法是整段一次性传入单个 `tts.stream(text=完整回复)`，服务端自己按
`chunk_length` 内部分段、连续吐音频块。这个切段还在偷偷绕过 `evaluate_speech_policy` 的
`max_speech_chars` 长度门——只拿切出来的第一段（保证 ≤120 字）去过检查，后面的段就绕过去了。

**第二次修复**（已实施+测试+真机验证）：
- `frontend/src/voice/speechText.ts`：删除 `textChunksForSpeech`/`textForSpeech`/`findChunkSplit`/
  `lastIndexOfAny`（确认全仓库无其他引用），导出 `prepareTextForSpeech`（原内部函数，只做清洗不切段）
- `frontend/src/voice/useTextToSpeech.ts`：`speakReply` 不再切段循环 `await`，整段一次性调用一次
  `playSpeechChunk`；移除现在已无用的 `maxSpeechCharsRef`
- `config/tts.json`/`tts.example.json`：`max_speech_chars` 120→4000（不再需要"切一小段去骗检查"，
  阈值要能覆盖真实回复长度；4000 留出生成参数 `max_output_tokens_per_turn=2400` token 对应的安全余量）
- `frontend/src/voice/speechText.test.ts`：删除切段相关测试，改为测 `prepareTextForSpeech`
- `backend/tests/test_tts.py`：2 处断言同步改成 4000（`test_tts_status_route` + `test_tts_evaluate_skips_long_reply` 的超长样本从 200 字符改 5000 字符）
- 496 pytest 全绿，tsc 零错误，前端 vitest 25/25 全绿

**真机验证（用 preview 工具走完整浏览器流程，不是 curl）**：发一条刻意很长的真实消息（"讲讲今天发生的事，
至少三件不同的小事，每件事都要展开"），LLM 回复 2825 tok、带十几个 Fish 标签贯穿全文。Network 面板确认
**只有一次** `/tts/stream` 请求（旧逻辑下这条长度的回复会被切成 8-10+ 次请求），状态 200。UI 的播放状态
从"Speaking"完整播到自然回到"TTS on"（`ended` 事件正常触发，没有卡死），全程 console 零错误。
两个修复（mime-type + 不切段）合在一起，长回复播放问题应该已经解决。

## 本轮新发现（真机验证副产物，记录供参考，未做任何处理）

- 当前 persona 在"好消息/庆祝"语境下的真实输出比此前认知更显性（露骨程度超出"现在是毒舌、暧昧是后做"的预期）——**这不是本轮改动引入的**，本轮没有动任何 persona 文件，是 Grok-4.20 + 现有 persona 本来的行为，只是第一次在非"毒舌吐槽"场景下做真机验证才看到。供后续「活人感/审核」话题讨论参考（见 TASK_QUEUE 对应章节），本轮未做任何处理，不是这次任务的 scope。
- 标签器（DeepSeek）在这条露骨内容上正常处理、未触发降级——对此前讨论的"标签器要不要担心内容审核"是个真实的正面数据点（目前看风险比预期低），但样本量=1，不构成结论，后续多观察。

## 已修改 / 新增文件

| 文件 | 改动 |
|---|---|
| `backend/app/tts/expression_tagger.py`（新增） | 表达层标签器：`apply_expression_tags()` + `TAGGER_INSTRUCTION_TEMPLATE` + `DEFAULT_TAGGER_PROVIDER="deepseek"` |
| `backend/tests/test_expression_tagger.py`（新增，14 个测试） | 正常路径 / ProviderError 降级 / 意外异常降级 / 空结果降级 / 空输入跳过调用 / provider_name 默认值与 override / mood+text 正确传入 prompt / prompt 核心规则断言 / 无硬性数量配额断言 |
| `backend/app/memory/context_builder.py` | 删除 `TEXT_CHAT_TAG_INSTRUCTION` 常量 + `append_text_chat_tag_instruction()` |
| `backend/app/main.py` | `chat_complete`、`_finalize_streamed_turn` 移除对已删函数的调用，改为调用 `apply_expression_tags()`；`tts_stream` 改用 `provider.stream_mime_type()` 而不是硬编码 `audio/mpeg` |
| `backend/app/tts/base.py` | 新增 `stream_mime_type()`（默认 `audio/mpeg`） |
| `backend/app/tts/fish_audio.py`、`backend/app/tts/doubao.py` | 各自覆盖 `stream_mime_type()`，复用已有 `FORMAT_TO_MIME` 映射 |
| `backend/tests/test_tts.py` | 新增 3 个测试（mime-type）+ 2 处断言改成 4000（chunking 移除后同步） |
| `docs/FISH_AUDIO_REFERENCE.md` | 新增第 9 节「Realtime Streaming 架构」，记录 HTTP streaming vs WebSocket 官方选型标准+WS 协议 schema+最佳实践 |
| `frontend/src/voice/speechText.ts` | 删除切段相关函数，导出 `prepareTextForSpeech` |
| `frontend/src/voice/useTextToSpeech.ts` | `speakReply` 不再切段循环，整段一次性播放；移除 `maxSpeechCharsRef` |
| `frontend/src/voice/speechText.test.ts` | 切段测试 → `prepareTextForSpeech` 测试 |
| `config/tts.json`、`config/tts.example.json` | `max_speech_chars` 120→4000 |
| `.claude/launch.json` | 移除 frontend 配置项的 `autoPort`（该 dev server 硬编码端口 5173，autoPort 会导致 preview 工具连错端口） |

**本轮未 commit**（P8-A/P8-B + 两个 TTS 修复都已实施+测试+真机验证，等待用户确认后再 commit；
用户对 P8 的标签效果还在继续测试，尚未最终拍板）。

## 当前未完成（产品侧）

- **【次优先】P8 语音 Pipecat 路径**：两阶段架构的第二条腿，按既定计划本轮不做。`companion_brain.py` 的
  `VOICE_MODE_INSTRUCTION` 仍是旧单阶段方式。启动时机：用户自行决定，要先选定延迟杠杆（见上方架构决策末尾）。
- **已知限制**（实施时发现，记录但本轮不处理）：
  - 标签器的 LLM 调用成本**不计入** `evaluate_llm_budget_gate`/`note_llm_turn` 预算追踪——budget gate 只看主 LLM 调用。
    DeepSeek 很便宜，本轮判断可接受，以后要精确控总花费需要补上。
  - 标签器固定用 `provider_name="deepseek"`（函数签名里的硬编码默认值，非 `config/providers.json` 配置项）。
    要换标签器模型目前需要改代码或在调用处传参。
- 其余既有未完成项延续（未受本轮影响）：P1（RTC character_manifest 同步）、信笺 UI P2（阻塞用户答题）、
  R11（搁置）、world brain 天气 API。

## 已知 bug / 风险

- **Fish 标签情绪准确性**：两阶段架构已落地 + 真机验证显示明显改善（标签分布+逐句判断两个症状本轮验证未再出现），
  但只测了 2 轮对话，样本小，需要日常使用持续观察是否稳定。
- 🆕 持久化的 assistant 消息含 Fish 标签文本（如 `[sigh]`）——如果信笺 UI（LetterView）等展示层直接渲染
  `message.content`，标签会原样可见。这是 P5-H 就有的既有取舍（文字聊天气泡故意显示标签方便肉眼核对），
  本轮未改变这个决定。
- **temperature=0.85**：用户听感"还可以，但和 0.7 区别不大"——非问题但也非确认改善，维持现状即可。
- **`（动作描述）` 可能仍偶发**：否定指令遵守度不稳定。
- **cost 模块不认 openrouter 模型**：`estimate_cost()` 对未知模型返回 $0.0，不影响功能（本轮真机验证响应中可见
  `pricing_source: "unknown-model"`，与本轮改动无关，是既有问题）。
- **R8**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。
- `docs/FISH_AUDIO_REFERENCE.md` 第 8 节列出的未验证点（`chunk_length` 默认值矛盾、`latency=low` 未实测、
  `normalize_loudness` 未核实、`FlushEvent` 未用）——这些是 Fish Audio API 参数层面的，跟本轮标签器架构无关，
  语音 Pipecat 路径用到延迟杠杆 D 时才需要回头看。

## TTS 管道说明（更新：文字聊天标签来源改变，其余不变）

| 路径 | TTS Provider | 情绪标签来源 |
|---|---|---|
| 文字聊天 `/chat/*` | **Fish Audio** `fish_audio.py`（HTTP, s2-pro, opus, temperature=0.85） | 🆕 **两阶段**：主 LLM（Grok）只写纯文本，独立标签器（DeepSeek，`expression_tagger.py`）插标签；下游透传方式不变 |
| Pipecat 语音 `run_voice.py` | **Fish Audio** 官方 `FishAudioTTSService`（WebSocket，`model="s2-pro"`） | 不变：`VOICE_MODE_INSTRUCTION` 指示 LLM 自写标签（单阶段，待后续启动语音两阶段路径时改） |

## 当前 providers.json 状态（本地，gitignored）
- `default_provider: openrouter`，model: `x-ai/grok-4.20`，`OPENROUTER_API_KEY` 已写入 `.env`
- DeepSeek 在 providers.json 里 enabled=true，本轮已实际作为表达层标签器的 provider 跑通真机验证

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若继续做 **P8 语音 Pipecat 路径**：再读 `backend/app/tts/expression_tagger.py`（本轮新建，可直接复用）+
  `backend/realtime/companion_brain.py` + `docs/FISH_AUDIO_REFERENCE.md` §7.2/7.7（延迟杠杆 D 的具体参数）
- 若只是日常用真机攒更多对话样本观察标签稳定性：不需要读任何文件，直接正常聊天

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替，且那是 Volcengine/Doubao 文档，跟 Fish Audio 无关）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/` 原始缓存全文（结论已整理进 `docs/FISH_AUDIO_REFERENCE.md`）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

1. **用户实际听一遍长回复**——自动化 preview 工具已经从网络层面（单次请求+200+`ended`事件正常触发）
   验证了播放链路通畅，但"听感"本身（有没有杂音、标签对应的语气是否真的对、声音是否完整不卡顿）
   只有人耳能确认，建议用户在浏览器里亲自试一条长回复。
2. 继续感受 P8 标签效果（标签语言要不要从英文换成中文，是个独立、随时可以决定的小开关）。
3. 都确认满意后，**一次性 commit 本轮全部改动**（P8-A/P8-B + TTS mime-type 修复 + TTS 切段移除）。
4. 之后进入观察期——日常使用多积累真实对话，确认两阶段架构在更多场景下持续稳定，再决定语音
   Pipecat 路径的启动时机和延迟杠杆选择。
