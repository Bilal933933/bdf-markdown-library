"""Application entrypoint: Exception -> Handler -> Unified Error Envelope."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.infrastructure.database import reset_engine
from app.middleware.api_key import ApiKeyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    reset_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        "DEBUG" if settings.debug else "INFO",
        log_file=settings.log_file,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.add_middleware(ApiKeyMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.include_router(api_router)
    register_exception_handlers(app)

    return app


app = create_app()
