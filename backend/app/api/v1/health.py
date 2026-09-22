"""Health probes — liveness, readiness, and detailed status (k8s friendly)."""

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from rq import Queue
from sqlalchemy import text

from app.api.envelopes import ErrorBody, ErrorEnvelope, Meta, SuccessEnvelope
from app.core.config import get_settings
from app.core.errors.codes import ErrorCode
from app.core.logging import get_request_id
from app.domains.conversion.pipeline.process import QUEUE_NAME
from app.infrastructure.database import get_engine
from app.infrastructure.redis import get_redis, ping, reset_redis

router = APIRouter()


def check_db() -> str:
    """Return 'up' if SELECT 1 succeeds, else 'down' — never raise."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


def check_redis() -> str:
    """Return 'up' if Redis pings, else 'down' — never raise."""
    try:
        return "up" if ping() else "down"
    except Exception:
        return "down"


def queue_depth() -> int | None:
    """Length of the conversions queue, or None when Redis is unreachable."""
    try:
        try:
            return Queue(QUEUE_NAME, connection=get_redis()).count
        finally:
            reset_redis()
    except Exception:
        return None


@router.get("/health", response_model=SuccessEnvelope[dict])
def health() -> SuccessEnvelope[dict]:
    return SuccessEnvelope(
        data={"status": "ok", "db": check_db()},
        meta=Meta(request_id=get_request_id()),
    )


@router.get("/health/live", response_model=SuccessEnvelope[dict])
def live() -> SuccessEnvelope[dict]:
    return SuccessEnvelope(
        data={"status": "ok"},
        meta=Meta(request_id=get_request_id()),
    )


@router.get("/health/ready")
def ready() -> JSONResponse:
    if check_db() != "up":
        envelope = ErrorEnvelope(
            error=ErrorBody(
                code=str(ErrorCode.INTERNAL_ERROR),
                message="Database unreachable",
                details=None,
                request_id=get_request_id(),
            )
        )
        return JSONResponse(status_code=503, content=jsonable_encoder(envelope))
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            SuccessEnvelope(
                data={"status": "ok", "db": "up"},
                meta=Meta(request_id=get_request_id()),
            )
        ),
    )


@router.get("/health/detailed", response_model=SuccessEnvelope[dict])
def detailed() -> SuccessEnvelope[dict]:
    settings = get_settings()
    return SuccessEnvelope(
        data={
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "db": check_db(),
            "redis": check_redis(),
            "queue_depth": queue_depth(),
        },
        meta=Meta(request_id=get_request_id()),
    )
