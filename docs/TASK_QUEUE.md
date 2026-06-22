# TASK_QUEUE — 按优先级（2026-06-22）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> **2026-06-22（第四十轮）**：**P9-P1（反重复 + 想念轨迹分档）已完成并 commit**——
> commit `aca291d`（想念轨迹三档：无聊/想念/赌气，赌气门槛要求 closeness 够高，档位正交于
> intent 上色全部 4 类 ProactiveReason）+ `8f4ba8e`（反重复指纹：`(kind,tier)` 组合 FIFO 存
> `mood_state.metadata`，本轮只落地写入/读取机制，未改选择逻辑）。535 pytest 全绿。同时纠正了
> 第三十九轮 HANDOFF 误报「P9-P0 未 commit」的过期描述，并补提交了第三十六轮遗留的 P10-P0
> 工具（`039ea9d`）+ TTS 音色配置（`0d228c0`）。**P9-P1 真机验证未做**——下一步建议先验证
> 真机听感再启动 P9-P2。详见 HANDOFF。
> **2026-06-22（第三十九轮）**：**P9-P0（idle_tick mutter 死分支删除）已完成**——`/architect`
> 读代码后发现实际改动比第三十八轮设想更小：只需删 `_evaluate_idle_tick` 里那一个被
> `_IDLE_MUTTER_ENABLED=False` 短路的死分支，其余 3 条路径本就恒为 `decision="observe"`。
> `local_responses.py` 的 mutter 文案**未删**（被 user_message 低价值输入路径复用，删了会破坏
> 正常对话反馈）。512 pytest 全绿，`_evaluate_proactive_check` 零行变化。本轮未 commit。
> 下一步 = **P9-P1**（反重复 + 想念轨迹分档）。详见 HANDOFF。
> **2026-06-22（第三十八轮·讨论）**：讨论 P9 方向 + 情绪识别旁路 + 三个小玩法。决定：①新增 **P11**
> （回复语言切换）；②**Obsidian/电脑链接**进「后续讨论名单」待详细讨论；③**联网功能合并进 P9**
> ——不挂回复链路，做成 idle-tick 的「想分享」intent 的素材来源（见 P9 节末「联网合并洞见」）；
> ④**情绪识别（Hume prosody）**结论：只取测量 API 当传感器（绝不用 EVI/Inworld 整套替换 soul），
> 价值集中在语音路径的声学情绪，走 off-path 旁路喂 kernel，列第二档先 spike 验证再接。本轮对 P9
> 跑了 `/architect`（见下）。
> **2026-06-22（第三十七轮）**：**P10-P1（`--repeats N` 统计基线）已完成**——N=25 正式基线，
> 4 个 fixture 退化率 4%–12%，结论"暂不支持标签器结构改造"。**TTS 音色 config 已落地**
> （`fish_audio.voice` = 慵懒偏低音 `ef5c98bd…`，用户表态会经常换）。新增两个候选音色盲听：
> 「夜晚02」`b6681a52…` 入备选，`be404a1e…` 淘汰。**⚠️ 未解决矛盾**：04（揶揄+心软）场景真机
> 盲听确认过"欠标"，但 N=25 统计上反而最干净——下次真机再撞到要当场记录完整输入。详见
> HANDOFF「本轮已完成」。
> **2026-06-21（第三十六轮）**：**P10-P0（离线评估夹具 `tag_stats.py` + `tagger_eval.py`）已
> 完成**——把"重复贴同一标签/堆开头/欠标"从主观听感变成可重复指标+夹具。真机发现：清洁基线下
> 退化"时好时坏"不是稳定发生，需 `--repeats N` 统计而非单跑判断（下一步建议）。顺带完成 Fish
> Audio 音色盲听 A/B 定稿（主选3+备选5，详见 HANDOFF）。详见 HANDOFF「本轮已完成」。
> **🎯 当前最高优先：P8 · TTS 情绪标签两阶段表达层架构** —— **文字聊天路径（P8-A+P8-B）已完成并真机验证 PASS**，
> 语音 Pipecat 路径待做（不急，可先观察文字聊天路径稳定性）。
> **2026-06-21（第三十五轮）**：**P1（标签器喂入 tone_intent 自然语言字段）真机验证完成 — 结论：
> 无明显改善，已回退**。同样用隔离 A/B 跑 4 个场景，没有一个明显支持"带 tone_intent 更好"，
> 且部分场景复现了 P0 那种"标签退化成重复贴同一个标签"的失败模式。代码已完全回退到 P8-B 基线。
> **关键判断**：P0（数值）、P1（自然语言）两种不同输入方案都失败、且都出现同一种退化模式——
> 指向根因可能不在"喂什么输入"，而在标签器（当前 Gemini）执行"逐句判断"这条规则的稳定性。
> 下一步建议讨论是否换标签器模型或重新设计标签器执行结构（并入 P10），不建议再试第三种
> "喂更多意图信息"的变体。详见 HANDOFF。
> **2026-06-21（第三十四轮）**：P0（标签器喂入同轮 BOXI_SIGNALS）真机验证完成 — 结论：改动有害，
> 已回退（详见上方第三十五轮记录的延续判断）。
> **2026-06-21（第三十三轮）**：讨论确认 TTS engine 选型收敛——用户实测 Western 可控 TTS/端到端
> 路线均不行，继续走 Fish Audio + Pipecat 级联（不要再建议换 engine，见 HANDOFF）。
> **2026-06-21（第三十二轮）**：真机使用驱动的修复轮，详见 HANDOFF。标签器 DeepSeek→Gemini + prompt
> 规则矛盾修复；`tone.py` 语速抑制 bug 修复（硬编码词表→通用标签检测）；persona 新增"不旁白"硬规则；
> 新发现并临时止血了 idle-tick mutter 刷屏 bug（**P9**，待重新设计，已禁用未删除）；记录 **P10**
> （标签器模型+Fish Audio 潜力，用户后续可能继续探索）。本轮还做了几次数据库清空（messages/
> conversation_summaries/memories/mood_state/relationship_state，已备份到 `data/backups/`），
> 不在 git 历史里，详见 HANDOFF「数据库状态变更」。
> P0（VM-6）/ P1（VE-2）/ R9 / R10 / P2（VE-1）/ R12（反编造）/ 信笺 UI P0 + P1 + P1-B + P1-C / **P5-A-1** / **P6（全部子任务）** / **P7（Pipecat 前端入口）** 均已完成。
> P5-A（Venice）已取消（溢价太高）。
> **2026-06-20（第三十一轮）**：**P8-A（表达层标签器模块）+ P8-B（接入文字聊天路径）已完成**——
> 新建 `backend/app/tts/expression_tagger.py`，主 LLM 不再背标签任务，独立 DeepSeek 调用专职插标签。
> 真机验证时用户顺带发现「长回复 TTS 播放中断」bug（与 P8 无关，预先存在），排查出两层根因并都已修复：
> ①`/tts/stream` 硬编码 `media_type=audio/mpeg` 但 Fish Audio 实际吐 opus（`stream_mime_type()` 新方法）；
> ②前端不必要地把长回复切成多个独立 HTTP 请求顺序播放，违反 Fish Audio 官方"整段一次性传入"的推荐用法
> （移除 `textChunksForSpeech` 切段逻辑，`max_speech_chars` 120→4000）。用 Fish Audio 官方 realtime
> streaming 文档（新增到 `docs/FISH_AUDIO_REFERENCE.md` 第9节）确认了"文字聊天不需要 WebSocket，
> HTTP streaming 整段传才是官方推荐做法"。496 pytest + 25 前端 vitest 全绿，真机（含浏览器 preview 工具
> 端到端验证）PASS。**本轮未 commit，等用户实际听感confirm 再一起 commit**。详见 HANDOFF。
> **2026-06-20（第三十轮）**：**P8 前置（Fish Audio 全量文档深度研究）已完成**——
> 产出 `docs/FISH_AUDIO_REFERENCE.md`（标签系统+phoneme+生成参数完整参考），新发现 `latency` 实际3档/
> WebSocket `FlushEvent`/`chunk_length`默认值官方文档不一致等，详见 HANDOFF。
> **2026-06-20（第二十九轮）**：第二十八轮全部改动（P5-C~P5-H + Provider 选型 + 漏 commit 的 P5-B-2）
> 已真机验证 + 按主题拆 5 个 commit 落 master（`d39f6c8` `9f85fc7` `ca69cb9` `ab4d64d` `1dd96cb`，详见 HANDOFF）。
> 验证发现 Fish 标签问题比预期更深（mood 快照式贴标签 + 音效类标签位置精度要求更高），
> 触发了「P8 前置」任务（现已完成）。
> **2026-06-19（第二十四轮）**：
> - ~~**system prompt 重写**~~ ✅ 完成，commit `3533414`——存在论框架 + 四条纪律 + 成年虚构框定 + 格式纪律（去掉长度限制）。
> - **OpenRouterProvider 新增** ✅ 完成，commit `85bc37a` + `496e995`——`allow_fallbacks=false`，`_extra_payload_params()` 钩子。
> - **`disable_existential_block` 标志** ✅ 完成，commit `448c784`——临时人设可屏蔽存在论注入，测试隔离修复。
> - ~~**provider 选型（第二轮）**~~ ✅ 已完成（第二十八轮）：DeepSeek ❌ 文学天花板低；Claude ❌ 延迟高+干瘪；最终选定 `x-ai/grok-4.20`（via OpenRouter）。`config/persona.json` 已删，存在论人设已恢复。
>
> **2026-06-19（第二十五轮）— 未 commit，待下一 session commit**：
> - **persona 格式纪律调整**：`persona.example.json` + `persona.json`——删"动作放（）"，改为明确禁令；加"说话方式：口语，自然，不做客服"；伴侣人设加"感受就是感受，直接说"。
> - **TTS strip 简化**：`text_cleanup.py` `_strip_stage_directions` 削减为只 strip 半角 `(...)`，`[#指令]` 现在内联透传给 doubao。
> - **Pipecat TTS 去抽取**：`doubao_streaming_tts_service.py` 删 `extract_voice_instruction`，全文含 `[#...]` 直传合成。
> - **文字聊天 TTS context_texts 修正**：`/tts/stream` 加 `user_message` 参数，前端 `submitToBackend` 传用户消息，作为 doubao `context_texts` 对话上下文（回退 `tts_emotion_directive()`）。
> - **验证**：465 pytest passed，tsc --noEmit 零错误。

