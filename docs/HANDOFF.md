# HANDOFF — 上下文交接（2026-06-24，第五十四轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P11（文字双语回复）全部完成（P0+P1+P2）并已 commit**。**P14 · Pipecat 链路最大化 epic 已结清**
（Phase 1+2+3+5 全部有结论且全部已 commit，Phase 4 双 LLM 仍未开工）。**P15（Pipecat 双方字幕）全部
完成并已 commit `d20d7f7`**。**下一步候选**：P14 Phase 4（双 LLM，epic 最大块，先 `/architect`）。

## 本轮已完成（2026-06-24，第五十四轮）

### P11-P2 · 历史消息译文持久化 ✅ 已完成并真机验证 PASS，已 commit `73e996a`
- **`/architect` 拆解后发现 scope 比 HANDOFF 旧描述更精确**：读取侧 `backend/app/memory/store.py`
  **不需要改**——`_message_to_schema` 已把整个 `metadata` dict 原样透传，新字段自动随 metadata 出现；
  真正要改的是写入侧 `backend/app/memory/chat_persistence.py`。
- **改动** [backend/app/memory/chat_persistence.py](../backend/app/memory/chat_persistence.py)：
  `persist_chat_turn` 新增 `translation: str | None = None` 参数，非空时写入
  `assistant_metadata["translation"]`（仿 `decision`/`avatar_state` 的可选字段写法）。
- **改动** [backend/app/main.py](../backend/app/main.py)：
  - `/chat/complete`：调用 `persist_chat_turn` 时多传 `translation=translation`（变量已在作用域内）。
  - `/chat/stream`：**实施时发现一个隐藏时序 bug**——`_finalize_streamed_turn` 内部先调用
    `persist_chat_turn` 落库，而外层翻译计算（`translate_to_chinese`）发生在该函数返回**之后**，
    导致流式路径落库时翻译永远还没算出来。修复：把翻译计算挪进 `_finalize_streamed_turn` 内部
    （新增 `target_language` 参数，复用内部已有的 `parsed.content`），函数返回值改为
    `tuple[ChatCompletionResult, str | None]`，外层用 `result, translation = _finalize_streamed_turn(...)`
    接收，删掉外层重复的翻译调用。
- **改动** [frontend/src/chat/types.ts](../frontend/src/chat/types.ts)：`storedMessageToChatMessage`
  新增 `translation` 字段映射（从 `message.metadata.translation` 读取，非 string 时降级 `undefined`）。
- **新增 2 个回归测试**：`test_chat_complete_persists_translation_into_message_metadata`
  （`backend/tests/test_providers.py`）+ `test_chat_stream_persists_translation_into_message_metadata`
  （`backend/tests/test_chat_stream.py`），均验证"落库→`/memory/messages` 读出"链路里 translation 字段
  对得上当轮响应值。
- **验证**：`tsc --noEmit` 零错误；579 pytest 全绿（含新增 2 个）；**真机浏览器验证 PASS**——开 EN/JA
  开关发一条消息，刷新页面后历史气泡下方中文译文仍正常显示。
- **已 commit `73e996a`**（7 files changed, 121 insertions, 37 deletions）。

### 清空 Boxi 对话历史（用户直接请求，非任务队列项）
- 用户要求"清空 Boxi 的上下文"，确认范围仅 `messages` 表（不动 `mood_state`/`relationship_state`/
  `memories`/`conversation_summaries`）。操作前已备份到
  `data/backups/cyber_companion_<timestamp>_before_clear_messages.db`，删除前 211 条记录，删除后确认
  `messages` 表为空。不在 git 历史里（数据库变更，非代码）。

## 本轮已完成（2026-06-23，第五十三轮）

> **⚠️ 更新（第五十四轮）：本节标注的"未 commit"已过期——P15-P0+P1 已合并 commit `d20d7f7`。**

