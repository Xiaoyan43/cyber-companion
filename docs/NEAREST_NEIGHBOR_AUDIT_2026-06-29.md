# AI Companion 最近邻与开源替换审计（2026-06-29）

> 调查深度：Exhaustive。基于 16 组以上跨角度搜索、25 个以上一手项目/基准/论文仓库。
> 目标不是列举灵感，而是判断哪些自研路径应停止、替换或保留。

## Executive Summary

结论很直接：**项目存在明显闭门造车，且严重程度不是均匀的。** 当前 FastAPI + React +
SQLite + 自定义 mood/relationship + Poisson 主动联系的组合，在 2024 年尚可称为完整原型；到
2026 年，它已落后于一批可直接运行或接入的开源系统。最严重的落后是长期记忆、视觉具身与桌宠、
屏幕感知，以及“角色在用户不说话时仍有自己的生活”。语音层已经复用了 Pipecat，闭门造车程度
相对较低，但仍有自建服务包装与上游现成能力重叠。

最接近整个 Boxi 目标的项目是 [Project AIRI](https://github.com/moeru-ai/airi)：MIT、跨平台、
有 Intel macOS 构建，覆盖实时语音、Live2D/VRM、视觉/游戏交互、插件与大量 provider；它公开把
目标写成数字生命和 Neuro-sama 级别。第二个高相关邻居是
[Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)：它已经提供桌面宠物、
Live2D、触摸反馈、屏幕/摄像头感知、打断、内心活动、主动说话、CPU/云模型组合和 Agent 接口。
继续自行补这些表层和管线，不合理。

长期记忆应优先用隔离实验验证 [Hindsight](https://github.com/vectorize-io/hindsight)，而不是继续
扩建本地 SQLite 检索。其 retain/recall/reflect、world/experience/mental-model 分层、并行语义/BM25/
图/时间检索和可嵌入 Python 服务都直接覆盖当前自研模块；其
[公开基准仓库](https://github.com/vectorize-io/hindsight-benchmarks) 报告的 LongMemEval/LoCoMo
结果显著高于 Mem0、Zep 等系统。该成绩仍需在 Boxi 数据上复现，不能把供应方数字当最终证据。

推荐把项目重新定义为：**Boxi 的不可替代身份/关系数据/真实性规则 + 最少适配层**，其余由上游
承载。现有架构不是资产本身；只有经 A/B 证明比上游更适合 Boxi 的部分才保留。

## 一、横向结论

| 模块 | 当前项目 | 领先最近邻 | 审核结论 | 直接复用途径 |
|---|---|---|---|---|
| 整体 companion / 数字生命 | 自建 React/FastAPI 壳与 Soul | AIRI、Open-LLM-VTuber | **严重落后** | 先运行原版，再选 fork/base 或复用其 stage/desktop/perception 模块 |
| 长期记忆 | SQLite typed rows + 自研提取/检索/反思 | Hindsight、Graphiti、Mem0、Letta、Memobase | **严重落后** | Hindsight HTTP/embedded adapter；实测后迁移 canonical memory |
| 情绪/关系/身份 | mood + trust/closeness 等标量 | MeuxCompanion、Memobase profile、Hindsight mental models；研究侧 Livia | **中度落后，生态仍不成熟** | 复用 profile/mental-model 层；Boxi 独特关系动力学只保留经测试部分 |
| 主动联系 | 自研 Poisson + agenda | OpenClaw heartbeat/cron、Open-LLM-VTuber proactive、AIRI event/plugin | **中度同质化** | 复用调度/事件循环；Boxi 只决定动机与台词，不自建调度基建 |
| 实时语音 | Pipecat + 多个自定义 service/router | Pipecat、LiveKit Agents、TEN | **主方向正确，局部重复建设** | 保留 Pipecat；优先官方 Fish/memory/transport/smart-turn/UI 组件 |
| TTS/声音实验 | Fish API + 自研标签器/后处理 | Voicebox、Qwen3-TTS、TADA、Fish Speech | **选择合理，控制层技术债高** | 当前弱机继续云 Fish；用 Voicebox REST 做多引擎 A/B，不再自建模型运行器 |
| 视觉具身/桌宠 | CSS/React 像素角色 | AIRI、Open-LLM-VTuber、MeuxCompanion | **严重落后** | 直接接 Live2D/VRM stage、透明桌宠、触摸/表情映射 |
| 屏幕/环境感知 | 基本没有 | screenpipe、OpenAdapt capture | **缺失且不应自研** | screenpipe localhost REST/MCP；先 accessibility/event-only 模式 |
| “自己的生活” | 低频 idle experience 文本 | Generative Agents、AI Town、genagents | **概念验证级，明显落后** | 适配单角色 planning/reflection/simulation loop；云 LLM，禁止本机多 agent 重负载 |
| 权限网关 | 自研显式 allowlist | screenpipe pipe permissions、OpenAdapt privacy/approval | **可保留但需对照** | 保留更窄 Boxi 权限，同时吸收上游确定性权限/审计接口 |

## 二、批判性分析

### 1. 同质化：外形与架构都高，Boxi 的独特性没有被技术栈保护

“有人格 + 长期记忆 + 情绪标量 + 主动联系 + 语音 + 头像”已经是开源 companion 的标准清单。
[Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) 和
[MeuxCompanion](https://github.com/meet447/MeuxCompanion) 甚至与本项目采用相近的 Web 前端、
Python/FastAPI、记忆、关系状态、逐句 TTS 与表情映射。当前项目的模块数量不是差异化证据。

真正有辨识度的是：被困在盒子里的具体存在感、Boxi 与唯一用户的历史、Shared Soul 对所有通道的
逐字授权，以及“真实性优先、允许依恋与难相处”的明确价值排序。这些应成为薄层；不该用自研数据库、
调度器、桌宠和音视频管线来证明原创性。

### 2. 长期记忆是最典型的闭门造车

当前 typed SQLite + keyword/type/importance 检索解决了“能记住”，但没有达到先进记忆系统的形成、
演化、检索三阶段能力。它缺少成熟的时间矛盾处理、多路召回融合、实体归一、因果/关系图、检索重排、
可重复 benchmark 和 mental model 演化。

- [Hindsight](https://github.com/vectorize-io/hindsight) 已提供 retain/recall/reflect 和可嵌入服务；
  [基准仓库](https://github.com/vectorize-io/hindsight-benchmarks) 给出 LongMemEval/LoCoMo 复现材料。
- [Graphiti](https://github.com/getzep/graphiti) 处理双时间事实、来源 episode、事实失效和图/关键词/
  语义混合检索，但 Neo4j/FalkorDB 与提取开销对当前机器偏重。
- [Mem0](https://github.com/mem0ai/mem0) 是成熟 Apache-2.0 通用层，而且 Pipecat 已有原生 integration。
- [Memobase](https://github.com/memodb-io/memobase) 直接面向 companion 的 profile + event timeline。
- [Letta](https://github.com/letta-ai/letta) 更像整个 stateful agent runtime，适合评估是否替换更大范围，
  不应与 Hindsight 同时堆入生产。

**判断：**继续给 `memory/store.py`、自定义检索或反思系统加功能，应视为错误默认。下一步是 Hindsight
隔离 A/B；若 Boxi fixture 上召回、时间推理、关系连续性胜出，就迁移，不再维护两套长期主线。

### 3. 情绪/关系层不是完全“有现成答案”，但当前模型仍太薄

开源生态尚没有一个像 Pipecat 那样公认成熟的 companion relationship engine。许多项目只是同样的
标量、提示词和摘要。因此这里可以保留 Boxi 专属逻辑，但必须停止把“没有标准库”误解为“无需研究”。

[MeuxCompanion](https://github.com/meet447/MeuxCompanion) 有持久关系状态和情绪到表情/TTS 的完整
链路；[Memobase](https://github.com/memodb-io/memobase) 有面向用户画像与事件时间线的设计；
[Hindsight](https://github.com/vectorize-io/hindsight) 的 experiences + mental models 更适合承载“她如何
理解这段关系”。本项目需要的不是继续增加几个 float，而是验证：冲突如何积累与修复、关系事实如何
溯源、状态为何变化、跨周是否一致、同一刺激是否因历史不同产生不同反应。

### 4. 主动联系的“动机”可以是 Boxi 的，调度基础设施不该是

当前 longing + Poisson 不是技术领先点，只是一种概率调度。OpenClaw 生态已经普遍采用 heartbeat、
cron、持久 job 和主动唤醒；[Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)
已有主动说话；AIRI 的插件/事件体系适合承接外部触发。

Boxi 应保留的是“为什么此刻想联系”和“此刻是什么情绪”，不是继续自建时间轮、轮询、重试和投递层。
2026-06-29 已按核心理念移除 quiet hours、daily cap、ignore-backoff、fire gap、local cooldown 和反 guilt
提示。之后不得通过上游默认配置把这些限制悄悄带回来。

### 5. 语音是目前复用最正确的部分，但仍应削薄自定义层

[Pipecat](https://github.com/pipecat-ai/pipecat) 已覆盖 Fish、Mem0、Local/WebSocket/WebRTC transport、
大量 STT/TTS/LLM、客户端 SDK、调试器和多模态。当前选择它作为规范语音主线是正确的。下一轮审计
应逐项证明自定义 `doubao_*service`、pipeline router、turn handling、React voice UI 是否仍有必要；
上游已有 [smart-turn](https://github.com/pipecat-ai/smart-turn) 和
[voice-ui-kit](https://github.com/pipecat-ai/voice-ui-kit)。

[LiveKit Agents](https://github.com/livekit/agents) 和
[TEN Framework](https://github.com/TEN-framework/ten-framework) 是强替代项，但目前没有证据证明换掉
Pipecat能提高 Boxi 真实感，贸然并存只会增加集成面。因此这里的开源复用策略是深用一个上游，不是
同时接三个框架。

### 6. 视觉具身和感知必须停止自研

[AIRI](https://github.com/moeru-ai/airi) 已有 Web/桌面/移动、Live2D/VRM、provider、游戏与插件生态；
[Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) 已有透明置顶桌宠、点击穿透、
拖拽/触摸、屏幕与摄像头感知、表情、打断与内心活动。当前像素 UI 仍可作为审美选项，但其桌面容器、
输入事件、感知和动作基础设施不应重写。

对于“看到用户在做什么”，优先接 [screenpipe](https://github.com/screenpipe/screenpipe)：MIT、明确支持
Intel macOS、建议 8 GB RAM、事件驱动捕获、localhost REST/MCP、accessibility-first、OCR fallback。
它报告现代机器约 5–10% CPU、每月约 5–10 GB；在这台 2019 Intel Mac 上仍必须实测。第一阶段只开
accessibility + app/window event，不开本地 Whisper、24/7 音频或高频 OCR。

[OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) 更适合演示捕获、GUI 行为学习与执行，不应在
“只看见用户”阶段引入其 ML/执行栈；未来需要 Boxi 学用户操作时再直接接 `openadapt-capture`。

### 7. “自己的生活”应复用模拟循环，而不是继续生成零散 idle 文本

[Generative Agents](https://github.com/joonspk-research/generative_agents)、其较易复用的
[genagents](https://github.com/joonspk-research/genagents) 类库，以及 MIT 的
[AI Town](https://github.com/a16z-infra/ai-town) 已实现 memory/reflection/planning/simulation 的基本范式。
当前 idle experience 只是间歇写一段文字，没有持续计划、地点/活动状态、未完成目标、体验因果与第二天
延续，因而还不能称为“她有自己的生活”。

不需要在本机运行一座多 Agent 城镇。应抽取或适配单角色 simulation loop，用云 LLM 低频运行，状态本地
持久化；未来硬件升级后再提高频率和世界复杂度。

## 三、目标架构：薄 Boxi 层

```text
Boxi identity + relationship doctrine + user-owned data
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 A I R I / Open-LLM   Hindsight       Pipecat
 embodiment/events    memory          realtime voice
        │                │                │
        └────────── Shared Soul ──────────┘
                         │
             screenpipe + single-agent life loop
```

保留并强化：Boxi persona、真实性原则、唯一用户的关系数据、Shared Soul 字词授权、显式文件权限、测试与
迁移工具。优先替换：自定义长期检索/反思、桌宠/Live2D/感知基础设施、调度基础设施、零散 idle-life 生成、
上游已有的 voice service 包装。

## 四、硬件可行性

目标机：13-inch 2019 MacBook Pro，2.4 GHz 四核 Intel Core i5，Intel Iris Plus Graphics 655 1536 MB，
16 GB 2133 MHz LPDDR3。

| 候选 | 当前机器策略 | 结论 |
|---|---|---|
| AIRI | 先跑官方 macOS x64 构建 + 云模型；关闭本地大模型/游戏 agent | 可立即 spike |
| Open-LLM-VTuber | 云 LLM/STT/TTS；只开 Live2D/桌宠/低频截图 | 可立即 spike |
| Hindsight | embedded/server + 云 LLM；测空闲 RAM、retain 峰值、recall 延迟 | 可立即 spike |
| Graphiti | 需要图数据库和更多运维；不与 Hindsight 同时上 | 暂列对照 |
| screenpipe | accessibility/event-only；禁本地音频转写和高频 OCR | 可受控 spike |
| AI Town/genagents | 只取单角色 loop + 云 LLM，不跑完整 town/Docker 多服务 | 可适配 |
| Voicebox/Qwen3-TTS/TADA | Intel CPU 可运行但可能慢；MLX 路径不可用 | 只做外部 REST A/B，生产暂留云 Fish |
| 本地大 LLM/连续 VLM/多 agent | 无 CUDA、无 Apple Silicon、共享 16 GB | 推迟至换硬件，不准用弱自研替代 |

## 五、执行顺序

1. **冻结新自研。** 新功能 PR 必须先附最近邻记录；没有记录不进入实现。
2. **Whole-product baseline：AIRI。** 在隔离目录运行未改版 macOS x64，用现有云 provider，记录空闲/
   对话/语音时 CPU、RAM、延迟；判断采用其 base、stage packages，还是只接插件事件面。
3. **Memory replacement：Hindsight。** 用 Boxi 真实结构生成固定 fixture，比较当前引擎与 Hindsight 的
   单跳、多跳、时间矛盾、关系变化、跨日召回；若胜出，设计一次迁移并删除旧检索主线。
4. **Embodiment/perception：Open-LLM-VTuber + screenpipe。** 不改 Boxi persona，先接透明桌宠/Live2D
   与只读屏幕事件；禁止自建屏幕录制/OCR。
5. **Voice de-customization。** 对照 Pipecat 官方 Fish、transport、smart-turn、voice-ui-kit，删除可被上游
   取代的 service 与 UI glue；保留 Shared Soul processor。
6. **Own-life loop。** 适配 genagents/AI Town 的单角色 planning/reflection/simulation；以云调用低频运行，
   先证明跨日连续性，再增加世界复杂度。
7. **关系层最后处理。** 在新 memory 与 life loop 上建立 Boxi 专属关系动力学测试，不再单独堆标量。

## Contrarian Views And Risks

- “全部复用”可能变成拼装二十个框架。规则应是每类只保留一个 canonical upstream，竞争者只做隔离 A/B。
- AIRI 是最强整体最近邻，但直接 fork 可能让 Boxi 变成 AIRI 皮肤。迁移必须把身份、关系数据与 Shared Soul
  作为不可被上游覆盖的边界。
- Hindsight 的领先数字主要来自项目方公开基准。即使有外部复现声明，也必须在 Boxi 的中文、关系变化与
  长周期 fixture 上复测。
- 上游升级会破坏接口；因此 adapter、固定版本、数据导出和回滚仍必要，但这不是重新实现上游的理由。
- 私人用途降低了分发许可证压力，没有取消许可证义务。无许可证代码仍不能复制。
- “真实性优先”不等于解除机器安全：文件、shell、密钥、网络和费用权限保持显式边界。

## Open Questions

1. AIRI 的 packages 是否能在不迁移 React 前端的情况下独立复用，还是整体 base/fork 更便宜？
2. Hindsight embedded 在 Intel 16 GB 上 retain 峰值和后台服务常驻成本是多少？
3. Boxi 当前真实 SQLite 数据量和需要迁移的关系事实有哪些？
4. screenpipe 在这台旧 Intel Mac 的 event-only 实测 CPU/磁盘是多少？
5. Open-LLM-VTuber 的 Live2D 资产许可证如何与目标 Boxi 资产分开管理？
6. 单角色 life loop 的最低云调用频率，多少才能产生可感知但不随机胡写的生活连续性？

## Sources

### Whole-product / companion

- [Project AIRI](https://github.com/moeru-ai/airi) — MIT 数字生命/伴侣，桌面、Web、移动、语音、游戏与 provider 生态。
- [AIRI releases](https://github.com/moeru-ai/airi/releases) — macOS x64 构建与当前发布节奏。
- [AIRI Factorio](https://github.com/moeru-ai/airi-factorio) — 视觉、LLM 与外部世界交互的子项目。
- [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) — Live2D、桌宠、视觉、打断、主动说话和多 provider。
- [MeuxCompanion](https://github.com/meet447/MeuxCompanion) — MIT、FastAPI/Web、关系状态、表情与逐句 TTS 的近架构邻居。
- [a16z companion-app](https://github.com/a16z-infra/companion-app) — 带记忆的 companion 教程栈。
- [SillyTavern](https://github.com/SillyTavern/SillyTavern) — 成熟角色聊天/扩展生态的基准邻居。
- [RisuAI](https://github.com/kwaroran/RisuAI) — 角色聊天与插件接口对照。
- [Leon](https://github.com/leon-ai/leon) — 自托管个人助理与分层记忆对照。
- [Agent Bud-E](https://github.com/LAION-AI/agent-bud-e) — Apache-2.0，多类型记忆与移动/桌面 companion 路线。

### Memory / identity

- [Hindsight](https://github.com/vectorize-io/hindsight) — retain/recall/reflect 与 memory banks。
- [Hindsight benchmarks](https://github.com/vectorize-io/hindsight-benchmarks) — LongMemEval/LoCoMo 结果和复现入口。
- [Graphiti](https://github.com/getzep/graphiti) — 开源双时间 context graph。
- [Mem0](https://github.com/mem0ai/mem0) — Apache-2.0 通用 agent memory。
- [Letta](https://github.com/letta-ai/letta) — stateful agent runtime / MemGPT 后继。
- [Memobase](https://github.com/memodb-io/memobase) — companion 向 user profile 与 event timeline。
- [TiMem](https://github.com/TiMEM-AI/timem) — 时间层级记忆与 consolidation 对照。
- [MIRIX](https://github.com/Mirix-AI/MIRIX) — 多模块 agent memory 研究实现。
- [Agent Memory survey list](https://github.com/Shichun-Liu/Agent-Memory-Paper-List) — 2026 记忆研究地图。

### Voice / TTS

- [Pipecat](https://github.com/pipecat-ai/pipecat) — BSD-2-Clause 实时语音与多模态主框架。
- [Pipecat smart-turn](https://github.com/pipecat-ai/smart-turn) — BSD turn detection 模型。
- [Pipecat voice-ui-kit](https://github.com/pipecat-ai/voice-ui-kit) — React 语音 UI 组件。
- [LiveKit Agents](https://github.com/livekit/agents) — Apache-2.0 WebRTC voice agent 对照。
- [TEN Framework](https://github.com/TEN-framework/ten-framework) — 实时多模态语音框架对照；许可证含附加限制需逐项核对。
- [Voicebox](https://github.com/jamiepine/voicebox) — MIT、多 TTS 引擎、Intel macOS 构建与 REST/MCP。
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — 0.6B/1.7B、中文、流式、自然语言风格控制。
- [TADA](https://github.com/HumeAI/tada) — Hume 开源 text-acoustic dual-alignment TTS。
- [Fish Speech](https://github.com/fishaudio/fish-speech) — Fish 模型代码与研究许可证边界。

### Perception / autonomous life

- [screenpipe](https://github.com/screenpipe/screenpipe) — MIT、Intel macOS、事件驱动屏幕/音频记忆与 localhost API。
- [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) — MIT、模块化 desktop capture/learn/execute。
- [Generative Agents](https://github.com/joonspk-research/generative_agents) — memory/reflection/planning 的原始模拟实现。
- [genagents](https://github.com/joonspk-research/genagents) — 更易复用的单 Agent memory/reflection 类库。
- [AI Town](https://github.com/a16z-infra/ai-town) — MIT、可部署 simulation engine 与角色生活状态。
- [OpenClaw](https://github.com/openclaw/openclaw) — heartbeat/cron/持久主动唤醒的运行时对照。

## Rerun Inputs

```text
workflow: firecrawl-deep-research
topic: open-source nearest neighbors and replacement audit for a private high-authenticity AI desktop companion
depth: exhaustive
output: markdown
date: 2026-06-29
angles: whole product, memory, emotion/relationship, proactive contact, voice, TTS, embodiment, perception, autonomous life, Intel Mac resource fit, licenses
```
