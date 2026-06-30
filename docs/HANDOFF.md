# HANDOFF — 上下文交接（2026-06-30，第八十六轮 · P2 两个回声 hack 已删除，已真机验证）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

> **🟢 2026-06-30 第八十六轮（最新，P2 · 两个回声 hack 删除已实施，Claude Code 直接实施）**：
> 1. **用户明确纠正了项目运作方式**：`CLAUDE.md` 里"Claude Code 不是主要实现者"那条规则已过时，
>    用户确认 Claude Code Sonnet 4.6 是项目主力实现者，默认应直接写代码，不需要先申请"例外"。
>    只有任务规模大/复杂、或 Sonnet 反复失败时，Claude Code 才需要主动提醒用户切到 Opus 4.8
>    high。已存成长期 feedback memory（`feedback-claude-code-primary-implementer`）。`CLAUDE.md`
>    本身尚未同步更新，下次读到时应提醒用户改写那条过时规则。
> 2. **删除决策依据（两次独立真机证据）**：①第八十二轮 throwaway spike——关闭两个 hack 纯靠
>    浏览器 `getUserMedia(echoCancellation:true)`，真实多轮场景全程无回声；②本轮在**当前生产
>    `SmallWebRTCTransport` 路径**上，用 `CYBER_COMPANION_VOICE_HALF_DUPLEX=0`（进程环境变量，
>    联动关闭 self-echo）跑了 6 轮真实对话，输出设备 = 用户日常实际设备（笔记本自带喇叭，用户
>    确认没有外接音箱，所以"外接音箱无 AEC"这个原始 bug 场景对用户而言本来就不存在），日志确认
>    无回声、无 ERROR。用户主观反馈"没有发现自问自答的现象"。
> 3. **代码改动（4 文件改 + 4 文件删）**：
>    - 删除 `backend/realtime/half_duplex_mute_processor.py`、`self_echo_filter.py`
>      （及其专属测试 `test_half_duplex_mute.py`、`test_self_echo_filter.py`）。
>    - 删除 untracked 的 `backend/realtime/spike_webrtc_pipeline.py`（phase 2 throwaway 脚本，
>      已完成历史使命且直接 import 了被删模块，留着会变成死代码/导入报错，按已有惯例清理）。
>    - `backend/realtime/run_voice.py`：`_main_pipeline()` 管线装配直接退回
>      `[transport.input(), vad, stt]`，去掉 `half_duplex`/`self_echo` 两个 if 分支和所有相关
>      装配、日志字段；docstring 里"STT->hacks->brain"改回"STT->brain"。
>    - `backend/realtime/voice_config.py`：删 `ENV_HALF_DUPLEX`/`ENV_SELF_ECHO_FILTER`/
>      `ENV_SELF_ECHO_WINDOW_MS`/`DEFAULT_HALF_DUPLEX`/`DEFAULT_SELF_ECHO_FILTER`/
>      `DEFAULT_SELF_ECHO_WINDOW_MS` 及对应 `load_half_duplex_enabled`/`load_self_echo_enabled`/
>      `load_self_echo_window_ms` 三个函数；`load_asr_end_window_ms`/`ENV_ASR_END_WINDOW_MS`
>      **保留**（`doubao_streaming_stt_service.py` 仍在用，是独立的 STT 端点检测参数，跟
>      half-duplex 无关，确认过引用后未误删）。
>    - `backend/tests/test_voice_config.py`：删掉 `ENV_HALF_DUPLEX`/`load_half_duplex_enabled`
>      相关的 setenv/delenv/assert 行。
> 4. **验证**：`backend/tests` 全量 **726 passed**（743 − 17，少掉的数量正好是两个被删测试文件
>    的用例数，无其他回归）。删除后用干净配置（不带任何 env override）重启后端，`/health` 200，
>    启动日志无报错。**真机语音端到端已在"删除后的干净生产代码"上重新验证，结论 PASS**——用户
>    在干净代码上做了 4 轮真实语音对话，日志逐轮确认 STT final→`Boxi decision=reply` 清晰
>    一对一映射、无多余回声 final；启动日志确认新装配生效（`Voice pipeline ready (STT=...,
>    TTS=...) — ... browser/device AEC handles speaker echo`，不再提 half_duplex/self_echo）；
>    断开流程干净（`WebRTC client disconnected`→`Pipecat pipeline task cancelled`→
>    `/realtime/stop 200 OK`）；全程无 ERROR/Traceback。
> 5. **本轮未改动**：`half_duplex`/`self_echo` 以外的任何语音管线代码（TTS/tagger/transport/
>    brain 均未碰）；`docs/ARCHITECTURE_SNAPSHOT.md` 未提及这两个 hack，故未改。
> 6. **结论：P0-OSS-4（Pipecat 去自研化）核心三项——transport 迁移、前端 WebRTC 客户端接入、
>    两个回声 hack 删除——全部完成并真机验证 PASS，正式结案，无遗留阻塞。**
> 7. **下一步候选**（均未开工，无优先级排序）：①打断/barge-in 独立管线重构任务（少了
>    half-duplex 强制静音麦克风后，理论上离"麦克风不再被物理静音"更近一步，但管线仍无
>    "用户开始说话→取消 TTS"信号链，这轮没有顺带解决打断能力）；②voice-ui-kit 接入范围 +
>    远程场景 TURN/STUN（P2，跟本轮解决的"同机自连"网络坑是两回事）；③P1-OSS-5 单角色"自己的
>    生活"；④`docs/TASK_QUEUE.md` 候选名单（长期记忆/情绪性格/主动联系/身份层，13 个未核实
>    项目名）。建议跟用户讨论选哪个，不要擅自挑一个开工。

> **🟢 2026-06-30 第八十五轮（用户真机验证 PASS）**：
> 1. **第八十四轮遗留的"待用户真机验证"已完成，结论 PASS**。用户在 `http://127.0.0.1:5173`
>    （Claude Code 本轮代为起的前端 dev server；后端是此前某 session 后台启动的常驻进程，
>    PID 未变）点击"开始 Soul 语音"测试，反馈"一切正常"。
> 2. **Claude Code 交叉核实方式**：用户的后端进程没有挂在任何终端上（`ps` 查到 `TTY=??`），
>    是此前某个 Claude Code session 用 `run_in_background` 之类方式启动、stdout/stderr 已经
>    被重定向进一个 scratchpad 日志文件——本轮没有新增日志机制，只是发现并读取了已存在的文件。
>    日志显示三轮真实语音对话全部正常：STT（豆包流式 `partial→final`）→
>    `companion_brain_processor` `decision=reply avatar_state=talking called_llm=True` →
>    `expression_tagger_processor` 逐句标签（含一次 `Sentence tagger altered the wording`
>    安全降级，行为符合既有设计，非新 bug）。用户主动停止时序干净：
>    `pipecat.transports.smallwebrtc...Media stream error while reading the audio; clearing
>    track` →`Discarding peer connection`→`backend.realtime.run_voice:_on_client_disconnected`
>    →`pipeline_router:stop_pipeline` `[P7] Pipecat pipeline task cancelled`→
>    `POST /realtime/stop 200 OK`。全程无 ERROR/Traceback。
> 3. **结论：P0-OSS-4 的 transport 换血序列（spike→生产迁移→前端客户端接入）全部完成且全部
>    真机验证 PASS，没有遗留阻塞项。** 两个回声 hack（`half_duplex_mute_processor.py`/
>    `self_echo_filter.py`）保持默认开启、本轮未碰。
> 4. **本轮未改动任何生产代码**，只更新了 `docs/HANDOFF.md`/`docs/TASK_QUEUE.md`。
> 5. **下一步 = 讨论 P2：两个回声 hack 删除决策**——前置条件（transport 迁移 PASS + 真机验证
>    PASS）均已满足；需要讨论的是要不要现在删，还是再等一段时间真实日用观察后再决定（详见
>    `docs/TASK_QUEUE.md` P0-OSS-4 节）。