### P15-P1 · Pipecat 双方字幕 · 前端渲染 ✅ 已完成并真机验证 PASS，未 commit
- **新建** [frontend/src/voice/useVoiceTranscript.ts](../frontend/src/voice/useVoiceTranscript.ts)：
  `pipecatStatus==="running"` 时打开 WebSocket 订阅 `/realtime/transcript`，关闭时断开，最多保留最近
  20 条（避免无限增长）。
- **改动** [frontend/src/App.tsx](../frontend/src/App.tsx)：classic 模式下 message-list 上方新增字幕
  区，复用现有 `.message`/`.speaker` 气泡样式渲染 user/boxi 两种字幕（与用户拍板"复用现有聊天气泡
  风格"一致），Pipecat 未运行时不渲染。
- **改动** [frontend/src/styles.css](../frontend/src/styles.css)：新增 `.pipecat-transcript` 容器样式
  （滚动、限高 160px，视觉与 `.message-list` 一致）。
- **验证**：`tsc --noEmit` 零错误，25 个 vitest 全绿；真机验证——启动 Pipecat、说话后字幕气泡正常显示
  user/boxi 两条，关闭后字幕区消失、无 console 报错。
- **未 commit**——与 P15-P0 一起，等用户确认后统一提交。

### P15-P0 · Pipecat 双方字幕 · 后端通道 ✅ 已完成并真机验证 PASS，未 commit
- **`/architect` 拆出 P0（后端通道）+ P1（前端渲染）**，关键发现：Pipecat 管线用
  `LocalAudioTransport`（音频在跑后端进程的本机，非浏览器麦克风），`pipeline_router.py` 之前只有
  start/stop/status，没有任何把文本推给前端的通道——P15 比"加个字幕组件"工作量大，需要先搭通道。
  用户拍板：①场景=本机调试用；②通道用 **WebSocket**（非 SSE，为以后可能的双向打断信号留口子）；
  ③前端渲染要复用现有聊天气泡样式（P1 任务范围）。
- **新建** [backend/realtime/transcript_broadcaster.py](../backend/realtime/transcript_broadcaster.py)：
  `TranscriptBroadcaster`（订阅者队列 + `emit`）+ 两个纯转发 tap——`_UserTranscriptTap`（捕获
  `TranscriptionFrame`，必须插在 `brain_processor` **之前**，因为 `CompanionBrainProcessor` 会吞掉
  `TranscriptionFrame` 不转发）、`_BoxiTranscriptTap`（聚合 `LLMTextFrame` delta 直到
  `LLMFullResponseEndFrame` 才发一条完整句子，插在 `brain_processor` **之后**）。
- **改动** [backend/realtime/run_voice.py](../backend/realtime/run_voice.py)：两个 tap 插入
  `pipeline_steps`（仿现有 `_LatencySpikeLogger` 的旁路写法，不拦截/不修改原 frame）。
- **改动** [backend/realtime/pipeline_router.py](../backend/realtime/pipeline_router.py)：新增
  `WS /realtime/transcript`，accept 后订阅 broadcaster、事件原样 `send_json`，断开时 unsubscribe。
- **真机验证 PASS**（用户本机跑 `python -m websockets ws://127.0.0.1:8000/realtime/transcript` +
  对话一轮）：终端收到 user/boxi 两条字幕事件，且语音对话本身听感与改动前一致，没有破坏原有行为。
- **未 commit**——下一 session/确认后再提交。

## 本轮已完成（2026-06-23，第五十二轮）

### P11-P1 · 前端 UI · 双语开关 + 气泡展示 ✅ 已完成并 commit `7393efe`
- **用户拍板的 3 点决策**：①历史消息译文消失（刷新后从 `/memory/messages` 拉的旧消息没有
  `translation`）暂时可接受，已立为 P11-P2 后续小任务；②toggle 只影响"未来新消息"，已经显示的旧
  译文不回溯隐藏；③切换 en/ja 不重新翻译屏幕上已显示的内容。
