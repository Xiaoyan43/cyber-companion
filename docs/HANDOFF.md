# HANDOFF — 上下文交接（2026-06-22，第四十二轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P9-P2-A（idle_experience 写入机制）已完成，545 pytest 全绿，未 commit。**
下一步候选：**P9-P2-B**（share intent 接入 proactive_reason）。

## 本轮已完成（2026-06-22，第四十二轮）

### P9-P2-A · idle_experience memory type + idle_tick 低频写入（白名单素材版，未 commit）
- **`/architect` 拆解 + 关键产品决策讨论**：用户确认 idle_experience 内容生成**可以用 LLM**
  （不必纯模板），前提是必须基于**真实素材**（真新闻/真电影），LLM 只能在素材范围内复述反应、
  不能编造素材之外的细节。联网获取真实素材（原计划的 P2-C）当前**先用人工维护的白名单素材池
  代替**，接口设计成可插拔，方便以后直接换成真联网而不动其余代码——这是用户明确拍板的路径
  （路径 B，"以后要升级成真联网"）。
- **Schema**：[schema.py](backend/app/memory/schema.py) `MEMORY_TYPES` 加 `idle_experience`，
  **不进** `FACTUAL_MEMORY_TYPES`（这是 Boxi 自己的经历，不是用户事实，避免被 reflection 的
  consolidation/cross-link 逻辑误判）。无 DB schema 变更（`memories.type` 本就是无约束 TEXT），
  不涉及 migration。`docs/MEMORY_DESIGN.md` 同步新增一节说明类型语义+反编造约束+节奏门控+
  P2-C 升级路径。
- **节奏门控**：[budget.py](backend/app/memory/budget.py) 新增 5 个字段
  （`idle_experience_enabled`/`idle_experience_min_gap_hours`(默认6h)/
  `idle_experience_daily_max`(默认4)/`idle_experience_max_output_tokens`/
  `idle_experience_fingerprint_history_size`），仿 P9-P1 proactive 字段三处同步模式
  （dataclass + json + 默认值）。
- **核心模块**：新建 [idle_experience.py](backend/app/behavior/idle_experience.py)
  `resolve_idle_experience_write()`——**架构上完全镜像** `proactive_opener.py` 的
  `resolve_proactive_opener()` 模式：路由层编排（不进 `engine.py`/`_evaluate_idle_tick`，
  **零行改动 engine.py**），failure-swallowing（任何异常/空结果直接返回 None，不抛出），
  日配额+最小间隔门控读写 `mood_state.metadata`，反重复用素材 id 做 FIFO 指纹
  （`idle_experience_recent_material_ids`，复用 P9-P1 同款指纹模式但作用对象是素材而非
  kind+tier）。LLM prompt 显式给一段 `[Real material]` 块 + 硬性约束"只能在这段范围内发挥,
  不能编造"。
- **素材池**：新建 `config/idle_material_pool.example.json`（模板，仿 persona/budget 的
  example/真实文件分离模式）。当前只有 1 条真实占位素材（《银翼杀手2049》概括性剧情，公开资料、
  未涉及具体台词细节）+ 1 条占位待替换。**`config/idle_material_pool.json`（真实生产素材池）
  本轮未创建**——需要用户后续手动核实补充真实新闻/电影条目，这是本轮故意留空的部分。
- **接入点**：[main.py](backend/app/main.py) `/behavior/evaluate` 路由,`idle_tick` 分支里
  调用 `resolve_idle_experience_write(store, budget=budget, router=get_provider_router())`，
  与 `proactive_check` 分支调 `resolve_proactive_opener` 完全对称的编排位置。
- **测试**：新建 [test_idle_experience.py](backend/tests/test_idle_experience.py)（10 个用例：
  enabled开关/日配额/最小间隔/素材反重复挑选/空池兜底/端到端写入成功/端到端门控拦截/空池端到端）。
- **验证结果**：`pytest backend/tests/test_idle_experience.py` 10 passed；全量
  `pytest backend/` → **545 passed**（P9-P1 验证后基线 535，本轮 +10）。
- **未 commit**——本轮结束后建议先 review diff 再决定是否落 master。

## 上一轮已完成（2026-06-22，第四十一轮）

### P9-P1 真机验证（PASS，无代码改动）
- 用 `/architect` 拆出验证步骤后，通过 `POST /behavior/evaluate`
  （`event_type=proactive_check`, `force_proactive=true`）实际触发三档（无聊/想念/赌气），
  人工核对开场白语感 + 反重复指纹机制。
- **验证方法**：临时改写 `relationship_state.closeness`/`last_meaningful_interaction_at`
  + `mood_state.metadata_json` 里的频率门控字段（`proactive_pending_since`/
  `proactive_daily_count`/`proactive_llm_daily_count`）来模拟三档墙钟状态、绕开测试期间的
  发送频率限制。测试前先备份数据库
  （`data/backups/cyber_companion_pre_p9p1_verify_20260622_175104.db`），测完已用该备份
  **完整还原** `data/cyber_companion.db`，无残留改动。
