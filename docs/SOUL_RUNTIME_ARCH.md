# Soul Runtime 架构（重构北极星）

> 状态：**目标架构 / 重构契约（Phase 0）**。本文件是 `codex/soul-runtime` 分支的源真相。
> 由 2026-06-27 的「全项目架构盘点 + Shared Soul Layer 重构准备」审查 + 用户 10 项拍板产生。
> 取代散落在各入口的回合编排；不改人格，只收敛结构。新 session 先读本文件 + `docs/ARCHITECTURE_V2.md`。
> **▶ Phase 1 已完成（text + Pipecat surfaces）。新 session 实施 Phase 2：见 §6 Phase 2 行 + §4 Ports 草案，只读 runtime 边界相关文件，不要全仓扫描。**

## 0. 北极星与范围

- **一个 `SoulRuntime`，所有 surface（text / Pipecat / RTC / future hardware）只是 adapter。**
- **memory / state / event-log / agenda / provider 都通过 ports 接入**，第一版实现仍是 SQLite。
- 目标不是改 Boxi 人格，而是把 text / Pipecat / RTC 里**重复 4 遍**的 soul-turn 编排收敛成一个核心 runtime。
- 不受现有代码束缚，但**增量、可回滚、small diff**；每 phase 测试绿才继续。

## 1. 已拍板决策（binding，2026-06-27）

| # | 决策 | 落地约束 |
|---|---|---|
| 1 | **接受 `backend/app/soul/` + `SoulTurnRuntime`** | 最高优先；4 个入口改薄壳调用它 |
| 2 | **引入 `MemoryPort` / `StatePort` / `EventLogPort`** | 第一版仍绑 SQLite；**不第一刀全仓改 24 文件** |
| 3 | **顺序：runtime → ports → event_log + open_loops** | Event Log/Agenda 是活人感核心，但必须先有 runtime seam |
| 4 | **拆 `mood_state`，但后置 + 先 deprecate 不删** | 无 migration framework → 新增表/列，旧列只读兼容一段时间 |
| 5 | **Letta 可 spike，排在 ports 之后；Mem0 仅对照** | 二者只能做 `MemoryPort` 后的 adapter 候选，**不接管 soul loop** |
| 6 | **RTC pure E2E 不并入主 SoulRuntime** | 保留为 fast fallback / transport experiment；只统一 off-path event 摄入 + memory/state 写回 + 最小观测 |
| 7 | **proactive 迁到 agenda/motivation，保留 longing/Poisson 作节奏闸** | open-loops/agenda 决定「为什么找你」，Poisson 决定「现在是否合适」 |
| 8 | **现在做轻量 persona 版本化** | 加 `persona_version` / `persona_profile_id` 元信息；不重写 Boxi |
| 9 | **前端视觉暂缓** | SoulRuntime 稳定前不开 PixiJS room；前端只做 debug panel / 验证 / 小 bugfix |
| 10 | **独立分支 `codex/soul-runtime`** | Phase 0 文档可小 commit；Phase 1/2 每阶段独立 commit，绿才继续 |

## 2. 目标分层

```
INPUT ADAPTERS    TextChat(HTTP) · Pipecat(frames) · RTC(subtitles) · ProactiveTick · (future)Hardware
       │  归一为 PerceivedEvent
PERCEPTION        behavior/rules.py: empty/low_value/rambling/overwhelmed/refused + 归一化
       │
┌─ SOUL RUNTIME (core) ──────────────────────────────────────────────────────┐
│  SoulTurnRuntime.run_turn(event) —— 唯一回合编排                              │
│   1 perceive → 2 motivation(应否回应/主动) → 3 retrieve → 4 assemble ctx      │
│   5 LLM orchestrate → 6 express → 7 commit(event-log+state+memory) → 8 schedule │
└───┬────────┬────────┬────────┬─────────┬─────────┬─────────┬─────────────────┘
 EventLog  State    Memory   Agenda   Motivation Expression  LLM Orchestrator
 (append)  (kernel) (facts)  /OpenLoops Policy    Policy(tone) (ctx+provider)
    └ Port ─┴─ Port ─┴─ Port: SQLite | (spike)Letta/Mem0/Viking/Postgres ┘
OUTPUT ADAPTERS   HTTP-SSE · Pipecat-TTS-frames · RTC-SetTTSContext · (future)Hardware
OFF-PATH WORKERS  Reflection(consolidate/link/impression/summary) · Observability/Eval
```

