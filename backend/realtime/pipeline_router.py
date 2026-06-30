"""WebRTC signaling + start/stop endpoints for the Pipecat voice pipeline.

POST /realtime/start      — SDP offer in, SDP answer out (SmallWebRTCTransport handshake);
                             launches the pipeline once the connection is established.
POST /realtime/stop       — disconnect the WebRTC connection and cancel the running pipeline
GET  /realtime/status     — status plus the most recent startup error, if any
WS   /realtime/transcript — push {"role": "user"|"boxi", "text": str, "ts": float} per finalized turn

One pipeline per server process (ConnectionMode.SINGLE) — a second /realtime/start while a
connection is already active is rejected by the WebRTC request handler.

P0-OSS-4 phase 3 (2026-06-30): transport switched from LocalAudioTransport (backend connects
directly to this machine's mic/speaker) to SmallWebRTCTransport (browser captures/plays audio
over WebRTC). See docs/TRANSPORT_SPIKE_RESULTS.md for the spike that validated this swap.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    ConnectionMode,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from backend.realtime.webrtc_loopback_candidate import patch_aioice_loopback_candidate

patch_aioice_loopback_candidate()

router = APIRouter()

_pipeline_task: asyncio.Task | None = None
_pipeline_last_error: str | None = None
_webrtc_handler = SmallWebRTCRequestHandler(connection_mode=ConnectionMode.SINGLE)


@router.post("/realtime/start")
async def start_pipeline(request: SmallWebRTCRequest) -> dict:
    """Accept an SDP offer, return an SDP answer, and launch the pipeline on connect."""
    global _pipeline_last_error

    async def _on_connection(connection: SmallWebRTCConnection) -> None:
        global _pipeline_last_error, _pipeline_task
        _pipeline_last_error = None
        _pipeline_task = asyncio.create_task(_run_pipeline(connection))
        logger.info("[P7] Pipecat pipeline task created (webrtc)")

    answer = await _webrtc_handler.handle_web_request(request, _on_connection)
    return answer


@router.post("/realtime/stop")
async def stop_pipeline() -> dict:
    global _pipeline_task
    running = _pipeline_task is not None and not _pipeline_task.done()
    await _webrtc_handler.close()
    if running:
        _pipeline_task.cancel()
        logger.info("[P7] Pipecat pipeline task cancelled")
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.get("/realtime/status")
async def pipeline_status() -> dict:
    running = _pipeline_task is not None and not _pipeline_task.done()
    return {
        "status": "running" if running else "stopped",
        "last_error": _pipeline_last_error,
    }


@router.websocket("/realtime/transcript")
async def transcript_ws(websocket: WebSocket) -> None:
    from backend.realtime.transcript_broadcaster import get_transcript_broadcaster

    await websocket.accept()
    broadcaster = get_transcript_broadcaster()
    queue = broadcaster.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.unsubscribe(queue)


async def _run_pipeline(connection: SmallWebRTCConnection) -> None:
    global _pipeline_last_error

    from backend.realtime.run_voice import _main_pipeline

    try:
        await _main_pipeline(connection)
    except asyncio.CancelledError:
        logger.info("[P7] Pipecat pipeline stopped by user")
    except Exception as exc:
        _pipeline_last_error = str(exc)
        logger.exception(f"[P7] Pipecat pipeline error: {exc}")
