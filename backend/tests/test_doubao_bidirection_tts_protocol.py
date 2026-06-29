"""Unit tests for the TTS 2.0 bidirection protocol module (no network required)."""

from __future__ import annotations

import json
import struct


from backend.realtime.doubao_bidirection_tts_protocol import (
    EVENT_CONNECTION_STARTED,
    EVENT_FINISH_CONNECTION,
    EVENT_FINISH_SESSION,
    EVENT_SESSION_FAILED,
    EVENT_SESSION_FINISHED,
    EVENT_SESSION_STARTED,
    EVENT_START_CONNECTION,
    EVENT_START_SESSION,
    EVENT_TASK_REQUEST,
    EVENT_TTS_RESPONSE,
    build_connection_frame,
    build_finish_session,
    build_start_session,
    build_task_request,
    parse_tts_frame,
)


# ── Event constant sanity checks ──────────────────────────────────────────────

def test_event_constants() -> None:
    assert EVENT_START_CONNECTION == 1
    assert EVENT_FINISH_CONNECTION == 2
    assert EVENT_CONNECTION_STARTED == 50
    assert EVENT_START_SESSION == 100
    assert EVENT_FINISH_SESSION == 102
    assert EVENT_SESSION_STARTED == 150
    assert EVENT_SESSION_FINISHED == 152
    assert EVENT_SESSION_FAILED == 153
    assert EVENT_TASK_REQUEST == 200
    assert EVENT_TTS_RESPONSE == 352


# ── build_connection_frame ────────────────────────────────────────────────────

def test_start_connection_frame_structure() -> None:
    frame = build_connection_frame(EVENT_START_CONNECTION)
    # 4-byte header + 4-byte event + 4-byte payload size + 2-byte payload "{}"
    assert len(frame) == 14
    event = struct.unpack(">i", frame[4:8])[0]
    assert event == EVENT_START_CONNECTION
    payload_size = struct.unpack(">I", frame[8:12])[0]
    assert payload_size == 2
    assert frame[12:14] == b"{}"


def test_finish_connection_frame_event() -> None:
    frame = build_connection_frame(EVENT_FINISH_CONNECTION)
    event = struct.unpack(">i", frame[4:8])[0]
    assert event == EVENT_FINISH_CONNECTION


# ── build_start_session ───────────────────────────────────────────────────────

def test_start_session_contains_session_id_and_params() -> None:
    params = {"req_params": {"speaker": "zh_female_vv_uranus_bigtts"}}
    frame = build_start_session("test-session-id", params)

    # header (4) + event (4) + sid_len (4) + sid + meta_len (4) + meta
    event = struct.unpack(">i", frame[4:8])[0]
    assert event == EVENT_START_SESSION

    sid_len = struct.unpack(">I", frame[8:12])[0]
    sid = frame[12: 12 + sid_len].decode("utf-8")
    assert sid == "test-session-id"

    offset = 12 + sid_len
    meta_len = struct.unpack(">I", frame[offset: offset + 4])[0]
    meta_bytes = frame[offset + 4: offset + 4 + meta_len]
    meta = json.loads(meta_bytes)
    assert meta["req_params"]["speaker"] == "zh_female_vv_uranus_bigtts"


# ── build_finish_session ──────────────────────────────────────────────────────

def test_finish_session_event_and_session_id() -> None:
    frame = build_finish_session("my-session")
    event = struct.unpack(">i", frame[4:8])[0]
    assert event == EVENT_FINISH_SESSION

    sid_len = struct.unpack(">I", frame[8:12])[0]
    sid = frame[12: 12 + sid_len].decode("utf-8")
    assert sid == "my-session"


# ── build_task_request ────────────────────────────────────────────────────────

def test_task_request_contains_text() -> None:
    frame = build_task_request("sess-abc", "你好，世界")
    event = struct.unpack(">i", frame[4:8])[0]
    assert event == EVENT_TASK_REQUEST

    sid_len = struct.unpack(">I", frame[8:12])[0]
    sid = frame[12: 12 + sid_len].decode("utf-8")
    assert sid == "sess-abc"

    offset = 12 + sid_len
    payload_len = struct.unpack(">I", frame[offset: offset + 4])[0]
    payload = json.loads(frame[offset + 4: offset + 4 + payload_len])
    assert payload["req_params"]["text"] == "你好，世界"


