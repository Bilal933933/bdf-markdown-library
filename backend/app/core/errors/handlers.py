"""FastAPI exception handlers for the application's error contract."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.envelopes import ErrorBody, ErrorEnvelope
from app.core.config import get_settings
from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import AppError
from app.core.logging import get_request_id
from app.core.validation import format_validation_errors

logger = logging.getLogger(__name__)
VALIDATION_ERROR_MESSAGE = "Validation failed"


def error_response(
    status_code: int,
    code: ErrorCode | str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=str(code),
            message=message,
            details=details,
            request_id=get_request_id(),
        )
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))


def register_exception_handlers(app: FastAPI) -> None:
    """Register all expected and unexpected error handlers on the app."""

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            422,
            ErrorCode.VALIDATION_ERROR,
            VALIDATION_ERROR_MESSAGE,
            format_validation_errors(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.HTTP_ERROR
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        details = str(exc) if get_settings().debug else None
        return error_response(500, ErrorCode.INTERNAL_ERROR, "Internal server error", details)
