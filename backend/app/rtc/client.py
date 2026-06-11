"""Signed calls to rtc.volcengineapi.com StartVoiceChat / StopVoiceChat."""

from __future__ import annotations

import json
from typing import Any

import httpx

from backend.app.rtc.config import RtcConfig, RtcMode
from backend.app.rtc.signer import sign_rtc_openapi_request
from backend.app.rtc.voice_chat import build_stop_voice_chat_body, build_voice_chat_body

RTC_HOST = "rtc.volcengineapi.com"
RTC_API_VERSION = "2024-12-01"


class RtcApiError(Exception):
    def __init__(self, message: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def _call_openapi(
    config: RtcConfig,
    *,
    action: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    query = {"Action": action, "Version": RTC_API_VERSION}
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    headers = sign_rtc_openapi_request(
        access_key=config.access_key,
        secret_key=config.secret_key,
        method="POST",
        host=RTC_HOST,
        path="/",
        query=query,
        body=payload,
    )
    url = f"https://{RTC_HOST}/?Action={action}&Version={RTC_API_VERSION}"
    response = httpx.post(url, headers=headers, content=payload.encode("utf-8"), timeout=30.0)
    try:
        data = response.json()
    except json.JSONDecodeError as error:
        raise RtcApiError(
            f"RTC OpenAPI returned non-JSON (HTTP {response.status_code})",
        ) from error

    metadata = data.get("ResponseMetadata") or {}
    error_info = metadata.get("Error")
    if error_info:
        raise RtcApiError(
            str(error_info.get("Message") or error_info),
            payload=data,
        )
    if response.status_code >= 400:
        raise RtcApiError(f"RTC OpenAPI HTTP {response.status_code}", payload=data)
    return data


def start_voice_chat(
    config: RtcConfig,
    *,
    mode: RtcMode,
    room_id: str,
    target_user_id: str,
    memory_context: str = "",
    welcome_message: str | None = None,
) -> dict[str, Any]:
    body = build_voice_chat_body(
        config,
        mode=mode,
        room_id=room_id,
        target_user_id=target_user_id,
        memory_context=memory_context,
        welcome_message=welcome_message,
    )
    return _call_openapi(config, action="StartVoiceChat", body=body)


def stop_voice_chat(
    config: RtcConfig,
    *,
    mode: RtcMode,
    room_id: str,
) -> dict[str, Any]:
    body = build_stop_voice_chat_body(config, mode=mode, room_id=room_id)
    return _call_openapi(config, action="StopVoiceChat", body=body)