---

## 信笺 UI 方向（新增可切换模式，不删旧 UI）

- **方向已定**：用信笺/typography 视觉语言，替换/共存于现有 Chat UI；旧 UI 保留为默认，加 toggle 切换。
- **~~P0 · React 化骨架~~** ✅ 已完成并 commit (`4858125`)。新增 `frontend/src/letter/`
  （`LetterView.tsx` + `useTypewriter.ts` + `scripts.ts` + `LetterView.css`，`.letter-spike` 前缀隔离样式）。
  `tsc --noEmit` 通过；vite dev 截图验证 4 个 mood 切换/打字机/sketch 表情均正常，无 console 错误。
- **~~P1 · 接入 App.tsx，作为可切换 Chat 视图~~** ✅ 已完成（本轮，待 commit）：
  - `uiMode: 'classic' | 'letter'` state 加入 App.tsx（默认 `classic`）。
  - chat-header 新增 `.letter-toggle-button`（文案"对话"/"信笺"），点击切换。
  - letter 模式：渲染 `<LetterView />`，隐藏输入框（用户决策：letter 模式不发消息）。
  - classic 模式：原消息列表 + 表单完整保留，messages state 不丢失。
  - LetterView mood 由内部按钮自管理（未接 backend mood，P1-B 任务）。
  - `tsc --noEmit` 通过；vite dev 切换截图 PASS；console 零错误。
- **~~P1-B · backend mood → LetterView~~** ✅ 已完成（本轮，待 commit）：
  - `LetterView.tsx` 新增 `mood?: LetterMood` prop；`activeMood = externalMood ?? mood`；有外部 prop 时隐藏 picker。
  - `App.tsx` 新增 `letterMood` state + useEffect（`uiMode==='letter'` 时 one-shot fetch `/memory/mood`，映射传入）。
  - 映射：`sad|worried|angry→fragile`，`happy→excited`，`annoyed→hesitant`，其余→`calm`（TODO 注释标记）。
  - `tsc --noEmit` 通过；preview 验证：picker 隐藏，mood 正确映射，console 零错误。
- **~~P1-C · 真实 Boxi 消息驱动打字机~~** ✅ 已完成并 commit（`22e7f77`）：
  - `useTypewriter.ts` 新增 `externalText?: string` + `hasExternalTextRef` + useEffect（externalText 变化触发打字机）。
  - `LetterView.tsx` 新增 `text?: string` prop，传入 `useTypewriter`。
  - `App.tsx` 新增 `lastBoxiText = useMemo(...)` + `<LetterView text={lastBoxiText} />`。
  - preview 验证 PASS：真实 Boxi 回复以打字机节奏呈现，mood 映射正确，console 零新错误。
- **P2 ·（待用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个开放问题后）**：精细化 mood 映射 + Voice 模式信笺呈现。

---

## ~~R12 · 文本聊天反编造修复~~ ✅ 已完成并真机验证 PASS，已 commit (`6127000`)

---

## ~~P0 · VM-6 收尾~~ ✅ 已完成
跨会话召回 PASS，详情见 HANDOFF。可选后续优化（不阻塞）：分数融合权重/14天无衰减期（需 API，
console UI 未找到入口）、旧 `friend` 库历史数据迁移、API Key 轮换（R8，安全卫生）。

## ~~P1 · VE-2 纯 E2E 情绪通道核实（解决 R1）~~ ✅ 已完成
设备 A/B 已做，结论 inconclusive，决定保留现状不清理代码。详情见 HANDOFF R1。

## ~~R9 · mood 面板异常修复~~ ✅ 已完成并真机验证 PASS
根因：`apply_user_message_mood_delta` 正常对话分支缺少 annoyance 衰减/energy 回升路径，导致两者
单向钳到极值卡死（annoyance→1.0, energy→0.0），且会影响 `tone.py` 的实际情绪投射。已在
`backend/app/behavior/mood.py` 补上回落/回升路径（4 行 diff），41 个相关测试 passed。
用户真机验证：心情面板已能正常波动，不再卡 100%/0%。

