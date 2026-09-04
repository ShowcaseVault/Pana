import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config.config import settings

# Lifecycle functions are imported from their modules rather than the package:
# the lifespan below is the only caller that should be starting or stopping a
# connection, so they are deliberately not part of the package surface.
from api.connections.database_connection import (
    async_disconnect,
    create_database_if_not_exists,
    setup_engine_and_session,
)
from api.connections.http_connection import http_disconnect
from api.connections.llm_connection import llm_disconnect
from api.connections.pubsub_connection import pubsub_disconnect
from api.connections.redis_connection import redis_disconnect, setup_redis_client

# Routes
from api.routes import (
    authentication,
    diary,
    history,
    home,
    recordings,
    transcription_event,
    transcriptions,
)
from api.utils.logging_config import setup_logging

# Load environment variables

# Configure logging once for the application
setup_logging()
logger = logging.getLogger(__name__)


async def lifespan(app: FastAPI):
    logger.info("Application lifespan startup: initializing datastores")
    await create_database_if_not_exists()
    await setup_engine_and_session()
    await setup_redis_client()
    logger.info("Application lifespan started successfully")
    yield
    logger.info("Application lifespan shutdown: disconnecting datastores")
    await async_disconnect()
    await redis_disconnect()
    pubsub_disconnect()
    await llm_disconnect()
    await http_disconnect()
    logger.info("Application shutdown cleanup complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    docs_url, redoc_url = ("/doc", "/redoc") if settings.SHOW_DOCS else (None, None)

    app = FastAPI(
        title="Pana-API",
        description="API for Pana UI.",
        version="0.0.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        prefix="api",
    )
    logger.info("FastAPI application instance created")

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware configured to allow all origins")

    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
    app.mount(
        "/recordings",
        StaticFiles(directory=settings.RECORDINGS_DIR),
        name="recordings",
    )

    # Include routers
    app.include_router(authentication.router)
    app.include_router(home.router, prefix="/api")
    app.include_router(recordings.router, prefix="/api")
    app.include_router(transcriptions.router, prefix="/api")
    app.include_router(transcription_event.router, prefix="/api")
    app.include_router(history.router, prefix="/api")
    app.include_router(diary.router, prefix="/api")

    # Test route
    @app.get("/", include_in_schema=False)
    async def root():
        logger.info("Health check endpoint '/' called")
        return {"message": "Hello from Pana API!!"}

    return app


app = create_app()