# ── parse_tts_frame ───────────────────────────────────────────────────────────

def _make_server_frame(
    message_type: int,
    event: int,
    *,
    session_id: str | None = None,
    payload: bytes = b"{}",
    is_audio: bool = False,
) -> bytes:
    """Craft a synthetic server binary frame for testing the parser."""
    serialization = 0b0000 if is_audio else 0b0001
    header = bytes([
        0x11,  # version=1, header_size=1
        (message_type << 4) | 0b0100,  # WITH_EVENT_NUMBER
        (serialization << 4) | 0b0000,  # no compression
        0x00,
    ])
    body = struct.pack(">i", event)
    if session_id is not None:
        sid_bytes = session_id.encode("utf-8")
        body += struct.pack(">I", len(sid_bytes)) + sid_bytes
    body += struct.pack(">I", len(payload)) + payload
    return header + body


def test_parse_connection_started() -> None:
    raw = _make_server_frame(0b1001, EVENT_CONNECTION_STARTED, payload=b"{}")
    frame = parse_tts_frame(raw)
    assert frame.event == EVENT_CONNECTION_STARTED
    assert frame.is_connection_started
    assert frame.session_id is None
    assert not frame.is_error


def test_parse_session_started() -> None:
    raw = _make_server_frame(0b1001, EVENT_SESSION_STARTED, session_id="s1", payload=b"{}")
    frame = parse_tts_frame(raw)
    assert frame.event == EVENT_SESSION_STARTED
    assert frame.is_session_started
    assert frame.session_id == "s1"


def test_parse_session_finished() -> None:
    meta = json.dumps({"status_code": 20000000, "message": "ok"}).encode()
    raw = _make_server_frame(0b1001, EVENT_SESSION_FINISHED, session_id="s1", payload=meta)
    frame = parse_tts_frame(raw)
    assert frame.is_session_finished
    assert frame.json_payload is not None
    assert frame.json_payload["status_code"] == 20000000


def test_parse_session_failed_is_session_finished() -> None:
    raw = _make_server_frame(0b1001, EVENT_SESSION_FAILED, session_id="s1", payload=b"{}")
    frame = parse_tts_frame(raw)
    assert frame.is_session_finished


def test_parse_audio_frame() -> None:
    pcm_data = b"\x00\x01\x02\x03" * 100
    raw = _make_server_frame(
        0b1011, EVENT_TTS_RESPONSE, session_id="s1", payload=pcm_data, is_audio=True
    )
    frame = parse_tts_frame(raw)
    assert frame.is_audio
    assert frame.audio_bytes == pcm_data
    assert frame.json_payload is None


def test_parse_error_frame() -> None:
    error_payload = json.dumps({"status_code": 45000001, "message": "bad request"}).encode()
    header = bytes([0x11, 0b1111_0000, 0b0001_0000, 0x00])
    body = struct.pack(">I", 45000001)  # error code
    body += struct.pack(">I", len(error_payload)) + error_payload
    raw = header + body
    frame = parse_tts_frame(raw)
    assert frame.is_error
    assert frame.error_code == 45000001


def test_round_trip_task_request() -> None:
    """Build a TaskRequest frame then reparse the session_id portion."""
    frame = build_task_request("roundtrip-sid", "测试文本")
    # Reparse session_id from the built frame (client → server format).
    # The builder embeds: header(4) + event(4) + sid_len(4) + sid + payload_len(4) + payload
    sid_len = struct.unpack(">I", frame[8:12])[0]
    sid = frame[12: 12 + sid_len].decode("utf-8")
    assert sid == "roundtrip-sid"
    offset = 12 + sid_len
    payload_len = struct.unpack(">I", frame[offset: offset + 4])[0]
    payload = json.loads(frame[offset + 4: offset + 4 + payload_len])
    assert payload["req_params"]["text"] == "测试文本"
