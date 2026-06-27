# Shared Soul Runtime — Post-Merge 稳定化计划

> **状态**：计划文档（非 implementation checkpoint）。  
> **进度真相源**：`docs/SOUL_RUNTIME_STATUS.md` · **架构契约**：`docs/SOUL_RUNTIME_ARCH.md`  
> 最后更新：**2026-06-27** · introduced by docs commit: `262bd02`

本文件记录 Phase 0–7 合并至 `master` 后的 **rollback 矩阵、观测清单、legacy/dual-write 退役路线**。  
**不包含**已完成的代码退役承诺；P2 退役需单独 session + 用户确认。

---

## 1. 当前基线

| 字段 | 值 |
|---|---|
| **branch** | `master` |
| **stabilization doc introduced by** | `262bd02` — `docs(soul): add stabilization rollback plan` |
| **merge commit** | `dbefff0` — `Merge pull request #1 from Xiaoyan43/codex/soul-runtime` |
| **accepted implementation HEAD** | `95848c4` — Phase 7 rebase integration 代码/测试验收 checkpoint |
| **invariant 回归** | `./.venv/bin/python -m pytest -m invariant` → **353 passed** |
| **backend 全量** | `./.venv/bin/python -m pytest backend/tests` → **725 passed** |

> 纯 docs commit（如 `6fc4c2f`、`1484577`）**不抬高** accepted implementation HEAD。  
> 有 dirty 工作树时，以 `95848c4` 为代码基准，不以工作树未提交内容为准。

---

## 2. Rollback 矩阵

按影响面从大到小排列。所有 rollback **优先 config / 停写**；整库 revert 为最后手段。

| 场景 | 机制 | 操作步骤 | 数据影响 | 验证 |
|---|---|---|---|---|
| **A. 整次 merge 回退** | Git revert / 部署旧 build | `git revert -m 1 dbefff0`（或 checkout pre-merge `master`）并跑全量测试 | 已写入的 additive 表（`soul_events`、`open_loops`、`existential_state`、`behavior_runtime_state`）**保留在 SQLite**，旧代码可能忽略 | invariant 353 + backend 725 绿；text/Pipecat  smoke |
| **B. Proactive agenda → longing 回退** | `proactive_reason_mode` | `config/budget.json` 设 `"proactive_reason_mode": "longing_only"`（示例见 `config/budget.example.json` 默认 `"agenda"`） | 无 schema 变更；空 `open_loops` 时行为接近 legacy check-in | `test_proactive_motivation.py::test_longing_only_mode_restores_check_in_fallback` · `test_proactive_pi4.py` |
| **C. Additive schema 停写** | 停写、不删表 | 回退 runtime `commit_turn` 的 `event_log.append`；或 revert Phase 3A/3B commits | `soul_events` / `open_loops` 表与历史行保留；读路径可空转 | `test_soul_events.py` · `test_open_loops.py`（若停写需定向调整预期） |
| **D. Memory candidate adapter** | 隔离模块 | 删除或忽略 `backend/app/memory/adapters/*`；**无需**动 `ports_from_store`（Phase 5 未接入） | 无 production DB 影响 | `test_memory_adapter_contract.py` |
| **E. RTC off-path commit 回退** | budget kill switch 或 revert Phase 7 | `config/budget.json` 设 `"enable_turn_analyzer": false`；或 revert `turn_analyzer` → `SoulTurnRuntime.commit_turn` 路径 | RTC 语音回合仍发生，但 off-path kernel/memory/event 写回停止 | `test_turn_analyzer.py`（`enable_turn_analyzer=False` 用例） |

### 2.1 Merge rollback（A）补充

- **不推荐**在生产库上 `DROP TABLE` 回滚 Phase 3/4 additive 表；旧列/旧表设计为只读兼容。
- 若仅需禁用新行为而保留代码：组合 **B + C（停写）+ E** 通常足够，无需 revert 整个 PR。

### 2.2 Proactive agenda rollback（B）补充

