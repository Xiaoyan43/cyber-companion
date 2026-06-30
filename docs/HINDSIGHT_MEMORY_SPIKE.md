# Hindsight Memory Replacement Spike（P0-OSS-2，2026-06-29，结论：reject-for-now）

> 对应 `docs/TASK_QUEUE.md` P0-OSS-2，依据 `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md` 的执行顺序第 3 步。
> 仓库内新增了可复用的 adapter + 评测脚本（非生产代码，未接入 `ports_from_store`）；
> 自托管 Hindsight 容器在仓库外的本地 Docker 中，测完已停止/移除。

## 结论：Reject-for-now（证据不够支持迁移，不是永久否决）

样本量很小（5 个固定 fixture，每个只问一句 query），不足以下"Hindsight 能力不行"的死结论，
但拿到的信号**没有一项支持现在迁移**，且有运维成本和功能倒退两类独立、扎实的反对理由：

1. **核心卖点（时间/recency 推理）在测试里翻车**：审计文档把"时间矛盾/recency 推理强"列为
   选 Hindsight 的主要理由之一。但 5 个 fixture 里唯一的 miss 恰恰是跨日召回——查询要"最新进展"，
   Hindsight 召回的 top 结果是最早那条记录，而 canonical（无 decay/recency 评分，纯关键词+
   insertion-order tie-break）反而答对了。
2. **运维代价真实存在**：Hindsight 没有 embedded/进程内模式，必须有一个常驻 Docker 容器
   （`ghcr.io/vectorize-io/hindsight:latest`，内置 Postgres），空闲态单进程 RSS ~893-907MB，
   跑完 5 次 retain+recall 后 ~931MB。这台机器（2019 Intel i5/16GB，无 CUDA）本来就要同时扛
   后端 + Pipecat 语音 + 前端，常驻吃近 1GB RAM 的额外服务跟 `ARCHITECTURE_SNAPSHOT.md`
   "默认云推理 + 轻本地编排"的硬件原则直接冲突。
3. **功能比 canonical 倒退**：真实 `hindsight-client` 0.8.3 SDK 没有按 memory id 删除单条记忆的
   接口（只有 `clear_bank_memories` 整库清空，可选按 type 过滤）；同步 `retain`（默认模式）
   返回的 `operation_id`/`operation_ids` 都是 `None`，没有任何可用的单条记录 id。Boxi 现有的
   反思/记忆巩固逻辑需要更新/删除单条记忆，Hindsight 目前的 API 形态没有对应钩子。
4. **不存原文，会改写**：Hindsight 走 LLM 事实抽取，存入的是抽取改写后的版本（附带
   `When:`/`Involving:` 结构化标注），不是逐字保存你给的原文。例如：
   - 写入 `"用户在做一个叫赛博伴侣的 AI 陪伴项目"`，召回得到
     `"用户在做名为赛博伴侣的 AI 陪伴项目。"`（改写）
   - 写入 `"小白这几天食欲不好，去看了医生"`，召回得到
     `"小白这几天食欲不好，去看了医生 | When: 2026-06-29 | Involving: 小白 | 食欲不好"`
   对于"soul 写每个字、措辞精确"的 Boxi（见 memory `direction-c-soul-authored`），这是风险点。
5. **延迟慢 200-700 倍**：canonical 0.7-1.7ms（纯内存关键词匹配） vs Hindsight 268-397ms
   （真实 embedding + LLM 抽取/重排序流水线）。语音实时对话场景里这个差距不是免费的。

## 验证范围

- **环境**：本地 Docker 容器（自托管，`docker run ... ghcr.io/vectorize-io/hindsight:latest`），
  LLM provider 配成 `openai`-compatible 指向 DeepSeek（`HINDSIGHT_API_LLM_BASE_URL=
  https://api.deepseek.com/v1`，`HINDSIGHT_API_LLM_MODEL=deepseek-chat`）。
- **代码**（仓库内，未接入生产路径）：
  - `backend/app/memory/adapters/hindsight_candidate.py` —— `CandidateMemoryBackend` 协议的
    Hindsight 实现，对照真实 SDK 源码（解压 wheel 读 `hindsight_client/hindsight_client.py`，
    非凭文档猜测）写就，已修正两处真实偏差：delete 显式标记为不支持（仿 Letta 的 search 不支持
    模式）；`write()` 在同步模式无 `operation_id` 时降级返回占位符而不是抛错。
  - `backend/scripts/memory_backend_fixtures.py` —— 5 个固定中文 fixture（单跳/多跳/时间矛盾/
    关系变化/跨日召回），各带 query + 预期关键词。
  - `backend/scripts/memory_backend_ab.py` —— A/B 跑分脚本。默认 dry-run 只测 canonical（零网络
    零花费）；`--live` 接真实 Hindsight 服务器，含 `_LiveClientAdapter` 把真实 SDK 的 Pydantic
    响应转成 adapter 期望的 dict 形状。
  - `backend/tests/test_hindsight_candidate.py` —— 4 个离线单测（fake client，不碰网络）。
- **未测试**：reflection/consolidation 场景下对单条记忆的更新/删除诉求（Hindsight 当前 API
  形态下需求与能力不匹配，已在结论里定性，未进一步精确测）；多轮/长对话规模下的表现；打包/
  生产部署下的真实资源占用（只测了 Docker Desktop 开发环境下的数字）。

## 关键数据

| fixture | canonical 命中 | canonical 延迟 | Hindsight 命中 | Hindsight 延迟 |
|---|---|---|---|---|
| 单跳 | ✅ | 0.7-0.8ms | ✅ | 284-532ms |
| 多跳 | ✅ | 0.7ms | ✅ | 397ms |
| 时间矛盾 | ✅ | 1.0-1.5ms | ✅ | 284ms |
| 关系变化 | ✅ | 1.7ms | ✅ | 268ms |
| 跨日召回 | ✅ | 1.0ms | ❌ | 324ms |

容器 RAM（`docker stats`）：空闲 ~893MB → 一次单跳调用后 ~908MB → 跑完全部 5 个 fixture 后 ~931MB
（增量小，未观察到明显泄漏，但基线本身就接近 1GB）。

## 迁移/回滚方案

不适用——本次 spike 全程隔离：Hindsight 服务跑在本地 Docker 容器（已停止/移除，未接入
`ports_from_store`），canonical SQLite 路径全程未改动。仓库内新增的 adapter/fixture/脚本是
非生产代码（不在 `requirements.txt` 里），可以保留作为未来更大样本复测的起点，也可以直接删除。

## 后续影响

- `docs/TASK_QUEUE.md` P0-OSS-2 标记结案（reject-for-now）。
- **若未来要重新评估**，至少需要：①更大样本（覆盖反思/巩固场景下的更新删除诉求，不只是单轮
  retain+recall）；②确认 Hindsight 是否有后续版本补上按 id 删除；③重新核实运维成本（是否有
  更轻量的自托管方式，或云托管选项），不要直接复用这次的"reject"结论而不重新测。
- adapter/fixture/脚本本身的代码质量与"真读 SDK 源码而非猜文档"的方法论可以复用在评估其他
  候选记忆系统（Graphiti/Mem0/Letta，见审计文档）时——尤其是"先解压 wheel 核对真实方法签名"
  这一步，本次发现 README 文档对 embedded 模式的描述是完全编造的，必须依赖源码验证。
