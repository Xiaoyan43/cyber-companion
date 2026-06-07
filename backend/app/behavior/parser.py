from __future__ import annotations

import json
import re
from dataclasses import dataclass

JSON_BLOCK_PATTERN = re.compile(r"\{[\s\S]*\}")


@dataclass(frozen=True)
class StructuredAssistantResponse:
    content: str
    avatar_state: str | None = None
    decision: str | None = None


def parse_structured_assistant_response(raw_content: str) -> StructuredAssistantResponse:
    stripped = raw_content.strip()
    if not stripped:
        return StructuredAssistantResponse(content="")

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