实现入口：`backend/app/behavior/motivation.py` → `resolve_proactive_motivation()`。

| mode | 行为 |
|---|---|
| `"agenda"`（当前默认） | `pick_agenda_proactive_reason()`；无 due/overdue open_loop 时 **无** longing-only fallback |
| `"longing_only"` | `pick_proactive_reason()` + check-in fallback（Phase 6 前行为） |

Longing/Poisson **节奏闸**与 mode 正交：`longing` 仍决定是否「现在合适」，mode 决定「为什么找你」。

### 2.3 Additive schema rollback（C）补充

Phase 3–4 新增表（均 **additive**，见 `backend/app/memory/schema.py`）：

| 表 | 写入入口 | 停写 kill switch |
|---|---|---|
| `soul_events` | `SoulTurnRuntime.commit_turn` → `EventLogPort.append` | 移除/跳过 append；`commit_turn` 内已有 `try/except` 吞掉 event 失败 |
| `open_loops` | `MemoryStore` CRUD；proactive 只读 due/overdue | 空表 = 无 agenda reason；`NoopAgendaPort` 可禁用 agenda 读 |
| `existential_state` | `update_existential_state` / backfill | 旧 mood 三列仍可读；context builder 已改读 canonical |
| `behavior_runtime_state` | `patch_behavior_runtime_metadata` 等 | 与 mood legacy dual-write 绑定，见 §4 |

**禁止**在未计划 migration 的情况下删列/删表。

### 2.4 Memory adapter spike rollback（D）补充

- 模块：`backend/app/memory/adapters/`（Letta/Mem0 candidate、`ShadowMemoryPort`）。
- `ports_from_store()` 始终绑 `SQLiteMemoryPort`；runtime **未**引用 candidate。
- 回滚 = 不 import / 删目录 + 删 `test_memory_adapter_contract.py`（若整 spike 废弃）。

### 2.5 RTC off-path commit rollback（E）补充

- 入口：`backend/app/reflection/turn_analyzer.py` → `analyze_turn()` → `SoulTurnRuntime.commit_turn(..., surface="rtc_off_path")`。
- Kill switch：`budget.enable_turn_analyzer = false`（`config/budget.example.json` 默认 `true`）。
- RTC 主链路（live transport）仍按 ARCH 决策 6 **不**走完整 `run_turn`；仅 off-path 写回与主 runtime 对齐。

---

## 3. Observability 清单

Post-merge 观测优先 **SQLite 可查询 + 现有测试名**，不依赖新 metrics 栈。

| 观测点 | 含义 | 代码 / 存储 | 建议检查方式 |
|---|---|---|---|
| **`soul_events` / `turn.committed`** | 回合 commit 是否写入 event log | `SoulTurnRuntime.commit_turn` · `MemoryStore.append_soul_event` | `store.tail_soul_events(kinds={"turn.committed"})`；测试 `test_soul_events.py` · `test_soul_ports.py` |
| **`open_loops` due/overdue reason** | Proactive「为什么找你」 | `pick_agenda_proactive_reason` · `SQLiteAgendaPort` | 查 `open_loops` 表 status/due_at；`test_open_loops.py` · `test_proactive_motivation.py` |
| **behavior runtime state / mood legacy dual-write** | operational metadata 是否 canonical + 兼容镜像 | `patch_behavior_runtime_metadata` 双写 `behavior_runtime_state` + `mood_state.metadata_json` | `test_behavior_runtime_state.py::test_runtime_patch_and_remove_dual_write_legacy_copy` |
| **existential_state canonical** | gap/box_relation/self_ease 读路径 | `get_existential_state` · context builder | `test_existential_state.py` |
| **summary / memory writes** | 回合持久化与 M2/M3 | `commit_turn` → memory port 链 | `test_memory*` · `test_soul_turn_contract.py` |
| **proactive decision mode** | agenda vs longing_only | `resolve_proactive_motivation` · `budget.proactive_reason_mode` | 日志/调试：reason 为 `None` vs check-in；`test_proactive_motivation.py` |
| **RTC off-path commit** | 语音纯 E2E 写回 | `turn_analyzer.analyze_turn` · surface=`rtc_off_path` | `test_turn_analyzer.py`；event payload `metadata` / `called_llm` |

