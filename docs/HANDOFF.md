# HANDOFF — 上下文交接（2026-06-18，第十六轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P7 完成（语音三路全通，见第十五轮）。本轮无代码改动——是一轮纯方向性讨论 session，成果全部沉淀进 `docs/TASK_QUEUE.md`「灵魂层进化」节。**
项目重心已明确转向**灵魂层**（time/world/记忆消解/活人感），画面前端明确搁置，移动迁移定为"待灵魂成熟后做、零返工"。

## 本轮已完成（2026-06-18，第十六轮 · 纯讨论，无 commit）

> 本轮**没有写任何代码、没有跑任何测试**。唯一文件改动 = `docs/TASK_QUEUE.md` 增量扩充（+83 行）。
> 以下是讨论结论（细节见 TASK_QUEUE「灵魂层进化」节）：

1. **Pipecat 延迟归因**：瓶颈是 LLM（DeepSeek ~1.3s），ASR/TTS 已优化到位。延迟是"旋钮"不是"飞跃"（LLM 1.3s→0.7s 也只 2.5s→1.9s）。**待区分模型 vs 网络**（极短请求测 TTFT；靠近 API 区域云主机对比）。豆包 LLM 可作候选（同厂少一跳网络）。

2. **Provider 三方对比（Fish Audio / MiniMax / 豆包）**：
   - **ASR**：MiniMax 无 ASR；Fish 仅批处理无流式 → **两家都不能替代豆包**实时 ASR。
   - **TTS**：豆包当前很强（62ms TTFA，双向流式，中文原生，context_texts 情绪通道已通）；MiniMax 中文原生+情绪自动预测、协议相似；Fish 标签情绪最细但中文质量未验。**现阶段无换 TTS 的必要**。

3. **灵魂层六脑**（核心认知：**「脑」≠「LLM」**，5/6 是状态+数据+定时，不需新增 LLM）：relationship/emotion/memory 多已有骨架；**time brain = 真缺口（核心）**；world brain 新增但简单（天气API/节日查表）；identity-成长高风险最后做。

4. **活人感 / 审核**：用户要"擦边"（暧昧不露骨）→ 提升伴侣感。**LLM 决定走 A 路线**（聪明+低成本 managed API，非无审核）；擦边在 A 下基本可行（轻/中档），取决于选哪个 provider。B 路线（自托管去审核）成本高一个数量级，仅作后备。审核可能在 ASR/LLM/TTS 三层，语音擦边需三层都放行。

5. **记忆消解（ADD/UPDATE/DELETE）**：借鉴 Mem0 一致性管理思路加进 `write_policy`（保留灵魂，补"记忆不矛盾"），**不整体换 Mem0**。疑似 R11 失忆根因，但 R11 验证搁置（当下无固定事件可测，下次发现失忆当场验）。

6. **移动迁移（iPhone 17 Pro Max）**：手机是客户端、后端跑不到手机上；后端上云 VM + PWA + 移动语音优先 RTC 路径。不碰灵魂层，零返工。

7. **画面前端**：**明确搁置重视觉**，保留信笺/typography UI 为默认，触发重启 = 灵魂成熟/有具体点子。

## 已修改文件 + 改动摘要（本轮）

| 文件 | 改动 | 说明 |
|---|---|---|
| `docs/TASK_QUEUE.md` | +83 行（未 commit）| 新增「灵魂层进化（Soul Layer）」节：六脑维度 + time brain 要点 + 优先级 + 探针 + 活人感/审核约束 + 记忆消解 + LLM provider 验证清单 + 活人感工程 7 项 + 移动迁移 + 画面前端搁置 |

> 副产物：`.firecrawl/` 下抓取的 Fish Audio / MiniMax 文档（gitignored，仅供本轮对比，不入库）。

## 当前未完成（产品侧，沿用上轮 + 本轮新增方向）

- **灵魂层进化（本轮新增，方向性、未拆解）**：time brain（核心缺口）/ world brain / 记忆消解 / 活人感工程——见 TASK_QUEUE「灵魂层进化」节。**要做时先 `/architect` 拆最小任务**。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。**下次发现失忆当场验证**，不主动排查。
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档（注：本轮已抓取部分公开文档，结论=中文质量待验、为审核换 TTS 则 Fish>MiniMax）。
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测。
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107。

## 已知 bug / 风险

- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。
- **记忆消解缺口（本轮新增怀疑，未验证）**：我们记忆可能只追加、不消解矛盾 → 疑似 R11 失忆根因。等下次失忆复现时连同 R11 一起验。
- **Pipecat 记忆写回**：`CompanionBrain` 写 SQLite，但语音轮次 off-path 反思（`analyze_turn`）是否与 RTC 路径等价未确认。如发现记忆遗漏，查 `companion_brain.py` 的 `persist_chat_turn` 调用链。

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **time brain 起步探针**（推荐）：读 `backend/app/memory/context_builder.py`（确认是否注入真实时间）+ events 表结构（确认有无时间戳）
- 若做 **记忆消解 / R11**：读 `backend/app/memory/write_policy.py` + `backend/app/rtc/viking_memory.py`
- 若做 **P2**（信笺 UI）：读 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` + `frontend/src/letter/LetterView.tsx`
- 若做 **延迟诊断 / 换 LLM**：读 `backend/app/providers/registry.py` + `config/providers.json`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ `.firecrawl/`（本轮抓取的厂商文档缓存，gitignored）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**time brain 起步探针**（纯读代码、零改动、性价比最高）：核实两件事 ——(a) 现在有没有把真实 `datetime` 注入 prompt；(b) events 表有没有时间戳。这两个答案决定 time brain 的起点。确认后若 (a) 缺失，"注入真实时间"是近乎零成本、临场感断崖式提升的第一刀。
