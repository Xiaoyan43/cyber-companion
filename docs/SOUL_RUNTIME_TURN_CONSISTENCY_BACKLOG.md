# Soul Runtime — Turn Consistency Backlog

> **状态**：计划 / backlog（非 implementation checkpoint）。  
> **架构缺口来源**：`docs/SOUL_RUNTIME_ARCH.md` §5 — 4 个 surface「同输入 → 同 kernel/memory 副作用」契约测试。  
> **进度真相源**：`docs/SOUL_RUNTIME_STATUS.md` · **稳定化上下文**：`docs/SOUL_RUNTIME_STABILIZATION.md`  
> 最后更新：**2026-06-27** · Post-merge 稳定化 P1-5

本文件记录 **turn 一致性** 的已覆盖范围、仍开放缺口、按优先级排序的 backlog，以及第一个可实施测试任务。**不宣称缺口已补完**；实现留后续 session。

---

## 1. 契约定义（ARCH §3 / §5）

**核心断言**：在固定 provider 回复（含 `<<<BOXI_SIGNALS>>>` trailer）与固定 budget 下，各 surface 对 **durable soul state** 的副作用必须一致：

| 副作用维度 | 包含 | 通常排除（合法 surface 差异） |
|---|---|---|
| **Kernel** | mood 标量、relationship 标量（`apply_signals` 结果） | `last_meaningful_interaction_at` 等时间戳字段（测试中 snapshot 时规避或归一化） |
| **Memory** | `list_memories` 行（type/content/importance/confidence/tags/source_message_id） | assistant **消息正文**（text 带 tagger、voice 纯文本） |
| **Chat persistence** | `count_chat_messages`、LLM-turn 计数 | 流式 delta 形态、SSE 帧顺序 |
| **Event log** | `turn.committed` append、`payload` 语义字段 | `payload.surface` 字面量（`text` / `text_stream` / `pipecat` / `rtc_off_path`） |

**合法差异（binding，决策 6 + Phase 1 约束）**：

1. **Streaming transport**：text stream / Pipecat 的 `yield delta` 与 HTTP 同步收集形态不同；契约比的是 **commit 之后** 的 durable 状态，不比 chunk 时序。
2. **Voice-mode instruction**：Pipecat `CompanionBrain` 在 provider 请求中追加 `VOICE_MODE_INSTRUCTION` system message；契约用 **固定 mock provider**（忽略 prompt 差异），只比 commit 段副作用。
3. **RTC 不走完整 `run_turn`**：live transport 不执行 §3 步骤 5–8；仅 off-path `turn_analyzer.analyze_turn` → `SoulTurnRuntime.commit_turn(surface="rtc_off_path")` 须与主 runtime commit 语义对齐。
4. **表达层输出**：text surface 经 `tag_reply_by_sentence`；Pipecat spoken path 为 plain text + 下游 tagger。不比 persisted assistant `content` 字符串。
5. **Off-path appraisal 输入**：RTC analyzer 用独立 LLM 拉 signals；与主链「同输入」契约应固定 **同一 signals dict 注入 commit**，而非强求同 prompt。

---

## 2. 四个 Surface 与代码入口

| Surface | Adapter 入口 | Runtime 路径 | Event `payload.surface` |
|---|---|---|---|
| **Text sync** | `main.py` `/chat/complete` | `SoulTurnRuntime.run_turn` | `text` |
| **Text stream** | `main.py` `/chat/stream` → `finalize_streamed_turn` | `run_turn` 流式 + inline commit | `text_stream` |
| **Pipecat** | `CompanionBrain.stream_turn` + `remember` | LLM 在 brain；持久化 `commit_turn` | `pipecat`（默认） |
| **RTC off-path** | `turn_analyzer.analyze_turn` | 仅 `commit_turn`（决策 6） | `rtc_off_path` |

参考实现：`backend/app/soul/runtime.py`（`run_turn` · `finalize_streamed_turn` · `commit_turn` · `_append_turn_event`）。

---

## 3. 当前已覆盖的测试

### 3.1 Text sync（`surface=text`）

