"""First real endpoint — proves the stack serves versioned routes."""

from fastapi import APIRouter

from app.core.logging import get_request_id
from app.schemas.common import Meta, SuccessEnvelope

router = APIRouter()


@router.get("/health", response_model=SuccessEnvelope[dict])
def health() -> SuccessEnvelope[dict]:
    return SuccessEnvelope(
        data={"status": "ok"},
        meta=Meta(request_id=get_request_id()),
    )
