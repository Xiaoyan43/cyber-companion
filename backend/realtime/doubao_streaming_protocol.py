"""Volcengine/Doubao BigASR streaming WebSocket binary protocol (pure stdlib).

Framing per the official 火山引擎 大模型流式语音识别 docs (doc series 6561, page
1354869): a 4-byte header (protocol version / header size / message type / flags /
serialization / compression), then for client requests a big-endian uint32 payload
size followed by a (gzip-compressed) payload. Server responses carry an optional
4-byte sequence (when the flags' sequence bit is set), the payload size, then the
gzip-JSON payload; error frames carry a 4-byte code + 4-byte size + message.

This module is dependency-free (stdlib only) so the frame builder/parser can be
unit-tested without pipecat or a live WebSocket. Reference: the public Volcengine
``sauc_python`` demo's ``generate_header`` / ``parse_response`` helpers.
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
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message-type-specific flags.
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010  # last (negative) packet, no explicit sequence number
NEG_WITH_SEQUENCE = 0b0011

# Serialization.
NO_SERIALIZATION = 0b0000
JSON = 0b0001

# Compression.
NO_COMPRESSION = 0b0000
GZIP = 0b0001

SUCCESS_CODE = 20000000


def _header(message_type: int, flags: int, serialization: int, compression: int) -> bytes:
    return bytes(
        [
            (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE,
            (message_type << 4) | flags,
            (serialization << 4) | compression,
            0x00,  # reserved
        ]
    )


def build_full_client_request(params: dict[str, Any]) -> bytes:
    """Build the initial ``full client request`` carrying the JSON config."""
    payload = gzip.compress(json.dumps(params).encode("utf-8"))
    return (
        _header(FULL_CLIENT_REQUEST, NO_SEQUENCE, JSON, GZIP)
        + struct.pack(">I", len(payload))
        + payload
    )


def build_audio_request(pcm: bytes, *, last: bool = False) -> bytes:
    """Build an ``audio only request`` carrying a gzip-compressed PCM chunk."""
    flags = NEG_SEQUENCE if last else NO_SEQUENCE
    payload = gzip.compress(pcm)
    return (
        _header(AUDIO_ONLY_REQUEST, flags, NO_SERIALIZATION, GZIP)
        + struct.pack(">I", len(payload))
        + payload
    )


@dataclass(frozen=True)
class DoubaoASRResponse:
    """Parsed server frame."""

    message_type: int
    is_last: bool
    code: int | None
    payload: dict[str, Any] | None
    seq: int | None

    @property
    def is_error(self) -> bool:
        return self.message_type == SERVER_ERROR_RESPONSE

    @property
    def text(self) -> str:
        if not self.payload:
            return ""
        result = self.payload.get("result")
        if isinstance(result, dict):
            return str(result.get("text") or "").strip()
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                return str(first.get("text") or "").strip()
        return ""

    @property
    def utterances(self) -> list[dict[str, Any]]:
        if not self.payload:
            return []
        result = self.payload.get("result")
        if isinstance(result, dict):
            items = result.get("utterances")
            return items if isinstance(items, list) else []
        return []

    @property
    def has_definite(self) -> bool:
        return any(bool(u.get("definite")) for u in self.utterances)


def parse_response(data: bytes) -> DoubaoASRResponse:
    """Parse a server WebSocket binary frame into a :class:`DoubaoASRResponse`."""
    if len(data) < 4:
        raise ValueError("Doubao ASR response is too short for a header.")

    header_size = data[0] & 0x0F
    message_type = data[1] >> 4
    flags = data[1] & 0x0F
    serialization = data[2] >> 4
    compression = data[2] & 0x0F

    body = data[header_size * 4 :]
    is_last = bool(flags & 0b0010)
    seq: int | None = None
    code: int | None = None
    payload_bytes = b""

    if message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(body[:4], "big")
        size = int.from_bytes(body[4:8], "big")
        payload_bytes = body[8 : 8 + size]
    else:
        offset = 0
        if flags & 0b0001:  # a sequence number precedes the payload size
            seq = int.from_bytes(body[:4], "big", signed=True)
            offset = 4
        size = int.from_bytes(body[offset : offset + 4], "big")
        payload_bytes = body[offset + 4 : offset + 4 + size]

    payload: dict[str, Any] | None = None
    if payload_bytes:
        if compression == GZIP:
            payload_bytes = gzip.decompress(payload_bytes)
        if serialization == JSON:
            decoded = json.loads(payload_bytes.decode("utf-8"))
            payload = decoded if isinstance(decoded, dict) else {"value": decoded}

    return DoubaoASRResponse(
        message_type=message_type,
        is_last=is_last,
        code=code,
        payload=payload,
        seq=seq,
    )
