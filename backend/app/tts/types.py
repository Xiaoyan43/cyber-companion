from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    decision: str | None = None
    avatar_state: str | None = None
    force: bool = False


@dataclass(frozen=True)
class SynthesisResult:
    provider: str
    model: str
    audio_bytes: bytes
    mime_type: str
    duration_ms: int
    mock: bool = False


@dataclass(frozen=True)
class TTSProviderStatus:
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False
    cloud: bool = False


@dataclass(frozen=True)
class SpeechPolicyDecision:
    should_speak: bool
    reason: str
