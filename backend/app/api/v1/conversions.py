"""Conversion intake, status, and output download — thin HTTP over services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.envelopes import Meta, SuccessEnvelope
from app.core.config import Settings, get_settings
from app.core.errors.exceptions import NotFoundError
from app.core.logging import get_request_id
from app.domains.conversion.models import Conversion
from app.domains.conversion.pipeline.process import queue_conversion
from app.domains.conversion.services.conversions import (
    create_conversion,
    get_conversion,
    list_conversions,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.storage import LocalStorage

router = APIRouter()

_MEDIA_TYPES = {".md": "text/markdown; charset=utf-8", ".json": "application/json"}


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> LocalStorage:
    return LocalStorage(settings.storage_dir)


@router.post("/conversions", response_model=SuccessEnvelope[Conversion], status_code=202)
async def enqueue_conversion(
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessEnvelope[Conversion]:
    data = await file.read()
    conversion = create_conversion(db, storage, file.filename or "upload.pdf", data, settings)
    queue_conversion(conversion.id)
    return SuccessEnvelope(data=conversion, meta=Meta(request_id=get_request_id()))


@router.get("/conversions", response_model=SuccessEnvelope[list[Conversion]])
def list_all_conversions(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SuccessEnvelope[list[Conversion]]:
    return SuccessEnvelope(
        data=list_conversions(db, limit=limit, offset=offset),
        meta=Meta(request_id=get_request_id()),
    )


@router.get("/conversions/{conversion_id}", response_model=SuccessEnvelope[Conversion])
def conversion_status(
    conversion_id: str, db: Annotated[Session, Depends(get_db)]
) -> SuccessEnvelope[Conversion]:
    return SuccessEnvelope(
        data=get_conversion(db, conversion_id), meta=Meta(request_id=get_request_id())
    )


@router.get("/conversions/{conversion_id}/outputs/{key:path}")
def download_output(
    conversion_id: str,
    key: str,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> Response:
    get_conversion(db, conversion_id)
    try:
        data = storage.load(f"{conversion_id}/output/{key}")
    except (FileNotFoundError, ValueError) as exc:
        raise NotFoundError(f"Output {key} not found") from exc
    suffix = f".{key.rsplit('.', 1)[-1]}" if "." in key else ""
    return Response(content=data, media_type=_MEDIA_TYPES.get(suffix, "application/octet-stream"))
