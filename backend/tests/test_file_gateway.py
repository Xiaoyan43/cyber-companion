from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.files.config import load_permissions_config
from backend.app.files.gateway import FileAccessGateway, reset_file_gateway
from backend.app.files.types import PermissionsConfig
from backend.app.main import app
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.providers.router import reset_provider_router


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    reset_file_gateway()
    yield
    reset_provider_router()
    reset_memory_store()
    reset_file_gateway()


@pytest.fixture
def sandbox_layout(tmp_path: Path) -> dict[str, Path]:
    config_dir = tmp_path / "config"
    sandbox = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    config_dir.mkdir()
    sandbox.mkdir()
    outside.mkdir()
    secret = sandbox / "notes.txt"
    secret.write_text("inside", encoding="utf-8")
    leaked = outside / "leaked.txt"
    leaked.write_text("outside", encoding="utf-8")
    escape_link = sandbox / "escape"
    escape_link.symlink_to(leaked)
    return {
        "config_dir": config_dir,
        "sandbox": sandbox,
        "outside": outside,
        "secret": secret,
        "leaked": leaked,
        "escape_link": escape_link,
    }


def _write_permissions(config_dir: Path, sandbox: Path, *, log_file_access: bool = True) -> None:
    payload = {
        "allowed_folders": [
            {
                "path": str(sandbox),
                "read": True,
                "write": True,
            }
        ],
        "deny_shell_execution": True,
        "log_file_access": log_file_access,
    }
    (config_dir / "permissions.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def gateway(sandbox_layout: dict[str, Path], tmp_path: Path) -> FileAccessGateway:
    _write_permissions(sandbox_layout["config_dir"], sandbox_layout["sandbox"])
    config = load_permissions_config(sandbox_layout["config_dir"])
    store = MemoryStore(db_path=tmp_path / "memory.db")
    return FileAccessGateway(config, store)


def test_allowed_read_inside_sandbox(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    result = gateway.check_path(str(sandbox_layout["secret"]), "read")

    assert result.allowed is True
    assert result.reason == "Allowed."
    assert result.matched_folder == str(sandbox_layout["sandbox"])


def test_allowed_write_inside_sandbox(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    target = sandbox_layout["sandbox"] / "new.txt"
    result = gateway.check_path(str(target), "write")

    assert result.allowed is True
    assert result.operation == "write"


def test_denies_path_outside_allowed_folder(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    result = gateway.check_path(str(sandbox_layout["leaked"]), "read")

    assert result.allowed is False
    assert "outside all allowed folders" in result.reason


def test_denies_parent_traversal(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    traversal = sandbox_layout["sandbox"] / ".." / "outside" / "leaked.txt"
    result = gateway.check_path(str(traversal), "read")

    assert result.allowed is False
    assert ".." in result.reason


def test_denies_symlink_escape(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    result = gateway.check_path(str(sandbox_layout["escape_link"]), "read")

    assert result.allowed is False
    assert "Symlink escape" in result.reason


def test_denies_operation_without_permission(
    sandbox_layout: dict[str, Path],
    tmp_path: Path,
) -> None:
    payload = {
        "allowed_folders": [
            {
                "path": str(sandbox_layout["sandbox"]),
                "read": True,
                "write": False,
            }
        ],
        "deny_shell_execution": True,
        "log_file_access": False,
    }
    (sandbox_layout["config_dir"] / "permissions.json").write_text(json.dumps(payload), encoding="utf-8")
    config = load_permissions_config(sandbox_layout["config_dir"])
    gateway = FileAccessGateway(config, MemoryStore(db_path=tmp_path / "memory.db"))

    result = gateway.check_path(str(sandbox_layout["secret"]), "write")

    assert result.allowed is False
    assert "Write access is not allowed" in result.reason


def test_logs_allowed_and_denied_attempts(gateway: FileAccessGateway, sandbox_layout: dict[str, Path]) -> None:
    assert gateway.store is not None

    gateway.check_path(str(sandbox_layout["secret"]), "read")
    gateway.check_path(str(sandbox_layout["leaked"]), "read")

    logs = gateway.store.list_file_access_logs(limit=10)
    assert len(logs) == 2
    assert logs[0].allowed is True
    assert logs[1].allowed is False


def test_denies_when_no_allowed_folders_configured(tmp_path: Path) -> None:
    config = PermissionsConfig(allowed_folders=(), deny_shell_execution=True, log_file_access=False)
    gateway = FileAccessGateway(config, MemoryStore(db_path=tmp_path / "memory.db"))

    result = gateway.check_path(str(tmp_path / "anything.txt"), "read")

    assert result.allowed is False
    assert "No allowed folders" in result.reason


@pytest.fixture
def client(sandbox_layout: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _write_permissions(sandbox_layout["config_dir"], sandbox_layout["sandbox"])
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(sandbox_layout["config_dir"]))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    return TestClient(app)


def test_permissions_status_route(client: TestClient, sandbox_layout: dict[str, Path]) -> None:
    response = client.get("/files/permissions/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deny_shell_execution"] is True
    assert payload["log_file_access"] is True
    assert len(payload["allowed_folders"]) == 1
    assert payload["allowed_folders"][0]["path"] == str(sandbox_layout["sandbox"])


def test_check_route_allows_sandbox_path(client: TestClient, sandbox_layout: dict[str, Path]) -> None:
    response = client.post(
        "/files/check",
        json={"path": str(sandbox_layout["secret"]), "operation": "read"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["allowed"] is True
    assert payload["reason"] == "Allowed."


def test_check_route_denies_symlink_escape(client: TestClient, sandbox_layout: dict[str, Path]) -> None:
    response = client.post(
        "/files/check",
        json={"path": str(sandbox_layout["escape_link"]), "operation": "read"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["allowed"] is False
    assert "Symlink escape" in payload["reason"]


def test_access_log_route(client: TestClient, sandbox_layout: dict[str, Path]) -> None:
    client.post("/files/check", json={"path": str(sandbox_layout["secret"]), "operation": "read"})
    client.post("/files/check", json={"path": str(sandbox_layout["leaked"]), "operation": "read"})

    response = client.get("/files/access-log")

    assert response.status_code == 200
    logs = response.json()["logs"]
    assert len(logs) == 2
    assert logs[0]["allowed"] is True
    assert logs[1]["allowed"] is False
