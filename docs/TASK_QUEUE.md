# TASK_QUEUE — 按优先级（2026-06-29）

> 每个任务限定 scope，给验收标准 + 预计要读的文件。配合 `docs/HANDOFF.md`、`docs/ARCHITECTURE_SNAPSHOT.md` 使用。
> **2026-06-29 路线重置（覆盖下方旧“只做 7 天验收”结论）**：Boxi 是永久私人项目，真实性优先；
> 全部关系节流/ignore-backoff/反 guilt 规则已删除。核心能力自研不是目标，开始按
> `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md` 逐模块替换。目标机为 2019 Intel i5/16 GB，默认
> 云推理 + 轻本地编排。**新功能先冻结。P0-OSS-1（AIRI）已结案 reject（2026-06-29，画风不符，详见
`docs/AIRI_BASELINE_SPIKE.md`）；P0-OSS-2（Hindsight）已结案 reject-for-now（2026-06-29，详见
`docs/HINDSIGHT_MEMORY_SPIKE.md`）；下一任务是 P0-OSS-3（具身/屏幕感知），不得跳过最近邻证据。**

> **环境提醒（2026-06-30）**：新建 worktree 后若 `npm run check`/`tsc` 报莫名其妙的类型错误（如
> `Property 'on' does not exist on type 'IRTCEngine'`），先 `npm ci` 而不是改代码——大概率是
> `node_modules` 没装全，不是真回归。已验证一次：[useRtcVoice.ts](../frontend/src/rtc/useRtcVoice.ts) 在干净
> `npm ci` 后 tsc 全绿，未改任何源码。

## 当前最高优先级 · 开源替换序列

### ~~P0-OSS-1 · AIRI 未修改 baseline~~ ✅ 已结案（2026-06-29，结论：reject）

隔离目录 `~/airi-spike/`（已删除）跑通 `apps/stage-tamagotchi`（用 `pnpm install --filter` 跳过
`services/minecraft` 的 `isolated-vm` 编译阻塞）。**Reject 主因 = 画风不符**：AIRI 整套展示层是
Live2D/二次元虚拟主播形象，与 Boxi 视觉方向不匹配，用户明确不走二次元路线。次要支撑证据：开发
模式空闲态单进程持续 ~96-97% CPU + 总 RSS ~2.4GB，对这台 2019 Intel i5 是显著负担（未测打包版
真实数字，画风结论已足够，不需要再精确测）。架构验证：展示层（`stage-ui`/`stage-ui-live2d`/
`stage-tamagotchi`）与对话/记忆层（`core-agent`/`memory-pgvector`）确认是独立 package，依赖管理
层面可分开装。详见 `docs/AIRI_BASELINE_SPIKE.md`。**画风预警**：P0-OSS-3 候选 Open-LLM-VTuber
同样是 Live2D/透明桌宠路线，评估前应先确认是否有非二次元展示选项，否则可直接判定不匹配、跳过
完整 spike。

### ~~P0-OSS-2 · Hindsight memory replacement spike~~ ✅ 已结案（2026-06-29，结论：reject-for-now）

真实自托管 Hindsight（Docker 容器 + DeepSeek 做 LLM provider）跑了 5 个固定中文 fixture（单跳/
多跳/时间矛盾/关系变化/跨日召回）vs canonical SQLite。**结果不支持迁移**：canonical 5/5 命中，
Hindsight 4/5（唯一 miss 恰好是它该最强的 recency 推理场景）；常驻 Docker 容器吃 ~900MB+ RAM，
跟硬件"轻本地编排"原则冲突；真实 SDK 没有按 id 删除单条记忆的接口、同步写入拿不到可用 id，比
canonical 功能倒退；写入内容会被 LLM 改写而非存原文；延迟慢 200-700 倍。详见
`docs/HINDSIGHT_MEMORY_SPIKE.md`。**非永久否决**——样本量小，若未来重测需更大样本 + 覆盖反思/
巩固场景对单条记忆更新删除的诉求，不能直接复用这次结论。Docker 容器已停止移除；Docker Desktop
本身按用户要求暂时保留，**项目后续若确认用不上，提醒用户卸载**。

### ~~P0-OSS-3 · 具身与屏幕感知复用~~ ✅ 已结案（2026-06-29，结论：两项均 reject）

- **Open-LLM-VTuber → reject**：只读官方 README/文档核实，未跑 spike。展示层只有网页版/桌面客户端
  窗口/桌面宠物浮窗三种模式，三种都基于 Live2D 渲染；"可定制"仅指换 Live2D 模型外观，不提供无头/
  静态图片/非二次元风格/可替换渲染层选项。与 AIRI（P0-OSS-1）reject 理由同构——画风直接冲突，
  Boxi 明确不走 Live2D/二次元路线，省下完整资源占用 spike 的成本。
- **screenpipe → reject**：只读官方文档/issue 核实，未本地安装。官方建议最低 8GB RAM（这台机器
  总共 16GB，screenpipe 一家吃掉一半推荐值）；真实 GitHub issue（#183）报告过 CPU>100%+RAM>10GB
  的故障案例；accessibility-only 配置下，accessibility 数据不可用时仍会自动 fallback 到 OCR，
  可能绕不开"禁高频 OCR"的硬性要求。资源画像跟硬件"轻本地编排"原则冲突，理由与 Hindsight reject
  同类（量级更夸张，8GB vs ~900MB）。
- **结论**：具身/桌宠/屏幕感知这条开源复用路径目前没有候选了——这不代表真实感缺口（"看到用户在
  做什么"）消失，只是现成方案在这台硬件上不可行。需要找更轻量的替代方案，或暂时接受这块空缺，
  留给以后硬件升级或新候选出现时重新评估。

### P0-OSS-4 · Pipecat 去自研化（进行中,2026-06-30 第八十三轮 · transport 三阶段全部完成）

- 对照官方 Fish service、Mem0 integration、transport、smart-turn、voice-ui-kit。
- 每个自定义 voice service/router/UI glue 必须证明上游不能替代，否则删除；Shared Soul processor 保留。

**清单审计已完成**（`backend/realtime/` 19 文件 + `frontend/src/voice/` 全部）：
- ✅ 合规/无需动：生产 TTS 已用官方 `FishAudioTTSService`；Mem0 对照无对应物（语音记忆复用文字
  聊天共用 SQLite 主线）。
- 🗑️ 疑似死代码,待核实引用后删除：`doubao_streaming_tts_service.py`、
  `doubao_bidirection_tts_protocol.py`、`doubao_tts_service.py`（生产已走 Fish,这三个豆包 TTS
  文件未见被实际调用）、`mac_say_tts.py`。
- ⚠️ 不在本任务范围（独立决策项）：`doubao_realtime_service.py`/`doubao_realtime_protocol.py`/
  `soul_llm_server.py` 只在非默认 `CYBER_COMPANION_VOICE_MODE=realtime` 分支用,是否继续维护这条
  legacy E2E 分支是另一个问题。

**追加候选 · Transport 换血 + smart-turn 接入**（已 `/architect` 拆三阶段：spike验证→生产迁移→
smart-turn接入）：
- 动机：`LocalAudioTransport`（后端直连本机麦克风/扬声器,前端只是远程控制面板,从不收发音频）换成
  `SmallWebRTCTransport` 可能同时解决三件事——浏览器原生 AEC（白送,`voice-bargein-needs-aec`
  memory 早就指出的真解法,届时可删 `half_duplex_mute_processor.py`+`self_echo_filter.py` 两个
  hack）、解锁 `voice-ui-kit` 组件、真正的打断/barge-in。
- **smart-turn 现在挂不上的根因跟 transport 无关**：管线没有标准 `LLMUserAggregator`
  （`CompanionBrainProcessor` 绕开了它），换 transport 不会自动解锁 smart-turn,需要单独restructure。
- **P0 spike 验证（phase 1，loopback）：已完成,结论 Accept**（2026-06-30,详见
  `docs/TRANSPORT_SPIKE_RESULTS.md`）——loopback 管线数据通道 RTT n=89 avg=2.8ms,主观听感延迟
  正常、回声压制（`echoCancellation:true`）有效,无重复/嗡鸣。`SmallWebRTCTransport` 端到端可用。
- **phase 2（真实多轮管线 transport 切换）：已完成真机验证**（2026-06-30,详见
  `docs/TRANSPORT_SPIKE_RESULTS.md` 「第二阶段」节,throwaway 脚本
  `backend/realtime/spike_webrtc_pipeline.py`,未改生产代码）——①两个 hack 默认开启时行为与
  生产一致,无回归；②关闭两个 hack 纯靠浏览器原生 AEC,真实多轮场景全程无回声,**可删 hack 有
  真机证据支持**；③**打断/barge-in 不能靠换 transport 解决**——日志坐实 STT 在 bot 说话期间
  持续正常识别,但管线没有"打断→取消 TTS"信号链,根因与 smart-turn 挂不上同源
  （`CompanionBrainProcessor` 绕开标准 `LLMUserAggregator`）,跟 transport 选型正交,不要算作
  换 transport 顺带解决的收益。
- **phase 3（生产 transport 迁移）：已完成并真机验证 PASS**（2026-06-30，第八十三轮，详见
  `docs/HANDOFF.md`，Claude Code 本轮例外直接实施）——`run_voice.py`/`pipeline_router.py`
  生产代码已切到 `SmallWebRTCTransport`（CLI 直跑路径仍保留 `LocalAudioTransport` 不变）；
  `/realtime/start` 改造成 WebRTC 信令入口（接收 SDP offer、返回 answer）。真机验证踩坑：
  这台机器 WiFi 路由器 AP/客户端隔离导致局域网 IP 自连丢包，已用代码层修补
  `webrtc_loopback_candidate.py`（让 aioice 额外提供 `127.0.0.1` 候选）彻底解决，不依赖
  网络环境。**两个回声 hack 本轮未删**（保持默认开启，逻辑不变，删除决策见下方「下一步」②）。
  743 backend passed，真机一轮对话 STT/brain/tagger/TTS 全链路确认正常出声。
- **phase 3 配套 · 前端 WebRTC 客户端接入：✅ 已完成并真机验证 PASS（2026-06-30，第八十四/
  八十五轮）**——`frontend/src/voice/pipecatApi.ts` 的 `startPipecat()` 已改成真正发 SDP offer /
  收 answer；新增 `frontend/src/voice/useWebRtcVoiceConnection.ts` 封装 `getUserMedia` +
  `RTCPeerConnection` 完整生命周期（参考 `backend/realtime/spike_webrtc_client.html` 握手逻辑，
  远端音轨走程序化 `new Audio()`，未改 `PipecatVoicePanel.tsx`/`App.tsx`）；`usePipecatVoice.ts`
  已接入。`tsc --noEmit` 全绿、前端 vitest 34 passed。**第八十五轮用户真机验证 PASS**——用户在
  `http://127.0.0.1:5173` 点"开始 Soul 语音"测试，反馈"一切正常"；Claude Code 通过后端进程的
  重定向日志文件（非用户终端，进程是此前某 session 后台启动、stdout/stderr 已落盘）交叉核实，
  确认 STT（豆包流式 partial→final）→`Boxi decision=reply called_llm=True`→tagger 逐句标签
  （含一次 wording-altered 安全降级，行为符合设计）全链路三轮对话均正常，断开时
  `WebRTC client disconnected`→`Pipecat pipeline task cancelled`→`/realtime/stop 200 OK` 释放
  干净，全程无 ERROR/Traceback。**P0-OSS-4 phase 1/2/3/前端配套全部完成并验证 PASS，无遗留阻塞。**
- **P2 · 两个回声 hack 删除：✅ 已完成（2026-06-30，第八十六轮，Claude Code 直接实施——用户已
  明确把"主要实现者"角色交给 Claude Code，不再是例外）**——`half_duplex_mute_processor.py` +
  `self_echo_filter.py` 及其专属测试已删除，`run_voice.py`/`voice_config.py` 相关装配/env var
  已清理。决策依据：①第八十二轮 throwaway spike + ②本轮在生产 `SmallWebRTCTransport` 路径上用
  `CYBER_COMPANION_VOICE_HALF_DUPLEX=0` 跑 6 轮真实对话（输出设备=用户日常笔记本喇叭，用户确认
  无外接音箱）两次独立证据，均显示浏览器原生 AEC 可完全顶替这两个 hack。`backend/tests` 全量
  726 passed（743−17，差额=被删测试用例数，无回归）。**真机验证缺口已补齐**：用户在删除后的
  干净代码上做了 4 轮真实语音对话，日志确认逐轮 STT final→`Boxi decision=reply` 清晰映射、无
  回声、断开流程干净、全程无 ERROR。

### ✅ P0-OSS-4（Pipecat 去自研化）核心三项全部结案（transport 迁移 + 前端接入 + 回声 hack 删除）

**无遗留阻塞**。

**原则提醒**（2026-06-29 新增 feedback）：diff 大/需要架构改动**不是**降级或拒绝候选的理由,只有
硬件资源/画风/实测指标冲突才是——见 memory `feedback-diff-size-not-reject-reason`。

### ✅ 打断/barge-in 独立管线重构（已结案，2026-06-30 第八十七轮 · P0+P1+真机验证全部完成）

- 动机：管线此前无"用户开始说话→取消 Boxi 当前 TTS 播放"的信号链，P0-OSS-4 回声 hack 删除没有
  顺带解决这个问题（详见 HANDOFF 第八十二/八十三轮）。
- **P0（Pipecat 中断信号契约 spike）：已完成**——对照 Pipecat 1.3.0 实际源码确认
  `FrameProcessor.broadcast_interruption()` 是触发打断的官方 API（自动双向广播
  `InterruptionFrame`）；TTS service / 两个 output transport（`LocalAudioOutputTransport` 和
  `SmallWebRTCOutputTransport`，均继承 `BaseOutputTransport`）已经自带正确的中断反应，不需要新写；
  `CompanionBrainProcessor` 也早已正确处理 `InterruptionFrame`。唯一缺的是"什么时候该调用
  `broadcast_interruption()`"这个决策逻辑。详见 HANDOFF 第八十七轮。
- **防抖阈值已做网络调研**：LiveKit Agents 官方 `InterruptionOptions.min_duration` 默认 0.5s；
  futureagi.com 生产指南推荐 200-300ms + 置信度>0.7。决定：新增独立阈值（不复用现有
  `CYBER_COMPANION_VOICE_VAD_STOP_SECS`），默认 300ms，叠加 VAD 自身 0.2s start_secs，总感知延迟
  ≈0.5s，对齐 LiveKit 官方默认。
- **P1（最小实现，CLI+WebRTC 两条路径都覆盖）：已完成**——新增 `backend/realtime/barge_in_processor.py`
  （`BargeInProcessor`），插在 `vad`/`stt` 之间；新增 env var `CYBER_COMPANION_VOICE_BARGE_IN`
  （kill-switch，默认 on）+ `CYBER_COMPANION_VOICE_BARGE_IN_MIN_SECS`（默认 0.3）。新增 5 个单测
  （用 Pipecat 官方 `run_test` harness），`backend/tests` 全量 731 passed（726+5，无回归）。
- **✅ 真机验证已完成，结论 PASS**：用户实测可以在 Boxi 说话途中打断她，立即停声，暂时没有观察到
  误打断。默认配置（300ms 防抖 + VAD 0.2s start_secs）未调参即可用，首轮观察非穷举测试，后续日常
  使用如发现误打断/不够灵敏再调 `CYBER_COMPANION_VOICE_BARGE_IN_MIN_SECS`。**无遗留阻塞，结案。**

**下一步候选（无优先级排序，需跟用户讨论选哪个）**：①voice-ui-kit 接入范围 + 远程场景 TURN/STUN
（P2，跟已解决的"同机自连"网络坑是两回事）；②P1-OSS-5 单角色"自己的生活"；③候选名单（长期记忆/
情绪性格/主动联系/身份层，13 个未核实项目名，见下方「候选名单」节）。

### ✅ 打断自知性 P0（已结案，2026-07-01 第八十八轮）+ 🔴 "打断有时不生效"根因已查明、修复未完成

- **打断自知性（Boxi 被打断后弱提示式提及）：已完成并真机验证 PASS**。`backend/realtime/
  companion_brain.py`/`companion_brain_processor.py` 改动，详见 HANDOFF 第八十八轮。
- **🔴 真实 bug，未解决，下一步候选**：`ExpressionTaggerProcessor._drain()` 并发预贴标 + 顺序释放
  没有真实播放节奏控制，标签打完就立刻全部推给 TTS——导致用户打断时，回复可能早就整段冲进 TTS
  队列，打断拦不住("Boxi 无视打断说完整段才回应")。**已用确定性复现脚本坐实根因，已尝试"估算朗读
  时长节流"的修复方案但已撤销**——真机测试发现节流制造的句间静默缺口会撞上 Pipecat 输出 transport
  的 `BOT_VAD_STOP_FALLBACK_SECS=3` 秒静默判定，导致 `bot_speaking` 误判 False、打断检测彻底失灵
  + ASR 录音不完整，比原 bug 更隐蔽更严重。**正确修复方向：需要输出层/TTS 真正回传"这句播完了"的
  信号（不是估算睡眠），需要新的跨层信号链路设计，diff 比这次大，需要专门 `/architect`。**详见
  HANDOFF 第八十八轮完整过程记录（含真机故障现象、根因分析、撤销范围）。
- **smart-turn 调研（非紧急，未排期）**：用户问过为什么现在没有 smart-turn。结论——模型本身轻量
  （8MB，CPU 10-100ms），硬件不是瓶颈；现有架构没装是因为 `CompanionBrainProcessor` 绕开了 Pipecat
  标准 `LLMUserAggregator`（smart-turn 设计上要挂在这个组件上）；要装需要要么改造接标准 aggregator
  （动核心管线的大手术），要么自己搭信号桥接（工作量小一些但仍是新架构）。**值得做但应单独立项**，
  跟"打断有时不生效"是相关但不同的两个问题（smart-turn 解决"用户说完了没"端点检测，不是打断逻辑）。

### Boxi 主动打断用户（未排期，独立于开源替换序列）

- 动机：跟"打断自知性"同一轮讨论提出，目的是让打断/被打断都有真人对话的真实感。用户明确：触发
  场景不限于"说话啰嗦"，可以是吵架/闹脾气/任何情绪驱动的场景。
- **已拍板的方向**：触发判断接入现有情绪内核（`tone.py`/`mood_state`/`relationship_state`，项目
  里情绪的单一真源），不要为打断单独新写一套判断逻辑——避免"内核说她没生气，但打断逻辑却让她像
  生气一样打断你"这种人格分裂。
