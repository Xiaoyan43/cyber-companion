"""Volcengine RTC AccessToken — ported from rtc-aigc-demo Server/token.js (BSD-3-Clause)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from dataclasses import dataclass, field

VERSION = "001"

PRIV_PUBLISH_STREAM = 0
PRIV_PUBLISH_AUDIO_STREAM = 1
PRIV_PUBLISH_VIDEO_STREAM = 2
PRIV_PUBLISH_DATA_STREAM = 3
PRIV_SUBSCRIBE_STREAM = 4


@dataclass
class AccessToken:
    app_id: str
    app_key: str
    room_id: str
    user_id: str
    issued_at: int = field(default_factory=lambda: int(__import__("time").time()))
    nonce: int = field(default_factory=lambda: int.from_bytes(os.urandom(4), "little"))
    expire_at: int = 0
    privileges: dict[int, int] = field(default_factory=dict)

    def add_privilege(self, privilege: int, expire_timestamp: int) -> None:
        self.privileges[privilege] = expire_timestamp
        if privilege == PRIV_PUBLISH_STREAM:
            self.privileges[PRIV_PUBLISH_VIDEO_STREAM] = expire_timestamp
            self.privileges[PRIV_PUBLISH_AUDIO_STREAM] = expire_timestamp
            self.privileges[PRIV_PUBLISH_DATA_STREAM] = expire_timestamp

    def expire_time(self, expire_timestamp: int) -> None:
        self.expire_at = expire_timestamp

    def _pack_msg(self) -> bytes:
        buf = bytearray()
        buf.extend(struct.pack("<I", self.nonce))
        buf.extend(struct.pack("<I", self.issued_at))
        buf.extend(struct.pack("<I", self.expire_at))
        buf.extend(_put_string(self.room_id))
        buf.extend(_put_string(self.user_id))
        buf.extend(_put_tree_map_u32(self.privileges))
        return bytes(buf)

    def serialize(self) -> str:
        msg = self._pack_msg()
        signature = hmac.new(self.app_key.encode("utf-8"), msg, hashlib.sha256).digest()
        # Demo token.js wraps the packed msg in putBytes() before appending the signature.
        content = _put_bytes(msg) + _put_bytes(signature)
        return VERSION + self.app_id + base64.b64encode(content).decode("ascii")


def mint_rtc_token(
    *,
    app_id: str,
    app_key: str,
    room_id: str,
    user_id: str,
    ttl_seconds: int = 86_400,
) -> str:
    token = AccessToken(app_id=app_id, app_key=app_key, room_id=room_id, user_id=user_id)
    token.add_privilege(PRIV_SUBSCRIBE_STREAM, 0)
    token.add_privilege(PRIV_PUBLISH_STREAM, 0)
    token.expire_time(token.issued_at + ttl_seconds)
    return token.serialize()


def _put_bytes(data: bytes) -> bytes:
    return struct.pack("<H", len(data)) + data


def _put_string(text: str) -> bytes:
    return _put_bytes(text.encode("utf-8"))


def _put_tree_map_u32(values: dict[int, int]) -> bytes:
    buf = bytearray()
    buf.extend(struct.pack("<H", len(values)))
    for key in sorted(values):
        buf.extend(struct.pack("<H", key))
        buf.extend(struct.pack("<I", values[key]))
    return bytes(buf)
