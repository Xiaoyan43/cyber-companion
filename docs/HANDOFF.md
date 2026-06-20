# HANDOFF — 上下文交接（2026-06-20，第二十九轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**第二十八轮改动已真机验证 + commit（第二十九轮，5 个 commit，见下）。**
provider 选型最终：LLM = `x-ai/grok-4.20`（via OpenRouter），TTS = Fish Audio（文字聊天 + Pipecat 语音两条路径）。
**真机验证发现标签问题比预期更深**（见下「架构决策」新增两条），**下一步最高优先改为
「Fish Audio 全量文档深度研究」（P8 前置，独立先做）**，再用 `/architect` 拆两阶段表达层架构（P8）。

## 🎯 架构决策（本轮讨论产出，下一 session 用 `/architect` 拆解的起点）

**问题根因**：一次 LLM 生成同时背负 7 大类认知任务（人格/状态投射/记忆/格式纪律/BOXI_SIGNALS/Fish标签/长度）。
其中"创作类"（演 Boxi）和"标注类"（BOXI_SIGNALS、Fish 标签）抢注意力——模型优先保人格，
标注退化成"最省力合规"：Fish 标签永远只堆在回复开头，正文中间的情绪/语气修饰从不出现。
**实测确认：纯靠改 prompt（含精简版路径A）无法稳定纠正，是任务结构问题，不是文案问题。**

**已定方向：内容/表达两阶段解耦（三层架构）**
- **决策层** = `behavior engine`（`evaluate_behavior`：回不回/register/连击）—— ✅ 已存在，纯代码
- **执行层（内容）** = 主 LLM（Grok-4.20）专注演 Boxi，输出**纯文本正文 + BOXI_SIGNALS**，prompt 里**不含 Fish 标签规则**
- **表达层（TTS 修饰）** = 独立"标签器"调用，输入=纯文本+情绪状态，唯一任务=插 Fish 标签，
  prompt **只有标签规则**，注意力 100% 在标签上 → 可摆上 Fish 全部潜力（69 表达+句中位置+自由描述+phoneme）

**关键边界（别建错地方）**：代码只能强制 Fish 标签的「格式/位置合法性」（拼写/英文标签集/是否只堆开头），
**强制不了「情绪恰当性」（该配 sad 还是 sighing）——那永远靠 LLM**。所以定位是
"代码做裁判（校验+路由），LLM 做专项选手（每次只干一件事）"。

**多 LLM 分工的正确定位**：用户有 Gemini / DeepSeek 等 API。
- 换模型**消除不了串行延迟**（标签器必须等内容写完才能标，是依赖关系不是模型问题）。
- 多 LLM 真正价值 = **专长匹配 + 省钱**：灵魂层用 Grok（人格最好），表达层标签器用 DeepSeek/Gemini Flash（快+便宜+指令遵循好做机械标注）。
- 标签器故障必须**降级**（用纯文本无标签也能正常说话），绝不能拖垮主对话。

**延迟三杠杆**（与"用几个模型"无关）：
- A. 标签器用快模型 → 第二段更短（次要优化）
- B. **句子级流水线（重叠）→ 把第二段藏进灵魂还在写后续句的时间里（真正的延迟杀手，P6 做过 LLM→TTS 重叠有基础）**
- C. 条件触发 → 代码校验发现"标签全堆开头"才补调标签器（合格回复零额外延迟）

**分路径落地**：文字聊天先做（延迟不敏感，验证架构的试验田，直接串行两阶段）；
语音 Pipecat 后做（延迟敏感，用杠杆 B 流水线 或 杠杆 C 校验+补救）。

**第二十九轮真机验证新增两条证据（比"位置"问题更深）**：
1. **标签像是抄 mood 持续快照，不是对当前这句话内容的现场判断**——连续 4 条回复几乎每条都带
   `[annoyed][worried]` 开头，但内容经常是温柔/牵挂语气（"你睡的时候我就在这儿守着吧"），
   情绪标签与该句实际语气不匹配。说明退化模式比"堆开头"更进一步：变成"直接照搬内核情绪状态"，
   而不是"读这句话该配什么标签"。两阶段架构的表达层标签器 prompt 需要显式要求"逐句重新判断"，
   不能简单继承上一句/整体 mood 的标签。
