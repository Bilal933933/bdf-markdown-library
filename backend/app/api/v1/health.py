"""First real endpoint — proves the stack serves versioned routes."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.envelopes import Meta, SuccessEnvelope
from app.core.logging import get_request_id
from app.infrastructure.database import get_engine

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


@router.get("/health", response_model=SuccessEnvelope[dict])
def health() -> SuccessEnvelope[dict]:
    return SuccessEnvelope(
        data={"status": "ok", "db": check_db()},
        meta=Meta(request_id=get_request_id()),
    )
