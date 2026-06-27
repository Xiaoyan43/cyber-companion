# Soul Runtime 跨 Session 状态

> **冷启动入口**：新 session 先读本文件 + `docs/SOUL_RUNTIME_ARCH.md`（架构契约）。
> 本文件记录**已验收进度**与**工作树禁区**；不替代 ARCH 的设计细节。

最后更新：**2026-06-27** · base `master@bd616d7` · integration branch `codex/product-integration-20260627` · **Phase 0–7 accepted / merged**

---

## 1. Git 指针

| 字段 | 值 |
|---|---|
| **branch** | `master` |
| **merge commit** | `dbefff0` — `Merge pull request #1 from Xiaoyan43/codex/soul-runtime` |
| **accepted implementation HEAD** | `95848c4` — `fix(soul): align tag_reply join with origin/master rebase base`（Phase 7 rebase integration 代码/测试验收 checkpoint） |
| **Phase 7 implementation commit** | `951efff` — `feat(soul): consolidate Phase 7 off-path commit and voice adapters` |
| **current integration checkpoint** | `a0e23dc` — provider 正名 + tagger 动态 mood 解耦 + 单字自回声，基于最新 master；不改变 Soul accepted HEAD |

> **accepted implementation HEAD** = 最后验收通过的**代码/测试** commit；下一 session 冷启动与回归以它为基准。
> 仅更新本 STATUS/ARCH 的 docs commit（如 `4b77306`…`7423fbc`）**不算**新的 implementation checkpoint，无需循环改 SHA。
> 工作树有 dirty 文件时，**以 accepted implementation HEAD 为准**，不要假设 dirty 内容已落地。

---

## 2. 测试基线（accepted implementation @ `95848c4`）

| 套件 | 命令 | 结果 |
|---|---|---|
| **invariant** | `./.venv/bin/python -m pytest -m invariant` | **353 passed** |
| **backend 全量** | `./.venv/bin/python -m pytest backend/tests` | **725 passed** |

invariant 入口：`pytest.ini` + `backend/tests/conftest.py`（collection hook 按 §5 文件名/前缀打标）。
详见 `docs/SOUL_RUNTIME_ARCH.md` §5。

最新 integration 门禁：**367 invariant passed**、**746 backend passed**、前端 `tsc --noEmit` 通过。

---

## 3. Phase 0–7 进度与 commits

| Phase | 状态 | 关键 commits | 摘要 |
|---|---|---|---|
| **0** | ✅ accepted | `5955b61` | Soul Runtime 架构文档 + 10 项拍板决策 |
| **1** | ✅ accepted | `df9ddff` · `69d2742` · `6b23349` · `b8b1383` · `e68acb7` | 抽 `SoulTurnRuntime`；text 非流/流 + Pipecat 薄壳；turn 一致性契约测试 |
| **2** | ✅ accepted | `11b7bcd` · `062f943` | `MemoryPort`/`StatePort`/`EventLogPort` + SQLite adapter @ runtime 边界 |
| **3A** | ✅ accepted | `f36309e` | append-only `soul_events`；runtime commit 写 `turn.committed` |
| **3B** | ✅ accepted | `4ba52dc` · `b0b33ee` · `6a0bda1` · `5aff7ac` | `open_loops` + `AgendaPort`；due open_loop → proactive reason |
| **4** | ✅ accepted | `31f1697` · `3c40a84` · `e22e8fa` | **4A** `existential_state` 拆分；**4B** `behavior_runtime_state` 拆分 + trust canonical |
| **4.5** | ✅ accepted | `1863829` · `f842694` | 注册 `invariant` pytest marker；353 条可 `-m invariant` 运行 |
| **5** | ✅ accepted | `d3ae3ea` · `22e332f` | 隔离 Mem0/Letta candidate adapter spike；SQLite canonical 不变；无 schema/runtime 接入 |
| **6** | ✅ accepted | `53c424d` | proactive 迁 `motivation.py`：`agenda` 模式 due/overdue open_loop 等为 reason 来源；longing/Poisson 仅节奏闸；`proactive_reason_mode=longing_only` rollback |
| **7** | ✅ accepted | `951efff` · `95848c4` | 合并 RTC off-path `turn_analyzer` commit 到 `SoulTurnRuntime.commit_turn`；`soul_llm_server`/`companion_brain` 明确为 voice/transport adapter；rebase integration 对齐 `origin/master` tagger helper；无 schema 变更 |

**Phase 4 后仍开放的 §5 缺口**：4 个 surface「同输入 → 同 kernel/memory 副作用」turn 一致性契约测试（部分已在 Phase 1 `test_soul_turn_contract` 起步，Pipecat/RTC 覆盖待补）。

---

## 4. 工作树边界

独立 integration worktree 基于 `origin/master` 创建并保持干净。原开发 worktree 的 `_LatencySpikeLogger`、实验脚本、音频数据与 agent/MCP 配置没有进入本分支；不要从原 worktree broad-add。

---

## 5. 后续 Phase 简述

| Phase | 范围 | 风险 | 前置 |
|---|---|---|---|
| **0–7** | Shared Soul Runtime 主干收敛 | 已验收并合并 | ✅ accepted @ `95848c4` / merged @ `dbefff0` |

Phase 0–7 完成后不继续无目的重构；下一步按 §8 四条路线择一推进。

---

## 6. Next task

**Phase 0–7 已完成并合入；当前已选择“产品体验”路线。**

1. 先完成本 integration 分支的 review/合入。
2. 做日用闭环 P0：启动、对话、记忆召回、情绪反馈、重启恢复的端到端验证与摩擦排序。
3. 只实施最高频、最阻塞的一个体验修复；不继续无目的 Soul/TTS 重构。

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
| **稳定化** | 退役 legacy mood metadata / dual-write；观测与 rollback 文档 | feature flag 清理、schema 只读列最终删除计划 |
| **Soul Quality** | 活人感与诚实约束 | agenda/motivation 深化、memory 检索质量、persona 版本化、§5 turn 一致性补全、reflection 收拢 |
| **产品体验** | 桌面伴侣 UI/交互 | 像素状态机 polish、debug panel、presence/idle 素材池、非 PixiJS 优先的小步 UX |
| **语音** | Fish/Pipecat 语音轨（与 soul 正交） | tagger 密度/位置、模型 A/B 结论落地、RTC transport 决策、`.env`/tts.json 实验残留整理 |

四条路线共享 invariant 回归门禁；当前 integration 基线为 **367 passed**。语音轨额外遵守 voice 专项测试，但不反向改动 Soul Runtime 契约。

---

## 9. 相关文档

| 文件 | 用途 |
|---|---|
| `docs/SOUL_RUNTIME_ARCH.md` | 架构北极星、ports 契约、invariants、迁移阶段表 |
| `docs/SOUL_RUNTIME_STABILIZATION.md` | Post-merge rollback、观测清单、legacy/dual-write 退役计划 |
| `docs/SOUL_RUNTIME_TURN_CONSISTENCY_BACKLOG.md` | ARCH §5 turn 一致性缺口与 P0/P1/P2 测试 backlog |
| `docs/ARCHITECTURE_V2.md` | 全项目分层（Soul 层之外） |
| `docs/HANDOFF.md` | 语音/tagger 轮次交接（**本分支不更新**） |
