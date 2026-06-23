# HANDOFF — 上下文交接（2026-06-23，第五十二轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P11（文字双语回复）全部完成（P0 后端 + P1 前端）**。**P14 · Pipecat 链路最大化 epic 已结清**
（Phase 1+2+3+5 全部有结论，Phase 4 双 LLM 仍未开工）。**下一步候选**：提交第五十轮遗留的
`run_voice.py` diff / P15（Pipecat 双方字幕）/ P14 Phase 4（双 LLM）。

## 本轮已完成（2026-06-23，第五十二轮）

### P11-P1 · 前端 UI · 双语开关 + 气泡展示 ✅ 已完成并 commit
- **用户拍板的 3 点决策**：①历史消息译文消失（刷新后从 `/memory/messages` 拉的旧消息没有
  `translation`）暂时可接受，后面要单独补一个任务做后端持久化；②toggle 只影响"未来新消息"，
  已经显示的旧译文不回溯隐藏；③切换 en/ja 不重新翻译屏幕上已显示的内容。
- **改动比原计划（仅 `App.tsx`）稍大**——架构拆解阶段读代码发现 `requestChatComplete`/
  `requestChatStream` 当前签名不支持传 `target_language`，必须连带改 `api/chat.ts`：
  - **[frontend/src/api/chat.ts](../frontend/src/api/chat.ts)**：两个请求函数加
    `targetLanguage?: "en"|"ja"` 参数，请求体按需透传 `target_language`；
    `ChatCompleteResponse`/`ChatStreamDoneMeta` 加 `translation?: string|null`。
  - **[frontend/src/chat/types.ts](../frontend/src/chat/types.ts)**：`ChatMessage` 加
    `translation?: string|null`。
  - **[frontend/src/avatar/useAvatarState.ts](../frontend/src/avatar/useAvatarState.ts)**：
    `ChatFetchResult`（流式/非流式结果的中间类型）同步加 `translation`——编译时才发现的缺漏。
  - **[frontend/src/App.tsx](../frontend/src/App.tsx)**：新增 `targetLanguage` state
    （三态 `"off"|"en"|"ja"`，初始值读 `localStorage["cyber-companion-target-language"]`，
    变化时写回）+ chat-header-actions 里一个循环式 toggle 按钮（关→EN→JA→关，沿用
    `.letter-toggle-button` 样式）+ 气泡渲染 `message.translation`（原文下方一行）。
  - **[frontend/src/styles.css](../frontend/src/styles.css)**：新增 `.message-translation`
    （斜体、浅色、略小字号）。
- **验证**：`tsc --noEmit` 零错误；浏览器 preview 真机验证——EN 档和 JA 档都实测过一轮真实对话
  （开启后**主 LLM 直接用目标语言回复**，`translation` 字段是**回译的中文**，对照展示在气泡
  下方）；localStorage 持久化验证通过（设置后刷新页面状态保留）；关闭开关后新消息恢复纯中文
  无译文、旧消息译文不消失，与上面 3 点拍板一致；console 零新报错。
- **🆕 真机验证副产物（新发现，未排查）**：JA 档下 Fish 标签偶发吐出脏标签 `[ zufrieden]`
  （带前导空格 + 德语词，非词表内标签）。只复现一次，根因未知，已记入下方「已知 bug/风险」。

## 已修改文件（本轮，第五十二轮）
- [frontend/src/api/chat.ts](../frontend/src/api/chat.ts)、
  [frontend/src/chat/types.ts](../frontend/src/chat/types.ts)、
  [frontend/src/avatar/useAvatarState.ts](../frontend/src/avatar/useAvatarState.ts)、
  [frontend/src/App.tsx](../frontend/src/App.tsx)、
  [frontend/src/styles.css](../frontend/src/styles.css)：见上「本轮已完成」逐文件说明。
- `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`：本轮交接更新。

## 未 commit 的历史遗留（非本轮产物，沿用第五十轮状态，本轮未碰）
- **`backend/realtime/run_voice.py` + `backend/tests/test_fish_audio_pipecat_tts.py`**：第五十轮 P14 Phase 5 P1
  的产物（锁 Fish latency=`balanced`，拒绝 `normal`/`low`）。diff 仍夹带历史 `_LatencySpikeLogger`（用户要求
  保留、一直未提交）——**提交时须选择性 stage，只进 latency 那几个 hunk**（同第四十九/五十轮的做法）。