> **🟢 2026-06-30 第八十四轮（前端 WebRTC 客户端接入）**：
> 1. **P1（前端 WebRTC 客户端接入）已完成（信令层 + 连接生命周期 hook + 整合），`tsc --noEmit`
>    全绿、前端 vitest 34 passed，但真机端到端（真实麦克风+扬声器+ICE 握手+TTS 出声）未验证，
>    留给用户下一步。** 这是承接上一轮（第八十三轮）后端 transport 迁移的前端配套——之前前端
>    `startPipecat()` 还是空 body POST，调新版 `/realtime/start` 必 422，本轮补上。
> 2. **代码改动（3 文件改 + 2 文件新增）**：
>    - `frontend/src/voice/pipecatApi.ts`：`startPipecat()` 从空 body POST 改为接收
>      `{sdp, type}` SDP offer、POST JSON body、返回 `{sdp, type, pc_id}` SDP answer。answer
>      字段已对照 pipecat 源码 `SmallWebRTCConnection.get_answer()`
>      （`pipecat/transports/smallwebrtc/connection.py:558`）确认，非猜测。
>    - 新增 `frontend/src/voice/useWebRtcVoiceConnection.ts`：`useWebRtcVoiceConnection()` hook，
>      暴露 `connect(): Promise<void>` / `disconnect(): void`。内部用 `useRef` 管理
>      `RTCPeerConnection`/`MediaStream` 生命周期：`getUserMedia → createOffer →
>      setLocalDescription → 等 ICE gathering complete`（非 trickle，参考
>      `spike_webrtc_client.html` 已验证过的握手序列）`→ startPipecat(offer) →
>      setRemoteDescription`；`ontrack` 把远端音轨接到**程序化创建的 `new Audio()`**（不是 DOM
>      `<audio>` 元素 + ref 透传——沿用项目里 `audioUnlock.ts`/`useTextToSpeech.ts` 已有的
>      "detached Audio() 在用户手势调用栈内播放"惯例，因此完全没有触碰
>      `PipecatVoicePanel.tsx`/`App.tsx`）；麦克风拒绝/握手失败/连接 `failed`/`closed` 都统一
>      转成可读 `Error` 并清理资源（停 track、关 pc、暂停清空 audio）。
>    - `frontend/src/voice/usePipecatVoice.ts`：`start()`/`stop()` 改调
>      `useWebRtcVoiceConnection` 的 `connect()`/`disconnect()`；`refreshStatus()` 新增防御性
>      逻辑——后端状态轮询发现非 running（无论是正常 stopped、报错、还是请求异常）都会调用
>      `disconnect()`，防止后端 pipeline 意外崩溃后前端还占着麦克风不放。
> 3. **验证中顺带修了一个真实 bug**：`useWebRtcVoiceConnection.ts` 内部的 `toError()` 原先在
>    `err` 本身已经是 `Error` 实例时（比如 `getUserMedia` 拒绝抛出的 `DOMException`，浏览器里
>    是 `Error` 子类）会直接原样返回，把传入的上下文消息整个丢掉——导致 UI 上只显示裸的
>    "Permission denied"，看不出是麦克风问题还是别的环节失败。已改成统一拼接
>    `"${contextMessage}: ${detail}"`，浏览器 preview 验证后变成 "Microphone access denied:
>    Permission denied"，更可读。
> 4. **测试环境小修正**：`waitForIceGatheringComplete()` 最初用 `window.setTimeout`/
>    `window.clearTimeout`（项目里 `usePipecatVoice.ts` 既有写法），但 `vitest.config.ts` 全局
>    是 `environment: "node"`，没有 `window` 全局对象，导致单测报 `window is not defined`。
>    改全局测试环境超出本任务 scope，换成不依赖 `window` 前缀的全局 `setTimeout`/`clearTimeout`，
>    浏览器运行时行为完全等价。
> 5. **验证**：`tsc --noEmit` 全绿；前端 `vitest` **34 passed（8 files）**（pipecatApi 4 +
>    useWebRtcVoiceConnection 5 + 既有 25）。浏览器 preview 实测：点击"开始 Soul 语音"按钮，
>    headless 环境无真实麦克风，`getUserMedia` 按预期报 "Microphone access denied: Permission
>    denied"；`preview_network` 确认这种情况下**没有任何 `/realtime/start` 请求被发出**——证明
>    错误处理在握手前正确短路，没有带着空/无效 offer 打后端。**真正的端到端验证（真实麦克风+
>    扬声器+ICE 握手+STT/brain/tagger/TTS 全链路出声）这台环境做不了，需要用户在真机浏览器里
>    测——这是下一步。**
> 6. **本轮严格未触碰**：`PipecatVoicePanel.tsx`、`App.tsx`、`useVoiceTranscript.ts`、任何后端
>    文件（后端 transport 迁移是上一轮/第八十三轮已经做完的事）。
> 7. **下一步**：①**用户真机验证**——开前端 + 后端，点"开始 Soul 语音"，确认麦克风权限弹窗正常、
>    SDP 握手成功、能听到 Boxi 出声、断开正常释放麦克风；②验证 PASS 后才能评估 P2（两个回声 hack
>    `half_duplex_mute_processor.py`/`self_echo_filter.py` 删除决策，在真实多轮日用场景下观察
>    是否真的不需要了）；③打断/barge-in 仍是独立的管线重构任务，跟本轮无关。

> **🟢 2026-06-30 第八十三轮（Claude Code 例外直接实施）**：
> 1. **P0-OSS-4 第三阶段（生产 transport 迁移）已完成并真机端到端验证 PASS**——这是本项目第一次
>    由 Claude Code 直接写代码（用户在本轮明确豁免「Claude Code 不做主要实现」的默认规则，仅本次例外）。
> 2. **代码改动（3 文件改 + 2 文件新增，diff: 173 插入/79 删除）**：
>    - `backend/realtime/run_voice.py`：`_main_pipeline()` 新增可选参数
>      `webrtc_connection: SmallWebRTCConnection | None`。`None`（CLI `python -m
>      backend.realtime.run_voice` 直跑路径）保持原 `LocalAudioTransport` +
>      `PipelineWorker`/`WorkerRunner` 不变；传入真实连接时（生产路径）改用
>      `SmallWebRTCTransport` + `PipelineTask`/`PipelineRunner`（这是
>      `spike_webrtc_pipeline.py` 第二阶段已验证过的组合，不是新猜的）。STT→两个回声
>      hack→brain→tagger→TTS 这条处理器链两条路径完全共用，未改动。
>    - `backend/realtime/pipeline_router.py`：`/realtime/start` 改造成 WebRTC 信令入口
>      （思路 A，按用户拍板）——接收 `SmallWebRTCRequest`（`{sdp, type}`），用官方
>      `SmallWebRTCRequestHandler(connection_mode=ConnectionMode.SINGLE)` 处理 offer/answer
>      握手，返回 SDP answer；`/realtime/stop` 同时断开 WebRTC 连接 + 取消 pipeline task；
>      `/realtime/status` 不变。**前端 `pipecatApi.ts` 的 `startPipecat()` 目前还是空 body
>      POST，调用新 `/realtime/start` 会被 422 拒绝——这是预期的、未完成的部分，留给 P1（前端
>      WebRTC 客户端）补，不是本轮 bug。**
>    - 新增 `backend/realtime/webrtc_loopback_candidate.py`：**关键修复**，详见下方「真机验证
>      踩坑」。
>    - `backend/tests/test_pipeline_router.py` 改写两个测试以适配新签名（monkeypatch
>      `_webrtc_handler.handle_web_request` 绕开真实 aiortc SDP 协商）；新增
>      `backend/tests/test_webrtc_loopback_candidate.py`（3 个测试）。
> 3. **真机验证踩坑 + 根治（不是本任务代码的 bug，是这台机器的网络环境问题，但已经用代码层面
>    彻底解决，不依赖网络环境）**：
>    - 现象：浏览器连上了（SDP 握手成功、麦克风轨道协商成功），但完全没有声音，STT 反复报
>      "8 秒没收到任何音频包"，aiortc ICE 卡在 checking 状态直到 60 秒超时。
>    - 排查链路：防火墙（两个相关 python 二进制 + Chrome 都已放行，排除）→ CORS（验证页面端口
>      不在白名单导致 fetch 失败，换端口绕过，非真因）→ 用 DEBUG 级别打开 `aioice` 底层日志，
>      看到反复 `OSError: [Errno 32] Broken pipe`，发送方是 Python 这边往浏览器候选端口发
>      STUN 包 → 用纯 `asyncio` 写了个不依赖 aiortc 的最小复现脚本，坐实：**这台 Mac 上，
>      自己发给自己的 UDP 包如果用 WiFi 网卡的局域网 IP（`192.168.68.52`）会被静默丢弃（内核
>      路由表显示走 `lo0`，但实际没到），换成真正的回环地址 `127.0.0.1` 完全正常**——典型的
>      WiFi 路由器 AP/客户端隔离（client isolation）特征。
>    - 根治：`aioice.ice.get_host_addresses()` 硬编码排除 `127.0.0.1`（只为跨设备通话场景
>      设计，不适合 Boxi「浏览器和后端永远同一台机器」的场景）。新增
>      `webrtc_loopback_candidate.py`，对 `aioice.ice.get_host_addresses` 做一个小范围受控
>      monkeypatch，让它在正常局域网候选之外**额外**返回 `127.0.0.1`（局域网候选不删，只是加），
>      ICE 因此多一对必定能连通的候选地址组合，不依赖用户去翻路由器后台关 AP 隔离、也不受
>      换网络环境影响。修复后真机连接：STT 识别用户语音 final transcript、brain 调用 LLM
>      回复、tagger 加情绪标签、TTS 真实出声，全链路确认正常。
> 4. **验证**：`backend/tests` 全量 **743 passed**（740 + 3 新增）；真机端到端一轮对话 PASS
>    （用户原话："能听到声音了"，日志确认 STT/brain/tagger 全部正确触发）。
> 5. **本轮严格未触碰**：`half_duplex_mute_processor.py`、`self_echo_filter.py`（两个回声
>    hack 默认开启、逻辑不变）、`companion_brain*.py`、frontend/、TURN/STUN 配置（按
>    open question 3 决策，本轮不做，远程访问场景以后单独评估）。
> 6. **下一步**：①P1——前端 WebRTC 客户端接入 `PipecatVoicePanel`（`pipecatApi.ts` 的
>    `startPipecat()` 需要改成真正发 SDP offer、收 answer；可参考
>    `backend/realtime/spike_webrtc_client.html` 的握手逻辑作为实现起点）；②P2——两个回声
>    hack 删除决策（P0+P1 上线、经过真实日用后再评估，不要在这之前删）；③打断/barge-in 仍是
>    独立的管线重构任务，跟本轮无关。

