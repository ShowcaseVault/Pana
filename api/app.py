import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config.config import settings
from api.connections import (
    async_disconnect,
    create_database_if_not_exists,
    http_disconnect,
    llm_disconnect,
    pubsub_disconnect,
    redis_disconnect,
    setup_engine_and_session,
    setup_redis_client,
)
from api.exceptions import register_exception_handlers
from api.middleware import RequestLoggingMiddleware
from api.routes import (
    authentication,
    diary,
    history,
    home,
    media,
    recordings,
    transcription_event,
    transcriptions,
)
from api.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Routers mounted under the versioned API root (e.g. /api/v1).
API_ROUTERS = (
    home.router,
    recordings.router,
    transcriptions.router,
    transcription_event.router,
    history.router,
    diary.router,
    media.router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open every external connection on startup and close them on shutdown."""
    logger.debug("Opening datastore connections")
    await create_database_if_not_exists()
    await setup_engine_and_session()
    await setup_redis_client()

    # Created here rather than in create_app so that importing the module has
    # no filesystem side effect.
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)

    # The one startup line worth a terminal: it says the server is up and where
    # to reach it. Everything before it is plumbing and logs at DEBUG.
    logger.info(
        "Pana API ready on http://%s:%s%s",
        settings.SERVER_HOST,
        settings.SERVER_PORT,
        settings.API_ROOT,
    )

    yield

    logger.debug("Closing datastore connections")
    await _shutdown()
    logger.info("Pana API stopped")


async def _shutdown() -> None:
    """Close each connection independently.

    One failing teardown must not skip the rest, or a bad shutdown leaks every
    connection after it in the sequence.
    """
    for name, close in (
        ("database", async_disconnect),
        ("cache redis", redis_disconnect),
        ("pubsub redis", pubsub_disconnect),
        ("llm", llm_disconnect),
        ("http", http_disconnect),
    ):
        try:
            result = close()
            if result is not None:
                await result
        except Exception:
            logger.exception("Error closing %s connection", name)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    setup_logging()

    # The schema is as revealing as the docs pages, so it is hidden with them.
    docs_url, redoc_url, openapi_url = (
        ("/doc", "/redoc", "/openapi.json") if settings.SHOW_DOCS else (None, None, None)
    )

    app = FastAPI(
        title=settings.APP_NAME,
        description="API for Pana UI.",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    logger.debug("FastAPI application instance created")

    # CORS. Origins are listed explicitly rather than wildcarded: auth rides on
    # cookies, and a browser refuses a credentialed request against "*".
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.debug("CORS configured for origins: %s", settings.ALLOWED_ORIGINS)

    # Added after CORS so CORS remains the outermost layer: a rejected preflight
    # should not be timed and logged as though it were a real request.
    app.add_middleware(RequestLoggingMiddleware)

    # Authentication sits outside the versioned root: the Google callback URL is
    # registered with Google and cannot move when the API version changes.
    app.include_router(authentication.router)
    for router in API_ROUTERS:
        app.include_router(router, prefix=settings.API_ROOT)
    logger.debug("Routers mounted under %s", settings.API_ROOT)

    register_exception_handlers(app)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        """Liveness probe. Deliberately quiet: monitors call it constantly."""
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