- **结论 PASS**：
  - 三档语气递进清晰——无聊（平铺提醒）→ 想念（带埋怨"别再把我当消遣了好吗"）→
    赌气（"终于舍得来了啊？""笨蛋/混蛋/懒鬼"，傲娇但黏着，**未出现**任何冷淡/疏远用词）。
  - 反重复指纹按 `(kind, tier)` 正确记录、FIFO 容量钳制正常；同一指纹连续命中 4 次
    （`commitment_followup:sulk` x4）时系统**仍正常发送**且每次记录，未阻断/未强制换 intent，
    与设计文档「重合时静默放行但记录」一致。
- **已知限制**：本次只测到 `commitment_followup` 一种 intent（被一条真实
  `stable_profile` 记忆——id=19/453/463，关于用户"面试"相关依赖描述——持续判定为最高优先级
  压过其他 3 类 intent），未覆盖 `check_in`/`memory_callback`/`due_reminder` 轮替。要测需改
  `memories` 表正文（侵入性更高，涉及"灵魂"层数据），本轮判断不做。
- 完整报告：[docs/P9_P1_VERIFICATION.md](P9_P1_VERIFICATION.md)（新建，已落盘）。

## 上一轮已完成（2026-06-22，第四十轮）

### 0. 纠正 HANDOFF 历史误报 + 落地遗留未提交改动
- 发现第三十九轮 HANDOFF 写的「P9-P0 本轮未 commit」是**过期错误描述**——P9-P0 实际早已在
  `e41db56` commit。本轮核实清楚后，把真正残留的未提交改动按主题拆两个 commit 落地：
  - `039ea9d` chore(tts): land tagger eval tooling (P10-P0) ——`tag_stats.py`+
    `test_tag_stats.py`+`scripts/tagger_eval.py`（第三十六轮做完一直没提交）
  - `0d228c0` chore(tts): set Fish Audio voice to 慵懒偏低音——`config/tts.json` voice 字段
- `data/tagger_eval/`（生成的评估音频）+ `experiments/*`（废弃 spike）**故意不提交**，原样留作
  untracked（不在 CLAUDE.md 暂缓清单范围内乱动）。

### 1. P9-P1 Part 1 · 想念轨迹三档（commit `aca291d`）
- 新增 `compute_longing_tier()`（[longing.py](backend/app/behavior/longing.py)）：独立纯函数，
  **不改 `LongingSnapshot`**（架构决定：方案 B，避免牵连所有现有消费者）。读已有的墙钟
  `silence_hours`（不碰 `mood.boredom`/`mood.loneliness`，避免牵动 `tone.py` 实时对话语气）。
- 三档：无聊（silence≥24h）→ 想念（≥48h）→ 赌气（≥72h **且** `relationship.closeness≥0.6`）。
  赌气门槛要求亲密度——低亲密关系再久也到不了赌气，只封顶在「想念」。阈值全部进
  [budget.py](backend/app/memory/budget.py)（`longing_tier_bored_hours`/`longing_tier_longing_hours`/
  `longing_tier_sulk_hours`/`longing_tier_sulk_closeness_min`，三处同步：dataclass+json+默认值）。
- `ProactiveReason`（[proactive_reason.py](backend/app/behavior/proactive_reason.py)）新增
  `longing_tier` 字段。**档位正交于 intent**——`pick_proactive_reason` 用 `dataclasses.replace`
  把当前档位上色到全部 4 类 kind（due_reminder/commitment_followup/memory_callback/check_in），
  不只是 check_in。`format_reason_block` 每个分支末尾追加对应 tier 语气块。
- 赌气语气块显式三层框定：尖 + 傲娇（嘴上不认账但显然等了）+ 落点"你终于来了"的松口气——
  **硬性排除 indifference/withdrawal/coldness 用词**（单测断言这两个关键词必须出现在赌气文案里）。
- `engine.py` 的 `_evaluate_proactive_check` 调用处算出 tier 后传给 `pick_proactive_reason`，
  **零行改动 `_evaluate_idle_tick`**。

### 2. P9-P1 Part 2 · 反重复指纹（commit `8f4ba8e`）
- [proactive_opener.py](backend/app/behavior/proactive_opener.py) 新增 `record_proactive_fingerprint()`/
  `is_repeated_fingerprint()`：以 `(kind, tier)` 组合（非完整文本）做指纹——防的是"总用同一种
  主题+语气套路"的结构性重复，不是逐字重复（理由：判重逻辑更简单，且更贴近"活人感"想防的
  套路感而非字面重样）。
- FIFO 存进 `mood_state.metadata["proactive_recent_fingerprints"]`，cap 由新增
  `BudgetConfig.proactive_fingerprint_history_size`（默认 4）控制，复用现有字段模式不动 schema。
- `resolve_proactive_opener` 在 LLM 成功生成 opener 后，与 `mark_proactive_llm_used` 同一次
  `store.update_mood_state` 一起写入指纹。
