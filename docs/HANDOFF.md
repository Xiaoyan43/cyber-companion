# HANDOFF — 上下文交接（2026-06-17，第九轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
文本 MVP + 主动发起（PI）已完成并实机 PASS。**信笺 UI** 方向 P0～P1-C 全部完成并已 commit。
Provider 替换计划（Venice AI + Fish Audio）已列入 P5 任务队列，P5-A-1 代码完成但**尚未 commit**。
**P6（Pipecat 语音链路复活）**本轮新增入队列，是实现 Direction C 的关键路径。

## 本轮已完成（本 session，均为讨论/规划，无新代码 commit）

- **架构核实**：
  - 实际 TTS 音色来自 env var `DOUBAO_TTS_VOICE_TYPE`，不是 `tts.json` 的 `model` 字段。
    - Cascaded TTS：`zh_female_vv_uranus_bigtts`（vv，天王星系列，seed-tts-2.0）
    - 纯 E2E RTC：`zh_female_vv_jupiter_bigtts`（vv，木星系列）
    - 两条链路都是 **vv** 的声音，音色系列略有不同（uranus vs jupiter）
  - DeepSeek LLM：`deepseek-chat`（V3 alias，直接透传 API，无硬编码版本号）
  - STT：豆包 `bigmodel` + resource_id `volc.bigasr.auc_turbo`，V3 flash ASR

- **Pipecat 历史复盘（读 SESSION_LOG 确认）**：
  - 搁置原因：Pipecat cascaded 路径延迟 ~3.35s（STT 占 2.7s 是瓶颈），火山 RTC-AIGC 纯 E2E sub-second 实机 PASS 后自然取代
  - STT 2.7s 根因：flash ASR 一次性文件识别，不是流式增量识别
  - DeepSeek 文字链路从未走 Pipecat：两者定位不同（HTTP 文字 vs 实时音频流水线），从一开始就是并行独立的

- **Pipecat vs 纯 E2E 自定义能力对比（结论）**：
  - 纯 E2E = 借豆包 O2.0 的嘴说话，`system_role`/`speaking_style` 与 O2.0 RLHF 竞争，A/B 实测 stance 影响有限
  - Pipecat cascaded = Boxi 自己说话：LLM/TTS 完全可换，灵魂层（behavior/ signals/kernel）每轮完整跑，情绪→TTS 完全受控
  - Direction C"soul 写每个字"只有 Pipecat 路径才能真正实现

- **P6（Pipecat 复活）新增入 TASK_QUEUE**：分 P6-A（ASR 增量识别评估）→ P6-B（LLM→TTS 流水线重叠）→ P6-C（延迟基线测试）→ P6-D（Venice/Fish Audio 接入）

- **Venice AI 模型选型讨论**：
  - 当前 venice 配置为 `llama-3.3-70b`（3.3 版安全训练加强，伴侣场景会拒绝）
  - 推荐换 `dolphin-2.9.2-qwen2-72b` 或更新 Dolphin 变体（专门去审查微调，中文底座好，指令跟随强）
  - **用户尚未确定模型**，需去 Venice 控制台确认当前可用模型列表再决定
  - P5-A-2 仍需 VENICE_API_KEY（用户尚未提供）

## 已修改文件 + 改动摘要（本轮）

**本轮唯一代码改动（docs）**：
- `docs/TASK_QUEUE.md` — 新增 P6（Pipecat 语音链路复活）四个子任务

**上轮遗留，尚未 commit（P5-A-1）**：
- `backend/app/providers/venice.py` — 新建 VeniceProvider（OpenAI-compatible，~190 行）
- `backend/app/providers/registry.py` — +import VeniceProvider，+if 分支（+9 行）
- `config/providers.example.json` — +venice entry（enabled:false，llama-3.3-70b）

**验证结果**：本轮无代码改动，无需运行测试。P5-A-1 验收（上轮）：415 pytest passed，tsc --noEmit 零错误。

## 当前未完成（产品侧）

- **P5-A-2**：切换默认 provider 为 Venice + 冒烟验证。**阻塞：** ① 用户提供 VENICE_API_KEY；② 用户去 Venice 控制台选定无审查模型（推荐 Dolphin 系列，非当前配置的 llama-3.3-70b）
- **P5-A-1 commit**：venice.py / registry.py / providers.example.json 尚未 commit，需先处理
- **P5-B**：TTS → Fish Audio。**阻塞：** 需用户提供 Fish Audio API 文档
- **P6**：Pipecat 语音链路复活（延迟优化）。从 P6-A 开始（评估 Doubao 流式 ASR 增量识别）
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题
- **R11（搁置）**：纯 E2E 长期记忆部分失忆。等用户可访问 VikingDB 控制台
- **VE-1 收尾**：playful 待 `relationship.closeness≥0.67` 自然达成后补测
- **P3 · VE-3**：IgnoreBracketText→avatar，阻塞，需用户补文档 6348/2386107

## 已知 bug / 风险

- **R2（仍存在）**：本地 master ahead of origin 1 commit（含上轮 letter-ui P1-C），未 push
- **P5-A-1 未 commit**：venice.py 等三个文件已改但未进 git，下次 session 开始前需确认 commit 或继续
- **Venice 模型选型未定**：当前 providers.json 写的 `llama-3.3-70b` 有内容审查，实际切换前需改成 Dolphin 等无审查模型
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它

## 下一步只需读取（按任务，只读这些）

- 永远先读：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **P5-A-2**（切换 Venice）：读 `config/providers.json` + `.env`；先确认模型已换为无审查版本
- 若做 **P6-A**（ASR 评估）：只读 `backend/realtime/doubao_streaming_stt_service.py`
- 若做 **P5-B**（Fish Audio）：等用户提供文档后，读 `backend/app/tts/base.py` + `backend/app/tts/doubao.py`

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，已用过，本轮已从中提取所需结论）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**先 commit P5-A-1**（三个文件进 git，清理 working tree），然后：

- 若用户已决定 Venice 模型 + 有 API Key → 做 **P5-A-2**（改两行 JSON + 冒烟验证）
- 若用户想先推进语音 → 做 **P6-A**（只读一个文件，评估 Doubao 流式 ASR 增量识别能力）

两者都是 small diff，P6-A 甚至不需要改代码。