- 调研过的开源参考：CleanS2S 的 `Proactivity`/`ProactivityChatHelper` 模块**不是**直接可用的打断
  实现——它解决的是"AI 下一轮回复该用什么态度"（敷衍/延迟/转移话题/拒绝/不回复等 8 选 1），不是
  音频层面的"打断用户说话中"，没有现成代码可抄，需要从零设计判断逻辑。
- **未开工**，需要新 session 单独 `/architect`，会碰受限层 `backend/app/behavior/`。

### P1-OSS-5 · 单角色“自己的生活”

- 适配 genagents/AI Town 的 planning/reflection/simulation loop，只跑一个角色并使用云 LLM。
- 验收是跨日计划、经历和未完成目标连续，不是随机生成几条 idle 文本。

### 候选名单（未排期，未核实，2026-06-29 用户提供）

> 以下项目**未做任何调研**（不确认是否存在/活跃/license/是否名称准确），只是按用户给的描述
> 粗略归类到现有模块，留给以后排期任务时先核实再决定是否值得 spike。**不是正式队列任务**，
> 不要直接当作可信结论引用。

- **长期记忆候选**：`eros-engine`（Rust，六维亲和力模型+双层记忆）、`kiwi-mem`（模拟遗忘/记忆
  加深/睡眠整合）、`MemoryConstellations`（自组织记忆，自动提取事实/归类话题/编织叙事）、
  `Mimir's Memory Hub`（持久记忆+多角色聊天，模拟遗忘/强化/梦境/情绪权重）、`AI-memory`、
  `Afterglow`、`Palimpsest`、`Formative Memory`、`sostenuto`（仅有名字，未核实具体内容）。
- **情绪/性格候选**：`MATE`（确定性情感+涌现性格，基于 20+ 心理学理论，纯数学函数驱动情感）。
- **主动联系候选**：`revive-companion`（主动关怀决策引擎，泊松过程+贝叶斯推断——与当前 Boxi
  主动联系系统用的 Poisson 调度直接同类，值得优先核实是否有可借鉴的改进点）。
- **身份/灵魂层候选**：`digital-companion-core`（有状态个性+记忆+情绪，提供"Soul"抽象，含身份/
  记忆/情绪）、`OpenSoul`（跨平台任务连续性，单 agent 可在 30+ 渠道保持任务状态）、OGMA 项目
  "跨版本身份继承"（强调 AI 人格在不同会话/模型/后台间保持一致——这一层是 Boxi 不可被上游覆盖的
  边界，借鉴机制思路即可，不应直接迁移整个身份层）。
- **下一步（非现在做）**：排到对应模块任务（长期记忆/情绪关系层/主动联系）时，先各花极小成本
  核实这些项目是否真实存在、是否活跃、license 是否兼容，再决定值不值得列入正式 spike 候选。
