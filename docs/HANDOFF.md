# HANDOFF — 上下文交接（2026-06-22，第四十三轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P9-P2-A + P9-P2-B 均已完成并 commit，557 pytest 全绿，working tree 干净。**
下一步候选：**P9-P2-C**（素材源升级真联网）或 **P9-D**（投递层 epic）。

## 本轮已完成（2026-06-22，第四十三轮）

### 1. P9-P2-A · review + commit（commit `be2a81d`）
- 上一轮（第四十二轮）写好但未提交的 idle_experience 机制本轮 review 后直接落 master：
  新 memory type `idle_experience`（不进 `FACTUAL_MEMORY_TYPES`）+ `resolve_idle_experience_write()`
  （镜像 `resolve_proactive_opener` 编排模式，零行改动 `engine.py`）+ 节奏门控（日配额+最小间隔）
  + 白名单素材池防编造。Review 结论 PASS，无 blocking issue。
- 一并提交了第四十二轮遗留的 `docs/P9_P1_VERIFICATION.md`（新建）+ `docs/HANDOFF.md`/`docs/TASK_QUEUE.md`/
  `docs/MEMORY_DESIGN.md` 的相应更新。
- `data/tagger_eval/`、`experiments/*` 仍保持 untracked（暂缓清单范围内，未动）。

### 2. P9-P2-B · share intent 接入 proactive_reason（commit `9890ca4`）
- 用 `/architect` 拆出 P0（决策）+ P1（实施）两步：
  - **P0 决策（用户拍板）**：① share 插在优先级链
    `due_reminder → commitment_followup → share → memory_callback`（排在硬约定之后、记忆回响之前）；
    ② 消费语义走 **FIFO 反重复指纹**（用过的记忆 id 进短期黑名单，过段时间可再被提起），不是一次性
    永久消费。
  - **P1 实施**：
    - [proactive_reason.py](../backend/app/behavior/proactive_reason.py)：`ProactiveReasonKind` 加
      `"share"`；新增 `_pick_share()`（从 `idle_experience` 类型记忆里挑未被指纹覆盖的最新一条）+
      `is_share_repeated()`/`record_share_fingerprint()`（FIFO，仿 `idle_experience.py` 自己的指纹
      模式，key 是 memory id 而非 `(kind,tier)`）；`pick_proactive_reason` 链上插入调用；
      `format_reason_block`/`fallback_line_for_reason` 补 share 分支（**fallback 文案故意不泄露
      具体素材内容**，只有 LLM 路径才会真正提到这段经历——所以 fallback 走的那次不算"用过"）。
    - [proactive_opener.py](../backend/app/behavior/proactive_opener.py)：`resolve_proactive_opener`
      在 LLM 生成**成功**后，若 `reason.kind=="share"` 则与 `mark_proactive_llm_used` 同一次
      `store.update_mood_state` 一起写入 share 指纹——**LLM 失败/未启用时不消费指纹**，与上面的
      fallback 设计一致。
    - [budget.py](../backend/app/memory/budget.py)：新增 `share_fingerprint_history_size`（默认4），
      三处同步模式（dataclass + json + 默认值）。
- **测试**：新建 [test_proactive_share.py](../backend/tests/test_proactive_share.py)（8 个用例：
  share 被选中/被 commitment 压过/反重复指纹排除后降级到 check_in/池空时降级到 memory_callback/
  指纹工具函数 FIFO/`resolve_proactive_opener` 成功写指纹/LLM 失败不写指纹）；同时把
  `test_proactive_opener.py` 两个全 kind 参数化测试（`format_reason_block`/`build_proactive_messages`）
  扩展进 `share`。
- **本轮发现并修复**：实施时在 `proactive_reason.py` 里手动插入代码引入了一处多余空行（双空行），
  review 阶段发现并修正——纯格式问题，不影响逻辑，commit 前已修好。
- **验证结果**：相关测试 67 passed；全量 `pytest backend/` → **557 passed**（P9-P2-A 后基线545，
  本轮 +12：8 个新测试 + 2 个参数化扩展共 +4 项）。

## 上一轮已完成（2026-06-22，第四十二轮）

### P9-P2-A · idle_experience memory type + idle_tick 低频写入（白名单素材版）
- **`/architect` 拆解 + 关键产品决策讨论**：用户确认 idle_experience 内容生成**可以用 LLM**
  （不必纯模板），前提是必须基于**真实素材**（真新闻/真电影），LLM 只能在素材范围内复述反应、
  不能编造素材之外的细节。联网获取真实素材（原计划的 P2-C）当前**先用人工维护的白名单素材池
  代替**，接口设计成可插拔，方便以后直接换成真联网而不动其余代码——这是用户明确拍板的路径
  （路径 B，"以后要升级成真联网"）。
- **Schema**：`schema.py` `MEMORY_TYPES` 加 `idle_experience`，**不进** `FACTUAL_MEMORY_TYPES`
  （这是 Boxi 自己的经历，不是用户事实，避免被 reflection 的 consolidation/cross-link 逻辑误判）。
  无 DB schema 变更，不涉及 migration。`docs/MEMORY_DESIGN.md` 同步新增一节说明类型语义+反编造
  约束+节奏门控+P2-C 升级路径。
