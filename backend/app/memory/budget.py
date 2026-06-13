from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BudgetConfig:
    max_input_tokens_per_turn: int = 4000
    max_output_tokens_per_turn: int = 300
    max_user_input_tokens: int = 1500
    max_raw_turns: int = 4
    max_memories_per_turn: int = 6
    summary_batch_size: int = 6
    behavior_tick_retention: int = 200
    auto_memory_write: bool = True
    llm_memory_extraction: bool = True
    enable_reflection: bool = True
    reflection_every_n_turns: int = 6
    enable_turn_analyzer: bool = True
    analyze_every_n_turns: int = 1
    llm_summary: bool = True
    allow_cloud_stt: bool = False
    allow_cloud_tts: bool = False
    # Spend brakes. <= 0 disables the corresponding cap.
    monthly_usd_limit: float = 10.0
    daily_llm_turn_limit: int = 200
    allow_reasoning_model: bool = False
    # Proactive initiation (PI-1 longing model). Defaults are conservative / quiet.
    enable_proactive: bool = True
    proactive_quiet_hours: tuple[int, ...] = (23, 8)
    proactive_min_gap_minutes: int = 30
    proactive_min_fire_gap_hours: float = 6.0
    proactive_daily_max: int = 2
    longing_silence_hours_scale: float = 48.0
    longing_closeness_weight: float = 0.55
    longing_loneliness_weight: float = 0.45
    longing_lambda_base_per_hour: float = 0.004
    longing_lambda_longing_gain: float = 2.5
    proactive_llm: bool = True
    proactive_max_output_tokens: int = 80
    proactive_llm_daily_max: int = 5


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def load_budget_config(config_dir: Path | None = None) -> BudgetConfig:
    root = config_dir or _config_dir()
    budget_path = root / "budget.json"
    example_path = root / "budget.example.json"
    path = budget_path if budget_path.exists() else example_path

    if not path.exists():
        return BudgetConfig()

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return BudgetConfig(
        max_input_tokens_per_turn=int(payload.get("max_input_tokens_per_turn", 4000)),
        max_output_tokens_per_turn=int(payload.get("max_output_tokens_per_turn", 300)),
        max_user_input_tokens=int(payload.get("max_user_input_tokens", 1500)),
        max_raw_turns=int(payload.get("max_raw_turns", 4)),
        max_memories_per_turn=int(payload.get("max_memories_per_turn", 6)),
        summary_batch_size=int(payload.get("summary_batch_size", 6)),
        behavior_tick_retention=int(payload.get("behavior_tick_retention", 200)),
        auto_memory_write=bool(payload.get("auto_memory_write", True)),
        llm_memory_extraction=bool(payload.get("llm_memory_extraction", True)),
        enable_reflection=bool(payload.get("enable_reflection", True)),
        reflection_every_n_turns=int(payload.get("reflection_every_n_turns", 6)),
        enable_turn_analyzer=bool(payload.get("enable_turn_analyzer", True)),
        analyze_every_n_turns=int(payload.get("analyze_every_n_turns", 1)),
        llm_summary=bool(payload.get("llm_summary", True)),
        allow_cloud_stt=bool(payload.get("allow_cloud_stt", False)),
        allow_cloud_tts=bool(payload.get("allow_cloud_tts", False)),
        monthly_usd_limit=float(payload.get("monthly_usd_limit", 10.0)),
        daily_llm_turn_limit=int(payload.get("daily_llm_turn_limit", 200)),
        allow_reasoning_model=bool(payload.get("allow_reasoning_model", False)),
        enable_proactive=bool(payload.get("enable_proactive", True)),
        proactive_quiet_hours=_parse_quiet_hours(payload.get("proactive_quiet_hours")),
        proactive_min_gap_minutes=int(payload.get("proactive_min_gap_minutes", 30)),
        proactive_min_fire_gap_hours=float(payload.get("proactive_min_fire_gap_hours", 6.0)),
        proactive_daily_max=int(payload.get("proactive_daily_max", 2)),
        longing_silence_hours_scale=float(payload.get("longing_silence_hours_scale", 48.0)),
        longing_closeness_weight=float(payload.get("longing_closeness_weight", 0.55)),
        longing_loneliness_weight=float(payload.get("longing_loneliness_weight", 0.45)),
        longing_lambda_base_per_hour=float(payload.get("longing_lambda_base_per_hour", 0.004)),
        longing_lambda_longing_gain=float(payload.get("longing_lambda_longing_gain", 2.5)),
        proactive_llm=bool(payload.get("proactive_llm", True)),
        proactive_max_output_tokens=int(payload.get("proactive_max_output_tokens", 80)),
        proactive_llm_daily_max=int(payload.get("proactive_llm_daily_max", 5)),
    )


def _parse_quiet_hours(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, list) or len(raw) < 2:
        return (23, 8)
    try:
        return (int(raw[0]), int(raw[1]))
    except (TypeError, ValueError):
        return (23, 8)
