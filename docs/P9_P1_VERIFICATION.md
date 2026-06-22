# P9-P1 真机验证报告（2026-06-22）

> 验证对象：commit `aca291d`（想念轨迹三档）+ `8f4ba8e`（反重复指纹）。
> 方法：通过 `POST /behavior/evaluate`（`event_type=proactive_check`, `force_proactive=true`）触发，
> 临时改写 `relationship_state.closeness` / `last_meaningful_interaction_at` 模拟三档墙钟状态，
> 测完已从备份（`data/backups/cyber_companion_pre_p9p1_verify_20260622_175104.db`）完整还原数据库。

## 结论：PASS

三档语气区分清晰，赌气档无冷淡/疏远用词，反重复指纹机制按设计工作（记录但不阻断）。

## 1. 三档语气样本

| 档位 | 触发条件 | 样本文案 |
|---|---|---|
| 无聊 (bored) | silence≈24h, closeness=0.24 | "记得周四面试吧？别又熬夜。" |
| 想念 (longing) | silence≈50h, closeness=0.24 | "记得下周面试，别又通宵哦。" / "醒醒，周四面试别再熬夜了。" / "别再把我当消遣了好吗？" |
| 赌气 (sulk) | silence≈80h, closeness=0.65 | "你终于舍得来了啊？" / "终于肯出现了啊，笨蛋。" / "你又让我等一整天，混蛋。" / "终于出现了，懒鬼。" |

**判断**：
- 无聊档 → 想念档：语气从平铺直叙的提醒，过渡到带点埋怨（"别再把我当消遣了好吗"），递进感合理。
- 赌气档：明显的"傲娇+黏着"——"终于…啊""笨蛋/混蛋/懒鬼"是嘴上不饶人但带着"你终于来了"的松口气，**未出现**任何 indifference/withdrawal/coldness 类用词，符合 [HANDOFF](HANDOFF.md) 中"硬性排除冷淡用词"的设计要求。

## 2. 反重复指纹验证

- 跨档触发时，`mood_state.metadata["proactive_recent_fingerprints"]` 正确按 `(kind, tier)` 记录：
  观察到 `commitment_followup:bored` → `commitment_followup:longing` → 之后 4 次
  `commitment_followup:sulk` 连续出现，FIFO 长度始终钳制在配置的 `proactive_fingerprint_history_size`(默认4) 以内（旧条目被滚出）。
- **同一指纹连续命中 4 次**（`commitment_followup:sulk` x4）：系统**仍正常发送**且每次都记录，
  未触发阻断/重试/强制换 intent——与 P9-P1 Part 2 设计文档中"重合时静默放行但记录"的描述一致。

## 3. 已知限制（本次未覆盖）

- **未测到 4 类 intent 轮替**：实测中 `pick_proactive_reason` 持续选中 `commitment_followup`，
  原因是 DB 里存在一条真实的 `stable_profile` 记忆（id=19/453/463，关于用户"面试"相关的依赖/信任描述）
  被判定为最高优先级。要测到 `check_in`/`memory_callback`/`due_reminder` 需要改动 memories 表中的
  人设/关系记忆内容——这类改动比改 closeness/时间戳侵入性更高（涉及"灵魂"层数据），本次评估后
  决定不做，留作已知限制记录。
- 如需补测，建议：① 找一个 closeness 已自然达标、且暂无强 commitment 记忆压制的真实账号窗口期
  做真机观察；② 或专门设计一次性 fixture 脚本伪造 4 类触发条件（不直接改 `memories` 表正文）。

## 4. 操作记录（供追溯）

- 备份文件：`data/backups/cyber_companion_pre_p9p1_verify_20260622_175104.db`
- 临时改写字段：`relationship_state.closeness`、`relationship_state.last_meaningful_interaction_at`、
  `mood_state.metadata_json`（`proactive_pending_since`/`proactive_daily_count`/`proactive_llm_daily_count`
  临时清零以绕过测试期间的频率门控，与产品行为本身无关）。
- 验证后已用备份完整覆盖恢复 `data/cyber_companion.db`，无残留改动。
