from __future__ import annotations

import json
import re
from dataclasses import dataclass

JSON_BLOCK_PATTERN = re.compile(r"\{[\s\S]*\}")
SIGNALS_SENTINEL = "<<<BOXI_SIGNALS>>>"


@dataclass(frozen=True)
class StructuredAssistantResponse:
    content: str
    avatar_state: str | None = None
    decision: str | None = None
    signals: dict | None = None


class SignalStreamFilter:
    """Emits reply text up to SIGNALS_SENTINEL; swallows the trailer. The caller
    still accumulates the full raw text separately for the final parse."""

    def __init__(self) -> None:
        self._buf = ""
        self._done = False

    def feed(self, chunk: str) -> str:
        if self._done:
            return ""
        self._buf += chunk
        idx = self._buf.find(SIGNALS_SENTINEL)
        if idx != -1:
            out = self._buf[:idx]
            self._buf = ""
            self._done = True
            return out
        keep = len(SIGNALS_SENTINEL) - 1
        if len(self._buf) > keep:
            out = self._buf[:-keep]
            self._buf = self._buf[-keep:]
            return out
        return ""

    def flush(self) -> str:
        if self._done:
            return ""
        out = self._buf
        self._buf = ""
        return out


def _parse_sentinel_trailer(trailer: str) -> dict | None:
    match = JSON_BLOCK_PATTERN.search(trailer)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def parse_structured_assistant_response(raw_content: str) -> StructuredAssistantResponse:
    stripped = raw_content.strip()
    if not stripped:
        return StructuredAssistantResponse(content="")

    if SIGNALS_SENTINEL in raw_content:
        idx = raw_content.find(SIGNALS_SENTINEL)
        content = raw_content[:idx].strip()
        trailer = raw_content[idx + len(SIGNALS_SENTINEL) :]
        payload = _parse_sentinel_trailer(trailer)
        if payload is not None:
            return StructuredAssistantResponse(
                content=content,
                avatar_state=payload.get("avatar_state"),
                decision=payload.get("decision"),
                signals=payload,
            )
        return StructuredAssistantResponse(content=content)

    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict) and "content" in payload:
                return StructuredAssistantResponse(
                    content=str(payload.get("content", "")),
                    avatar_state=payload.get("avatar_state"),
                    decision=payload.get("decision"),
                )
        except json.JSONDecodeError:
            pass

    match = JSON_BLOCK_PATTERN.search(stripped)
    if match:
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, dict) and "content" in payload:
                prefix = stripped[: match.start()].strip()
                content = str(payload.get("content", ""))
                if prefix:
                    content = f"{prefix}\n{content}".strip()
                return StructuredAssistantResponse(
                    content=content,
                    avatar_state=payload.get("avatar_state"),
                    decision=payload.get("decision"),
                )
        except json.JSONDecodeError:
            pass

    return StructuredAssistantResponse(content=stripped)
