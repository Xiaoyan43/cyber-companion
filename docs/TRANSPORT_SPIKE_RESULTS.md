# P0-OSS-4 Transport Spike 结果（2026-06-30）

对应 `docs/TASK_QUEUE.md` P0-OSS-4「Transport 换血」三阶段计划的第一阶段：
`LocalAudioTransport` → `SmallWebRTCTransport` 的最小 loopback 验证（不含 STT/brain/TTS,纯音频passthrough + 数据通道 ping/pong）。

## 测试方法

- 后端：`.venv/bin/python backend/realtime/spike_webrtc_loopback.py -t webrtc`（默认监听
  `http://localhost:7860`)。
- 客户端：`backend/realtime/spike_webrtc_client.html` 需用 HTTP 服务器打开（`file://` 在现代
  Chrome 下 `navigator.mediaDevices` 为 `undefined`,不是安全上下文,无法 `getUserMedia`）。
  本次用 `python3 -m http.server` serve。
- 精细量化层：浏览器端 `performance.now()` 对数据通道 ping/pong 计时,真实端到端 RTT。
- 人工判断层：对外接音箱说话/拍手,听回放延迟感、回声是否被压住。

## 排查过程中发现并修复的环境/脚本问题

1. **macOS 防火墙**：`.venv` 实际运行的二进制是
   `.../Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python`（非
   `/usr/bin/python3`),未在防火墙允许列表,导致 ICE 连接卡在 `checking` 状态直至 60s 超时。
   已加入 `socketfilterfw` 允许列表。
2. **`spike_webrtc_client.html` non-trickle ICE bug**（已修复,见该文件 diff）：原代码
   `setLocalDescription` 后立即把 `offer.sdp` POST 给后端,没等 ICE candidate 收集完成,导致
   SDP 里没有候选地址。修复：等待 `pc.iceGatheringState === "complete"` 后再发送
   `pc.localDescription.sdp`。
3. 调试时发现：不能用 `exec()` 之类的非标准方式跑这个脚本——pipecat `runner.run.main()`
   依赖标准 module 调用栈反射定位 `bot` 函数,`exec` 包装会导致
   `Could not find 'bot' function`,连接看似建立但 `on_client_connected`/app-message 都不会
   正常触发。正常的 `python backend/realtime/spike_webrtc_loopback.py -t webrtc` 调用方式没有
   这个问题。

## 实测数据

- 数据通道 RTT（本机 loopback,n=89）：avg **2.8ms**,min 1.4ms,max 21.2ms。
- 主观听感：延迟感正常；对外接音箱说话/拍手,回放声音干净,无重复/嗡鸣——`echoCancellation:
  true` 的回声压制有效。

## 结论：Accept

`SmallWebRTCTransport` 端到端可用,RTT 和回声压制都达标,可以进入 P0-OSS-4 的第二阶段（生产
迁移）评估。本 spike 本身是独立 throwaway 脚本,不影响生产语音管线
（`run_voice.py`/`pipeline_router.py`/`companion_brain*.py` 均未改动）。

下一步（生产迁移阶段）需要单独评估的点：迁移后 `half_duplex_mute_processor.py` +
`self_echo_filter.py` 两个 hack 能否删除、`voice-ui-kit` 组件接入范围、是否需要为非 localhost
场景（真机/远程）配置 TURN/STUN。

## 第二阶段：真实多轮管线 transport 切换（2026-06-30）

对应 P0-OSS-4「Transport 换血」第二阶段：把完整 STT→half-duplex hack→brain→self-echo
hack→tagger→TTS 真实管线接到 `SmallWebRTCTransport`，而非纯 loopback。新建独立 throwaway
脚本 `backend/realtime/spike_webrtc_pipeline.py`（不修改 `run_voice.py`/`pipeline_router.py`/
两个 hack 源文件），复用 `run_voice.py` 现成的 STT/TTS 构建函数，管线组装顺序与生产
`_main_pipeline()` 完全一致，唯一替换点是 transport。

### 实验 A：两个 hack 保持默认开启（与生产配置一致）

- 真机多轮对话正常：STT 识别、brain 回复、TTS 播放均正常，无新增异常。
- 打断不了 Boxi——但日志确认这是 `HalfDuplexMuteProcessor` 按设计在 Boxi 说话时静音麦克风
  （`Half-duplex: user muted (bot speaking)`），跟生产 `LocalAudioTransport` 路径**行为一致**，
  不是这次换 transport 引入的新问题。
- **结论：行为与生产路径一致，无回归。**

### 实验 B：临时关闭两个 hack（`CYBER_COMPANION_VOICE_HALF_DUPLEX=0`，未改 `.env`，仅本次进程环境变量；
`self_echo_enabled = half_duplex and load_self_echo_enabled()` 联动自动关闭），纯靠浏览器原生 AEC

- 真机多轮对话（外接音箱，未戴耳机）**全程无自问自答/回声**——验证了浏览器原生 AEC 在真实多轮
  场景下确实能顶替这两个 hack 的回声压制功能，不止 phase-1 loopback 那种简单场景。
- **仍然打断不了 Boxi**：日志坐实根因——`SileroVADProcessor`+STT 在 Boxi 说话期间持续正常工作
  （能看到用户说话的 partial transcript 在 bot 说话窗口内被实时识别出来），但用户的话只是被
  排进下一轮、等 Boxi 自然说完才处理，管线没有触发任何"打断/取消当前 TTS"的信号。
- **根因与 transport 无关**：跟 `docs/TASK_QUEUE.md` 已记录的 smart-turn 挂不上的根因同源——
  `CompanionBrainProcessor` 绕开了标准 `LLMUserAggregator`，没有"用户开始说话→发
  interruption frame→取消 TTS"的标准信号链。`PipelineParams(allow_interruptions=True)` 本身
  不会自动生效，需要管线显式支持。

### 第二阶段总结

- **回声压制可以删 hack**：换 transport 后浏览器原生 AEC 在真实多轮场景下有效，
  `half_duplex_mute_processor.py` + `self_echo_filter.py` 两个 hack 理论上可删除（仅针对它们
  解决回声的功能而言）。
- **打断/barge-in 不能靠换 transport 解决**：这是独立的管线重构任务（需要给
  `CompanionBrainProcessor` 接上标准中断信号链或等价机制），跟 transport 选型正交，不要把它
  算作"换 transport 顺带解决"的收益。
- **基本功能（识别/回复/播放）在真实多轮场景下无退化。**
