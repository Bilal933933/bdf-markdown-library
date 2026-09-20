"""Application entrypoint: Exception -> Handler -> Unified Error Envelope."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        "DEBUG" if settings.debug else "INFO",
        log_file=settings.log_file,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_router)
    register_exception_handlers(app)

    return app


app = create_app()
