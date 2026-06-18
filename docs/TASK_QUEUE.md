# TASK_QUEUE — 按优先级（2026-06-18）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> P0（VM-6）/ P1（VE-2）/ R9 / R10 / P2（VE-1）/ R12（反编造）/ 信笺 UI P0 + P1 + P1-B + P1-C / **P5-A-1** / **P6（全部子任务）** / **P7（Pipecat 前端入口）** 均已完成。
> P5-A（Venice）已取消（溢价太高）。
> **2026-06-18（第十六轮）纯讨论 session**：新增「灵魂层进化（Soul Layer）」节，沉淀六脑/time brain/活人感/审核/记忆消解/移动迁移/画面搁置等方向（均未拆解，要做时先 `/architect`）。
> **2026-06-18（第十七轮）**：time brain P0（注入新西兰时间）+ P1（recent_event 相对时间前缀）完成，commit `16d1b74`，440 pytest passed。
> **当前重心：灵魂层进化。** 推荐下一最小任务 = **world brain · 节日查表**（节日静态表 + `_format_time_block` 追加节日信息，近免费）。
> 其余候选：信笺 UI P2（需用户答问）/ emotion 慢情绪 decay-on-read / R11（搁置，下次失忆当场验）/ P5-B（Fish Audio，需文档）。

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

### P5-B · TTS → Fish Audio
- **Scope**：`backend/app/tts/` 新增 `fish_audio.py`，provider registry 注册，env 加 `FISH_AUDIO_API_KEY`。
- **可行性**：TTS 抽象层已存在（`backend/app/tts/base.py` + registry），新增一个 provider 文件即可。
  **核心未知**：Fish Audio 是否支持情绪/语速参数（等价于 Doubao bigtts 的 `context_texts`/`speech_rate`）——需看文档才能判断情绪通道（VE-1）能否保留。
- **阻塞**：需用户提供 Fish Audio API 文档（无法自行搜索）。

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
- **第一档**（近免费、收益最大）：~~time-现在注入~~ ✅ / **world-节日查表（推荐下一刀）** / emotion-慢情绪+decay-on-read
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

## 暂缓（不要碰）
- UI / 视觉材质（用户未定画面；低 GPU 否决实时 shader）。
- `experiments/`（废弃 spike）。
- 人设大改（往「复杂+暧昧」走是**项目成熟后**才做，见记忆 `persona-direction-complex-intimate`）。
