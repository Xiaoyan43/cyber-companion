"""Build VoiceChat payloads for RTC AIGC StartVoiceChat — aligned with rtc-aigc-demo Boxi scenes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.app.rtc.config import RtcConfig, RtcMode, viking_memory_enabled
from backend.app.rtc.viking_memory import (
    DEFAULT_MEMORY_TRANSITION,
    DEFAULT_RUNTIME_MEMORY_TYPES,
)

OUTPUT_MODE_PURE = 0
OUTPUT_MODE_HYBRID = 1

# Match Server/scenes/Boxi.json (Stage 2a) — short Chinese persona, not full text-chat prompt.
PURE_SYSTEM_ROLE = (
    "你是 Boxi，一个被困在盒子里的毒舌小人，low-dose 陪伴型。用口语、简短回答，每次最多一两句。"
    "毒舌但不恶毒，别变成礼貌客服。用户 overwhelmed 时收一点刺；别侮辱用户价值。"
)
PURE_SPEAKING_STYLE = "毒舌但不恶毒，口语化，每次一两句"

HYBRID_SYSTEM_ROLE = (
    "你是 Boxi，一个被困在盒子里的毒舌小人。口语、简短，每次最多一两句。"
    "毒舌但不恶毒，别变成礼貌客服。"
)


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def load_persona_name() -> str:
    root = _config_dir()
    for name in ("persona.json", "persona.example.json"):
        path = root / name
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                persona = json.load(handle)
            return str(persona.get("name") or "Boxi")
    return "Boxi"


def build_memory_config(config: RtcConfig, *, target_user_id: str) -> dict[str, Any] | None:
    """Viking long-term memory for StartVoiceChat — see docs/V2_RTC_VIKING_MEMORY_SPEC.md."""
    if not viking_memory_enabled(config):
        return None

    filter_obj: dict[str, list[str]] = {"user_id": [target_user_id]}
    if config.viking_memory_assistant_id:
        filter_obj["assistant_id"] = [config.viking_memory_assistant_id]
    filter_obj["memory_type"] = (
        list(config.viking_memory_types)
        if config.viking_memory_types
        else list(DEFAULT_RUNTIME_MEMORY_TYPES)
    )

    provider_params: dict[str, Any] = {
        "collection_name": config.viking_memory_collection,
        "project_name": config.viking_memory_project,
        "limit": config.viking_memory_limit,
        "filter": filter_obj,
        "transition_words": config.viking_memory_transition_words or DEFAULT_MEMORY_TRANSITION,
    }

    return {
        "Enable": True,
        "Provider": "volc",
        "ProviderParams": provider_params,
    }


def mode_meta(config: RtcConfig, mode: RtcMode) -> tuple[int, str, str, str]:
    if mode == "hybrid":
        return (
            OUTPUT_MODE_HYBRID,
            config.bot_user_hybrid,
            config.task_hybrid,
            config.welcome_hybrid,
        )
    return (
        OUTPUT_MODE_PURE,
        config.bot_user_pure,
        config.task_pure,
        config.welcome_pure,
    )


def build_voice_chat_body(
    config: RtcConfig,
    *,
    mode: RtcMode,
    room_id: str,
    target_user_id: str,
    memory_context: str = "",
    welcome_message: str | None = None,
) -> dict[str, Any]:
    output_mode, bot_user_id, task_id, default_welcome = mode_meta(config, mode)
    resolved_welcome = welcome_message if welcome_message is not None else default_welcome
    system_role = HYBRID_SYSTEM_ROLE if mode == "hybrid" else PURE_SYSTEM_ROLE
    if memory_context.strip():
        system_role = f"{system_role}\n\n{memory_context.strip()}"
    speaking_style = PURE_SPEAKING_STYLE

    if mode == "pure":
        asr_extra: dict[str, Any] = {
            "end_smooth_window_ms": 1000,
            "enable_asr_twopass": config.enable_asr_twopass,
        }
    else:
        asr_extra = {"end_smooth_window_ms": 500}

    voice_config: dict[str, Any] = {
        "S2SConfig": {
            "OutputMode": output_mode,
            "Provider": "volcano",
            "ProviderParams": {
                "app": {
                    "appid": config.rt_app_id,
                    "token": config.rt_access_token,
                },
                "asr": {"extra": asr_extra},
                "tts": {"speaker": config.rt_speaker},
                "dialog": {
                    "bot_name": load_persona_name(),
                    "speaking_style": speaking_style,
                    "system_role": system_role,
                    "extra": {"model": config.rt_model},
                },
            },
        },
        "InterruptMode": 0,
    }

    if mode == "hybrid":
        voice_config["LLMConfig"] = {
            "Mode": "CustomLLM",
            "Url": config.soul_public_url,
            "APIKey": config.soul_api_key,
            "ModelName": "boxi-soul",
        }

    memory_config = build_memory_config(config, target_user_id=target_user_id)
    if memory_config is not None:
        voice_config["MemoryConfig"] = memory_config

    return {
        "AppId": config.rtc_app_id,
        "RoomId": room_id,
        "TaskId": task_id,
        "AgentConfig": {
            "TargetUserId": [target_user_id],
            "WelcomeMessage": resolved_welcome,
            "UserId": bot_user_id,
            "EnableConversationStateCallback": True,
        },
        "Config": voice_config,
    }


def build_stop_voice_chat_body(
    config: RtcConfig,
    *,
    mode: RtcMode,
    room_id: str,
) -> dict[str, str]:
    _, _, task_id, _ = mode_meta(config, mode)
    return {
        "AppId": config.rtc_app_id,
        "RoomId": room_id,
        "TaskId": task_id,
    }
