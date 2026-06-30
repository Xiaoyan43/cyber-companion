import asyncio

from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequest

from backend.realtime import pipeline_router


class _FakeWebRTCConnection:
    """Stand-in for SmallWebRTCConnection — _main_pipeline is monkeypatched in these tests, so
    the connection object itself is never touched, only threaded through."""


async def _fake_handle_web_request(request, webrtc_connection_callback) -> dict:
    await webrtc_connection_callback(_FakeWebRTCConnection())
    return {"sdp": "fake-answer-sdp", "type": "answer", "pc_id": "fake-pc-id"}


def _patch_webrtc_handshake(monkeypatch) -> None:
    # Real handle_web_request drives aiortc SDP negotiation, which doesn't make sense in a unit
    # test; these tests are about /realtime/start|stop|status' pipeline-task bookkeeping, not the
    # WebRTC handshake itself (that's exercised manually with a real browser, see HANDOFF).
    monkeypatch.setattr(pipeline_router._webrtc_handler, "handle_web_request", _fake_handle_web_request)


def test_pipeline_status_exposes_last_startup_error(monkeypatch) -> None:
    async def fail_pipeline(connection) -> None:
        raise RuntimeError("missing voice configuration")

    monkeypatch.setattr("backend.realtime.run_voice._main_pipeline", fail_pipeline)
    _patch_webrtc_handshake(monkeypatch)
    pipeline_router._pipeline_task = None
    pipeline_router._pipeline_last_error = None

    async def exercise() -> dict:
        await pipeline_router.start_pipeline(SmallWebRTCRequest(sdp="offer-sdp", type="offer"))
        assert pipeline_router._pipeline_task is not None
        await pipeline_router._pipeline_task
        return await pipeline_router.pipeline_status()

    status = asyncio.run(exercise())

    assert status == {
        "status": "stopped",
        "last_error": "missing voice configuration",
    }


def test_start_pipeline_clears_previous_error(monkeypatch) -> None:
    started = asyncio.Event()

    async def wait_until_cancelled(connection) -> None:
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("backend.realtime.run_voice._main_pipeline", wait_until_cancelled)
    _patch_webrtc_handshake(monkeypatch)
    pipeline_router._pipeline_task = None
    pipeline_router._pipeline_last_error = "old failure"

    async def exercise() -> tuple[dict, dict]:
        start_result = await pipeline_router.start_pipeline(
            SmallWebRTCRequest(sdp="offer-sdp", type="offer")
        )
        await started.wait()
        status = await pipeline_router.pipeline_status()
        await pipeline_router.stop_pipeline()
        assert pipeline_router._pipeline_task is not None
        try:
            await pipeline_router._pipeline_task
        except asyncio.CancelledError:
            pass
        return start_result, status

    start_result, status = asyncio.run(exercise())

    assert start_result == {"sdp": "fake-answer-sdp", "type": "answer", "pc_id": "fake-pc-id"}
    assert status == {"status": "running", "last_error": None}
