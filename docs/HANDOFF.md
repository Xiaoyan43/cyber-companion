# HANDOFF — 上下文交接（2026-06-15）

> 本文件每次「瘦身交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。当前阶段 = **让语音有真实的情绪层次 + 让长期记忆更贴人设**
（语音情绪/记忆改造，见 `docs/VOICE_EMOTION_MEMORY_PLAN.md`）。UI/视觉**暂缓**（用户未定画面；低 GPU 已否决实时 shader）。

## 本轮已完成（commits 961da74 → 6c52ab4，除 6c52ab4 外均已 push）
1. **felt-vs-shown 情绪投射 + 逗你**（961da74）：`tone.py` 成统一情绪投射真源；新增 `playful`（desync-2 逗你）+ 正向连击点亮；RTC/文字/语音一致。
2. **UI 决定记录**（d031506）：光+墨实时 shader 因低 GPU 否决；UI 待用户定画面。
3. **纯 E2E 语音接 felt-shown 连击**（6976f77）：核实语音 turn 经 `analyze_turn→evaluate_behavior` 已推进连击 + 回归测试。
4. **reference/ gitignore**（3ef8aeb）：厂商文档投放区（不公开）。
5. **语音情绪/记忆方案**（2812c4a）：`docs/VOICE_EMOTION_MEMORY_PLAN.md` + TODO 切片（VE-1/VE-2/VM-6/VE-3）。
6. **VE-1 spec + 动态范围**（ec4a7bb, 89dee22）：`docs/VE1_SPEC.md`；情绪强度走 base/intense 动态档。
7. **VE-1 实现**（7f61e6b）：cascaded TTS 情绪（`context_texts`+`speech_rate`，kernel 驱动）+ 后端文本清洗。
8. **省略号修复**（4c611cf）：TTS 清洗保留 `……`。
9. **VM-6 spec**（e6e8175）：`docs/VM6_SPEC.md`（Boxi 自定义 Viking schema）。
10. **VM-6 代码半**（6c52ab4，**未 push**）：`viking_memory.py` 支持内置+自定义类型（默认仍内置，env 激活）。

## 已修改文件 + 改动摘要（本轮累计）
**后端代码：**
- `backend/app/behavior/tone.py` — 新统一投射 `project_tone`（felt/expressed_edge/is_performative/register）+ 连击 + VE-1 `tts_emotion_directive`/`register_intensity` + base/intense 情绪映射（**单一真源**）。
- `backend/app/behavior/types.py` — `ToneMode` 加 `playful`；`BehaviorDecision.tone` 字段。
- `backend/app/behavior/mood.py` — `choose_tone_mode` 改为 `project_tone` 薄壳。
- `backend/app/behavior/engine.py` — 用 `project_tone` + 连击点亮，决策带 `tone`。
- `backend/app/behavior/local_responses.py` — `playful` 口吻指令。
- `backend/app/reflection/turn_analyzer.py` — 注释钉住「语音 turn 推进连击」依赖。
- `backend/app/rtc/state_block.py` — 情绪文案改读 `tone.py` base 档（RTC 钉死串不变）。
- `backend/app/rtc/viking_memory.py` — 类型 kind 映射（内置 `profile_v1/event_v1` + 自定义 `boxi_profile/boxi_event`）+ 扁平画像解析；**默认仍内置**。
- `backend/app/tts/types.py` — `SynthesisRequest` 加 `context_texts`/`speech_rate`。
- `backend/app/tts/doubao.py` — payload 注入 `context_texts`/`speech_rate` + 合成前 `clean_text_for_tts`；空参向后兼容。
- `backend/app/tts/text_cleanup.py`（新）— 去 markdown/emoji/括号舞台提示，**保留省略号**。
- `backend/app/main.py` — `/tts/synthesize` 读内核 → `tts_emotion_directive`，仅 doubao 且配置就绪时注入。

**测试：** `test_tone.py`、`test_behavior.py`、`test_rtc_state_block.py`、`test_turn_analyzer.py`、`test_tts.py`、`test_rtc_viking_memory.py`（均扩展，未删旧断言）。

**文档：** `docs/VOICE_EMOTION_MEMORY_PLAN.md`、`VE1_SPEC.md`、`VM6_SPEC.md`（新）；`docs/TODO.md`、`SESSION_LOG.md`、`PERSONA_AND_BEHAVIOR.md`、`.gitignore`（更新）。

**gate：** `PYTHON_BIN=.venv/bin/python npm run check` → 411 backend passed + tsc 绿（本轮最后状态）。

## 当前未完成
- **VM-6（进行中）**：代码半完成；**待用户**在火山 console 建 `boxi_event`/`boxi_profile` schema + 权重/衰减 + 设 env，再验证召回。步骤见 `docs/TODO.md` VM-6 条 + `docs/VM6_SPEC.md`。
- **VE-2**：纯 E2E `SetTTSContext` 是否生效，待**用户设备 A/B**（大概率 no-op，见风险）。
- **VE-1 收尾**：真机听感确认；`/tts/stream` 未接情绪；路由级「非中性→带情绪」集成测试未补。
- **VE-3**：IgnoreBracketText→avatar，需补文档 `6348/2386107`。
- 其它：O2.0 persona 收尾、`get_context` 迁移评估、延迟旋钮（均可选）。

## 已知 bug / 风险
- **R1（最重要）**：纯端到端(OutputMode 0) 平台**忽略 TTSConfig** → 我们 `voice_chat.py`/`routes.py` 给 pure 体的 `TTSConfig.Context` + `SetTTSContext`（PS-6）**很可能 no-op**。未确认 → VE-2 解决。**别在此基础上加东西。**
- **R2**：`6c52ab4`（VM-6 代码）**未 push**。
- **R3**：VM-6 自定义 `boxi_profile` 的检索响应 JSON 结构**未实测**；当前解析是容错/通用拼接，待首条真实响应再细化字段格式化。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike，低 GPU 已否决实时 shader）——**不要继续开发它**。
- **R5**：VE-1 情绪只接 `/tts/synthesize`，`/tts/stream` 未接（不一致，已知）。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 做 **VM-6 收尾**：`docs/VM6_SPEC.md`、`backend/app/rtc/viking_memory.py`、`backend/app/rtc/config.py`、`backend/app/rtc/voice_chat.py`。
- 做 **VE-2**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`、`backend/app/rtc/voice_chat.py`、`backend/app/rtc/routes.py`、`backend/app/rtc/state_block.py`。
- 做 **VE-1 收尾**：`docs/VE1_SPEC.md`、`backend/app/tts/doubao.py`、`backend/app/main.py`、`backend/app/behavior/tone.py`。
- 需要厂商 API 细节时：`reference/SYNTHESIS.md`（已是全量精读结论），再按需点开 `reference/NN.md`。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（3900+ 行历史，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；只在确需某接口字段时点开单篇）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块（如 `files/`、`stt/`、`providers/` 除非任务相关）。
- ❌ 旧的 V2_*/SD*/PS* spec（除非明确回到那条线）。

## 推荐下一个最小任务
**VM-6 收尾**（代码已就绪，剩用户侧 + 验证）：用户在火山 console 按 `docs/VM6_SPEC.md`/TODO 步骤建好 schema + 设 env → 新 session 只需核对 `/rtc/status` 的 `viking_memory_enabled` 与一次跨会话召回。
若用户暂不便弄 console：退而做 **VE-2 设备 A/B**（确认 R1，决定是否拆 pure 体 TTSConfig，纯核实+小清理）。