> **🟢 2026-06-30 第八十二轮**：
> 1. **P0-OSS-4 第二阶段（真实多轮管线 transport 切换）已完成真机验证**，结论详见
>    `docs/TRANSPORT_SPIKE_RESULTS.md` 新增的「第二阶段」节。新建独立 throwaway 脚本
>    `backend/realtime/spike_webrtc_pipeline.py`（不改 `run_voice.py`/`pipeline_router.py`/
>    两个 hack 源文件，复用 `run_voice.py` 现成构建函数，管线组装顺序与生产 `_main_pipeline()`
>    完全一致，唯一替换点是 transport）。
> 2. **两组真机实验**：①两个 hack 保持默认开启——行为与生产 `LocalAudioTransport` 路径一致
>    （打断不了是 `HalfDuplexMuteProcessor` 按设计静音麦克风,非新问题），无回归；②临时关闭两个
>    hack（仅进程环境变量 `CYBER_COMPANION_VOICE_HALF_DUPLEX=0`,未改 `.env`,`self_echo_enabled`
>    联动自动关闭）,纯靠浏览器原生 AEC——**真实多轮场景下全程无自问自答/回声**,验证了 AEC 可以
>    顶替这两个 hack 的回声压制功能,不止 phase-1 loopback 简单场景。
> 3. **重要负面发现：打断/barge-in 不能靠换 transport 解决**。日志坐实——STT 在 Boxi 说话期间
>    持续正常识别用户语音（partial transcript 实时可见），但用户的话只是排进下一轮、等 Boxi
>    自然说完才处理,管线没有触发任何"打断/取消当前 TTS"信号。根因与 transport 无关,跟已知的
>    smart-turn 挂不上同源——`CompanionBrainProcessor` 绕开了标准 `LLMUserAggregator`,没有
>    "用户开始说话→发 interruption frame→取消 TTS"的信号链,`allow_interruptions=True` 本身不会
>    自动生效。**不要把"打断"算作换 transport 顺带解决的收益,这是独立的管线重构任务。**
> 4. **基本功能（STT 识别/brain 回复/TTS 播放）在真实多轮场景下确认无退化。**
> 5. **下一步候选**：①P0-OSS-4 第三阶段——决定是否真的把生产 `run_voice.py` 迁移到
>    `SmallWebRTCTransport`、删除两个回声 hack（现在有真机证据支持"可删"）；②真正的打断能力是
>    独立的管线重构任务,需要先决定要不要做、怎么做（接标准 aggregator 还是自定义信号）；
>    ③voice-ui-kit 接入范围 + 远程 TURN/STUN 调研（P2，未开始）。
> 6. **本轮未改动任何生产代码**——只新增一个 throwaway spike 脚本 + 追加了 spike 结果文档一节，
>    `run_voice.py`/`pipeline_router.py`/两个 hack 文件均未触碰。

> **🟢 2026-06-30 第八十一轮**：
> 1. **P0-OSS-4 spike 核心测量已完成，结论 Accept**：详见新建的 `docs/TRANSPORT_SPIKE_RESULTS.md`。
>    用 `backend/realtime/spike_webrtc_loopback.py -t webrtc` + `backend/realtime/spike_webrtc_client.html`
>    跑通 mic→`SmallWebRTCTransport`→speaker 最小 loopback（不接 STT/brain/TTS）。数据通道 RTT
>    （n=89）avg=2.8ms / min=1.4ms / max=21.2ms；真机主观听感：延迟正常，对外接音箱说话/拍手
>    回放干净无重复/嗡鸣——`getUserMedia(echoCancellation:true)` 的回声压制有效。
> 2. **过程中排查并修复三个环境/脚本问题（细节见 `TRANSPORT_SPIKE_RESULTS.md`）**：①macOS 应用
>    防火墙未放行 `.venv` 实际运行的 `Python.app/Contents/MacOS/Python` 二进制,导致 ICE 一直卡
>    `checking` 直到 60s 超时,已加入 `socketfilterfw` 允许列表；②**`spike_webrtc_client.html`
>    本身有 non-trickle ICE bug**（`setLocalDescription` 后立刻发 offer,没等 ICE candidate 收集
>    完成,SDP 里没有候选地址）,已修复为等待 `pc.iceGatheringState==="complete"` 后再发送
>    `pc.localDescription.sdp`；③调试时发现该脚本不能用 `exec()` 包装跑,会破坏 pipecat
>    `runner.run.main()` 靠调用栈反射定位 `bot` 函数的机制,导致连接表面建立但
>    `on_client_connected`/app-message 都不触发——必须用标准 `python spike_webrtc_loopback.py -t
>    webrtc` 方式跑。
> 3. **本 spike 完全独立 throwaway,不影响生产语音管线**：未改动 `run_voice.py`/
>    `pipeline_router.py`/`companion_brain*.py`；唯一改动的生产相关文件是
>    `spike_webrtc_client.html` 本身（修 bug）。
> 4. **下一步 = P0-OSS-4 第二阶段：生产迁移评估**（`LocalAudioTransport`→`SmallWebRTCTransport`）。
>    需要单独判断：①`half_duplex_mute_processor.py`+`self_echo_filter.py` 两个 hack 能否删除
>    （理论上浏览器原生 AEC 顶替,但要在真实多轮对话管线上验证,不是 loopback 这种简单场景）；
>    ②`voice-ui-kit` 组件接入范围；③本机 localhost 没有 TURN/STUN 问题,但如果以后要支持
>    远程/真机访问需要补；④smart-turn 接入仍是独立任务,跟 transport 换血无关
>    （管线没有标准 `LLMUserAggregator`，`CompanionBrainProcessor` 绕开了它）。