> **2026-06-28（第七十四轮）**：**P16 · 默认 Soul 语音入口已完成。** 前端主语音面改为 Pipecat（`/realtime/start|stop|status` + transcript WS），RTC-AIGC 保留为折叠的实验对照；两入口互斥。启动错误现可经 status `last_error` 回传 UI。后端 747 + invariant 366 + 前端 28 + tsc 全绿。**P0=12/12；下一步=连续 7 天日用验收，不开新功能。**
> **2026-06-27（第七十三轮稳定化）**：dirty 工作树已从 `codex/soul-runtime` 分离到 `codex/voice-stabilization-20260627`，并按 provider 正名 `67ab085`、tagger 位置 `9847d9e`、Fish 参数 `26f0ef4`、单字自回声 `dd026ee` 四组独立提交。后端 745、invariant 366、前端 `tsc --noEmit` 全绿；`_LatencySpikeLogger` 与全部实验/音频/工具配置仍明确未提交。**下一步 = 产品体验，不再继续 Fish/tagger 微调。**
> **2026-06-27（第七十二轮用户验收）**：用户已听完 `position_v5` 并决定保留。B 类位置精修结案；动态 mood 不再注入 tagger，正文保持为唯一情绪来源。
> **2026-06-27（第七十二轮）**：B 类位置根因坐实为动态 mood 注入会抢过已写完的原文证据。继续叠示例的 `position_v3/v4` 不稳定；neutral-mood A/B 两轮 10/10 不再提前染色。生产已移除 tagger prompt 的动态 `mood_block`，保留函数参数兼容；正文成为唯一情绪来源。最终 `position_v5` 五条落点全部正确，后端全量 745 passed，用户听感 PASS 并决定保留。
> **2026-06-27（第七十一轮）**：标签器 provider 命名债已结案。`"gemini"` 已正名为模型无关的 `"tagger"`，tagger/翻译共用该辅助 OpenRouter 入口；新 env 为 `OPENROUTER_TAGGER_API_KEY`，但旧 provider key 和 `OPENROUTER_GEMINI_API_KEY` 均保留自动兼容。后端全量 744 passed，前端 `tsc --noEmit` 通过，本机旧密钥配置可继续使用。
> **2026-06-27（第七十轮）**：`normalize=false` 已进 Pipecat 真机链路，听感可接受；发平/呼吸延后与音色和其他参数统一评估。
> 真机发现 Boxi「先睡，乖。」尾音被 ASR 回收成单字「乖。」，逃过 `min_chars=2` 后触发自回复。已做 2s 窄窗口精确尾字修复 +3 测试（21 passed）。
> 真机又运行三轮，Boxi 实际生成单字回复「一」；本次尾音未被 ASR 回收、未自触发，真实用户后续输入正常。直接拦截命中由 +3 确定性测试覆盖。
> **下一步 = 转日常真机观察；再次自触发时记录 ASR final + 时序后继，不再主动制造回声。**
> **2026-06-26（第六十七轮）**：**标签密度双向攻坚，未 commit，待量化验证后 commit。**
> ① `TAGGER_INSTRUCTION_TEMPLATE` Rule 3 重写——从"软倾向不加"改成"明确条件判断（条件A/B，默认否）"，
> 针对 Haiku 对"克制类"指令遵循弱的特性；② 新代码护栏 `suppress_repeated_leading_tags`——连续句
> 首个非exempt标签完全相同时去重，音效/break标签豁免，空白句重置基线；③ 接入 `apply_expression_tags`
> + `main.py` `_tag_reply_by_sentence`；④ +10 个单测，69 tagger 相关测试全绿。
> **下一步 = 用 `experiments/tagger_ab.py 3` 量化复核效果，有效则 commit；参见 HANDOFF。**
> **2026-06-26（第六十五轮）**：**文字路径标签器逐句化（P0+P1）已完成并真机验证 PASS，
> 已 commit `111c70c`。** `/architect` 拆出 P0（分句/拼回工具从 `expression_tagger_processor.py`
> 搬到 `expression_tagger.py`，消除 app→realtime 反向依赖）+ P1（`main.py` 两处调用点改
> `ThreadPoolExecutor` 并发逐句标签，单句失败只退化那一句，不再整段作废）。新增 5 个测试，
> 655 pytest 全绿。随后做了大量标签质量调优 + 模型 A/B：① prompt 规则3 加密度克制措辞，对
> Gemini 2.5 Flash Lite 有效（密度降明显）、对 Claude Haiku 4.5 几乎无效（它对"克制类"指令
> 遵循弱于格式类规则）；②自建 `experiments/tagger_ab.py` 量化对比 Gemini/Haiku/MiniMax-M3——
> **MiniMax-M3 出局**（延迟~9.5s/句、几乎不贴标签）；Gemini vs Haiku 是质量(Haiku更准) vs
> 密度/延迟/成本(Gemini更优) 的真实权衡，当前生产配置（`config/providers.json`，gitignored）
> 临时停在 Haiku，密度问题未解决，**下一步主线**。③真机复核排除了"嘉岚音色情绪响应弱"的猜测
> （已撤回，无官方依据，问题在标签密度不在音色）。④调研 Fish Audio 克隆/Voice Design，发现
> 这两个功能需要 Plus 套餐（用户当前 Free 套餐锁住），用户决定暂不升级、维持嘉岚为主音色。
> 详见 HANDOFF。
>
> **2026-06-26（第六十四轮）**：**TTS 模型切换 + 两个配置 bug 修复 + 标签器 token 预算修正，
> 已 commit `982a168`**。①用户带来 Fish 官方博客确认 S2.1 Pro / S2.1 Pro Free 同一套模型权重，
> 切 `config/tts.json` 到 `s2.1-pro-free`；过程中发现并修复两处独立 bug——`registry.py` 的
> `fish_audio` 分支没传 `model=entry.model`（文字路径一直用代码默认值 `s2-pro`，配置不生效）+
> `run_voice.py` 硬编码 `model="s2-pro"`（语音路径同样不读配置）。②真机复现"文字路径长回复标签
> 全部消失"，定位到 `expression_tagger.py` 的 `max_output_tokens` 预算用 `estimate_token_count`
> （`len//3`，按英文调校）严重低估中文 token 数，长回复"复述原文+插标签"撞预算上限被截断，
> `_preserves_original_wording` 护栏正确拒绝截断结果但导致整段标签作废——改成按字符数+256 的
> 预算（`_tagger_output_token_budget`），消除截断。③**截断消除后暴露出更深层问题**：还观察到一次
> "漏句"（标签器吞掉原文开头一个小句）导致同样的整段作废——**坐实文字路径"整段全有或全无"架构
> 本身脆弱，不管失败原因是什么，单点失败就让全篇标签归零**。语音路径已经是逐句调用
> （`apply_expression_tags_to_sentence`）所以只丢一句，文字路径还是整段调用（`apply_expression_
> tags`）。**下一步主线 = 文字路径标签器逐句化**，复用语音路径现成的逐句函数，对齐两条路径的
> 容错粒度。详见 HANDOFF。④新增 Fish Audio 官方文档 MCP server（`claude mcp add` 写入
> `.mcp.json`，project scope），评估后认为这层对本项目有实质帮助（直接命中本轮"文档信息滞后/
> 拼凑出错"的反复症状），llms.txt 不装直接按需 WebFetch、Agent Skills 对已有定制集成代码价值不大
> 跳过。**MCP 状态 pending approval，需在新 session 里首次批准才能用**。⑤用户反馈切换免费版后
> 仍被扣钱，怀疑根因是克隆音色（`reference_id`）本身的使用费、与 model 档位选择是两套独立计费——
> **未验证，留给用户自行核实**。
>
> **2026-06-25（第六十三轮）**：**task 3（标签器音效标签语义闭门）已完成并真机验证 PASS，已 commit
> `70d5c7a`。** `/architect` 确认 scope 收窄到只改 `TAGGER_INSTRUCTION_TEMPLATE` 一个字符串：①规则4
> A/B 类区分纠正为"独立可分离声音事件 vs 改变音色/语气"（用户指出原"会不会发声"措辞不准）；②新增
> 子规则——A 类标签只能在文字写到该动作真实发生时用，不能当情绪基调代用记号，给正反例
> （`[sighing]` vs `[nostalgic]`）；③音效词表每个标签补官方 description 当判断锚点。讨论后明确
> **排除**整段喂 Fish phoneme 发音文档给 tagger（会撞改字护栏 + 官方情绪文档本身有反例会反向强化
> bug + 流式按句调用 token 成本）。真机验证：~20 句调用里 A 类标签从旧基线"6+ 次/轮"降到
> `[sighing]` 1 次 + `[crying loudly]` 1 次（均为语义边界本身模糊的灰色案例），其余惆怅/温柔位置
> 正确分流到 `[soft tone]`/`[whispering]` 等 B 类标签，判定净正向可结案；副产物确认 task 2 的 P1
> 守卫（`[break]` 冗余/密度）真机 4 次触发全部行为正确、与本轮改动无冲突。**59 pytest 全绿（21+38），
> 未跑全量 `npm run check`。task 3 结案，下一步无紧急主线**——建议观察真机稳定性或从沿用未完成项
> （P12/P9-P2-C/task2 P2-P3）里选，详见 HANDOFF。
>
> **2026-06-25（第六十二轮）**：**task 2 位置/格式守卫 P0+P1 已 commit `b07375d`（真机两轮净正向、不误伤）。**
> `/architect` 把 task 2 拆成四个守卫（畸形归一化 / `[break]` 冗余密度 / 词中插 / 开头堆叠），本轮落地前两个：
> P0 `_normalize_malformed_tags`（`[ sighing ]`→`[sighing]`、`[soft  tone]`→`[soft tone]`、空标签 `[]`/`[   ]` 剥除）
> + P1 `_normalize_break_tags`（`[break]`/`[long-break]` 紧贴停顿标点即剥除 + 单次调用≤1，孤立无标点相邻的单 break 保留）
> 组合进 `_normalize_tag_placement`，接在 `_strip_dangling_trailing_tags` 之后，**整段 + 流式逐句双路径统一生效**；
> 只增删/修复 `[tags]`、原文一字不动。加 `🧹 placement guard` 观测日志（守卫真改动时打 before→after，**看后端终端非前端**）。
> 21 新单测 + 既有 38 全绿，相关切片 134 passed。**真机两轮 P0/P1 一次没触发**（`[ sighing ]` 畸形 / `[break]`
> 这两轮没复现 → 守卫针对**低频**症状），但证明**零误伤**（8+ 种合法标签全保留）。**真机暴露两个新问题（均非位置/格式
> 守卫射程，见下「🔴 task 3 / 🟡 task 4」）；P2/P3（词中插 / 开头堆叠）降级——这两轮均未复现，优先级让位 task 3。**
>
> 🔴 **task 3 · 标签器音效标签滥用（语义判断质量，建议下一步主线）**：Gemini 把 `[sighing]`（Fish 里是触发**真实
> 叹气声**的音效标签）当成「这句偏温柔/惆怅」的**通用软情绪记号**在用——真机一轮内伤感故事 + 表白场景出现 6+ 次，
> 真人不会每隔一句实际叹气，**听感不自然**。**根因 = 语义归类错误（音效 vs 语气混淆），属 LLM 判断、不属位置/格式。**
> 治本杠杆全在 LLM 侧：① prompt 划清「音效/生理类 = 会发真实声音、只在 Boxi 真会做那个动作时才用；想表达 wistful
> 用 `[soft tone]` 等语气标签」；② 或换标签器模型（memory `future-provider-swap-candidates` 已记 tagger LLM 待换）。
> **禁止用代码删 `[sighing]`**——那是替 LLM 判断情绪恰当性、踩架构红线，且用户明确不要代码硬干预密度（治标不治本）。
> 要读：`backend/app/tts/expression_tagger.py`（`TAGGER_INSTRUCTION_TEMPLATE` 第 4 条音效/语气精度区分）+
> `docs/FISH_AUDIO_REFERENCE.md`（音效标签「触发真实声音 vs 仅影响演绎」分类）。先 `/architect`。
>
> 🟡 **task 4 · 自回声残余（归 self-echo/AEC 兜底，暂缓）**：真机一轮 Boxi 自问自答——其上句结尾「现在想让我**怎么
> 陪你**？」的音箱尾音被麦克风采回，ASR 误转成「能陪你」，因不是 Boxi 尾巴的干净精确/同音后缀（多了误听的「能」）
> 或已超 4s 窗口，逃过 `self_echo_filter` → brain 当用户输入回应。**这是 self-echo 内容级兜底（commit `c40efda`）的
> 已知残余，真治靠 AEC（浏览器/WebRTC 白送），挂未来「产品上 web/WebRTC」独立 epic。** 收紧匹配会误杀真实接话
> （用户也可能真说「能陪你」），是兜底固有两难。**本轮不动；与 voice-bargein-needs-aec 同源。**
>
> **2026-06-25（第六十一轮）**：**语音体验三连修复，全部真机 PASS 并 commit。** ①省略号修复真机确认后
> commit `a922465`（上一轮代码）。②**自我回声**（commit `c40efda`）：真根因 = half-duplex 在 BotStoppedSpeaking
> 解除静音，但音箱仍在放缓冲尾音（输出缓冲领先真实播放）→ 外接音箱无 AEC → 麦克风采回 → ASR 在 resume guard
> 后出 final → Boxi 自问自答。修复 = 新建 `self_echo_filter.py`（内容级兜底：用户 final 若是 Boxi 上句**尾巴**
> 且在 bot 停说 4s 窗口内 → 丢弃；只认尾巴不误杀真实接话）。③**偏长被砍落在完整句**（commit `6087d31`）：
> 根因 = max_tokens=200 砍半句 + tagger 收尾 flush 把残尾也念出来。修复 = `VoiceTurnOutcome.truncated`
> （`output_tokens >= max_tokens` 判定，无需 finish_reason）→ 挂 End 帧 → flush 时 truncated 丢残尾。
> 132 相关测试绿，未跑全量门禁。**下一步主线 = task 2 标签器放置质量**（本轮真机新攒症状：`[ sighing ]` 畸形空格、
> `[break]` 句中滥用/紧贴标点冗余、`[calm] [bored]` 堆叠、历史词中插 `那[sighing]股`；prompt 方案历史已证失败 →
> 走**代码后处理位置/格式守卫**，先 `/architect`）。OPEN：是否抬 `DEFAULT_VOICE_MAX_TOKENS`（截断 fix 后变可选，
> 默认维持 200；用户试改 .env 512 未生效）。barge-in = 未来独立 epic，核心是 AEC（浏览器/WebRTC 白送）非换 ASR。
> **2026-06-25（第六十轮）**：**「省略号怪声」真机定位真正根因 + 清理回干净基线，全部未 commit。**
> ①真机诊断（临时诊断代码已删）**逐一证伪**跨轮 context 竞态 / send 顺序错乱 / `s2.1-pro-free` 模型版本三个猜测；
> **✅ 真根因 = 流式断句器把「…」当句子终止符**——Grok 把「…」当句中停顿写（「…单纯地…羡慕…？」是一整句），
> 断句器在「…」切刀 → 给 Fish 喂语法残缺半句「…单纯地。」→ Fish 即兴合成填充音 = 怪声。**文本断句层问题，
> 非音频/模型/prompt。** ②试 `s2.1-pro-free` 在省略号场景**更差**（持续怪声须强退），已回退 `s2-pro`。③清理：撤掉
> `run_voice.py` 全部诊断代码（净改动归零）+ 撤掉有害补丁 `normalize_trailing_ellipsis`；**有原则修复 = `SENTENCE_TERMINATORS`
> 解耦排除「…」**（`tag_stats._TERMINATORS` 保留「…」）；保留两个 guard（连续终止符合并 + `_schedule` 丢无内容碎片）。
> 13/195 测试绿，未跑全量 `npm run check`。**⚠️ 修复尚未真机验证（改完即交接）。下一步 = 真机听怪声是否进一步减少：
> 改善则 commit（只 stage expression_tagger_processor.py + test + tts.json + 上轮 P0 两文件，排除 run_voice.py）；
> 仍差则确认是 Fish 范式天花板 → 启动 TTS 选型 spike。** s2.1-pro-free 别再随手换（memory 已记）。
> **2026-06-25（第五十九轮）**：**主线转向 = TTS 选型重评（Fish 难驯化根因 → 候选收敛），未 commit。**
> ①P0「标签器·省略号幻觉」代码护栏做完（`expression_tagger.py` 新增 `_strip_dangling_trailing_tags`：标签后无
> taggable content 即判悬空、直接 strip；接入两个标签函数；+6 单测，39 passed / tts 全集 142 passed），**但真机
> 仍幻觉合成 + 原文字句被直接替换 → 护栏不够，问题是结构性的**。②借此停下做 Fish vs 豆包 vs MiniMax vs
> Qwen3-TTS 横向架构对比：**Fish 行内位置标签范式与 LLM 弱项（精确位置标注 + 内容保真）正面相撞，控制信号和
> 内容共用一条通道 → 控制出错就改字/幻觉，纯 prompt/护栏治不好**；豆包/MiniMax/Qwen3 走旁路/自然语言指令，
> 结构上避开这类失败。**候选收敛 = Qwen3-TTS（最低调教压力+97ms+开源）/ 豆包（大库+引入上文）/ MiniMax（枚举+
> Turbo）三选一**。③用户真机试豆包 playground 三机制（语音标签/语音指令/引入上文），洞见「引入上文=用户上一轮
> 发言，我们手上就有，调教成本归零」最贴 pipeline。**⚠️ 对比资料是 playground 指南非 API spec，下注前必拉官方 API
> 文档。下一步 = TTS 选型 spike 前置（拉三家 API 文档 + 查 Pipecat service 现状，不接代码），先 `/architect`。**
> P0 护栏可独立 commit（净改进，待用户点头，只 stage expression_tagger.py + test）。
> **2026-06-24（第五十八轮）**：**P0「破音/音频欠载」根因定位 + 修复完成，已 commit `8d5b2fb`，真机
> Fish+Doubao 双路径 PASS**。真机隔离 + 静态排除逐项证伪（标签器/Phase4/Fish/采样率/P15 tap/探针/设备全部
> 排除），根因 = pipecat `LocalAudioOutputTransport.start()` 创建 PyAudio **输出**流时没传 `frames_per_buffer`
> （`local/audio.py:155`；那个 20ms 是 input 流的），用 PortAudio 默认小缓冲 + blocking write，event loop 偶发
> 停顿（VAD onnx/jieba/网络）→ 供帧 gap → underrun → 破音。修复 = `run_voice.py` `_main_pipeline` 新增
> `_BufferedLocalAudioOutputTransport`（subclass override `start`，输出流显式 `frames_per_buffer`≈200ms）+
> `_BufferedLocalAudioTransport`，只动真机路径（`_main_realtime` Doubao S2S 未碰）。8 realtime 测试绿。
> **代价**：首音延迟理论 +≤200ms（真机未觉明显，可调系数 0.2→0.1 权衡）。**破音排查前两轮连猜连错（底层固有/
> Fish 采样率均证伪）——纪律：必须真机隔离，不凭日志/记忆猜。** 副产物：隔离时切 Doubao，用户听感「Doubao 音色
> 不如 Fish 丰富但质量/自然度更高」→ TTS 选型重新打开为后续候选（memory 已记，不是现在换）。**下一步主线 =
> B 标签器质量（P1）**：真机确认依旧——省略号 `…` 幻觉（合成原文不存在内容/重复旧话）、标签位置错位、`[break]`
> 句中滥用。**⚠️ `.env` 本轮隔离用的 `CYBER_COMPANION_VOICE_TTS` / `EXPRESSION_TAGGER` 已全部还原正常配置。**
> **2026-06-24（第五十七轮）**：**P14 Phase 4 已 commit 落地（`a1232b4` + `d153991`）**。①坐实首音延迟卡点
> 是 TTS 自带 `SimpleTextAggregator` 的句末 lookahead（**不是**上轮猜的 `AggregatedFrameSequencer`）——遇句末
> 标点要等下一个字符到达才确认边界，第 1 句因此被卡到第 2 句标签调用完成。②修复 = processor 改推
> `AggregatedTextFrame`（直通 `_push_tts_frames`、跳过 lookahead），真机首音 **4.9s→~2.5s**，标签效果不退化，
> PASS，commit `a1232b4`（含整套 P0+P1+P2，排除 `_LatencySpikeLogger`）。③**并发预贴标**（每句标签调用并行
> 在飞 + 按序释放 + 中断守卫，+2 测试）commit `d153991`，真机延迟未退化、按序、中断正常。**但真机暴露两个
> 独立新问题**：**A.「破音/音频欠载」**（无标签处也破音、像「耳机没插好」=输出缓冲欠载；与标签器/并发改动
> 无关；并发预贴标消除时序依赖后破音照旧 → 不是时序问题；**下一步主线 P0** = 先做隔离实验「关标签器听破音
> 是否还在」一刀切分清责任）；**B. 标签器质量 P1**（标签位置错位贴标点前/句尾、`[break]`/`[long-break]` 句中
> 滥用、省略号 `…` 幻觉杂音）。**⚠️ `.env` 已还原 `=1`，做 A 实验会临时改 0、测完务必改回 1。** 详见 HANDOFF。
> **2026-06-24（第五十六轮）**：**体检 + A/B + 根因排查，未 commit**。体检确认上一 session 卡死时
> P14 Phase 4 代码（P0+P1+P2）本身完整、真机标签效果已验证 PASS，唯一半成品是 `run_voice.py` 没接
> `CYBER_COMPANION_VOICE_EXPRESSION_TAGGER` 开关——已补全（3 处小改）。借这个开关做真机 A/B：tagger
> ON 首音延迟均值 4.90s vs OFF 均值 2.42s（砍半）。深挖根因发现**首音延迟卡在"第 2 句"标签器调用
> 完成、不是第 1 句**（三组真机数据强相关，差值固定 0.7-0.9s）——OQ1 非对称变体"第 1 句跳过标签器"
> 这个优化**没能**省下首音延迟，疑似 Pipecat TTS 帧排序机制（`AggregatedFrameSequencer`）在等第 2 句
> 文本到位才放音频，未读源码坐实。**下一步 = 选一个修复方向**（坐实机制/并发预贴标/扩大 skip-first/
> 换更快标签模型，4 选，详见 HANDOFF 第五十六轮节），决定后才能 commit。**⚠️ `.env` 里
> `CYBER_COMPANION_VOICE_EXPRESSION_TAGGER=0` 仍是测试用的关闭状态，下次正常用 `run_voice` 前记得还原**。
> **2026-06-24（第五十五轮）**：**P14 Phase 4（语音双 LLM）开工**。先跑探针证伪——把文字路径好 prompt
> 搬进语音单阶段 Grok（改 `companion_brain.py` `VOICE_MODE_INSTRUCTION`）后 `--repeats 25 --extended`
> 重测：短回复/多轮 opening_only 明显好转，但 `long_narrative`（立 Phase 4 的头号理由）repeat 退化
> **60%→60% 纹丝不动**、tagged_ratio 0.16→0.10 → **坐实是任务结构问题、必须两阶段**。随后定形态 B +
> 三个 OQ（OQ1=简化变体「所有句子都交标签器、效果不行再换非对称」、OQ2=整段已说作 prior_context、
> OQ3=Gemini）。**P0（`apply_expression_tags_to_sentence` 离线流式逐句标签器函数 + 8 单测，25 passed）
> 已完成**。随后**同 session 把 P1（`ExpressionTaggerProcessor` + 管线装配）+ P2（brain 停止自贴标签）
> 代码也全部写完，**595 pytest 全绿，全部未 commit**。新建 `expression_tagger_processor.py`（增量断句 +
> 整段已说 prior_context + `_turn_id` 中断守卫 + 每句 to_thread 调 Gemini 标签器），插在 `run_voice.py` 的
> `boxi_transcript_tap` 之后/`tts` 之前（字幕纯文本、TTS 拿带标签）；`VOICE_MODE_INSTRUCTION` 移除全部标签
> 规则（覆盖探针 prompt）。**下一步 = 真机验证语音两阶段链路**（用户跑 `run_voice`，照 HANDOFF「真机验证
> 清单」5 条听感判断；PASS → commit 排除 `_LatencySpikeLogger`，不行 → 按 OQ1 换非对称方案）。
> **2026-06-24（第五十四轮）**：**P11-P2（历史消息译文持久化）已完成并真机验证 PASS，已 commit `73e996a`**。
> `/architect` 拆解后发现 scope 比旧描述更精确——读取侧 `store.py` 不需要改（metadata 已整体透传），
> 真正改动在 `chat_persistence.py`（`persist_chat_turn` 新增 `translation` 参数）+ `main.py`（两条聊天
> 路由传参）+ 前端 `chat/types.ts`。**实施中发现并修复一个隐藏 bug**：`/chat/stream` 路径原本在
> `_finalize_streamed_turn` 落库**之后**才计算翻译，导致流式路径翻译永远来不及落库——已把翻译计算挪
> 进该函数内部解决。新增 2 个回归测试，579 pytest 全绿，真机验证（刷新页面后译文仍在）PASS。**P11 全部
> 完成（P0+P1+P2）**。同轮用户还直接请求清空 `messages` 表（已备份，211 条记录清空，不影响 mood/
> relationship/memories）。**下一步**：P14 Phase 4（双 LLM）。详见 HANDOFF。
> **2026-06-23（第五十三轮）**：**P15（Pipecat 双方字幕）全部完成（P0+P1）并真机验证 PASS，未
> commit**。`/architect` 拆出 P0（后端）+ P1（前端）；新建 `backend/realtime/transcript_broadcaster.py`
> （`TranscriptBroadcaster` + 两个旁路 tap，用户句 tap 插在 `brain_processor` 前、Boxi 句 tap 插在
> 之后），`pipeline_router.py` 新增 `WS /realtime/transcript`；前端新建 `voice/useVoiceTranscript.ts`
> 订阅该 WebSocket，`App.tsx` 复用现有聊天气泡样式渲染字幕。用户拍板：场景=本机调试、通道=WebSocket
> （为以后双向打断信号留口子）、前端渲染复用现有气泡样式。两轮真机验证均 PASS（后端事件正确收到、
> 语音行为不受影响；前端字幕正常显示、关闭后消失无报错）。**下一步**：P11-P2（译文持久化）/ P14
> Phase 4（双 LLM），详见 HANDOFF。
> **2026-06-23（第五十二轮）**：**P11-P1（前端：双语开关 + 气泡展示）已完成并 commit `7393efe`**。
> EN/JA 两档真机验证通过；用户拍板「历史译文消失暂可接受，后面补」+「toggle 只影响新消息」+
> 「切换语言不重翻已显示内容」。**P11 全部完成（P0+P1）**。真机验证时新发现一个未排查小 bug
> （JA 档下 Fish 偶发脏标签 `[ zufrieden]`），已记录，无优先级，留给以后排查。
> 同轮新增**日语 Fish Audio 音色试听**（新建 `backend/scripts/ja_voice_audition.py`，commit `41fa0eb`，
> 用法同 `tagger_eval.py --voice`）——两批共 11 个候选音色试听完，结果落 memory
> （`fish-audio-ja-voice-shortlist`，独立于中文清单，未接后端按语言切换）。`config/tts.json` 的
> `fish_audio.voice` 中途多次切换试听，**最终切回中文主选「慵懒偏低音」`ef5c98bdc…`，无净改动**。
> 同轮还清掉了第五十/五十一轮遗留的几个未提交小尾巴，分 3 个 commit 落地：`255a063`（锁死 Pipecat
> latency=balanced，选择性 stage 排除 `_LatencySpikeLogger`）、`94d40dc`（文字聊天 latency 改回
> normal + `.gitignore`）、`0c1d01f`（语音路径标签退化率统计脚本）、`f7204f9`（P9-P2-B 生产素材池 +
> 验证报告）。`_LatencySpikeLogger` 仍按用户要求留在工作区未提交。
> **下一步候选**：① P11 译文持久化（历史消息刷新后译文消失，small 任务）；② P15（Pipecat 双方字幕，
> 新立项）；③ P14 Phase 4（双 LLM，epic 最大块）。详见 HANDOFF。
> **2026-06-23（第五十一轮）**：**P11-P0（后端：翻译模块 + 双语开关接入）已完成并 commit `2d79671`**。
> `/architect` 把 P11 拆成 P0（后端）+ P1（前端），用户拍板「双语生成方式用第二个模型（Gemini）分担、
> 不让主 LLM 背翻译任务」+「全局 toggle（开/关 + en/ja）」+「信笺模式先不动」+「toggle 状态 localStorage 持久化」。
> 新建 `backend/app/tts/translator.py`（复用 `expression_tagger.py` 的解耦骨架，独立调 Gemini 把主回复
> 翻译成中文，失败硬性降级为 `None`，不阻断主回复）；`context_builder.py` 的 `build_provider_context` 加
> `target_language` 参数，开启时注入 `[Output language]` 指令；`/chat/complete` + `/chat/stream` 两条路由
> 接入，response/SSE meta 新增 `translation` 字段；关闭时（默认）零行为变化。577 pytest 全绿（561+16）。
> **下一步 = P11-P1（前端）**：开关 UI（en/ja + localStorage 持久化）+ 气泡双语展示，详见下方 P11 节。
> **2026-06-23（第五十轮）**：**P14 Phase 5 P1 结案 = 放弃 normal，锁死 balanced（P13 won't fix）**。
> route A（subclass 救 normal）真机验证仍失声 → 根因纠正（normal 是「服务端整段批量渲染」，首字节 ~3.5s
> 超过 pipecat 3.0s 队列超时 `_stop_frame_timeout_s`）→ A/B 实测确认 normal 音质提升微小、不值每轮 ~3 秒死寂
> → `run_voice.py` 只允许 `balanced`，拒绝 `normal`/`low`（未 commit，6 tests 绿）。**P14 epic Phase 1+2+3+5
> 全部结清**，剩 Phase 4 双 LLM（其延迟杠杆设计要据「锁 balanced 流式」重估）。**用户新需求两条，已定优先级**：
> ① **P11 文字双语回复 = 队首（下一步先 `/architect`）**；② **P15 Pipecat 双方字幕（新立项）**。详见 HANDOFF。
> **2026-06-23（第四十九轮）**：`/architect` 把 **P14 Phase 5** 拆成 P0（删 `low` latency 选项）+
> P1（修 P13 normal 失声）。**P0 已完成并 commit `507c9e9`**——消掉 `PIPECAT_AUDIT.md` 审计唯一 🔴；
> 新增 3 个回归测试。**P1 用户已选路线 A（subclass `FishAudioTTSService`）**，但需真机验证、medium diff，
> 留独立 session。详见 HANDOFF 和下方 Phase 5 节。
> **2026-06-23（第四十七轮）**：用户决定开一个大 epic **P14 · Pipecat 链路最大化**（全量读 Pipecat +
> Fish Audio Pipecat 文档 → 审计现有链路配置是否最优/正确 → 批量测试 → 双 LLM 决策讨论 → 修 P13）。
> 本轮只做了 epic 拆解 + 落 TASK_QUEUE，**未开工**。已确认这是多 session epic，每个 phase 一个干净
> session。下一步 = `/clear` 后新 session 做 **P14 Phase 1（文档全量落盘）**。本轮联网研究已经预先拿到
> 几个关键事实（写进下方 P14 节，避免新 session 重复 derive）。详见 HANDOFF。
> **2026-06-22（第四十六轮）**：**P8-C spike round 2（扩大样本量）已完成，结论反转——确认推进两阶段
> 拆分**。第四十五轮的 spike（N=8，只测 4 个孤立单轮 fixture）得出"标签退化率初步不比文字路径差"，
> 本轮在 `companion_brain_tag_eval.py` 新增 3 个场景 fixture（真实多轮历史/长篇展开/单轮情绪转折）+
> 把样本量提到 N=25（单轮）/N=10（长篇）/N=15（多轮），结果推翻了原结论：①原 4 个 fixture 在 N=25
> 下 opening_only 退化率 16%–24%，比 N=8 测出的 12.5% 高近一倍，也明显高于文字路径基线（4%–12%）；
> ②**长篇展开场景退化严重**——60%（6/10）样本出现同标签重复堆叠，整篇平均仅 16% 句子带标签
> （短回复场景普遍 65%–80%）；③真实多轮历史场景 opening_only 退化率 33%，比孤立单轮还高。**结论：
> 语音路径标签退化明显比文字路径差，长篇/多轮场景下更严重，确认推进 P8-C 两阶段拆分**，下一步
> 先选延迟杠杆（B/C/D，见 P8-C 节）。详见 HANDOFF。
> **2026-06-22（第四十五轮）**：**P8-C 前置 spike 已完成（延迟基线+标签退化率统计），结论喜忧参半**——
> 延迟换 provider 后基本没变（~2.2s vs 旧基线 2.3s）；标签退化率（N=8）初步不比文字路径差，削弱了
> "必须现在做两阶段拆分"的紧迫性，但样本小，优先级待用户决定。过程中**发现一个新真实 bug（P13，
> 高优先级未修）**：Pipecat latency=normal 时多轮对话会失声；**还发生了一次生产数据库污染事故**
> （两次"隔离"测试因 `load_dotenv(override=True)` 失效都写进了生产库）——**已完整清理还原**，并建立
> 了强制隔离测试规范（必须改 `.env` 文件，不能用命令行环境变量）。另外正式立项 **P12**（情绪识别
> 旁路 Hume prosody）+ 收紧 **P11** 范围（仅文字路径，新增需同时显示中文译文的需求）。详见 HANDOFF。
> **2026-06-22（第四十四轮）**：**生产素材池已建好 + P9-P2-B 真机验证完成，结论 PASS**——
> 用户授权 Claude 直接建 `config/idle_material_pool.json`（8条真实可核实素材：5电影+3历史科学
> 新闻）。随后做了 P9-P2-B 真机验证（方法同 P9-P1，临时改 DB 状态测完还原）：idle_experience
> 用真实素材生成的内容贴合人设、未编造细节；share intent 端到端验证通过，两次触发正确轮换了
> 两条不同 idle_experience 记忆，反重复指纹按设计工作。发现两个非阻塞观察项：①commitment_followup
> 优先级链上持续压过 share，生产环境实际触发频率可能偏低；②LLM 产出偏"复述"原文，可后续微调
> prompt。完整报告见 `docs/P9_P2B_VERIFICATION.md`。**P9-P2-A/B 全部完成（设计+实现+测试+
> 真机验证）。下一步：讨论是否启动 P9-D（投递层 epic）**，或先做 P9-P2-C（真联网素材源）。详见
> HANDOFF。
> **2026-06-22（第四十三轮）**：**P9-P2-A 已 review + commit（`be2a81d`）+ P9-P2-B（share intent）
> 已完成并 commit（`9890ca4`）**——`/architect` 拆出 P0（决策：share 插在
> `commitment_followup → share → memory_callback`；消费语义=FIFO 反重复指纹，非一次性永久消费）+
> P1（实施）。`proactive_reason.py` 新增 `_pick_share()`/指纹工具函数，`proactive_opener.py` 在
> LLM 生成成功后才消费指纹（失败/禁用不消费，与 fallback 文案不泄露具体素材内容一致）。
> 557 pytest 全绿（545+12）。**下一步：`config/idle_material_pool.json` 真实素材池待用户手动
> 补充**——补好之前 share intent 长期空转（池空自动降级，不报错但也不会真的触发）。详见 HANDOFF。
> **2026-06-22（第四十二轮）**：**P9-P2-A（idle_experience 写入机制）已完成，未 commit**——
> 新增 `idle_experience` memory type（不进 `FACTUAL_MEMORY_TYPES`）；`resolve_idle_experience_write()`
> 镜像 `resolve_proactive_opener()` 的路由层编排模式，零行改动 `engine.py`；节奏门控（日配额+最小
> 间隔）+ 素材反重复指纹；LLM 生成严格约束在白名单素材池范围内（防编造），素材源接口可插拔，
> 为后续升级真联网（P2-C）留好替换点。当前只有 `idle_material_pool.example.json` 模板，生产真实
> 素材池待用户后续补充。545 pytest 全绿（535+10）。**下一步：先 review/commit 本轮 diff，再启动
> P9-P2-B**（share intent）。详见 HANDOFF。
> **2026-06-22（第四十一轮）**：**P9-P1 真机验证已完成，结论 PASS**——三档语气递进清晰，赌气档
> 傲娇但黏着、无冷淡用词；反重复指纹按 `(kind,tier)` 记录、同指纹连续命中不阻断发送，与设计一致。
> 已知限制：只测到 `commitment_followup` 一种 intent，未覆盖另外 3 类轮替（非阻塞）。完整报告见
> `docs/P9_P1_VERIFICATION.md`。**下一步：启动 P9-P2**（"她有自己的生活"）。详见 HANDOFF。
> **2026-06-22（第四十轮）**：**P9-P1（反重复 + 想念轨迹分档）已完成并 commit**——
> commit `aca291d`（想念轨迹三档：无聊/想念/赌气，赌气门槛要求 closeness 够高，档位正交于
> intent 上色全部 4 类 ProactiveReason）+ `8f4ba8e`（反重复指纹：`(kind,tier)` 组合 FIFO 存
> `mood_state.metadata`，本轮只落地写入/读取机制，未改选择逻辑）。535 pytest 全绿。同时纠正了
> 第三十九轮 HANDOFF 误报「P9-P0 未 commit」的过期描述，并补提交了第三十六轮遗留的 P10-P0
> 工具（`039ea9d`）+ TTS 音色配置（`0d228c0`）。**P9-P1 真机验证未做**——下一步建议先验证
> 真机听感再启动 P9-P2。详见 HANDOFF。
> **2026-06-22（第三十九轮）**：**P9-P0（idle_tick mutter 死分支删除）已完成**——`/architect`
> 读代码后发现实际改动比第三十八轮设想更小：只需删 `_evaluate_idle_tick` 里那一个被
> `_IDLE_MUTTER_ENABLED=False` 短路的死分支，其余 3 条路径本就恒为 `decision="observe"`。
> `local_responses.py` 的 mutter 文案**未删**（被 user_message 低价值输入路径复用，删了会破坏
> 正常对话反馈）。512 pytest 全绿，`_evaluate_proactive_check` 零行变化。本轮未 commit。
> 下一步 = **P9-P1**（反重复 + 想念轨迹分档）。详见 HANDOFF。
> **2026-06-22（第三十八轮·讨论）**：讨论 P9 方向 + 情绪识别旁路 + 三个小玩法。决定：①新增 **P11**
> （回复语言切换）；②**Obsidian/电脑链接**进「后续讨论名单」待详细讨论；③**联网功能合并进 P9**
> ——不挂回复链路，做成 idle-tick 的「想分享」intent 的素材来源（见 P9 节末「联网合并洞见」）；
> ④**情绪识别（Hume prosody）**结论：只取测量 API 当传感器（绝不用 EVI/Inworld 整套替换 soul），
> 价值集中在语音路径的声学情绪，走 off-path 旁路喂 kernel，列第二档先 spike 验证再接。本轮对 P9
> 跑了 `/architect`（见下）。
> **2026-06-22（第三十七轮）**：**P10-P1（`--repeats N` 统计基线）已完成**——N=25 正式基线，
> 4 个 fixture 退化率 4%–12%，结论"暂不支持标签器结构改造"。**TTS 音色 config 已落地**
> （`fish_audio.voice` = 慵懒偏低音 `ef5c98bd…`，用户表态会经常换）。新增两个候选音色盲听：
> 「夜晚02」`b6681a52…` 入备选，`be404a1e…` 淘汰。**⚠️ 未解决矛盾**：04（揶揄+心软）场景真机
> 盲听确认过"欠标"，但 N=25 统计上反而最干净——下次真机再撞到要当场记录完整输入。详见
> HANDOFF「本轮已完成」。
> **2026-06-21（第三十六轮）**：**P10-P0（离线评估夹具 `tag_stats.py` + `tagger_eval.py`）已
> 完成**——把"重复贴同一标签/堆开头/欠标"从主观听感变成可重复指标+夹具。真机发现：清洁基线下
> 退化"时好时坏"不是稳定发生，需 `--repeats N` 统计而非单跑判断（下一步建议）。顺带完成 Fish
> Audio 音色盲听 A/B 定稿（主选3+备选5，详见 HANDOFF）。详见 HANDOFF「本轮已完成」。
> **🎯 当前最高优先：P8 · TTS 情绪标签两阶段表达层架构** —— **文字聊天路径（P8-A+P8-B）已完成并真机验证 PASS**，
> 语音 Pipecat 路径待做（不急，可先观察文字聊天路径稳定性）。
> **2026-06-21（第三十五轮）**：**P1（标签器喂入 tone_intent 自然语言字段）真机验证完成 — 结论：
> 无明显改善，已回退**。同样用隔离 A/B 跑 4 个场景，没有一个明显支持"带 tone_intent 更好"，
> 且部分场景复现了 P0 那种"标签退化成重复贴同一个标签"的失败模式。代码已完全回退到 P8-B 基线。
> **关键判断**：P0（数值）、P1（自然语言）两种不同输入方案都失败、且都出现同一种退化模式——
> 指向根因可能不在"喂什么输入"，而在标签器（当前 Gemini）执行"逐句判断"这条规则的稳定性。
> 下一步建议讨论是否换标签器模型或重新设计标签器执行结构（并入 P10），不建议再试第三种
> "喂更多意图信息"的变体。详见 HANDOFF。
> **2026-06-21（第三十四轮）**：P0（标签器喂入同轮 BOXI_SIGNALS）真机验证完成 — 结论：改动有害，
> 已回退（详见上方第三十五轮记录的延续判断）。
> **2026-06-21（第三十三轮）**：讨论确认 TTS engine 选型收敛——用户实测 Western 可控 TTS/端到端
> 路线均不行，继续走 Fish Audio + Pipecat 级联（不要再建议换 engine，见 HANDOFF）。
> **2026-06-21（第三十二轮）**：真机使用驱动的修复轮，详见 HANDOFF。标签器 DeepSeek→Gemini + prompt
> 规则矛盾修复；`tone.py` 语速抑制 bug 修复（硬编码词表→通用标签检测）；persona 新增"不旁白"硬规则；
> 新发现并临时止血了 idle-tick mutter 刷屏 bug（**P9**，待重新设计，已禁用未删除）；记录 **P10**
> （标签器模型+Fish Audio 潜力，用户后续可能继续探索）。本轮还做了几次数据库清空（messages/
> conversation_summaries/memories/mood_state/relationship_state，已备份到 `data/backups/`），
> 不在 git 历史里，详见 HANDOFF「数据库状态变更」。
> P0（VM-6）/ P1（VE-2）/ R9 / R10 / P2（VE-1）/ R12（反编造）/ 信笺 UI P0 + P1 + P1-B + P1-C / **P5-A-1** / **P6（全部子任务）** / **P7（Pipecat 前端入口）** 均已完成。
> P5-A（Venice）已取消（溢价太高）。
> **2026-06-20（第三十一轮）**：**P8-A（表达层标签器模块）+ P8-B（接入文字聊天路径）已完成**——
> 新建 `backend/app/tts/expression_tagger.py`，主 LLM 不再背标签任务，独立 DeepSeek 调用专职插标签。
> 真机验证时用户顺带发现「长回复 TTS 播放中断」bug（与 P8 无关，预先存在），排查出两层根因并都已修复：
> ①`/tts/stream` 硬编码 `media_type=audio/mpeg` 但 Fish Audio 实际吐 opus（`stream_mime_type()` 新方法）；
> ②前端不必要地把长回复切成多个独立 HTTP 请求顺序播放，违反 Fish Audio 官方"整段一次性传入"的推荐用法
> （移除 `textChunksForSpeech` 切段逻辑，`max_speech_chars` 120→4000）。用 Fish Audio 官方 realtime
> streaming 文档（新增到 `docs/FISH_AUDIO_REFERENCE.md` 第9节）确认了"文字聊天不需要 WebSocket，
> HTTP streaming 整段传才是官方推荐做法"。496 pytest + 25 前端 vitest 全绿，真机（含浏览器 preview 工具
> 端到端验证）PASS。**本轮未 commit，等用户实际听感confirm 再一起 commit**。详见 HANDOFF。
> **2026-06-20（第三十轮）**：**P8 前置（Fish Audio 全量文档深度研究）已完成**——
> 产出 `docs/FISH_AUDIO_REFERENCE.md`（标签系统+phoneme+生成参数完整参考），新发现 `latency` 实际3档/
> WebSocket `FlushEvent`/`chunk_length`默认值官方文档不一致等，详见 HANDOFF。
> **2026-06-20（第二十九轮）**：第二十八轮全部改动（P5-C~P5-H + Provider 选型 + 漏 commit 的 P5-B-2）
> 已真机验证 + 按主题拆 5 个 commit 落 master（`d39f6c8` `9f85fc7` `ca69cb9` `ab4d64d` `1dd96cb`，详见 HANDOFF）。
> 验证发现 Fish 标签问题比预期更深（mood 快照式贴标签 + 音效类标签位置精度要求更高），
> 触发了「P8 前置」任务（现已完成）。
> **2026-06-19（第二十四轮）**：
> - ~~**system prompt 重写**~~ ✅ 完成，commit `3533414`——存在论框架 + 四条纪律 + 成年虚构框定 + 格式纪律（去掉长度限制）。
> - **OpenRouterProvider 新增** ✅ 完成，commit `85bc37a` + `496e995`——`allow_fallbacks=false`，`_extra_payload_params()` 钩子。
> - **`disable_existential_block` 标志** ✅ 完成，commit `448c784`——临时人设可屏蔽存在论注入，测试隔离修复。
> - ~~**provider 选型（第二轮）**~~ ✅ 已完成（第二十八轮）：DeepSeek ❌ 文学天花板低；Claude ❌ 延迟高+干瘪；最终选定 `x-ai/grok-4.20`（via OpenRouter）。`config/persona.json` 已删，存在论人设已恢复。
>
> **2026-06-19（第二十五轮）— 未 commit，待下一 session commit**：
> - **persona 格式纪律调整**：`persona.example.json` + `persona.json`——删"动作放（）"，改为明确禁令；加"说话方式：口语，自然，不做客服"；伴侣人设加"感受就是感受，直接说"。
> - **TTS strip 简化**：`text_cleanup.py` `_strip_stage_directions` 削减为只 strip 半角 `(...)`，`[#指令]` 现在内联透传给 doubao。
> - **Pipecat TTS 去抽取**：`doubao_streaming_tts_service.py` 删 `extract_voice_instruction`，全文含 `[#...]` 直传合成。
> - **文字聊天 TTS context_texts 修正**：`/tts/stream` 加 `user_message` 参数，前端 `submitToBackend` 传用户消息，作为 doubao `context_texts` 对话上下文（回退 `tts_emotion_directive()`）。
> - **验证**：465 pytest passed，tsc --noEmit 零错误。