- `.gitignore`、`backend/app/tts/fish_audio.py`、`backend/tests/test_tts.py`、
  `backend/scripts/companion_brain_tag_eval.py`、`config/idle_material_pool.json`、`docs/P9_P2B_VERIFICATION.md`、
  `experiments/*`：更早轮次的遗留，本轮未碰，等用户决定何时一起提交。

## 当前未完成
- **P11 后续小任务（非阻塞，用户已知）**：历史消息（刷新后从 `/memory/messages` 拉取）不带
  `translation`——后端目前只在当轮响应里返回译文，没有持久化进消息 metadata。想要刷新后保留
  历史译文，需要单独开一个小任务改后端 metadata 持久化。
- **提交第五十轮遗留的 `run_voice.py` diff（次选，随时可插空做）**：锁死 Fish latency=balanced，
  选择性 stage 排除 spike logger（见上「未 commit 的历史遗留」）。
- **P15 · Pipecat 链路双方字幕（次优，新立项）**：把 STT 文本 + brain 文本接出来推 UI。先 `/architect` 查
  Pipecat 与前端现状再拆。
- **P14 Phase 4 · 双 LLM 两阶段标签（未开工，epic 最大块）**：原生路线（`LLMTextProcessor`+
  `PatternPairAggregator` 插 brain↔tts），先讨论形态再 `/architect`。注意：Phase 5 锁了 balanced 流式，
  双 LLM 的延迟杠杆设计要据此重估。
- **P14 Phase 3 剩余（需真机+用户在场）**：抢话（bot 被打断，审计 D）量化 `resume_guard`；Fish 调参
  （temperature/prosody，审计 B-2）。
- **沿用未完成项**：P12（Hume prosody，仅立项）、P9-P2-C（素材源真联网）、P9-D（投递层，用户暂缓）。

## 已知 bug / 风险
- **P13（已结案 = won't fix）**：Pipecat `latency=normal` 多轮失声——锁死 `balanced`，不再尝试修。
  **勿在新 session 重开此修复**。
- **⚠️ `run_voice.py` 的 `load_dotenv(override=True)` 隔离坑仍在**：命令行环境变量覆盖
  `CYBER_COMPANION_DATA_DIR` 会被悄悄吃掉，**必须直接改 `.env` 文件**（见
  `docs/TASK_QUEUE.md`「Pipecat 真机测试隔离规范」）。
- **「抢话」（bot 被打断，审计 D）架构性根因未修**：half-duplex resume_guard 基于「逻辑停说」非「实际播完」。
- 沿用既有风险（详见 `docs/TASK_QUEUE.md` P10 节）：cost 模块不认 openrouter 模型、R8、R4、标签器质量基线矛盾等。
- **P11-P0 已知限制（非阻塞，设计如此）**：本地兜底回复（预算拦截/behavior 本地短路）路径不调用翻译——
  这些路径本就是中文短句，无需翻译，`translation` 字段恒为 `None`，前端只需按字段存在与否渲染。
- **P11-P1 已知限制（非阻塞，用户已知）**：历史消息译文不持久化，刷新后消失（见上「当前未完成」）。
- **🆕 新发现（P11-P1 真机验证时，日语档，未排查，无优先级）**：Fish 标签偶发输出脏标签
  `[ zufrieden]`（带前导空格 + 德语词，非词表内标签）。只在 `target_language=ja` 真机测试中复现
  一次，未排查根因（不确定是主 LLM 在日语模式下标签词表混乱、还是 Fish 标签生成本身的已知抽风）。
  **复现条件**：开 JA 译文档 + 发一条消息触发主 LLM 用日语回复。留给以后专门 session 排查。

## 推荐下一个最小任务
- **首选 = 提交第五十轮遗留的 `run_voice.py` diff**：纯收尾性质，scope 明确（选择性 stage 排除
  spike logger），随时可插空做。
- **次选 = P15（Pipecat 双方字幕）或 P14 Phase 4（双 LLM）**：均需先 `/architect` 细化 scope。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