> **🟢 2026-06-29 第八十轮**：
> 1. **P0-OSS-4（Pipecat 去自研化）已用 `/architect` 拆解 + 完成清单审计**，盘点了
>    `backend/realtime/` 全部 19 个文件 + `frontend/src/voice/` 全部文件，逐个标注"可被官方组件
>    替代/Boxi 专属保留/疑似死代码"。关键结论：①生产 TTS 已经在用官方 `FishAudioTTSService`，
>    合规；②Mem0 对照无对应物（语音记忆复用文字聊天共用的 SQLite 主线，没有另起胶水）；
>    ③`smart-turn` 现在挂不上是因为管线没有标准 `LLMUserAggregator`（`CompanionBrainProcessor`
>    绕开了它），跟 transport 无关；④`half_duplex_mute_processor.py`/`self_echo_filter.py` 解决
>    的是声学回声（无 AEC），跟 smart-turn 解决的"用户说完没说完"是不同问题；⑤豆包 TTS 三件套
>    （`doubao_streaming_tts_service.py`/`doubao_bidirection_tts_protocol.py`/
>    `doubao_tts_service.py`）疑似死代码（生产路径已确认走 Fish,未见这三个文件被实际调用),需要
>    核实引用后决定删除；⑥`mac_say_tts.py` 同样疑似死代码。
> 2. **讨论后追加了一个高价值候选：Transport 换血**——把 `LocalAudioTransport`（后端直连本机
>    麦克风/扬声器,前端只是远程控制面板）换成 WebRTC 兼容 transport（`SmallWebRTCTransport`），
>    可能同时解决三件事：①浏览器原生 AEC（白送,memory `voice-bargein-needs-aec` 早就指出这是
>    真正解法）,届时可删掉 `half_duplex_mute_processor.py`+`self_echo_filter.py` 两个 hack；
>    ②解锁 `voice-ui-kit` 组件可用；③真正的打断/barge-in。**已记一条新 feedback memory**：
>    diff 大/需要架构改动不是降级或拒绝候选的理由,只有硬件/画风/实测指标冲突才是。
>    已 `/architect` 拆成 spike验证→生产迁移→smart-turn接入 三阶段。
> 3. **P0（spike 验证）开工但只完成"环境准备"，核心交付物（延迟实测+真机 AEC 效果+
>    accept/reject 结论）未做，留给下一 session**。已确认 `SmallWebRTCTransport` 能正常 import
>    可用。过程中 `pip install "pipecat-ai[webrtc]"` 意外把生产 `pipecat-ai` 从 1.3.0 降到
>    0.0.108（连带改了 numpy/av/tokenizers），**已修复**：`pip install --no-deps "pipecat-ai==1.3.0"`
>    恢复正确版本（`onnxruntime` 按 `backend/requirements-realtime.txt` 注释的已知 workaround
>    维持 `1.23.2`，不能用默认 resolver 装 1.3.0 否则会卡在 `onnxruntime~=1.24.3` 在这个平台
>    没有 wheel）。验证：筛选子集 93 passed + **全量 backend 740 passed**，搬移前后各跑一次确认
>    零回归。
> 4. **顺带彻底根治了 iCloud venv 隐患（长期记忆 `dev-machine-icloud-venv-risk` 记录的老问题）**：
>    `.venv`（643M）+ 根 `node_modules`（32M）已用 `mv` 物理搬到 `~/.venvs/`（完全脱离
>    `~/Documents` 的 iCloud "桌面与文档" 同步范围），原路径留 symlink，所有现有脚本/路径不用改。
>    验证：搬移后 740 backend 跑 26.11s（无冷文件延迟）；`node_modules/.bin/tsc`/`npx tsc` 正常
>    解析。**⚠️ 如果以后整个 `.venv` 或 `node_modules` 被删了重建,新建的会重新落进
>    `~/Documents`、重新进入 iCloud 同步范围——这不是自动生效的系统设置,重建后要记得再搬一次。**
> 5. ~~**意外发现一个跟本轮无关的真实 pre-existing bug**~~ **✅ 已排查，结论：不是真回归。**
>    `npm run check --workspace frontend`（`tsc --noEmit`）一度在 `frontend/src/rtc/useRtcVoice.ts`
>    报 7 个类型错误（`Property 'on' does not exist on type 'IRTCEngine'`）。当时误判为已提交到
>    仓库的真实回归，用 `spawn_task` 立案（worktree `affectionate-einstein-77a2d3`）。**2026-06-30
>    worktree 任务排查坐实：根因是该 worktree 的 `node_modules` 没装全，跟 `npm ci` 后 tsc 全绿，
>    未改任何源码**——不是真的类型回归。worktree 已清理（无需合并，唯一产出是这条文档结论，已写入
>    `docs/TASK_QUEUE.md` 顶部环境提醒）。
> 6. **下一步 = 继续 P0 spike 核心工作**：搭最小 loopback 管线（mic→`SmallWebRTCTransport`→
>    speaker，不接大脑）实测端到端延迟；开浏览器真机测 `getUserMedia(echoCancellation:true)`
>    对外接音箱回声的真实压制效果（**AEC 实际发生在浏览器音频采集层，不是 aiortc/Python 后端**——
>    这是本轮纠正的一个之前的简化说法）；产出 accept/reject 结论后再决定要不要进入生产迁移阶段。

> **🟢 2026-06-29 第七十九轮**：
> 1. **P0-OSS-3（具身与屏幕感知复用）已结案，结论：两项均 reject**，纯文档/网络调研，未跑本地
>    spike、未装任何软件。①**Open-LLM-VTuber**：只读官方 README/Live2D 文档，确认展示层（网页版/
>    桌面客户端/桌面宠物浮窗）三种模式都基于 Live2D 渲染，"可定制"仅指换模型外观，没有无头/静态
>    图片/非二次元风格选项——与 AIRI reject 理由同构，画风直接冲突。②**screenpipe**：只读官方
>    文档/GitHub issue，未本地安装。官方建议最低 8GB RAM（这台机器总共 16GB）；真实 issue #183
>    报告过 CPU>100%+RAM>10GB 故障；accessibility-only 模式下,accessibility 数据不可用时仍会
>    自动 fallback 到 OCR,可能绕不开"禁高频 OCR"硬性要求。资源画像跟硬件"轻本地编排"原则冲突，
>    与 Hindsight reject 同类理由（量级更夸张）。详见更新后的 `docs/TASK_QUEUE.md` P0-OSS-3 节。
> 2. **重要澄清**：reject 这两个开源候选**不代表"看到用户在做什么"的真实感缺口消失**——只是
>    现成方案在这台硬件上不可行，缺口仍在，需要找更轻量替代方案或暂时接受空缺。
> 3. **用户提供了一批未核实的候选项目名单**，按模块归类记入 `docs/TASK_QUEUE.md`「候选名单」
>    节（长期记忆/情绪性格/主动联系/身份灵魂层四类，共 13 个项目名）。**全部未做任何调研**，
>    只是先占位，排到对应模块任务时再花小成本核实是否真实存在/活跃/license 兼容。
> 4. **下一步 = P0-OSS-4（Pipecat 去自研化）**，已用 `/architect` 开始拆解（拆解结果见对话记录，
>    本轮 HANDOFF 暂未细化子任务，下一 session 若中断需重新 `/architect` 一次）。

> **🟢 2026-06-29 第七十八轮**：
> 1. **P0-OSS-2（Hindsight memory spike）已结案，结论 reject-for-now**：真实自托管 Hindsight
>    （本地 Docker 容器 + DeepSeek 做 LLM provider，未接入生产路径）跑了 5 个固定中文 fixture
>    （单跳/多跳/时间矛盾/关系变化/跨日召回）vs canonical SQLite。canonical 5/5 命中，Hindsight
>    4/5——唯一 miss 是跨日召回（recency 推理），恰好是审计文档预期它最强的场景。另外三个独立
>    反对理由：①常驻 Docker 容器吃 ~900MB+ RAM，跟硬件"轻本地编排"原则冲突，且 Hindsight 没有
>    embedded 模式（早期从网页摘要得到的"HindsightServer 内嵌服务器"是 AI 摘要工具编造的，解压
>    真实 wheel 验证后确认不存在）；②真实 SDK 没有按 id 删除单条记忆的接口（只有整库清空），
>    同步写入也拿不到可用 id，比 canonical 现有功能倒退；③写入内容会被 LLM 抽取改写，不存原文。
>    详见 `docs/HINDSIGHT_MEMORY_SPIKE.md`。**非永久否决**，样本量小，重测需更大样本。
>    新增非生产代码：`backend/app/memory/adapters/hindsight_candidate.py`（对照真实 SDK 源码写的
>    adapter，非凭文档猜）、`backend/scripts/memory_backend_fixtures.py` + `memory_backend_ab.py`
>    （A/B 评测脚本，dry-run 免费/--live 接真实服务）、`backend/tests/test_hindsight_candidate.py`。
> 2. **本轮副产物（环境/磁盘问题，非任务本身）**：①为测 Hindsight 装了 Docker Desktop（brew
>    cask），按用户要求测完已停止移除 Hindsight 容器，**Docker Desktop 本体暂时保留**（用户口头
>    同意，后续确认用不上要提醒卸载）；②排查中发现本机本地磁盘一度只剩 12GB，根因是
>    `/private/var/folders` 下 Codex/Chrome 的代码签名校验临时克隆文件 + App Store 缓存堆积到
>    32GB 未自动清理，已清掉，可用空间回到 47GB；③**发现项目目录（含 `.venv`）在 iCloud Drive
>    同步范围内**，磁盘紧张时 iCloud "优化储存空间"会把 venv 里的 Python 包文件换成占位符，导致
>    pytest 间歇性读空文件报错（`wc -c`/`ls` 显示的文件大小是元数据假象，不代表本地真的有内容，
>    必须用 `cat`/`python open().read()` 才能验证真实是否在本地）——这是长期隐患，磁盘再紧张会
>    再犯，根治需要把 `.venv` 移出 iCloud 同步范围，本轮未做（只是腾出空间绕过了，不是修复）。
> 3. **下一步 = P0-OSS-3（具身与屏幕感知复用）**，按 `docs/TASK_QUEUE.md` 范围；评估
>    Open-LLM-VTuber 前先确认有无非二次元展示选项（画风预警已写进队列）。