2. **音效类标签（产生真实声音事件）比语气类标签对位置精度要求更高**——`[sighing]`/`[anxious]`
   这类标签会触发可听见的音效（如真实叹气声），放错语境位置产生的是违和的声音，不只是"语气没对上"。
   表达层标签器设计需要区分对待：**音效类标签需要精确语境锚点**（紧跟该情绪真正发生的词/句），
   **语气/音调类标签位置容错更高**（影响整句演绎风格即可）。
3. **新增前置任务**：用户要求先深度+完整解析 Fish Audio 全部官方文档并产出独立 reference doc
   （而非每次现场重新解释），P8 `/architect` 设计表达层标签器 prompt 时直接引用，见下「当前未完成」。

## 本轮已完成（2026-06-19，第二十八轮 · 跨多次 model 切换，未 commit）

| 任务 | 描述 |
|---|---|
| 文字聊天 TTS 情绪 soul-authored | `context_builder.py` 新增 `TEXT_CHAT_TAG_INSTRUCTION` + `append_text_chat_tag_instruction()`；`main.py` 两处 `/chat/complete`/`/chat/stream` 接入。标签由 LLM 自写 |
| `fish_audio.py` 移除映射前置 | 删 `_DIRECTIVE_TAG_MAP`（8 条中文短语→标签映射）；标签由 LLM 写在正文里直接透传 |
| **Provider 选型收尾** | 确认最终 LLM=grok-4.20、TTS=Fish Audio；`rm config/persona.json`；验证存在论人设恢复 |
| 换音色 | `config/tts.json`（本地）fish_audio voice 最终 = `fbe02f8306fc4d3d915e9871722a39d5` |
| Pipecat / 纯E2E RTC 长度限制打开 | `companion_brain.py` `VOICE_MODE_INSTRUCTION` + `persona.example.json` `rtc_character_manifest` 删长度限制（**RTC 只删长度，括号约定+core_persona 未动**） |
| **`speech_rate` 死代码修复**（真实 bug） | `main.py` 两路由 mood→speech_rate 计算原被 `if provider_name=="doubao"` 包住，Fish 成默认后恒为 0。改为 provider-agnostic，context_texts 仍只 doubao 分支赋值。+回归测试 |
| **speech_rate 让位 Tone Marker** | `tone.py` 新增 `TONE_MARKER_TAGS`（5 个官方 pacing/volume 标签）+ `contains_tone_marker_tag()`；`main.py` 两路由：文本含 Tone Marker 标签则 speech_rate=0，避免跟 LLM 自写节奏标签打架。+2 回归测试 |
| 标签指令多轮迭代（最终落「路径A精简版」） | `VOICE_MODE_INSTRUCTION` + `TEXT_CHAT_TAG_INSTRUCTION` 经历：内容驱动长度→多句多标签→69 全量标签+phoneme→**最终精简到 13 情绪+5 音调+5 音效 + 硬性要求(≥3句正文必须出现非开头标签) + 正反示例对照**。⚠️ 这是**临时可用状态**（标签确实出现在非开头了），但用户否决"精简掉 Fish 潜力"的方向，定为走两阶段架构（届时表达层恢复完整能力） |
| 前端改为**显示**标签 | `App.tsx` 去掉聊天气泡 + `lastBoxiText` 的 `stripLeadingFishTags()` 调用（函数保留未删）。用户决定标签暴露在气泡里，方便肉眼核对标签位置 |
| temperature 调高 | `fish_audio.py` 新增 `DEFAULT_TEMPERATURE = 0.85`（官方默认 0.7），构造函数+payload 接入。**待用户实测**听感，太飘往回调、不够再往上 |

