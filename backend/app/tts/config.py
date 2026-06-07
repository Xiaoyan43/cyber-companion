from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TTSProviderConfigEntry:
    name: str
    enabled: bool
    model: str
    voice: str | None = None
    api_key_env: str | None = None
    placeholder: bool = False
    cloud: bool = False


@dataclass(frozen=True)
class TTSConfig:
    enabled: bool
    default_provider: str
    force_mock: bool
    max_speech_chars: int
    speak_decisions: tuple[str, ...]
    providers: dict[str, TTSProviderConfigEntry]


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_tts_config(config_dir: Path | None = None) -> TTSConfig:
    root = config_dir or _config_dir()
    tts_path = root / "tts.json"
    example_path = root / "tts.example.json"

    if tts_path.exists():
        payload = _load_json(tts_path)
    elif example_path.exists():
        payload = _load_json(example_path)
    else:
        return TTSConfig(
            enabled=False,
            default_provider="mock",
            force_mock=True,
            max_speech_chars=120,
            speak_decisions=("proactive", "interrupt", "refuse", "reply"),
            providers={
                "mock": TTSProviderConfigEntry(
                    name="mock",
                    enabled=True,
                    model="mock-tts",
                )
            },
        )

    providers: dict[str, TTSProviderConfigEntry] = {}
    for name, entry in payload.get("providers", {}).items():
        providers[name] = TTSProviderConfigEntry(
            name=name,
            enabled=bool(entry.get("enabled", False)),
            model=str(entry.get("model", name)),
            voice=entry.get("voice"),
            api_key_env=entry.get("api_key_env"),
            placeholder=bool(entry.get("placeholder", False)),
            cloud=bool(entry.get("cloud", name != "mock")),
        )

    if "mock" not in providers:
        providers["mock"] = TTSProviderConfigEntry(
            name="mock",
            enabled=True,
            model="mock-tts",
            cloud=False,
        )

    force_mock = os.getenv("CYBER_COMPANION_TTS_MODE", "").strip().lower() == "mock"
    default_provider = "mock" if force_mock else str(payload.get("default_provider", "mock"))
    speak_decisions = tuple(
        str(item) for item in payload.get("speak_decisions", ["proactive", "interrupt", "refuse", "reply"])
    )

    return TTSConfig(
        enabled=bool(payload.get("enabled", False)),
        default_provider=default_provider,
        force_mock=force_mock,
        max_speech_chars=int(payload.get("max_speech_chars", 120)),
        speak_decisions=speak_decisions,
        providers=providers,
    )
