# TASK_QUEUE — 按优先级（2026-06-15）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> P0（VM-6）/ P1（VE-2）/ R9（mood 修复）/ R10（tension 阈值修复）已完成并真机验证 PASS。当前优先候选
> = **R11**（纯 E2E 长期记忆部分失忆，新发现，未排查），其次 P2（VE-1①真机听感）。

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

## R11 ·（新，建议优先）纯 E2E 长期记忆部分失忆
- **Scope**：用户反馈纯 E2E 语音对话中，Boxi 对**部分长期记忆**（之前提过的事）"记不起来"。
  涉及 Viking 长期记忆库的写入/检索/注入链路（`backend/app/rtc/viking_memory.py`、VM-6
  自定义 schema、`AddSession`/检索响应解析）。**先评估，不直接重写**。
- **建议**：下一 session 用 `/architect` 拆解。需先向用户确认：忘的是"很久以前的事"还是"最近一次
  会话里的事"？是完全没存进去，还是存了但检索不到？这决定排查方向是写入侧还是检索侧。
- **关联**：`ARCHITECTURE_SNAPSHOT.md` 的 **U3**（VM-6 自定义 `boxi_profile` 检索响应 JSON 结构
  未实测，解析做了容错）可能相关——如果检索响应结构和容错解析不匹配，会导致"存了但读不出来"。

## P2 · VE-1 收尾
- **Scope**：① 真机听一条 comfort/real_sharp/playful，确认情绪有层次不夸张（`emotion_scale` 没用，靠措辞+`speech_rate`）。② ~~给 `/tts/stream` 也接同一情绪 directive（与 `/tts/synthesize` 对齐）~~ **已完成**，见 HANDOFF。③ ~~补一条路由级「非中性内核→payload 带情绪」集成测试~~ **已完成**，见 HANDOFF。
- **验收**：听感 OK（待用户真机，blocked）；`/tts/stream` 与 `/tts/synthesize` 情绪一致（代码侧已对齐，已测试覆盖）。
- **要读**：`docs/VE1_SPEC.md`、`backend/app/tts/doubao.py`、`backend/app/main.py`、`backend/app/behavior/tone.py`、`backend/tests/test_tts.py`。

## P3 · VE-3 IgnoreBracketText → 前端情绪 cue（later）
- **Scope**：Boxi 把动作/情绪写进括号 → TTS 不读、随字幕下发驱动前端 cue（与最终画面解耦，先做信号层）。
- **阻塞**：需用户先补文档 `6348/2386107（传递自定义指令）`。
- **验收**：括号指令不进语音、能在前端拿到并触发一个 cue。
- **要读**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`、`reference/14.md`（IgnoreBracketText 段）、待补的 2386107。

## P4 ·（可选）记忆/延迟/persona
- **VM-7**：评估用 `get_context` 替代手动 `SearchMemory`（`reference/06.md`）。Scope=评估+spec，不直接重写。
- **延迟旋钮**：`ThinkingType=disabled`/`Prefill`/`AIVAD`/`SilenceTime` 调优（仅混合编排/模块化路径）。要读 `reference/13.md`、`reference/14.md`。
- **O2.0 persona 收尾**：新 Boxi 音色设备 A/B、`speaking_style` 去规则化、`dialog_id`/`external_rag`。要读 `docs/TODO.md`(O2.0 条)。

## 暂缓（不要碰）
- UI / 视觉材质（用户未定画面；低 GPU 否决实时 shader）。
- `experiments/`（废弃 spike）。
- 人设大改（往「复杂+暧昧」走是**项目成熟后**才做，见记忆 `persona-direction-complex-intimate`）。
