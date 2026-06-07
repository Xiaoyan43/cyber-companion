from __future__ import annotations

from backend.app.tts.types import SpeechPolicyDecision

_SKIP_DECISIONS = {"silent", "mutter", "observe"}
_SKIP_AVATAR_STATES = {"silent", "muted"}
_ALWAYS_SPEAK_DECISIONS = {"proactive", "interrupt", "refuse"}


def evaluate_speech_policy(
    text: str,
    *,
    decision: str | None = None,
    avatar_state: str | None = None,
    max_speech_chars: int = 120,
    speak_decisions: tuple[str, ...] | None = None,
    force: bool = False,
) -> SpeechPolicyDecision:
    if force:
        if not text.strip():
            return SpeechPolicyDecision(False, "empty text")
        return SpeechPolicyDecision(True, "forced")

    normalized = text.strip()
    if not normalized:
        return SpeechPolicyDecision(False, "empty text")

    if avatar_state in _SKIP_AVATAR_STATES:
        return SpeechPolicyDecision(False, f"avatar state `{avatar_state}`")

    if decision in _SKIP_DECISIONS:
        return SpeechPolicyDecision(False, f"decision `{decision}`")

    allowed = set(speak_decisions or ("proactive", "interrupt", "refuse", "reply"))
    if decision and decision not in allowed:
        return SpeechPolicyDecision(False, f"decision `{decision}` not in speak list")

    if decision in _ALWAYS_SPEAK_DECISIONS and len(normalized) <= max_speech_chars:
        return SpeechPolicyDecision(True, f"selective `{decision}` line")

    if len(normalized) > max_speech_chars:
        return SpeechPolicyDecision(False, "text too long for selective TTS")

    return SpeechPolicyDecision(True, "short reply")