- **改动**（架构拆解阶段读代码发现比原计划"只改 `App.tsx`"稍大，必须连带改 `api/chat.ts`）：
  - `frontend/src/api/chat.ts`：两个请求函数加 `targetLanguage?: "en"|"ja"` 参数；
    `ChatCompleteResponse`/`ChatStreamDoneMeta` 加 `translation?: string|null`。
  - `frontend/src/chat/types.ts`：`ChatMessage` 加 `translation?: string|null`。
  - `frontend/src/avatar/useAvatarState.ts`：`ChatFetchResult`（中间类型）同步加 `translation`
    ——编译时才发现的缺漏。
  - `frontend/src/App.tsx`：新增 `targetLanguage` state（三态 `"off"|"en"|"ja"`，localStorage key
    `cyber-companion-target-language`）+ 循环式 toggle 按钮（关→EN→JA→关）+ 气泡渲染
    `message.translation`。
  - `frontend/src/styles.css`：新增 `.message-translation`（斜体、浅色、略小字号）。
- **验证**：`tsc --noEmit` 零错误；浏览器 preview 真机验证——EN/JA 两档都实测过一轮真实对话（开启后
  **主 LLM 直接用目标语言回复**，`translation` 字段是**回译的中文**，对照展示在气泡下方）；
  localStorage 持久化验证通过；关闭开关后新消息恢复纯中文无译文、旧消息译文不消失，与 3 点拍板一致；
  console 零新报错。
- **🆕 真机验证副产物（新发现，未排查）**：JA 档下 Fish 标签偶发吐出脏标签 `[ zufrieden]`（带前导
  空格 + 德语词，非词表内标签）。只复现一次，根因未知，已记入下方「已知 bug/风险」。

### 日语 Fish Audio 音色试听（两批，11 个候选）
- **新建 [backend/scripts/ja_voice_audition.py](../backend/scripts/ja_voice_audition.py)**
  （commit `41fa0eb`）：用法仿 `tagger_eval.py --voice`，4 段手写带标签的 Boxi 风格日语台词
  （兴奋重逢/冷淡委屈/得意挖苦/揶揄+心软）在每个候选音色下各合成一遍，输出到
  `data/ja_voice_audition/<voice_id>/`（gitignored）。
- **试听结果已落 memory**（`fish-audio-ja-voice-shortlist`，与中文清单 `fish-audio-preferred-voices`
  分开记）：
  - 主选（8）：关西腔 `569c5eef…`、正常动漫 `0089dce5…`、动漫 `73647cd4…`、`dae087ca…`、
    `5161d414…`、`63bc41e6…`、`9ef9e752…`、`2d0a1ea9…`。
  - 备选（2）：播音男 `297a6fd2…`、温柔 `5c33c0e2…`。
  - 淘汰（1）：游戏 `dc487cc6…`。
- **`config/tts.json` 的 `fish_audio.voice` 中途多次切换试听**（关西腔→动漫→正常动漫），**最终切回
  中文主选「慵懒偏低音」`ef5c98bdc88845b7a4a4c7382179e5ea`**——当前生效音色对仓库状态**无净改动**
  （`git diff config/tts.json` 为空）。当前**没有按语言自动切换音色的机制**，日语清单目前只是为以后
  接入做的预选，还未接进后端。

### 清掉第五十/五十一轮遗留的未提交小尾巴（4 个 commit）
- **`255a063`**：锁死 Pipecat 语音路径 `latency=balanced`（P14 Phase 5 P1，P13 won't fix）。只
  stage 了 latency 那一处 hunk，`_LatencySpikeLogger`（用户要求保留）仍留在工作区未提交。
- **`94d40dc`**：文字聊天 TTS `latency` 改回 `normal`（第五十轮已拍板的例外，之前没跟着一起提交）+
  `.gitignore` 加 `data/pipecat_spike/`。
- **`0c1d01f`**：新建 `backend/scripts/companion_brain_tag_eval.py`（P8-C 前置 spike 用的语音路径
  标签退化率统计脚本，spike 早已跑完出结论，脚本收进仓库留作以后复测）。