| 测试文件 | 覆盖内容 | 缺口 |
|---|---|---|
| `backend/tests/test_soul_turn_contract.py` | `_run_text` → `run_turn`；与 Pipecat 路径比 kernel / memory / message count / LLM-turn 计数（LLM 与 local 两用例） | 未断言 `soul_events`；未与 text stream 比 |
| `backend/tests/test_soul_ports.py` | fake ports 本地回合 `turn.committed` payload 字段（`surface=text`） | 非 cross-surface；用 fake port 非 SQLite 全链 |
| `backend/tests/test_chat_complete*.py`（若存在） | HTTP 行为、预算门 | 非 kernel/memory 契约 |

### 3.2 Text stream（`surface=text_stream`）

| 测试文件 | 覆盖内容 | 缺口 |
|---|---|---|
| `backend/tests/test_chat_stream.py` | SSE 帧、`done` 事件、budget block 流式回复 | **无** 与 text sync 的 kernel/memory/event  parity |
| `backend/tests/test_soul_turn_contract.py` | — | **未覆盖** stream surface |

### 3.3 Pipecat（`CompanionBrain` → `commit_turn`）

| 测试文件 | 覆盖内容 | 缺口 |
|---|---|---|
| `backend/tests/test_soul_turn_contract.py` | `_run_voice`：`stream_turn` + `remember`；与 text 比 kernel/memory/计数 | 未单独断言 `commit_turn`；**未断言** `turn.committed`；未测 `remember` 与 `run_turn` 在 **同一 DB 事件+log** 级等价 |
| `backend/tests/test_companion_brain.py` | voice instruction、delta 剥 signal trailer、truncation、local silent | 行为/transport 测试，非 turn 一致性契约 |
| `backend/tests/test_soul_events.py` | store 层 append/tail；示例 payload 含 `surface=pipecat` | **合成数据**，非 runtime 写入路径 |

### 3.4 RTC off-path（`surface=rtc_off_path`）

| 测试文件 | 覆盖内容 | 缺口 |
|---|---|---|
| `backend/tests/test_turn_analyzer.py` | signals 成功 → relationship + memory；provider/parse 失败 → transcript only；disabled/blank；streak 跨 surface | **未断言** `soul_events` / `turn.committed`；**未与** text/Pipecat commit 比同 signals 副作用 |
| `backend/tests/test_rtc_turn.py` | RTC 路由 `_run_turn_analysis`、TTS context 注入 | transport 层，非 soul commit 契约 |

### 3.5 跨 surface 小结

```
已证明（部分）：
  text sync  ←→  Pipecat commit   kernel + memory + counts  (test_soul_turn_contract)

仍开放：
  text sync  ←→  text stream       durable 副作用
  text/Pipecat ←→  rtc_off_path   同 signals → 同 commit 副作用 + event log
  各 surface                     turn.committed payload 契约（除 fake-port 单测）
  budget_block / local_outcome    错误 signals 不写入
```

---

## 4. 缺口定义（ARCH §5 仍开放）

| # | 缺口 | 说明 |
|---|---|---|
| G1 | **Pipecat commit 契约不完整** | 现有 contract 比的是 text `run_turn` vs voice 全路径，但未验证 `commit_turn` 写入的 **event log** 与 text 路径字段级一致（除 `surface`）。 |
| G2 | **RTC off-path 无 event-log 契约** | `analyze_turn` 已走 `commit_turn`，但测试未 tail `soul_events` 或对比 payload。 |
| G3 | **Text sync vs stream 无 parity** | `finalize_streamed_turn` 与 `run_turn` 应产生相同 kernel/memory；无专门测试。 |
| G4 | **Local / budget_block 路径** | 低价值输入与 spend gate 命中时，须证明 **不** 写入 signal-driven memory、**不** 误标 `called_llm`、event payload 正确。 |
| G5 | **Future hardware** | 尚无 adapter 契约模板。 |

**不纳入本 backlog 的范围**（明确允许差异）：

