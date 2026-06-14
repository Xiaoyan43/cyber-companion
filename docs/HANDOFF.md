# HANDOFF — 上下文交接（2026-06-15）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。当前阶段 = **让语音有真实的情绪层次 + 让长期记忆更贴人设**
（语音情绪/记忆改造，见 `docs/VOICE_EMOTION_MEMORY_PLAN.md`）。UI/视觉**暂缓**（用户未定画面；低 GPU 已否决实时 shader）。

## 本轮已完成（VE-1 收尾 ②，本 session）
- `backend/app/main.py`：`tts_stream`（`/tts/stream`）现在与 `tts_synthesize`（`/tts/synthesize`）一样，
  在 doubao provider 且非中性内核时计算 `context_texts`/`speech_rate` 并传入 `SynthesisRequest`
  （之前 `/tts/stream` 完全不接情绪 directive，R5 已解决）。
- `backend/tests/test_tts.py`：新增 `test_tts_stream_neutral_kernel_omits_emotion_on_doubao`，
  对齐已有的 `test_tts_synthesize_neutral_kernel_omits_emotion_on_doubao`，验证中性态下 `/tts/stream`
  仍 `context_texts=None, speech_rate=0`（向后兼容）。
- 验证：`PYTHON_BIN=.venv/bin/python npm run check` → **412 backend passed** + 前端 tsc 绿。
- **未做（已知缺口，非阻塞）**：非中性内核下 `/tts/stream` + `/tts/synthesize` 的情绪 directive
  集成测试都缺失（不是本轮新引入的问题，本轮只对齐到「中性态向后兼容」级别，未扩大 scope）。

> 上上一轮（工作流改造：CLAUDE.md 总工程师模式 + `/architect` `/review-diff` `/handoff` `/resume-lite`
> 四个本地 slash command，`.claude/` 被 gitignore，见 R6）已折叠，详情见 `git log` / 本文件历史版本。
> 再上一轮产品开发（commits 961da74 → 6c52ab4，VE-1/VM-6 等）同样已折叠进下方「当前未完成」「已知风险」。

## 已修改文件 + 改动摘要（本轮）
- `backend/app/main.py` — `tts_stream` 增加情绪 directive 计算块（resolve provider →
  mood/relationship → `project_tone`/`register_intensity`/`tts_emotion_directive`），
  传入 `SynthesisRequest.context_texts`/`speech_rate`。
- `backend/tests/test_tts.py` — 新增 `test_tts_stream_neutral_kernel_omits_emotion_on_doubao`。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — 本次交接更新。

**测试结果**：`PYTHON_BIN=.venv/bin/python npm run check` → 412 backend passed（原 411 + 1 新）+
前端 tsc 绿。

## 当前未完成（产品侧）
- **VM-6（进行中）**：代码半完成；**待用户**在火山 console 建 `boxi_event`/`boxi_profile` schema +
  权重/衰减 + 设 env，再验证召回。步骤见 `docs/TODO.md` VM-6 条 + `docs/VM6_SPEC.md`。
- **VE-2（BLOCKED：需用户设备 A/B）**：纯 E2E `SetTTSContext`/`TTSConfig.Context` 是否生效（R1/U1），
  待**用户设备 A/B**。P1-B（代码清理）依赖 P1-A 结论，暂不可推进。
- **VE-1 收尾**：① 真机听感确认（待用户）。② `/tts/stream` 接情绪 directive **已完成（本轮）**。
  ③ 非中性内核集成测试仍缺（`/tts/synthesize` 与 `/tts/stream` 都缺）——**建议作为下一个独立 small
  task，不要混入其它任务**。
- **VE-3**：IgnoreBracketText→avatar，需补文档 `6348/2386107`。
- 其它：O2.0 persona 收尾、`get_context` 迁移评估、延迟旋钮（均可选）。

## 已知 bug / 风险
- **R1（最重要）**：纯端到端(OutputMode 0) 平台**忽略 TTSConfig** → 我们 `voice_chat.py`/`routes.py`
  给 pure 体的 `TTSConfig.Context` + `SetTTSContext`（PS-6）**很可能 no-op**。未确认 → VE-2 解决。
  **别在此基础上加东西。**
- **R2**：`6c52ab4`（VM-6 代码）**未 push**（本地 ahead of origin by 2 commits：259cf59 + 6c52ab4）。
  本轮新增 commit 会进一步增加未 push 数量，待用户决定何时 push。
- **R3**：VM-6 自定义 `boxi_profile` 的检索响应 JSON 结构**未实测**；当前解析是容错/通用拼接，
  待首条真实响应再细化字段格式化。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike，低 GPU 已否决实时 shader）——**不要继续开发它**。
- ~~**R5**：VE-1 情绪只接 `/tts/synthesize`，`/tts/stream` 未接（不一致，已知）。~~
  **已解决（本轮）**：`/tts/stream` 已接同一情绪 directive 逻辑。
- **R6**：`.claude/commands/*.md`（本地 slash command）被 `.gitignore` 的 `.claude/` 规则忽略，
  不会进入仓库历史。若想让这套工作流对其他协作者/设备可见，需要在 `.gitignore` 中为
  `.claude/commands/` 开白名单——**待用户决定，本轮未动 `.gitignore`**。
- **R7（新）**：非中性内核下 `/tts/synthesize` + `/tts/stream` 的情绪 directive 集成测试缺失
  （测试覆盖缺口，非代码阻塞）。建议下一个独立 small task 补上。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 做 **R7（非中性内核 TTS 情绪集成测试）**：`backend/app/main.py`（`tts_synthesize`/`tts_stream`）、
  `backend/tests/test_tts.py`、`backend/app/behavior/tone.py`（`tts_emotion_directive` 签名）。
- 做 **VM-6 收尾**：`docs/VM6_SPEC.md`、`backend/app/rtc/viking_memory.py`、
  `backend/app/rtc/config.py`、`backend/app/rtc/voice_chat.py`。
- 做 **VE-2**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`、`backend/app/rtc/voice_chat.py`、
  `backend/app/rtc/routes.py`、`backend/app/rtc/state_block.py`。
- 需要厂商 API 细节时：`reference/SYNTHESIS.md`（已是全量精读结论），再按需点开 `reference/NN.md`。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（3900+ 行历史，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；只在确需某接口字段时点开单篇）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块（如 `files/`、`stt/`、`providers/` 除非任务相关）。
- ❌ 旧的 V2_*/SD*/PS* spec（除非明确回到那条线）。

## 推荐下一个最小任务
**R7：补非中性内核下 `/tts/synthesize` + `/tts/stream` 的情绪 directive 集成测试**
（纯代码+测试，不依赖设备/console/听感，small diff，与本轮改动同模块）。

若用户更想推进产品验证：**VM-6 收尾**（待火山 console）或 **VE-2 设备 A/B**（待真机），均为
BLOCKED/待用户操作项。