### 层职责 + 现有代码归属

| 层 | 职责 | 同步/off-path | 现有代码 |
|---|---|---|---|
| Input Adapters | HTTP/帧/字幕 → `PerceivedEvent` | sync | `main.py` 路由壳 · `companion_brain_processor` · `rtc/routes` |
| Perception | 解析输入信号 | sync | `behavior/rules.py`（已有） |
| **Soul Event Log** | append-only「发生过什么」 | 写 sync / 读 off-path | **新建**（Phase 3） |
| State Store (kernel) | momentary mood / slow relationship / existential baseline（**拆 3 概念**） | sync | `behavior/kernel.py` + 拆分后 `mood_state` |
| Memory Store | facts/summaries/links + 诚实约束 | retrieve sync / write off-path | `memory/store.py` 记忆部分 → `MemoryPort` |
| **Agenda / Open Loops** | 未了之事 / 未来事件 / 承诺跟进 | sync 读 / off-path 写 | **新建**（`reminders` 是雏形） |
| Motivation Policy | 应否回应 / 何时主动 / 为什么 | sync | `engine.py` + `longing` + `proactive_reason` |
| Expression Policy | felt-vs-shown → 各 surface 措辞 + Fish 标签 | sync | **`behavior/tone.py`（已是此层，保留）** + `expression_tagger` |
| LLM Orchestrator | 上下文装配 + provider + 解析 | sync | `context_builder` + `providers/*` + `parser` |
| Output Adapters | 回合结果 → 各 surface 输出 | sync | SSE / Pipecat TTS / RTC |
| Reflection Workers | consolidate/link/impression/summary | off-path | `reflection/*` |
| Observability/Eval | 密度/位置/延迟/turn 一致性 | off-path | `tts/tag_stats` + `scripts/tagger_eval`（待收拢） |

**关键事实**：text 与 Pipecat 走 `build_provider_context`（完整 persona+记忆注入）；**RTC 不走**——它用 join-time `state_block`+sqlite+viking。口吻层（`tone.py`）已统一，但上下文装配层目前分叉。决策 6：RTC 不强行并入，只统一 off-path 写回与观测。

## 3. SoulTurnRuntime 契约

替代当前 4 份重复实现：
- `main.py:/chat/complete`（[backend/app/main.py](../backend/app/main.py)）
- `main.py:_finalize_streamed_turn`（`/chat/stream`）
- `realtime/companion_brain.py:stream_turn`+`remember`
- `reflection/turn_analyzer.py:analyze_turn`（RTC off-path）

统一回合步骤（**行为必须与现有逐字节等价**，差异只允许出现在各 surface 的 streaming/back-task 形态）：

```
run_turn(event: PerceivedEvent) -> TurnOutcome:
  1 decision   = motivation.decide(event)              # evaluate_behavior
  2 if not decision.should_call_llm: return local_outcome(decision)
  3 gate       = usage_guard.gate(target_model)        # evaluate_llm_budget_gate
  4 if not gate.allowed: return budget_block_outcome(gate)
  5 context    = orchestrator.assemble(event, decision)# build_provider_context
  6 stream     = orchestrator.complete(context)        # provider.complete[_stream]
  7 parsed     = parser.parse(stream)                  # <<<BOXI_SIGNALS>>>
  8 expressed  = expression.render(parsed, surface)    # tone + expression_tagger
  9 commit:                                            # off-path-able
       state.apply_signals(parsed.signals)             # apply_signals_to_kernel
       memory.persist_turn(...)                        # persist_chat_turn
       memory.record_turn_memories(...)                # M2/M3
       memory.maybe_update_summary(...)
       event_log.append(turn_event)                    # Phase 3
  10 schedule.reflection_if_due()                      # off-path
```

Surface 差异通过 **adapter + `surface` 形参**表达，不是复制整条链：
- text/complete：同步收集后返回。
- text/stream + Pipecat：`yield` delta，`commit` 进 back-task。
- RTC：**不调用 `run_turn` 的 5–8 段**（决策 6），只复用第 9 段的 `commit`（off-path event/memory/state 写回）。

## 4. Ports 草案（Phase 2 落地；此处为设计签名，非实现）

> 第一版每个 Port 的唯一实现是包裹现有 `MemoryStore` 的 SQLite adapter。先在 runtime 边界定义接口，**不立刻改 24 个 import 点**。

