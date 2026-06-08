import pytest
from fastapi.testclient import TestClient

from backend.app.cors import load_cors_origins
from backend.app.main import app


def test_load_cors_origins_includes_default_dev_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CYBER_COMPANION_CORS_ORIGINS", raising=False)

    origins = load_cors_origins()

    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5174" in origins
    assert "http://localhost:5174" in origins


def test_load_cors_origins_merges_env_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CYBER_COMPANION_CORS_ORIGINS",
        "http://127.0.0.1:3000,http://127.0.0.1:5173",
    )

    origins = load_cors_origins()

    assert origins.count("http://127.0.0.1:5173") == 1
    assert "http://127.0.0.1:3000" in origins


def test_load_cors_origins_rejects_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CYBER_COMPANION_CORS_ORIGINS", "http://127.0.0.1:*")

    with pytest.raises(ValueError, match="Wildcard"):
        load_cors_origins()


def test_cors_allows_default_frontend_port() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_allows_alternate_frontend_port() -> None:
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5174"


def test_cors_blocks_unknown_origin() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://evil.example"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