**验证**：479 pytest passed，0 failed；前端 `tsc --noEmit` 零错误 ✅
**未做（第二十八轮结束时）**：① 浏览器/语音真机验证本轮全部改动端到端效果；② temperature=0.85 听感未实测；③ 全部改动未 commit。

## 本轮已完成（2026-06-20，第二十九轮）

| 任务 | 结果 |
|---|---|
| 文字聊天真机验证（P0） | Fish 标签确认能出现在正文非开头位置（位置问题有改善）。**但发现更深问题**：标签像抄 mood 持续快照而非逐句判断（见上「架构决策」新增 1、2 条）。用户结论："情绪标签依旧没有正确工作"——已知限制，不阻塞 commit，留给 P8 根治 |
| Pipecat 真机验证（P1） | 用户测试，**无 blocking 问题** |
| temperature=0.85 听感 | "还可以，但不能说和 0.7 有区别"——非明确改善也非劣化，维持现状，不继续调 |
| 479 pytest 复核 | commit 前重跑一次，仍 479 passed，0 failed，确认无回归 |
| **commit 第二十八轮 + 未提交的 P5-B-2** | 按主题拆 5 个 commit（见下表），全部已落 master，未 push |

**本轮 5 个 commit**（按主题，均已 push 状态为"ahead of origin"，未 push）：

| commit | 内容 |
|---|---|
| `d39f6c8` | fix(tts): speech_rate 改为 provider-agnostic + 让位 Tone Marker 标签 |
| `9f85fc7` | feat(voice): 文字聊天+语音标签由 LLM 自写，长度改内容驱动 |
| `ca69cb9` | feat(tts): 移除标签前置拼接 + Fish Audio temperature 调至 0.85 |
| `ab4d64d` | feat(frontend): 聊天气泡暴露 Fish 标签供肉眼核对（`stripLeadingFishTags` 留待之后用） |
| `1dd96cb` | feat(realtime): Pipecat TTS 默认切换到官方 Fish Audio service（P5-B-2，上一轮漏 commit） |

**用户新增要求**：先深度、完整解析 Fish Audio 全部官方文档并产出独立 reference doc，
不要每次现场重新解释——见下「当前未完成」新增的 P8 前置任务。

## ⚠️ 用户要求的提醒（2026-06-19）

**`config/persona.example.json` 的 `core_persona` 字段**（`"毒舌被困小人 + low-dose companionship"`）+
`rtc_character_manifest` 其余部分（括号动作约定、"毒舌被困小人"框架）仍是旧人设，跟新 `persona_prompt`
（存在论框架/两张脸）不一致——**用户明确说"后面再说，记得提醒我"**，下次涉及人设/RTC 话题时主动提一句。

## TTS 管道说明（第二十八轮变更后）

| 路径 | TTS Provider | 情绪控制（当前=临时单阶段；目标=两阶段表达层） |
|---|---|---|
| 文字聊天 `/chat/*` | **Fish Audio** `fish_audio.py`（HTTP, s2-pro, opus, temperature=0.85） | `TEXT_CHAT_TAG_INSTRUCTION` 指示 LLM 自写标签，透传；含 Tone Marker 标签时 speech_rate 让位 |
| Pipecat 语音 `run_voice.py` | **Fish Audio** 官方 `FishAudioTTSService`（WebSocket，`model="s2-pro"`） | `VOICE_MODE_INSTRUCTION` 指示 LLM 自写标签；speech_rate 无法逐句调（协议限制） |

## 当前 providers.json 状态（本地，gitignored）
- `default_provider: openrouter`，model: `x-ai/grok-4.20`，`OPENROUTER_API_KEY` 已写入 `.env`
- DeepSeek 在 providers.json 里 enabled=true（可作两阶段标签器候选）；Gemini 可走 OpenRouter

