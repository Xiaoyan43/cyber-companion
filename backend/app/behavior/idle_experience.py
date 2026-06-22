from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MemoryRecord, MoodStateRecord
from backend.app.memory.persona import load_chinese_persona_prompt
from backend.app.memory.store import MemoryStore
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatMessage

_IDLE_EXPERIENCE_INSTRUCTION = (
    "[Idle experience task]\n"
    "You are Boxi, alone in the box, briefly noticing something on your own — "
    "NOT talking to the user, just a private moment to remember later.\n"
    "Below is the ONLY real material you may reference. Stay strictly within it: "
    "do not invent plot details, facts, names, or events beyond what is given.\n"
    "Write 1-2 short sentences in Chinese, first person, in Boxi's voice — a small "
    "reaction or thought, not a summary or review.\n"
    "Output ONLY the line(s). No JSON, no quotes, no stage directions."
)

_LAST_AT_KEY = "idle_experience_last_at"
_DAILY_DATE_KEY = "idle_experience_daily_date"
_DAILY_COUNT_KEY = "idle_experience_daily_count"
_FINGERPRINT_KEY = "idle_experience_recent_material_ids"


def _aware_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def load_material_pool(config_dir: Path | None = None) -> list[dict[str, Any]]:
    root = config_dir or _config_dir()
    real_path = root / "idle_material_pool.json"
    example_path = root / "idle_material_pool.example.json"
    path = real_path if real_path.exists() else example_path
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    items = payload.get("items")
    return list(items) if isinstance(items, list) else []


def _daily_count_today(metadata: dict[str, object], *, now: datetime) -> int:
    today = now.date().isoformat()
    if metadata.get(_DAILY_DATE_KEY) != today:
        return 0
    raw = metadata.get(_DAILY_COUNT_KEY, 0)
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _hours_since_last(metadata: dict[str, object], *, now: datetime) -> float | None:
    raw = metadata.get(_LAST_AT_KEY)
    if not isinstance(raw, str) or not raw:
        return None
    try:
        last = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    delta = now.astimezone(timezone.utc) - last.astimezone(timezone.utc)
    return delta.total_seconds() / 3600.0


def idle_experience_allowed(
    budget: BudgetConfig,
    mood: MoodStateRecord,
    *,
    now: datetime | None = None,
) -> bool:
    if not budget.idle_experience_enabled:
        return False
    aware = _aware_now(now)
    daily_max = max(0, budget.idle_experience_daily_max)
    if daily_max <= 0:
        return False
    if _daily_count_today(mood.metadata, now=aware) >= daily_max:
        return False
    hours_since = _hours_since_last(mood.metadata, now=aware)
    if hours_since is not None and hours_since < budget.idle_experience_min_gap_hours:
        return False
    return True


def mark_idle_experience_used(metadata: dict[str, object], *, now: datetime) -> dict[str, object]:
    updated = dict(metadata)
    today = now.date().isoformat()
    if updated.get(_DAILY_DATE_KEY) != today:
        updated[_DAILY_DATE_KEY] = today
        updated[_DAILY_COUNT_KEY] = 1
    else:
        updated[_DAILY_COUNT_KEY] = _daily_count_today(updated, now=now) + 1
    updated[_LAST_AT_KEY] = now.astimezone(timezone.utc).isoformat()
    return updated


def record_material_fingerprint(
    metadata: dict[str, object],
    material_id: str,
    *,
    max_size: int,
) -> dict[str, object]:
    updated = dict(metadata)
    history = updated.get(_FINGERPRINT_KEY)
    history_list = list(history) if isinstance(history, list) else []
    history_list.append(material_id)
    cap = max(1, max_size)
    updated[_FINGERPRINT_KEY] = history_list[-cap:]
    return updated


def pick_material(
    pool: list[dict[str, Any]],
    metadata: dict[str, object],
    *,
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    if not pool:
        return None
    history = metadata.get(_FINGERPRINT_KEY)
    recent_ids = set(history) if isinstance(history, list) else set()
    candidates = [item for item in pool if item.get("id") not in recent_ids]
    if not candidates:
        candidates = pool
    chooser = rng or random
    return chooser.choice(candidates)


def build_idle_experience_messages(material: dict[str, Any]) -> list[ChatMessage]:
    persona = load_chinese_persona_prompt()
    material_block = (
        "[Real material]\n"
        f"kind: {material.get('kind', '')}\n"
        f"title: {material.get('title', '')}\n"
        f"summary: {material.get('summary', '')}"
    )
    system_content = "\n\n".join([persona, material_block, _IDLE_EXPERIENCE_INSTRUCTION])
    user_content = "[Notice this on your own, write your private reaction now.]"
    return [
        ChatMessage(role="system", content=system_content),
        ChatMessage(role="user", content=user_content),
    ]


def _sanitize_experience_line(raw: str) -> str:
    line = raw.strip().strip('"').strip("'").strip("「」")
    if not line:
        return ""
    if len(line) > 200:
        line = line[:200].rstrip()
    return line


def _pick_idle_experience_provider(router: ProviderRouter, provider_name: str | None) -> str:
    if provider_name:
        return provider_name
    preferred = router.resolve_provider_name(None)
    if preferred == "mock":
        return "mock"
    try:
        status = router.get_provider(preferred).status()
        if status.configured and status.api_key_present and not status.placeholder:
            return preferred
    except ProviderError:
        pass
    return "mock"


def resolve_idle_experience_write(
    store: MemoryStore,
    *,
    budget: BudgetConfig,
    router: ProviderRouter,
    provider_name: str | None = None,
    now: datetime | None = None,
) -> MemoryRecord | None:
    """Route-layer orchestration: low-frequency, anti-fabrication idle memory write.

    Mirrors resolve_proactive_opener's failure-swallowing shape, but never sends a
    message — this only writes a memory for later `share` intent recall (P9-P2-B).
    """
    aware = _aware_now(now)
    mood = store.get_mood_state()

    if not idle_experience_allowed(budget, mood, now=aware):
        return None

    pool = load_material_pool()
    material = pick_material(pool, mood.metadata)
    if material is None:
        return None

    messages = build_idle_experience_messages(material)
    request = ChatCompletionRequest(
        messages=messages,
        max_output_tokens=max(32, budget.idle_experience_max_output_tokens),
    )
    resolved_provider = _pick_idle_experience_provider(router, provider_name)

    try:
        result = router.complete(request, provider_name=resolved_provider)
    except Exception:
        return None

    line = _sanitize_experience_line(result.content)
    if not line:
        return None

    memory = store.create_memory(
        type="idle_experience",
        content=line,
        importance=0.4,
        confidence=0.6,
        metadata={
            "writer": "idle_experience",
            "source_pool_id": material.get("id"),
            "source_kind": material.get("kind"),
        },
    )

    updated_metadata = mark_idle_experience_used(mood.metadata, now=aware)
    updated_metadata = record_material_fingerprint(
        updated_metadata,
        str(material.get("id")),
        max_size=budget.idle_experience_fingerprint_history_size,
    )
    store.update_mood_state(metadata=updated_metadata)
    return memory