---

## 信笺 UI 方向（新增可切换模式，不删旧 UI）

- **方向已定**：用信笺/typography 视觉语言，替换/共存于现有 Chat UI；旧 UI 保留为默认，加 toggle 切换。
- **~~P0 · React 化骨架~~** ✅ 已完成并 commit (`4858125`)。新增 `frontend/src/letter/`
  （`LetterView.tsx` + `useTypewriter.ts` + `scripts.ts` + `LetterView.css`，`.letter-spike` 前缀隔离样式）。
  `tsc --noEmit` 通过；vite dev 截图验证 4 个 mood 切换/打字机/sketch 表情均正常，无 console 错误。
- **~~P1 · 接入 App.tsx，作为可切换 Chat 视图~~** ✅ 已完成（本轮，待 commit）：
  - `uiMode: 'classic' | 'letter'` state 加入 App.tsx（默认 `classic`）。
  - chat-header 新增 `.letter-toggle-button`（文案"对话"/"信笺"），点击切换。
  - letter 模式：渲染 `<LetterView />`，隐藏输入框（用户决策：letter 模式不发消息）。
  - classic 模式：原消息列表 + 表单完整保留，messages state 不丢失。
  - LetterView mood 由内部按钮自管理（未接 backend mood，P1-B 任务）。
  - `tsc --noEmit` 通过；vite dev 切换截图 PASS；console 零错误。
- **~~P1-B · backend mood → LetterView~~** ✅ 已完成（本轮，待 commit）：
  - `LetterView.tsx` 新增 `mood?: LetterMood` prop；`activeMood = externalMood ?? mood`；有外部 prop 时隐藏 picker。
  - `App.tsx` 新增 `letterMood` state + useEffect（`uiMode==='letter'` 时 one-shot fetch `/memory/mood`，映射传入）。
  - 映射：`sad|worried|angry→fragile`，`happy→excited`，`annoyed→hesitant`，其余→`calm`（TODO 注释标记）。
  - `tsc --noEmit` 通过；preview 验证：picker 隐藏，mood 正确映射，console 零错误。
- **~~P1-C · 真实 Boxi 消息驱动打字机~~** ✅ 已完成并 commit（`22e7f77`）：
  - `useTypewriter.ts` 新增 `externalText?: string` + `hasExternalTextRef` + useEffect（externalText 变化触发打字机）。
  - `LetterView.tsx` 新增 `text?: string` prop，传入 `useTypewriter`。
  - `App.tsx` 新增 `lastBoxiText = useMemo(...)` + `<LetterView text={lastBoxiText} />`。
  - preview 验证 PASS：真实 Boxi 回复以打字机节奏呈现，mood 映射正确，console 零新错误。
- **P2 ·（待用户回答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个开放问题后）**：精细化 mood 映射 + Voice 模式信笺呈现。

---

## ~~R12 · 文本聊天反编造修复~~ ✅ 已完成并真机验证 PASS，已 commit (`6127000`)

---

## ~~P0 · VM-6 收尾~~ ✅ 已完成
跨会话召回 PASS，详情见 HANDOFF。可选后续优化（不阻塞）：分数融合权重/14天无衰减期（需 API，
console UI 未找到入口）、旧 `friend` 库历史数据迁移、API Key 轮换（R8，安全卫生）。

## ~~P1 · VE-2 纯 E2E 情绪通道核实（解决 R1）~~ ✅ 已完成
设备 A/B 已做，结论 inconclusive，决定保留现状不清理代码。详情见 HANDOFF R1。

## ~~R9 · mood 面板异常修复~~ ✅ 已完成并真机验证 PASS
根因：`apply_user_message_mood_delta` 正常对话分支缺少 annoyance 衰减/energy 回升路径，导致两者
单向钳到极值卡死（annoyance→1.0, energy→0.0），且会影响 `tone.py` 的实际情绪投射。已在
`backend/app/behavior/mood.py` 补上回落/回升路径（4 行 diff），41 个相关测试 passed。
用户真机验证：心情面板已能正常波动，不再卡 100%/0%。

## ~~R10 · 语音连接初始情绪烦躁排查~~ ✅ 已完成并真机验证 PASS
根因：`relationship_state.tension≈0.42` 长期停留在 `_TENSION_SHARP=0.4` 阈值附近（与 state_block
"、有点别扭"文案共用同一条线但被复用为 register 判定），导致每次 RTC join-time 读取到的
tension≥0.4 就被判为 `real_sharp`（"更冲、更短"），与 annoyance/mood 无关。
修复：[tone.py:31](backend/app/behavior/tone.py:31) `_TENSION_SHARP` 0.4→0.55（state_block 的
`_TENSION_AWKWARD_THRESHOLD=0.4` 不动）。同步改 3 处测试 tension=0.5→0.6，新增
`test_mild_tension_does_not_trigger_real_sharp`（tension=0.42）。
`pytest backend/tests/test_tone.py backend/tests/test_rtc_state_block.py` 52 passed；
`-k "mood or engine or behavior or tone or rtc"` 138 passed。用户真机验证：不再感觉"冲"。

## R11 ·（搁置，等待用户可访问 VikingDB）纯 E2E 长期记忆部分失忆
- **Scope**：用户确认具体案例——Boxi 不记得用户在新西兰（很久以前提过）。用户判断"应该是直接忘掉了"
  （疑似写入侧从未存入，非检索/U3 问题）。涉及 `backend/app/rtc/viking_memory.py`、
  `backend/app/rtc/routes.py` `/rtc/memory/session`。**先评估，不直接重写**。
