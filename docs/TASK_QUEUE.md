# TASK_QUEUE — 按优先级（2026-06-17）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> P0（VM-6）/ P1（VE-2）/ R9 / R10 / P2（VE-1）/ R12（反编造）/ 信笺 UI P0 + P1 + P1-B 均已完成。
> 当前优先候选 = **信笺 UI · P1-C**（真实 Boxi 消息驱动打字机），其次 **P5-A**（Venice AI，随时可开始），
> 再次 **P5-B**（Fish Audio，等用户提供文档），最后 **R11**（等 VikingDB 访问）。

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
- **P1-C · 真实 Boxi 消息驱动打字机（P1-B 之后）**：
  - 把最新一条 Boxi 回复文本传给 `LetterView`，驱动打字机替代 demo scripts。
  - 需给 `useTypewriter.ts` 加受控文本 prop；`LetterView` 加 `text?: string` prop。
  - 要读：`useTypewriter.ts` + `LetterView.tsx` + `App.tsx`（messages state）。
  - 验收：letter 模式下能看到 Boxi 最新回复以打字机节奏呈现。
  - 预计 diff：small-medium。
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

## P5 · Provider 替换（已计划，待排期）

### P5-A · LLM → Venice AI
- **Scope**：`backend/app/providers/` 新增 `venice.py`（OpenAI-compatible），`config/providers.json` 加 venice entry，env 加 `VENICE_API_KEY`。
- **可行性**：Venice AI 使用 OpenAI-compatible API（`/v1/chat/completions`），项目已有 provider 抽象层，DeepSeek 也走同一套接口——预计改动极小（~1 文件 + 配置）。
- **注意**：Venice AI 是隐私/无审查平台，需评估模型选型对 Boxi 人设一致性的影响（Llama/Mistral 系列 vs DeepSeek-chat）。
- **阻塞**：无；可随时开始。

### P5-B · TTS → Fish Audio
- **Scope**：`backend/app/tts/` 新增 `fish_audio.py`，provider registry 注册，env 加 `FISH_AUDIO_API_KEY`。
- **可行性**：TTS 抽象层已存在（`backend/app/tts/base.py` + registry），新增一个 provider 文件即可。
  **核心未知**：Fish Audio 是否支持情绪/语速参数（等价于 Doubao bigtts 的 `context_texts`/`speech_rate`）——需看文档才能判断情绪通道（VE-1）能否保留。
- **阻塞**：需用户提供 Fish Audio API 文档（无法自行搜索）。

## P4 ·（可选）记忆/延迟/persona
- **VM-7**：评估用 `get_context` 替代手动 `SearchMemory`（`reference/06.md`）。Scope=评估+spec，不直接重写。
- **延迟旋钮**：`ThinkingType=disabled`/`Prefill`/`AIVAD`/`SilenceTime` 调优（仅混合编排/模块化路径）。要读 `reference/13.md`、`reference/14.md`。
- **O2.0 persona 收尾**：新 Boxi 音色设备 A/B、`speaking_style` 去规则化、`dialog_id`/`external_rag`。要读 `docs/TODO.md`(O2.0 条)。

## 暂缓（不要碰）
- UI / 视觉材质（用户未定画面；低 GPU 否决实时 shader）。
- `experiments/`（废弃 spike）。
- 人设大改（往「复杂+暧昧」走是**项目成熟后**才做，见记忆 `persona-direction-complex-intimate`）。
