from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

FileOperation = Literal["read", "write"]


@dataclass(frozen=True)
class AllowedFolder:
    raw_path: str
    root: Path
    read: bool
    write: bool


@dataclass(frozen=True)
class PermissionsConfig:
    allowed_folders: tuple[AllowedFolder, ...]
    deny_shell_execution: bool
    log_file_access: bool


@dataclass(frozen=True)
class PathAccessResult:
    allowed: bool
    operation: FileOperation
    requested_path: str
    resolved_path: str
    reason: str
    matched_folder: str | None = None
