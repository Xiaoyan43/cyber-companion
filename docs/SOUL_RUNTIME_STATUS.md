# Soul Runtime 跨 Session 状态

> **冷启动入口**：新 session 先读本文件 + `docs/SOUL_RUNTIME_ARCH.md`（架构契约）。
> 本文件记录**已验收进度**与**工作树禁区**；不替代 ARCH 的设计细节。

最后更新：**2026-06-27** · branch `codex/soul-runtime` · **Phase 0–6 accepted**

---

## 1. Git 指针

| 字段 | 值 |
|---|---|
| **branch** | `codex/soul-runtime` |
| **accepted implementation HEAD** | `e0b4f23` — `feat(soul): route proactive motivation through agenda`（Phase 6 代码/测试验收 checkpoint） |
| **status/doc branch tip** | `c223234` — 末条 Phase 6 状态对齐 docs（**纯 docs commit 不抬高 implementation checkpoint**） |

> **accepted implementation HEAD** = 最后验收通过的**代码/测试** commit；下一 session 冷启动与回归以它为基准。
> 其后仅更新本 STATUS/ARCH 的 docs commit（如 `c59ce2f`…`c223234`）**不算**新的 implementation checkpoint，无需循环改 SHA。
> 工作树有 dirty 文件时，**以 accepted implementation HEAD 为准**，不要假设 dirty 内容已落地。

---

## 2. 测试基线（accepted implementation @ `e0b4f23`）

| 套件 | 命令 | 结果 |
|---|---|---|
| **Phase 5 targeted** | `pytest backend/tests/test_memory_adapter_contract.py backend/tests/test_soul_ports.py backend/tests/test_soul_turn_contract.py` | **13 passed** |
| **invariant** | `pytest -m invariant` | **365 passed** |
| **backend 全量** | `pytest backend/tests` | **738 passed** |

invariant 入口：`pytest.ini` + `backend/tests/conftest.py`（collection hook 按 §5 文件名/前缀打标）。
详见 `docs/SOUL_RUNTIME_ARCH.md` §5。

---

## 3. Phase 0–5 进度与 commits

| Phase | 状态 | 关键 commits | 摘要 |
|---|---|---|---|
| **0** | ✅ accepted | `fb053c3` | Soul Runtime 架构文档 + 10 项拍板决策 |
| **1** | ✅ accepted | `3562c33` · `7c263c1` · `17daf62` · `d69290e` · `cd904cd` | 抽 `SoulTurnRuntime`；text 非流/流 + Pipecat 薄壳；turn 一致性契约测试 |
| **2** | ✅ accepted | `79e824b` · `429c41f` | `MemoryPort`/`StatePort`/`EventLogPort` + SQLite adapter @ runtime 边界 |
| **3A** | ✅ accepted | `a63301a` | append-only `soul_events`；runtime commit 写 `turn.committed` |
| **3B** | ✅ accepted | `6038447` · `be1a4fb` · `4c5bd21` · `c525de9` | `open_loops` + `AgendaPort`；due open_loop → proactive reason |
| **4** | ✅ accepted | `6518c14` · `40eb4c7` · `2d22e4f` | **4A** `existential_state` 拆分；**4B** `behavior_runtime_state` 拆分 + trust canonical |
| **4.5** | ✅ accepted | `1a625db` · `d6003f1` | 注册 `invariant` pytest marker；351 条可 `-m invariant` 运行 |
| **5** | ✅ accepted | `72d3076` · `90ddedb` | 隔离 Mem0/Letta candidate adapter spike；SQLite canonical 不变；无 schema/runtime 接入 |
| **6** | ✅ accepted | `e0b4f23` | proactive 迁 `motivation.py`：`agenda` 模式 due/overdue open_loop 等为 reason 来源；longing/Poisson 仅节奏闸；`proactive_reason_mode=longing_only` rollback |

**Phase 4 后仍开放的 §5 缺口**：4 个 surface「同输入 → 同 kernel/memory 副作用」turn 一致性契约测试（部分已在 Phase 1 `test_soul_turn_contract` 起步，Pipecat/RTC 覆盖待补）。

---

## 4. 当前 dirty 禁区（**禁止 stage / 禁止 soul-runtime session 触碰**）

> 共 ~32 项 unstaged/untracked 实验残留（2026-06-27 盘点）。Soul Runtime phase 全程不得修改或提交。