### 3.1 手动 smoke（可选）

```bash
# invariant 门禁
./.venv/bin/python -m pytest -m invariant -q

# soul 专项
./.venv/bin/python -m pytest backend/tests/test_soul_events.py backend/tests/test_open_loops.py \
  backend/tests/test_proactive_motivation.py backend/tests/test_behavior_runtime_state.py \
  backend/tests/test_turn_analyzer.py -q
```

---

## 4. Legacy / dual-write 退役计划（P2 — 未开始）

**当前状态**：dual-write **仍在运行**（Phase 4B 兼容期）。本计划 **不** 宣称已退役。

### 4.1 原则

1. **不立刻删** legacy 列/表/metadata 路径。
2. **先标记** 所有读写路径（canonical vs legacy copy）。
3. **补 invariant / targeted tests** 证明读路径只依赖 canonical。
4. **停 legacy write**（单 PR，可回滚）。
5. **最后** 评估 schema cleanup（需 migration 框架或显式用户批准）。

### 4.2 已知 dual-write / legacy 区域

| 区域 | Canonical | Legacy / dual-write | 关键 API |
|---|---|---|---|
| Operational mood metadata | `behavior_runtime_state.metadata_json` | `mood_state.metadata_json` 镜像 | `patch_behavior_runtime_metadata` · `replace_mood_metadata` |
| Existential baseline | `existential_state` | mood 三列（停止生产读写，列保留） | `get_existential_state` · context builder |
| Relationship trust | `relationship_state.trust` | mood GET/PUT trust 别名 | mood API 兼容层 |
| `positive_zone_streak` | 仍在 `mood_state` | — | tone / behavior 路径 |

### 4.3 P2 退役验收标准（草案）

- [ ] 读写路径 inventory 文档化（本文件 §4.2 扩展为完整表格）
- [ ] 新增或扩展 invariant：legacy 列在 patch 后 **不再** 被生产写入
- [ ] `pytest -m invariant` ≥ 353 passed；`backend/tests` ≥ 725 passed
- [ ] 旧 DB（dual-write 期间创建）可原地打开，无 crash
- [ ] 用户明确批准 schema 列删除（若有）

---

## 5. Feature flags / Kill switches

> **来源**：`BudgetConfig`（`backend/app/memory/budget.py`）+ `config/budget.example.json`；  
> 生产覆盖写 `config/budget.json`（gitignored）。  
> **Example 列** = `budget.example.json` 显式值；未列出字段用 `BudgetConfig` dataclass 默认（`load_budget_config` fallback）。  
> **Rollback 列** = 已知可安全回退 / 刹车的配置值；`≤0` 对 spend cap 表示**禁用该上限**（见 `usage_guard.py`）。  
> **类型**：`flag` = 显式布尔/枚举；`throttle` = 数值节流；`structural` = 无独立 config，靠结构/接线隔离。

### 5.1 Soul / proactive

