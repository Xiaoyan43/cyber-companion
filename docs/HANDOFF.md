# HANDOFF — 上下文交接（2026-06-18，第十八轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**灵魂层进化**：time brain P0+P1 ✅ + world brain 节日查表 ✅。Boxi 现在有时间感知（精确时间+相对时间）和节日窗口感知（±3天历史/±7天预告，动态使用不强制播报）。下一刀候选：emotion 慢情绪 decay-on-read / 信笺 UI P2。

## 本轮已完成（2026-06-18，第十八轮）

| commit | 内容 |
|---|---|
| `16d1b74` | feat(soul): time brain P0+P1 — 注入新西兰时间 + recent_event 相对时间前缀 |
| (staged) | feat(soul): world brain · 节日查表 — ±3天历史/±7天预告窗口注入 |

### world brain · 节日查表

**设计核心**：不做"今天是X节"机器播报，而是给 Boxi 一个 ±N 天节日窗口让她自己决定要不要提、怎么提、什么时候提（提前预告 / 当天 / 事后回顾）。

- **新建 `backend/app/memory/holidays.py`**：
  - `_FIXED`：跨年公历固定节日（元旦/怀唐伊日/妇女节/劳动节/国庆/圣诞等 12 条）
  - `_LUNAR`：年份键农历+可变公历节日（2026: 春节/端午/中秋/复活节/马塔里基等 15 条）
  - `get_holiday_window(today, before_days=3, after_days=7) -> list[tuple[int, str]]`：返回 (delta_days, 节日名) 列表，delta 负=过去可回顾，0=今天，正=未来可预告

- **修改 `backend/app/memory/context_builder.py`**（`_format_time_block` 区域）：
  - 新增 `_DELTA_LABELS` 常量（named offset → 人类标签）
  - 新增 `_delta_to_label(delta)` → "昨天/前天/今天/明天/后天/N天后"
  - `_format_time_block()` 调用 `get_holiday_window`；窗口为空时输出纯时间行（无变化）；有节日时追加 `[近期节日（参考用，不必主动提及，可提前预告也可事后回顾）]` 段

- **system prompt 示例（端午节当天）**：
  ```
  [Time]
  现在是 2026年6月22日 周一 14:30（新西兰时间）
  [近期节日（参考用，不必主动提及，可提前预告也可事后回顾）]
  - 今天：端午节
  ```

- **system prompt 示例（端午节前2天）**：
  ```
  [Time]
  现在是 2026年6月20日 周六 10:00（新西兰时间）
  [近期节日（参考用，不必主动提及，可提前预告也可事后回顾）]
  - 后天：端午节
  ```

### 测试
- 新增 5 条测试（`test_get_holiday_window_returns_holiday_on_exact_day` / `test_get_holiday_window_returns_upcoming_holiday` / `test_format_time_block_includes_holiday_window_when_present` / `test_format_time_block_no_holiday_section_when_empty` / `test_delta_to_label_all_named_offsets`）
- 全量 backend：**445 passed**，12 warnings，0 failures。

## 已修改文件 + 改动摘要（本轮）

| 文件 | 改动 | 说明 |
|---|---|---|
| `backend/app/memory/holidays.py` | +60 行（新建） | 节日数据 + `get_holiday_window()` |
| `backend/app/memory/context_builder.py` | +22 行 | import、`_DELTA_LABELS`、`_delta_to_label()`、`_format_time_block()` 改写 |
| `backend/tests/test_context_builder.py` | +46 行 | 新 import + 5 条测试 |

## 当前未完成（产品侧）

- **灵魂层进化**：
  - ~~time brain P0+P1~~ ✅ / ~~world brain 节日查表~~ ✅
  - **emotion · 慢情绪 + decay-on-read**（第一档，后续做）
  - **world brain 后续**：world-天气API（第二档）/ 未来事件表（第二档）
  - **time brain P3（低优）**：recent_event `created_at` 是写入时间非事件时间，如需精准需加 `occurred_at` 字段
  - **节日表维护**：每年需人工补 `_LUNAR` 下一年条目（马塔里基日期尤其需查）
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
- 若做 **emotion · 慢情绪 decay-on-read**（推荐）：读 `backend/app/behavior/mood.py` + `backend/app/memory/store.py`
- 若做 **world brain 节日表扩充**（补年份/补马塔里基）：读 `backend/app/memory/holidays.py`
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

**emotion · 慢情绪 + decay-on-read**：在 `mood.py` 引入"多日基线漂移"时间尺度——快情绪（瞬时，现有）+ 慢基线（按天 decay-on-read 惰性求值）。改动范围：`mood.py` + `store.py`，需先读代码评估规模。

备选：**world brain 后续**（天气 API，需第三方 key）/ **信笺 UI P2**（需用户答 3 个问题）。
