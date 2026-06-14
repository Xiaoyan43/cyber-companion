# TASK_QUEUE — 按优先级（2026-06-15）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> P0/P1 均 BLOCKED（待用户火山 console / 设备 A/B）。**当前可独立推进的最小任务 = P0' · R7**（见下）。

> 本轮（VE-1 收尾 ②）完成：`/tts/stream` 接入与 `/tts/synthesize` 同源的情绪 directive；新增中性态对齐测试；
> `npm run check` 412 backend passed。详情见 HANDOFF。

---

## P0' · R7 — 非中性内核 TTS 情绪 directive 集成测试（新，可独立推进）
- **Scope**：为 `/tts/synthesize` 和 `/tts/stream` 各补一条「非中性内核 → payload 带 `context_texts`/`speech_rate`」的集成测试（与已有的中性态对齐测试成对）。
- **验收**：新测试绿；`npm run check` 全绿；HANDOFF R7 标记已解决。
- **要读**：`backend/app/main.py`、`backend/tests/test_tts.py`、`backend/app/behavior/tone.py`（`tts_emotion_directive`/`project_tone`/`register_intensity` 签名）。
- **不动**：`backend/app/rtc/*`、`backend/realtime/*`、VM-6/VE-2 相关代码。
- **依赖**：无（不需设备/console/听感）。

## P0 · VM-6 收尾（代码已就绪，剩用户侧 + 验证）—— BLOCKED：待火山 console
- **Scope**：用户在火山 console/API 建 `boxi_event`/`boxi_profile` schema + 权重(`importance` 表达式)/分数融合/14 天无衰减 + IAM 授权；改 `.env`（`VIKING_MEMORY_COLLECTION`、`VIKING_MEMORY_TYPES=boxi_profile,boxi_event`）。代码侧**已完成**，不要再改。
- **验收**：`GET /rtc/status` → `viking_memory_enabled: true`；跨会话召回（昵称/城市/求职进度/承诺 各 1 条）实机 PASS；env 改回内置即回退。
- **要读**：`docs/VM6_SPEC.md`、`docs/TODO.md`(VM-6 条)、`backend/app/rtc/viking_memory.py`、`backend/app/rtc/config.py`。
- **不动**：SQLite / soul kernel / behavior 契约。

## P1 · VE-2 纯 E2E 情绪通道核实（解决 R1）—— **BLOCKED：需用户设备 A/B 结论**
- **P1-A（BLOCKED）**：用户做设备 A/B——确认 `SetTTSContext`/`TTSConfig.Context` 在 OutputMode 0 是否真生效。结论写入 HANDOFF 的 U1/R1。**等用户有空做真机听感测试后再继续。**
- **P1-B（BLOCKED，依赖 P1-A）**：若 P1-A 结论为 no-op，从 `voice_chat.py:172-178` 移除 pure 体的 `TTSConfig.Context` + `routes.py:65-87` 停发 `SetTTSContext`，情绪收口到 `speaking_style`。**仅核实 + 删冗余，不加功能。**
- **验收**：结论写入 HANDOFF/TODO；若 no-op，pure 体不再发无效字段，RTC 测试仍绿。
- **要读**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`(§2)、`backend/app/rtc/voice_chat.py`、`backend/app/rtc/routes.py`、`backend/app/rtc/state_block.py`；需依据时 `reference/12.md`。

## P2 · VE-1 收尾
- **Scope**：① 真机听一条 comfort/real_sharp/playful，确认情绪有层次不夸张（`emotion_scale` 没用，靠措辞+`speech_rate`）。② ~~给 `/tts/stream` 也接同一情绪 directive（与 `/tts/synthesize` 对齐）~~ **已完成**，见 HANDOFF。③ ~~补一条路由级「非中性内核→payload 带情绪」集成测试~~ **部分完成**（已补中性态对齐测试；非中性态集成测试仍缺）。
- **验收**：听感 OK（待用户真机，blocked）；`/tts/stream` 与 `/tts/synthesize` 情绪一致（代码侧已对齐）；新测试绿；`npm run check` 绿。
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