```python
class StatePort(Protocol):           # kernel：mood / relationship / existential
    def get_mood(self) -> MoodState: ...
    def get_relationship(self) -> RelationshipState: ...
    def apply_signals(self, signals: dict | None) -> None: ...   # 唯一写口

class MemoryPort(Protocol):          # facts / summaries / links（诚实约束契约见 §5）
    def retrieve(self, query: str, *, budget) -> list[Memory]: ...
    def record_turn(self, *, user_input, signals, source_message_id, budget) -> None: ...
    def persist_turn(self, messages, result, *, decision, avatar_state) -> list[int]: ...
    def latest_summary(self) -> Summary | None: ...

class EventLogPort(Protocol):        # Phase 3：append-only
    def append(self, event: SoulEvent) -> None: ...
    def tail(self, *, kinds, limit) -> list[SoulEvent]: ...

class AgendaPort(Protocol):          # Phase 3：open loops / future events
    def open_loops(self, *, now) -> list[OpenLoop]: ...
    def upsert(self, loop: OpenLoop) -> None: ...
    def close(self, loop_id: int) -> None: ...
```

## 5. Invariants（重构必须守住的「验证过的行为」）

重构前把以下测试标为 **invariant suite**（`pytest -m invariant`），任何 phase 改动后必须全绿。

**角色连续性**（即使将来 Boxi 改向女友/伴侣方向）：人格版本化、不随机漂移、不编造关系经历、不退化成通用客服。
**记忆诚实约束**（`MemoryPort` 契约）：来源/类型/置信度/重要性；不发全历史；不编造（anti-fabrication note）；用户纠正可更新；敏感信息摘要化；可删除/导出；可换后端。
**表达**：felt-vs-shown（core 不撒谎、ink 是表演）、desync-1 抑制、desync-2 表演性逗、positive-zone streak、register→各 surface 自措辞。
**语音调参结论（写死，勿重测）**：`latency=balanced`、Fish `s2.1-pro`、`normalize=false`、`[break]` 系不必迁 `[pause]`、逐句标签 + 跨句去重。
**边界**：public/MIT、密钥只在 env/gitignored、不重写已发布历史。

invariant 测试清单（现有）：`test_tone` · `test_mood` · `test_behavior` · `test_memory*` · `test_reflection` · `test_relationship_state` · `test_rtc_state_block` · `test_expression_tagger*` · `test_proactive*` · `test_context_builder`。
**缺口（需新增）**：4 个 surface「同输入 → 同 kernel/memory 副作用」的 turn 一致性契约测试。

## 6. 迁移阶段（按决策调整后的顺序）

