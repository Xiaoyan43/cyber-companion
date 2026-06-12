"""Unit tests for Doubao Dialog S2S protocol (network-free).

The protocol module is pure stdlib, so these run in the V1 gate without pipecat or
websockets installed. Service import is guarded behind importorskip.
"""

import gzip
import importlib
import json
import struct

import pytest

from backend.realtime import doubao_realtime_protocol as proto


def _decode_header(frame: bytes) -> dict:
    return {
        "message_type": frame[1] >> 4,
        "flags": frame[1] & 0x0F,
        "serialization": frame[2] >> 4,
        "compression": frame[2] & 0x0F,
    }


def test_start_connection_event_frame() -> None:
    frame = proto.build_connect_event(proto.EVENT_START_CONNECTION)
    header = _decode_header(frame)
    assert header["message_type"] == proto.FULL_CLIENT_REQUEST
    assert header["flags"] == proto.MSG_WITH_EVENT
    event = struct.unpack(">I", frame[4:8])[0]
    assert event == proto.EVENT_START_CONNECTION
    size = struct.unpack(">I", frame[8:12])[0]
    assert json.loads(gzip.decompress(frame[12:])) == {}


def test_start_session_includes_session_id_and_persona_json() -> None:
    from backend.realtime.doubao_realtime_service import build_start_session_payload

    session_id = "test-session-001"
    payload = build_start_session_payload()
    frame = proto.build_session_event(proto.EVENT_START_SESSION, session_id, payload)

    header = _decode_header(frame)
    assert header["message_type"] == proto.FULL_CLIENT_REQUEST
    event = struct.unpack(">I", frame[4:8])[0]
    assert event == proto.EVENT_START_SESSION
    sid_len = struct.unpack(">I", frame[8:12])[0]
    sid = frame[12 : 12 + sid_len].decode("utf-8")
    assert sid == session_id
    offset = 12 + sid_len
    size = struct.unpack(">I", frame[offset : offset + 4])[0]
    decoded = json.loads(gzip.decompress(frame[offset + 4 : offset + 4 + size]))
    assert decoded["dialog"]["bot_name"]
    assert "Boxi" in decoded["dialog"]["system_role"]
    assert "毒舌" in decoded["dialog"]["system_role"]
    assert "边界" not in decoded["dialog"]["system_role"]
    assert "口语化" in decoded["dialog"]["speaking_style"]
    assert decoded["asr"]["extra"]["end_smooth_window_ms"] == 1000
    assert decoded["asr"]["extra"]["enable_asr_twopass"] is True
    assert decoded["asr"]["extra"]["enable_custom_vad"] is True
    assert decoded["dialog"]["extra"]["model"] == "1.2.1.1"
    assert decoded["dialog"]["extra"]["enable_music"] is True
    assert decoded["tts"]["audio_config"]["format"] == "pcm_s16le"


def test_task_request_audio_frame() -> None:
    pcm = b"\x00\x01" * 80
    frame = proto.build_task_request("sess", pcm)
    header = _decode_header(frame)
    assert header["message_type"] == proto.AUDIO_ONLY_REQUEST
    # event(4) + sid_len(4) + sid(4) + payload_size(4) = 16 bytes after 4-byte header
    payload_size = struct.unpack(">I", frame[16:20])[0]
    payload = frame[20 : 20 + payload_size]
    assert gzip.decompress(payload) == pcm


def _server_text_event(event_id: int, payload: dict, *, session_id: str = "sess") -> bytes:
    body = json.dumps(payload).encode("utf-8")
    sid = session_id.encode("utf-8")
    header = bytes(
        [
            (proto.PROTOCOL_VERSION << 4) | proto.DEFAULT_HEADER_SIZE,
            (proto.FULL_SERVER_RESPONSE << 4) | proto.MSG_WITH_EVENT,
            (proto.JSON << 4) | proto.NO_COMPRESSION,
            0x00,
        ]
    )
    return (
        header
        + struct.pack(">I", event_id)
        + struct.pack(">I", len(sid))
        + sid
        + struct.pack(">I", len(body))
        + body
    )


def test_parse_asr_response() -> None:
    raw = _server_text_event(
        proto.EVENT_ASR_RESPONSE,
        {"results": [{"text": "你好", "is_interim": False}]},
    )
    parsed = proto.parse_response(raw)
    assert parsed.event == proto.EVENT_ASR_RESPONSE
    assert parsed.asr_text == "你好"


def test_parse_tts_audio_response() -> None:
    audio = b"OggS" + b"\x00" * 16
    sid = b"sess"
    header = bytes(
        [
            (proto.PROTOCOL_VERSION << 4) | proto.DEFAULT_HEADER_SIZE,
            (proto.AUDIO_ONLY_RESPONSE << 4) | proto.MSG_WITH_EVENT,
            (proto.NO_SERIALIZATION << 4) | proto.NO_COMPRESSION,
            0x00,
        ]
    )
    raw = (
        header
        + struct.pack(">I", proto.EVENT_TTS_RESPONSE)
        + struct.pack(">I", len(sid))
        + sid
        + struct.pack(">I", len(audio))
        + audio
    )
    parsed = proto.parse_response(raw)
    assert parsed.is_audio
    assert parsed.event == proto.EVENT_TTS_RESPONSE
    assert parsed.payload_bytes == audio


def test_doubao_realtime_service_imports_with_env(monkeypatch) -> None:
    pytest.importorskip("pipecat")
    monkeypatch.setenv("DOUBAO_RT_APP_ID", "test-app")
    monkeypatch.setenv("DOUBAO_RT_ACCESS_TOKEN", "test-token")
    module = importlib.import_module("backend.realtime.doubao_realtime_service")
    service = module.DoubaoRealtimeService()
    assert service._session_id
