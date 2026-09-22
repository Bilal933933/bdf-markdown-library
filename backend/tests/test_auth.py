import pytest
from fastapi.testclient import TestClient

import app.middleware.api_key as guard
from app.core.config import Settings
from app.main import app


@pytest.fixture()
def enforced(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(guard, "get_settings", lambda: Settings(api_keys="secret"))
    return TestClient(app)


def test_health_stays_open_without_key(enforced: TestClient) -> None:
    assert enforced.get("/api/v1/health").status_code == 200


def test_missing_key_returns_401(enforced: TestClient) -> None:
    response = enforced.get("/api/v1/conversions/unknown")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_wrong_key_returns_403(enforced: TestClient) -> None:
    response = enforced.get("/api/v1/conversions/unknown", headers={"X-API-Key": "bad"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_valid_key_passes_through(enforced: TestClient) -> None:
    response = enforced.get("/api/v1/conversions/unknown", headers={"X-API-Key": "secret"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_open_mode_without_keys() -> None:
    response = TestClient(app).get("/api/v1/conversions/unknown")
    assert response.status_code == 404
