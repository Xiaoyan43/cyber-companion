"""HTTP start/stop endpoints for the Pipecat local voice pipeline.

POST /realtime/start  — launch pipeline (LocalAudioTransport, mic+speaker)
POST /realtime/stop   — cancel the running pipeline
GET  /realtime/status — {"status": "running"|"stopped"}

One pipeline per server process; starting again while running is a no-op.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from loguru import logger

router = APIRouter()

_pipeline_task: asyncio.Task | None = None


@router.post("/realtime/start")
async def start_pipeline() -> dict:
    global _pipeline_task
    if _pipeline_task and not _pipeline_task.done():
        return {"status": "already_running"}
    _pipeline_task = asyncio.create_task(_run_pipeline())
    logger.info("[P7] Pipecat pipeline task created")
    return {"status": "started"}


@router.post("/realtime/stop")
async def stop_pipeline() -> dict:
    global _pipeline_task
    if _pipeline_task and not _pipeline_task.done():
        _pipeline_task.cancel()
        logger.info("[P7] Pipecat pipeline task cancelled")
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.get("/realtime/status")
async def pipeline_status() -> dict:
    running = _pipeline_task is not None and not _pipeline_task.done()
    return {"status": "running" if running else "stopped"}


async def _run_pipeline() -> None:
    from backend.realtime.run_voice import _main_pipeline

    try:
        await _main_pipeline()
    except asyncio.CancelledError:
        logger.info("[P7] Pipecat pipeline stopped by user")
    except Exception as exc:
        logger.exception(f"[P7] Pipecat pipeline error: {exc}")