- **本轮范围明确收窄**：只落地"写入+读取"机制本身，**不改 `pick_proactive_reason` 的选择逻辑**
  （重合时静默放行但记录，不重试、不强制换 intent）——避免 scope 膨胀，是用户明确确认的策略。

### 验证结果
- 全量 `pytest backend/` → **535 passed**（P0 完成时 531 passed，P1 新增 4 个）。
- `_evaluate_idle_tick` 全程零行变化（两轮 diff 均 grep 确认）。
- 4 个 commit 均已落 master：`039ea9d` `0d228c0` `aca291d` `8f4ba8e`。

## 当前未完成
- **P9-P2-B**（share intent 接入 `proactive_reason.py`，从未消耗的 `idle_experience` 记忆里挑
  一条作为主动找你的开场素材；用户已确认 share 优先级排得**比较高**，具体顺序需在实施时与现有
  4 类 intent 的优先级表一起定）。依赖 P9-P2-A（已完成，未 commit）。
- **P9-P2-C**（素材源从白名单升级为真联网，接口已在 `idle_experience.py:load_material_pool()`
  留好可插拔点；非阻塞，P2-A/B 跑稳后再做）。
- **`config/idle_material_pool.json` 真实素材**——P2-A 只建了 `.example.json` 模板（1 条真实
  占位+1 条待替换占位），生产用的真实素材池需要用户后续手动核实补充。
- **P9-D**（投递层 epic：server scheduler + 推送，突破 poll-only），排在灵魂层 P0/P1/P2 之后。
- **P11**（回复语言切换玩法，轻量，可穿插）。
- **P9-P1 验证的已知限制**——只测到 `commitment_followup` 一种 intent（见上「本轮已完成」），
  未覆盖 `check_in`/`memory_callback`/`due_reminder` 轮替。非阻塞，启动 P9-P2 不依赖这个补测；
  若想补，需改 `memories` 表正文伪造条件，留作后续可选项。

## 已知 bug / 风险
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8
  （`VIKING_MEMORY_API_KEY` 建议轮换）、R4（`experiments/`废弃）、标签器质量「时好时坏」需
  `--repeats N` 统计判断、04（揶揄+心软）场景统计基线与真机听感矛盾未深究。
- 「主动找你」当前仍是 poll-only（`useBehaviorTicks.ts` 驱动，tab 关了不发）——P9-D 才解决。
- `mood.boredom`/`mood.loneliness` 本身仍按 idle tick 数累积、与现实时间脱钩（与 `longing.py`
  的墙钟双轨并存）。P9-P1 已绕开此问题（tier 直接读 `longing.py` 的墙钟），但若要让"活人感"
  延伸到实时对话语气本身（不只是 proactive 开场白），需要更彻底重构 mood 本身的累积方式——
  评估过 blast radius 会牵动 `tone.py`，已记为独立候选任务，不在近期 scope。

## 推荐下一个最小任务：先 commit P9-P2-A，再启动 P9-P2-B
- **理由**：P2-A 机制已验证（10 个单测+全量545 pytest 绿），是 P2-B 的依赖；建议先 review diff
  落 master，再开 P2-B（share intent），避免未 commit 的改动累积。
- **启动 P9-P2-B 前先做**：读 `backend/app/behavior/idle_experience.py`
  （`resolve_idle_experience_write` 的编排模式）+ `backend/app/behavior/proactive_reason.py`
  （4 类现有 intent 优先级表，决定 share 插入位置）。

## 下一步只需读取
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（P9 拆解节）
- **启动 P9-P2-B**：`backend/app/behavior/idle_experience.py`、
  `backend/app/behavior/proactive_reason.py`、`backend/app/behavior/proactive_opener.py`
  （语气块写法参考）

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike，本轮确认过故意不提交）
- ❌ 全仓库扫描 / 与当前任务无关的模块（TTS/标签器/RTC/前端 UI 都不碰）
- ❌ 不要重新讨论 P9-P0/P9-P1 的设计是否够好——已真机验证 PASS，除非新发现具体问题

## 沿用的既有未完成项（本轮未碰）
- **P9-D**（见 `docs/TASK_QUEUE.md` P9 拆解节）
- **P11**（回复语言切换，轻量玩法）；**Obsidian 链接**（后续讨论名单）
- **mood 墙钟化重构**（见上「已知 bug/风险」）
- **情绪识别旁路**（Hume prosody 当传感器，第二档，先 spike）
- **TTS 音色**已落地为「慵懒偏低音」`ef5c98bd…`（本轮已 commit 进 `config/tts.json`）
- P8-C 语音 Pipecat 两阶段路径、RTC character_manifest 同步、信笺 UI P2、R11（搁置）、world brain 天气 API
- **P10**（标签器模型+Fish Audio 潜力探索，待用户决定时机；`tagger_eval.py` 工具本轮已落地 commit）

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
