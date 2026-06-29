import asyncio

from backend.realtime import pipeline_router


def test_pipeline_status_exposes_last_startup_error(monkeypatch) -> None:
    async def fail_pipeline() -> None:
        raise RuntimeError("missing voice configuration")

    monkeypatch.setattr("backend.realtime.run_voice._main_pipeline", fail_pipeline)
    pipeline_router._pipeline_task = None
    pipeline_router._pipeline_last_error = None

    async def exercise() -> dict:
        await pipeline_router.start_pipeline()
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

    async def wait_until_cancelled() -> None:
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("backend.realtime.run_voice._main_pipeline", wait_until_cancelled)
    pipeline_router._pipeline_task = None
    pipeline_router._pipeline_last_error = "old failure"

    async def exercise() -> tuple[dict, dict]:
        start_result = await pipeline_router.start_pipeline()
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

    assert start_result == {"status": "started"}
    assert status == {"status": "running", "last_error": None}
