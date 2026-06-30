# AIRI Baseline Spike（P0-OSS-1，2026-06-29，结论：reject）

> 对应 `docs/TASK_QUEUE.md` P0-OSS-1，依据 `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md` 的执行顺序第 2 步。
> 隔离目录在仓库外（`~/airi-spike/`，已删除），本仓库无生产代码改动。

## 结论：Reject（整体 + 展示层都不收编）

**主要理由（产品方向，决定性）**：AIRI 的整套展示层（Live2D/二次元虚拟主播形象）与 Boxi 的视觉方向不匹配——本项目明确不走二次元/Live2D 画风。即使技术上可行，画风不符本身就足以否决，不需要继续验证其余维度。

**次要支撑证据（性能，独立于画风也指向谨慎）**：开发模式下空闲态（无人交互）持续占用接近一整个 CPU 核心，详见下方数据，对这台 2019 Intel i5 机器是显著负担。

## 验证范围

- 隔离目录：`~/airi-spike/`（仓库外），clone 官方仓库（`moeru-ai/airi`，MIT）。
- 只针对桌宠应用 `apps/stage-tamagotchi` 及其 workspace 依赖做 `pnpm install --filter`，**不安装/不测试** `core-agent`、`core-character`、`memory-pgvector` 等对话/记忆相关包，也不涉及 `services/minecraft`（游戏 agent）。
- 跑 `pnpm dev:tamagotchi`（开发模式），观察启动日志 + 用 `ps` 采样空闲态 CPU/RAM。
- 未测试打包版（`electron-builder` 产物）的真实资源占用——开发模式数字通常偏高估，本次未验证偏高多少，因为画风结论已经够用，不需要再花时间精确测打包版数字。

## 关键发现

### 架构验证（呼应 Open Question 1）

AIRI 是真正分层的 pnpm monorepo，展示层（`stage-ui`、`stage-ui-live2d`、`stage-tamagotchi`）与对话层（`core-agent`、`core-character`）、记忆层（`memory-pgvector`、`duckdb-wasm`）是独立 package，没有直接依赖关系。**`isolated-vm` 原生模块编译失败**这个真实遇到的问题，根源是 `services/minecraft`（游戏 agent 服务）的依赖，跟桌宠展示层无关——用 `pnpm install --filter "@proj-airi/stage-tamagotchi..."` 精确跳过即可，验证了"只装展示层，不装对话/游戏 agent 部分"在依赖管理层面是可行的。

这意味着如果未来评估其他展示层候选（如 Open-LLM-VTuber）时，也可以用类似方法只验证展示层依赖图是否独立。

### 性能数据（开发模式，非打包版，仅供参考）

| 指标 | 数值 |
|---|---|
| 依赖安装耗时（已跳过 minecraft 服务） | ~1m25s |
| 主窗口首次启动耗时（含首次资源下载：Live2D/VRM 模型、Cubism SDK） | 14.5s |
| 空闲态总 RSS（多进程 Electron：1 main + 2 renderer + GPU + 3 utility） | ~2.4 GB |
| 空闲态单个 renderer 进程 CPU（持续 35s+ 未降，无人交互） | ~96-97% |
| 空闲态 GPU helper 进程 CPU | ~37-40% |

**这台机器**：2019 13" Intel i5 四核、Intel Iris Plus 655、16 GB RAM，无 dGPU/CUDA/Apple Silicon。如果 Boxi 后端 + Pipecat 语音管线 + 这个桌宠展示层同时跑，CPU 资源会非常紧张——这是即使忽略画风问题、单纯从硬件负担角度也支持谨慎/reject 的独立证据。

## 迁移/回滚方案

不适用——本次 spike 未触碰任何生产代码、未安装任何依赖到本仓库，隔离目录已删除。Boxi 现有的像素风格 React/CSS 视觉层维持不变，无需任何回滚动作。

## 后续影响

- `docs/TASK_QUEUE.md` P0-OSS-1 标记结案（reject）。
- **画风预警**：P0-OSS-3（具身/屏幕感知，候选 Open-LLM-VTuber）描述里同样是"透明置顶桌宠、Live2D"路线，大概率会撞上同一个画风否决理由。建议评估前先确认 Open-LLM-VTuber 是否有非 Live2D/二次元的展示选项，否则可以直接跳过完整 spike、提前判定不匹配。
- AIRI 的"展示层与对话/记忆层解耦"这个架构验证方法（`pnpm install --filter` 精确排除游戏 agent 依赖）可以复用在后续其他候选项目的快速可行性筛查上。