- **节奏门控**：`budget.py` 新增 5 个字段（`idle_experience_enabled`/`idle_experience_min_gap_hours`
  (默认6h)/`idle_experience_daily_max`(默认4)/`idle_experience_max_output_tokens`/
  `idle_experience_fingerprint_history_size`）。
- **核心模块**：新建 [idle_experience.py](../backend/app/behavior/idle_experience.py)
  `resolve_idle_experience_write()`——**架构上完全镜像** `proactive_opener.py` 的
  `resolve_proactive_opener()` 模式：路由层编排（不进 `engine.py`，零行改动），failure-swallowing，
  日配额+最小间隔门控，反重复用素材 id 做 FIFO 指纹。
- **素材池**：新建 `config/idle_material_pool.example.json`（模板，1 条真实占位素材+1 条占位待
  替换）。**`config/idle_material_pool.json`（真实生产素材池）仍未创建**——需要用户后续手动核实
  补充真实新闻/电影条目。
- **接入点**：`main.py` `/behavior/evaluate` 路由，`idle_tick` 分支里调用
  `resolve_idle_experience_write`，与 `proactive_check` 分支调 `resolve_proactive_opener` 完全对称。
- **测试**：新建 `test_idle_experience.py`（10 个用例）。

### 上一轮验证结果
- `pytest backend/tests/test_idle_experience.py` 10 passed；全量 `pytest backend/` → 545 passed。

## 当前未完成
- **`config/idle_material_pool.json` 真实素材**——P2-A 只建了 `.example.json` 模板（1 条真实
  占位+1 条待替换占位），生产用的真实素材池需要用户后续手动核实补充。**这是 share intent 真正
  有内容可分享的前提**——当前线上 share 池为空（除非用户已自行补充），`_pick_share` 会自然降级
  到下一优先级，不会报错，但也不会真的触发分享。
- **P9-P2-C**（素材源从白名单升级为真联网，接口已在 `idle_experience.py:load_material_pool()`
  留好可插拔点；非阻塞，P2-A/B 跑稳后再做）。
- **P9-D**（投递层 epic：server scheduler + 推送，突破 poll-only），排在灵魂层 P0/P1/P2 之后。
- **P11**（回复语言切换玩法，轻量，可穿插）。
- **P9-P2-B 真机验证未做**——本轮只做了单测层面验证（67 passed + 全量557 passed），未实际触发
  share intent 走一遍真机对话观察语感（需要先有真实素材池才有意义测）。建议补了真实素材池后
  再做这次真机验证，和 P9-P1 那次的验证方法类似（临时改写 mood_state/relationship_state 模拟条件）。
- **P9-P1 验证的已知限制**（沿用自第四十一轮）：只测到 `commitment_followup` 一种 intent，
  未覆盖 `check_in`/`memory_callback`/`due_reminder`/现在新增的 `share` 轮替。非阻塞。

## 已知 bug / 风险
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8
  （`VIKING_MEMORY_API_KEY` 建议轮换）、R4（`experiments/`废弃）、标签器质量「时好时坏」需
  `--repeats N` 统计判断、04（揶揄+心软）场景统计基线与真机听感矛盾未深究。
- 「主动找你」当前仍是 poll-only（`useBehaviorTicks.ts` 驱动，tab 关了不发）——P9-D 才解决。
- `mood.boredom`/`mood.loneliness` 本身仍按 idle tick 数累积、与现实时间脱钩（与 `longing.py`
  的墙钟双轨并存）。P9-P1/P9-P2 均已绕开此问题，未触碰。
- **本轮无新增 bug/风险**——P9-P2-B 实施过程中发现的唯一问题（多余空行）已在 review 阶段自查修复。

## 推荐下一个最小任务
- **补充 `config/idle_material_pool.json` 真实素材**（用户手动核实，非 Claude 任务范围）——这是
  让 P9-P2-A/B 真正产生效果的前提，建议优先做，否则 share intent 长期是"装好了但没东西分享"的
  空转状态。
- 其次候选：**P9-P2-B 真机验证**（待素材池补好后）或直接讨论 **P9-D**（投递层 epic）启动时机。

## 下一步只需读取
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（P9 拆解节）
- **若做 P9-P2-B 真机验证**：参考 `docs/P9_P1_VERIFICATION.md` 的验证方法（临时改写 DB 状态模拟
  条件，测完用备份还原）。
- **若启动 P9-D**：`docs/TASK_QUEUE.md` 里 P9-D 的 D1/D2/D3 拆解（server scheduler / 持久消息线 /
  推送）。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike，确认过故意不提交）
- ❌ 全仓库扫描 / 与当前任务无关的模块（TTS/标签器/RTC/前端 UI 都不碰）
- ❌ 不要重新讨论 P9-P0/P9-P1/P9-P2-A/P9-P2-B 的设计是否够好——均已 review/测试通过，除非新发现
  具体问题

## 沿用的既有未完成项（本轮未碰）
- **P9-D**（见 `docs/TASK_QUEUE.md` P9 拆解节）
- **P11**（回复语言切换，轻量玩法）；**Obsidian 链接**（后续讨论名单）
- **mood 墙钟化重构**（见上「已知 bug/风险」）
- **情绪识别旁路**（Hume prosody 当传感器，第二档，先 spike）
- P8-C 语音 Pipecat 两阶段路径、RTC character_manifest 同步、信笺 UI P2、R11（搁置）、world brain 天气 API
- **P10**（标签器模型+Fish Audio 潜力探索，待用户决定时机）

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
