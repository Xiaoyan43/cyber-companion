# HANDOFF — 上下文交接（2026-06-22，第四十轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P9-P1（反重复 + 想念轨迹分档）已完成并 commit。**
下一步候选：**P9-P2**（"她有自己的生活" idle 经历生成）或先验证 P9-P1 真机效果。

## 本轮已完成（2026-06-22，第四十轮）

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
- **P9-P2**（"她有自己的生活"——idle 低频生成"盒子里的念头/经历"写入记忆，新增 `share` intent
  取用之）。⚠️ 可能新增 `idle_experience` memory type，撞 CLAUDE.md「改 schema 须更新
  `docs/MEMORY_DESIGN.md`」，启动前先决策复用现有 memory type vs 新增。
- **P9-D**（投递层 epic：server scheduler + 推送，突破 poll-only），排在灵魂层 P0/P1/P2 之后。
- **P11**（回复语言切换玩法，轻量，可穿插）。
- **P9-P1 真机验证未做**——本轮只验证了单测，实际 proactive 开场白在赌气/想念档下听感如何、
  指纹去重是否真的减少了"套路感"，都还没真机听过。下一次有 proactive 真实触发时建议留意。

## 已知 bug / 风险
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8
  （`VIKING_MEMORY_API_KEY` 建议轮换）、R4（`experiments/`废弃）、标签器质量「时好时坏」需
  `--repeats N` 统计判断、04（揶揄+心软）场景统计基线与真机听感矛盾未深究。
- 「主动找你」当前仍是 poll-only（`useBehaviorTicks.ts` 驱动，tab 关了不发）——P9-D 才解决。
- **本轮新增候选项（非 bug，记入 TASK_QUEUE 后续讨论名单）**：`mood.boredom`/`mood.loneliness`
  本身仍按 idle tick 数累积、与现实时间脱钩（与 `longing.py` 的墙钟双轨并存）。P9-P1 已绕开此
  问题（tier 直接读 `longing.py` 的墙钟），但若要让"活人感"延伸到实时对话语气本身（不只是
  proactive 开场白），需要更彻底重构 mood 本身的累积方式——评估过 blast radius 会牵动
  `tone.py`，已记为独立候选任务，不在本轮 scope。

## 推荐下一个最小任务：先真机验证 P9-P1，再决定是否启动 P9-P2
- **理由**：P9-P0/P9-P1 都只验证过单测，从未真机看过 proactive 开场白长什么样。继续往
  P9-P2（更大的"经历生成"功能）叠加之前，先确认地基（tier 语气+反重复）真的有效，避免在
  有缺陷的基础上继续盖楼。
- **怎么验证**：可用 `force_proactive=True` 触发几次（不同 closeness/silence 组合），肉眼看
  4 类 intent 在 3 个 tier 下生成的开场白是否真的有"无聊/想念/赌气"的语感区分，赌气是否真的
  传达出"傲娇但黏着"而非冷淡。
- **若验证 PASS**，下一步是 **P9-P2**（要先读 `docs/TASK_QUEUE.md` P9 拆解节，决定
  `idle_experience` memory type 的 schema 问题怎么处理，再启动 `/architect`）。

## 下一步只需读取
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（P9 拆解节）
- **真机验证**：`backend/app/behavior/proactive_opener.py`、`engine.py` 的
  `_evaluate_proactive_check`（`force_proactive` 参数用法）
- **若启动 P9-P2**：再额外读 `backend/app/memory/database.py`（memory type 现状）、
  `docs/MEMORY_DESIGN.md`

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike，本轮确认过故意不提交）
- ❌ 全仓库扫描 / 与当前任务无关的模块（TTS/标签器/RTC/前端 UI 都不碰）
- ❌ 不要重新讨论 P9-P0/P9-P1 的设计是否够好——单测已验证逻辑正确，除非真机验证发现具体问题

## 沿用的既有未完成项（本轮未碰）
- **P9-P2 / P9-D**（见 `docs/TASK_QUEUE.md` P9 拆解节）
- **P11**（回复语言切换，轻量玩法）；**Obsidian 链接**（后续讨论名单）
- **mood 墙钟化重构**（本轮新增候选，见上「已知 bug/风险」）
- **情绪识别旁路**（Hume prosody 当传感器，第二档，先 spike）
- **TTS 音色**已落地为「慵懒偏低音」`ef5c98bd…`（本轮已 commit 进 `config/tts.json`）
- P8-C 语音 Pipecat 两阶段路径、RTC character_manifest 同步、信笺 UI P2、R11（搁置）、world brain 天气 API
- **P10**（标签器模型+Fish Audio 潜力探索，待用户决定时机；`tagger_eval.py` 工具本轮已落地 commit）

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