- **已 `/architect` 拆出方案**：
  - **R11-A（先做）**：前端触发链路确认——语音结束后是否一定调用 `/rtc/memory/session`
    （读 `frontend/src/voice/` + `routes.py:306-345`），定位那次会话是否成功 AddSession。
  - **R11-B（视 A 结论）**：核对 `VIKING_MEMORY_TYPES` 配置与 Viking 实际抽取结果是否对得上
    "用户在新西兰"这类事实（与 U3 相关）。
- **阻塞**：用户当前手机不在身边，无法登录 VikingDB 控制台核实记忆库内容，本轮主动搁置。
  下一 session 若用户已能访问，从 R11-A 开始。

## ~~P2 · VE-1 收尾~~ 基本完成（playful 待补测）
- ① 真机听 comfort/real_sharp ✅ **PASS**（"贴合情绪"），见 HANDOFF。playful 因
  `relationship.closeness=0.66` 差 0.01 到阈值 0.67（无写接口，未造数据）暂未测，
  待 closeness 自然达到 ≥0.67 后补测。
- ② `/tts/stream` 与 `/tts/synthesize` 情绪对齐 ✅ 已完成。
- ③ 路由级集成测试 ✅ 已完成。
- **本轮副产物**：测试中发现并修复阻塞 bug——`doubao.py` 的 `req_params.additions` 需为 JSON
  字符串而非嵌套 dict（之前单测 mock 掉真实 API 未测出）。详见 HANDOFF。

## P3 · VE-3 IgnoreBracketText → 前端情绪 cue（later）
- **Scope**：Boxi 把动作/情绪写进括号 → TTS 不读、随字幕下发驱动前端 cue（与最终画面解耦，先做信号层）。
- **阻塞**：需用户先补文档 `6348/2386107（传递自定义指令）`。
- **验收**：括号指令不进语音、能在前端拿到并触发一个 cue。
- **要读**：`docs/VOICE_EMOTION_MEMORY_PLAN.md`、`reference/14.md`（IgnoreBracketText 段）、待补的 2386107。

## P5 · Provider 替换

### ~~P5-A-1 · 新增 venice.py + 配置注册~~ ✅ 已完成（2026-06-17，未 commit）
- `backend/app/providers/venice.py` 新建（VeniceProvider，OpenAI-compatible）
- `backend/app/providers/registry.py` +venice 分支
- `config/providers.json` +venice entry（enabled:false，llama-3.3-70b）
- 415 pytest passed，tsc --noEmit 零错误
- **价格**：$0.70/$2.80 per 1M (in/out)，比 DeepSeek 贵 5x/10x，绝对量小可接受

### ~~P5-A-2 · 切换默认 + 冒烟验证~~ ❌ 取消
- 用户决定不使用 Venice，后续考虑换其他 provider。

### ~~P5-B · TTS → Fish Audio（文字聊天路径）~~ ✅ 已完成（2026-06-19，第二十六轮）
- `backend/app/tts/fish_audio.py` 新建（FishAudioTTSProvider，s2-pro，opus，emotion bracket，prosody.speed）
- registry 注册，tts.example.json 加模板条目，473 pytest passed
- 情绪：context_texts[0] 包进 `[phrase]` 前置文本，S2-Pro 自动读取
- speed 映射：`prosody.speed = 1.0 + speech_rate * 0.025`，钳位 [0.5, 2.0]
- 实机验证：文字聊天有音频输出 ✅

### ~~P5-B-2 · Pipecat TTS → Fish Audio（语音路径）~~ ✅ 已完成（2026-06-19，第二十七轮）
- `run_voice.py` 的 `_build_tts("fish_audio")` 换成官方 `FishAudioTTSService`（WebSocket + ormsgpack）
- 自写 HTTP 版 `fish_audio_tts_service.py` 已删除

### ~~P5-C · 文字聊天 TTS 情绪 soul-authored~~ ✅ 已完成（2026-06-19，第二十八轮）
- `context_builder.py` 新增 `TEXT_CHAT_TAG_INSTRUCTION` + `append_text_chat_tag_instruction()`，对齐 Pipecat 的 `VOICE_MODE_INSTRUCTION` 做法
- `fish_audio.py` 移除 `_DIRECTIVE_TAG_MAP` 映射前置，标签由 LLM 自写、直接透传
- `App.tsx` 新增 `stripLeadingFishTags()`，聊天气泡 + LetterView 展示层隐藏标签
- 477 pytest passed，tsc 零错误；**浏览器真机验证未做**，下一 session 第一件事

### ~~P5-D · 长度限制打开（Pipecat + 纯 E2E RTC）~~ ✅ 已完成（2026-06-19，第二十八轮）
- `companion_brain.py` `VOICE_MODE_INSTRUCTION` 删"一句话…简短（必要时最多两句）"
- `persona.example.json` `rtc_character_manifest` 删"话少而冲一次最多一两句"+"简短"/"尽量短"，只删长度
- **`core_persona` 字段、括号动作约定均未动**——用户明确要求 `core_persona` 暂不改，见 HANDOFF「用户要求的提醒」

### ~~P5-E · speech_rate 死代码修复~~ ✅ 已完成（2026-06-19，第二十八轮，审查时发现的真实 bug）
- `main.py` 的 `/tts/synthesize`、`/tts/stream`：mood→speech_rate 计算原本整段被 `if provider_name == "doubao":` 包住，
  Fish Audio 成为默认 provider 后该分支永远不执行，`speech_rate` 恒为 0，语速从未随情绪变化
- 修复：speech_rate 计算移出 if 块（provider-agnostic），`context_texts`（doubao 专属短语）仍只在 doubao 分支赋值
- 新增回归测试 `test_tts_stream_mood_speech_rate_reaches_fish_audio`，477 pytest passed

### ~~P5-F（P0）· 长度+标签指令重写~~ ✅ 已完成（2026-06-19，第二十八轮，核对 Fish Audio 官方文档后）
- `VOICE_MODE_INSTRUCTION`（companion_brain.py）：长度改内容驱动（默认1-3句，深聊/讲故事可展开，不设硬上限）
- 两个指令（+`TEXT_CHAT_TAG_INSTRUCTION`）都改为允许多句/情绪转折处重复加标签（不再只是开头一组），加官方 `[in a hurry tone]` 标签
- `App.tsx` 故意不动——用户决定文字聊天多标签先暴露在气泡里，方便肉眼核对标签位置对不对
- 479 pytest passed（含 P5-G）

### ~~P5-G（P1）· speech_rate 数值兜底让位 Tone Marker 标签~~ ✅ 已完成（2026-06-19，第二十八轮）
- `tone.py` 新增 `TONE_MARKER_TAGS`（`[in a hurry tone]` `[shouting]` `[screaming]` `[whispering]` `[soft tone]`）+ `contains_tone_marker_tag()`
- `main.py` 两处路由：文本含 Tone Marker 标签时强制 `speech_rate=0`，让标签主导节奏，不含时维持 mood 驱动数值兜底
- **Pipecat 不做数值语速改动**——WebSocket 协议 `prosody.speed` 只能在 `start` 事件设一次，逐句更新需整个断连重连，已与用户确认放弃
- 新增 2 个回归测试，479 pytest passed

### ~~Provider 选型（第二轮）~~ ✅ 已完成（2026-06-19，第二十八轮）
- 最终选择：LLM = `x-ai/grok-4.20`（via OpenRouter），TTS = Fish Audio
- `config/persona.json`（临时人设）已删除，存在论人设已恢复并验证

### ~~P5-H · 标签指令多轮迭代（含路径A精简）+ 前端显示标签 + temperature~~ ✅ 已完成（2026-06-19，第二十八轮，临时状态）
- 标签指令经历：多句多标签 → 69 全量+phoneme → **最终精简到 13 情绪+5 音调+5 音效 + 硬性要求(≥3句正文必须出现非开头标签) + 正反示例**
- `App.tsx` 去掉 `stripLeadingFishTags()` 调用 → 聊天气泡现在**显示**标签（函数保留），用户用于肉眼核对标签位置
- `fish_audio.py` 加 `DEFAULT_TEMPERATURE=0.85`（官方默认 0.7），待用户实测听感
- ⚠️ **实测结论：纯 prompt（含精简版）无法稳定纠正"标签只堆开头"——是任务结构问题。用户否决"精简掉 Fish 潜力"方向，定为走两阶段架构（见 P8）。当前指令是临时可用状态。**

## ~~P8 前置 · Fish Audio 全量文档深度研究~~ ✅ 已完成（2026-06-20，第三十轮）

> **触发**（第二十九轮真机验证）：标签问题比预期更深，不只是"位置"——①标签像抄 mood 持续快照非逐句
> 判断；②音效类标签比语气类标签对位置精度要求更高。用户要求深度+完整解析 Fish Audio 全部官方文档。
>
> **产出**：`docs/FISH_AUDIO_REFERENCE.md`（8 节 + 附录，定稿）——S2-Pro vs S1 语法边界、语言质量分层、
> 标签 6 类词表+扩展词表、"触发真实声音 vs 仅影响演绎"分类、位置规则、phoneme 三语言语法、官方完整
> 生成参数表（含新发现：`latency` 实际3档/WebSocket `FlushEvent`/`chunk_length`默认值文档内部不一致）、
> 已知限制清单。来源覆盖 docs.fish.audio 官方文档站 + fish.audio/blog 技术博客 + GitHub README 交叉验证。
> 详见 `docs/HANDOFF.md`「本轮已完成」。

## P8 · TTS 情绪标签两阶段表达层架构

> **根因**：一次 LLM 生成同时背 7 类认知任务（人格/状态/记忆/格式/BOXI_SIGNALS/Fish标签/长度），
> 创作类与标注类抢注意力 → Fish 标签退化成只堆开头。**实测确认纯改 prompt 治不好。**
>
> **方案（详见 `docs/HANDOFF.md`「架构决策」节）**：内容/表达两阶段解耦——
> - 决策层 = behavior engine（已有，纯代码）
> - 执行层 = 主 LLM(Grok) 写纯文本+BOXI_SIGNALS，prompt 不含 Fish 标签规则
> - 表达层 = 独立标签器调用（DeepSeek），prompt 只有标签规则 → 释放 Fish 全部潜力（完整词表+规则见 `docs/FISH_AUDIO_REFERENCE.md`）
>
> **关键边界**：代码只能强制标签「格式/位置合法性」，「情绪恰当性」永远靠 LLM。

### ~~P8-A · 表达层标签器模块~~ ✅ 已完成（2026-06-20，第三十一轮）
- 新建 `backend/app/tts/expression_tagger.py`：`apply_expression_tags(text, mood, *, router, provider_name="deepseek")`
- prompt 只含标签规则（全量6类词表+A/B类位置精度区分+逐句判断要求，去掉旧版硬性数量配额）
- 失败/空结果硬性降级返回原文；14 个单测全绿

### ~~P8-B · 接入 /chat/complete + /chat/stream~~ ✅ 已完成并真机验证 PASS（2026-06-20，第三十一轮）
- `context_builder.py` 删除 `TEXT_CHAT_TAG_INSTRUCTION` + `append_text_chat_tag_instruction()`
- `main.py` 两处路由在 `apply_signals_to_kernel` 之后调用标签器替换最终 content
- 493 pytest 全绿，真机验证 2 轮对话 PASS（标签分布+逐句判断两症状未再出现，`[sarcastic]`精确位置验证 A/B 类区分生效）
- 本轮未 commit。详见 HANDOFF「本轮新发现」——验证中观察到 persona 在庆祝语境下输出比预期更显性，
  与本次架构改动无关（未碰 persona 文件），记录供「活人感/审核」话题参考

### P8-C · 语音 Pipecat 路径（✅ 已确认推进，第四十六轮决定，下一步选延迟杠杆）
- 同样的两阶段拆分应用到 `companion_brain.py` 的 `VOICE_MODE_INSTRUCTION`，但语音延迟敏感，
  串行两次调用不能直接照搬文字聊天的做法
- **下一步**：先选定延迟杠杆：B 句子级流水线重叠（真正杀手）/ C 条件触发补调 / D Fish API 层手段
  （`latency="low"`、WebSocket `FlushEvent`、连接预热，见 `docs/FISH_AUDIO_REFERENCE.md` §7.2/7.7）。
  **长篇展开场景退化最严重**（见 round 2 spike），选杠杆时优先确保长回复路径也能稳定走两阶段。
- 要读：`backend/app/tts/expression_tagger.py`（可直接复用）+ `backend/realtime/companion_brain.py`

#### P8-C 前置 spike（2026-06-22，本轮新增，启动 P8-C 实施前必须先做）
> **触发**：读代码确认了 `companion_brain.py` 的 `VOICE_MODE_INSTRUCTION`（`backend/realtime/companion_brain.py:34`）
> 仍是单阶段——主 LLM 自己在同一次输出里写正文+Fish 标签，**没有接入** `expression_tagger.py` 两阶段
> 架构。这正是文字路径在 P8-A/B 之前已实测证明"纯 prompt 治不好标签堆开头"的旧架构，但 Pipecat
> 这条路径**从未跑过 `tag_stats.py`/`tagger_eval.py` 那套统计**，所以"语音侧标签退化到底多严重"
> 目前是未知，不能假设。同时发现现有 latency 基线已过期：P6-C（2026-06-17）测的 ~2.3s 端到端延迟，
> 当时 LLM 还是 DeepSeek、TTS 还是 Doubao streaming，之后 LLM 换成了 grok-4.20（OpenRouter，第二
> 十八轮）、TTS 换成了 Fish Audio WebSocket（P5-B-2，第二十七轮），两个变量都变了但没有重新测过。
- **Scope**：① 用真实 Pipecat 语音对话重新跑一次端到端延迟基线（用户停说→首个音频），拿到对得上
  当前 LLM/TTS 配置的数字；② 把 `tag_stats.py` 的退化指标用到 Pipecat 真实输出上（同样的真机
  多轮对话场景，--repeats N 统计），看标签堆开头/逐句判断不稳是否在语音侧重现。
- **不做**：不在 spike 阶段动 `companion_brain.py` 代码、不提前实施两阶段拆分——先拿到两个数据
  （延迟基线、退化率）再决定怎么拆、选哪个延迟杠杆。
- **验收标准**：输出两份数字（最新端到端延迟 ms 级基线 + Pipecat 标签退化率），供后续选延迟杠杆和
  决定拆分方式时引用，不要求本 spike 阶段就有结论性方案。

#### P8-C spike round 2 · 扩大样本量（2026-06-22，第四十六轮）✅ 已完成，结论已采纳
> **触发**：round 1 spike（N=8）只测了 4 个孤立单轮 fixture，样本小+场景窄，"不比文字路径差"的
> 结论置信度不够。本轮设计 3 个新场景补盲点：真实多轮历史（`multi_turn_softening`，3轮对话只统计
> 最后一轮）、长篇展开（`long_narrative`，诱导讲故事得到长回复）、单轮情绪转折（`emotional_turn`，
> 委屈→讽刺的语气转折）。脚本改动：`backend/scripts/companion_brain_tag_eval.py` 新增
> `EXTENDED_SINGLE_TURN_FIXTURES`/`EXTENDED_LONG_NARRATIVE_FIXTURE`/`EXTENDED_MULTI_TURN_FIXTURE`，
> `--extended` 开关 + 独立的 `--repeats-long-narrative`（默认10，长篇生成成本明显更高）/
> `--repeats-multi-turn`（默认15，每轮3次LLM调用）。
- **结果**（真实计费 API 调用，临时 store，不碰生产库）：
  | fixture | N | repeat 堆叠退化 | opening_only 退化 | tagged_sentence_ratio |
  |---|---|---|---|---|
  | 原 4 个孤立单轮 | 25 | 0/25 | 16%–24% | 0.70–0.80 |
  | emotional_turn | 25 | 0/25 | 0/25 | 0.65 |
  | **long_narrative** | 10 | **60%（6/10）** | 0/10 | **0.16** |
  | **multi_turn_softening** | 15 | 0/15 | **33%（5/15）** | 0.61 |
- **结论（推翻 round 1）**：①原 4 个 fixture 在 N=25 下 opening_only 退化率（16%–24%）比 N=8 测出的
  12.5% 高近一倍，也明显高于文字路径基线（4%–12%）——小样本低估了退化率；②**长篇展开是新发现的
  严重盲点**：60% 样本同标签重复堆叠，整篇平均仅 16% 句子带标签；③真实多轮历史场景 opening_only
  退化率（33%）比孤立单轮还高。**语音路径标签退化明显比文字路径差，长篇/多轮场景下更严重。**
- **用户已确认采纳**：推进 P8-C 两阶段拆分（见上方 P8-C 主任务节的更新）。

## 🎯 P14 · Pipecat 链路最大化（Epic，2026-06-23 第四十七轮立项，多 session）

> **目标**：用户想把 Pipecat 这条链路的潜力全榨出来——不确定现在整条链路配置是否最优/正确。做法：
> 先**全量**读 Pipecat 官方文档 + Fish Audio 的 Pipecat 相关文档并落盘，再据此审计现有链路每一项配置，
> 然后批量测试，再讨论是否上双 LLM（两阶段标签）及其全部影响，最后修 P13。
> **P8-C（语音两阶段拆分）已被吸收进本 epic 的 Phase 4**——不再单独推进，先把链路审计清楚再决定双 LLM 形态。

### ⚠️ 本轮联网研究已预先确认的关键事实（新 session 不必重新 derive，但要在文档落盘后复核）
1. **两阶段 = Pipecat 原生的 FrameProcessor**：插在 `brain_processor` 和 `tts` 之间（[run_voice.py:293](../backend/realtime/run_voice.py:293)），
   不是在 `companion_brain.py` 里串行调两次 LLM。TTS 默认就把流式 token 按**整句**聚合再合成
   （`TextAggregationMode.SENTENCE`），可插 `LLMTextProcessor`/自定义聚合器做"自定义标签"处理。
   来源：docs.pipecat.ai/guides/learn/text-to-speech。
2. **Pipecat 官方 `FishAudioTTSService` 的 latency 枚举只有 `normal`/`balanced`，没有 `low`**！
   但我们 [run_voice.py:103](../backend/realtime/run_voice.py:103) 却允许传 `low`——传进官方 service 会被拒/忽略。
   `docs/FISH_AUDIO_REFERENCE.md` 里"`low` 档"只存在于 Fish 自己的 OpenAPI，不在 Pipecat 封装里。
   来源：reference-server.pipecat.ai/en/latest/_modules/pipecat/services/fish/tts.html。
