"""Unit tests for the Doubao streaming ASR binary protocol (network-free).

The protocol module is pure stdlib, so these run in the V1 gate without pipecat or
websockets installed. The service import + toggle are guarded behind importorskip.
"""

import gzip
import importlib
import json
import struct

import pytest

from backend.realtime import doubao_streaming_protocol as proto


def _decode_header(frame: bytes) -> dict:
    return {
        "version": frame[0] >> 4,
        "header_size": frame[0] & 0x0F,
        "message_type": frame[1] >> 4,
        "flags": frame[1] & 0x0F,
        "serialization": frame[2] >> 4,
        "compression": frame[2] & 0x0F,
    }


def test_full_client_request_is_gzip_json_with_size() -> None:
    params = {"audio": {"format": "pcm"}, "request": {"model_name": "bigmodel"}}
    frame = proto.build_full_client_request(params)

    header = _decode_header(frame)
    assert header["version"] == proto.PROTOCOL_VERSION
    assert header["message_type"] == proto.FULL_CLIENT_REQUEST
    assert header["serialization"] == proto.JSON
    assert header["compression"] == proto.GZIP

    size = struct.unpack(">I", frame[4:8])[0]
    payload = frame[8:]
    assert size == len(payload)
    assert json.loads(gzip.decompress(payload).decode("utf-8")) == params


def test_audio_request_flags_and_payload() -> None:
    pcm = b"\x01\x02\x03\x04"

    mid = proto.build_audio_request(pcm, last=False)
    assert _decode_header(mid)["message_type"] == proto.AUDIO_ONLY_REQUEST
    assert _decode_header(mid)["flags"] == proto.NO_SEQUENCE
    assert gzip.decompress(mid[8:]) == pcm

    last = proto.build_audio_request(pcm, last=True)
    assert _decode_header(last)["flags"] == proto.NEG_SEQUENCE


def _server_frame(payload: dict, *, flags: int = proto.POS_SEQUENCE, seq: int = 1) -> bytes:
    body = gzip.compress(json.dumps(payload).encode("utf-8"))
    header = bytes(
        [
            (proto.PROTOCOL_VERSION << 4) | proto.DEFAULT_HEADER_SIZE,
            (proto.FULL_SERVER_RESPONSE << 4) | flags,
            (proto.JSON << 4) | proto.GZIP,
            0x00,
        ]
    )
    prefix = struct.pack(">i", seq) if flags & 0b0001 else b""
    return header + prefix + struct.pack(">I", len(body)) + body


def test_parse_interim_response() -> None:
    payload = {"result": {"text": "你好", "utterances": [{"text": "你好", "definite": False}]}}
    parsed = proto.parse_response(_server_frame(payload))

    assert parsed.message_type == proto.FULL_SERVER_RESPONSE
    assert parsed.seq == 1
    assert parsed.text == "你好"
    assert parsed.has_definite is False
    assert parsed.is_last is False


def test_parse_definite_response_without_sequence() -> None:
    payload = {"result": {"text": "你好世界", "utterances": [{"text": "你好世界", "definite": True}]}}
    parsed = proto.parse_response(_server_frame(payload, flags=proto.NO_SEQUENCE))

    assert parsed.seq is None
    assert parsed.text == "你好世界"
    assert parsed.has_definite is True


def test_parse_last_packet_flag() -> None:
    payload = {"result": {"text": "结束", "utterances": []}}
    parsed = proto.parse_response(_server_frame(payload, flags=proto.NEG_WITH_SEQUENCE, seq=3))

    assert parsed.is_last is True
    assert parsed.text == "结束"


def test_parse_error_frame() -> None:
    message = json.dumps({"error": "bad"}).encode("utf-8")
    header = bytes(
        [
            (proto.PROTOCOL_VERSION << 4) | proto.DEFAULT_HEADER_SIZE,
            (proto.SERVER_ERROR_RESPONSE << 4) | proto.NO_SEQUENCE,
            (proto.JSON << 4) | proto.NO_COMPRESSION,
            0x00,
        ]
    )
    frame = header + struct.pack(">I", 45000001) + struct.pack(">I", len(message)) + message
    parsed = proto.parse_response(frame)

    assert parsed.is_error is True
    assert parsed.code == 45000001


def test_parse_rejects_short_frame() -> None:
    with pytest.raises(ValueError):
        proto.parse_response(b"\x11")


def test_streaming_service_imports_when_pipecat_present() -> None:
    pytest.importorskip("pipecat")
    pytest.importorskip("websockets")
    module = importlib.import_module("backend.realtime.doubao_streaming_stt_service")
    assert module.DoubaoStreamingSTTService is not None
    assert module.INPUT_SAMPLE_RATE == 16_000
    assert module.DEFAULT_RESOURCE_ID == "volc.seedasr.sauc.duration"