> **🟢 2026-06-29 第七十七轮**：
> 1. **A2（本地物归位）已完成**：`.gitignore` 新增 `experiments/`、`.agents/`、`.cursor/`、`.mcp.json`、
>    5 个历史 A/B 数据子目录；`git status` 清爽，只剩本文件改动。`run_voice.py` 的 `_LatencySpikeLogger`
>    探针在 A1 合并时已被清理，HANDOFF 旧条目过期，本轮未发现需要处理的代码残留。
> 2. **P0-OSS-1（AIRI baseline spike）已结案，结论 reject**：隔离目录 `~/airi-spike/`（已删除）
>    跑通 `apps/stage-tamagotchi`，用 `pnpm install --filter` 跳过 `services/minecraft` 的
>    `isolated-vm` 编译阻塞，验证了 AIRI 展示层与对话/记忆层确实是独立 package。**Reject 主因 =
>    画风不符**（AIRI 整套是 Live2D/二次元虚拟主播形象，Boxi 明确不走这个视觉方向）；次要支撑证据
>    = 开发模式空闲态单进程持续 ~96-97% CPU + 总 RSS ~2.4GB，对 2019 Intel i5 是显著负担。详见
>    `docs/AIRI_BASELINE_SPIKE.md`。**画风预警已写进 TASK_QUEUE**：P0-OSS-3 候选 Open-LLM-VTuber
>    同样是 Live2D 路线，评估前先确认有无非二次元展示选项，避免重复踩坑。
> 3. **下一步 = P0-OSS-2（Hindsight memory replacement spike）**，按 `docs/TASK_QUEUE.md` 范围
>    （独立 DB/服务 + adapter + 固定 Boxi fixture，不先改 canonical SQLite）。

> **🟢 2026-06-29 第七十六轮**：
> 1. **路线重置已落盘**：codex 的 2026-06-29 重置（删关系节流 + store.py 拆 mixin + 前端默认 Pipecat
>    + 最近邻审计）经 Opus 审查 PASS，分 4 个主题 commit + 1 个路线图 commit 落在
>    `codex/voice-stabilization-20260627`（`2dacd28`/`e36847d`/`1016af8`/`ef6944a`/`98a9559`）。
>    736 backend + tsc 绿。`run_voice.py` 探针 + experiments/data/工具配置按约定仍保持本地未提交。
> 2. **完整剩余任务地图 = `docs/ROADMAP.md`（向前看的唯一权威）**——含依赖图 + Track A–E，已切到
>    Sonnet 可执行粒度。**新 session 务必读它**（`/resume-lite` 默认不读，需手动加）。
> 3. **A1 分支收敛已完成**：路线重置经确定性合并(`-s ours`+overlay)进 master(`f086eb0`)，
>    736+tsc 绿，**已 push origin/master**；本地/远端只剩 master 单分支单 worktree；冗余分支全删，
>    保底标签 `backup/master-pre-a1`/`backup/voice-pre-a1`/`archive/*`。**所有后续以 origin/master 为准。**
> 4. **下一步 = A2 本地物归位**（gitignore experiments/data/工具配置 + 处理 run_voice.py 探针，small diff）
>    → **B1 AIRI baseline**（首个开源替换 spike，可交 Sonnet）。细则见 `docs/ROADMAP.md` Track A/B。
> 4. **冻结新自研**：B 序列期间不加自研功能，只做开源替换 spike + 7 天日用验收(Track C, 并行)。

## ⚠️ 给新 session 的最小上手指引

1. 先读本文件 + `docs/MVP_STATUS.md`（进度记分牌 + 下一步，单一事实来源）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`，**不要全仓库扫描**。

> **2026-06-29 产品原则/开源路线重置（当前）**：用户明确本项目永久私人使用，目标是不惜代价追求
> 关系真实感；依恋与用户依赖是允许的设计手段。代码已删除 quiet hours、主动联系 daily cap、
> post-conversation/fire gap、ignore-backoff、被忽略后不升级、local-line cooldown、长离线 Δt cap、
> proactive LLM daily cap 与反 guilt/neediness/accusation prompt；schema v9 会清掉旧 guard metadata。
> 机器安全、文件权限与全局费用开关保留。硬件固定为 2019 13-inch Intel i5/16 GB MacBook Pro，重
> 本地模型与持续视觉暂缓。项目同时完成 exhaustive 最近邻调查，结论是长期记忆、具身/桌宠、屏幕
> 感知和“自己的生活”存在严重闭门造车；语音因 Pipecat 相对正确。今后 Boxi = identity/关系原则/
> 用户数据/Shared Soul 薄层 + 最强上游。下一任务 P0-OSS-1 = 隔离运行 AIRI 官方 macOS x64 baseline，
> 随后 P0-OSS-2 = Hindsight memory replacement A/B。证据见
> `docs/NEAREST_NEIGHBOR_AUDIT_2026-06-29.md`。
> 验证：`PYTHON_BIN=.venv/bin/python npm run check` **736 backend passed + tsc 绿**；
> invariant **358 passed**；frontend Vitest **28 passed**；`git diff --check` 绿。

> **2026-06-28 #8 深档 checkpoint（本轮）**：前端默认语音入口已从 RTC-AIGC 切到 soul-authored Pipecat。新 `PipecatVoicePanel` 直接控制 `/realtime/start|stop|status`，展示 `/realtime/transcript` 双方字幕；RTC-AIGC 保留在「实验对照」折叠区，两条语音入口互斥。后端 status 新增 `last_error`，启动失败不再在 UI 假显示 running。当前仍用 `LocalAudioTransport`（后端连本机麦克风+扬声器），未做浏览器原生音频传输。验证：前端 **28 passed + tsc 绿**，后端 **747 passed + 366 invariant**，`git diff --check` 绿；`/health=ok`、`/realtime/status=stopped,last_error=null`。**P0 = 12/12，下一步只做 7 天日用验收，不开 P1/P2。**
>
> **2026-06-28 体检+浅档 checkpoint（前序同日浅档）**：跑了全盘代码体检（产物在 `_audit/`，已 gitignore）。结论：代码健康（平均复杂度 A、182/187 文件 MI A 级、无 import 循环），非屎山。已做：① 语音主线**浅档决策**——Pipecat cascaded(soul-authored, `CYBER_COMPANION_VOICE_MODE=pipeline`) = 规范主线，RTC-AIGC 降为可运行的实验对照面（两者独立 surface，玩 RTC 不受影响）；已写进 `ARCHITECTURE_SNAPSHOT.md`。② 零风险止血：`ruff` 删 24 个未用 import。③ **重构 `memory/store.py`**：按职责拆成 6 个 mixin（`_store_messages/_memories/_loops/_state/_records/_meta` + `_store_helpers`），`MemoryStore` 公共 API 与导入路径**完全不变**；MI **C0.35→A89.9**，整个 memory 包无 C/F 文件。④ 文档对齐：建 `docs/MVP_STATUS.md`（记分牌+完全体路线图+文档地图），并把 `AGENTS.md`/`.cursor/rules/cyber-companion.mdc`/`CLAUDE.md` 三处「session 必读」统一为 HANDOFF+MVP_STATUS+ARCHITECTURE_SNAPSHOT+TASK_QUEUE，旧 spec/SESSION_LOG 降级为「历史，勿当现状」。**当时 745 passed**。该 checkpoint 当时记录的唯一 P0 缺口 #8，已由上方第七十四轮深档闭合。
2. **当前分支 = `codex/voice-stabilization-20260627`，voice implementation checkpoint = `dd026ee`**。已从 `codex/soul-runtime` 的 `f1298d3` 分离；工作树仍有故意不提交残留：
   - `backend/realtime/run_voice.py`（`_LatencySpikeLogger`，P8-C 探针）——**不要 commit**。
   - untracked：`experiments/tagger_ab.py`（已本地改过，见下）、`experiments/tagger_listen_haiku.py`、
     `voice_compare.py`、`data/tagger_eval/`、`.mcp.json` 等实验/数据。
3. 生效配置（`config/providers.json` 与 `.env` gitignored；`config/tts.json` 已进 voice checkpoint）：
   - `config/providers.json`：tagger 跑 `anthropic/claude-haiku-4.5`（provider 条目已正名为 `"tagger"`）。
   - `config/tts.json`：`fish_audio.model = s2.1-pro`，当前音色 `35d2396e569d4513883ecd23c05eabf7`（用户 2026-06-28 手动切换）。
   - `.env`：`CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`（第六十九轮 A/B 胜出项）。
4. `normalize=false` 已进入 Pipecat 真实多轮链路，用户听感「还可以」；发平/句间呼吸的最终优化延后与音色和其他参数一起评估，不继续单点追节奏标签。
5. 本轮发现单字尾音自回声：Boxi「先睡，乖。」→ ASR「乖。」→ Boxi 再回复。已做窄修复：仅在停止播放后 2s 内拦截与尾字完全一致的单字。真机已生成单字回复「一」，本次未被 ASR 回收且未自触发；直接拦截命中待自然复现时观察。
6. 第七十三轮稳定化后已重新跑通：后端全量 **745 passed**、invariant **366 passed**、前端 `tsc --noEmit` 通过、`git diff --check` 通过。
7. Codex 已配置 Fish 官方 agent tooling（全局，不在仓库 commit 内）：Fish Docs MCP + `fish-audio-api`/`fish-audio-sdk` skills。新会话可能需要重启后才热加载。
8. 标签器/翻译共用的 OpenRouter provider 已从误导性的 `"gemini"` 正名为 `"tagger"`；实际模型仍是 Haiku。新环境变量为 `OPENROUTER_TAGGER_API_KEY`，但注册层会自动兼容旧 `OPENROUTER_GEMINI_API_KEY`，本机无需立即迁移。
9. B 类位置的真正杠杆是移除 tagger prompt 的动态 mood 注入：已写完的正文是唯一情绪来源。neutral-mood A/B 两轮 10/10 不再提前染色，`position_v5` **已由用户听感验收通过，决定保留**。
10. **语音微调与 dirty 分轨均已结案**，下一会话不要继续追加 tagger/Fish 规则。下一步进入产品体验整合；日常使用中被动观察单字自回声即可。

---

## 第六十七轮已完成（2026-06-26，**已 commit `08bf0ec` + `0d51acb`**）

### ✅ 代码：Rule 3 重写 + 跨句去重护栏

**方向一 · Rule 3 重写（Haiku-friendly 明确判断协议）**
- `TAGGER_INSTRUCTION_TEMPLATE` Rule 3：从「软倾向不加」→「默认不加；仅条件 A（情绪切换）或 B（开头突出）才加」。
- 两条 `禁止` 针对 Haiku 常见违规：按句机械分配 / 循环轮换不同标签制造多样感。
- 测试：`"逐句重新判断"` → `"每句话默认不加标签"`。

**方向二 · `suppress_repeated_leading_tags`**
- 新函数 + `_SOUND_EFFECT_TAG_INNERS` / `_DEDUP_EXEMPT_TAG_INNERS`（`expression_tagger.py`）。
- 连续两句句首非 exempt 标签完全相同 → 删后一句（延续基调，非新切换）；无标签句重置基线。
- 接入 `apply_expression_tags`（全文路径）+ `main.py` `_tag_reply_by_sentence`（逐句 join 后）。
- +10 单测（`test_expression_tagger_guards.py`），tagger 相关 **69 pytest 全绿**。

**已修改文件（`08bf0ec`）**
- `backend/app/tts/expression_tagger.py`
- `backend/app/main.py`
- `backend/tests/test_expression_tagger.py`
- `backend/tests/test_expression_tagger_guards.py`

### ✅ 量化验证（同轮 Cursor session，`experiments/tagger_ab.py` N=3）

脚本走**生产逐句路径** + join 后 `suppress_repeated_leading_tags`（本地 untracked 版已改好，未 commit）。

| 模型 | 场景 | 改前基线 | 改后（含护栏） |
|------|------|----------|----------------|
| **Haiku** | long_story | ~1.00 | **0.67** |
| **Haiku** | short_chat | ~1.00 | **0.56** |
| Gemini | long_story | 0.43 | **0.43**（无回归） |
| Gemini | short_chat | 0.11–0.33 | **0.33–0.44** |

**结论**：Haiku 密度从「几乎句句贴」降到「约 2/3 句有标签」，主目标达成；Gemini 未退化。

**同轮 `tagger_eval.py`（全文路径，4 fixture，Haiku）**

| Fixture | 标签 | tagged_sent | 评价 |
|---------|------|-------------|------|
| 01 揶揄+想念 | `[sarcastic]` + `[nostalgic]` | 2/4 | 转折处分贴，好 |
| 02 冷淡失落 | `[lonely]` 仅句首 | 1/4 | opening_only，略平 |
| 03 得意挖苦 | `[smug]` 仅句首 | 1/3 | opening_only，可接受 |
| 04 揶揄→心软 | `[soft tone]` 在「不过」前 | 1/4 | 转折点句中插入，好 |

### ✅ Fish 文档对照 + 密度/位置/语义分析（同轮讨论，无新代码）

对照 [Fish Emotion Control](https://docs.fish.audio/developer-guide/core-features/emotions) +
`docs/FISH_AUDIO_REFERENCE.md` §3–4，结论摘要：

**密度**
- Fish：「space out emotional changes」「短文本别滥用」「一句最多一种情绪（不是每句都必须有标签）」。
- **不是过少**：长故事 0.67、短对话 0.25–0.56，已从过密回到合理区间。
- **长叙事略密于 Fish 理想（~0.35–0.50）**，但可接受；短对话偏克制，符合官方「短文本别滥用」。

**位置准确度（中等偏上）**
- **做得好**：情绪转折点句中插入（04 `[soft tone]`、01 后半 `[nostalgic]`）；break 冗余/悬空标签有代码护栏。
- **仍偏弱**：B 类常偷懒贴句首（整句染色，精度不如句中贴）；`opening_only`（02/03 仅开头一标）。
- **未做**：task 2 的 P2（词中插 `那[sighing]股`）/ P3（无意义句首堆叠）守卫。

**语义对齐 & A/B 类标签用法**
- **Haiku（当前生产）**：B 类情绪跟情节走（`[nostalgic]`/`[sad]`/`[relieved]`），A 类滥用少（task 3 prompt 仍有效）。
- **Gemini**：密度优，但 A 类语义错（`[sighing]`/`[panting]` 贴拟声「扑通」）、生造标签（`[heartbeat]`、`[wistful]`）、脏标签（`[beklagende]`）。
- **架构边界不变**：代码只强制格式/明显非法位置；**情绪恰当性 & A/B 类选对**靠 LLM，`_preserves_original_wording` 会在改字插标时整句放弃标签。

**架构决策（仍有效）**：禁止用代码硬删 `[sighing]` 等语义判断——见 TASK_QUEUE task 3 结案记录。

### ✅ 运维：前后端已重启供真机检测

- 后端：`http://127.0.0.1:8000`（`bash scripts/dev_backend.sh`）
- 前端：`http://127.0.0.1:5173`（`npm run dev --workspace frontend`）
- 用户开新 session 前若服务已停，重新 `npm run dev:backend` + `npm run dev:frontend`。