| 开关 | 类型 | 配置位置 | Example 默认 | Rollback / kill-switch | 影响面 | 验证 |
|---|---|---|---|---|---|---|
| `proactive_reason_mode` | flag | `budget.json` | `"agenda"` | `"longing_only"` | **为什么找你**：`agenda` 仅 due/overdue open_loop / reminder / memory 等实质 reason；`longing_only` 恢复 Phase 6 前 check-in fallback | `test_proactive_motivation.py::test_longing_only_mode_restores_check_in_fallback` · `test_agenda_mode_blocks_longing_only_check_in` · `test_proactive_pi4.py` |
| `enable_proactive` | flag | `budget.json` | `true` | `false` | 关闭全部 proactive tick / opener；`force_proactive` dev 路径仍受此门 | `test_pi1_followups.py::test_force_proactive_still_respects_enable_proactive` · `test_longing.py`（gate 系列） |
| `proactive_quiet_hours` | throttle | `budget.json` | `[23, 8]` | 扩至全天如 `[0, 0]`（测试用）或缩窄窗口 | 本地时间 quiet window 内不主动 | `test_longing.py::test_quiet_hours_block` |
| `proactive_min_gap_minutes` | throttle | `budget.json` | `30` | 增大（如 `1440`）或 `0`（测试） | 距上次用户消息后最短等待 | `test_longing.py::test_post_conversation_cooldown_blocks` |
| `proactive_min_fire_gap_hours` | throttle | `budget.json` | `6` | 增大或 `0` | 两次 proactive **发射**之间的最短间隔 | `test_longing.py`（`check_proactive_availability` gate） |
| `proactive_daily_max` | throttle | `budget.json` | `2` | `0`（禁用日上限）或 `1` | 每日 proactive 发射次数上限 | `test_longing.py::test_daily_cap_blocks` |
| `proactive_max_delta_seconds` | throttle | `budget.json` | `600` | 减小 | longing snapshot 墙钟 delta 上限（防异常跳时） | `test_longing.py::test_poisson_probability_is_deterministic` |
| `longing_silence_hours_scale` | throttle | `budget.json` | `48` | 调大 → 想念涨得更慢 | longing intensity 对沉默时长缩放 | `test_longing.py::test_longing_rises_with_silence_at_same_closeness` |
| `longing_closeness_weight` | throttle | `budget.json` | `0.55` | 调低 → 亲密度对想念影响减弱 | longing intensity 权重 | `test_longing.py::test_longing_rises_with_closeness_at_same_silence` |
| `longing_loneliness_weight` | throttle | `budget.json` | `0.45` | 同上 | longing intensity 权重 | `test_longing.py` |
| `longing_lambda_base_per_hour` | throttle | `budget.json` | `0.06`（validation 期；dataclass fallback `0.004`） | `0` → Poisson **永不命中**（节奏闸常关） | Poisson 基础触发率；与 `proactive_reason_mode` 正交 | `test_longing.py::test_proactive_check_misses_when_lambda_zero` · `test_proactive_motivation.py::test_agenda_mode_poisson_miss_with_due_loop` |
| `longing_lambda_longing_gain` | throttle | `budget.json` | `2.5` | 调低 → 高强度想念也难触发 | Poisson 率随 longing 放大 | `test_longing.py`（Poisson 确定性种子） |
| `longing_tier_bored_hours` | throttle | `budget.json`（无键） | `24`（dataclass） | 调大 → 更长「无聊」档 | bored / longing / sulk 轨迹分档 | `test_longing.py::test_longing_tier_*` |
| `longing_tier_longing_hours` | throttle | `budget.json`（无键） | `48` | 同上 | 同上 | 同上 |
| `longing_tier_sulk_hours` | throttle | `budget.json`（无键） | `72` | 同上 | 同上 | 同上 |
| `longing_tier_sulk_closeness_min` | throttle | `budget.json`（无键） | `0.6` | 调高 → 更难进入 sulk | sulk 档需高亲密度 | `test_longing.py::test_longing_tier_high_silence_low_closeness_caps_at_longing` |
| `proactive_llm` | flag | `budget.json` | `true` | `false` | proactive opener 是否调 LLM（否则用 fallback line） | `test_proactive_opener.py`（`proactive_llm=False` 用例） |
| `proactive_max_output_tokens` | throttle | `budget.json` | `80` | 减小 | proactive LLM 输出 token 上限 | `test_proactive_opener.py` · `test_proactive_pi4.py` |
| `proactive_llm_daily_max` | throttle | `budget.json` | `5` | `0` | 每日 proactive LLM 调用上限 | `test_proactive_opener.py::test_proactive_llm_gate_respects_daily_cap` |
| `proactive_fingerprint_history_size` | throttle | `budget.json`（无键） | `4` | `0` → 不去重 | 近期 proactive 指纹避重窗口 | `test_proactive_opener.py`（fingerprint） |
| `share_fingerprint_history_size` | throttle | `budget.json`（无键） | `4` | `0` | idle_experience share opener 避重 | `test_proactive_share.py` |
| `idle_experience_enabled` | flag | `budget.json`（无键） | `true` | `false` | 关闭 idle 时「她自己过日子」离线路记忆写入 | `test_idle_experience.py::test_idle_experience_disabled_blocks` |
| `idle_experience_min_gap_hours` | throttle | `budget.json`（无键） | `6` | 增大 | idle 体验写入最小间隔 | `test_idle_experience.py::test_idle_experience_min_gap_blocks` |
| `idle_experience_daily_max` | throttle | `budget.json`（无键） | `4` | `0` | 每日 idle 体验写入上限 | `test_idle_experience.py::test_idle_experience_daily_cap_blocks` |
| `idle_experience_max_output_tokens` | throttle | `budget.json`（无键） | `160` | 减小 | idle LLM 输出上限 | `test_idle_experience.py::test_resolve_idle_experience_write_creates_memory` |
| 空 `open_loops` 表 | **structural** | SQLite `open_loops` | 无行 | 保持空表或删除 due/overdue 行 | `agenda` 模式下无实质 proactive reason（longing 节奏闸仍可过，但 `resolve_proactive_motivation` 无 why） | `test_open_loops.py` · `test_proactive_motivation.py::test_agenda_mode_blocks_longing_only_check_in` |

