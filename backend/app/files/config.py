from __future__ import annotations

import json
import os
from pathlib import Path

from backend.app.files.types import AllowedFolder, PermissionsConfig


def _config_dir() -> Path:
    configured = os.getenv("CYBER_COMPANION_CONFIG_DIR", "./config")
    return Path(configured).expanduser().resolve()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_folder_path(raw_path: str, config_dir: Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (config_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def load_permissions_config(config_dir: Path | None = None) -> PermissionsConfig:
    root = config_dir or _config_dir()
    permissions_path = root / "permissions.json"
    example_path = root / "permissions.example.json"

    if permissions_path.exists():
        payload = _load_json(permissions_path)
    elif example_path.exists():
        payload = _load_json(example_path)
    else:
        return PermissionsConfig(
            allowed_folders=(),
            deny_shell_execution=True,
            log_file_access=True,
        )

    allowed_folders: list[AllowedFolder] = []
    for entry in payload.get("allowed_folders", []):
        raw_path = str(entry.get("path", "")).strip()
        if not raw_path:
            continue
        allowed_folders.append(
            AllowedFolder(
                raw_path=raw_path,
                root=_resolve_folder_path(raw_path, root),
                read=bool(entry.get("read", False)),
                write=bool(entry.get("write", False)),
            )
        )

    return PermissionsConfig(
        allowed_folders=tuple(allowed_folders),
        deny_shell_execution=bool(payload.get("deny_shell_execution", True)),
        log_file_access=bool(payload.get("log_file_access", True)),
    )
