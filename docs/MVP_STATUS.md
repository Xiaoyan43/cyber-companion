# MVP 进度记分牌（单一事实来源）

> 这是「项目现在到了哪一步」的唯一记分牌。基于 2026-06-28 代码体检（`_audit/`）建立。
> **规则**：每个 session 结束时更新本表的状态列与「下一步」；状态判定要能指到具体代码，不能凭感觉。
> 判定来源：`_audit/CROSS_VALIDATION_REPORT.md`（每个里程碑重跑 `project_audit.sh` 后刷新）。

## A. 健康度三指标（防屎山，每个里程碑重测）
| 指标 | 基线(2026-06-28) | 警戒方向 |
|---|---|---|
| 死代码（vulture 真阳，排除路由/fixture 误报） | 少量协议常量/未用字段 | 往上=堆积 |
| 重复代码块（pylint） | 57（主要 provider 适配器 + test↔test） | 往上=堆积 |
| 可维护性 < B 的文件数（radon MI） | **1**（`test_tts.py`；`memory/store.py` 已 2026-06-28 重构 C0.35→**A89.9**） | 往上=堆积 |
| 后端测试 | **736 passed + 358 invariant；前端 28 passed**（2026-06-29） | 出现 failed=立即停 |

## B. P0 记分牌（12 项 = MVP 是否成立）
图例：✅已实现　🟡部分　❌未做
| # | P0 能力 | 状态 | 关键代码 |
|---|---|---|---|
| 1 | 稳定人格 | ✅ | `behavior/tone.py`、`memory/persona.py` |
| 2 | 文字聊天(流式+历史+重启恢复) | ✅ | `main.py` chat_complete/chat_stream、`memory/chat_persistence.py` |
| 3 | 长期记忆 | ✅ | `memory/store.py`、`retrieval.py`、`write_policy.py` |
| 4 | 记忆诚实(紧凑上下文/可纠正) | ✅ | `context_builder.build_provider_context`、`store.update_memory/delete_memory` |
| 5 | 情绪与关系(mood/trust/closeness) | ✅ | `behavior/mood.py`、`kernel.py`、`store.update_*_state` |
| 6 | 行为决策(回复/沉默/拒绝/调侃/主动) | ✅ | `behavior/types.py`、`engine.py` |
| 7 | 主动陪伴(open loop+longing；无关系节流/ignore-backoff) | ✅ | `behavior/proactive_reason.py`、`proactive_opener.py` |
| 8 | **Shared Soul(默认文字+语音入口)** | ✅ | 文字+Pipecat 经 `soul/runtime.py`；前端默认语音面板已切 Pipecat，RTC-AIGC 仅保留为实验对照 |
| 9 | 基础语音(半双工+字幕+启停) | ✅ | `realtime/run_voice.py`(主线)、`rtc/`(对照) |
| 10 | 数据持久化 | ✅ | `memory/database.py`、`schema.py` |
| 11 | 安全与成本 | ✅ | `files/gateway.py`、`memory/usage_guard.py` |
| 12 | 可维护性(一键启动/健康检查) | ✅ | `scripts/dev.sh`、`main.py /health` |

**P0 进度：12 / 12。** #8 已闭合：前端默认语音入口现在启动 soul-authored Pipecat，RTC-AIGC 降为折叠的实验对照面。当前音频 I/O 仍是后端 `LocalAudioTransport`（本机麦克风+扬声器）；真正浏览器音频传输/远程访问属 P2，不是 MVP 闭合条件。

## C. MVP 整体验收（连续 7 天日用，全绿才算 MVP 完成）
> 逐日证据记录：`docs/MVP_DAILY_ACCEPTANCE.md`（Day 1：2026-06-28，进行中）。

- [ ] 连续 7 天每天文字+语音交流
- [ ] 重启后人格/关系/记忆连续
- [ ] 正确召回数个跨天事件
- [ ] 至少一次基于真实 open loop 的主动交流
- [ ] 不需开终端修状态
- [ ] 无频繁回声自触发
- [ ] 无明显人格漂移/虚构记忆
- [ ] 云失败不破坏本地数据