---

## 第六十八轮补充（2026-06-26，**未 commit，仅更新 HANDOFF + Codex 全局配置**）

### ✅ 用户真机听感结论已记录

- 当前标签密度/稳定性：**较为稳定**，不再是第六十七轮前那种「几乎句句贴」的主问题。
- 主要听感问题：**稍微发平**，重点像是**语句之间停顿不足、没有顿挫感**。
- 方向判断：下一步不应全局加密度，也不应回退到句句贴；主线应切到 Fish TTS 的**节奏/韵律控制**。

### ✅ Fish 文档复核后的新调优线索

只读 `docs/FISH_AUDIO_REFERENCE.md`、`docs/PIPECAT_REFERENCE.md`、`docs/PIPECAT_AUDIT.md` 与当前 Fish/Pipecat 装配，结论：

1. **节奏标签疑似需要 A/B**
   Fish S2-Pro 文档里的节奏类标签是 `[pause]` / `[short pause]` / `[long pause]`，但当前标签器 prompt 和守卫用的是 `[break]` / `[long-break]`。历史上 `[break]` 似乎有过效果，不能直接断言是 bug；但这正贴合「句间没顿挫」症状，应优先固定文本 A/B。
2. **Pipecat 语音路径没有显式传 Fish 表达参数**
   `backend/realtime/run_voice.py` 当前只传 `voice` / `model` / `latency=balanced`。Pipecat `FishAudioTTSService.Settings` 支持 `normalize`、`temperature`、`top_p`、`prosody_speed`、`prosody_volume`，但语音路径未显式设置。
3. **文字路径和语音路径配置不一致**
   `backend/app/tts/fish_audio.py` 已传 `temperature/top_p`，并设置 `prosody.normalize_loudness=false`；Pipecat 语音路径仍走默认 `normalize=True`，可能压平 whisper/shouting 等动态。
4. **`latency=normal` 仍不要碰**
   项目已真机确认 normal 在 Pipecat 多轮会失声，且首字节约 3.5s；继续锁 `balanced` 是当前正确取舍。

### ✅ Codex 侧 Fish 官方 agent tooling 已配置

根据 Fish 官方博客 `llms.txt + MCP + Agent Skills`：

- 已在 `/Users/xiaoiwawang/.codex/config.toml` 追加全局 MCP：
  - `[mcp_servers.fish_audio]`
  - `url = "https://docs.fish.audio/mcp"`
  - 备份：`/Users/xiaoiwawang/.codex/config.toml.bak-fish-audio-mcp`
- 已安装 Codex 全局 skills：
  - `/Users/xiaoiwawang/.agents/skills/fish-audio-api`
  - `/Users/xiaoiwawang/.agents/skills/fish-audio-sdk`
- 当前会话可能不会热加载；新 Codex 会话应可发现。以后 Fish API/SDK 代码生成优先用 skill，开放式/最新文档问题优先查 MCP。

---

## 第六十九轮补充（2026-06-27，**未 commit，Fish 节奏/参数 A/B**）

### ✅ 固定文本节奏标签 A/B 已做，结论：不要迁移词表

