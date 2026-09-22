import pytest
from fastapi.testclient import TestClient

import app.api.v1.health as health_module
from app.main import app


def test_live_is_always_ok() -> None:
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_ready_is_200_when_db_up() -> None:
    response = TestClient(app).get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok", "db": "up"}


def test_ready_is_503_when_db_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_module, "check_db", lambda: "down")
    response = TestClient(app).get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_detailed_reports_deps_and_app() -> None:
    response = TestClient(app).get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["db"] in ("up", "down")
    assert data["redis"] in ("up", "down")
    assert data["app"] == "document-conversion-engine"
    assert "queue_depth" in data


def test_probes_bypass_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.middleware.api_key as guard
    from app.core.config import Settings

    monkeypatch.setattr(guard, "get_settings", lambda: Settings(api_keys="secret"))
    client = TestClient(app)
    for path in ("/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready"):
        assert client.get(path).status_code in (200, 503)