## D. 下一步（每个 session 开头读这一行就够）
> **当前下一步**：先执行 2026-06-29 开源路线重置：停止扩建自研模块，依次做 AIRI 原版 x64
> whole-product baseline 与 Hindsight memory replacement spike；细则见
> `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md` 和 `docs/TASK_QUEUE.md` 顶部。7 天日用验收保留，
> 但不再作为阻止上游替换审计的闸门。
> ~~止血：重构 `memory/store.py`~~ **已完成 2026-06-28（C0.35→A89.9，745 绿）**。

## 如何判断「在正确路线上」（给非技术作者）
1. **看 §B**：P0 还有 🟡/❌ 的，就是还没到 MVP；别去碰 P2（全双工/Hume/多端）。
2. **看 §A**：三个指标只要往上走，就是屎山在堆，当场清。
3. **看测试**：任何改动后 `.venv/bin/python -m pytest -q`，最后一行没有 `failed` 才算安全。
4. **每里程碑**重跑 `bash project_audit.sh backend`，用新事实刷新 §A/§B。

---

## E. 通往「完全体」的阶段路线图（北极星 = TARGET.md 的 P0+P1+P2 全做完）
> 原则：**完全体 = Boxi 专属薄层 + 每个模块中实测最强且硬件可承受的上游**。现有 MVP 是可回滚
> 基线，不是必须继续扩建的架构地基。

- **阶段 0 · 地基稳固（已完成）**：P0 = 12/12；健康度全绿；默认语音 Shared Soul 已闭合。
- **阶段 1 · 上游重置（当前所在）**：AIRI baseline + Hindsight replacement spike + Open-LLM-VTuber/
  screenpipe 复用设计。用 A/B 决定替换面，不再默认保留自研。
- **阶段 2 · 日用验收**：在选定上游组合上重新连续 7 天验收；当前 MVP 同时保留为回滚基线。
- **阶段 3 · P2 之「体验完全体」**：外放全双工 + AEC、Hume 声学情绪、Smart Turn 高级判停。**这层才允许碰全双工**（TARGET 明确：MVP 用半双工）。
- **阶段 4 · P2 之「多端完全体」**：Mac 桌面封装 → 浏览器完善 → iPhone 原生。Shared Soul 已是后端单一内核，多端只接表面。
- **阶段 5 · P2 之「能力完全体」**：高级向量库、摄像头视觉、麦克风阵列/硬件 AEC、多角色。

**门槛规则**：每个替换只做一个隔离 spike，必须有资源数据、能力 A/B、迁移/回滚方案和验收；通过后
删除被替代主线，禁止长期双栈。

## F. 文档地图（防止新 session 读错文档跑偏）
> ⚠️ 仓库有 60+ 文档,大多是**历史 spec/日志**,不是当前状态。新 session **只读 §「当前」三件**,其余按需。

- **🟢 当前（每个 session 必读，唯一权威）**：`AGENTS.md` 的核心原则、`docs/HANDOFF.md`、
  `docs/MVP_STATUS.md`（本文件）、`docs/ARCHITECTURE_SNAPSHOT.md`。任务展开再加
  `docs/TASK_QUEUE.md`；开源替换任务同时读 `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md`。
- **🔵 参考（任务触及该模块时读）**：`ARCHITECTURE.md`、`MEMORY_DESIGN.md`、`PERSONA_AND_BEHAVIOR.md`、`SOUL_RUNTIME_ARCH.md`、`COST_AND_TOKEN_BUDGET.md`、`SECURITY_AND_PERMISSIONS.md`、`PROACTIVE_INITIATION_SPEC.md`、`FISH_AUDIO_REFERENCE.md`、`PIPECAT_REFERENCE.md`。
- **⚪ 历史（**不要**当作当前状态，仅考古）**：`SESSION_LOG.md`、所有 `SD*_SPEC`、`V2_*`、`VE1`/`VM6`/`PHASE_*`/`P9_*`、`REBUILD_ROADMAP`、`VISUAL_SPIKE_SPEC`、`SOUL_RUNTIME_PHASE5_SPIKE`、`MANUAL_VERIFICATION` 等。它们描述的是已完成或已放弃的轮次。

**判断口诀**：想知道「现在是什么样」→ 只信 🟢 三件 + 代码体检 `_audit/`；🟢 与任何 ⚪ 冲突，以 🟢 + 代码为准。
