from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_bytes: bytes
    mime_type: str
    language: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    provider: str
    model: str
    text: str
    mock: bool = False
    language: str | None = None


@dataclass(frozen=True)
class STTProviderStatus:
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False
    cloud: bool = False
