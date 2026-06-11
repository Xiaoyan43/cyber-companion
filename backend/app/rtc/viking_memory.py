"""Viking 记忆库 — AddSession write + SearchMemory inject for pure E2E RTC."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx

from backend.app.rtc.config import RtcConfig

DEFAULT_VIKING_HOST = "https://api-knowledgebase.mlp.cn-beijing.volces.com"
ADD_SESSION_PATH = "/api/memory/session/add"
SEARCH_MEMORY_PATH = "/api/memory/search"
DEFAULT_SEARCH_MEMORY_TYPES = ("profile_v1", "event_v1")
DEFAULT_RUNTIME_MEMORY_TYPES = ("profile_v1",)
DEFAULT_MEMORY_TRANSITION = "关于这位用户，你已知道："
MEMORY_INJECT_INSTRUCTION = (
    "下列为用户长期记忆。用户问名字、所在地、职业等时，必须以【用户档案】为准直接回答，"
    "不要说你不知道或让用户再说一遍。"
)
_CONTRADICTORY_EVENT_MARKERS = (
    "还未告知",
    "没告诉我",
    "你还没",
    "不知道你叫",
    "没说过名字",
)


class VikingMemoryError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _viking_headers(config: RtcConfig) -> dict[str, str]:
    if not config.viking_memory_api_key:
        raise VikingMemoryError("VIKING_MEMORY_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {config.viking_memory_api_key}",
        "Content-Type": "application/json",
    }


def _viking_post(config: RtcConfig, path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{config.viking_memory_host.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=_viking_headers(config), json=body)
    except httpx.HTTPError as error:
        raise VikingMemoryError(f"Viking API request failed: {error}") from error

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason_phrase
        raise VikingMemoryError(
            f"Viking API failed ({response.status_code}): {detail}",
            status_code=response.status_code,
        )
    try:
        return response.json()
    except ValueError as error:
        raise VikingMemoryError("Viking API returned non-JSON response") from error


def _search_memory_types(config: RtcConfig) -> list[str]:
    if config.viking_memory_types:
        return list(config.viking_memory_types)
    return list(DEFAULT_SEARCH_MEMORY_TYPES)


def search_user_memories(
    config: RtcConfig,
    user_id: str,
    *,
    query: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent profile + event memories for session-start inject (no user query yet)."""
    if not config.viking_memory_collection:
        raise VikingMemoryError("VIKING_MEMORY_COLLECTION is not configured")

    body: dict[str, Any] = {
        "collection_name": config.viking_memory_collection,
        "project_name": config.viking_memory_project,
        "limit": limit or config.viking_memory_limit,
        "filter": {
            "user_id": user_id,
            "memory_type": _search_memory_types(config),
        },
    }
    if query.strip():
        body["query"] = query.strip()

    payload = _viking_post(config, SEARCH_MEMORY_PATH, body)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return []
    result_list = data.get("result_list")
    if not isinstance(result_list, list):
        return []
    return [item for item in result_list if isinstance(item, dict)]


def _memory_info_to_line(memory_info: Any) -> str:
    if memory_info is None:
        return ""
    if isinstance(memory_info, str):
        return memory_info.strip()
    if isinstance(memory_info, dict):
        if summary := memory_info.get("summary"):
            return str(summary).strip()
        if profile := memory_info.get("user_profile"):
            if isinstance(profile, dict):
                return json.dumps(profile, ensure_ascii=False)
            return str(profile).strip()
        return json.dumps(memory_info, ensure_ascii=False)
    return str(memory_info).strip()


def _coerce_profile_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    if isinstance(raw, dict):
        return raw
    return {}


def _profile_line_from_hit(hit: dict[str, Any]) -> str:
    memory_info = hit.get("memory_info")
    if not isinstance(memory_info, dict):
        return ""
    profile = _coerce_profile_dict(memory_info.get("user_profile"))
    basic = profile.get("基础信息")
    if not isinstance(basic, dict):
        return ""
    parts: list[str] = []
    if nick := basic.get("昵称"):
        parts.append(f"昵称 {nick}")
    if city := basic.get("常驻城市"):
        parts.append(f"在{city}")
    if job := basic.get("职业规划"):
        parts.append(f"正在{job}")
    return "，".join(parts)


