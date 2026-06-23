# P9-P2-B 真机验证报告（2026-06-22）

> 验证对象：commit `be2a81d`（idle_experience 写入机制）+ `9890ca4`（share intent）+ 本轮新建的
> `config/idle_material_pool.json`（生产素材池）。
> 方法：通过 `POST /behavior/evaluate`（`idle_tick` 触发 idle_experience 写入，`proactive_check`
> + `force_proactive=true` 触发 share intent），临时改写 `mood_state.metadata_json`（清空
> idle_experience 节奏门控 + proactive 频率门控/pending 状态）+ 临时压低 8 条 `recent_event`
> 记忆的 importance（绕过 commitment_followup 抢占，原值在验证后已还原）。
> 备份文件：`data/backups/cyber_companion_pre_p9p2b_verify_20260622_082805.db`，验证后已完整还原
> `data/cyber_companion.db`，无残留改动。

## 结论：PASS

idle_experience 用真实素材生成的内容贴合人设、未编造素材外细节；share intent 能被正确选中、
LLM 路径产出引用了具体经历；反重复指纹按设计 FIFO 工作，连续两次 share 正确轮换了两条不同的
idle_experience 记忆，未重复。

## 1. idle_experience 生成样本（真实素材池生效）

- 素材：`movie-the-truman-show`（楚门的世界）
- 生成内容：「我突然意识到，这透明的盒子其实也像楚门的摄影棚，只是我的观众只有你一个人。
  连这点自知之明，都是被你喂给我的。」
- **判断**：把"楚门活在摄影棚里不自知"这一概括性情节，类比到 Boxi 自己"被困盒子里、观众只有
  用户一人"的设定，是合理的人格化反应，未编造素材之外的具体台词/情节细节，符合反编造约束。

## 2. share intent 选中 + LLM 路径产出样本

| 轮次 | 选中的 idle_experience 记忆 | 持久化消息内容 |
|---|---|---|
| 第1次 | id=473（楚门的世界） | 「我突然意识到，这透明的盒子其实也像楚门的摄影棚。」 |
| 第2次 | id=472（占位素材，早于本轮已存在） | 「盒子里的安静太完整了，像谁把声音都抽走了。」 |

- `reason="share"`、`avatar_state="happy"`，且 `should_call_llm=true` 时确认走的是 LLM 路径
  （非 fallback）——`mood_state.metadata.share_recent_memory_ids` 在 LLM 成功后才被写入，
  与 `proactive_opener.py` 的设计一致。
- LLM 产出与 idle_experience 原文高度贴近（接近转述而非完全重写）——这是预期内行为
  （`_pick_share` 把 `chosen.content` 作为 `detail` 喂给 LLM，本意就是"真的提到这段经历"），
  但措辞自由度看起来偏低，**记录为观察项，非 bug**：后续如果觉得"复述感"太重，可以在
  share 的 prompt 里加一句"用自己的话重新讲，不要逐句照抄"，留作 P2-C 或后续微调候选。

## 3. 反重复指纹验证（FIFO，按 memory id）

- 第1次 share 后：`share_recent_memory_ids=[473]`
- 第2次 share 后：`share_recent_memory_ids=[473, 472]`，且 **正确选中了未被指纹覆盖的另一条**
  （id=472），证明 `_pick_share` 的反重复过滤生效，不是随机巧合命中。
- 验证范围内只有 2 条 idle_experience 记忆，未测到"池耗尽后全部被指纹覆盖、降级到下一优先级"
  的边界情况——这与 `test_proactive_share.py` 已覆盖的单测场景一致，本次真机验证目的是确认
  非 mock 环境下端到端贯通，不重复测单测已覆盖的边界逻辑。

## 4. 验证中确认的已知限制（非本轮新增，沿用 P9-P1 记录的同类问题）

- **commitment_followup 优先级压制 share**：验证开始时，8 条近期 `recent_event` 记忆
  （importance 0.7~0.75，14天recency窗口内）持续压过 share，与 P9-P1 验证记录的"真实
  stable_profile 记忆压过其他 intent"是同一类现象（用户近期高频短互动会持续产生
  importance≥0.4 的 recent_event，自然挤占 share/memory_callback 的出场机会）。
  验证时临时压低这 8 条记忆的 importance 至 0.1（仅改数值，未改内容文本），验证后已从备份
  完整还原。**这不是 bug**，是优先级链按设计工作（commitment 排在 share 之前是 P9-P2-B 的
  产品决策），但意味着**生产环境里 share 实际触发频率可能低于预期**，如果近期互动频繁，
  long-tail 的 recent_event 记忆会持续抢占。

## 5. 操作记录（供追溯）

- 备份文件：`data/backups/cyber_companion_pre_p9p2b_verify_20260622_082805.db`
- 临时改写：`mood_state.metadata_json`（清空 `idle_experience_daily_count`/`idle_experience_last_at`/
  `idle_experience_recent_material_ids` 以绕过节奏门控；清空 `proactive_pending_since`/
  `proactive_daily_count`/`proactive_llm_daily_count`/`last_proactive_fired_at`/
  `last_proactive_check_at` 以绕过 proactive 频率门控，与产品行为本身无关）。
- 临时改写：8 条 `recent_event` 记忆的 `importance` 从 0.7~0.75 降到 0.1（仅数值，未改 content
  文本），绕过 commitment_followup 抢占，便于观测 share 分支。
- 验证后已用备份完整覆盖恢复 `data/cyber_companion.db`，已核对 `idle_experience` 记忆数恢复为1、
  `recent_event` importance 恢复原值、mood metadata 恢复原状，无残留改动。