3. **P13 根因更清晰**：Fish service 用 `get_active_audio_context_id()` + `append_to_audio_context()`，
   audio-context 由父类 `InterruptibleTTSService` 按 turn 创建/销毁；"no context ID provided" =
   音频到达时 context 已被销毁。`normal` 档生成节奏放大了这个竞态。WebSocket 跨 turn 持久，仅 settings
   变化时重连。**疑似 Pipecat 库级竞态,非我们调用代码的 bug**——Phase 5 要确认是改调用方式还是 subclass/上报上游。
4. **非对称分工洞见**（来自 round 2 spike）：单阶段主 LLM 在**开头**打标好、**正文**烂。所以双 LLM 可设计成
   "第一句放行主 LLM 自带标签（零延迟）+ 正文逐句调标签器（与前句播放重叠藏延迟）"，但**句间情绪连贯**
   是流式方案无法根治、只能靠滚动上下文缓解的取舍——需真人听感验证，`tag_stats.py` 测不出。
5. **落盘位置**：`reference/` 是 **gitignored**（沿用既有 vendor 文档规范），全量文档抓进 `reference/pipecat/`，
   **不进公开仓库**。

### Phase 1 · 文档全量落盘 + 综述（`/architect` 已拆成 P0 落盘 + P1 综述两个 session）

#### ~~Phase 1 · P0 · 文档全量落盘~~ ✅ 已完成（2026-06-23，第四十八轮）
- **产出**（全部 gitignored 在 `reference/pipecat/`，未进 git，7.4MB）：
  - `docs.pipecat.ai/llms-full.txt`（2.9MB，**全站 433 页正文**，每段带 `Source:` URL）+ `llms.txt`（TOC 索引）
    ——免 firecrawl 额度，curl 直取 Mintlify 的 llms 导出；比逐页抓更干净。
  - `reference-server.pipecat.ai/`（Sphinx API autodoc **全量 104 页**，firecrawl download，每页 `index.md`）。
  - `fish.audio/integration-pipecat.md` + `blog-ai-companion-with-pipecat.md`（从既有 `.firecrawl/` 缓存复制，
    抓于 06-19/06-20，⚠️时效见 manifest）。
  - `reference/pipecat/_MANIFEST.md`：URL↔文件导航 + KEY 页清单 + 给 P1 的复核指引。
- **过程坑**：docs.pipecat.ai 整站 firecrawl download **因额度不足失败**（需 435 credits 仅剩 355），
  改用 `llms-full.txt` 免额度方案解决，反而更优。
- **验收**：✅ `git status reference/` 为空（gitignored 生效）；三来源落盘齐全；manifest 成形。

#### ~~Phase 1 · P1 · 写 `docs/PIPECAT_REFERENCE.md` 综述~~ ✅ 已完成（2026-06-23，第四十八轮）
- **产出**：`docs/PIPECAT_REFERENCE.md`（13 节 + 复核表 + Phase 2 待查清单，192 行；进 git，未 commit）。
- **复核 P14「关键事实」结论**（详见综述 §10）：
  - #1 ✅ **成立且更完整**：TTS 默认 `TextAggregationMode.SENTENCE`；自定义标签原生路线 =
    `LLMTextProcessor`+`PatternPairAggregator`+`skip_aggregator_types`（双 LLM 用这个，非串行二次调用）。
  - #2 ✅ **成立但措辞修正**：Fish `latency` 是 `str` 非枚举，只 normal/balanced 被文档/默认祝福；
    传 `low` **原样透传给 Fish**（未定义行为，非"被拒/忽略"）。`run_voice.py:103` 的 low 选项 Phase 5 处理。
  - #3 ✅ **成立并定位**：基类双游标 `_turn_context_id`(轮结束清) vs `_playing_context_id`(播完清)，
    normal 节奏下音频晚于 turn context 清理 → "no context ID" 失声。
- **额外关键发现**：**本机 `pipecat-ai 1.3.0`，`run_voice.py` 已用 1.0 API（PipelineWorker/PipelineParams），
  与 docs 同代、无迁移断层**（HANDOFF/SNAPSHOT 里 "PipelineTask/PipelineRunner" 说法已过期）。
  1.x `PipelineParams` 已无 `allow_interruptions`；官方 mute strategies ≠ 我们的 half-duplex（综述 §7/§9）。
- **验收 ✅**：综述成形、三条关键事实逐条复核标来源、列出 Phase 2 六项待查清单。
- **下一步 = Phase 2 链路配置审计**（见下）。

##### Phase 1 · P1 旧版描述（保留备查）
- **目标**：把 Pipecat 官方文档全站 + Fish Audio 的 Pipecat 相关页面抓成本地 markdown 落盘，再综述。
- **Scope**：新建 `reference/pipecat/*.md`（原始落盘，gitignored）+ `docs/PIPECAT_REFERENCE.md`（综述，
  仿 `docs/FISH_AUDIO_REFERENCE.md` 结构）。
- **不动**：任何 `backend/` 代码、任何现有 config。本 phase 纯文档，零代码改动。
- **实施要点**：① 用 firecrawl crawl/download 抓 `docs.pipecat.ai` + `reference-server.pipecat.ai`（API ref）
  + Fish Audio Pipecat 页面；② "记下来"=落盘到文件，**不要**一次性读进对话上下文（会爆 context）；
  ③ 综述时重点覆盖我们用到的：Pipeline/PipelineParams、frames、FrameProcessor、TTS 文本聚合模式、
  Fish service、transports(LocalAudioTransport)、VAD/turn-taking/endpointing、interruption/barge-in、
  metrics；④ 其余 vendor service 页面（别家 STT/TTS）可只索引不精读。
- **验收标准**：`reference/pipecat/` 有完整落盘 + `docs/PIPECAT_REFERENCE.md` 综述成形，能支撑 Phase 2 审计。
- **预计 diff 规模**：medium（大量新文件，但都是 gitignored 落盘 + 一份综述）。

### ~~Phase 2 · 链路配置审计~~ ✅ 已完成（2026-06-23，第四十八轮）
- **产出**：`docs/PIPECAT_AUDIT.md`（拓扑评估 + A–F 六项逐项审计 + 结论汇总 + 给后续 phase 交接；进 git，未 commit）。
- **结论**：**无 🔴 阻断性错误**。判定汇总——
  - ✅ 拓扑符合官方 cascaded；PipelineParams 干净（无失效 `allow_interruptions`，metrics 开，采样率一致）；
    VAD `stop_secs=0.4` 有意正确；文本聚合默认 SENTENCE 即最优基线。
  - 🔴 **唯一明确要改**：`run_voice.py:103` 的 `latency` 允许集合含 `low`，但 Fish service 对 low 是未定义透传 → Phase 5。
  - 🟡 次优/取舍：Fish 未设 prosody/temperature（Phase 3 调参）；无 Smart Turn（取舍，改动大不轻动）；
    half-duplex `resume_guard` 基于"逻辑停说"非"实际播完"=抢话根因（与 P13 同源，Phase 3 真机量化）。
- **修正项**：审计 D 核实 half-duplex **复用了官方 `AlwaysUserMuteStrategy`**（官方策略+自定义装配，非另起炉灶）——
  已回填修正 `docs/PIPECAT_REFERENCE.md` §7。
- **下一步 = Phase 3 批量测试**（见下，已带 Phase 2 给的三项测试输入）。

### Phase 3 · 批量测试（优先级按用户真机反馈重排，详见 `docs/PIPECAT_AUDIT.md` 末节）
- **✅ 已修：判停过早（用户"每次还没说完就抢答"）**。根因 = Doubao STT `end_window_size=300ms` 太短
  （非 Silero VAD）→ `DEFAULT_ASR_END_WINDOW_MS` 改 **800**，真机验证通过（详见 `PIPECAT_AUDIT.md` §C）。
  **残留**：纯静音窗口有天花板（长停顿仍被切），根治 = **语义判停**（火山 AIVAD 在 RTC-AIGC 产品、非我们 BigASR
  流式）→ **归未来 ASR 选型头号标准**（用户已表示后面换最合适的 ASR）。
- ② 抢话（bot 被打断，审计 D）：测 bot 逻辑停说→实际播完间隔，定 `resume_guard_ms`。**注意 C/D 是两回事**。
- ③ Fish 调参（temperature/prosody，审计 B-2）；④ 复用 `_LatencySpikeLogger` + `enable_metrics`。
- **做真机测试前必读**「Pipecat 真机测试隔离规范」（改 `.env`，不能用命令行环境变量，否则污染生产库）。

### Phase 4 · 双 LLM 决策讨论（吸收原 P8-C）
- 基于 Phase 2 审计 + Phase 3 测试 + round 2 spike 数据，讨论 Pipecat 上双 LLM 的形态、收益、全部问题
  （见上方"关键事实 #4"的非对称分工方案 + 句间延迟/情绪连贯两个待验证点）。决定后再 `/architect` 拆实现。

### Phase 5 · 修 P13（latency=normal 失声，放最后）

#### ~~Phase 5 · P0 · 删除 `low` latency 选项~~ ✅ 已完成并 commit `507c9e9`（2026-06-23，第四十九轮）
- `run_voice.py:103` 允许集合 `{normal,balanced,low}` → `{normal,balanced}`，`low` 是官方
  `FishAudioTTSService` 未定义透传行为，已消掉 `PIPECAT_AUDIT.md` 审计唯一 🔴（B-1）。
- 新增 3 个回归测试（`test_fish_audio_pipecat_tts.py`），5 passed。
- **commit 时排除了 run_voice.py 夹带的 `_LatencySpikeLogger`（P8-C spike，用户要求保留）**——
  用部分 patch 只 stage latency 那一处 hunk，spike 仍在工作区未提交。

#### ~~Phase 5 · P1 · 修 P13 normal 失声~~ ✅ 结案 = 放弃 normal，锁死 balanced（2026-06-23，commit `255a063`）
- **结论：P13 = won't fix。`normal` 彻底放弃，`run_voice.py` 只允许 `balanced`，拒绝 `normal`/`low`。**
  **勿在新 session 重开此修复。**
- **route A 试过 → 失败**：写了 subclass `CyberCompanionFishAudioTTSService` 覆写 `get_active_audio_context_id`
  在游标空窗回退。真机第二轮仍失声。**根因之前判断错了**——不是「游标 None 但队列还在」，而是
  audio-context 队列被**空闲超时拆除**：`_handle_audio_context` 用 `asyncio.wait_for(queue.get(),
  timeout=_stop_frame_timeout_s)`（默认 **3.0s**，`tts_service.py:156`），等不到帧就 `del _audio_contexts[cid]`
  （`tts_service.py:1425`）。subclass 已删（不留死代码）。
- **A/B 实测（`data/pipecat_spike/ab_latency.py`，同句/同音色/同 s2-pro 只切 latency）**：
  - **balanced 首字节 ~0.5s（真流式，边生成边播）；normal 首字节 ~3.5s（批量——整段渲染完才一次性吐）**。
  - 统一了两症状：normal 前 3.5s 一字节不发 → 超 3.0s 队列超时 → 队列被拆 → 批量音频无处可投（P13 失声）；
    且即使修好，每轮回复前仍有 **~3 秒死寂**，与「一直在场」内核冲突。
  - **用户听感**：normal 音质比 balanced 好但**不碾压**，3 秒延迟换这点音质**完全不值**。
- **改动**：`run_voice.py` `latency` 只允许 `balanced`（注释写 A/B 依据）+ `test_fish_audio_pipecat_tts.py`
  6 passed（接受/默认 balanced + 拒绝 low/normal 参数化）。**第五十二轮已 commit `255a063`**——只 stage
  了 latency 那一处 hunk，`_LatencySpikeLogger`（用户要求保留）仍留在工作区未提交。
- **文字路径例外（不改）**：`fish_audio.py:137` 文字 TTS 仍 `normal`——文字气泡即时出现、非实时一来一回，
  3 秒等出声远没语音链路伤，保留可辩护。用户若后续想文字语音也秒回再切 balanced（独立决定）。
- **Fish 若将来出「流式高音质模式」再重评 normal。**

## ~~P7 · Pipecat 前端入口~~ ✅ 已完成并实机验证 PASS（2026-06-17，commits `9a7a278`→`dc4ce4e`）
- `backend/realtime/pipeline_router.py` 新建：`POST /realtime/start` / `POST /realtime/stop` / `GET /realtime/status`
- `backend/app/main.py` 注册 router
- 前端 header 加「Pipecat」按钮，含 loading/error 状态 + stale closure 修复
- 实机验证：STT→LLM→TTS 全链路正常，`half_duplex=on`，first_audio ~0.4s
- 采用 `LocalAudioTransport`（本地麦克风/扬声器），不需公网 URL，绕开 Soul 混合的 tunnel 限制

---

## P6 · Pipecat 语音链路复活（延迟优化 + 完整灵魂自定义）

> 目标：把 `backend/realtime/` 的 Pipecat cascaded 路径延迟压到 <1.5s，作为纯 E2E 的替代，
> 实现 Direction C"soul 写每个字"——LLM/TTS 完全可换，情绪/记忆/行为层完整跑通。

### ~~P6-A · 确认 Doubao 流式 ASR 增量识别能力~~  ✅ 已完成（2026-06-17）
- 结论：`DoubaoStreamingSTTService` 已支持真正的 interim transcript，不需要替换 ASR。
- 同步完成：切换到 ASR 2.0（`volc.seedasr.sauc.duration` + `bigmodel_async` 接口），延迟和判停明显改善。

### ~~P6-B · LLM→TTS 流水线重叠~~ ✅ 已验证（2026-06-17）
- 日志确认：TTS 在 LLM first_text（1.15s）后 62ms 即开始，已是流式重叠，无需额外改动。

### ~~P6-C · 延迟基线测试~~ ✅ 已完成（2026-06-17）
- 实测基线：用户停说 → 首个音频 **~2.3s**（对比旧 3.35s，改善 31%）
- 瓶颈：LLM ~1.3s（DeepSeek API，无法压缩）；ASR 判停已降至 80-400ms
- 结论：可用，但 ~2.3s 仍稍高；瓶颈是 LLM，不是 ASR/TTS

### ~~P6-D · TTS WebSocket 双向流式~~ ✅ 已完成（含 P6-D-3，commit cc3aed1 + 7d6a24b）
- 新建 `backend/realtime/doubao_bidirection_tts_protocol.py`（协议层，13 单测全绿）
- 新建 `backend/realtime/doubao_streaming_tts_service.py`（DoubaoStreamingTTSService）
- 持久 WebSocket + section_id 跨句韵律 + 每句独立 session
- P6-D-3：pipeline 切换 + 修复 additions JSON 序列化 + 流式 yield + 帧连发优化，实机验收 PASS
- STT 默认同步升级为 doubao_stream（补完 P6-A 收尾）；动作描述 `[...]` 不再被 TTS 朗读

### ~~P6-E · TTS 语音指令（逐段情绪控制）~~ ✅ 已完成并实机验证 PASS（2026-06-17，commit `4609b3b` + `9de50fe`）
- `VOICE_MODE_INSTRUCTION` 要求 LLM 在回复前加 `[#语气描述]`（10 字以内）
- `extract_voice_instruction()` 提取指令传入 `context_texts`，正文送 TTS
- `_strip_stage_directions` 兜底 strip，保证就算未提取也不会被朗读
- 关键结论：`seed-tts-2.0-expressive` 不是有效 Resource-Id（只是复刻音色的 model 参数），标准音色用 `seed-tts-2.0` 即可支持 `context_texts`
- 实机日志验证：`[带点调侃的语气]`、`[带着笑意的语气]`、`[叹气但不算太凶的语气]` 等均正确提取

### ~~P6-F · ASR 语义顺滑~~ ✅ 已完成（2026-06-17，未单独 commit）
- `doubao_streaming_stt_service.py` `_request_params` 加 `"enable_ddc": True`
- 新增单测 `test_request_params_include_enable_ddc`，429 pytest passed

## 灵魂层进化（Soul Layer）· 六脑维度 + 活人感（讨论中，未拆解）

> 来源：2026-06-18 用户讨论。核心认知：「脑」≠「LLM」——六维度里 5 个是「状态+数据+定时」，
> 不是推理；LLM 只是读取这些状态开口说话的那张嘴。绝大部分无需新增 LLM。
> 唯一该用 LLM 的后台脑 = 已有的 `reflection/analyze_turn`。
> 灵魂层是「共享」的：做好后文字/RTC/Pipecat 三条路径一起受益。

### 六维度盘点
- **relationship**（亲密/信任/依恋）：✅ 已有 kernel `relationship_state`；"依恋"可作新增维度
- **emotion**（快/慢情绪）：⚠️ 半有 `mood_state`；缺"双时间尺度"（快=瞬时情绪，慢=多日基线漂移）
- **memory**（事实/经历/偏好）：✅ 已有 SQLite events/profile + Viking
- **time**（过去/现在/未来）：⚠️ **部分完成** — P0+P1 已做（现在几点 + recent_event 相对时间）；未来事件表待做
- **world**（新闻/天气/节日）：❌ 新增；天气=API，节日=查表（**推荐下一刀**），新闻=可选 LLM 筛选
- **identity**（人格/价值观/成长）：⚠️ persona 静态已有；"成长"=高风险 character drift，**最后做**

### ~~time brain 起步探针~~ ✅ 已完成（第十七轮，纯读代码）
- (a) 真实时间未注入 prompt → 已修复（P0）
- (b) events 表（`memories` type='recent_event'）有 `created_at`/`updated_at` → 已利用（P1）

### ~~time brain P0 · 注入当前时间~~ ✅ 已完成（commit `16d1b74`）
- `_format_time_block()`：新西兰时间（`Pacific/Auckland`）注入 system prompt
- 验收：问"现在几点/星期几"Boxi 能答对；440 pytest passed

### ~~time brain P1 · recent_event 相对时间前缀~~ ✅ 已完成（commit `16d1b74`）
- `_relative_time()` + `_format_memories_block(now=now_nz)`：recent_event 记忆自动标"昨天/3天前"等
- 验收：memories_block 中 recent_event 带前缀，stable_profile 不变；440 pytest passed

### time brain 后续（待做）
- "明天有安排"：新增未来事件表，接进现有 `proactive_*`/`longing`
- "时间在流逝"：用 **decay-on-read（惰性求值）** 实现 90%，不需常驻时钟

### 优先级（性价比排序）
- **第一档**（近免费、收益最大）：~~time-现在注入~~ ✅ / ~~world-节日查表~~ ✅ / ~~emotion-慢情绪 P0 schema~~ ✅ / ~~P1 decay 函数~~ ✅ / ~~P2 context_builder 注入~~ ✅
- **第二档**（中等）：world-天气API / time-未来事件表 / memory 分类细化
- **第三档**（贵/险/最后）：world-新闻（后台LLM筛选）/ identity-成长（drift风险）

