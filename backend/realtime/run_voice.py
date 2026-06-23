"""Standalone Pipecat voice loop — mic → VAD → STT → Companion Brain → TTS → speaker.

Run: ``python -m backend.realtime.run_voice`` (see ``backend/realtime/README.md``).
Not part of the V1 HTTP gate; soul wiring is V2 Phase 3.

``CYBER_COMPANION_VOICE_MODE=realtime`` swaps the STT+brain+TTS chain for Doubao Dialog
S2S (OutputMode 0). Default ``pipeline`` keeps the existing path.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Intel-mac OpenBLAS can SIGFPE inside its multithreaded GEMM when numpy's LAPACK
# (pulled in transitively by faster-whisper / VAD / audio resampling, and run from
# Pipecat worker threads via asyncio.to_thread) is exercised concurrently. Serialize
# BLAS *before* numpy is first imported in this process. Harmless on Apple Silicon.
for _blas_threads_var in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_blas_threads_var, "1")

from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level=os.getenv("CYBER_COMPANION_VOICE_LOG_LEVEL", "INFO"))

INPUT_SAMPLE_RATE = 16_000


def _voice_backend(name: str, *, allowed: set[str], default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in allowed:
        raise SystemExit(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return value


def _require_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise SystemExit(f"{key} is not set.")
    return value


def _build_stt(stt_backend: str):
    if stt_backend == "whisper":
        from pipecat.services.whisper.stt import WhisperSTTService

        return WhisperSTTService(
            settings=WhisperSTTService.Settings(model="base"),
            device="cpu",
            compute_type="int8",
        )

    if stt_backend == "doubao_stream":
        from backend.realtime.doubao_streaming_stt_service import DoubaoStreamingSTTService

        _require_env("DOUBAO_API_KEY")
        return DoubaoStreamingSTTService()

    from backend.realtime.doubao_stt_service import DoubaoFlashSTTService

    _require_env("DOUBAO_API_KEY")
    return DoubaoFlashSTTService()


def _build_tts(tts_backend: str) -> tuple[object, int]:
    if tts_backend == "mac_say":
        from backend.realtime.mac_say_tts import MacSayTTSService, SAMPLE_RATE

        return MacSayTTSService(), SAMPLE_RATE

    if tts_backend == "fish_audio":
        import json
        import pathlib

        from pipecat.services.fish.tts import FishAudioTTSService

        api_key = _require_env("FISH_AUDIO_API_KEY")
        reference_id = os.getenv("FISH_AUDIO_REFERENCE_ID", "").strip()
        if not reference_id:
            cfg_path = pathlib.Path(__file__).parent.parent.parent / "config" / "tts.json"
            try:
                reference_id = json.loads(cfg_path.read_text())["providers"]["fish_audio"]["voice"]
            except Exception:
                pass
        if not reference_id:
            raise SystemExit(
                "FISH_AUDIO_REFERENCE_ID env or config/tts.json providers.fish_audio.voice required"
            )

        FISH_SAMPLE_RATE = 44_100
        latency = os.getenv("CYBER_COMPANION_VOICE_TTS_LATENCY", "balanced").strip().lower()
        # Only `balanced` is allowed (P14 Phase 5 P1, A/B verdict 2026-06-23):
        #  - `low`  : undefined passthrough to the Fish server (P0, round 49).
        #  - `normal`: Fish renders the whole clip server-side then sends it in one batch
        #    (measured first-byte ~3.5s vs balanced ~0.5s). This (a) caused the P13 multi-turn
        #    silence — the batch arrives after pipecat's 3.0s stop_frame_timeout_s tears the
        #    audio context down — and (b) means ~3s of dead air before every reply, which kills
        #    presence. Same-sentence A/B confirmed normal's quality edge is marginal, not worth
        #    the cost. Decision: lock `balanced` (true streaming), drop `normal`. Re-evaluate only
        #    if Fish ships a streaming high-quality mode.
        if latency != "balanced":
            raise SystemExit("CYBER_COMPANION_VOICE_TTS_LATENCY must be: balanced")
        svc = FishAudioTTSService(
            api_key=api_key,
            settings=FishAudioTTSService.Settings(
                voice=reference_id,
                model="s2-pro",
                latency=latency,
            ),
            output_format="pcm",
            sample_rate=FISH_SAMPLE_RATE,
        )
        return svc, FISH_SAMPLE_RATE

    from backend.realtime.doubao_streaming_tts_service import DoubaoStreamingTTSService, SAMPLE_RATE

    _require_env("DOUBAO_TTS_API_KEY")
    _require_env("DOUBAO_TTS_VOICE_TYPE")
    return DoubaoStreamingTTSService(), SAMPLE_RATE


async def _main_realtime() -> None:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
    from pipecat.workers.runner import WorkerRunner

    from backend.realtime.doubao_realtime_service import (
        DoubaoRealtimeService,
        INPUT_SAMPLE_RATE as RT_INPUT_RATE,
        OUTPUT_SAMPLE_RATE,
    )
    from backend.realtime.voice_config import (
        ENV_VOICE_MODE,
        ENV_VOICE_OUTPUT_MODE,
        load_voice_mode,
        load_voice_output_mode,
    )

    output_mode = load_voice_output_mode()
    if output_mode != 0:
        raise SystemExit(
            f"{ENV_VOICE_OUTPUT_MODE}=1 (hybrid) is not implemented yet — use 0 for pure S2S."
        )

    _require_env("DOUBAO_RT_APP_ID")
    _require_env("DOUBAO_RT_ACCESS_TOKEN")

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )
    realtime = DoubaoRealtimeService()
    pipeline = Pipeline([transport.input(), realtime, transport.output()])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=RT_INPUT_RATE,
            audio_out_sample_rate=OUTPUT_SAMPLE_RATE,
        ),
    )
    runner = WorkerRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info(
        f"Voice realtime ready (mode={load_voice_mode()}, output_mode={output_mode}) — "
        "Doubao Dialog S2S; cloud VAD + barge-in. Use headphones. Ctrl+C to exit."
    )
    await runner.add_workers(worker)
    await runner.run()


async def _main_pipeline() -> None:
    _require_env("DEEPSEEK_API_KEY")

    stt_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_STT",
        allowed={"whisper", "doubao", "doubao_stream"},
        default="doubao_stream",
    )
    tts_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_TTS",
        allowed={"mac_say", "doubao", "fish_audio"},
        default="fish_audio",
    )

    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
    from pipecat.workers.runner import WorkerRunner

    from backend.app.memory.retrieval import tokenize
    from backend.app.memory.store import get_memory_store
    from backend.realtime.companion_brain import CompanionBrain
    from backend.realtime.companion_brain_processor import CompanionBrainProcessor
    from backend.realtime.half_duplex_mute_processor import HalfDuplexMuteGate, HalfDuplexMuteProcessor
    from backend.realtime.transcript_broadcaster import (
        boxi_transcript_tap,
        get_transcript_broadcaster,
        user_transcript_tap,
    )
    from backend.realtime.vad_processor import SileroVADProcessor
    from backend.realtime.voice_config import (
        ENV_ASR_END_WINDOW_MS,
        ENV_HALF_DUPLEX,
        ENV_MAX_TOKENS,
        ENV_VAD_STOP_SECS,
        load_asr_end_window_ms,
        load_half_duplex_enabled,
        load_vad_stop_secs,
        load_voice_max_tokens,
    )

    tokenize("预热")

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    stt = _build_stt(stt_backend)
    tts, output_sample_rate = _build_tts(tts_backend)

    voice_max_tokens = load_voice_max_tokens()
    vad_stop_secs = load_vad_stop_secs()
    asr_end_window_ms = load_asr_end_window_ms()
    half_duplex = load_half_duplex_enabled()

    store = get_memory_store()
    brain = CompanionBrain(store, max_output_tokens=voice_max_tokens)
    vad = SileroVADProcessor(stop_secs=vad_stop_secs)
    brain_processor = CompanionBrainProcessor(brain)

    pipeline_steps: list[object] = [transport.input()]
    if half_duplex:
        mute_gate = HalfDuplexMuteGate(resume_guard_ms=asr_end_window_ms)
        pipeline_steps.extend(
            [
                HalfDuplexMuteProcessor(mute_gate, role="input"),
                vad,
                stt,
                HalfDuplexMuteProcessor(mute_gate, role="stt_out"),
            ]
        )
    else:
        pipeline_steps.extend([vad, stt])

    transcript_broadcaster = get_transcript_broadcaster()
    pipeline_steps.extend(
        [
            user_transcript_tap(transcript_broadcaster),
            brain_processor,
            boxi_transcript_tap(transcript_broadcaster),
            tts,
            transport.output(),
        ]
    )

    pipeline = Pipeline(pipeline_steps)

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=INPUT_SAMPLE_RATE,
            audio_out_sample_rate=output_sample_rate,
        ),
    )

    runner = WorkerRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info(
        f"Voice pipeline ready (STT={stt_backend}, TTS={tts_backend}, "
        f"half_duplex={'on' if half_duplex else 'off'}) — speak into the mic; "
        + (
            "external speakers OK (no barge-in while Boxi speaks). "
            if half_duplex
            else "use headphones to avoid echo / enable barge-in. "
        )
        + "Ctrl+C to exit."
    )
    logger.info(
        "Voice tuning: "
        f"{ENV_VAD_STOP_SECS}={vad_stop_secs}, "
        f"{ENV_ASR_END_WINDOW_MS}={asr_end_window_ms}, "
        f"{ENV_MAX_TOKENS}={voice_max_tokens}, "
        f"{ENV_HALF_DUPLEX}={'on' if half_duplex else 'off'}; "
        "smart_turn=off (no LLMUserAggregator in pipeline — VAD-only endpointing)"
    )

    await runner.add_workers(worker)
    await runner.run()


async def main() -> None:
    from backend.realtime.voice_config import ENV_VOICE_MODE

    voice_mode = _voice_backend(
        ENV_VOICE_MODE,
        allowed={"pipeline", "realtime"},
        default="pipeline",
    )
    if voice_mode == "realtime":
        await _main_realtime()
    else:
        await _main_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
