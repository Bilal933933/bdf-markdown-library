"""Expected application errors with a consistent HTTP contract."""

from typing import Any

from app.core.errors.codes import ErrorCode


class AppError(Exception):
    """Base class for errors that are safe to expose to API clients."""

    status_code = 500
    code = ErrorCode.APP_ERROR
    default_message = "Application error"

    def __init__(self, message: str | None = None, *, details: Any | None = None) -> None:
        resolved_message = message or self.default_message
        super().__init__(resolved_message)
        self.message = resolved_message
        self.details = details


class BadRequestError(AppError):
    status_code = 400
    code = ErrorCode.BAD_REQUEST
    default_message = "Bad request"


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED
    default_message = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN
    default_message = "Access denied"


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT
    default_message = "Resource conflict"


class ValidationError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR
    default_message = "Validation failed"
