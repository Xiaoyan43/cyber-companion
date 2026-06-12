from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

RtcMode = Literal["pure", "hybrid"]

ENV_RTC_APP_ID = "VOLC_RTC_APP_ID"
ENV_RTC_APP_KEY = "VOLC_RTC_APP_KEY"
ENV_ACCESS_KEY = "VOLC_ACCESS_KEY"
ENV_SECRET_KEY = "VOLC_SECRET_KEY"
ENV_RT_APP_ID = "DOUBAO_RT_APP_ID"
ENV_RT_ACCESS_TOKEN = "DOUBAO_RT_ACCESS_TOKEN"
ENV_RT_SPEAKER = "DOUBAO_RT_SPEAKER"
ENV_RT_MODEL = "DOUBAO_RT_MODEL"
ENV_RT_SERIES = "DOUBAO_RT_SERIES"
ENV_SOUL_PUBLIC_URL = "SOUL_LLM_PUBLIC_URL"
ENV_SOUL_API_KEY = "SOUL_LLM_API_KEY"
ENV_RTC_DEFAULT_USER_ID = "VOLC_RTC_DEFAULT_USER_ID"
ENV_VIKING_MEMORY_API_KEY = "VIKING_MEMORY_API_KEY"
ENV_VIKING_MEMORY_COLLECTION = "VIKING_MEMORY_COLLECTION"
ENV_VIKING_MEMORY_PROJECT = "VIKING_MEMORY_PROJECT"
ENV_VIKING_MEMORY_HOST = "VIKING_MEMORY_HOST"
ENV_VIKING_MEMORY_ASSISTANT_ID = "VIKING_MEMORY_ASSISTANT_ID"
ENV_VIKING_MEMORY_LIMIT = "VIKING_MEMORY_LIMIT"
ENV_VIKING_MEMORY_TRANSITION = "VIKING_MEMORY_TRANSITION_WORDS"
ENV_VIKING_MEMORY_TYPES = "VIKING_MEMORY_TYPES"

DEFAULT_RTC_USER_ID = "boxi_user"
DEFAULT_VIKING_MEMORY_PROJECT = "default"
DEFAULT_VIKING_MEMORY_HOST = "https://api-knowledgebase.mlp.cn-beijing.volces.com"
DEFAULT_VIKING_MEMORY_LIMIT = 3
DEFAULT_RT_SPEAKER = "zh_female_vv_jupiter_bigtts"
DEFAULT_RT_MODEL = "1.2.1.1"
DEFAULT_RT_SERIES = "o"
DEFAULT_WELCOME_PURE = "行吧，我又醒了。你想聊什么？"
DEFAULT_WELCOME_HYBRID = "行吧，Soul 模式。说点什么。"
DEFAULT_BOT_USER_PURE = "BoxiBot"
DEFAULT_BOT_USER_HYBRID = "BoxiHybridBot"
DEFAULT_TASK_PURE = "BoxiTask01"
DEFAULT_TASK_HYBRID = "BoxiHybridTask01"


