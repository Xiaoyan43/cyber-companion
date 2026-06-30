"""P0-OSS-4 transport spike — minimal mic -> SmallWebRTCTransport -> speaker loopback.

Standalone and isolated from the production voice pipeline (run_voice.py /
pipeline_router.py / companion_brain*.py). Does not import or modify them.
Purpose: validate SmallWebRTCTransport end-to-end and produce an
accept/reject input for the transport-swap candidate in docs/TASK_QUEUE.md
(P0-OSS-4 "Transport 换血"). No STT/brain/TTS attached — pure audio passthrough.

Run:
    .venv/bin/python backend/realtime/spike_webrtc_loopback.py
Then open spike_webrtc_client.html in a browser (see that file's header for
how to serve it) and click "Connect". Speak into the mic and listen to your
own voice loop back through the speakers — that's the perceptual layer
(does it feel real-time, does echoCancellation kill the echo from an
external speaker).

Precise layer (this script's job): a ping/pong over the WebRTC data channel,
round-trip-timed by the browser with performance.now() and shown on the
page. That number is a genuine end-to-end measurement over the real
connection. A second, much smaller number is logged here in the terminal —
the time our own passthrough processor takes to convert an InputAudioRawFrame
into an OutputAudioRawFrame. That second number is NOT an end-to-end latency
(it excludes browser capture/playback and the aiortc/network leg) — it only
confirms our code isn't adding meaningful overhead of its own.
"""

import time
from collections import deque

from loguru import logger

from pipecat.frames.frames import InputAudioRawFrame, OutputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

_LOG_EVERY_N_FRAMES = 100
_SAMPLE_RATE = 16000


class LoopbackProbe(FrameProcessor):
    """Converts mic input frames to speaker output frames and times the hop."""

    def __init__(self):
        super().__init__()
        self._samples: deque[float] = deque(maxlen=500)
        self._count = 0

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if not isinstance(frame, InputAudioRawFrame):
            await self.push_frame(frame, direction)
            return

        started = time.monotonic()
        out = OutputAudioRawFrame(
            audio=frame.audio,
            sample_rate=frame.sample_rate,
            num_channels=frame.num_channels,
        )
        self._samples.append((time.monotonic() - started) * 1000)
        self._count += 1
        if self._count % _LOG_EVERY_N_FRAMES == 0:
            self._log_stats()
        await self.push_frame(out, FrameDirection.DOWNSTREAM)

    def _log_stats(self):
        samples = list(self._samples)
        if not samples:
            return
        avg = sum(samples) / len(samples)
        logger.info(
            f"[spike-loopback] frames={self._count} processor-hop avg={avg:.3f}ms "
            f"min={min(samples):.3f}ms max={max(samples):.3f}ms "
            "(NOT end-to-end — see file header; real RTT is the data-channel "
            "ping/pong shown on the client page)"
        )


async def bot(runner_args: RunnerArguments):
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        raise RuntimeError(
            "spike_webrtc_loopback only supports the webrtc transport "
            "(run with: python spike_webrtc_loopback.py -t webrtc)"
        )

    webrtc_connection = runner_args.webrtc_connection

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=_SAMPLE_RATE,
            audio_out_sample_rate=_SAMPLE_RATE,
        ),
    )

    probe = LoopbackProbe()
    pipeline = Pipeline([transport.input(), probe, transport.output()])
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=False))

    @transport.event_handler("on_client_connected")
    async def on_connected(_transport, _client):
        logger.info("[spike] client connected — loopback active, speak and listen")

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(_transport, _client):
        logger.info("[spike] client disconnected")
        await task.cancel()

    @transport.event_handler("on_app_message")
    async def on_app_message(_transport, message, _sender):
        # Data-channel ping/pong: the precise, genuine end-to-end RTT layer.
        # The browser stamps t0 with performance.now() and computes RTT itself
        # on reply; we just echo the same payload straight back.
        if isinstance(message, dict) and message.get("type") == "ping":
            webrtc_connection.send_app_message({"type": "pong", "t0": message.get("t0")})

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