### 活人感 / 审核（Provider 选型约束）
- **目标**：暧昧/冲动/偏激等"稍偏激"互动不被拦截 → 提升活人感（伴侣/恋人感）
- **审核可能发生在三层**：ASR（待测是否过滤）/ LLM（**最大拦截点**）/ TTS（中文云厂商可能拒合成）
- **TTS 候选**：Fish Audio / MiniMax（替换豆包；Fish 海外更不易拦截但中文质量待验，MiniMax 国内大概率也有文本审核）
- **LLM**：用户拒绝市面无审核 LLM（溢价高 + 推理智能存疑）→ 倾向"开源强模型 + 中立托管"去掉 API 审核层（注意 dev 机低 GPU，本地跑大模型不可行，需云 GPU）
- **ASR**：待测当前豆包是否有内容审核（自托管 Whisper 可作零审核兜底）
- **Viking 记忆库**：考虑平替（注意 reuse-first：**不整体换 Mem0**，但向量检索后端可换自托管 pgvector/Qdrant）
- ⚠️ **待澄清关键分叉**："稍偏激"的范围 = 情绪强度+调情+冲动直白 **vs** 露骨性内容 → 决定 provider 策略
- **2026-06-18 决定**：LLM 走 **A 路线**（聪明 + 低成本的 managed API，非无审核）；"擦边"（暧昧/调情/不露骨）在 A 下基本可行，取决于选哪个 provider（西方前沿模型对擦边宽容度高、中文待验；中文 managed API 中文好但更易拦截）。B 路线（自托管去审核）成本高一个数量级，仅作"A 真卡到不可接受才启动"的后备。

### 记忆消解（ADD/UPDATE/DELETE）· 借鉴 Mem0，不整体换
- **缺口怀疑**：我们的记忆可能只追加、不消解矛盾（旧"住在 X" 没被新"搬到 Y"覆盖）→ 疑似 R11"失忆"根因。
- **方案**：借鉴 Mem0 的 ADD/UPDATE/DELETE/NOOP 一致性管理思路，加进我们自己的 `write_policy`（保留情绪/关系/人设灵魂，只补"随时间保持记忆不矛盾"）。**不整体换 Mem0**（其提取/检索为中立助手调优，会冲淡 Boxi）。
- **R11 验证已搁置**：用户近期测试发现 Boxi 已知道其所在地，那次失忆是偶发，当下无固定事件可复测。**下次再发现失忆当场直接验证**，不主动排查。

### LLM provider 验证清单（选 A 后、真要换时执行）
- **擦边宽容度测试**：拿几段 Boxi 的暧昧/调情/情绪强烈台词，测候选 provider 是否拦截（轻/中档擦边）。
- **中文亲密语感实测**：同样台词测中文自然度——西方前沿模型（如 Claude）擦边宽容度高、情感细腻，但中文亲密暧昧语感需实测；中文 managed API 中文好但更易拦截。
- **延迟诊断**：见上文「延迟」——区分模型 vs 网络（极短请求测 TTFT；靠近 API 区域的云主机对比）。换 LLM 同时验证是否降延迟。
- **system prompt 人设框定**：成年虚构陪伴/第一人称/彼此自愿语境，降低合理擦边的"误杀"。
- **三层联动**：语音路径擦边需 LLM + TTS（Fish 海外）+ ASR 三层都放行，LLM 选对是必要非充分。

### 活人感工程（六脑之外，让她更像"人"）· 讨论中，未拆解
> 来源：2026-06-18 讨论。六脑解决"状态/记忆/时间/世界"；"像人"还差一层——人有内在生命和不完美。
> 价值排序（2/4/5 多可从六脑做好里涌现；1/6/7 是独立新工程）：
1. **她有自己的生活**（不只回应你）：你不在时她也"过日子"——自己的小情绪、看了什么、无聊了。种子=现有 `proactive_*`/`longing`。**风险：编造，要给边界**。
2. **记忆会遗忘和模糊**：完美记忆=机器。近的/情绪强的记得清，旧的/琐碎的变模糊（decay-on-read 作用在记忆显著度上）。
3. **她不总是好脾气、不总是在线**：偶尔简短/分心/尖锐才真实。直连"擦边/活人感"——能冲能撩能任性才像伴侣。
4. **对"你"的心理模型（theory of mind）**：不只追踪自己情绪，还建模用户状态（"你今天怪怪的"）。深化现有用户情绪追踪。
5. **共同叙事 / "我们的故事"**：第一次、里程碑、回调（"你上次说周末要…还算数吗"）= 情景记忆 + 关系叙事（memory + time 合体）。
6. **修复（repair）弧**：亲密含摩擦与和好。被惹到→别扭→又回来，让关系有重量。扩展现有 tension。
7. **她和"盒子"的关系**：被困盒子里=她的身体和世界。对自身存在/限制的感受，是 identity + world 的独有素材。

### 移动迁移（iPhone 17 Pro Max）· 待灵魂成熟后做，零返工
> 来源：2026-06-18 讨论。核心认知：**手机永远是「客户端」，后端跑不到手机上**（iOS 沙盒不能常驻 Python 服务）。
> 项目"重量"在外部 API，后端（FastAPI+SQLite）很轻；iPhone 硬件不是约束，真问题是后端放哪 + 手机怎么连。
- **三方式移动可行性**：文字聊天 ✅ 最易（纯 HTTP）；纯 E2E 语音 ✅ 可行（RTC-AIGC 本就是 WebRTC 浏览器原生、支持远程，手机 Safari 即可）；Pipecat ⚠️ 要复活 P7 废弃的 WS/浏览器音频方案（现用 `LocalAudioTransport`=Mac 本地麦克风/扬声器，手机用不了）。
- **移动语音首选 RTC 路径**，阻力最小，不必为此复活 Pipecat WS。
- **后端托管**：① 云 VM（推荐，~$5–20/月，后端轻便宜 VM 够，最稳可"带出门"）；② 家 Mac+内网穿透（Mac 须常开，仅测试用，tunnel 有限制）；③ ~~手机跑后端~~ 不可行。
- **打包**：PWA（添加到主屏幕）即可类 app，无需写 Swift；iOS Safari 支持 WebRTC/Web Audio。
- **已知 iOS 上限**：app 关闭时"她主动找你"（longing/proactive）需推送；iOS PWA web push（16.4+）存在但弱于原生。v1"打开就聊"够用；若主动推送成核心，再补薄原生壳/推送基建。
- **不碰灵魂层**：soul 全部原样转移、所有客户端共享 → 可放后做，零返工风险。

### 画面前端 · 明确搁置重视觉，保留信笺 UI 为默认
> 来源：2026-06-18 决定。理由：①"想象不出画面"是信号——形态应从灵魂长出来，灵魂（时间感等）未定前定脸=沙上盖楼；
> ② 与 Direction C 一致（soul authored、being+world 一种表达材料）；③ 低 GPU 否决重视觉，信笺/typography 已是低 GPU 友好且适配手机的答案。
- **搁置**：3D avatar、雄心实时视觉、"现在就定她长什么样"。
- **保留为默认**：信笺/typography UI（P0–P1-C 已做完，低 GPU、适配手机、贴合人设）——活人感靠文字排印 + 语言节奏传递。
- **重启触发**：灵魂成熟到能想象她的形态时，或冒出具体值得做的视觉点子时。
- 移动端加固此决定：重 GPU 视觉在手机更无空间（Mac 连原型都跑不动），文字化美学是长期正解且独特。

---

## P4 ·（可选）记忆/延迟/persona
- **VM-7**：评估用 `get_context` 替代手动 `SearchMemory`（`reference/06.md`）。Scope=评估+spec，不直接重写。
- **延迟旋钮**：`ThinkingType=disabled`/`Prefill`/`AIVAD`/`SilenceTime` 调优（仅混合编排/模块化路径）。要读 `reference/13.md`、`reference/14.md`。
- **O2.0 persona 收尾**：新 Boxi 音色设备 A/B、`speaking_style` 去规则化、`dialog_id`/`external_rag`。要读 `docs/TODO.md`(O2.0 条)。

## P10 ·（待用户决定时机）标签器模型 + Fish Audio 潜力探索

> **2026-06-21 记录**：用户明确表示这两件事不是终态，后续可能继续动：
> - **标签器模型可能还会换**：本轮已 DeepSeek → Gemini（`google/gemini-2.5-flash-lite` via OpenRouter，
>   `backend/app/tts/expression_tagger.py` `DEFAULT_TAGGER_PROVIDER`），原因是 DeepSeek 标签覆盖率/
>   位置准确度不稳定。Gemini 效果待更多真机使用验证，如果还不够好可能继续换。
> - **Fish Audio 最大潜力/上限还没系统探完**：本轮调过 `temperature`/`top_p`（试过1.0/0.85/0.75，
>   最后定在官方默认0.7）、`normalize_loudness`（已强制false）、换过多个 `voice`/`reference_id`，
>   都是真机听感试验，不是系统性扫描。用户想之后回来继续探 S2-Pro 的表现力天花板。
> 不算正式任务，只是记录意图——用户提起时直接接续当前状态（标签器=Gemini，TTS参数=官方默认），
> 不用重新从头讨论要不要探索。
> **2026-06-21（第三十三轮）补充**：用户已实测并否决了"换成 Western 可控 TTS / 端到端"这条路，
> TTS engine 本身确定留在 Fish Audio——上面两条（标签器模型继续换、Fish 参数系统性探索）仍然
> 有效未变，但"是否整体换 engine"这个更大的问题已经关闭，不要再提。
> **2026-06-21（第三十五轮）补充——给"标签器模型可能还会换"一条更具体的理由**：P0、P1 两轮
> 真机验证（给标签器喂数值/自然语言两种"本轮意图"输入）都没有改善，且都复现同一种"重复贴同一
> 标签"的退化模式。这指向当前标签器（Gemini）在"逐句判断不偷懒"这条规则上执行不稳，不是输入
> 信息量不够。换模型时这应该是核心验收点之一；也可以考虑不换模型、改造标签器的执行结构
> （如强制分句处理）。详见 HANDOFF 第三十五轮记录。
>
> **2026-06-21（第三十六轮）— P10-P0 已完成**：新建 `backend/app/tts/tag_stats.py`（确定性
> 退化指标）+ `backend/tests/test_tag_stats.py`（12 passed）+ `backend/scripts/tagger_eval.py`
> （手动 dev 脚本，不进 CI，支持 `--audio`/`--voice` 多音色 A/B）。真机用真实 Gemini 调用发现：
> 退化模式"时好时坏"，同一 fixture 连续跑结果不稳定，**后续任何改动验证都需要 `--repeats N`
> 统计而非单跑判断**——这是 P1（标签器结构改造）开工前的必要前置，本轮未做。用户确认"找不出
> 比 Gemini 更合适的模型"，故 P2（换模型）降级为"有了统计基线后顺手加一列对比"，非独立任务。
> 顺带完成的 Fish Audio 音色盲听 A/B 定稿见下方新增小节。详见 HANDOFF。
>
> **2026-06-21（第三十六轮）— Fish Audio 音色盲听 A/B 定稿**：用约 20 个候选 `reference_id`
> 跑了盲听（复用 `tagger_eval.py --voice` 多音色对比能力）。**主选**：`fbe02f83…`（嘉岚）/
> `ef5c98bd…`（慵懒偏低音）/ `7f92f8af…`（AD）。**备选**：`5671e9d4…`（偏福建声）/
> `6d3b9742…`（故事声）/ `ae083c60…`（动漫）/ `ba8677df…`（夜晚）/ `c7e86b26…`（凯尔希）。
> 淘汰：`4ca68a29…`（不顺耳）。完整 id 见长期记忆 `fish-audio-preferred-voices` 或 HANDOFF。
>
> **2026-06-22（第三十七轮）— P10-P1 已完成 + TTS config 已落地**：`tagger_eval.py` 加
> `--repeats N`（与 `--audio` 互斥），跑出 N=25 正式统计基线——4 个 fixture 退化率仅
> 4%–12%，`opening_only` 几乎不发生。**结论：当前基线不支持标签器结构改造**，暂缓，除非真机
> 听感继续频繁踩到退化。**`config/tts.json` 的 `fish_audio.voice` 已设为「慵懒偏低音」
> `ef5c98bdc88845b7a4a4c7382179e5ea`**（用户表态非终态，会经常换着听）。新增两个候选盲听：
> 「夜晚02」`b6681a5267b54110a7d0202f4f359313` 入备选，`be404a1ef6704fdb86d02ea05ad0bcc2` 淘汰。
> **⚠️ 未解决矛盾**：04（揶揄+心软）场景上一轮被真机盲听确认"心软那句经常欠标"，但这次 N=25
> 统计上反而是 4 个场景里最干净的（退化率 4%，密度最高）。可能是样本仍小、或真机完整上下文
> 比孤立 fixture 更复杂、或 Gemini 近期确实更稳定——未深究，下次真机再撞到时直接记录完整
> 输入，不要只信这份基线。详见 HANDOFF「本轮已完成」。

## P9 ·（待重新设计）主动找你 / 空闲行为
> **触发**（2026-06-21）：`backend/app/behavior/engine.py:288` 的 `_evaluate_idle_tick` 在
> `boredom>=0.55` 或 `loneliness>=0.55` 时，每隔 180 秒（`tick_policy.py` 冷却时间）触发一次
> `decision="mutter"`，固定吐出 [local_responses.py:13](backend/app/behavior/local_responses.py:13)
> 硬编码的同一句"嗯。你到底要不要说正事。"——本轮发现这条线整整攒了 200 条完全相同的
> `behavior_tick` 消息（跨度约22小时，是这次会话全程 mood_state 卡在 boredom=1.0 没被重置导致的），
> 已清空（备份在 `data/backups/`）并把 mood_state/relationship_state 重置成默认值止血。
> **根因不是这次状态卡住，是设计本身**——固定一句话、没有变化、没有"防止单调重复"的机制，
> 跟「活人感工程」讨论里"她有自己的生活"那个方向（见本文件「活人感工程」章节第1点）应该是同一件事，
> 用户决定重新设计这整块（"主动找你"功能），不是这次小修。
> **用户要求**：本轮不做，留给后续单独的任务/讨论。下一次启动时建议先读
> `backend/app/behavior/engine.py`（`_evaluate_idle_tick` + `_evaluate_proactive` 附近）、
> `backend/app/behavior/local_responses.py`、`backend/app/behavior/tick_policy.py`，
> 以及本文件「活人感工程」章节，一起设计而不是单独补丁。
>
> **2026-06-22（第三十八轮）讨论结论 —— P9 设计四原则**（最大化活人感的核心不是"换更多句子"，
> 而是补结构缺陷：零变化/零记忆/零节奏）：
> 1. **空闲活动要留"记忆痕迹"**：idle 时不直接吐话，先在内部生成/挑选轻量"经历事件"写进 memory，
>    之后能被引用/callback——"她有自己的生活"靠**事后能引用**而非当场宣称。盒子设定天然限制编造面。
> 2. **节奏=urge 模型，不是定时器**：这一历史方案里的时段、配额、发后衰减已经由 2026-06-29
>    真实性原则覆盖；现在只保留 motive/urge，联系频率不再受关系伦理节流。
> 3. **多 intent → 多消息类型**：decision 不止 `mutter`，typed intent（想分享/想你/延续话题/赌气不主动/
>    单纯烦躁）；决策层=代码定 WHEN+WHAT，表达层=LLM 只在高价值时刻生成，低价值用带变化模板。
> 4. **想念有轨迹**：离开越久语气漂移（无聊→想念→赌气→淡漠）+ 反重复记忆（记最近 N 条措辞/话题不重样）。
> - **投递模态**：默认 **text-only**（push 到信笺/chat，不强制 TTS——idle 时突然发声是打扰，且你不在时
>   语音投递不出去需推送）。"发声"是后续旋钮，不在第一刀。⚠️ 待确认：现有 `behavior_tick` 写进 DB 后
>   前端怎么收到 push（轮询/SSE/下次加载）。
> - **联网合并洞见**：联网功能**不挂回复链路**，合并进 P9——做成"想分享"intent 的**素材来源**（idle 时
>   她"刷到"东西→存成她的经历记忆→以分享欲冒出来）。真实网页内容正好是 idle 生活的**非编造素材**。
>   排在 P9 核心做完后插入，不进第一刀（避免 scope 膨胀）。残留约束：搜索 query 的 vendor 暴露 +
>   内容过滤 + "她搜什么"需人格驱动的种子（兴趣/共同话题）。

