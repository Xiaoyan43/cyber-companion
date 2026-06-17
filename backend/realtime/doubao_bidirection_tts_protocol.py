"""Volcengine/Doubao TTS 2.0 bidirectional WebSocket binary protocol (pure stdlib).

Framing per the official 火山引擎 语音合成2.0API.md bidirection spec:
  - 4-byte header (protocol version / header size / message type / WITH_EVENT_NUMBER flag /
    serialization / compression)
  - bytes 4-7:  event number (int32 big-endian)
  - bytes 8-11: session_id length (uint32 big-endian) — only in session/data frames
  - bytes 12+:  session_id UTF-8, then payload length (uint32) + payload bytes

This protocol is structurally different from the ASR streaming protocol
(doubao_streaming_protocol.py): TTS uses event numbers embedded per-frame and no gzip.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Any

# ── Header constants ─────────────────────────────────────────────────────────

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message types (upper nibble of byte 1)
FULL_CLIENT_REQUEST = 0b0001   # 0x1_
FULL_SERVER_RESPONSE = 0b1001  # 0x9_
AUDIO_ONLY_RESPONSE = 0b1011   # 0xB_
SERVER_ERROR = 0b1111          # 0xF_

# Message type specific flags (lower nibble of byte 1)
WITH_EVENT_NUMBER = 0b0100     # all TTS bidirection frames carry an event number

# Serialization (upper nibble of byte 2)
JSON_SERIALIZATION = 0b0001
RAW_SERIALIZATION = 0b0000

# Compression (lower nibble of byte 2)
NO_COMPRESSION = 0b0000

# ── Event codes ───────────────────────────────────────────────────────────────

# Connection lifecycle (client → server)
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
# Connection lifecycle (server → client)
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51
EVENT_CONNECTION_FINISHED = 52

# Session lifecycle (client → server)
EVENT_START_SESSION = 100
EVENT_CANCEL_SESSION = 101
EVENT_FINISH_SESSION = 102
# Session lifecycle (server → client)
EVENT_SESSION_STARTED = 150
EVENT_SESSION_CANCELED = 151
EVENT_SESSION_FINISHED = 152
EVENT_SESSION_FAILED = 153

# Data (client → server / server → client)
EVENT_TASK_REQUEST = 200
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_SENTENCE_END = 351
EVENT_TTS_RESPONSE = 352       # audio-only frame

SUCCESS_CODE = 20000000


# ── Frame builders ────────────────────────────────────────────────────────────

def _header(message_type: int, serialization: int) -> bytes:
    return bytes([
        (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE,
        (message_type << 4) | WITH_EVENT_NUMBER,
        (serialization << 4) | NO_COMPRESSION,
        0x00,
    ])


def _pack_event(event: int) -> bytes:
    return struct.pack(">i", event)


def _pack_session_id(session_id: str) -> bytes:
    sid_bytes = session_id.encode("utf-8")
    return struct.pack(">I", len(sid_bytes)) + sid_bytes


def _pack_payload(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


def build_connection_frame(event: int) -> bytes:
    """Build StartConnection (event=1) or FinishConnection (event=2)."""
    payload = b"{}"
    return (
        _header(FULL_CLIENT_REQUEST, JSON_SERIALIZATION)
        + _pack_event(event)
        + _pack_payload(payload)
    )


def build_start_session(session_id: str, tts_params: dict[str, Any]) -> bytes:
    """Build StartSession frame (event=100) with TTS synthesis parameters."""
    meta = json.dumps(tts_params, ensure_ascii=False).encode("utf-8")
    return (
        _header(FULL_CLIENT_REQUEST, JSON_SERIALIZATION)
        + _pack_event(EVENT_START_SESSION)
        + _pack_session_id(session_id)
        + _pack_payload(meta)
    )


def build_finish_session(session_id: str) -> bytes:
    """Build FinishSession frame (event=102) — signals no more text for this session."""
    return (
        _header(FULL_CLIENT_REQUEST, JSON_SERIALIZATION)
        + _pack_event(EVENT_FINISH_SESSION)
        + _pack_session_id(session_id)
        + _pack_payload(b"{}")
    )


def build_task_request(session_id: str, text: str) -> bytes:
    """Build TaskRequest frame (event=200) carrying the text to synthesise."""
    payload = json.dumps(
        {"event": EVENT_TASK_REQUEST, "req_params": {"text": text}},
        ensure_ascii=False,
    ).encode("utf-8")
    return (
        _header(FULL_CLIENT_REQUEST, JSON_SERIALIZATION)
        + _pack_event(EVENT_TASK_REQUEST)
        + _pack_session_id(session_id)
        + _pack_payload(payload)
    )


# ── Response parser ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DoubaoTTSFrame:
    """Parsed server frame from the TTS bidirection WebSocket."""

    event: int
    session_id: str | None
    audio_bytes: bytes | None      # set for TTSResponse (event 352)
    json_payload: dict[str, Any] | None
    error_code: int | None

    @property
    def is_error(self) -> bool:
        return self.error_code is not None

    @property
    def is_audio(self) -> bool:
        return self.event == EVENT_TTS_RESPONSE and self.audio_bytes is not None

    @property
    def is_session_finished(self) -> bool:
        return self.event in (EVENT_SESSION_FINISHED, EVENT_SESSION_FAILED, EVENT_SESSION_CANCELED)

    @property
    def is_session_started(self) -> bool:
        return self.event == EVENT_SESSION_STARTED

    @property
    def is_connection_started(self) -> bool:
        return self.event == EVENT_CONNECTION_STARTED


def parse_tts_frame(data: bytes) -> DoubaoTTSFrame:
    """Parse a server WebSocket binary frame into a :class:`DoubaoTTSFrame`."""
    if len(data) < 8:
        raise ValueError(f"TTS frame too short: {len(data)} bytes")

    header_size = (data[0] & 0x0F) * 4
    message_type = data[1] >> 4
    serialization = data[2] >> 4

    event = struct.unpack(">i", data[4:8])[0]
    body = data[header_size:]  # everything after the 4-byte header

    # Error frame: header + error_code(4) + payload_size(4) + payload
    if message_type == SERVER_ERROR:
        error_code = struct.unpack(">I", body[:4])[0]
        size = struct.unpack(">I", body[4:8])[0]
        msg_bytes = body[8: 8 + size]
        try:
            msg = json.loads(msg_bytes.decode("utf-8"))
        except Exception:
            msg = {"raw": msg_bytes.decode("utf-8", errors="replace")}
        return DoubaoTTSFrame(
            event=event,
            session_id=None,
            audio_bytes=None,
            json_payload=msg,
            error_code=error_code,
        )

    # Normal frame: event(4) + [session_id_len(4) + session_id] + payload_len(4) + payload
    offset = 4  # skip event bytes already read
    session_id: str | None = None
    audio_bytes: bytes | None = None
    json_payload: dict[str, Any] | None = None

    # Connection-level frames (ConnectionStarted/Failed/Finished) have no session_id.
    # Session/data frames embed session_id after the event number.
    if event not in (
        EVENT_CONNECTION_STARTED,
        EVENT_CONNECTION_FAILED,
        EVENT_CONNECTION_FINISHED,
    ):
        if offset + 4 <= len(body):
            sid_len = struct.unpack(">I", body[offset: offset + 4])[0]
            offset += 4
            if offset + sid_len <= len(body):
                session_id = body[offset: offset + sid_len].decode("utf-8")
                offset += sid_len

    if offset + 4 <= len(body):
        payload_size = struct.unpack(">I", body[offset: offset + 4])[0]
        offset += 4
        payload_bytes = body[offset: offset + payload_size]

        if event == EVENT_TTS_RESPONSE and message_type == AUDIO_ONLY_RESPONSE:
            audio_bytes = payload_bytes
        elif serialization == JSON_SERIALIZATION and payload_bytes:
            try:
                decoded = json.loads(payload_bytes.decode("utf-8"))
                json_payload = decoded if isinstance(decoded, dict) else {"value": decoded}
            except Exception:
                pass

    return DoubaoTTSFrame(
        event=event,
        session_id=session_id,
        audio_bytes=audio_bytes,
        json_payload=json_payload,
        error_code=None,
    )