实现入口：`resolve_proactive_motivation()`（`motivation.py`）· `check_proactive_availability()` / `should_fire_longing()`（`longing.py`）· `_evaluate_proactive_check()`（`engine.py`）。

### 5.2 RTC off-path / reflection

| 开关 | 类型 | 配置位置 | Example 默认 | Rollback / kill-switch | 影响面 | 验证 |
|---|---|---|---|---|---|---|
| `enable_turn_analyzer` | flag | `budget.json` | `true` | `false` | 关闭 RTC pure-E2E off-path `analyze_turn()` 整段（无 kernel/memory/event 写回） | `test_turn_analyzer.py::test_analyze_turn_disabled_returns_early` |
| `analyze_every_n_turns` | throttle | `budget.json` | `1` | 增大（如 `10`） | 降低 off-path LLM appraisal 频率；`≤1` = 每回合 | `test_turn_analyzer.py`（`analyze_every_n_turns=10`  streak 用例） |
| `enable_reflection` | flag | `budget.json` | `true` | `false` | 关闭 off-path reflection worker（consolidate/link/impression/summary jobs） | `test_reflection.py::test_run_reflection_disabled` |
| `reflection_every_n_turns` | throttle | `budget.json` | `6` | 增大 | reflection 认领频率（`store.claim_reflection`） | `test_reflection.py::test_run_reflection_not_due_below_threshold` · `test_claim_reflection_at_threshold_and_single_flight` |

实现入口：`turn_analyzer.analyze_turn()`（RTC off-path commit + 可选 reflection）· `reflection/runner.run_reflection_if_due()`。  
RTC **主 transport** 仍不走 `run_turn`（ARCH 决策 6）；仅 off-path 受上表约束。

### 5.3 LLM / memory budget

