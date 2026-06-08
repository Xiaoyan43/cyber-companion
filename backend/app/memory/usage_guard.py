from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore

# Substrings that mark a model as a (pricier) reasoning model. Conservative on
# purpose: only block when the configured model clearly looks like one.
_REASONING_MODEL_MARKERS = ("reason", "thinking", "o1-", "-o1", "o3-", "-o3")


def is_reasoning_model(model: str) -> bool:
    lowered = model.lower()
    return any(marker in lowered for marker in _REASONING_MODEL_MARKERS)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _day_start_str(now: datetime) -> str:
    return now.strftime("%Y-%m-%d 00:00:00")


def _month_start_str(now: datetime) -> str:
    return now.strftime("%Y-%m-01 00:00:00")


@dataclass(frozen=True)
class BudgetGate:
    allowed: bool
    blocked_by: str | None = None  # "reasoning_model" | "daily_turns" | "monthly_usd"
    block_line: str | None = None


def evaluate_llm_budget_gate(
    store: MemoryStore,
    budget: BudgetConfig,
    *,
    target_model: str,
    now: datetime | None = None,
) -> BudgetGate:
    """Decide whether an LLM call is allowed under the configured spend brakes.

    Returns a non-allowed gate with an in-character `block_line` when a cap is
    hit, so the caller can answer locally without ever touching the provider.
    """
    if not budget.allow_reasoning_model and is_reasoning_model(target_model):
        return BudgetGate(
            allowed=False,
            blocked_by="reasoning_model",
            block_line=(
                f"reasoning 模型（{target_model}）这个月没给你开。"
                "用普通模型，或者去 budget.json 把 allow_reasoning_model 打开。"
            ),
        )

    moment = now or _utc_now()

    if budget.daily_llm_turn_limit > 0:
        daily_turns = store.count_llm_turns_since(_day_start_str(moment))
        if daily_turns >= budget.daily_llm_turn_limit:
            return BudgetGate(
                allowed=False,
                blocked_by="daily_turns",
                block_line=(
                    f"今天的对话额度（{budget.daily_llm_turn_limit} 次）用完了。"
                    "我也要喘口气。明天再来，或者改 budget.json。"
                ),
            )

    if budget.monthly_usd_limit > 0:
        month_cost = store.sum_llm_cost_since(_month_start_str(moment))
        if month_cost >= budget.monthly_usd_limit:
            return BudgetGate(
                allowed=False,
                blocked_by="monthly_usd",
                block_line=(
                    f"这个月的预算（${budget.monthly_usd_limit:.2f}）被你榨干了，"
                    f"已经烧掉约 ${month_cost:.4f}。省着点，今天先用自己的脑子。"
                ),
            )

    return BudgetGate(allowed=True)
