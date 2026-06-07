from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderConfigEntry:
    name: str
    enabled: bool
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    placeholder: bool = False


@dataclass(frozen=True)
class ProvidersConfig:
    default_provider: str
    force_mock: bool
    providers: dict[str, ProviderConfigEntry]


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_providers_config(config_dir: Path | None = None) -> ProvidersConfig:
    root = config_dir or _config_dir()
    providers_path = root / "providers.json"
    example_path = root / "providers.example.json"

    if providers_path.exists():
        payload = _load_json(providers_path)
    elif example_path.exists():
        payload = _load_json(example_path)
    else:
        raise FileNotFoundError(
            f"Provider config not found in {root}. Expected providers.json or providers.example.json."
        )

    providers: dict[str, ProviderConfigEntry] = {}
    for name, entry in payload.get("providers", {}).items():
        providers[name] = ProviderConfigEntry(
            name=name,
            enabled=bool(entry.get("enabled", False)),
            model=str(entry.get("model", name)),
            base_url=entry.get("base_url"),
            api_key_env=entry.get("api_key_env"),
            placeholder=bool(entry.get("placeholder", False)),
        )

    if "mock" not in providers:
        providers["mock"] = ProviderConfigEntry(
            name="mock",
            enabled=True,
            model="mock-boxi",
            placeholder=False,
        )

    force_mock = os.getenv("CYBER_COMPANION_PROVIDER_MODE", "").strip().lower() == "mock"
    default_provider = "mock" if force_mock else str(payload.get("default_provider", "mock"))

    return ProvidersConfig(
        default_provider=default_provider,
        force_mock=force_mock,
        providers=providers,
    )
