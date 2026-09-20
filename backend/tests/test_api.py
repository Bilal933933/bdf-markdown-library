from typing import Annotated

from fastapi import Query
from fastapi.testclient import TestClient

from app.main import app, create_app

api_client = TestClient(app)
validation_app = create_app()
validation_client = TestClient(validation_app)


@validation_app.get("/validation-test")
def validation_test(limit: Annotated[int, Query(gt=0)]) -> dict[str, int]:
    return {"limit": limit}


def test_health_returns_request_id() -> None:
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.json()["data"] == {"status": "ok"}
    assert response.json()["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_not_found_uses_error_envelope() -> None:
    response = api_client.get("/api/v1/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_request_validation_is_caught_globally() -> None:
    response = validation_client.get("/validation-test", params={"limit": "invalid"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"] == [
        {
            "field": "query.limit",
            "message": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