### 已修改（M）
- `.env.example`
- `backend/app/tts/expression_tagger.py`
- `backend/realtime/run_voice.py`
- `backend/realtime/voice_config.py`
- `backend/tests/test_expression_tagger.py`
- `backend/tests/test_fish_audio_pipecat_tts.py`
- `backend/tests/test_voice_config.py`
- `config/tts.json`
- `docs/HANDOFF.md`（独立交接文档，本分支 session 不更新）

### 未跟踪（??）
- `.agents/` · `.cursor/mcp.json` · `.cursor/skills/` · `.mcp.json` · `skills-lock.json`
- `data/fish_model_ab/` · `data/fish_rhythm_ab/` · `data/ja_voice_audition/` · `data/tagger_eval/` · `data/tagger_position_listen/`
- `experiments/*`（Fish/tagger/voice A/B、presence-ui、proactive smoke 等）

**RTC 主链路**（`backend/app/rtc/**`）与 **Fish/voice 参数实验**属于并行轨道，不在 soul-runtime phase 范围内。

---

## 5. 后续 Phase 简述

| Phase | 范围 | 风险 | 前置 |
|---|---|---|---|
| **6** | proactive 迁 agenda/motivation；longing/Poisson 仅作节奏闸 | 中 | ✅ accepted @ `e0b4f23` |
| **7** | 清理：合并 turn_analyzer、退役 soul_llm_server、统一语音换件 | 低 | Phase 6 accepted @ `e0b4f23` |

并行列项：**persona 版本化**（决策 8）可在 Phase 5–6 顺带；**RTC**（决策 6）在 Phase 7 决定归档/删除。

---

## 6. Next task

**Phase 7 — 清理**（下一 session）

1. 合并 turn_analyzer、退役/合并 soul_llm_server、统一语音换件。
2. `pytest -m invariant` + `pytest backend/tests` 全绿才继续。
3. 继续遵守 §4 禁区；不碰 Fish/voice/.env/data/experiments/HANDOFF（除非 Phase 7 明确 scope）。

---

## 7. 状态定义（implemented / reviewed / accepted）

| 状态 | 含义 | 谁定 |
|---|---|---|
| **implemented** | 代码/doc 已 commit 到分支，本地测试通过 | implementer（Codex/Cursor session） |
| **reviewed** | 独立审查过 diff/行为等价性，无 blocking issue | 用户或 Claude review session |
| **accepted** | reviewed 通过，**accepted implementation HEAD** 前移（仅代码/测试 checkpoint）；纯 STATUS/docs commit 不抬高 | 用户明确确认或审查 PASS |

流转：`implemented` → `reviewed` → `accepted`（更新本文件 §1 implementation checkpoint + §3 表格）。

未 accepted 的 implementation commit 不算下一 session 代码起点；dirty 工作树永远低于 accepted implementation HEAD。

---

## 8. Phase 7 后的四条路线

Phase 7（清理/合并）完成后，Soul Runtime 主干收敛，后续可并行选轨（不必严格顺序）：

| 路线 | 目标 | 典型工作 |
|---|---|---|
| **稳定化** | 合并 `codex/soul-runtime` → main；退役 legacy mood metadata / dual-write；观测与 rollback 文档 | merge PR、feature flag 清理、schema 只读列最终删除计划 |
| **Soul Quality** | 活人感与诚实约束 | agenda/motivation 深化、memory 检索质量、persona 版本化、§5 turn 一致性补全、reflection 收拢 |
| **产品体验** | 桌面伴侣 UI/交互 | 像素状态机 polish、debug panel、presence/idle 素材池、非 PixiJS 优先的小步 UX |
| **语音** | Fish/Pipecat 语音轨（与 soul 正交） | tagger 密度/位置、模型 A/B 结论落地、RTC transport 决策、`.env`/tts.json 实验残留整理 |

四条路线共享 **invariant 365** 回归门禁；语音轨额外遵守 voice 专项测试，但不反向改动 Soul Runtime 契约。

---

## 9. 相关文档

| 文件 | 用途 |
|---|---|
| `docs/SOUL_RUNTIME_ARCH.md` | 架构北极星、ports 契约、invariants、迁移阶段表 |
| `docs/ARCHITECTURE_V2.md` | 全项目分层（Soul 层之外） |
| `docs/HANDOFF.md` | 语音/tagger 轮次交接（**本分支不更新**） |