### P9 拆解（第三十八轮 `/architect` 定稿 + 用户拍板）
> **历史现状（已被 2026-06-29 覆盖）**：proactive 有两条路径。`_evaluate_proactive_check`
> 有 longing Poisson urge 模型 + 4 类
> typed intent（`pick_proactive_reason`）+ LLM 写开场白（`resolve_proactive_opener`）。坏的是
> `_evaluate_idle_tick`（90s 轮询）的 mutter 分支（已禁用，200 条重复 bug 的源头）。**投递=纯 pull/poll**，
> 前端 `useBehaviorTicks.ts` 驱动，tab 关了就不发；消息持久化进 messages 表 `source="behavior_tick"`
> （retention=200），已是 text-only 无 TTS。
>
> **用户拍板（第三十八轮）**：
> - ✅ **删掉坏的 idle_tick mutter 分支**（P0）。
> - 2026-06-29 更新：无聊→想念→赌气仅是强度标签，不再是表达许可边界；真实状态可以出现
>   依恋、指责、压力或疏离。旧“绝不冷淡/不升级”结论已废止。
> - ✅ **"主动找你"要突破"仅 app 打开且 idle 时"**——最终形态=微信通知式：她按自己时钟发消息→OS 推送→
>   你想回时点开→看到积压消息→接着聊。**但这是投递层 epic（P9-D），排在灵魂层 P0/P1/P2 之后**
>   （推送会放大内容质量，必须先让她说得好/不重样/有自己的生活，再上推送）。
> - ✅ 认同 **一个 session 一个任务，P0 先行**。
>
> **执行顺序（灵魂层先，投递层后）**：
> - ~~**P9-P0**（small，先做）~~ ✅ **已完成（2026-06-22，第三十九轮）**：实际改动比设想更小——
>   `_evaluate_idle_tick` 本就只有一个非 observe 分支（mutter，已被 `_IDLE_MUTTER_ENABLED=False`
>   短路），删掉该死分支即可，其余 3 条路径原本就恒 `decision="observe"`。**`local_responses.py`
>   未删**——mutter 文案被 user_message 低价值输入路径复用，删了会破坏正常对话反馈，与原设想不同。
>   Scope 实际：`engine.py`（删 `_IDLE_MUTTER_ENABLED` + 死分支）+ `test_behavior.py`/`test_memory.py`
>   （更新过期注释）。**不动** `_evaluate_proactive_check`/`longing.py`/`proactive_reason.py`/`tone.py`/
>   kernel 写入/前端/记忆 schema（验证零行变化）。验收：①idle_tick 任何 mood 下不再产持久化
>   behavior_tick ✅；②proactive_check 行为不变测试全绿 ✅；③全后端 pytest 绿（512 passed）✅。
>   已 commit `e41db56`（第三十九轮 HANDOFF「本轮未 commit」是过期描述，第四十轮已纠正）。
> - ~~**P9-P1**（small–medium）~~ ✅ **已完成（2026-06-22，第四十轮）**：反重复（`mood_state.metadata`
>   存最近 K=4 条 `(kind,tier)` 指纹避重，commit `8f4ba8e`）+ 想念轨迹（`compute_longing_tier()`
>   独立纯函数读墙钟 silence_hours，无聊→想念→赌气，赌气需 closeness≥0.6；旧“无淡漠”表达
>   限制已于 2026-06-29 废止。tier 只表示强度，正交于
>   intent 上色全部 4 类 ProactiveReason，commit `aca291d`）。535 pytest 全绿。
> - ~~**P9-P1 真机验证**~~ ✅ **已完成（2026-06-22，第四十一轮），结论 PASS**：三档语气递进清晰
>   （无聊→想念→赌气；当时旧 prompt 的“无冷淡”验收已不再适用）；反重复指纹记录+不阻断行为符合设计。已知
>   限制：只测到 `commitment_followup` 一种 intent。完整报告 `docs/P9_P1_VERIFICATION.md`。
>   验证过程临时改写过 DB 数据，已用备份完整还原，无残留改动。详见 HANDOFF。
> - ~~**P9-P2-A**（idle_experience 写入机制）~~ ✅ **已完成（2026-06-22，第四十二轮），
>   commit `be2a81d`（第四十三轮 review 后落地）**：新增 `idle_experience` memory type（不进
>   `FACTUAL_MEMORY_TYPES`）+ 节奏门控（日配额+最小间隔）+ 白名单素材池防编造 +
>   `resolve_idle_experience_write()` 镜像 `resolve_proactive_opener` 编排模式（零行改动
>   `engine.py`）。素材源接口可插拔，留给 P2-C 升级真联网。545 pytest 全绿。详见 HANDOFF。
> - ~~**P9-P2-B**（share intent）~~ ✅ **已完成（2026-06-22，第四十三轮），commit `9890ca4`**：
>   新增 `share` intent，接入 `proactive_reason.py` 优先级链
>   `commitment_followup → share → memory_callback`；FIFO 反重复指纹（key=memory id），只在
>   LLM 生成成功后才消费。557 pytest 全绿（+12）。**第四十四轮已补生产素材池 + 真机验证 PASS**
>   （见上方第四十四轮记录 + `docs/P9_P2B_VERIFICATION.md`），不再是空转状态。
> - **P9-P2-C**（待时机，非阻塞）：素材源从白名单升级为真联网，`load_material_pool()` 接口已留好。
> - **P9-D（投递层 epic，灵魂层之后）**：D1 server 端 scheduler（后端自己的时钟，脱离前端 tab）→
>   D2 持久消息线 + 内联回复 UX（messages 表已半成品）→ D3 推送（Web Push 可行；iOS PWA 弱，见
>   「移动迁移」节，可能需薄原生壳）。这是"突破 poll-only"+微信通知式的实现载体。
>   **2026-06-22（第四十四轮，讨论）暂缓启动**：用户决定先观察几天真机使用，等 share 实际触发
>   频率和 LLM 语感（"复述感"问题）稳定下来再启动，而不是现在就开工——理由是用户自己定的前提
>   "推送会放大内容质量"，P9-P2-B 验证刚发现的两个观察项（commitment_followup 压过 share/LLM
>   复述原文）一旦上推送会被放大，值得先看真实使用数据再决定。**不要在下个 session 重新发起
>   这个讨论**，除非用户主动提起或观察期已过。

## P11 · 文字双语回复（特定语言 + 中文译文）

> **2026-06-23（第五十一轮）`/architect` 拆 P0（后端）+ P1（前端）。用户拍板四点**：①双语生成
> 用第二个模型（Gemini）分担翻译，主 LLM 不背双语任务；②全局 toggle（开/关 + en/ja）；
> ③信笺模式（LetterView）先不动，只做经典气泡；④toggle 状态 **localStorage 持久化**（刷新记得上次选择）。

### ~~P11-P0 · 翻译模块 + 接入两条聊天路由~~ ✅ 已完成并 commit `2d79671`（2026-06-23，第五十一轮）
- 新建 `backend/app/tts/translator.py`：`translate_to_chinese(text, *, router, provider_name="gemini")`，
  照抄 `expression_tagger.py` 的解耦骨架（独立单一任务 prompt + 失败硬性降级返回 `None`，绝不阻断主回复）。
- `backend/app/memory/context_builder.py`：`build_provider_context` 新增 `target_language` 参数，
  开启时注入 `[Output language]` 指令（已正确扣减 token 预算）；关闭（默认 `None`）零行为变化。
- `backend/app/schemas.py`：`ChatCompleteRequest` 加 `target_language: Literal["en","ja"]|None`，
  `ChatCompleteResponse` 加 `translation: str|None`。
- `backend/app/main.py`：`/chat/complete`（723行）+ `/chat/stream`（972行）两处接入——主 LLM 回复成功后，
  若 `target_language` 不为空才调一次 `translate_to_chinese`，结果落进 response 字段 / SSE `done.meta.translation`。
- 577 pytest 全绿（561 + 新增 16：`test_translator.py` 8 + `test_context_builder.py` 4 +
  `test_providers.py`/`test_chat_stream.py` 各 2，覆盖 on/off 两态 + provider 报错降级）。

### ~~P11-P1 · 前端 UI · 开关 + 双语展示 + localStorage 持久化~~ ✅ 已完成（2026-06-23，第五十二轮）
- **实际改动面比原计划稍大**——`frontend/src/api/chat.ts`（`requestChatComplete`/`requestChatStream`
  加 `targetLanguage` 参数 + 响应类型加 `translation` 字段）、`frontend/src/chat/types.ts`（`ChatMessage`
  加 `translation`）、`frontend/src/avatar/useAvatarState.ts`（`ChatFetchResult` 同步加 `translation`，
  编译时发现的中间类型缺漏）、`frontend/src/App.tsx`（三态循环开关：关/EN/JA，localStorage key
  `cyber-companion-target-language`，气泡渲染 `message.translation`）、`frontend/src/styles.css`
  （新增 `.message-translation` 样式）。
- **用户拍板的 3 点细节**：①历史消息译文消失（刷新后从 `/memory/messages` 拉的旧消息没有 translation）
  暂时可接受，后面要单独补一个任务做后端持久化；②toggle 只影响新消息，已显示的旧译文不回溯隐藏；
  ③切换 en/ja 不重新翻译屏幕上已有内容。
- **验证**：`tsc --noEmit` 零错误；浏览器 preview 真机验证——EN 档和 JA 档都实测过（开启后主 LLM 直接用
  目标语言回复，`translation` 字段是回译的中文，对照展示在气泡下方斜体小字）；localStorage 持久化（设置
  后刷新页面状态保留）验证通过；关闭开关后新消息恢复纯中文无译文、旧消息译文不消失，符合上面 3 点拍板；
  console 零新报错。
- **🆕 真机验证副产物（新发现，未排查，已记 HANDOFF「已知 bug/风险」）**：JA 档下 Fish 标签偶发吐出
  脏标签 `[ zufrieden]`（带前导空格 + 德语词，非词表内标签），只复现一次，根因未知，留给以后专门排查。

### ~~P11-P2 · 历史消息译文持久化~~ ✅ 已完成并真机验证 PASS，已 commit `73e996a`（2026-06-24，第五十四轮）
- **触发**：P11-P1 真机验证时用户发现"刷新页面后中文译文消失"——这是设计已知限制（见上），不是 bug。
- **实际改动**（scope 比原计划更精确）：`backend/app/memory/chat_persistence.py`（`persist_chat_turn`
  新增 `translation` 参数，仿 `decision`/`avatar_state` 写法）+ `backend/app/main.py`（`/chat/complete`
  直传；`/chat/stream` 因隐藏时序 bug 把翻译计算挪进 `_finalize_streamed_turn` 内部，函数返回值改为
  `tuple[ChatCompletionResult, str|None]`）+ `frontend/src/chat/types.ts`（`storedMessageToChatMessage`
  新增 `translation` 映射）。`backend/app/memory/store.py` **未改**——metadata 已整体透传，无需改读取层。
- **验收 ✅**：新增 2 个回归测试验证落库→读出链路；真机验证——发一条带译文的消息→刷新页面→历史
  消息气泡下方仍显示译文。579 pytest 全绿，`tsc --noEmit` 零错误。

## P15 ·（新立项，次优）Pipecat 链路对话显示双方字幕
> **2026-06-23（第五十轮）用户新提**：和 Boxi 用 Pipecat 链路对话时，想像现在纯 E2E 一样**看到双方字幕**
> （你说的 ASR 文本 + 她回的文本）。
- **现状**：`backend/realtime/run_voice.py` 跑的是 **LocalAudioTransport（本机麦克风+音箱）**，是终端语音
  循环，**没有把字幕推到前端 UI**。纯 E2E 之所以有字幕，是每轮走 `/rtc/turn` 下发。
- **本质**：把链路里**已有的** STT 识别文本（`DoubaoStreamingSTTService` 的 `TranscriptionFrame`）+
  brain 输出文本（`CompanionBrain`）接出来，推给某个 UI 通道。
- **未定/先查**：P7 加过 `/realtime/start` 等前端入口，但 **Pipecat 现在到底走不走前端、是否已有字幕通道**
  需 `/architect` 时读代码确认（别臆断）。可能要决定字幕走 WebSocket/SSE 还是别的。
- **Scope（待 `/architect` 细化）**：不动 soul/behavior/memory；只在 Pipecat transport/processor 层把两侧
  文本接出 + 前端呈现。
- **验收（初定）**：Pipecat 对话时前端能实时看到「用户说的」+「Boxi 回的」两侧文本。
- **要读（`/architect` 时）**：`backend/realtime/run_voice.py`、`backend/realtime/pipeline_router.py`（P7 入口）、
  `frontend/src/voice/`、`backend/realtime/companion_brain*.py`。

## 后续讨论名单（未拆解，仅记录方向，待用户发起详细讨论）
- **Obsidian / 电脑链接（让 Boxi 更了解我）**：⚠️ 撞 CLAUDE.md「不加宽泛文件系统访问」限制。
  正确方向是**收窄**——只读、单个指定 vault 路径、**单向 ingest** 进现有 memory/retrieval（不是实时任意 FS）。
  真正成本不在代码，在**隐私**（大量个人笔记进 prompt/embedding = 大面积 vendor 暴露）+ 同步/索引/staleness
  维护（中高）。**不是小玩法**，要做先把 scope 钉死。下次专门讨论实现可能性 + 具体功能方向。
- **mood.boredom/loneliness 墙钟化**（2026-06-22 第四十轮讨论中提出）：现状两者按 idle tick 数累积
  （`mood.py` `apply_idle_tick_mood_delta`），与现实时间脱钩、tab 关了不涨；而 `longing.py` 的
  `silence_hours` 已经是按真实时钟算的，**系统里存在双轨**。用户直觉"现实连续 N 天没找才开始攒孤独/
  无聊"是对的，但 `mood.boredom/loneliness` 同时喂 `tone.py`（决定实时对话语气），重写会牵动对话路径，
  blast radius 远超 P9-P1。**P9-P1 已绕开此问题**——想念轨迹三档直接读 `longing.py` 的墙钟 `silence_hours`，
  不碰 mood 本身。此项是**更彻底的重构**：让 mood.boredom/loneliness 本身也按真实时间分阶段累积，
  让"活人感"延伸到实时对话语气而不只是 proactive 开场白。要做先评估对 `tone.py`/`engine.py` 的影响面。



## 🐛 P13 ·（高优先级，新发现真实 bug）Pipecat Fish Audio TTS：latency=normal 时多轮对话会失声

> **2026-06-23 用户真机复核确认**：用户反馈"latency 最高音质档用不了"——即 `normal` 实际不可用，
> 与本 bug 一致。**最高音质暂时拿不到，必须停 `balanced`，等 P14 Phase 5 修。** 根因见 `docs/PIPECAT_REFERENCE.md` §5
> （基类双游标 `_turn_context_id`/`_playing_context_id` 竞态）。
> **来源**：2026-06-22，P8-C 前置 spike 真机测试时发现。换 `latency="balanced"`→`"normal"` 后，
> 第一轮对话音频正常，**从第二轮开始 TTS 完全不出声**（文字侧 STT→LLM 全程正常，`called_llm=True`
> 一直在跳，但音频帧完全不产生）。
- **根因（DEBUG 日志确认）**：Pipecat 库内部反复打印
  `FishAudioTTSService#0 unable to append audio to context: no context ID provided`。
  `TTFB` 日志显示 Fish Audio 确实把音频字节传回来了，但 Pipecat 本地维护的 audio-context 已经在
  上一轮 `TTSStoppedFrame` 触发时被清理，新音频对不上 context id，被静默丢弃。`latency="balanced"`
  下同一套代码连续跑 10 轮全部正常出声，没有这个问题——目前怀疑是 `normal`（更高音质/更慢生成）
  节奏下，context 清理时机和音频到达时机的竞态被放大触发，但具体是 Pipecat 库 bug 还是我们这边
  调用方式缺了什么（比如没有显式管理 audio context 生命周期）还没确认。
- **当前状态**：已把 Pipecat 侧 latency 改回 `"balanced"`（默认值，确认稳定），**未继续测 `low`**——
  先把这个 bug 搞清楚更划算，否则会在还没搞懂根因前继续浪费真实计费 LLM/TTS 调用。
- **Scope（下次要做的）**：① 确认这是 Pipecat 库版本的已知问题还是我们调用方式的问题（查
  `pipecat.services.tts_service` 的 `create_audio_context`/`append_to_audio_context` 相关源码 +
  GitHub issue）；② 如果是调用方式问题，看是否需要在 `companion_brain_processor.py` 或
  `run_voice.py` 里显式管理 audio context 生命周期；③ 确认问题范围是否只影响 `normal`，要不要也
  测一下 `low`（在确认根因或至少有止损方案之前不要再测,会重复触发同样的失声)。
- **要读**：`backend/realtime/run_voice.py`（`_build_tts`）、Pipecat 已安装库
  `pipecat/services/fish/tts.py` + `pipecat/services/tts_service.py`（`append_to_audio_context`/
  `create_audio_context` 相关代码）。
- **不动**：在搞清楚根因前不要随意改 `companion_brain_processor.py` 去"绕过"这个问题。

## Pipecat 真机测试隔离规范（2026-06-22 新增，强制遵守）
> **触发**：P8-C 前置 spike 真机测试时，本想用 `CYBER_COMPANION_DATA_DIR` 环境变量隔离测试数据，
> 结果**两次都失败**，测试对话被真实写进了生产库（`data/cyber_companion.db`）——根因是
> `run_voice.py:32` 的 `load_dotenv(override=True)` 会用 `.env` 文件里的值覆盖掉命令行传的环境
> 变量。已发现并清理（备份在 `data/backups/cyber_companion_pre_p8c_cleanup_20260622_220247.db`，
> 删除了污染的 messages/memories，mood_state/relationship_state 还原到当天 08:28 的值）。
- **唯一可靠的隔离方法**：**临时直接改 `.env` 文件里的 `CYBER_COMPANION_DATA_DIR` 这一行**指向隔离
  目录（比如 `./data/pipecat_spike`），跑完测试**立刻改回 `./data`**，不要依赖命令行 `VAR=value`
  覆盖（会被 `load_dotenv(override=True)` 吃掉，不生效）。
- **`backend/scripts/companion_brain_tag_eval.py` 不受影响**——它直接构造
  `MemoryStore(db_path=tempfile...)`，绕开了 `get_memory_store()`/env var 解析,天生隔离,可以放心用。
- **项目收尾时清理**：用户已确认——项目彻底完工后，所有这类隔离测试产生的数据/目录要整体删除，
  从零开始，不需要现在就保留长期归档计划。

## P12 ·（第二档，先 spike）情绪识别旁路 —— Hume prosody 声学情绪传感器
> **来源**：2026-06-18（第三十八轮）讨论。语音路径里说话的语调/起伏（声学情绪）是文字 LLM
> 拿不到的信号，文字记忆里此前一直缺这条线。
- **结论（已拍板，不要重新讨论方向）**：只取 Hume 的**测量 API** 当传感器用，**不**引入
  EVI/Inworld 那种整套对话方案去替换现有 soul（会冲淡 Boxi 人格）。
- **接入方式**：走 **off-path 旁路**喂 kernel，类似现有 `reflection/analyze_turn` 的后台分析
  模式——不挂在主对话链路上，不影响实时响应延迟。
- **优先级**：第二档（中等，非紧急）。**先做 spike**，验证信号是否真的有用 + 延迟是否可接受，
  再决定要不要正式接入，不要跳过 spike 直接做正式集成。
- **Scope（spike 阶段）**：小范围验证 Hume 测量 API 的声学情绪输出对 Boxi 语音路径（纯 E2E 或
  Pipecat 任一）是否有可用信号、延迟量级如何。不动 `behavior/`、`memory/`、`tone.py` 等现有灵魂层
  代码，先离线/旁路验证可行性。
- **验收标准（spike）**：明确回答"这条信号有没有价值、接入代价多大"，输出结论（继续做正式集成 /
  搁置 / 否决），不要求 spike 阶段就有生产代码落地。
- **状态**：未开工，连 spike 都没做。

## 暂缓（不要碰）
- UI / 视觉材质（用户未定画面；低 GPU 否决实时 shader）。
- `experiments/`（废弃 spike）。
- 人设大改（往「复杂+暧昧」走是**项目成熟后**才做，见记忆 `persona-direction-complex-intimate`）。