- **`f7204f9`**：`config/idle_material_pool.json`（P9-P2-B 生产素材池，8 条事实核查素材）+
  `docs/P9_P2B_VERIFICATION.md`（真机验证报告，结论 PASS）。

## 已修改文件（本轮，第五十二轮，共 6 个 commit）
- `7393efe`：`frontend/src/{api/chat.ts, chat/types.ts, avatar/useAvatarState.ts, App.tsx,
  styles.css}` + `docs/HANDOFF.md`/`docs/TASK_QUEUE.md`（P11-P1 前端）。
- `41fa0eb`：新建 `backend/scripts/ja_voice_audition.py`。
- `255a063`：`backend/realtime/run_voice.py`（仅 latency hunk）+
  `backend/tests/test_fish_audio_pipecat_tts.py`。
- `94d40dc`：`.gitignore` + `backend/app/tts/fish_audio.py` + `backend/tests/test_tts.py`。
- `0c1d01f`：新建 `backend/scripts/companion_brain_tag_eval.py`。
- `f7204f9`：新建 `config/idle_material_pool.json` + `docs/P9_P2B_VERIFICATION.md`。

## 未 commit 的历史遗留（仅剩 1 项，用户要求保留）
- **`backend/realtime/run_voice.py` 里的 `_LatencySpikeLogger`**：P8-C 前置 spike 的临时延迟探针
  代码，用户明确要求保留在工作区、不提交。提交 `run_voice.py` 任何后续改动时都要用部分 patch 选择性
  stage，排除这段（同第四十九/五十/本轮的做法）。

## 当前未完成
- **P11-P2 已完成并真机验证 PASS，未 commit**（详见上方本轮节）。
- **P14 Phase 4 · 双 LLM 两阶段标签（未开工，epic 最大块）**：原生路线（`LLMTextProcessor`+
  `PatternPairAggregator` 插 brain↔tts），先讨论形态再 `/architect`。注意：Phase 5 锁了 balanced 流式，
  双 LLM 的延迟杠杆设计要据此重估。
- **P14 Phase 3 剩余（需真机+用户在场）**：抢话（bot 被打断，审计 D）量化 `resume_guard`；Fish 调参
  （temperature/prosody，审计 B-2）。
- **日语音色清单未接后端**：`fish-audio-ja-voice-shortlist` 只是预选名单，没有"按 `target_language`
  自动切换音色"的机制。若想要 JA 回复自动换音色，需要单独开任务接 TTS 路由层。
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
- ~~**P11-P1 已知限制**：历史消息译文不持久化，刷新后消失。~~ **已在 P11-P2（第五十四轮）修复**。
- **🆕 新发现（P11-P1 真机验证时，日语档，未排查，无优先级）**：Fish 标签偶发输出脏标签
  `[ zufrieden]`（带前导空格 + 德语词，非词表内标签）。只在 `target_language=ja` 真机测试中复现
  一次，未排查根因（不确定是主 LLM 在日语模式下标签词表混乱、还是 Fish 标签生成本身的已知抽风）。
  **复现条件**：开 JA 译文档 + 发一条消息触发主 LLM 用日语回复。留给以后专门 session 排查。

## 下一步只需读取（按候选任务挑一个）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **做 P14 Phase 4（双 LLM）**：先讨论形态，要读 `docs/PIPECAT_REFERENCE.md` §7（`LLMTextProcessor`/
  `PatternPairAggregator` 原生路线）+ `docs/PIPECAT_AUDIT.md`。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（含 `reference/pipecat/`，P14 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ **不要重开 P13 normal 修复**（已结案 won't fix）
- ❌ 不要重新发起 P9-D 投递层讨论（用户已暂缓）
- ❌ 不要重新发起日语音色试听（两批 11 个已试完，名单已定，除非用户主动提起）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **P14 Phase 4（双 LLM）**：epic 最后一块，需先讨论形态再 `/architect` 细化 scope。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
