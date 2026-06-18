# HANDOFF — 上下文交接（2026-06-18，第十七轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**灵魂层进化（第一刀已落）**：time brain P0+P1 完成（注入新西兰当前时间 + recent_event 相对时间前缀）。下一刀候选：world brain 节日查表 / emotion 慢情绪 decay-on-read / 信笺 UI P2。

## 本轮已完成（2026-06-18，第十七轮）

| commit | 内容 |
|---|---|
| `16d1b74` | feat(soul): time brain P0+P1 — 注入新西兰时间 + recent_event 相对时间前缀 |

### P0 · 注入当前时间（`context_builder.py`）
- `_format_time_block()`：每次构建上下文时，把新西兰本地时间（`Pacific/Auckland`）格式化为 `[Time]\n现在是 YYYY年M月D日 周X HH:MM（新西兰时间）` 注入 system prompt（排在 persona 之后、mood 之前）。
- LLM 现在每轮都知道精确时间 / 星期几。

### P1 · recent_event 相对时间前缀（`context_builder.py`）
- `_relative_time(created_at_iso, now)`：把 UTC ISO 字符串转换成"今天/昨天/N天前/N周前/N个月前"（按新西兰日期计算，容忍 SQLite 空格格式）。
- `_format_memories_block` 加 `now: datetime | None` 可选参数；仅对 `type='recent_event'` 的记忆加时间前缀，其他类型不变。
- `build_provider_context` 传入 `now_nz = datetime.now(_NZ_TZ)`。

### 测试
- 新增 5 条单测（`test_format_time_block_contains_nz_time_fields` / `test_context_builder_system_message_contains_time_block` / `test_relative_time_labels` / `test_format_memories_block_recent_event_gets_time_prefix` / `test_format_memories_block_stable_profile_no_time_prefix`）
- 全量 backend：**440 passed**，12 warnings，0 failures。

## 已修改文件 + 改动摘要（本轮）

| 文件 | 改动 | 说明 |
|---|---|---|
| `backend/app/memory/context_builder.py` | +57 行 | `ZoneInfo` import、`_NZ_TZ`/`_WEEKDAYS_CN` 常量、`_format_time_block()`、`_relative_time()`、`_format_memories_block` 加 now 参数、`build_provider_context` 加 `now_nz` + 调用点更新 |
| `backend/tests/test_context_builder.py` | +67 行 | `datetime`/`timezone` import、新 exports import、5 条新测试 |

## 当前未完成（产品侧）

- **灵魂层进化 · time brain 后续**：
  - **P0-P1 完成**（已 commit `16d1b74`）
  - **P2（time brain）**：world brain 节日查表（近免费，无 API 依赖）
  - **P3（time brain）**：recent_event `created_at` 与"事件发生时间"是否一致尚未核实——当前是写入时间，不影响 P0/P1 功能，但如需精准"事件时间"需新增字段（低优）
  - **emotion · 慢情绪 + decay-on-read**（第一档，后续做）
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。**下次发现失忆当场验证**，不主动排查。
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档。
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107。

## 已知 bug / 风险

- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。
- **记忆消解缺口（怀疑，未验证）**：记忆可能只追加、不消解矛盾 → 疑似 R11 失忆根因。等下次失忆复现时连同 R11 一起验。
- **Pipecat 记忆写回**：`CompanionBrain` 写 SQLite，但语音轮次 off-path 反思（`analyze_turn`）是否与 RTC 路径等价未确认。如发现记忆遗漏，查 `companion_brain.py` 的 `persist_chat_turn` 调用链。
- **时区说明**：`recent_event` 的 `created_at` 是 UTC 写入时间（不是"事件发生时间"），相对时间前缀按新西兰日期计算。绝大多数场景无影响；如未来需精准事件时间，需加 `occurred_at` 字段。

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **world brain · 节日查表**（推荐）：读 `backend/app/memory/context_builder.py`（确认注入位置）
- 若做 **emotion · 慢情绪 decay-on-read**：读 `backend/app/behavior/mood.py` + `backend/app/memory/store.py`
- 若做 **P2 信笺 UI**：读 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` + `frontend/src/letter/LetterView.tsx`
- 若做 **记忆消解 / R11**：读 `backend/app/memory/write_policy.py` + `backend/app/rtc/viking_memory.py`
- 若做 **延迟诊断 / 换 LLM**：读 `backend/app/providers/registry.py` + `config/providers.json`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/`（厂商文档缓存，gitignored）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**world brain · 节日查表**（近免费，无 API 依赖）：新建一个中国/新西兰节假日静态表（JSON 或 Python dict），在 `_format_time_block()` 里判断今天是否有节日并追加一行（如"今天是端午节"）。改动范围仅 `context_builder.py` + 新增节日数据文件，diff 极小，立即提升"世界感"。

备选：**emotion · 慢情绪 decay-on-read**（多日基线漂移，读 mood.py 先评估改动规模）。
