"""Standalone Pipecat voice skeleton — mic → VAD → STT → DeepSeek → TTS → speaker.

Run: ``python -m backend.realtime.run_voice`` (see ``backend/realtime/README.md``).
Not part of the V1 HTTP gate; soul wiring lands in Phase 3.
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

BOXI_VOICE_PROMPT = (
    "你是 Boxi，一个被困在玻璃盒子里的小人。说话简短、口语化，带点毒舌但不恶毒。"
    "你在语音对话里回答，不要用 markdown、列表或表情符号。"
)

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

    stt_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_STT",
        allowed={"whisper", "doubao"},
        default="doubao",
    )
    tts_backend = _voice_backend(
        "CYBER_COMPANION_VOICE_TTS",
        allowed={"mac_say", "doubao"},
        default="doubao",
    )

    # Pipecat 1.3.0 local voice agent pattern (see examples/getting-started/06a-voice-agent-local.py).
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
    )
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
    from pipecat.workers.runner import WorkerRunner

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    stt = _build_stt(stt_backend)
    tts, output_sample_rate = _build_tts(tts_backend)

    llm = OpenAILLMService(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        settings=OpenAILLMService.Settings(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            system_instruction=BOXI_VOICE_PROMPT,
            temperature=0.7,
            max_tokens=300,
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
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
        f"Voice skeleton ready (STT={stt_backend}, TTS={tts_backend}) — speak into the mic; "
        "use headphones to avoid echo. Ctrl+C to exit."
    )

    await runner.add_workers(worker)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
