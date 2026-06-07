from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class STTProviderConfigEntry:
    name: str
    enabled: bool
    model: str
    api_key_env: str | None = None
    placeholder: bool = False
    cloud: bool = False


@dataclass(frozen=True)
class STTConfig:
    enabled: bool
    default_provider: str
    force_mock: bool
    providers: dict[str, STTProviderConfigEntry]


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_stt_config(config_dir: Path | None = None) -> STTConfig:
    root = config_dir or _config_dir()
    stt_path = root / "stt.json"
    example_path = root / "stt.example.json"

    if stt_path.exists():
        payload = _load_json(stt_path)
    elif example_path.exists():
        payload = _load_json(example_path)
    else:
        return STTConfig(
            enabled=False,
            default_provider="mock",
            force_mock=True,
            providers={
                "mock": STTProviderConfigEntry(
                    name="mock",
                    enabled=True,
                    model="mock-stt",
                )
            },
        )

    providers: dict[str, STTProviderConfigEntry] = {}
    for name, entry in payload.get("providers", {}).items():
        providers[name] = STTProviderConfigEntry(
            name=name,
            enabled=bool(entry.get("enabled", False)),
            model=str(entry.get("model", name)),
            api_key_env=entry.get("api_key_env"),
            placeholder=bool(entry.get("placeholder", False)),
            cloud=bool(entry.get("cloud", name != "mock")),
        )

    if "mock" not in providers:
        providers["mock"] = STTProviderConfigEntry(
            name="mock",
            enabled=True,
            model="mock-stt",
            cloud=False,
        )

    force_mock = os.getenv("CYBER_COMPANION_STT_MODE", "").strip().lower() == "mock"
    default_provider = "mock" if force_mock else str(payload.get("default_provider", "mock"))

    return STTConfig(
        enabled=bool(payload.get("enabled", False)),
        default_provider=default_provider,
        force_mock=force_mock,
        providers=providers,
    )