- Fish Audio / 真实 Pipecat pipeline / RTC live WebSocket transport。
- Prompt 形状（voice instruction、RTC join-time `state_block`）。
- Assistant 可见文案（tagger vs plain）。

---

## 5. Backlog 清单

### P0-1 — Pipecat `commit_turn` consistency（无真实音频）

| 字段 | 内容 |
|---|---|
| **目标** | 固定 user_input + 固定 provider 原始回复下，`CompanionBrain.stream_turn` + `remember` 产生的 kernel / memory / message count / LLM-turn 计数 / `turn.committed` payload（规范化后）与 `SoulTurnRuntime.run_turn(surface="text")` 一致。 |
| **建议测试文件** | `backend/tests/test_soul_turn_contract.py`（扩展）或 `backend/tests/test_pipecat_commit_contract.py` |
| **Fake / stub 策略** | `_FixedReplyProvider`（已有）；`CYBER_COMPANION_PROVIDER_MODE=mock`；**不** 实例化 Pipecat transport / Fish TTS；直接驱动 `CompanionBrain`，mock `complete_stream`。 |
| **允许差异** | `payload.surface`：`text` vs `pipecat`；persisted assistant `content`（tagged vs plain）；无 audio 帧。 |
| **验收标准** | ① `_assert_side_effects_match` 扩展为含 event log（见 P0-1 helper）；② `tail_soul_events(kinds={"turn.committed"})` 各 1 条；③ 除 `surface` 外 payload 键一致（`called_llm`、`decision`、`has_signals`、`message_ids` 长度等）；④ `pytest backend/tests/test_soul_turn_contract.py` 绿；⑤ invariant 353 + backend 725 不回归。 |

---

### P0-2 — RTC off-path `surface=rtc_off_path` event-log + memory 契约

| 字段 | 内容 |
|---|---|
| **目标** | `turn_analyzer.analyze_turn` 在固定 signals 下：`commit_turn(surface="rtc_off_path")` 写入的 kernel / memory / chat messages / `turn.committed` 与 **同 signals 直接调用** `SoulTurnRuntime.commit_turn(..., surface="rtc_off_path", apply_signals=True)` 等价；并证明 event 确实 append。 |
| **建议测试文件** | `backend/tests/test_turn_analyzer.py`（扩展）+ 可选 `test_soul_turn_contract.py` 共享 snapshot helper |
| **Fake / stub 策略** | `_install_analyze_provider(_signals_payload())`（已有）；隔离 `tmp_path` SQLite；`enable_reflection=False` 避免 off-path 噪音。 |
| **允许差异** | assistant metadata `provider=doubao_realtime`（RTC  transcript 标记）；analyzer LLM 调用次数（契约固定 signals 结果后比 commit）；`payload.surface=rtc_off_path`。 |
| **验收标准** | ① analyze 后 `tail_soul_events` 含 1 条 `turn.committed`，`surface=rtc_off_path`；② kernel/memory snapshot 与 golden `commit_turn` 路径一致；③ provider 失败时 **无** event 或 `called_llm`/signals 语义与现有「transcript only」测试一致（不新增矛盾断言）；④ 全文件绿。 |

---

### P1-1 — Text sync vs text stream side-effect parity

| 字段 | 内容 |
|---|---|
| **目标** | 同一 `PerceivedEvent` + 同一 mock 流式回复下，`run_turn(surface="text")` 与 `finalize_streamed_turn`（或 `/chat/stream` 薄壳调用的 runtime 方法）commit 后 kernel / memory / counts / event 语义一致。 |
| **建议测试文件** | `backend/tests/test_soul_turn_contract.py` |
| **Fake / stub 策略** | `_FixedReplyProvider.complete` + `.complete_stream` 同 raw；独立 `tmp_path` DB 各一条路径。 |
| **允许差异** | `payload.surface`：`text` vs `text_stream`；无 SSE 帧断言。 |
| **验收标准** | ① 新增 `test_stream_turn_side_effects_match_text_sync`（名可调整）；② snapshot helpers 复用 §3.1；③ LLM 与 local 各至少 1 用例（stream local 可走 empty/low_value）。 |