| 开关 | 类型 | 配置位置 | Example 默认 | Rollback / kill-switch | 影响面 | 验证 |
|---|---|---|---|---|---|---|
| `max_output_tokens_per_turn` | throttle | `budget.json` | `2400`（dataclass fallback `300`） | 减小 | 主回合 LLM `ChatCompletionRequest.max_output_tokens` | `test_context_builder.py` · `test_companion_brain.py`（truncation） |
| `max_input_tokens_per_turn` | throttle | `budget.json` | `4000` | 减小 | 上下文装配总 input token 预算 | `test_context_builder.py` |
| `max_user_input_tokens` | throttle | `budget.json` | `1500` | 减小 | 单轮用户输入截断 | `test_user_input_truncation.py` |
| `max_raw_turns` | throttle | `budget.json` | `4` | 减小 | 注入上下文的最近 raw 回合数 | `test_context_builder.py` |
| `max_memories_per_turn` | throttle | `budget.json` | `6` | `0` | 每回合检索记忆条数上限 | `test_memory.py` · `test_context_builder.py` |
| `daily_llm_turn_limit` | throttle | `budget.json` | `200` | `0`（禁用日 turn 上限）或调低 | `evaluate_llm_budget_gate` 日 turn 刹车 | `test_usage_guard.py::test_gate_blocks_on_daily_turn_limit` · `test_chat_complete_blocks_when_daily_limit_reached` |
| `monthly_usd_limit` | throttle | `budget.json` | `10` | `0`（禁用月 spend 上限）或调低 | 月 LLM 花费刹车 | `test_usage_guard.py::test_gate_blocks_on_monthly_cost_limit` |
| `allow_reasoning_model` | flag | `budget.json` | `false` | 保持 `false` | 阻止 reasoning 模型名命中 gate | `test_usage_guard.py::test_gate_blocks_reasoning_model_when_disallowed` |
| `auto_memory_write` | flag | `budget.json` | `true` | `false` | 关闭回合后自动记忆写入（M2/M3 路径） | `test_memory_write_policy.py::test_auto_memory_write_can_be_disabled` · `test_record_turn_memories_respects_auto_memory_write_gate` |
| `llm_memory_extraction` | flag | `budget.json` | `true` | `false` | 关闭从 `<<<BOXI_SIGNALS>>>` 解析的记忆提取（仍可在 `auto_memory_write=true` 时走规则路径） | `test_memory_write_policy.py`（`llm_memory_extraction=False` 用例） |
| `llm_summary` | flag | `budget.json` | `true` | `false` | 关闭 reflection 内 LLM 摘要；回退 rule-based summary | `test_reflection.py::test_maybe_update_summary_rule_based_when_llm_summary_off` |
| `summary_batch_size` | throttle | `budget.json` | `6` | 增大 | LLM / rule summary 批次大小 | `test_reflection.py::test_summarize_job_writes_summary` |
| `behavior_tick_retention` | throttle | `budget.json` | `200` | 减小 | behavior tick 历史保留条数 | `test_behavior.py` |
| `allow_cloud_stt` | flag | `budget.json` | `false` | 保持 `false` | 云 STT 许可（语音轨；soul budget 字段） | `test_voice_config.py`（若启用云 STT 路径） |
| `allow_cloud_tts` | flag | `budget.json` | `false` | 保持 `false` | 云 TTS 许可 | 同上 |

Spend brake 在 `SoulTurnRuntime.run_turn` step 4（`memory.check_llm_budget` → `evaluate_llm_budget_gate`）；命中时本地 `budget_block` 回复，不调 provider。

### 5.4 Port / adapter kill switches