@dataclass(frozen=True)
class RtcConfig:
    rtc_app_id: str
    rtc_app_key: str
    access_key: str
    secret_key: str
    rt_app_id: str
    rt_access_token: str
    rt_speaker: str
    rt_model: str
    rt_series: str
    soul_public_url: str
    soul_api_key: str
    welcome_pure: str
    welcome_hybrid: str
    bot_user_pure: str
    bot_user_hybrid: str
    task_pure: str
    task_hybrid: str
    default_user_id: str
    viking_memory_api_key: str
    viking_memory_collection: str
    viking_memory_project: str
    viking_memory_host: str
    viking_memory_assistant_id: str
    viking_memory_limit: int
    viking_memory_transition_words: str
    viking_memory_types: tuple[str, ...]
    # Off by default: twopass ASR can finalize the same utterance twice → double reply.
    enable_asr_twopass: bool
    # O2.0 singing — requires dialog.extra.enable_music (Volc S2S docs); on by default.
    enable_music: bool


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    return int(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_rt_series() -> str:
    raw = _env(ENV_RT_SERIES, DEFAULT_RT_SERIES).lower()
    return raw if raw in {"o", "sc"} else DEFAULT_RT_SERIES


def _env_csv(name: str) -> tuple[str, ...]:
    raw = _env(name)
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def load_rtc_config() -> RtcConfig:
    return RtcConfig(
        rtc_app_id=_env(ENV_RTC_APP_ID),
        rtc_app_key=_env(ENV_RTC_APP_KEY),
        access_key=_env(ENV_ACCESS_KEY),
        secret_key=_env(ENV_SECRET_KEY),
        rt_app_id=_env(ENV_RT_APP_ID),
        rt_access_token=_env(ENV_RT_ACCESS_TOKEN),
        rt_speaker=_env(ENV_RT_SPEAKER, DEFAULT_RT_SPEAKER),
        rt_model=_env(ENV_RT_MODEL, DEFAULT_RT_MODEL),
        rt_series=_env_rt_series(),
        soul_public_url=_env(ENV_SOUL_PUBLIC_URL),
        soul_api_key=_env(ENV_SOUL_API_KEY),
        welcome_pure=_env("VOLC_RTC_WELCOME_PURE", DEFAULT_WELCOME_PURE),
        welcome_hybrid=_env("VOLC_RTC_WELCOME_HYBRID", DEFAULT_WELCOME_HYBRID),
        bot_user_pure=_env("VOLC_RTC_BOT_USER_PURE", DEFAULT_BOT_USER_PURE),
        bot_user_hybrid=_env("VOLC_RTC_BOT_USER_HYBRID", DEFAULT_BOT_USER_HYBRID),
        task_pure=_env("VOLC_RTC_TASK_PURE", DEFAULT_TASK_PURE),
        task_hybrid=_env("VOLC_RTC_TASK_HYBRID", DEFAULT_TASK_HYBRID),
        default_user_id=_env(ENV_RTC_DEFAULT_USER_ID, DEFAULT_RTC_USER_ID),
        viking_memory_api_key=_env(ENV_VIKING_MEMORY_API_KEY),
        viking_memory_collection=_env(ENV_VIKING_MEMORY_COLLECTION),
        viking_memory_project=_env(ENV_VIKING_MEMORY_PROJECT, DEFAULT_VIKING_MEMORY_PROJECT),
        viking_memory_host=_env(ENV_VIKING_MEMORY_HOST, DEFAULT_VIKING_MEMORY_HOST),
        viking_memory_assistant_id=_env(ENV_VIKING_MEMORY_ASSISTANT_ID),
        viking_memory_limit=_env_int(ENV_VIKING_MEMORY_LIMIT, DEFAULT_VIKING_MEMORY_LIMIT),
        viking_memory_transition_words=_env(ENV_VIKING_MEMORY_TRANSITION),
        viking_memory_types=_env_csv(ENV_VIKING_MEMORY_TYPES),
        enable_asr_twopass=_env_bool("VOLC_RTC_ENABLE_ASR_TWOPASS", False),
        enable_music=_env_bool("DOUBAO_RT_ENABLE_MUSIC", True),
    )


def viking_memory_enabled(config: RtcConfig) -> bool:
    return bool(config.viking_memory_collection)


def viking_memory_write_ready(config: RtcConfig) -> bool:
    return bool(config.viking_memory_collection and config.viking_memory_api_key)


def resolve_rtc_user_id(explicit_user_id: str, config: RtcConfig) -> str:
    """Stable user id for Viking filter — avoid random UUID per session."""
    trimmed = explicit_user_id.strip()
    if trimmed:
        return trimmed
    return config.default_user_id or DEFAULT_RTC_USER_ID


def base_rtc_ready(config: RtcConfig) -> bool:
    return bool(
        config.rtc_app_id
        and config.rtc_app_key
        and config.access_key
        and config.secret_key
        and config.rt_app_id
        and config.rt_access_token
    )


def mode_ready(config: RtcConfig, mode: RtcMode) -> bool:
    if not base_rtc_ready(config):
        return False
    if mode == "hybrid":
        return bool(config.soul_public_url and config.soul_api_key)
    return True


def missing_for_mode(config: RtcConfig, mode: RtcMode) -> list[str]:
    missing: list[str] = []
    for name, value in (
        (ENV_RTC_APP_ID, config.rtc_app_id),
        (ENV_RTC_APP_KEY, config.rtc_app_key),
        (ENV_ACCESS_KEY, config.access_key),
        (ENV_SECRET_KEY, config.secret_key),
        (ENV_RT_APP_ID, config.rt_app_id),
        (ENV_RT_ACCESS_TOKEN, config.rt_access_token),
    ):
        if not value:
            missing.append(name)
    if mode == "hybrid":
        if not config.soul_public_url:
            missing.append(ENV_SOUL_PUBLIC_URL)
        if not config.soul_api_key:
            missing.append(ENV_SOUL_API_KEY)
    return missing