| Phase | scope | touched | risk | tests | rollback |
|---|---|---|---|---|---|
| **0 ✅** | 本文档 + invariants 标记 | docs | 无 | 标 `-m invariant` | 删 doc |
| **1 ✅** | 抽 `backend/app/soul/runtime.py`，3 个主链路入口改薄壳（text 非流式/流式 + Pipecat；turn_analyzer 按决策6延后） | main.py · companion_brain · 新 soul/ | 中（须等价） | 现有 4 路测试 + 新 turn 一致性契约 `test_soul_turn_contract` | runtime 是新增文件，壳层 revert |
| **2** | 定义 `MemoryPort/StatePort/EventLogPort`，SQLite adapter 包裹 `MemoryStore`；**只在 runtime 边界依赖接口** | soul/ + store adapter | 中 | 契约测试跑 `InMemoryFakeStore` | 接口默认绑 SQLite |
| **3** | `soul_events`（append-only）+ `open_loops`（reminders 升级） | schema(additive) · runtime commit · proactive_reason | 中 | event 写入 + open-loop 触发 | 表 additive，停写即无副作用 |
| **4** | 拆 `mood_state`：existential/计时器/死字段 `trust` 移出 | schema(additive) · kernel · mood · state_block | 中高 | §5 kernel/mood/tone invariant | **先 deprecate 不删**，旧列只读灰度 |
| **5** | `MemoryPort` 后做 Letta（spike）/ Mem0（对照）adapter | memory/adapters/* | 低（隔离） | 契约测试复用 | 删 adapter |
| **6** | proactive 迁 agenda/motivation，longing 留作节奏闸 | motivation policy · engine proactive 分支 | 中 | proactive 闸门 + agenda 触发 | feature flag 切回 longing |
| **7** | 清理：合并 turn_analyzer、退役/合并 soul_llm_server、统一语音换件 | main.py · rtc · realtime | 低 | 全 invariant | 单 commit revert |

并行的轻量项：persona 版本化（决策 8）可在 Phase 1–2 顺带加 `persona_version` 元信息；RTC（决策 6）在 Phase 7 决定归档/删除。

## 7. 待办 / 开放问题

- Phase 1 的 `PerceivedEvent` / `TurnOutcome` 具体字段：在 Phase 1 任务开始前定稿。
- turn 一致性契约测试如何在不跑真实音频的前提下覆盖 Pipecat 路径（用 fake transport / 直接测 `CompanionBrain` 而非全 pipeline）。
- RTC off-path 写回与主 runtime `commit` 的复用边界（决策 6）。

## 8. Phase 1 启动（next session · 冷启动自洽）

> **✅ Phase 1 COMPLETED**（commits `3562c33` · `7c263c1` · `17daf62` · `d69290e`）。
> Phase 1 completed for text + Pipecat surfaces; RTC pure E2E off-path analyzer
> intentionally deferred per decision 6. 子步骤 1-5 全绿，`backend/tests` 670 passed。
> 本 §8 以下内容保留作为 Phase 1 的实施记录；新 session 请转 Phase 2（§6 + §4）。

**状态**：Phase 0 已完成并 commit（`fb053c3`，仅本文档）。当前分支 `codex/soul-runtime`。
工作树有 32 项 Fish/tagger 实验残留（unstaged，**故意不提交**）——Phase 1 全程不要 stage 它们。

**Phase 1 目标**：抽出 `backend/app/soul/runtime.py` 的 `SoulTurnRuntime.run_turn()`，
把 §3 契约里重复 4 遍的回合编排收敛成一处，入口改薄壳。**行为逐字节等价。**

**用户拍板的 Phase 1 约束（binding）**：
1. 不碰 Fish/tagger/Pipecat 参数实验残留；不碰 `.env*`、`data/`、`experiments/`。
2. 不碰 RTC 主链路；`turn_analyzer` 最多复用 commit helper，**不并入完整 runtime**。
3. 不做 ports，不改 `MemoryStore`/`schema`——ports 留 Phase 2。
4. 实施顺序：**先 text non-stream → 再 text stream → 再 Pipecat `CompanionBrain`**。
5. 每一步跑对应测试，确认行为等价后再继续下一步。

**允许读取**：本文件 · `backend/app/main.py` · `backend/realtime/companion_brain.py` ·
`backend/app/behavior/{engine,parser,completion}.py` ·
`backend/app/memory/{context_builder,chat_persistence,write_policy,summary_policy,usage_guard}.py` ·
对应 `backend/tests/`。（`turn_analyzer.py` 仅为对照 commit 段，约束 2。）

**禁止触碰**：约束 1 的全部残留文件 · `backend/app/rtc/**` · `memory/schema.py` · `memory/store.py` · 前端。

**子步骤（每步独立 commit，测试绿才继续）**：
1. 定 `PerceivedEvent` / `TurnOutcome` 字段（先够 text 用），建 `backend/app/soul/__init__.py` + `runtime.py` 骨架。
2. text non-stream：`/chat/complete` 改薄壳调 `run_turn()`；跑 `test_chat_*` + `test_behavior` + `test_memory*`。
3. text stream：`/chat/stream` 的 `_finalize_streamed_turn` 收敛进 runtime；跑 `test_chat_stream` + `test_user_input_truncation`。
4. Pipecat：`companion_brain.stream_turn`+`remember` 改薄壳（保留 voice_mode 指令 + `truncated` 逻辑）；跑 `test_companion_brain`。
5. 新增「同输入 → 同 kernel/memory 副作用」turn 一致性契约测试（§5 缺口）。

**验收**：上述测试全绿 + `pytest backend/tests --co` 仍 668 + diff 不含禁止文件。

> 外部复用结论（详见审查报告 §9）：Pipecat 已采为 base；**Letta 唯一建议 spike（排 ports 之后）**；Generative Agents/Xiaoice/ElizaOS 仅学架构；Mem0 仅对照；Inworld/Convai/Hume EVI 不引入（违背 public/「soul 写每个字」）。
