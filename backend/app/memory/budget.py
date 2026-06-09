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
    allow_cloud_stt: bool = False
    allow_cloud_tts: bool = False
    # Spend brakes. <= 0 disables the corresponding cap.
    monthly_usd_limit: float = 10.0
    daily_llm_turn_limit: int = 200
    allow_reasoning_model: bool = False


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
        allow_cloud_stt=bool(payload.get("allow_cloud_stt", False)),
        allow_cloud_tts=bool(payload.get("allow_cloud_tts", False)),
        monthly_usd_limit=float(payload.get("monthly_usd_limit", 10.0)),
        daily_llm_turn_limit=int(payload.get("daily_llm_turn_limit", 200)),
        allow_reasoning_model=bool(payload.get("allow_reasoning_model", False)),
    )
