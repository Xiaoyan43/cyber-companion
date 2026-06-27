from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TYPE_CHECKING

from backend.app.behavior.longing import LongingSnapshot
from backend.app.behavior.proactive_reason import (
    LongingTier,
    ProactiveReason,
    check_in_proactive_reason,
    pick_agenda_proactive_reason,
    pick_proactive_reason,
)
from backend.app.memory.budget import BudgetConfig

if TYPE_CHECKING:
    from backend.app.memory.store import MemoryStore

ProactiveReasonMode = Literal["agenda", "longing_only"]


@dataclass(frozen=True)
class ProactiveMotivation:
    """Why a proactive check might fire (agenda) vs when (longing/Poisson rhythm gate)."""

    reason: ProactiveReason | None
    mode: ProactiveReasonMode


def resolve_proactive_motivation(
    store: MemoryStore,
    *,
    budget: BudgetConfig,
    longing: LongingSnapshot,
    longing_tier: LongingTier,
    now: datetime,
    force_proactive: bool = False,
) -> ProactiveMotivation:
    """Resolve proactive *why* from agenda/motivation policy.

    - ``agenda`` (default): due/overdue open loops and other substantive reasons;
      longing alone does not produce a reason.
    - ``longing_only`` (rollback): legacy path — always yields a reason via check-in
      fallback when no agenda item exists.
    - ``force_proactive``: dev/smoke escape hatch — uses check-in when agenda is empty.
    """
    mode = budget.proactive_reason_mode

    if mode == "longing_only":
        reason = pick_proactive_reason(
            store,
            longing_intensity=longing.intensity,
            longing_tier=longing_tier,
            now=now,
        )
        return ProactiveMotivation(reason=reason, mode=mode)

    reason = pick_agenda_proactive_reason(store, longing_tier=longing_tier, now=now)
    if reason is None and force_proactive:
        reason = check_in_proactive_reason(
            longing_intensity=longing.intensity,
            longing_tier=longing_tier,
        )
    return ProactiveMotivation(reason=reason, mode=mode)
