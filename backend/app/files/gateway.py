from __future__ import annotations

import os
from pathlib import Path

from backend.app.files.config import load_permissions_config
from backend.app.files.types import AllowedFolder, FileOperation, PathAccessResult, PermissionsConfig
from backend.app.memory.store import MemoryStore, get_memory_store


def _contains_parent_reference(path: Path) -> bool:
    return ".." in path.parts


def _absolute_lexical_path(path: Path) -> Path:
    if path.is_absolute():
        return Path(os.path.normpath(path))
    return Path(os.path.normpath(Path.cwd() / path))


def _is_within_root(resolved_path: Path, root: Path) -> bool:
    try:
        resolved_path.relative_to(root)
        return True
    except ValueError:
        return False


class FileAccessGateway:
    def __init__(
        self,
        config: PermissionsConfig,
        store: MemoryStore | None = None,
    ) -> None:
        self.config = config
        self.store = store

    def check_path(self, requested_path: str, operation: FileOperation) -> PathAccessResult:
        requested = requested_path.strip()
        if not requested:
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path="",
                    reason="Empty path is not allowed.",
                )
            )

        candidate = Path(requested).expanduser()
        if _contains_parent_reference(candidate):
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(candidate),
                    reason="Path traversal with '..' is not allowed.",
                )
            )

        try:
            lexical_path = _absolute_lexical_path(candidate)
        except OSError as error:
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(candidate),
                    reason=f"Unable to resolve path: {error}",
                )
            )

        if not self.config.allowed_folders:
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(lexical_path),
                    reason="No allowed folders are configured.",
                )
            )

        matched_folder: AllowedFolder | None = None
        for folder in self.config.allowed_folders:
            folder_root = folder.root.resolve()
            if _is_within_root(lexical_path, folder_root):
                matched_folder = folder
                break

        if matched_folder is None:
            try:
                resolved_preview = str(candidate.resolve(strict=False))
            except OSError:
                resolved_preview = str(lexical_path)
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=resolved_preview,
                    reason="Path is outside all allowed folders.",
                )
            )

        permission_ok = matched_folder.read if operation == "read" else matched_folder.write
        if not permission_ok:
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(lexical_path),
                    reason=f"{operation.capitalize()} access is not allowed for this folder.",
                    matched_folder=matched_folder.raw_path,
                )
            )

        real_root = matched_folder.root.resolve()
        try:
            real_target = Path(os.path.realpath(lexical_path))
        except OSError as error:
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(lexical_path),
                    reason=f"Unable to resolve real path: {error}",
                    matched_folder=matched_folder.raw_path,
                )
            )
        if not _is_within_root(real_target, real_root):
            return self._finalize(
                PathAccessResult(
                    allowed=False,
                    operation=operation,
                    requested_path=requested_path,
                    resolved_path=str(real_target),
                    reason="Symlink escape outside the allowed folder is not permitted.",
                    matched_folder=matched_folder.raw_path,
                )
            )

        return self._finalize(
            PathAccessResult(
                allowed=True,
                operation=operation,
                requested_path=requested_path,
                resolved_path=str(real_target),
                reason="Allowed.",
                matched_folder=matched_folder.raw_path,
            )
        )

    def _finalize(self, result: PathAccessResult) -> PathAccessResult:
        if self.store is not None and self.config.log_file_access:
            self.store.log_file_access(
                operation=result.operation,
                requested_path=result.requested_path,
                resolved_path=result.resolved_path,
                allowed=result.allowed,
                reason=result.reason,
            )
        return result


_gateway: FileAccessGateway | None = None


def get_file_gateway() -> FileAccessGateway:
    global _gateway
    if _gateway is None:
        _gateway = FileAccessGateway(load_permissions_config(), get_memory_store())
    return _gateway


def reset_file_gateway() -> None:
    global _gateway
    _gateway = None
