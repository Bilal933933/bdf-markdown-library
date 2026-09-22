import pytest
from fastapi.testclient import TestClient

import app.middleware.api_key as guard
import app.middleware.rate_limit as limiter
from app.core.config import Settings
from app.main import app


def limited_settings(rate: int = 2) -> Settings:
    return Settings(api_keys="admin-key,reader-key:read", rate_limit_per_minute=rate)


@pytest.fixture()
def limited(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(guard, "get_settings", lambda: limited_settings())
    monkeypatch.setattr(limiter, "get_settings", lambda: limited_settings())
    limiter.reset_rate_limits()
    yield TestClient(app)
    limiter.reset_rate_limits()


def test_two_pass_third_is_rejected(limited: TestClient) -> None:
    headers = {"X-API-Key": "admin-key"}
    assert limited.get("/api/v1/conversions/x", headers=headers).status_code == 404
    assert limited.get("/api/v1/conversions/x", headers=headers).status_code == 404
    rejected = limited.get("/api/v1/conversions/x", headers=headers)
    assert rejected.status_code == 429
    assert rejected.json()["error"]["code"] == "RATE_LIMITED"
    assert rejected.json()["error"]["request_id"] == rejected.headers["X-Request-ID"]


def test_health_is_excluded_from_limit(limited: TestClient) -> None:
    for _ in range(3):
        assert limited.get("/api/v1/health").status_code == 200


def test_read_key_cannot_write(limited: TestClient) -> None:
    response = limited.post("/api/v1/conversions", headers={"X-API-Key": "reader-key"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_read_key_can_read(limited: TestClient) -> None:
    response = limited.get("/api/v1/conversions/x", headers={"X-API-Key": "reader-key"})
    assert response.status_code == 404
