from dataclasses import dataclass, field
from typing import Any, Literal

BehaviorDecisionType = Literal[
    "reply",
    "silent",
    "mutter",
    "refuse",
    "interrupt",
    "proactive",
    "observe",
]

ToneMode = Literal["normal", "comfort", "tease"]
BehaviorEventType = Literal["user_message", "idle_tick", "app_tick", "proactive_check"]


@dataclass(frozen=True)
class BehaviorEvent:
    event_type: BehaviorEventType
    user_input: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BehaviorDecision:
    decision: BehaviorDecisionType
    avatar_state: str
    should_call_llm: bool
    reason: str
    local_response: str | None = None
    tone_mode: ToneMode = "normal"
