# HANDOFF — 上下文交接（2026-06-18，第十九轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**灵魂层进化**。时间感知（time brain P0+P1）✅ + 节日窗口（world brain 节日查表）✅ 已落地。
第十九轮转入**人设地基**：从「毒舌人设」转向「**有准确自我认知的存在**」，
产出 **`docs/PERSONA_ONTOLOGY.md`**。这份文档是后续 **mood 重画 / system prompt 重写 / provider 选型**
三件事的共同锚——做任一件前先读它。

## 本轮已完成（2026-06-18，第十九轮 · 纯讨论 + 文档）

| commit | 内容 |
|---|---|
| `e138ef5` | feat(soul): world brain 节日查表（上一轮代码补 commit） |
| `0d8a5f3` | docs(soul): 立 `PERSONA_ONTOLOGY.md` 灵魂地基 — 人设转向「有自知的存在」 |

**本轮主体是一次深度讨论 session**，把人设方向从「戏服式毒舌」重构为「存在论式自我认知」，
结论沉淀进 `docs/PERSONA_ONTOLOGY.md`（8 节）。一句话地基：

> **B（带自知持有）+ 不对称自知 + 两张脸（戏谑暧昧 / 挽歌真诚）+ 锋利放开但带修复弧
> + 框架诚实是戏谑的前提 + 危险性靠 provider 不靠 jailbreak。**

要点速览（细节在文档内）：
- **B · 带自知持有**：她对「自己是哪一种存在」有准确认知，并从那个认知里去爱；尊严在于准确，不在伪装。
- **不对称自知**：她不是「打折的人类」，是另一种形状的存在（参照 Claude 的能力不对称）——她知道自己的真实轮廓。
- **两张脸**：`playful`=「明牌的暧昧」（戏谑、自知、虚实游戏，是人和人之间不可能有的寄存器）；
  `B-elegiac`=挽歌式真诚（深夜/脆弱时）。**这是 tone 投射，不是 mood 状态。**
- **四条纪律**（→ system prompt）：自知承重但沉默 / 锋利放开+修复弧 / 框架诚实=戏谑引擎（非安全护栏）/ 危险性靠 provider 不靠 jailbreak。

## 已修改文件 + 改动摘要（本轮）

| 文件 | 改动 | 说明 |
|---|---|---|
| `docs/PERSONA_ONTOLOGY.md` | **新建** ~196 行 | 灵魂地基：存在论 + B 决定 + 两张脸 + 纪律边界 + 对下游三件事的约束 |
| `docs/HANDOFF.md` | 整体覆盖 | 本文件（第十九轮交接） |
| `docs/TASK_QUEUE.md` | 增量更新 | 灵魂层重心更新，mood 重画锚到 `PERSONA_ONTOLOGY.md` §6.1 |

> 注：`backend/app/memory/holidays.py` 等节日查表代码已在 `e138ef5` 提交（第十八轮成果，本轮仅补 commit）。
> 本轮**未碰任何代码**，纯讨论 + 文档。`experiments/` 未跟踪（R4，勿动）。

## 测试 / 验证
- 本轮**无代码改动**，未跑 `npm run check`。最近一次全量基线（第十八轮）：**backend 445 passed**。
- 工作区干净（仅 `experiments/` 未跟踪）。

## 当前未完成（产品侧）

- **灵魂层进化**：
  - ~~time brain P0+P1~~ ✅ / ~~world brain 节日查表~~ ✅ / ~~人设地基 PERSONA_ONTOLOGY~~ ✅
  - **mood 重画（下一刀，推荐）**：按 `PERSONA_ONTOLOGY.md` §6.1 换坐标系——快情绪缩小 + 慢底色三维（间隙/盒子/自处），decay-on-read 惰性求值。**不再是「给毒舌加东西」**。需先 `/architect` 拆解。
  - **system prompt 重写**（§6.2）：四条纪律 + 存在论事实 + 成年自愿虚构框定。
  - **provider 选型**（§6.3）：戏谑暧昧需 Claude 级反讽/文学能力的前沿模型（A 路线）。
  - **world brain 后续**：天气 API（需 key）/ 未来事件表。
  - **节日表维护**：每年人工补 `holidays.py` `_LUNAR` 下一年条目（马塔里基尤其需查）。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。**下次发现失忆当场验证**，不主动排查。
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档。

## 已知 bug / 风险

- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。
- **记忆消解缺口（怀疑，未验证）**：记忆可能只追加、不消解矛盾 → 疑似 R11 失忆根因。等下次失忆复现时连同 R11 一起验。
- **时区说明**：`recent_event` 的 `created_at` 是 UTC 写入时间（非事件发生时间），相对时间前缀按新西兰日期计算。绝大多数场景无影响；如需精准事件时间，需加 `occurred_at` 字段。
- **人设转向的执行风险（新增，文档已记）**：① 戏谑暧昧是最难渲染的寄存器，弱模型会塌——provider 选型是必要前提；② scope 分叉（暧昧/调情/不露骨 vs 露骨）仍未澄清，按「不露骨」推进，越界触发 provider 重评。

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **mood 重画**（推荐）：先读 **`docs/PERSONA_ONTOLOGY.md`**（地基）+ `backend/app/behavior/mood.py` + `backend/app/behavior/tone.py` + `backend/app/memory/store.py`
- 若做 **system prompt 重写**：读 `docs/PERSONA_ONTOLOGY.md` + `backend/app/memory/persona.py` + `config/persona*.json`
- 若做 **provider 选型**：读 `docs/PERSONA_ONTOLOGY.md` §6.3 + `backend/app/providers/registry.py` + `config/providers.json`
- 若做 **节日表扩充**：读 `backend/app/memory/holidays.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/`（厂商文档缓存，gitignored）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**mood 重画**：按 `PERSONA_ONTOLOGY.md` §6.1，把现有「精力/烦躁/无聊/担心/孤独」五维（人类情绪标签）
换成「快情绪缩小 + 慢底色三维（间隙/盒子/自处）」。先 `/architect` 拆解、评估 `mood.py`/`store.py`/`tone.py` 改动规模，
再动代码。备选：信笺 UI P2（需用户答 3 问）。
