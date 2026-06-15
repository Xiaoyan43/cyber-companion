# HANDOFF — 上下文交接（2026-06-15）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。当前阶段 = **让语音有真实的情绪层次 + 让长期记忆更贴人设**
（语音情绪/记忆改造，见 `docs/VOICE_EMOTION_MEMORY_PLAN.md`）。UI/视觉**暂缓**（用户未定画面；低 GPU 已否决实时 shader）。

## 本轮已完成（R10 修复，本 session）
- **R10 根因确认 + 修复**：用户反馈"每次打开 Boxi 语音都感觉她很冲/烦躁"——
  - 排查过程：先查当前 `mood_state`，annoyance=0.0（正常，非 R9 残留）。再查 `relationship_state`，
    发现 `tension=0.421`。
  - 根因：[tone.py](backend/app/behavior/tone.py) 的 `_TENSION_SHARP=0.4` 与
    [state_block.py](backend/app/rtc/state_block.py) 的 `_TENSION_AWKWARD_THRESHOLD=0.4` 数值相同但是
    两个独立常量。tension≈0.42（"有点别扭"级别的常见关系状态）一旦 ≥0.4 就被 `_is_real_sharp()`
    判为 `real_sharp` → RTC join-time 的 `speaking_style` 被加上"；现在更冲、更短"。tension 本身有
    `*0.9`/turn 的衰减路径（非单向卡死，与 R9 不同），但 RTC join-time 读取的是上一次会话结束时的
    残留快照，停在 0.4 附近时每次新连接都会误判。
  - **修复**（[tone.py:31](backend/app/behavior/tone.py:31)）：`_TENSION_SHARP` 0.4 → 0.55。
    `state_block.py` 的 `_TENSION_AWKWARD_THRESHOLD=0.4`（"、有点别扭"文案）不动。
  - **测试改动**：[test_tone.py](backend/tests/test_tone.py) `test_tension_alone_triggers_real_sharp`
    改用 `tension=0.6`；新增 `test_mild_tension_does_not_trigger_real_sharp`（tension=0.42）。
    [test_rtc_state_block.py](backend/tests/test_rtc_state_block.py) 两处 `tension=0.5`→`0.6`。
  - **测试结果**：`pytest backend/tests/test_tone.py backend/tests/test_rtc_state_block.py` 52 passed；
    `pytest backend/tests/ -k "mood or engine or behavior or tone or rtc"` 138 passed。
  - **真机验证**：✅ 用户确认"不冲了"。

> 上一轮（R9 mood 面板修复；VE-2 设备 A/B inconclusive；VM-6 收尾）已折叠，详情见 `git log` / 本文件历史版本。

## 已修改文件 + 改动摘要（本轮）
- `backend/app/behavior/tone.py` — `_TENSION_SHARP` 0.4→0.55（1 行）。
- `backend/tests/test_tone.py` — 改 1 处测试值 + 新增 1 条回归测试。
- `backend/tests/test_rtc_state_block.py` — 改 2 处测试值（0.5→0.6）。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — R10 标记已完成，新增 R11。

**测试结果**：见上。未运行 `npm run check`（仅后端纯函数+测试改动，前端 tsc 不受影响）。

## 真机验证结果（用户反馈，本 session 末）
- ✅ R10 修复有效：语音连接不再"冲"。
- ⚠️ **新发现（R11，未排查）**：用户反馈"纯 E2E 语音对话中，Boxi 对部分长期记忆记不起来"——
  即 Viking 长期记忆库（VM 系列）部分内容检索/注入失效。**本 session 未排查**，记入 TASK_QUEUE R11。
  待确认细节：忘的是"很久以前的事"还是"最近一次会话的事"？是没存进去还是存了读不出来？

## 当前未完成（产品侧）
- **R10**：✅ **已完成并真机验证 PASS**（本轮）。语音连接不再"更冲"。
- **R11（新，未排查，建议优先）**：纯 E2E 长期记忆部分失忆——疑似 Viking 记忆写入/检索/注入链路问题，
  可能与 `ARCHITECTURE_SNAPSHOT.md` 的 **U3**（VM-6 自定义 `boxi_profile` 检索响应结构未实测）相关。
  建议下一 session 先向用户追问细节，再 `/architect` 拆解。
- **VE-1 收尾**：① 真机听感确认（待用户，未做）。R10 已修复，烦躁基线干扰已排除，可独立进行。
- **VE-3**：IgnoreBracketText→avatar，需补文档 `6348/2386107`（未变）。
- 其它：O2.0 persona 收尾、`get_context` 迁移评估、延迟旋钮、API Key 轮换（R8，安全卫生，均可选，未变）。

## 已知 bug / 风险
- **R10**：✅ **已修复并真机验证 PASS（本轮）**——`_TENSION_SHARP` 阈值过低（0.4）导致常见的轻微
  tension（≈0.42）误判为 real_sharp。已调至 0.55。
- **R11（新，未排查）**：纯 E2E 语音中 Boxi 对部分长期记忆记不起来，疑似 Viking 记忆检索/注入问题，
  与 U3（VM-6 自定义 schema 响应结构未实测）可能相关。
- **R2**：`6c52ab4`（VM-6 代码）仍**未 push**（本地 ahead of origin，本轮无新代码 commit）。
- **R8（低优先级，未处理）**：上一轮 `.env` 中 `VIKING_MEMORY_API_KEY` 明文被截图分享过，建议用户在
  火山 console 重新生成 key（授权 `friend`+`friend02`）并替换、作废旧 key。不阻塞功能。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike，低 GPU 已否决实时 shader）——**不要继续开发它**。

## 下一步只需读取（按任务，**只读这些**）
- 永远先读：本文件 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- 若做 **R11（纯 E2E 长期记忆部分失忆排查）**：先向用户追问细节（忘的是什么类型/写入侧还是检索侧），
  再读 `backend/app/rtc/viking_memory.py`（VM 系列）、`backend/app/rtc/routes.py`（`/rtc/memory/session`
  写入 `AddSession` 处）、`backend/app/rtc/voice_chat.py`（`MemoryConfig`/检索注入处）。
- 若做 **VE-1①真机听感**：用户真机听感+看心情面板，无需读代码（除非发现新问题）。
- 需要厂商 API 细节时：`reference/SYNTHESIS.md`（已是全量精读结论），再按需点开 `reference/NN.md`，
  尤其 VM-6 相关的 `boxi_profile` schema 部分。

## 下一步**不要**读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（3900+ 行历史，本文件已概括）。
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替；只在确需某接口字段时点开单篇）。
- ❌ `experiments/`（废弃 spike）。
- ❌ 全仓库扫描 / 与当前任务无关的模块（如 `files/`、`stt/`、`providers/` 除非任务相关）。
- ❌ 旧的 V2_*/SD*/PS* spec（除非明确回到那条线）。

## 推荐下一个最小任务
**R11：排查"纯 E2E 长期记忆部分失忆"**——先向用户追问细节（忘的类型/写入侧 vs 检索侧），
再 `/architect` 拆解，预计涉及 `backend/app/rtc/viking_memory.py` + VM-6 自定义 schema（U3）。
其次：**VE-1①真机听感**（R10 已修复，可独立进行）。
