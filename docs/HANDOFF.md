# HANDOFF — 上下文交接（2026-06-16）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 本轮已完成（VE-1①真机听感 + doubao additions 字段 bug 修复，本 session）
- **VE-1①真机听感**：comfort / real_sharp 两条 register 真机听感 ✅ PASS（"贴合情绪"）。
  playful 因 `relationship.closeness=0.66` 差 0.01 到阈值 0.67（且无写接口，不强行造数据）暂未测，
  标记为「待自然达成 closeness≥0.67 后再测」。
- **新发现并修复阻塞 bug**：[doubao.py:251](backend/app/tts/doubao.py:251) `req_params.additions`
  之前传嵌套 dict `{"context_texts": [...]}`，但 Doubao API 要求 `additions` 是 **JSON 字符串**——
  实际调用报 `cannot unmarshal object into Go struct field TTSReqParams.req_params.additions of type string`，
  此前单测 mock 掉了真实 API 未测出。修复：`req_params["additions"] = json.dumps({...})`（1 行）。
  同步改 [test_tts.py:645](backend/tests/test_tts.py:645) 断言为 `json.loads(req["additions"])[...]`。
- **测试结果**：`pytest backend/tests/test_tts.py` 41 passed。
- **现场操作**：测试期间通过 `PUT /memory/mood` 临时设置 worry/annoyance 触发 comfort/real_sharp，
  测完已恢复为 `mood="neutral", worry=0.0, annoyance=0.0`（energy/boredom/trust/loneliness 全程未动）。

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

> 上一轮（R10 tension 阈值修复；R9 mood 面板修复；VE-2 设备 A/B inconclusive；VM-6 收尾）已折叠，
> 详情见 `git log` / 本文件历史版本。

## 已修改文件 + 改动摘要（本轮）
- `backend/app/tts/doubao.py` — `req_params["additions"]` 改为 `json.dumps(...)`（1 行，阻塞 bug 修复）。
- `backend/tests/test_tts.py` — 同步改 1 处断言为 `json.loads(req["additions"])[...]`。
- `docs/HANDOFF.md` / `docs/TASK_QUEUE.md` — VE-1① 标记已完成（除 playful），记录新 bug 修复。

**测试结果**：`pytest backend/tests/test_tts.py` 41 passed。未运行 `npm run check`
（仅 TTS 模块 + 测试改动，前端 tsc 不受影响）。

## 真机验证结果（用户反馈，本 session）
- ✅ VE-1① comfort / real_sharp 两条 register 听感 PASS（"贴合情绪"）。
- ⏸️ playful 未测（`relationship.closeness=0.66` 差 0.01 到阈值 0.67，无写接口，未强行造数据）。

## 当前未完成（产品侧）
- **R11（未排查，建议优先）**：纯 E2E 长期记忆部分失忆——疑似 Viking 记忆写入/检索/注入链路问题，
  可能与 `ARCHITECTURE_SNAPSHOT.md` 的 **U3**（VM-6 自定义 `boxi_profile` 检索响应结构未实测）相关。
  建议下一 session 先向用户追问细节，再 `/architect` 拆解。
- **VE-1 收尾**：① comfort/real_sharp ✅ PASS（本轮）；playful 待 `closeness≥0.67` 自然达成后补测。
- **VE-3**：IgnoreBracketText→avatar，需补文档 `6348/2386107`（未变）。
- 其它：O2.0 persona 收尾、`get_context` 迁移评估、延迟旋钮、API Key 轮换（R8，安全卫生，均可选，未变）。

## 已知 bug / 风险
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