新增 `experiments/fish_rhythm_ab.py`，真实 Fish HTTP 生成固定文本 A/B：

- 输出目录：`data/fish_rhythm_ab/s21-pro-free/`
- 比较：无标签 / `[break]` / `[long-break]` / `[pause]` / `[short pause]` / `[long pause]`
- 用户听感：**区别不是很大**
- 决策：**暂不把生产 prompt/guard 从 `[break]` 系迁移到 `[pause]` 系**；节奏标签词表不是当前主矛盾。

### ✅ Fish 参数 A/B 已做，结论：只关 normalize

同一脚本生成 `pause` 固定文本参数 A/B：

- `pipecat_default_norm_true`（近似 Pipecat 默认 `normalize=True`）
- `normalize_false`
- `normalize_false_speed_094`
- `normalize_false_speed_094_temp_08`

用户听感：

- **`normalize=false` 最正常**
- 其他三组句间呼吸略别扭

已改：

- `.env` 增加 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`
- `backend/realtime/run_voice.py` 已支持可选 Fish Settings：`normalize` / `temperature` / `top_p` / `prosody_speed` / `prosody_volume`
- `.env.example` 标注当前推荐：只关 normalize；降速/升温仅作为后续实验项
- 测试：`pytest backend/tests/test_voice_config.py backend/tests/test_fish_audio_pipecat_tts.py` → 11 passed

下一步：**跑 Pipecat 真机语音链路验证 `normalize=false` 是否也改善真实对话**。不要同时开 `prosody_speed=0.94` 或 `temperature=0.8`。

### ✅ 模型版本 A/B 样本已生成（S2.1 Pro paid vs free vs S2.0/S2-Pro）

用户多轮真机怀疑问题可能来自 `s2.1-pro-free`。按 Fish 文档/API 语义确认：

- S2.1 Pro paid：`model` header 用 `s2.1-pro`
- S2.1 Pro Free：`s2.1-pro-free`
- 上一代 S2 / S2.0：`s2-pro`

新增 `experiments/fish_model_ab.py`，只做离线 HTTP `/v1/tts` 样本，不改生产配置。

生成参数：

- voice：嘉岚 `fbe02f8306fc4d3d915e9871722a39d5`
- models：`s2.1-pro` vs `s2.1-pro-free` vs `s2-pro`
- fixtures：5 条不同情绪（teasing / soft / angry / excited / lonely）
- `format=mp3`
- `latency=balanced`（贴近当前 Pipecat 真实链路）
- `temperature=0.7`
- `top_p=0.7`
- `prosody.normalize_loudness=false`

输出：

- `data/fish_model_ab/s2.1-pro/*.mp3`
- `data/fish_model_ab/s2.1-pro-free/*.mp3`
- `data/fish_model_ab/s2-pro/*.mp3`
- `data/fish_model_ab/manifest.json`

下一步：用户人工横向听同名文件（如三组 `01_teasing.mp3`），判断 paid S2.1 Pro 是否明显优于 Free，或 `s2-pro` 是否更自然。

用户听后三组结论：**`s2.1-pro-free` 明显过于粗糙，当前 `s2.1-pro` 最好**。已把本地 `config/tts.json`
切到 `s2.1-pro`；Pipecat 构造验证为 `model=s2.1-pro`、`latency=balanced`、`normalize=False`。

### ✅ Paid S2.1 Pro 上已重做停顿/normalize 样本

因为前一轮 `[break]`/`[pause]` 和 `normalize=false/true` 判断基于 `s2.1-pro-free`，用户要求在 paid
`s2.1-pro` 上重测。已用同一固定文本、同一嘉岚音色、同一参数生成：

- `data/fish_rhythm_ab/s21-pro/rhythm_norm_false/*.mp3`
- `data/fish_rhythm_ab/s21-pro/rhythm_norm_true/*.mp3`

每组 6 条：`none` / `break` / `long_break` / `short_pause` / `pause` / `long_pause`。

用户听感结论：

- 停顿/顿挫：各标签**没什么区别**，不要因为这轮去大改节奏词表。
- `normalize=false`：比 `true` **稍微好一点**，当前 `.env` 保留 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`。
- 奇怪现象：两组里 `long_pause` 的**音质**都更好一些，但这不像是“停顿/顿挫”改善，更可能是 Fish 生成随机性、
  分段/采样路径变化，或 `[long pause]` 对整句韵律的副作用。**不要直接把所有停顿迁移成 `[long pause]`**；
  若要利用它，需再做多次重复样本确认稳定性。

### ✅ B 类标签位置 prompt 精修已做

用户决定不再围绕停顿标签打转，转向 B 类标签位置精修。已修改
`backend/app/tts/expression_tagger.py` 的 `TAGGER_INSTRUCTION_TEMPLATE`：

- 强化语气/情绪/音调类标签不要偷懒全放句首。
- 优先贴在情绪真正开始的位置，尤其是转折词或情绪起点前：如「不过」「但是」「其实」「只是」「偏偏」
  「突然」「后来」「那一刻」。
- 只有整句从第一个字开始就是同一种明确情绪时，才句首贴。
- 新增正反例：
  - `我嘴上嫌你烦，[soft tone]不过还是给你留了灯。`
  - `我今天去了那家店，[sad]后来才发现你不在。`

边界：这次**没有**新增代码语义 guard。B 类标签位置属于语义判断，仍交给 tagger LLM；代码只做格式/明显非法位置护栏。

测试：`pytest backend/tests/test_expression_tagger.py backend/tests/test_expression_tagger_guards.py backend/tests/test_main_tag_reply_by_sentence.py`
→ 76 passed。

### ✅ B 类位置精修听感样本已生成

新增 `experiments/tagger_position_listen.py`，用真实 tagger（当前 `"gemini"` provider 实际 Haiku）+
paid `s2.1-pro` + 嘉岚 + `latency=balanced` + `normalize_loudness=false` 生成 5 条位置专项样本：

- 输出：`data/tagger_position_listen/s2.1-pro/*.mp3`
- manifest：`data/tagger_position_listen/s2.1-pro/manifest.json`

样本专门设计成「前文中性 → 当前句中途转情绪」，用来听 B 类标签是否贴在转折/情绪起点：

- `01_tease_to_soft`：成功贴到 `[soft tone]不过`
- `03_dry_to_sarcastic`：成功贴到 `[disdainful]其实`
- `02_neutral_to_sad`：仍偏句首 `[sad]我本来只是想随便看看...`，没贴到「后来」
- `04_calm_to_worried`：过早贴 `[worried]水也喝一口`，且第二句又贴 worried
- `05_story_to_nostalgic`：opening-only / 重复 `[nostalgic]`

初步观察：prompt 精修有作用，但 Haiku 仍不稳定；下一步以用户听感为准。若仍不满意，可能要继续 prompt 收紧
「不要提前染中性铺垫」，或改 tagger 策略，而不是继续调 TTS。

### ⚠️ 已撤销：`[sad]` / `[worried]` high-risk guard

曾短暂尝试把 `[sad]` / `[worried]` 强制替换成 `[low voice]` / `[soft tone]`，但用户复听后判断：

- 02 / 04 的主要问题是**位置**，不是 `[sad]` / `[worried]` 标签本身。
- 不需要替换 `[sad]` / `[worried]`。
- 也不要在 prompt 里保留“谨慎使用”提醒。

因此已撤销：

- `_normalize_high_risk_tone_tags()` 删除。
- `[sad]` / `[worried]` 保留在基础情绪词表。
- prompt 不再提示它们是 high-risk。
- 相关测试断言已恢复。

保留结论：下一步继续处理 B 类标签**位置**，不要用代码硬替换情绪标签。

---

## 第七十轮补充（2026-06-27，**未 commit，Pipecat 真机 + 单字自回声修复**）

### ✅ `normalize=false` 真实链路已验证

- 启动日志确认：`Fish TTS explicit settings: {'normalize': False}`。
- 真机多轮完成 STT → soul → 逐句 tagger → Fish TTS；一轮 `user-stopped→first-audio = 2.576s`。
- 用户听感：「还可以」；发平和句间呼吸暂不继续单点调参，最后与换音色/其他设置统一评估。
- 继续保留 `s2.1-pro + latency=balanced + normalize=false`；不开 `prosody_speed=0.94` / `temperature=0.8`，不迁移 `[pause]` 词表。

### ✅ 单字尾音自回声已做窄修复

真机时 Boxi 上轮末句是「先睡，乖。」，播放尾音被 ASR 识别成新的用户 final「乖。」，
触发 Boxi 再回复「嗯，这就乖了。」。根因是现有 `is_self_echo` 故意保留单字用户回复，
`min_chars=2` 让单字尾音漏过。

修复：

- 保留通用匹配器 `min_chars=2`，不全局吞掉「嗯」/「好」这类真实单字接话。
- `SelfEchoGate` 新增 2s 窄窗口：只有用户 final 正好等于 Boxi 尾字时才拦截，且不做模糊单字匹配。
- +3 回归测试：1.5s 内「乖」被拦截；2.1s 后「乖」保留；窗口内无关「好」保留。
- 测试：21 passed。真机又运行三轮，Boxi 实际生成单字回复「一」；本次扬声器尾音没有被 ASR 回收，因此未直接命中 `self-echo suppressed`，但也未自触发下一轮。随后真实用户输入正常通过。

---

## 第七十一轮补充（2026-06-27，**未 commit，标签器 provider 正名**）

### ✅ `gemini` 别名已改为模型无关的 `tagger`

- `DEFAULT_TAGGER_PROVIDER` 和共用翻译 provider 的默认名统一为 `"tagger"`。
- `config/providers.example.json` 及本机 `config/providers.json` 已改用 `"tagger"`；本机模型仍是 `anthropic/claude-haiku-4.5`。
- 新环境变量名为 `OPENROUTER_TAGGER_API_KEY`。注册层优先用新名，新名缺失时自动回退到旧 `OPENROUTER_GEMINI_API_KEY`；旧 `"gemini"` provider key 也保留为配置兼容别名。
- 本机按 dev backend 的 `.env` 加载方式验证：`tagger` 可解析且旧密钥兼容生效，未打印密钥。
- 测试：相关切片 67 + 54 passed；后端全量 744 passed；前端 `tsc --noEmit` 通过；`git diff --check` 通过。

---

## 第七十二轮补充（2026-06-27，**未 commit，B 类位置 prompt + 真实样本**）

### ✅ 根因坐实：动态 mood 注入在二次创作情绪

- `position_v2` 坐实旧问题：04 提前把中性「水也喝一口」染成 worried，05 在景物铺垫和「那一刻」重复 nostalgic。
- 继续叠具体示例的 `position_v3/v4` 不稳定：Haiku 会模仿示例吞掉前缀，或仍然被 mood 拉回句首。因此撤掉过拟合的长示例，不再继续叠 prompt。
- A/B：同样 5 个 fixture，只把 mood 设为 neutral，两轮共 10/10 条都没有提前染中性铺垫，情绪点稳定落在正文证据附近。
- 生产改动：移除 `TAGGER_INSTRUCTION_TEMPLATE` 的动态 `mood_block`。`mood` 参数暂保留在函数契约中保持调用兼容，但不再进 prompt；已写完的 Boxi 正文是 tagger 的唯一情绪来源。
- 实验脚本新增 `--label` 可重复选项，可只重生成单个 fixture，避免重复付费调其他样本。
- 最终 `position_v5` 五条全部正确：01 `[soft tone]不过`；02 在「那里安静得有点过分」前；03 `[sarcastic]其实`；04 在「我有点担心」前；05 `[nostalgic]那一刻`。
- 样本：`data/tagger_position_listen/s2.1-pro/position_v5/`，当前 Haiku tagger + paid `s2.1-pro` + `normalize_loudness=false`。
- 测试：相关 92 passed；后端全量 745 passed；`git diff --check` 通过。

### ✅ 用户听感验收通过

2026-06-27，用户听完 `position_v5` 并明确决定保留。B 类位置精修正式结案；不再重开动态 mood 注入、high-risk 替换或节奏词表迁移。

---

## 当前项目目标

赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标

**Fish/TTS/tagger 微调与工程稳定化均已结案。语音改动已在独立分支形成四个可审查实现 checkpoint，下一步转入产品体验。**
文字路径逐句化（P0+P1）已在 `111c70c` 落地并真机验证。

---

## 已知 bug / 风险

- **~~Haiku 密度过高~~ → 已大幅改善**：`tagger_ab` N=3 证实 long_story 1.00→0.67；用户真机反馈当前较稳定。
- **当前听感偏平**：主要像语句之间停顿/顿挫不足，不是标签数量不足。
- **节奏标签词表 A/B 差异不大**：当前 prompt/guard 仍保留 `[break]` / `[long-break]`，不要仅凭文档迁移到 `[pause]` 系。
- **Pipecat Fish 参数已暴露，A/B 胜出项是 `normalize=false`**：本地 `.env` 已设置；降速/升温听感别扭，先不要启用。
- **~~标签器 provider 命名债~~ → 已完成**：默认 key 已改为 `"tagger"`，并保留旧 key/env 兼容。
- **位置精度**：B 类句首粗放、opening_only；A 类一旦出现容错极低——真机重点听。
- **Gemini A 类语义错**：若回退 Gemini 换密度，会重新引入音效标签误用。
- **改字护栏副作用**：Haiku 试图给「扑通」插 `[扑通]` 类标签时被拒绝 → 该句无标签（正确降级，但丢表达）。
- Fish 账号 Free 套餐锁住克隆/Voice Design（不阻塞）。
- **自回声残余**：本轮已补单字干净尾音；ASR 增字/误听成非干净后缀仍是内容匹配器的固有边界，真治仍是未来 WebRTC/AEC。
- 沿用：P12、P9-P2-C、P9-D、日语音色未接后端、Fish WS 空闲断连。

---

## 当前未完成

### 🟡 单字自回声后续观察

代码和确定性回归已完成；真机生成单字回复时未重现回声，暂不为了制造回声继续消耗云调用。

推荐最小顺序：

1. 下次日常真机对话若再出现尾字回收，确认日志出现 `self-echo suppressed`，并且没有新的 `Boxi decision=reply`。
2. 若仍自触发，记录 ASR final 文字和相对 `BotStopped` 时间；不盲目继续放宽单字匹配。

### ✅ 位置精修（用户听感 PASS，结案）

- Prompt 保留抽象证据规则：中性铺垫不贴标签，后文情绪不得倒灌。
- 动态 mood 不再注入 tagger；正文是唯一情绪来源。
- `position_v5` 已由用户听感验收并决定保留。
- 代码守卫（未做）：P2 词中插、P3 无意义句首堆叠（task 2 遗留，真机未复现故降级过）。

### 🟢 Fish 音色克隆/设计（等用户升级 Plus）

详见 memory `fish-voice-creation-plan`。当前维持嘉岚。

### 沿用未完成项

task 4 非干净后缀自回声/AEC、P12、P9-P2-C、P9-D、日语音色切换。

---

## 历史背景（第六十五轮 `111c70c`，摘要）

- P0/P1：文字路径标签器逐句化 + 并发，单句失败不再整段作废。
- 模型 A/B：Haiku 情绪准 / Gemini 密度优；MiniMax-M3 出局。
- task 3（第六十三轮 `70d5c7a`）：A/B 类音效 vs 语气 prompt 修正，`[sighing]` 滥用从 6+/轮 降到 ~1–2/20 句。
- 嘉岚音色无问题；长叙事听感差根因是密度过高（本轮已量化改善）。
- Fish 克隆/Voice Design 需 Plus，用户暂不升级。

---

## 下一步只需读取（按任务挑）

- **永远先读**：本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **节奏/韵律 A/B**：`docs/FISH_AUDIO_REFERENCE.md` §2/4/7/9 + `docs/PIPECAT_REFERENCE.md` §4/8 +
  `docs/PIPECAT_AUDIT.md` B 项 + `backend/realtime/run_voice.py` + `backend/app/tts/fish_audio.py` +
  `backend/app/tts/expression_tagger.py`（节奏词表/guard）。
- **checkpoint 状态**：`docs/SOUL_RUNTIME_STATUS.md` + `git status`；确认只剩 `_LatencySpikeLogger` 与明确排除的本地实验/数据。

## 下一步不要读取

- ❌ `docs/SESSION_LOG.md`
- ❌ `reference/`（Pipecat/Fish 文档线已结；Fish 查 `docs/FISH_AUDIO_REFERENCE.md` 或 MCP）
- ❌ `experiments/` 废弃 spike（**除外**：`tagger_ab.py`、`tagger_listen_haiku.py`、`voice_compare.py`）
- ❌ 不要重开：P0/P1 逐句化、嘉岚音色问题、MiniMax-M3、Fish 会员门槛、第六十七轮密度代码（已 commit）
- ❌ 全仓库扫描

## 推荐下一个最小任务

1. 转入产品体验：优先低 GPU、asset-based 视觉存在感与端到端日常使用，不再继续微调 TTS。
2. 日常真机若再次出现尾字回收，只记录 ASR final 与 `BotStopped` 相对时间；不要主动制造回声或扩大匹配。
3. `_LatencySpikeLogger`、音频数据、实验脚本与 agent/MCP 工具配置继续保持本地未提交。

---

> **给新 session**：`/clear` 后只读 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
> 用户真机听感结论已记录：`normalize=false` 真实链路「还可以」；`position_v5` 已验收保留。下一步进入产品体验，单字尾音自回声仅随日常使用观察。
