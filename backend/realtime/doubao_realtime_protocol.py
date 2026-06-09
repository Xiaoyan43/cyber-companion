"""Volcengine Doubao Dialog / realtime S2S WebSocket binary protocol (stdlib only).

Framing per the official 端到端实时语音大模型 API docs (doc series 6561, page 1594356):
4-byte header, optional fields (event / session id / sequence), payload size, payload.
Client events carry gzip-compressed JSON; TaskRequest audio is gzip-compressed PCM.

Adapted from the vendor ``realtime_dialog`` Python sample (protocol.py / client helpers).
Kept dependency-free so frame builder/parser can be unit-tested without pipecat or a live socket.
"""

from __future__ import annotations

import gzip
import json
import struct
from dataclasses import dataclass
from typing import Any

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message types.
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
AUDIO_ONLY_RESPONSE = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message-type-specific flags.
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
MSG_WITH_EVENT = 0b0100

# Serialization / compression.
NO_SERIALIZATION = 0b0000
JSON = 0b0001
NO_COMPRESSION = 0b0000
GZIP = 0b0001

# Client events (subset used in Phase 2c Task 1).
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_TASK_REQUEST = 200

# Server events (subset).
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51
EVENT_SESSION_STARTED = 150
EVENT_SESSION_FAILED = 153
EVENT_ASR_INFO = 450
EVENT_ASR_RESPONSE = 451
EVENT_ASR_ENDED = 459
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_RESPONSE = 352
EVENT_TTS_ENDED = 359
EVENT_CHAT_RESPONSE = 550
EVENT_CHAT_ENDED = 559
EVENT_DIALOG_ERROR = 599


def _header(
    message_type: int,
    flags: int,
    serialization: int = JSON,
    compression: int = GZIP,
) -> bytes:
    return bytes(
        [
            (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE,
            (message_type << 4) | flags,
            (serialization << 4) | compression,
            0x00,
        ]
    )


def build_connect_event(event_id: int, payload: dict[str, Any] | None = None) -> bytes:
    """Build a connection-level client event (no session id)."""
    body = gzip.compress(json.dumps(payload or {}).encode("utf-8"))
    return (
        _header(FULL_CLIENT_REQUEST, MSG_WITH_EVENT)
        + struct.pack(">I", event_id)
        + struct.pack(">I", len(body))
        + body
    )


def build_session_event(
    event_id: int,
    session_id: str,
    payload: dict[str, Any] | None = None,
    *,
    message_type: int = FULL_CLIENT_REQUEST,
    serialization: int = JSON,
    compression: int = GZIP,
) -> bytes:
    """Build a session-level client event."""
    sid = session_id.encode("utf-8")
    if serialization == JSON:
        raw = json.dumps(payload or {}).encode("utf-8")
        body = gzip.compress(raw) if compression == GZIP else raw
    else:
        body = payload if isinstance(payload, (bytes, bytearray)) else b""
        if compression == GZIP and body:
            body = gzip.compress(body)

    return (
        _header(message_type, MSG_WITH_EVENT, serialization=serialization, compression=compression)
        + struct.pack(">I", event_id)
        + struct.pack(">I", len(sid))
        + sid
        + struct.pack(">I", len(body))
        + body
    )


def build_task_request(session_id: str, pcm: bytes) -> bytes:
    """Build a TaskRequest (event 200) carrying gzip-compressed mic PCM."""
    body = gzip.compress(pcm)
    sid = session_id.encode("utf-8")
    return (
        _header(AUDIO_ONLY_REQUEST, MSG_WITH_EVENT, serialization=NO_SERIALIZATION, compression=GZIP)
        + struct.pack(">I", EVENT_TASK_REQUEST)
        + struct.pack(">I", len(sid))
        + sid
        + struct.pack(">I", len(body))
        + body
    )


@dataclass(frozen=True)
class DoubaoDialogResponse:
    """Parsed Dialog server frame."""

    message_type: int
    flags: int
    serialization: int
    compression: int
    event: int | None
    session_id: str | None
    code: int | None
    payload_bytes: bytes
    payload_json: dict[str, Any] | None

    @property
    def is_error(self) -> bool:
        return self.message_type == SERVER_ERROR_RESPONSE

    @property
    def is_audio(self) -> bool:
        return self.message_type == AUDIO_ONLY_RESPONSE

    @property
    def asr_text(self) -> str:
        if not self.payload_json:
            return ""
        results = self.payload_json.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                return str(first.get("text") or "").strip()
        return ""

    @property
    def chat_text(self) -> str:
        if not self.payload_json:
            return ""
        return str(self.payload_json.get("content") or "").strip()


def parse_response(data: bytes) -> DoubaoDialogResponse:
    """Parse a server WebSocket binary frame."""
    if len(data) < 4:
        raise ValueError("Doubao Dialog response is too short for a header.")

    header_size = data[0] & 0x0F
    message_type = data[1] >> 4
    flags = data[1] & 0x0F
    serialization = data[2] >> 4
    compression = data[2] & 0x0F

    body = data[header_size * 4 :]
    event: int | None = None
    session_id: str | None = None
    code: int | None = None
    payload_bytes = b""

    if message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(body[:4], "big")
        size = int.from_bytes(body[4:8], "big")
        payload_bytes = body[8 : 8 + size]
    else:
        offset = 0
        if flags & POS_SEQUENCE:
            offset += 4
        if flags & MSG_WITH_EVENT:
            event = int.from_bytes(body[offset : offset + 4], "big")
            offset += 4
        if message_type in {FULL_SERVER_RESPONSE, AUDIO_ONLY_RESPONSE} and offset + 4 <= len(body):
            session_id_size = int.from_bytes(body[offset : offset + 4], "big", signed=True)
            offset += 4
            if session_id_size > 0:
                session_id = body[offset : offset + session_id_size].decode("utf-8", errors="replace")
                offset += session_id_size
        if offset + 4 <= len(body):
            size = int.from_bytes(body[offset : offset + 4], "big")
            offset += 4
            payload_bytes = body[offset : offset + size]

    if payload_bytes and compression == GZIP:
        try:
            payload_bytes = gzip.decompress(payload_bytes)
        except OSError:
            pass

    payload_json: dict[str, Any] | None = None
    if payload_bytes and serialization == JSON:
        decoded = json.loads(payload_bytes.decode("utf-8"))
        payload_json = decoded if isinstance(decoded, dict) else {"value": decoded}

    return DoubaoDialogResponse(
        message_type=message_type,
        flags=flags,
        serialization=serialization,
        compression=compression,
        event=event,
        session_id=session_id,
        code=code,
        payload_bytes=payload_bytes if serialization != JSON else b"",
        payload_json=payload_json,
    )
