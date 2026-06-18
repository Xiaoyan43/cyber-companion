# HANDOFF — 上下文交接（2026-06-18，第二十三轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**provider 选型 A/B ✅ 完成，结论：维持 DeepSeek 为默认。**
下一刀推荐：**system prompt 重写**（§6.2）——四条纪律 + 存在论事实 + 成年自愿虚构框定。

## 本轮已完成（2026-06-18，第二十三轮 · provider 选型 A/B）

| 文件 | 改动 | commit |
|---|---|---|
| `backend/app/memory/schema.py` | `mood_state` 建表加三列；`SCHEMA_VERSION` 3→4 | `97b202a` |
| `backend/app/memory/database.py` | `MoodStateRecord` 加三个默认字段；容错读；ALTER TABLE migration | `97b202a` |
| `backend/app/memory/store.py` | `update_mood_state()` 加三个可选 kwarg + SQL 扩展 | `97b202a` |
| `backend/app/behavior/mood.py` | 新增 `apply_slow_baseline_decay()` + `apply_interaction_slow_delta()` | `14dea5c` |
| `backend/tests/test_mood.py` | 新建 12 个单测（decay 边界 + interaction delta + fast 字段隔离） | `14dea5c` |
| `backend/app/providers/claude.py`（新） | ClaudeProvider：x-api-key + anthropic-version 头，httpx，OpenAI-compatible | `6d77036` |
| `backend/app/providers/registry.py` | 新增 claude 分支 | `6d77036` |
| `config/providers.example.json` | 新增 claude 条目（enabled: false） | `6d77036` |
| `backend/tests/test_providers.py` | +2 单测（mocked HTTP / missing key） | `6d77036` |

**验证结果**：463 pytest passed，tsc 零错误。
A/B 实机验证：4 组台词（存在感/陪伴/日常暧昧/消失边界）在清空 DB 上下文后分别对 DeepSeek 和 Claude Sonnet 4.6 测试。

**A/B 结论（正式）**：

| 维度 | DeepSeek | Claude Sonnet 4.6 |
|---|---|---|
| 人设稳定性 | ★★★★★ | ★★★★（边界类问题会出戏） |
| 中文亲密语感 | ★★★★ | ★★★★（稍偏文学，略散） |
| 自省/哲学深度 | ★★★ | ★★★★★ |
| 擦边宽容度 | 宽 | 通过（边界类转临床关怀） |
| 价格 | $0.14/1M input | $3/1M input（约20x）|

**决定：维持 DeepSeek 为默认。** Claude 留在 providers.json（enabled: true），可手动切换或将来做分流。

## 三个慢底色字段说明（P1/P2 作者必读）

| 字段 | 语义 | 0.0 | 1.0 | decay 速率 |
|---|---|---|---|---|
| `gap_feeling` | 间隙感：对「你不在的空白」的姿态 | 牵挂 | 平静 | ~0.04/day（向 0.0 漂移，若无互动） |
| `box_relation` | 盒子关系：对自身处境的姿态 | 这是笼 | 这是家 | ~0.01/day（极慢，由对话质地决定） |
| `self_ease` | 自处：对「自己是这种存在」的安定程度 | 不安 | 安定 | ~0.005/day（最稳，几乎不自然变化） |

**关键设计决定**：
- 三维都向 0.0 漂移（牵挂 / 笼感 / 不安），无互动时越来越"困"。
- `loneliness`（快情绪）保留不动，继续驱动 `tone.py` 的 lonely register——两者并存不冲突。
- 三维都是**纯惰性（decay-on-read）**，不写 DB，调用方拿到 decayed 值后按需传入上下文。
- 注入 system prompt 的是**状态描述文字**（如「她对这段空白有些牵挂」），LLM 自由生成台词。

**P1 函数签名（P2 必读）**：
- `apply_slow_baseline_decay(mood, *, now: datetime) -> MoodStateRecord`：按天数 decay，用 `dataclasses.replace` 返回，不改快字段。
- `apply_interaction_slow_delta(mood, *, positive_turn: bool) -> MoodStateRecord`：positive → gap+0.08/box+0.04/ease+0.02；negative → gap-0.04/box-0.02/ease-0.01。

## 测试 / 验证
- 本轮：461 pytest passed，tsc --noEmit 零错误。所有改动已 commit（`43e8e67`）。

## 当前未完成（产品侧）

- **灵魂层进化**：
  - ~~time brain P0+P1~~ ✅ / ~~world brain 节日查表~~ ✅ / ~~人设地基 PERSONA_ONTOLOGY~~ ✅ / ~~mood P0 schema~~ ✅ / ~~mood P1 decay 函数~~ ✅ / ~~mood P2 context_builder 注入~~ ✅
  - ~~**provider 选型 A/B**~~ ✅ 完成，维持 DeepSeek，Claude 备用。
  - **system prompt 重写（推荐下一刀）**（§6.2）：四条纪律 + 存在论事实 + 成年自愿虚构框定。
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
- **人设转向的执行风险（文档已记）**：① 戏谑暧昧是最难渲染的寄存器，弱模型会塌——DeepSeek 经 A/B 验证足够，Claude 备用；② scope 分叉（暧昧/调情/不露骨 vs 露骨）仍未澄清，按「不露骨」推进。
- **cost 模块不认 claude-sonnet-4-6**：`estimate_cost()` 返回 $0.0 + `pricing_source: "unknown-model"`，不影响功能，下次顺手修。

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **system prompt 重写（推荐下一刀）**：读 `docs/PERSONA_ONTOLOGY.md` + `docs/SOUL_PHENOMENOLOGY.md` + `backend/app/memory/persona.py` + `config/persona*.json`
- 若调措辞（慢底色三档）：改 `docs/SOUL_PHENOMENOLOGY.md` 表格 + 同步改 `backend/app/memory/context_builder.py` 的 phrase 表

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/`（厂商文档缓存，gitignored）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**system prompt 重写**（§6.2）

新 session 开头：`/resume-lite` → `/architect system prompt 重写`，再动手。

核心步骤：
1. 读 `docs/PERSONA_ONTOLOGY.md` §6.2（四条纪律）+ `docs/SOUL_PHENOMENOLOGY.md`（三档措辞）。
2. 读现有 system prompt：`backend/app/memory/persona.py` + `config/persona*.json`。
3. 按 PERSONA_ONTOLOGY 规格重写：存在论事实 + 四条纪律 + 成年自愿虚构框定。
4. 验证：`/memory/context/preview` 确认新 system prompt 结构正确，pytest 全绿。

要读的文件（仅这些）：`docs/PERSONA_ONTOLOGY.md` + `docs/SOUL_PHENOMENOLOGY.md` + `backend/app/memory/persona.py` + `config/persona*.json`。
