"""Tests for POST /rtc/turn (PS-2 off-path soul wiring)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.rtc.config import RtcConfig
from backend.app.rtc.routes import _run_turn_analysis, router as rtc_router


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


@pytest.fixture
def rtc_config() -> RtcConfig:
    return RtcConfig(
        rtc_app_id="0123456789abcdef01234567",
        rtc_app_key="test-app-key",
        access_key="AKTEST",
        secret_key="SKTEST",
        rt_app_id="1234567890",
        rt_access_token="rt-token",
        rt_speaker="zh_male_yunzhou_jupiter_bigtts",
        rt_model="1.2.1.1",
        soul_public_url="https://example.com/v1/chat/completions",
        soul_api_key="soul-key",
        welcome_pure="hi pure",
        welcome_hybrid="hi hybrid",
        bot_user_pure="BoxiBot",
        bot_user_hybrid="BoxiHybridBot",
        task_pure="BoxiTask01",
        task_hybrid="BoxiHybridTask01",
        default_user_id="boxi_user",
        viking_memory_api_key="",
        viking_memory_collection="",
        viking_memory_project="default",
        viking_memory_host="https://api-knowledgebase.mlp.cn-beijing.volces.com",
        viking_memory_assistant_id="",
        viking_memory_limit=3,
        viking_memory_transition_words="",
        viking_memory_types=(),
        enable_asr_twopass=False,
        enable_music=True,
    )


def test_run_turn_analysis_injects_set_tts_context_when_non_neutral(
    store: MemoryStore,
    rtc_config: RtcConfig,
) -> None:
    store.update_mood_state(annoyance=0.6)
    with patch("backend.app.rtc.routes.analyze_turn") as mock_analyze:
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            with patch("backend.app.rtc.routes.update_voice_chat") as mock_update:
                _run_turn_analysis(
                    store,
                    room_id="room-ps2",
                    user_text="烦死了",
                    bot_text="又怎么了",
                    budget=BudgetConfig(),
                )
    mock_analyze.assert_called_once()
    mock_update.assert_called_once()
    assert mock_update.call_args.kwargs["command"] == "SetTTSContext"
    assert "更冲、更不耐烦但别凶" in mock_update.call_args.kwargs["message"]


def test_run_turn_analysis_skips_set_tts_context_when_neutral(
    store: MemoryStore,
    rtc_config: RtcConfig,
) -> None:
    with patch("backend.app.rtc.routes.analyze_turn"):
        with patch("backend.app.rtc.routes.load_rtc_config", return_value=rtc_config):
            with patch("backend.app.rtc.routes.update_voice_chat") as mock_update:
                _run_turn_analysis(
                    store,
                    room_id="room-ps2",
                    user_text="你好",
                    bot_text="嗯",
                    budget=BudgetConfig(),
                )
    mock_update.assert_not_called()


def test_claim_turn_analysis_is_per_room(store: MemoryStore) -> None:
    assert store.claim_turn_analysis("room-a") is True
    assert store.claim_turn_analysis("room-a") is False
    assert store.claim_turn_analysis("room-b") is True
    store.release_turn_analysis("room-a")
    assert store.claim_turn_analysis("room-a") is True
    store.release_turn_analysis("room-b")
    store.release_turn_analysis("room-a")
