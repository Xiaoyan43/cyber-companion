# VM-6 Spec — VikingDB 自定义 schema（Boxi 对齐的事件/画像 + 权重 + 衰减）`[Claude spec → 用户 console/API 应用 + Cursor 接代码 → Claude review]`

给纯 E2E 的火山长期记忆配**Boxi 对齐的自定义抽取规则**，取代目前的内置 `profile_v1`/`event_v1`，
让召回更贴人设、可加权、可衰减。母文档 `docs/VOICE_EMOTION_MEMORY_PLAN.md`；依据 `reference/06.md`（自定义 schema/算子/权重/衰减）、`reference/05.md`（控制台规则）、`reference/14.md`（`MemoryConfig`）。

> 定位：**SQLite 仍是 source of truth**；Viking 只在纯 E2E RTC 把长期记忆喂进 `system_role`。本切片只换"火山侧抽取什么、怎么排序"，不动 soul kernel / SQLite。

## 现状（已核实）
- 用内置类型：`backend/app/rtc/viking_memory.py` `DEFAULT_SEARCH_MEMORY_TYPES=("profile_v1","event_v1")`，runtime 注入默认只用 `profile_v1`。
- 画像消费：`_profile_line_from_hit` 读 `user_profile.基础信息.{昵称,常驻城市,职业规划}` → `【用户档案】…`；事件 → bullet 摘要（`_sort_hits_for_inject` 画像优先、事件按 time 倒序、过滤矛盾事件）。
- 写入：`build_add_session_body` → `AddSession`，`extract_memory_type=config.viking_memory_types`。
- 配置：`config.viking_memory_collection/project/types`（env `CYBER_COMPANION_VIKING_*`）。

## 设计

### A. 事件规则 `boxi_event`（CustomEventTypeSchemas）
抽取方法（Description，喂给抽取 LLM）：「从 Boxi 与用户的对话中，抽取对长期陪伴有价值的离散事件：用户的进展/挫折、情绪触发点、明确的计划或承诺、生活/求职/项目里的关键节点。忽略寒暄与一次性闲聊。」
Properties：
| PropertyName | 类型 | 说明 |
|---|---|---|
| summary | string | 事件来龙去脉（含人物/时间） |
| event_time | string | 事件发生时间 |
| topic | string | 类别：求职 / 情绪 / 生活 / 项目 / 关系 / 其它 |
| user_commitment | string | 用户说要做的事（无则空）——喂 PI 跟进/proactive |
| importance | float32 | 重要度 0–1（抽取时由 LLM 评分；"用户明确要求记住的"取高分）——用于权重表达式 |

### B. 画像规则 `boxi_profile`（CustomProfileTypeSchemas）
抽取方法：「维护对用户稳定、跨会话有用的画像：基础信息、求职档案、性格与沟通偏好、与 Boxi 的关系基调。只放稳定特征，不放一次性事件。」
更新时机=实时；更新方式=覆盖更新（在原画像演化）。Properties：
| PropertyName | 类型 | 说明 |
|---|---|---|
| basic_info | string | 昵称 / 常驻城市 / 职业 等基础信息 |
| job_search | string | 求职目标、进度、签证时钟等（Chris 的核心线） |
| personality_prefs | string | 性格、沟通偏好、什么话对他"管用"、雷区 |
| relationship_tone | string | 与 Boxi 的关系基调（信任/亲近/别扭的叙述） |

> 说明：放弃内置 `profile_v1` 的嵌套 `基础信息{…}` 结构，改扁平字段（自定义 schema 的 Properties 是扁平的）。代码消费端需相应改（见 D）。

### C. 权重 + 分数融合 + 衰减（`reference/06.md`）
- **事件权重**：选「按事件字段配置」，表达式 = `importance`（float32）。即重要事件检索分更高。
- **检索分数融合**（最终 = 向量×w + 时间衰减×w + 自定义×w）建议：向量 0.6 / 时间 0.25 / 事件 0.15 起步，按手感调。
- **无衰减期**（`no_decay_period`）：近 14 天事件不衰减（保住近期重要节点）；之后自然下降。
- 画像不衰减（稳定特征）。

### D. 代码改动（Cursor，最小）
1. `config.py`：`viking_memory_types` 默认/env 改为 `("boxi_profile","boxi_event")`；runtime 注入类型默认 `("boxi_profile",)`（对应原 `profile_v1` only）。保留 env 覆盖，便于回退到内置。
2. `viking_memory.py`：
   - `_sort_hits_for_inject` / `format_memories_for_system_role` 的 `memory_type` 判断 `profile_v1→boxi_profile`、`event_v1→boxi_event`（建议抽成常量，不要散落字符串）。
   - 画像解析改读扁平字段：`【用户档案】` 由 `basic_info`（+ 必要时 `job_search`）拼；昵称从 `basic_info` 文本里取（或新增可选 `nickname` 字段更稳）。
   - 矛盾事件过滤逻辑保留。
3. `voice_chat.py`：`MemoryConfig.filter.memory_type` 已读 `config.viking_memory_types`，自动跟随；确认 `Score` 阈值仍合理（默认 0.7，可按融合权重调）。
4. **不改** SQLite / soul kernel / behavior 契约。

### E. 应用方式（用户侧，二选一）
- **(推荐) 新建一个 collection**（如 `boxi_v2`）配自定义 schema → env 切过去。好处：不动现有 `profile_v1/event_v1` 数据，可随时回退；坏处：旧记忆不带过来（可重新 AddSession 灌历史）。
- 或 **`UpdateCollection`** 给现 collection 追加自定义类型（`reference/06.md`）。注意首次写入 **3–5 分钟建索引**，期间检索报 `1000023` → 需重试。
- 控制台配法见 `reference/05.md`；API 配法（`CustomEventTypeSchemas/CustomProfileTypeSchemas` + `AggregateExpression`）见 `reference/06.md`。**鉴权 + console 操作归用户**（Claude 不接触账号）。

## Done criteria
- console/API 里建好 `boxi_event`+`boxi_profile`（字段如上）+ 事件权重表达式 `importance` + 融合权重 + 14 天无衰减期。
- 代码切到自定义类型，`/rtc/status` 的 `viking_memory_enabled` 仍 true；system_role 注入正常（画像优先、事件加权倒序）。
- 跨会话召回 **用户实机 PASS**（昵称/城市/求职进度/承诺 至少各验一条）。
- 回退路径在：env 改回 `profile_v1,event_v1` 即恢复。
- `npm run check` 绿（解析改动加单测：扁平画像 → `【用户档案】`、事件加权排序、类型常量映射）。

## 边界 / 决策点（用户可调）
- 字段集是**建议**，用户在 console 应用时可增删（如加 `nickname`、拆求职为独立事件类型）。
- 不动 SQLite source of truth；Viking 只喂 RTC `system_role`；不破 VM-1…5。
- collection 策略（新建 vs Update）由用户定；推荐新建可回退。
- 真机鉴权 / 控制台 / IAM 授权（`VoiceChatRoleForRTC` + `MLPlatformVikingDBFullAccess`/`VikingdbFullAccess`，见 `reference/14.md`）归用户。
