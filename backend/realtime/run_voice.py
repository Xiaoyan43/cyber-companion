"""Standalone Pipecat voice loop — mic → VAD → STT → Companion Brain → TTS → speaker.

Run: ``python -m backend.realtime.run_voice`` (see ``backend/realtime/README.md``).
Not part of the V1 HTTP gate; soul wiring is V2 Phase 3.
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

    from backend.realtime.doubao_tts_service import DoubaoTTSService, SAMPLE_RATE

    _require_env("DOUBAO_TTS_API_KEY")
    _require_env("DOUBAO_TTS_VOICE_TYPE")
    return DoubaoTTSService(), SAMPLE_RATE


async def main() -> None:
    _require_env("DEEPSEEK_API_KEY")

    # Default stays flash `doubao` until streaming is validated against a live mic
    # (Phase 2b done-criteria #2); switch via CYBER_COMPANION_VOICE_STT=doubao_stream.
    stt_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_STT",
        allowed={"whisper", "doubao", "doubao_stream"},
        default="doubao",
    )
    tts_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_TTS",
        allowed={"mac_say", "doubao"},
        default="doubao",
    )

    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
    from pipecat.workers.runner import WorkerRunner

    from backend.app.memory.store import get_memory_store
    from backend.realtime.companion_brain import CompanionBrain
    from backend.realtime.companion_brain_processor import CompanionBrainProcessor
    from backend.realtime.vad_processor import SileroVADProcessor
    from backend.realtime.voice_config import (
        ENV_ASR_END_WINDOW_MS,
        ENV_MAX_TOKENS,
        ENV_VAD_STOP_SECS,
        load_asr_end_window_ms,
        load_vad_stop_secs,
        load_voice_max_tokens,
    )

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

    store = get_memory_store()
    brain = CompanionBrain(store, max_output_tokens=voice_max_tokens)
    vad = SileroVADProcessor(stop_secs=vad_stop_secs)
    brain_processor = CompanionBrainProcessor(brain)

    pipeline = Pipeline(
        [
            transport.input(),
            vad,
            stt,
            brain_processor,
            tts,
            transport.output(),
        ]
    )

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
        f"Voice brain ready (STT={stt_backend}, TTS={tts_backend}) — speak into the mic; "
        "use headphones to avoid echo. Ctrl+C to exit."
    )
    logger.info(
        "Voice tuning: "
        f"{ENV_VAD_STOP_SECS}={vad_stop_secs}, "
        f"{ENV_ASR_END_WINDOW_MS}={asr_end_window_ms}, "
        f"{ENV_MAX_TOKENS}={voice_max_tokens}; "
        "smart_turn=off (no LLMUserAggregator in pipeline — VAD-only endpointing)"
    )

    await runner.add_workers(worker)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