## ~~R10 · 语音连接初始情绪烦躁排查~~ ✅ 已完成并真机验证 PASS
根因：`relationship_state.tension≈0.42` 长期停留在 `_TENSION_SHARP=0.4` 阈值附近（与 state_block
"、有点别扭"文案共用同一条线但被复用为 register 判定），导致每次 RTC join-time 读取到的
tension≥0.4 就被判为 `real_sharp`（"更冲、更短"），与 annoyance/mood 无关。
修复：[tone.py:31](backend/app/behavior/tone.py:31) `_TENSION_SHARP` 0.4→0.55（state_block 的
`_TENSION_AWKWARD_THRESHOLD=0.4` 不动）。同步改 3 处测试 tension=0.5→0.6，新增
`test_mild_tension_does_not_trigger_real_sharp`（tension=0.42）。
`pytest backend/tests/test_tone.py backend/tests/test_rtc_state_block.py` 52 passed；
`-k "mood or engine or behavior or tone or rtc"` 138 passed。用户真机验证：不再感觉"冲"。

## R11 ·（搁置，等待用户可访问 VikingDB）纯 E2E 长期记忆部分失忆
- **Scope**：用户确认具体案例——Boxi 不记得用户在新西兰（很久以前提过）。用户判断"应该是直接忘掉了"
  （疑似写入侧从未存入，非检索/U3 问题）。涉及 `backend/app/rtc/viking_memory.py`、
  `backend/app/rtc/routes.py` `/rtc/memory/session`。**先评估，不直接重写**。
- **已 `/architect` 拆出方案**：
  - **R11-A（先做）**：前端触发链路确认——语音结束后是否一定调用 `/rtc/memory/session`
    （读 `frontend/src/voice/` + `routes.py:306-345`），定位那次会话是否成功 AddSession。
  - **R11-B（视 A 结论）**：核对 `VIKING_MEMORY_TYPES` 配置与 Viking 实际抽取结果是否对得上
    "用户在新西兰"这类事实（与 U3 相关）。
- **阻塞**：用户当前手机不在身边，无法登录 VikingDB 控制台核实记忆库内容，本轮主动搁置。
  下一 session 若用户已能访问，从 R11-A 开始。

## ~~P2 · VE-1 收尾~~ 基本完成（playful 待补测）
- ① 真机听 comfort/real_sharp ✅ **PASS**（"贴合情绪"），见 HANDOFF。playful 因
  `relationship.closeness=0.66` 差 0.01 到阈值 0.67（无写接口，未造数据）暂未测，
  待 closeness 自然达到 ≥0.67 后补测。
- ② `/tts/stream` 与 `/tts/synthesize` 情绪对齐 ✅ 已完成。
- ③ 路由级集成测试 ✅ 已完成。
- **本轮副产物**：测试中发现并修复阻塞 bug——`doubao.py` 的 `req_params.additions` 需为 JSON
  字符串而非嵌套 dict（之前单测 mock 掉真实 API 未测出）。详见 HANDOFF。