def _extract_profile_nickname(hits: list[dict[str, Any]]) -> str:
    for hit in hits:
        if hit.get("memory_type") != "profile_v1":
            continue
        memory_info = hit.get("memory_info")
        if not isinstance(memory_info, dict):
            continue
        profile = _coerce_profile_dict(memory_info.get("user_profile"))
        basic = profile.get("基础信息")
        if isinstance(basic, dict) and (nick := basic.get("昵称")):
            return str(nick).strip()
    return ""


def _sort_hits_for_inject(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = [hit for hit in hits if hit.get("memory_type") == "profile_v1"]
    events = [hit for hit in hits if hit.get("memory_type") == "event_v1"]
    events.sort(key=lambda hit: int(hit.get("time") or 0), reverse=True)
    other = [
        hit
        for hit in hits
        if hit.get("memory_type") not in {"profile_v1", "event_v1"}
    ]
    return profiles + events + other


def _should_skip_event_summary(summary: str, nickname: str) -> bool:
    if not nickname:
        return False
    return any(marker in summary for marker in _CONTRADICTORY_EVENT_MARKERS)


def format_memories_for_system_role(hits: list[dict[str, Any]]) -> str:
    sorted_hits = _sort_hits_for_inject(hits)
    nickname = _extract_profile_nickname(sorted_hits)
    lines: list[str] = []
    for hit in sorted_hits:
        memory_type = hit.get("memory_type")
        if memory_type == "profile_v1":
            line = _profile_line_from_hit(hit)
            if line:
                lines.append(f"【用户档案】{line}")
            continue
        summary = _memory_info_to_line(hit.get("memory_info"))
        if not summary:
            continue
        if memory_type == "event_v1" and _should_skip_event_summary(summary, nickname):
            continue
        lines.append(f"- {summary}")
    if not lines:
        return ""
    return f"{MEMORY_INJECT_INSTRUCTION}\n\n" + "\n".join(lines)


def merge_subtitle_turns(
    subtitles: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Collapse streaming subtitle lines into alternating user/assistant messages."""
    messages: list[dict[str, str]] = []
    for line in subtitles:
        text = line.get("text", "").strip()
        if not text:
            continue
        speaker = line.get("speaker", "user")
        role = "assistant" if speaker == "boxi" else "user"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] = f"{messages[-1]['content']}{text}"
        else:
            messages.append({"role": role, "content": text})
    return messages


def build_add_session_body(
    config: RtcConfig,
    *,
    session_id: str,
    user_id: str,
    bot_user_id: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    if not messages:
        raise VikingMemoryError("No transcript messages to save")

    assistant_id = config.viking_memory_assistant_id or bot_user_id or config.bot_user_pure
    body: dict[str, Any] = {
        "collection_name": config.viking_memory_collection,
        "project_name": config.viking_memory_project,
        "session_id": session_id,
        "messages": messages,
        "metadata": {
            "default_user_id": user_id,
            "default_assistant_id": assistant_id,
            "default_assistant_name": "Boxi",
            "time": int(time.time() * 1000),
        },
    }
    if config.viking_memory_types:
        body["extract_memory_type"] = list(config.viking_memory_types)
    return body


def add_memory_session(
    config: RtcConfig,
    *,
    user_id: str,
    bot_user_id: str,
    messages: list[dict[str, str]],
    session_id: str | None = None,
) -> dict[str, Any]:
    if not config.viking_memory_api_key:
        raise VikingMemoryError("VIKING_MEMORY_API_KEY is not configured")
    if not config.viking_memory_collection:
        raise VikingMemoryError("VIKING_MEMORY_COLLECTION is not configured")

    resolved_session_id = session_id or f"rtc_{uuid.uuid4().hex}"
    body = build_add_session_body(
        config,
        session_id=resolved_session_id,
        user_id=user_id,
        bot_user_id=bot_user_id,
        messages=messages,
    )
    payload = _viking_post(config, ADD_SESSION_PATH, body)
    return {
        "session_id": resolved_session_id,
        "message_count": len(messages),
        "response": payload,
    }