| 开关 | 类型 | 配置位置 | Example 默认 | Rollback / kill-switch | 影响面 | 验证 |
|---|---|---|---|---|---|---|
| 空 `open_loops` 表 | **structural** | SQLite | 无 due/overdue 行 | 见 §5.1 | Agenda proactive reason 为空；不等于停写 `soul_events` | 见 §5.1 |
| `NoopAgendaPort` | **structural** | `SoulPorts.agenda` 默认构造 | 非 production | 手动构造 `SoulPorts(..., agenda=NoopAgendaPort())` 或不用 `ports_from_store` | Agenda 读恒 `[]`；生产 `ports_from_store` 用 `SQLiteAgendaPort` | `test_soul_ports.py::test_soul_ports_default_agenda_is_noop` · `test_open_loops.py`（Noop 用例） |
| `NoopEventLogPort` | **structural** | `SoulTurnRuntime` 部分 port 注入 | 非 production | 构造 runtime 时传 `event_log_port=NoopEventLogPort()` | 跳过 `turn.committed` event append；`commit_turn` 内 `try/except` 已吞异常 | `test_soul_ports.py`（fake event log）；smoke：`tail_soul_events` 无新行 |
| Candidate memory adapters | **structural** | `backend/app/memory/adapters/*` | **未接入** `ports_from_store` | 不 import / 不替换 `SQLiteMemoryPort` | 零 production 影响；Letta/Mem0/Shadow 仅 spike | `test_memory_adapter_contract.py` · ARCH Phase 5 |
| `SQLiteEventLogPort` / `SQLiteAgendaPort` | wiring | `ports_from_store()` | production 默认 | 换 Noop 或停写（§2.3） | 正常 event log + open_loop 读写 | `test_soul_events.py` · `test_open_loops.py` · `test_soul_ports.py::test_ports_from_store_includes_sqlite_agenda` |

> **未宣称 rollback**：将 production `ports_from_store` 换成 candidate adapter 或 Shadow port——Phase 5 spike **未验收**为可回滚生产路径，不在此表列为 supported rollback。

### 5.5 环境变量（非 budget flag，但影响加载 / 隔离）

| 变量 | 类型 | 配置位置 | 默认 | Rollback / 隔离值 | 影响面 | 验证 |
|---|---|---|---|---|---|---|
| `CYBER_COMPANION_CONFIG_DIR` | path | env | `./config` | 指向含 `budget.json` 的目录 | `load_budget_config` 读取路径 | 测试 fixture 广泛设置；smoke：确认 `budget.json` 路径 |
| `CYBER_COMPANION_DATA_DIR` | path | env | `./data` | 指向隔离目录 | SQLite DB / 数据文件位置 | `test_memory.py` fixture · 手动 smoke 勿污染生产 `data/` |
| `CYBER_COMPANION_PROVIDER_MODE` | flag | env | （未设 = 正常 provider 配置） | `mock` | 测试/mock provider 路由 | `test_soul_turn_contract.py` · `test_turn_analyzer.py` |

语音轨另有 `CYBER_COMPANION_TTS_MODE` 等（见 `docs/HANDOFF.md`）；**不属于** Soul Runtime budget inventory，稳定化 session 不展开。

### 5.6 快速 smoke（改 budget 后）

```bash
# proactive / longing rollback
./.venv/bin/python -m pytest backend/tests/test_proactive_motivation.py backend/tests/test_longing.py -q

# RTC off-path kill switch
./.venv/bin/python -m pytest backend/tests/test_turn_analyzer.py::test_analyze_turn_disabled_returns_early -q

# spend / memory gates
./.venv/bin/python -m pytest backend/tests/test_usage_guard.py backend/tests/test_memory_write_policy.py -q
```

---

## 6. 推荐后续任务

| 优先级 | 任务 | 说明 |
|---|---|---|
| ~~**P1-3**~~ | ~~Feature flag inventory~~ | ✅ 本节 §5 全量表（2026-06-27） |
| **P1-5** | Turn consistency backlog | §5 ARCH 缺口：Pipecat/RTC surface 契约测试清单 |
| **P2** | Dual-write 退役 | 需单独 approval；按 §4 顺序执行，不在稳定化 docs session 改代码 |
| — | Soul Quality / 语音轨 | 见 STATUS §8 四条路线；不得反向改动 Soul Runtime 契约 |

---

## 7. 相关文档

| 文件 | 用途 |
|---|---|
| `docs/SOUL_RUNTIME_STATUS.md` | 进度、基线、dirty 禁区 |
| `docs/SOUL_RUNTIME_ARCH.md` | 架构契约、Phase 表、invariants |
| `docs/SOUL_RUNTIME_PHASE5_SPIKE.md` | Memory candidate adapter spike 细节 |
| `config/budget.example.json` | budget / proactive / turn_analyzer 默认值 |