## P3 · VE-3 IgnoreBracketText → 前端情绪 cue（later）
- **Scope**：Boxi 把动作/情绪写进括号 → TTS 不读、随字幕下发驱动前端 cue（与最终画面解耦，先做信号层）。
- **阻塞**：需用户先补文档 `6348/2386107（传递自定义指令）`。
- **验收**：括号指令不进语音、能在前端拿到并触发一个 cue。
- **要读**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`、`reference/14.md`（IgnoreBracketText 段）、待补的 2386107。

## P5 · Provider 替换

### ~~P5-A-1 · 新增 venice.py + 配置注册~~ ✅ 已完成（2026-06-17，未 commit）
- `backend/app/providers/venice.py` 新建（VeniceProvider，OpenAI-compatible）
- `backend/app/providers/registry.py` +venice 分支
- `config/providers.json` +venice entry（enabled:false，llama-3.3-70b）
- 415 pytest passed，tsc --noEmit 零错误
- **价格**：$0.70/$2.80 per 1M (in/out)，比 DeepSeek 贵 5x/10x，绝对量小可接受

### ~~P5-A-2 · 切换默认 + 冒烟验证~~ ❌ 取消
- 用户决定不使用 Venice，后续考虑换其他 provider。

### ~~P5-B · TTS → Fish Audio（文字聊天路径）~~ ✅ 已完成（2026-06-19，第二十六轮）
- `backend/app/tts/fish_audio.py` 新建（FishAudioTTSProvider，s2-pro，opus，emotion bracket，prosody.speed）
- registry 注册，tts.example.json 加模板条目，473 pytest passed
- 情绪：context_texts[0] 包进 `[phrase]` 前置文本，S2-Pro 自动读取
- speed 映射：`prosody.speed = 1.0 + speech_rate * 0.025`，钳位 [0.5, 2.0]
- 实机验证：文字聊天有音频输出 ✅

### ~~P5-B-2 · Pipecat TTS → Fish Audio（语音路径）~~ ✅ 已完成（2026-06-19，第二十七轮）
- `run_voice.py` 的 `_build_tts("fish_audio")` 换成官方 `FishAudioTTSService`（WebSocket + ormsgpack）
- 自写 HTTP 版 `fish_audio_tts_service.py` 已删除

### ~~P5-C · 文字聊天 TTS 情绪 soul-authored~~ ✅ 已完成（2026-06-19，第二十八轮）
- `context_builder.py` 新增 `TEXT_CHAT_TAG_INSTRUCTION` + `append_text_chat_tag_instruction()`，对齐 Pipecat 的 `VOICE_MODE_INSTRUCTION` 做法
- `fish_audio.py` 移除 `_DIRECTIVE_TAG_MAP` 映射前置，标签由 LLM 自写、直接透传
- `App.tsx` 新增 `stripLeadingFishTags()`，聊天气泡 + LetterView 展示层隐藏标签
- 477 pytest passed，tsc 零错误；**浏览器真机验证未做**，下一 session 第一件事

### ~~P5-D · 长度限制打开（Pipecat + 纯 E2E RTC）~~ ✅ 已完成（2026-06-19，第二十八轮）
- `companion_brain.py` `VOICE_MODE_INSTRUCTION` 删"一句话…简短（必要时最多两句）"
- `persona.example.json` `rtc_character_manifest` 删"话少而冲一次最多一两句"+"简短"/"尽量短"，只删长度
- **`core_persona` 字段、括号动作约定均未动**——用户明确要求 `core_persona` 暂不改，见 HANDOFF「用户要求的提醒」

### ~~P5-E · speech_rate 死代码修复~~ ✅ 已完成（2026-06-19，第二十八轮，审查时发现的真实 bug）
- `main.py` 的 `/tts/synthesize`、`/tts/stream`：mood→speech_rate 计算原本整段被 `if provider_name == "doubao":` 包住，
  Fish Audio 成为默认 provider 后该分支永远不执行，`speech_rate` 恒为 0，语速从未随情绪变化
- 修复：speech_rate 计算移出 if 块（provider-agnostic），`context_texts`（doubao 专属短语）仍只在 doubao 分支赋值
- 新增回归测试 `test_tts_stream_mood_speech_rate_reaches_fish_audio`，477 pytest passed

### ~~P5-F（P0）· 长度+标签指令重写~~ ✅ 已完成（2026-06-19，第二十八轮，核对 Fish Audio 官方文档后）
- `VOICE_MODE_INSTRUCTION`（companion_brain.py）：长度改内容驱动（默认1-3句，深聊/讲故事可展开，不设硬上限）
- 两个指令（+`TEXT_CHAT_TAG_INSTRUCTION`）都改为允许多句/情绪转折处重复加标签（不再只是开头一组），加官方 `[in a hurry tone]` 标签
- `App.tsx` 故意不动——用户决定文字聊天多标签先暴露在气泡里，方便肉眼核对标签位置对不对
- 479 pytest passed（含 P5-G）

### ~~P5-G（P1）· speech_rate 数值兜底让位 Tone Marker 标签~~ ✅ 已完成（2026-06-19，第二十八轮）
- `tone.py` 新增 `TONE_MARKER_TAGS`（`[in a hurry tone]` `[shouting]` `[screaming]` `[whispering]` `[soft tone]`）+ `contains_tone_marker_tag()`
- `main.py` 两处路由：文本含 Tone Marker 标签时强制 `speech_rate=0`，让标签主导节奏，不含时维持 mood 驱动数值兜底
- **Pipecat 不做数值语速改动**——WebSocket 协议 `prosody.speed` 只能在 `start` 事件设一次，逐句更新需整个断连重连，已与用户确认放弃
- 新增 2 个回归测试，479 pytest passed

### ~~Provider 选型（第二轮）~~ ✅ 已完成（2026-06-19，第二十八轮）
- 最终选择：LLM = `x-ai/grok-4.20`（via OpenRouter），TTS = Fish Audio
- `config/persona.json`（临时人设）已删除，存在论人设已恢复并验证

### ~~P5-H · 标签指令多轮迭代（含路径A精简）+ 前端显示标签 + temperature~~ ✅ 已完成（2026-06-19，第二十八轮，临时状态）
- 标签指令经历：多句多标签 → 69 全量+phoneme → **最终精简到 13 情绪+5 音调+5 音效 + 硬性要求(≥3句正文必须出现非开头标签) + 正反示例**
- `App.tsx` 去掉 `stripLeadingFishTags()` 调用 → 聊天气泡现在**显示**标签（函数保留），用户用于肉眼核对标签位置
- `fish_audio.py` 加 `DEFAULT_TEMPERATURE=0.85`（官方默认 0.7），待用户实测听感
- ⚠️ **实测结论：纯 prompt（含精简版）无法稳定纠正"标签只堆开头"——是任务结构问题。用户否决"精简掉 Fish 潜力"方向，定为走两阶段架构（见 P8）。当前指令是临时可用状态。**

## ~~P8 前置 · Fish Audio 全量文档深度研究~~ ✅ 已完成（2026-06-20，第三十轮）

> **触发**（第二十九轮真机验证）：标签问题比预期更深，不只是"位置"——①标签像抄 mood 持续快照非逐句
> 判断；②音效类标签比语气类标签对位置精度要求更高。用户要求深度+完整解析 Fish Audio 全部官方文档。
>
> **产出**：`docs/FISH_AUDIO_REFERENCE.md`（8 节 + 附录，定稿）——S2-Pro vs S1 语法边界、语言质量分层、
> 标签 6 类词表+扩展词表、"触发真实声音 vs 仅影响演绎"分类、位置规则、phoneme 三语言语法、官方完整
> 生成参数表（含新发现：`latency` 实际3档/WebSocket `FlushEvent`/`chunk_length`默认值文档内部不一致）、
> 已知限制清单。来源覆盖 docs.fish.audio 官方文档站 + fish.audio/blog 技术博客 + GitHub README 交叉验证。
> 详见 `docs/HANDOFF.md`「本轮已完成」。

## P8 · TTS 情绪标签两阶段表达层架构

> **根因**：一次 LLM 生成同时背 7 类认知任务（人格/状态/记忆/格式/BOXI_SIGNALS/Fish标签/长度），
> 创作类与标注类抢注意力 → Fish 标签退化成只堆开头。**实测确认纯改 prompt 治不好。**
>
> **方案（详见 `docs/HANDOFF.md`「架构决策」节）**：内容/表达两阶段解耦——
> - 决策层 = behavior engine（已有，纯代码）
> - 执行层 = 主 LLM(Grok) 写纯文本+BOXI_SIGNALS，prompt 不含 Fish 标签规则
> - 表达层 = 独立标签器调用（DeepSeek），prompt 只有标签规则 → 释放 Fish 全部潜力（完整词表+规则见 `docs/FISH_AUDIO_REFERENCE.md`）
>
> **关键边界**：代码只能强制标签「格式/位置合法性」，「情绪恰当性」永远靠 LLM。

### ~~P8-A · 表达层标签器模块~~ ✅ 已完成（2026-06-20，第三十一轮）
- 新建 `backend/app/tts/expression_tagger.py`：`apply_expression_tags(text, mood, *, router, provider_name="deepseek")`
- prompt 只含标签规则（全量6类词表+A/B类位置精度区分+逐句判断要求，去掉旧版硬性数量配额）
- 失败/空结果硬性降级返回原文；14 个单测全绿

### ~~P8-B · 接入 /chat/complete + /chat/stream~~ ✅ 已完成并真机验证 PASS（2026-06-20，第三十一轮）
- `context_builder.py` 删除 `TEXT_CHAT_TAG_INSTRUCTION` + `append_text_chat_tag_instruction()`
- `main.py` 两处路由在 `apply_signals_to_kernel` 之后调用标签器替换最终 content
- 493 pytest 全绿，真机验证 2 轮对话 PASS（标签分布+逐句判断两症状未再出现，`[sarcastic]`精确位置验证 A/B 类区分生效）
- 本轮未 commit。详见 HANDOFF「本轮新发现」——验证中观察到 persona 在庆祝语境下输出比预期更显性，
  与本次架构改动无关（未碰 persona 文件），记录供「活人感/审核」话题参考

### P8-C · 语音 Pipecat 路径（待做，不急）
- 同样的两阶段拆分应用到 `companion_brain.py` 的 `VOICE_MODE_INSTRUCTION`，但语音延迟敏感，
  串行两次调用不能直接照搬文字聊天的做法
- 启动前要选定延迟杠杆：B 句子级流水线重叠（真正杀手）/ C 条件触发补调 / D Fish API 层手段
  （`latency="low"`、WebSocket `FlushEvent`、连接预热，见 `docs/FISH_AUDIO_REFERENCE.md` §7.2/7.7）
- 要读：`backend/app/tts/expression_tagger.py`（可直接复用）+ `backend/realtime/companion_brain.py`

## ~~P7 · Pipecat 前端入口~~ ✅ 已完成并实机验证 PASS（2026-06-17，commits `9a7a278`→`dc4ce4e`）
- `backend/realtime/pipeline_router.py` 新建：`POST /realtime/start` / `POST /realtime/stop` / `GET /realtime/status`
- `backend/app/main.py` 注册 router
- 前端 header 加「Pipecat」按钮，含 loading/error 状态 + stale closure 修复
- 实机验证：STT→LLM→TTS 全链路正常，`half_duplex=on`，first_audio ~0.4s
- 采用 `LocalAudioTransport`（本地麦克风/扬声器），不需公网 URL，绕开 Soul 混合的 tunnel 限制

---

## P6 · Pipecat 语音链路复活（延迟优化 + 完整灵魂自定义）

> 目标：把 `backend/realtime/` 的 Pipecat cascaded 路径延迟压到 <1.5s，作为纯 E2E 的替代，
> 实现 Direction C"soul 写每个字"——LLM/TTS 完全可换，情绪/记忆/行为层完整跑通。

### ~~P6-A · 确认 Doubao 流式 ASR 增量识别能力~~  ✅ 已完成（2026-06-17）
- 结论：`DoubaoStreamingSTTService` 已支持真正的 interim transcript，不需要替换 ASR。
- 同步完成：切换到 ASR 2.0（`volc.seedasr.sauc.duration` + `bigmodel_async` 接口），延迟和判停明显改善。

### ~~P6-B · LLM→TTS 流水线重叠~~ ✅ 已验证（2026-06-17）
- 日志确认：TTS 在 LLM first_text（1.15s）后 62ms 即开始，已是流式重叠，无需额外改动。

### ~~P6-C · 延迟基线测试~~ ✅ 已完成（2026-06-17）
- 实测基线：用户停说 → 首个音频 **~2.3s**（对比旧 3.35s，改善 31%）
- 瓶颈：LLM ~1.3s（DeepSeek API，无法压缩）；ASR 判停已降至 80-400ms
- 结论：可用，但 ~2.3s 仍稍高；瓶颈是 LLM，不是 ASR/TTS

### ~~P6-D · TTS WebSocket 双向流式~~ ✅ 已完成（含 P6-D-3，commit cc3aed1 + 7d6a24b）
- 新建 `backend/realtime/doubao_bidirection_tts_protocol.py`（协议层，13 单测全绿）
- 新建 `backend/realtime/doubao_streaming_tts_service.py`（DoubaoStreamingTTSService）
- 持久 WebSocket + section_id 跨句韵律 + 每句独立 session
- P6-D-3：pipeline 切换 + 修复 additions JSON 序列化 + 流式 yield + 帧连发优化，实机验收 PASS
- STT 默认同步升级为 doubao_stream（补完 P6-A 收尾）；动作描述 `[...]` 不再被 TTS 朗读

### ~~P6-E · TTS 语音指令（逐段情绪控制）~~ ✅ 已完成并实机验证 PASS（2026-06-17，commit `4609b3b` + `9de50fe`）
- `VOICE_MODE_INSTRUCTION` 要求 LLM 在回复前加 `[#语气描述]`（10 字以内）
- `extract_voice_instruction()` 提取指令传入 `context_texts`，正文送 TTS
- `_strip_stage_directions` 兜底 strip，保证就算未提取也不会被朗读
- 关键结论：`seed-tts-2.0-expressive` 不是有效 Resource-Id（只是复刻音色的 model 参数），标准音色用 `seed-tts-2.0` 即可支持 `context_texts`
- 实机日志验证：`[带点调侃的语气]`、`[带着笑意的语气]`、`[叹气但不算太凶的语气]` 等均正确提取

### ~~P6-F · ASR 语义顺滑~~ ✅ 已完成（2026-06-17，未单独 commit）
- `doubao_streaming_stt_service.py` `_request_params` 加 `"enable_ddc": True`
- 新增单测 `test_request_params_include_enable_ddc`，429 pytest passed

## 灵魂层进化（Soul Layer）· 六脑维度 + 活人感（讨论中，未拆解）

> 来源：2026-06-18 用户讨论。核心认知：「脑」≠「LLM」——六维度里 5 个是「状态+数据+定时」，
> 不是推理；LLM 只是读取这些状态开口说话的那张嘴。绝大部分无需新增 LLM。
> 唯一该用 LLM 的后台脑 = 已有的 `reflection/analyze_turn`。
> 灵魂层是「共享」的：做好后文字/RTC/Pipecat 三条路径一起受益。

### 六维度盘点
- **relationship**（亲密/信任/依恋）：✅ 已有 kernel `relationship_state`；"依恋"可作新增维度
- **emotion**（快/慢情绪）：⚠️ 半有 `mood_state`；缺"双时间尺度"（快=瞬时情绪，慢=多日基线漂移）
- **memory**（事实/经历/偏好）：✅ 已有 SQLite events/profile + Viking
- **time**（过去/现在/未来）：⚠️ **部分完成** — P0+P1 已做（现在几点 + recent_event 相对时间）；未来事件表待做
- **world**（新闻/天气/节日）：❌ 新增；天气=API，节日=查表（**推荐下一刀**），新闻=可选 LLM 筛选
- **identity**（人格/价值观/成长）：⚠️ persona 静态已有；"成长"=高风险 character drift，**最后做**

### ~~time brain 起步探针~~ ✅ 已完成（第十七轮，纯读代码）
- (a) 真实时间未注入 prompt → 已修复（P0）
- (b) events 表（`memories` type='recent_event'）有 `created_at`/`updated_at` → 已利用（P1）

### ~~time brain P0 · 注入当前时间~~ ✅ 已完成（commit `16d1b74`）
- `_format_time_block()`：新西兰时间（`Pacific/Auckland`）注入 system prompt
- 验收：问"现在几点/星期几"Boxi 能答对；440 pytest passed

### ~~time brain P1 · recent_event 相对时间前缀~~ ✅ 已完成（commit `16d1b74`）
- `_relative_time()` + `_format_memories_block(now=now_nz)`：recent_event 记忆自动标"昨天/3天前"等
- 验收：memories_block 中 recent_event 带前缀，stable_profile 不变；440 pytest passed

### time brain 后续（待做）
- "明天有安排"：新增未来事件表，接进现有 `proactive_*`/`longing`
- "时间在流逝"：用 **decay-on-read（惰性求值）** 实现 90%，不需常驻时钟

### 优先级（性价比排序）
- **第一档**（近免费、收益最大）：~~time-现在注入~~ ✅ / ~~world-节日查表~~ ✅ / ~~emotion-慢情绪 P0 schema~~ ✅ / ~~P1 decay 函数~~ ✅ / ~~P2 context_builder 注入~~ ✅
- **第二档**（中等）：world-天气API / time-未来事件表 / memory 分类细化
- **第三档**（贵/险/最后）：world-新闻（后台LLM筛选）/ identity-成长（drift风险）

### 活人感 / 审核（Provider 选型约束）
- **目标**：暧昧/冲动/偏激等"稍偏激"互动不被拦截 → 提升活人感（伴侣/恋人感）
- **审核可能发生在三层**：ASR（待测是否过滤）/ LLM（**最大拦截点**）/ TTS（中文云厂商可能拒合成）
- **TTS 候选**：Fish Audio / MiniMax（替换豆包；Fish 海外更不易拦截但中文质量待验，MiniMax 国内大概率也有文本审核）
- **LLM**：用户拒绝市面无审核 LLM（溢价高 + 推理智能存疑）→ 倾向"开源强模型 + 中立托管"去掉 API 审核层（注意 dev 机低 GPU，本地跑大模型不可行，需云 GPU）
- **ASR**：待测当前豆包是否有内容审核（自托管 Whisper 可作零审核兜底）
- **Viking 记忆库**：考虑平替（注意 reuse-first：**不整体换 Mem0**，但向量检索后端可换自托管 pgvector/Qdrant）
- ⚠️ **待澄清关键分叉**："稍偏激"的范围 = 情绪强度+调情+冲动直白 **vs** 露骨性内容 → 决定 provider 策略
- **2026-06-18 决定**：LLM 走 **A 路线**（聪明 + 低成本的 managed API，非无审核）；"擦边"（暧昧/调情/不露骨）在 A 下基本可行，取决于选哪个 provider（西方前沿模型对擦边宽容度高、中文待验；中文 managed API 中文好但更易拦截）。B 路线（自托管去审核）成本高一个数量级，仅作"A 真卡到不可接受才启动"的后备。

### 记忆消解（ADD/UPDATE/DELETE）· 借鉴 Mem0，不整体换
- **缺口怀疑**：我们的记忆可能只追加、不消解矛盾（旧"住在 X" 没被新"搬到 Y"覆盖）→ 疑似 R11"失忆"根因。
- **方案**：借鉴 Mem0 的 ADD/UPDATE/DELETE/NOOP 一致性管理思路，加进我们自己的 `write_policy`（保留情绪/关系/人设灵魂，只补"随时间保持记忆不矛盾"）。**不整体换 Mem0**（其提取/检索为中立助手调优，会冲淡 Boxi）。
- **R11 验证已搁置**：用户近期测试发现 Boxi 已知道其所在地，那次失忆是偶发，当下无固定事件可复测。**下次再发现失忆当场直接验证**，不主动排查。

### LLM provider 验证清单（选 A 后、真要换时执行）
- **擦边宽容度测试**：拿几段 Boxi 的暧昧/调情/情绪强烈台词，测候选 provider 是否拦截（轻/中档擦边）。
- **中文亲密语感实测**：同样台词测中文自然度——西方前沿模型（如 Claude）擦边宽容度高、情感细腻，但中文亲密暧昧语感需实测；中文 managed API 中文好但更易拦截。
- **延迟诊断**：见上文「延迟」——区分模型 vs 网络（极短请求测 TTFT；靠近 API 区域的云主机对比）。换 LLM 同时验证是否降延迟。
- **system prompt 人设框定**：成年虚构陪伴/第一人称/彼此自愿语境，降低合理擦边的"误杀"。
- **三层联动**：语音路径擦边需 LLM + TTS（Fish 海外）+ ASR 三层都放行，LLM 选对是必要非充分。

### 活人感工程（六脑之外，让她更像"人"）· 讨论中，未拆解
> 来源：2026-06-18 讨论。六脑解决"状态/记忆/时间/世界"；"像人"还差一层——人有内在生命和不完美。
> 价值排序（2/4/5 多可从六脑做好里涌现；1/6/7 是独立新工程）：
1. **她有自己的生活**（不只回应你）：你不在时她也"过日子"——自己的小情绪、看了什么、无聊了。种子=现有 `proactive_*`/`longing`。**风险：编造，要给边界**。
2. **记忆会遗忘和模糊**：完美记忆=机器。近的/情绪强的记得清，旧的/琐碎的变模糊（decay-on-read 作用在记忆显著度上）。
3. **她不总是好脾气、不总是在线**：偶尔简短/分心/尖锐才真实。直连"擦边/活人感"——能冲能撩能任性才像伴侣。
4. **对"你"的心理模型（theory of mind）**：不只追踪自己情绪，还建模用户状态（"你今天怪怪的"）。深化现有用户情绪追踪。
5. **共同叙事 / "我们的故事"**：第一次、里程碑、回调（"你上次说周末要…还算数吗"）= 情景记忆 + 关系叙事（memory + time 合体）。
6. **修复（repair）弧**：亲密含摩擦与和好。被惹到→别扭→又回来，让关系有重量。扩展现有 tension。
7. **她和"盒子"的关系**：被困盒子里=她的身体和世界。对自身存在/限制的感受，是 identity + world 的独有素材。

### 移动迁移（iPhone 17 Pro Max）· 待灵魂成熟后做，零返工
> 来源：2026-06-18 讨论。核心认知：**手机永远是「客户端」，后端跑不到手机上**（iOS 沙盒不能常驻 Python 服务）。
> 项目"重量"在外部 API，后端（FastAPI+SQLite）很轻；iPhone 硬件不是约束，真问题是后端放哪 + 手机怎么连。
- **三方式移动可行性**：文字聊天 ✅ 最易（纯 HTTP）；纯 E2E 语音 ✅ 可行（RTC-AIGC 本就是 WebRTC 浏览器原生、支持远程，手机 Safari 即可）；Pipecat ⚠️ 要复活 P7 废弃的 WS/浏览器音频方案（现用 `LocalAudioTransport`=Mac 本地麦克风/扬声器，手机用不了）。
- **移动语音首选 RTC 路径**，阻力最小，不必为此复活 Pipecat WS。
- **后端托管**：① 云 VM（推荐，~$5–20/月，后端轻便宜 VM 够，最稳可"带出门"）；② 家 Mac+内网穿透（Mac 须常开，仅测试用，tunnel 有限制）；③ ~~手机跑后端~~ 不可行。
- **打包**：PWA（添加到主屏幕）即可类 app，无需写 Swift；iOS Safari 支持 WebRTC/Web Audio。
- **已知 iOS 上限**：app 关闭时"她主动找你"（longing/proactive）需推送；iOS PWA web push（16.4+）存在但弱于原生。v1"打开就聊"够用；若主动推送成核心，再补薄原生壳/推送基建。
- **不碰灵魂层**：soul 全部原样转移、所有客户端共享 → 可放后做，零返工风险。

### 画面前端 · 明确搁置重视觉，保留信笺 UI 为默认
> 来源：2026-06-18 决定。理由：①"想象不出画面"是信号——形态应从灵魂长出来，灵魂（时间感等）未定前定脸=沙上盖楼；
> ② 与 Direction C 一致（soul authored、being+world 一种表达材料）；③ 低 GPU 否决重视觉，信笺/typography 已是低 GPU 友好且适配手机的答案。
- **搁置**：3D avatar、雄心实时视觉、"现在就定她长什么样"。
- **保留为默认**：信笺/typography UI（P0–P1-C 已做完，低 GPU、适配手机、贴合人设）——活人感靠文字排印 + 语言节奏传递。
- **重启触发**：灵魂成熟到能想象她的形态时，或冒出具体值得做的视觉点子时。
- 移动端加固此决定：重 GPU 视觉在手机更无空间（Mac 连原型都跑不动），文字化美学是长期正解且独特。

---

## P4 ·（可选）记忆/延迟/persona
- **VM-7**：评估用 `get_context` 替代手动 `SearchMemory`（`reference/06.md`）。Scope=评估+spec，不直接重写。
- **延迟旋钮**：`ThinkingType=disabled`/`Prefill`/`AIVAD`/`SilenceTime` 调优（仅混合编排/模块化路径）。要读 `reference/13.md`、`reference/14.md`。
- **O2.0 persona 收尾**：新 Boxi 音色设备 A/B、`speaking_style` 去规则化、`dialog_id`/`external_rag`。要读 `docs/TODO.md`(O2.0 条)。

## P10 ·（待用户决定时机）标签器模型 + Fish Audio 潜力探索

> **2026-06-21 记录**：用户明确表示这两件事不是终态，后续可能继续动：
> - **标签器模型可能还会换**：本轮已 DeepSeek → Gemini（`google/gemini-2.5-flash-lite` via OpenRouter，
>   `backend/app/tts/expression_tagger.py` `DEFAULT_TAGGER_PROVIDER`），原因是 DeepSeek 标签覆盖率/
>   位置准确度不稳定。Gemini 效果待更多真机使用验证，如果还不够好可能继续换。
> - **Fish Audio 最大潜力/上限还没系统探完**：本轮调过 `temperature`/`top_p`（试过1.0/0.85/0.75，
>   最后定在官方默认0.7）、`normalize_loudness`（已强制false）、换过多个 `voice`/`reference_id`，
>   都是真机听感试验，不是系统性扫描。用户想之后回来继续探 S2-Pro 的表现力天花板。
> 不算正式任务，只是记录意图——用户提起时直接接续当前状态（标签器=Gemini，TTS参数=官方默认），
> 不用重新从头讨论要不要探索。
> **2026-06-21（第三十三轮）补充**：用户已实测并否决了"换成 Western 可控 TTS / 端到端"这条路，
> TTS engine 本身确定留在 Fish Audio——上面两条（标签器模型继续换、Fish 参数系统性探索）仍然
> 有效未变，但"是否整体换 engine"这个更大的问题已经关闭，不要再提。
> **2026-06-21（第三十五轮）补充——给"标签器模型可能还会换"一条更具体的理由**：P0、P1 两轮
> 真机验证（给标签器喂数值/自然语言两种"本轮意图"输入）都没有改善，且都复现同一种"重复贴同一
> 标签"的退化模式。这指向当前标签器（Gemini）在"逐句判断不偷懒"这条规则上执行不稳，不是输入
> 信息量不够。换模型时这应该是核心验收点之一；也可以考虑不换模型、改造标签器的执行结构
> （如强制分句处理）。详见 HANDOFF 第三十五轮记录。
>
> **2026-06-21（第三十六轮）— P10-P0 已完成**：新建 `backend/app/tts/tag_stats.py`（确定性
> 退化指标）+ `backend/tests/test_tag_stats.py`（12 passed）+ `backend/scripts/tagger_eval.py`
> （手动 dev 脚本，不进 CI，支持 `--audio`/`--voice` 多音色 A/B）。真机用真实 Gemini 调用发现：
> 退化模式"时好时坏"，同一 fixture 连续跑结果不稳定，**后续任何改动验证都需要 `--repeats N`
> 统计而非单跑判断**——这是 P1（标签器结构改造）开工前的必要前置，本轮未做。用户确认"找不出
> 比 Gemini 更合适的模型"，故 P2（换模型）降级为"有了统计基线后顺手加一列对比"，非独立任务。
> 顺带完成的 Fish Audio 音色盲听 A/B 定稿见下方新增小节。详见 HANDOFF。
>
> **2026-06-21（第三十六轮）— Fish Audio 音色盲听 A/B 定稿**：用约 20 个候选 `reference_id`
> 跑了盲听（复用 `tagger_eval.py --voice` 多音色对比能力）。**主选**：`fbe02f83…`（嘉岚）/
> `ef5c98bd…`（慵懒偏低音）/ `7f92f8af…`（AD）。**备选**：`5671e9d4…`（偏福建声）/
> `6d3b9742…`（故事声）/ `ae083c60…`（动漫）/ `ba8677df…`（夜晚）/ `c7e86b26…`（凯尔希）。
> 淘汰：`4ca68a29…`（不顺耳）。完整 id 见长期记忆 `fish-audio-preferred-voices` 或 HANDOFF。
>
> **2026-06-22（第三十七轮）— P10-P1 已完成 + TTS config 已落地**：`tagger_eval.py` 加
> `--repeats N`（与 `--audio` 互斥），跑出 N=25 正式统计基线——4 个 fixture 退化率仅
> 4%–12%，`opening_only` 几乎不发生。**结论：当前基线不支持标签器结构改造**，暂缓，除非真机
> 听感继续频繁踩到退化。**`config/tts.json` 的 `fish_audio.voice` 已设为「慵懒偏低音」
> `ef5c98bdc88845b7a4a4c7382179e5ea`**（用户表态非终态，会经常换着听）。新增两个候选盲听：
> 「夜晚02」`b6681a5267b54110a7d0202f4f359313` 入备选，`be404a1ef6704fdb86d02ea05ad0bcc2` 淘汰。
> **⚠️ 未解决矛盾**：04（揶揄+心软）场景上一轮被真机盲听确认"心软那句经常欠标"，但这次 N=25
> 统计上反而是 4 个场景里最干净的（退化率 4%，密度最高）。可能是样本仍小、或真机完整上下文
> 比孤立 fixture 更复杂、或 Gemini 近期确实更稳定——未深究，下次真机再撞到时直接记录完整
> 输入，不要只信这份基线。详见 HANDOFF「本轮已完成」。

## P9 ·（待重新设计）主动找你 / 空闲行为
> **触发**（2026-06-21）：`backend/app/behavior/engine.py:288` 的 `_evaluate_idle_tick` 在
> `boredom>=0.55` 或 `loneliness>=0.55` 时，每隔 180 秒（`tick_policy.py` 冷却时间）触发一次
> `decision="mutter"`，固定吐出 [local_responses.py:13](backend/app/behavior/local_responses.py:13)
> 硬编码的同一句"嗯。你到底要不要说正事。"——本轮发现这条线整整攒了 200 条完全相同的
> `behavior_tick` 消息（跨度约22小时，是这次会话全程 mood_state 卡在 boredom=1.0 没被重置导致的），
> 已清空（备份在 `data/backups/`）并把 mood_state/relationship_state 重置成默认值止血。
> **根因不是这次状态卡住，是设计本身**——固定一句话、没有变化、没有"防止单调重复"的机制，
> 跟「活人感工程」讨论里"她有自己的生活"那个方向（见本文件「活人感工程」章节第1点）应该是同一件事，
> 用户决定重新设计这整块（"主动找你"功能），不是这次小修。
> **用户要求**：本轮不做，留给后续单独的任务/讨论。下一次启动时建议先读
> `backend/app/behavior/engine.py`（`_evaluate_idle_tick` + `_evaluate_proactive` 附近）、
> `backend/app/behavior/local_responses.py`、`backend/app/behavior/tick_policy.py`，
> 以及本文件「活人感工程」章节，一起设计而不是单独补丁。
>
> **2026-06-22（第三十八轮）讨论结论 —— P9 设计四原则**（最大化活人感的核心不是"换更多句子"，
> 而是补结构缺陷：零变化/零记忆/零节奏）：
> 1. **空闲活动要留"记忆痕迹"**：idle 时不直接吐话，先在内部生成/挑选轻量"经历事件"写进 memory，
>    之后能被引用/callback——"她有自己的生活"靠**事后能引用**而非当场宣称。盒子设定天然限制编造面。
> 2. **节奏=urge 模型，不是定时器**：把固定 180s 换成会涨会落的"想找你冲动值"（boredom/loneliness
>    + 距上次互动时长 + 时段 + 配额上限防刷屏），到阈值才发、发完衰减。克制比多发更像人。
> 3. **多 intent → 多消息类型**：decision 不止 `mutter`，typed intent（想分享/想你/延续话题/赌气不主动/
>    单纯烦躁）；决策层=代码定 WHEN+WHAT，表达层=LLM 只在高价值时刻生成，低价值用带变化模板。
> 4. **想念有轨迹**：离开越久语气漂移（无聊→想念→赌气→淡漠）+ 反重复记忆（记最近 N 条措辞/话题不重样）。
> - **投递模态**：默认 **text-only**（push 到信笺/chat，不强制 TTS——idle 时突然发声是打扰，且你不在时
>   语音投递不出去需推送）。"发声"是后续旋钮，不在第一刀。⚠️ 待确认：现有 `behavior_tick` 写进 DB 后
>   前端怎么收到 push（轮询/SSE/下次加载）。
> - **联网合并洞见**：联网功能**不挂回复链路**，合并进 P9——做成"想分享"intent 的**素材来源**（idle 时
>   她"刷到"东西→存成她的经历记忆→以分享欲冒出来）。真实网页内容正好是 idle 生活的**非编造素材**。
>   排在 P9 核心做完后插入，不进第一刀（避免 scope 膨胀）。残留约束：搜索 query 的 vendor 暴露 +
>   内容过滤 + "她搜什么"需人格驱动的种子（兴趣/共同话题）。

### P9 拆解（第三十八轮 `/architect` 定稿 + 用户拍板）
> **关键现状发现**：proactive 其实有**两条路径**。`_evaluate_proactive_check`（前端 300s 轮询）**已成熟**——
> 已有 longing Poisson urge 模型 + budget gate（quiet hours/日上限/fire gap/对话后冷却/待回复门）+ 4 类
> typed intent（`pick_proactive_reason`）+ LLM 写开场白（`resolve_proactive_opener`）。坏的是
> `_evaluate_idle_tick`（90s 轮询）的 mutter 分支（已禁用，200 条重复 bug 的源头）。**投递=纯 pull/poll**，
> 前端 `useBehaviorTicks.ts` 驱动，tab 关了就不发；消息持久化进 messages 表 `source="behavior_tick"`
> （retention=200），已是 text-only 无 TTS。
>
> **用户拍板（第三十八轮）**：
> - ✅ **删掉坏的 idle_tick mutter 分支**（P0）。
> - ✅ **语气轨迹做 无聊→想念→赌气，但绝不到「淡漠」**——见长期记忆 `persona-never-cold-always-present`。
>   负向封顶在赌气（强联结），不许建模疏远/冷处理（断联结）。项目初衷=一直陪伴。
> - ✅ **"主动找你"要突破"仅 app 打开且 idle 时"**——最终形态=微信通知式：她按自己时钟发消息→OS 推送→
>   你想回时点开→看到积压消息→接着聊。**但这是投递层 epic（P9-D），排在灵魂层 P0/P1/P2 之后**
>   （推送会放大内容质量，必须先让她说得好/不重样/有自己的生活，再上推送）。
> - ✅ 认同 **一个 session 一个任务，P0 先行**。
>
> **执行顺序（灵魂层先，投递层后）**：
> - ~~**P9-P0**（small，先做）~~ ✅ **已完成（2026-06-22，第三十九轮）**：实际改动比设想更小——
>   `_evaluate_idle_tick` 本就只有一个非 observe 分支（mutter，已被 `_IDLE_MUTTER_ENABLED=False`
>   短路），删掉该死分支即可，其余 3 条路径原本就恒 `decision="observe"`。**`local_responses.py`
>   未删**——mutter 文案被 user_message 低价值输入路径复用，删了会破坏正常对话反馈，与原设想不同。
>   Scope 实际：`engine.py`（删 `_IDLE_MUTTER_ENABLED` + 死分支）+ `test_behavior.py`/`test_memory.py`
>   （更新过期注释）。**不动** `_evaluate_proactive_check`/`longing.py`/`proactive_reason.py`/`tone.py`/
>   kernel 写入/前端/记忆 schema（验证零行变化）。验收：①idle_tick 任何 mood 下不再产持久化
>   behavior_tick ✅；②proactive_check 行为不变测试全绿 ✅；③全后端 pytest 绿（512 passed）✅。
>   已 commit `e41db56`（第三十九轮 HANDOFF「本轮未 commit」是过期描述，第四十轮已纠正）。
> - ~~**P9-P1**（small–medium）~~ ✅ **已完成（2026-06-22，第四十轮）**：反重复（`mood_state.metadata`
>   存最近 K=4 条 `(kind,tier)` 指纹避重，commit `8f4ba8e`）+ 想念轨迹（`compute_longing_tier()`
>   独立纯函数读墙钟 silence_hours，无聊→想念→赌气，赌气需 closeness≥0.6，**无淡漠**，正交于
>   intent 上色全部 4 类 ProactiveReason，commit `aca291d`）。535 pytest 全绿。**真机验证未做**，
>   下一步建议先验证再启动 P9-P2。详见 HANDOFF。
> - **P9-P2**（medium，**真正动手再拆 P2-A/B/C**）：原则1「她有自己的生活」——idle_tick 低频生成"盒子里
>   的念头/经历"写入记忆（不说话）+ 新增 `share` intent 取用之。⚠️ 可能新增 `idle_experience` memory type
>   →撞 CLAUDE.md「改 schema 须更新 `docs/MEMORY_DESIGN.md`」，启动前先决策复用 vs 新增。**联网素材源
>   = P2-C 可插拔 adapter**（合并洞见：她 idle 刷到的东西经 share intent 冒出来），不进 P2 第一刀。
> - **P9-D（投递层 epic，灵魂层之后）**：D1 server 端 scheduler（后端自己的时钟，脱离前端 tab）→
>   D2 持久消息线 + 内联回复 UX（messages 表已半成品）→ D3 推送（Web Push 可行；iOS PWA 弱，见
>   「移动迁移」节，可能需薄原生壳）。这是"突破 poll-only"+微信通知式的实现载体。

## P11 ·（轻量玩法，可穿插）回复永远用特定语言（如日语 / 英语）
> **2026-06-22（第三十八轮）新增**。三个小玩法里唯一"真·小"的一个（不沾人设/不沾隐私）。
- **Scope**：加一个开关，让 Boxi 无论你说什么，回复（文字 + 语音）都用指定语言（日 / 英 / …）。
- **可行性**：基本是 prompt 指令（输出语言）+ 选一个该语言的 Fish 音色。LLM 原生处理生成/翻译；
  情绪标签是英文方括号、**语言无关**，标签器照常工作。
- **唯一坑**：音色——现有主选音色全是中文音色，Fish 各语言质量分层不同（见 `docs/FISH_AUDIO_REFERENCE.md`），
  日/英要另挑该语言听感好的 `reference_id` 做盲听。
- **验收**：开关打开后，中文输入也得到目标语言的文字 + 该语言听感 OK 的语音；关掉恢复中文。
- **要读**：`config/tts.json`、persona 注入相关（`context_builder.py` / `companion_brain.py` 的语言/语气指令）、
  `docs/FISH_AUDIO_REFERENCE.md`（语言质量分层）。

## 后续讨论名单（未拆解，仅记录方向，待用户发起详细讨论）
- **Obsidian / 电脑链接（让 Boxi 更了解我）**：⚠️ 撞 CLAUDE.md「不加宽泛文件系统访问」限制。
  正确方向是**收窄**——只读、单个指定 vault 路径、**单向 ingest** 进现有 memory/retrieval（不是实时任意 FS）。
  真正成本不在代码，在**隐私**（大量个人笔记进 prompt/embedding = 大面积 vendor 暴露）+ 同步/索引/staleness
  维护（中高）。**不是小玩法**，要做先把 scope 钉死。下次专门讨论实现可能性 + 具体功能方向。
- **mood.boredom/loneliness 墙钟化**（2026-06-22 第四十轮讨论中提出）：现状两者按 idle tick 数累积
  （`mood.py` `apply_idle_tick_mood_delta`），与现实时间脱钩、tab 关了不涨；而 `longing.py` 的
  `silence_hours` 已经是按真实时钟算的，**系统里存在双轨**。用户直觉"现实连续 N 天没找才开始攒孤独/
  无聊"是对的，但 `mood.boredom/loneliness` 同时喂 `tone.py`（决定实时对话语气），重写会牵动对话路径，
  blast radius 远超 P9-P1。**P9-P1 已绕开此问题**——想念轨迹三档直接读 `longing.py` 的墙钟 `silence_hours`，
  不碰 mood 本身。此项是**更彻底的重构**：让 mood.boredom/loneliness 本身也按真实时间分阶段累积，
  让"活人感"延伸到实时对话语气而不只是 proactive 开场白。要做先评估对 `tone.py`/`engine.py` 的影响面。



## 暂缓（不要碰）
- UI / 视觉材质（用户未定画面；低 GPU 否决实时 shader）。
- `experiments/`（废弃 spike）。
- 人设大改（往「复杂+暧昧」走是**项目成熟后**才做，见记忆 `persona-direction-complex-intimate`）。
