from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "cyber-companion-api",
        "version": "0.1.0",
    }
