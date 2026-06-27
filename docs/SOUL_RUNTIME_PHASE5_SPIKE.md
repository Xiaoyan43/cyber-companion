# Soul Runtime Phase 5 — Memory Backend Spike 决策

> 状态：**implemented spike**（非 production 接入）  
> 分支：`codex/soul-runtime`  
> 检查日期：**2026-06-27**

---

## 1. 本阶段做了什么

在 `backend/app/memory/adapters/` 新增**隔离**的 candidate 层：

| 模块 | 作用 |
|---|---|
| `contract.py` | 窄 DTO + `CandidateMemoryBackend` 协议 + `CandidateMemoryCapabilities` |
| `mem0_candidate.py` | Mem0 对照 adapter（injected client；`search(..., filters={"user_id": ...})`） |
| `letta_candidate.py` | Letta memory blocks CRUD spike（**不**调用 agent/message API） |
| `shadow.py` | `ShadowMemoryPort`：canonical 仍走 `SQLiteMemoryPort`，仅镜像 `MemoryRecord` |

**未接入**：`ports_from_store`、runtime 主链路、feature flag、schema migration。

---

## 2. 当前宽 `MemoryPort` 的结构性限制

Phase 2 接受的 `MemoryPort`（`backend/app/soul/ports.py`）把以下职责绑在同一接口：

- behavior 决策（`decide_user_message`）
- LLM budget gate（`check_llm_budget`）
- provider context 装配（`build_context` → `context_builder` + 本地 `rank_memories`）
- chat persistence（`persist_turn`）
- turn memory write policy（`record_turn_memories`）
- summary / LLM turn accounting（`maybe_update_summary`、`note_llm_turn`）

**没有独立 `retrieve()` seam**。检索发生在 `build_context` 内部，经由 SQLite `MemoryStore.list_memories` + `retrieval.rank_memories`，不是可插拔的后端调用。

因此：

1. Letta/Mem0 **不能**在 Phase 5 假装完整替换 SQLite。
2. candidate 只能映射 **durable fact 子集**（type/content/tags/importance/confidence/source_message_id/metadata）。
3. 任何 future backend 切换必须先 **拆窄 MemoryPort** 或增加独立 `MemoryRetrievalPort`，再谈 canonical 替换。

---

## 3. Letta 与 Soul Runtime 的边界冲突

| Letta 模型 | Soul Runtime 需求 | 冲突 |
|---|---|---|
| Agent + memory blocks + tool loop | `SoulTurnRuntime` 已是唯一回合编排 | Letta agent/message API **不得**接管 soul loop |
| Block = label/value 文档 | typed facts + importance/confidence + honest constraints | 无等价 semantic ranking；block 更像 persona scratchpad |
| 内建 retrieval 绑 agent 上下文 | `build_context` 需要 budget/token 感知的 rank | spike 明确 `scoped_search=False`、`semantic_search=False` |

**Phase 5 结论**：Letta memory blocks 可作为 **对照/实验性镜像**（`ShadowMemoryPort`），但不具备成为 canonical memory backend 的条件，除非接受 Letta 的 agent 范式或大幅改写 Soul 层。

官方资料（检查 2026-06-27）：

- https://docs.letta.com/
- https://github.com/letta-ai/letta
- 许可证：**Apache-2.0**（GitHub `LICENSE` 文件，2026-06-27 目视确认）

---

## 4. Mem0 是否更适合作为后续可选 memory backend

| 维度 | Mem0 | Letta blocks |
|---|---|---|
| scoped write/search/delete/export | ✅ candidate 已实现 | write/delete/export ✅；search ❌ |
| `user_id` namespace 隔离 | ✅ `filters={"user_id": ...}` | namespace 靠 block label/metadata 约定 |
| semantic search | ✅（Mem0 向量检索） | ❌ unsupported |
| 与现有 `MemoryRecord` 字段对齐 | metadata 映射可行 | block value 可存 content，type 进 metadata |
| soul loop 侵入 | 无（仅 memory API） | 无（本 spike 禁用 agent/message） |
| 提取/消解哲学 | 偏通用助手记忆 | 偏 agent 状态块 |

**Phase 5 结论**：Mem0 **更适合**作为后续 *可选* memory backend 对照（若产品接受外部向量化与其中立提取调性）。Letta 保留 architecture 学习价值，但不优先于 Mem0 做 backend 实验。

官方资料（检查 2026-06-27）：

- https://docs.mem0.ai/
- https://github.com/mem0ai/mem0
- 许可证：**Apache-2.0**（GitHub `LICENSE` 文件，2026-06-27 目视确认）

---

## 5. Candidate 能力矩阵

| Capability | SQLite canonical | Mem0 candidate | Letta candidate |
|---|---|---|---|
| scoped_write | ✅ (via write_policy) | ✅ | ✅ (block create/update) |
| scoped_search | ✅ (rank_memories in build_context) | ✅ `filters={"user_id"}` | ❌ `UnsupportedCandidateCapability` |
| delete | ✅ | ✅ | ✅ (block delete) |
| export/list | ✅ | ✅ `get_all(user_id=...)` | ✅ `list_blocks` + namespace filter |
| semantic_search | ✅ (local rank) | ✅ (Mem0 backend) | ❌ |
| behavior/budget/context/persistence | ✅ MemoryPort | ❌ out of scope | ❌ out of scope |

---

## 6. Production 接入状态

**无 production 接入。**

- `ShadowMemoryPort` 仅供 spike / 测试构造。
- 未修改 `ports_from_store`、`SoulTurnRuntime` 默认构造路径。
- 无 env flag、无依赖安装、无网络调用。

---

## 7. Schema / migration

**无。** SQLite schema 与 `MemoryStore` 内部未改动。

---

## 8. Rollback

删除以下新增路径即可完全回退 Phase 5：

- `backend/app/memory/adapters/`
- `backend/tests/test_memory_adapter_contract.py`
- `docs/SOUL_RUNTIME_PHASE5_SPIKE.md`

无需 DB rollback。

---

## 9. 未解决的契约缺口（留 Phase 6+ / MemoryPort 拆分）

1. **独立 retrieve seam**：candidate search 无法接入 `build_context` 而不改 MemoryPort。
2. **Memory 消解/UPDATE/DELETE 语义**：Mem0 有 ADD/UPDATE/DELETE；当前 SQLite `write_policy` 规则未映射到 candidate。
3. **expires_at / anti-fabrication**：candidate DTO 暂未建模 TTL 与诚实约束 enforcement。
4. **Summary + chat message canonical**：仍在 SQLite；candidate 镜像仅 cover `record_turn_memories` 产出。
5. **Shadow 诊断**：仅记录 error_type/backend/namespace/count；无 metrics pipeline。
6. **Letta block 与 typed MEMORY_TYPES**：一对多 block vs 多 fact 行的映射策略未定型。

---

## 10. 测试证据

离线 fake client 测试：`backend/tests/test_memory_adapter_contract.py`

- Mem0 字段映射 + `user_id` namespace 隔离
- Mem0 `search` 使用 `filters={"user_id": ...}`
- Letta blocks CRUD；`search` 显式 unsupported；未调用 agent/message stub
- `ShadowMemoryPort` 不改变 kernel/memory/message count/LLM accounting
- candidate 异常时 SQLite canonical commit 仍成功

回归（2026-06-27 本地）：

- `pytest backend/tests/test_memory_adapter_contract.py backend/tests/test_soul_ports.py backend/tests/test_soul_turn_contract.py` → **13 passed**
- `pytest -m invariant` → **358 passed**（+7 来自 `test_memory*` 前缀自动打标）
- `pytest backend/tests` → **731 passed**
