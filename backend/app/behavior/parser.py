from __future__ import annotations

import json
import re
from dataclasses import dataclass

JSON_BLOCK_PATTERN = re.compile(r"\{[\s\S]*\}")
SIGNALS_SENTINEL = "<<<BOXI_SIGNALS>>>"
# Models sometimes typo the sentinel (e.g. SIGANLS); match any BOXI_* trailer marker.
SIGNALS_SENTINEL_PATTERN = re.compile(r"<<<BOXI_\w+>>>")
_SENTINEL_KEEP_CHARS = 19  # len("<<<BOXI_SIGNALS>>>")
_LEAKED_REMINDER_MARKER = "（系统提醒："


@dataclass(frozen=True)
class StructuredAssistantResponse:
    content: str
    avatar_state: str | None = None
    decision: str | None = None
    signals: dict | None = None


def _find_complete_sentinel_start(text: str) -> int | None:
    match = SIGNALS_SENTINEL_PATTERN.search(text)
    if match is None:
        return None
    return match.start()


def _strip_trailing_sentinel_fragment(text: str) -> str:
    start = text.rfind("<<<BOXI_")
    if start == -1:
        return text
    return text[:start].rstrip()


class SignalStreamFilter:
    """Emits reply text up to the signals sentinel; swallows the trailer. The caller
    still accumulates the full raw text separately for the final parse."""

    def __init__(self) -> None:
        self._buf = ""
        self._done = False

    def feed(self, chunk: str) -> str:
        if self._done:
            return ""
        self._buf += chunk
        sentinel_start = _find_complete_sentinel_start(self._buf)
        if sentinel_start is not None:
            out = strip_leaked_provider_reminder(self._buf[:sentinel_start])
            self._buf = ""
            self._done = True
            return out
        keep = _SENTINEL_KEEP_CHARS - 1
        if len(self._buf) > keep:
            out = self._buf[:-keep]
            self._buf = self._buf[-keep:]
            leak_idx = out.find(_LEAKED_REMINDER_MARKER)
            if leak_idx != -1:
                self._done = True
                return out[:leak_idx].rstrip()
            return out
        return ""

    def flush(self) -> str:
        if self._done:
            return ""
        out = strip_leaked_provider_reminder(_strip_trailing_sentinel_fragment(self._buf))
        self._buf = ""
        return out


def strip_leaked_provider_reminder(content: str) -> str:
    """Remove echoed user-turn trailer reminder if the model copies it into the reply."""
    idx = content.find(_LEAKED_REMINDER_MARKER)
    if idx == -1:
        return content
    return content[:idx].rstrip()


def _finalize_visible_content(content: str) -> str:
    return strip_leaked_provider_reminder(content.strip())


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


def _split_sentinel_response(raw_content: str) -> tuple[str, str] | None:
    match = SIGNALS_SENTINEL_PATTERN.search(raw_content)
    if match is None:
        return None
    return raw_content[: match.start()].strip(), raw_content[match.end() :]


def parse_structured_assistant_response(raw_content: str) -> StructuredAssistantResponse:
    stripped = raw_content.strip()
    if not stripped:
        return StructuredAssistantResponse(content="")

    sentinel_parts = _split_sentinel_response(raw_content)
    if sentinel_parts is not None:
        content, trailer = sentinel_parts
        content = _finalize_visible_content(content)
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
                    content=_finalize_visible_content(str(payload.get("content", ""))),
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
                    content=_finalize_visible_content(content),
                    avatar_state=payload.get("avatar_state"),
                    decision=payload.get("decision"),
                )
        except json.JSONDecodeError:
            pass

    return StructuredAssistantResponse(content=_finalize_visible_content(stripped))
