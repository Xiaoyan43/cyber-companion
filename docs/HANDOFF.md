# HANDOFF — 上下文交接（2026-06-22，第三十九轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P9（主动找你 / 空闲行为重新设计）灵魂层第一步 P9-P0 已完成。**
下一步 = **P9-P1**（反重复 + 想念轨迹分档）。

## 本轮已完成（2026-06-22，第三十九轮）：P9-P0 idle_tick 死分支删除（未 commit）

### 实施内容
`/architect` 拆解时读代码发现：HANDOFF 第三十八轮的设想（"idle_tick 退为纯内在状态演化"）描述的
改动范围比实际需要的更大——`_evaluate_idle_tick` 本来就只有一个会输出非 observe 的分支（mutter,
已被 `_IDLE_MUTTER_ENABLED=False` 短路），其余 3 条路径（cooldown / 低能量 / 默认）从一开始就只
返回 `decision="observe"`。**实际改动 = 删掉那一个死分支，其余完全不用动**：

- [engine.py](backend/app/behavior/engine.py)：删除 `_IDLE_MUTTER_ENABLED` 常量+说明注释，删除
  `if _IDLE_MUTTER_ENABLED and (...)` 整个分支（净删 19 行）。`_evaluate_idle_tick` 现在只剩
  3 条路径（cooldown / 低能量 sleepy / 默认 idle），**全部恒为 `decision="observe"`**，不再可能
  产生持久化 `behavior_tick` 消息。开口能力完全收口到 `_evaluate_proactive_check`。
- [test_behavior.py](backend/tests/test_behavior.py)、[test_memory.py](backend/tests/test_memory.py)：
  更新两处引用 `_IDLE_MUTTER_ENABLED` 的过期注释（断言本身原本就是 `observe`/无持久化，未改逻辑）。

### 关键修正（与第三十八轮设想不同的地方）
- **`local_responses.py` 的 mutter 文案分支不能删**——读代码确认 `decision="mutter"` 不是
  idle_tick 专属，`_evaluate_user_message` 的 low_value 输入分支（`annoyance < 0.55` 时）也会
  返回 `decision="mutter"` 并复用同一句 `local_response_for_decision("mutter")`。**本轮未动
  `local_responses.py`**，避免破坏正常对话的"敷衍输入"反馈。
- `chat_persistence.py` 的 `_LOCAL_LINE_DECISIONS = {"mutter", "proactive"}` 决定哪些 decision
  会落成持久化消息——idle_tick 不再返回 `"mutter"` 后自动不会命中这个判断，**不需要改
  `main.py` / `chat_persistence.py`**，是结构上自动达成的，不是单独的改动点。

### 验证结果
- `grep _IDLE_MUTTER_ENABLED backend/` → 无结果，确认死代码清干净。
- `pytest backend/` → **512 passed**（含 `test_behavior.py`、`test_memory.py`）。
- `_evaluate_proactive_check` 全函数 0 行变化（未碰）。

### 本轮未 commit
- 改动文件：`backend/app/behavior/engine.py`、`backend/tests/test_behavior.py`、
  `backend/tests/test_memory.py`。等用户确认后统一提交。

## 当前未完成
- **P9-P1**（下一步，见下方「推荐下一个最小任务」）。
- **P9-P2 / P9-D**（投递层 epic，排在灵魂层 P0/P1/P2 之后）。
- **P11**（回复语言切换玩法，轻量，可穿插）。
- 沿用上一轮未解决事项（见下「已知 bug / 风险」）。

## 已知 bug / 风险
- 「主动找你」当前仍是 poll-only（`useBehaviorTicks.ts` 驱动，tab 关了不发）——P9-D 才解决（需
  server scheduler + 推送），本轮未触碰。
- 沿用既有风险：`（动作描述）`偶发、cost 模块不认 openrouter 模型、R8
  （`VIKING_MEMORY_API_KEY` 建议轮换）、R4（`experiments/`废弃）、标签器质量「时好时坏」需
  `--repeats N` 统计判断（非单跑）、04（揶揄+心软）场景统计基线与真机听感矛盾未深究
  （详见 `docs/TASK_QUEUE.md` P10 节）。
- **无新增风险**——本轮是纯删除死分支，不引入新行为。

## 推荐下一个最小任务：P9-P1（反重复 + 想念轨迹分档）
- **目标**：①反重复——`mood_state.metadata` 存最近 K 条 proactive 措辞指纹，避免连续几次开场白
  重样；②想念轨迹——`longing.intensity` 分档（无聊→想念→赌气，**绝不淡漠**，见长期记忆
  `persona-never-cold-always-present`），作为 `ProactiveReason` 字段下发 prompt。
- **Scope**：`backend/app/behavior/proactive_reason.py` + `backend/app/behavior/longing.py`/可能
  新建小模块 + `mood_state.metadata`（复用现有字段，不动 schema）+ 对应单测。
- **不动**：`_evaluate_idle_tick`（本轮刚改完）、`tone.py`、kernel 写入路径、前端、记忆 schema。

## 下一步只需读取（P9-P1）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（P9 拆解节）
- **P9-P1 代码**：`backend/app/behavior/proactive_reason.py`、`backend/app/behavior/longing.py`、
  `backend/app/behavior/mood.py`（metadata 结构）、对应单测
- 长期记忆 `persona-never-cold-always-present`（想念轨迹分档的硬约束来源，强相关）

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与 P9-P1 无关的模块（TTS/标签器/RTC/前端 UI/idle_tick 本身都不碰）
- ❌ 不要重新讨论 idle_tick mutter 删除是否够——已验证 512 pytest 绿，不需要回头复查 P9-P0

## 沿用的既有未完成项（本轮未碰）
- **P9-P2 / P9-D**（见 `docs/TASK_QUEUE.md` P9 拆解节）
- **P11**（回复语言切换，轻量玩法）；**Obsidian 链接**（后续讨论名单）
- **情绪识别旁路**（Hume prosody 当传感器，第二档，先 spike）
- **TTS 音色**已落地为「慵懒偏低音」`ef5c98bd…`（用户表态会经常换，换时同步 `config/tts.json` +
  记忆 `fish-audio-preferred-voices`）
- P8-C 语音 Pipecat 两阶段路径、RTC character_manifest 同步、信笺 UI P2、R11（搁置）、world brain 天气 API

---

> 建议执行 `/clear` 或新开 session。下一 session 实施 **P9-P1**，只需读取 `docs/HANDOFF.md`、
> `docs/TASK_QUEUE.md`（P9 拆解节）、上面列的 behavior 文件 + 对应单测。