---

### P1-2 — Budget block / local outcome 不写错误 signals

| 字段 | 内容 |
|---|---|
| **目标** | `evaluate_behavior` → local path，与 `evaluate_llm_budget_gate` → budget_block path：不产生 signal-driven memory；`called_llm=false`；kernel 仅反映 local 决策预期（或无 `apply_signals`）；event `has_signals=false`。 |
| **建议测试文件** | `backend/tests/test_soul_turn_contract.py` 或 `backend/tests/test_soul_turn_local_budget.py` |
| **Fake / stub 策略** | local：`user_input="嗯"`（已有）；budget block：`BudgetConfig(daily_llm_turn_limit=0)` 或 monkeypatch `check_llm_budget`；**不** 依赖真实 spend 数据。 |
| **允许差异** | local 回复文案因 surface 略异可接受；不比 content。 |
| **验收标准** | ① text + Pipecat（至少一条）同路径断言；② `list_memories` 无 signal 写入；③ `count_llm_turns_since` 不增加；④ event payload `called_llm is False`；⑤ 与 `test_chat_stream_budget_block` 行为不矛盾。 |

---

### P2-1 — Future hardware adapter contract template

| 字段 | 内容 |
|---|---|
| **目标** | 为未实现的 hardware input adapter 预留 **与 Pipecat 同形** 的契约：adapter 负责 `PerceivedEvent` + 可选 transport；soul 副作用只通过 `run_turn` 或 `commit_turn`。 |
| **建议测试文件** | `backend/tests/test_hardware_turn_contract.py`（占位，`pytest.mark.skip` 直至有 adapter） |
| **Fake / stub 策略** | 复制 P0-1 的 `_FixedReplyProvider` + snapshot helpers；`surface="hardware_stub"`。 |
| **允许差异** | transport 二进制帧、设备元数据进 `PerceivedEvent.metadata`；`payload.surface` 字面量。 |
| **验收标准** | ① 文档化 checklist（本 item）；② 占位测试 skip 理由明确；③ 实现 hardware 时取消 skip 并满足与 P0-1 同级的 snapshot 断言。 |

---

## 6. 建议实施顺序

```
P0-1  Pipecat commit + event log     ← 第一个可实施（见 §7）
P0-2  RTC off-path event + commit
P1-1  text sync ↔ stream
P1-2  local / budget_block 防污染
P2-1  hardware 模板（仅在有 adapter 时落地）
```

每条实现后：跑 `pytest -m invariant`（≥353）+ `pytest backend/tests`（≥725）；**不** 抬高 accepted implementation HEAD（纯测试 commit 由用户 review 后接受）。

---

## 7. 下一步第一个可实施测试任务（不实现）

**任务 ID**：`TC-P0-1`  
**标题**：扩展 Pipecat commit consistency — 含 `turn.committed` event-log 断言

**范围**：

1. 在 `test_soul_turn_contract.py` 增加 `_event_snapshot(store)`：tail 最后一条 `turn.committed`，strip/忽略 `surface` 与不稳定 id/timestamp。
2. 扩展 `test_llm_turn_side_effects_match_across_surfaces`（或新增并列测试）：在现有 kernel/memory 断言后，断言 text 与 voice 各写入 1 条 event，且规范化 payload 相等。
3. 可选加强：直接对 `voice_store` 断言 `payload.surface == "pipecat"`、`text_store` 为 `"text"`。

**不在此任务内**：text stream parity（P1-1）、RTC（P0-2）、真实 Pipecat pipeline。

**预估 touch**：仅 `backend/tests/test_soul_turn_contract.py`（+ 若 helper 共享则不改 production 代码）。

---

## 8. 相关文档

| 文件 | 用途 |
|---|---|
| `docs/SOUL_RUNTIME_ARCH.md` | §3 回合步骤、§5 invariant 缺口 |
| `docs/SOUL_RUNTIME_STABILIZATION.md` | Post-merge P1-5 稳定化索引 |
| `docs/SOUL_RUNTIME_STATUS.md` | 测试基线、路线选择 |
