"""Build VoiceChat payloads for RTC AIGC StartVoiceChat — aligned with rtc-aigc-demo Boxi scenes."""

from __future__ import annotations

from typing import Any

from backend.app.memory.persona import (
    load_persona_name,
    load_rtc_character_manifest,
    load_rtc_system_role,
)
from backend.app.rtc.config import RtcConfig, RtcMode, viking_memory_enabled
from backend.app.rtc.state_block import build_rtc_speaking_style, build_rtc_speaking_style_modifier
from backend.app.rtc.viking_memory import (
    DEFAULT_MEMORY_TRANSITION,
    DEFAULT_RUNTIME_MEMORY_TYPES,
)

OUTPUT_MODE_PURE = 0
OUTPUT_MODE_HYBRID = 1


def _hybrid_speaking_style() -> str:
    from backend.app.memory.persona import load_rtc_speaking_style

    return load_rtc_speaking_style()


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


def _dialog_extra(config: RtcConfig) -> dict[str, Any]:
    extra: dict[str, Any] = {"model": config.rt_model}
    if config.enable_music:
        extra["enable_music"] = True
    return extra


def _merge_dialog_context(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _build_o2_pure_dialog(config: RtcConfig, memory_context: str) -> dict[str, Any]:
    system_role = load_rtc_system_role()
    if memory_context.strip():
        system_role = f"{system_role}\n\n{memory_context.strip()}"
    return {
        "bot_name": load_persona_name(),
        "speaking_style": build_rtc_speaking_style(),
        "system_role": system_role,
        "extra": _dialog_extra(config),
    }


def _build_sc_pure_dialog(config: RtcConfig, memory_context: str) -> dict[str, Any]:
    manifest_parts = [load_rtc_character_manifest()]
    if memory_context.strip():
        manifest_parts.append(memory_context.strip())
    stance = build_rtc_speaking_style_modifier()
    if stance:
        manifest_parts.append(stance)
    return {
        "character_manifest": _merge_dialog_context(*manifest_parts),
        "extra": {"model": config.rt_model},
    }


def _build_pure_dialog(config: RtcConfig, memory_context: str) -> dict[str, Any]:
    if config.rt_series == "sc":
        return _build_sc_pure_dialog(config, memory_context)
    return _build_o2_pure_dialog(config, memory_context)


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
                "dialog": (
                    _build_pure_dialog(config, memory_context)
                    if mode == "pure"
                    else {
                        "bot_name": load_persona_name(),
                        "speaking_style": _hybrid_speaking_style(),
                        "system_role": _merge_dialog_context(
                            load_rtc_system_role(),
                            memory_context,
                        ),
                        "extra": _dialog_extra(config),
                    }
                ),
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
    elif mode == "pure":
        voice_config["TTSConfig"] = {
            "Context": {
                "TagParse": True,
                "QuoteUserQuestion": True,
            },
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


def build_update_voice_chat_body(
    config: RtcConfig,
    *,
    mode: RtcMode,
    room_id: str,
    command: str,
    message: str = "",
) -> dict[str, str]:
    _, _, task_id, _ = mode_meta(config, mode)
    body: dict[str, str] = {
        "AppId": config.rtc_app_id,
        "RoomId": room_id,
        "TaskId": task_id,
        "Command": command,
    }
    if message:
        body["Message"] = message
    return body