## 当前未完成（产品侧）
- **【最高优先，P8 前置】Fish Audio 全量文档深度研究**：通读 Fish Audio 全部官方文档，产出独立
  reference doc（建议 `docs/FISH_AUDIO_REFERENCE.md`），覆盖标签全集分类（情绪/音调/音效，
  哪些产生真实声音 vs 只影响演绎风格）、位置规则、phoneme 控制、S2-Pro vs S1 语法差异、
  temperature/top_p 等生成参数。独立先做，做完后 P8 `/architect` 直接引用。
- **【次优先】两阶段表达层架构（P8）**：见上「架构决策」，含第二十九轮新增两条证据。
  待 Fish 文档研究完成后用 `/architect` 拆解，从文字聊天起步。
- **P1（RTC character_manifest 同步）**：`rtc_character_manifest` + `_DEFAULT_RTC_CHARACTER_MANIFEST` 还是旧毒舌框架（用户要求 core_persona 暂不动，见上提醒）。
- **信笺 UI · P2**：阻塞，需用户答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。下次发现当场验证。
- **world brain 后续**：天气 API（需 key）/ 未来事件表。

## 已知 bug / 风险
- **Fish 标签情绪准确性=未解决**（第二十九轮真机验证升级判定，不只是"位置"问题）：①标签像抄
  mood 持续快照而非逐句判断（连续多条回复带同样的 `[annoyed][worried]`，与该句实际语气不符）；
  ②音效类标签（`[sighing]`等）位置精度要求高于语气类标签，错位产生违和声音。根治靠两阶段架构 P8。
- **temperature=0.85**：用户听感"还可以，但和 0.7 区别不大"——非问题但也非确认改善，维持现状即可。
- **`（动作描述）` 可能仍偶发**：否定指令遵守度不稳定。
- **cost 模块不认 openrouter 模型**：`estimate_cost()` 对未知模型返回 $0.0，不影响功能。
- **R8**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。

## Fish Audio 方法论备注（避免重复踩坑）
- Fish 官网 Pipecat 文档滞后于已安装库（`model_id="s1"` 默认等是旧 API）。**调 Pipecat/Fish 配置优先信已安装包源码** `pipecat/services/fish/tts.py`，不信官网。
- Fish 标签：S2-Pro 用 `[方括号]` + 可自由英文描述（不限固定词表）；S1 才用 `(圆括号)` 固定集。**标签必须英文**（官方所有示例均英文，中文标签未验证生效）。最多叠加 3 个。情绪标签放句首最佳；音调/音效标签可放句中任意位置。
- `fine-grained-control.md` 的 `(breath)`/`(laugh)` 等圆括号特效是 **V1.6 Control Model 专属 + Experimental**，跟我们的 s2-pro 方括号语法不是一套，**没采用**。
- Phoneme 发音控制（英文 CMU Arpabet / 中文声调拼音）= 独立功能，可治英文技术词/多音字读错，曾加进 prompt 但路径A精简时移除，两阶段架构的表达层可恢复。
- `temperature`/`top_p` 是 TTS 生成参数（非 LLM）：temperature 高=表现力强但不稳，低=一致但机械；top_p 高=候选宽更有个性，低=只挑最保险。建议静态设、听感调，不要 mood 驱动。

## 下一步只需读取（按任务，只读这些）
- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **两阶段架构 `/architect`**：读 `backend/realtime/companion_brain.py`（生成主流程）+ `backend/app/main.py`（`/chat/*` 路由）+ `backend/app/memory/context_builder.py`（`TEXT_CHAT_TAG_INSTRUCTION`）+ `backend/app/providers/router.py`（多 provider 调度）
- 若做 **真机验证 + commit**：重启后端实测，不需额外读文件

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/`（本轮抓的 Fish 文档缓存，结论已提炼进上面「方法论备注」）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务
**Fish Audio 全量文档深度研究**（通读官方文档，产出 `docs/FISH_AUDIO_REFERENCE.md`），
**完成后再用 `/architect` 拆解两阶段表达层架构 P8**（从文字聊天起步）。两件事不要混在一个 session。
