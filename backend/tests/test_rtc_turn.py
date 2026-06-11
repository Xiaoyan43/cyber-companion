"""Tests for POST /rtc/turn (PS-2 off-path soul wiring)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.rtc.routes import router as rtc_router


@pytest.fixture
def rtc_client() -> TestClient:
    app = FastAPI()
    app.include_router(rtc_router)
    return TestClient(app)


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MemoryStore:
    reset_memory_store()
    memory_store = MemoryStore(db_path=tmp_path / "rtc_turn.db")
    monkeypatch.setattr("backend.app.rtc.routes.get_memory_store", lambda: memory_store)
    return memory_store


def _turn_payload() -> dict[str, str]:
    return {
        "room_id": "room-ps2",
        "user_id": "user-ps2",
        "user_text": "我在准备面试。",
        "bot_text": "行吧，别慌。",
    }


def test_rtc_turn_returns_ok_immediately(rtc_client: TestClient, store: MemoryStore) -> None:
    with patch("backend.app.rtc.routes.analyze_turn") as mock_analyze:
        with patch("backend.app.rtc.routes.load_budget_config", return_value=BudgetConfig()):
            response = rtc_client.post("/rtc/turn", json=_turn_payload())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_analyze.assert_called_once()
    assert mock_analyze.call_args.kwargs["user_text"] == "我在准备面试。"
    assert store.get_meta("turn_analyzing:room-ps2") == "0"


def test_rtc_turn_rejects_empty_fields(rtc_client: TestClient) -> None:
    response = rtc_client.post(
        "/rtc/turn",
        json={**_turn_payload(), "user_text": "   "},
    )
    assert response.status_code == 400


def test_rtc_turn_single_flight_skips_when_room_already_analyzing(
    rtc_client: TestClient,
    store: MemoryStore,
) -> None:
    store.set_meta("turn_analyzing:room-ps2", "1")
    with patch("backend.app.rtc.routes.analyze_turn") as mock_analyze:
        response = rtc_client.post("/rtc/turn", json=_turn_payload())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_analyze.assert_not_called()
    assert store.get_meta("turn_analyzing:room-ps2") == "1"


def test_claim_turn_analysis_is_per_room(store: MemoryStore) -> None:
    assert store.claim_turn_analysis("room-a") is True
    assert store.claim_turn_analysis("room-a") is False
    assert store.claim_turn_analysis("room-b") is True
    store.release_turn_analysis("room-a")
    assert store.claim_turn_analysis("room-a") is True
    store.release_turn_analysis("room-b")
    store.release_turn_analysis("room-a")
