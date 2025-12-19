import uvicorn
import logging
from api.config.config import settings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.connections.database_connection import (
    create_database_if_not_exists,
    setup_engine_and_session,
    create_all_tables,
    async_disconnect,
)

# Routes
from api.routes import (
    authentication,
    home,
    recordings,
    transcriptions,
    transcription_event
)

from api.utils.logging_config import setup_logging

# For authentication
# from api.auth.dependency import get_current_user


# Load environment variables
CONFIG = settings

# Configure logging once for the application
setup_logging()
logger = logging.getLogger(__name__)


# Tables are created using async engine in startup event.
async def lifespan(app: FastAPI):
    logger.info("Application lifespan startup: initializing database")
    await create_database_if_not_exists()
    await setup_engine_and_session()
    await create_all_tables()
    logger.info("Application lifespan started successfully")
    yield
    logger.info("Application lifespan shutdown: disconnecting database")
    await async_disconnect()
    logger.info("Application shutdown cleanup complete")


# Docs Settings
if CONFIG.SHOW_DOCS:
    docs = ["/doc", "/redoc"]
else:
    docs = [None, None]

# Create FastAPI instance
app = FastAPI(
    title="Pana-API",
    description="API for Pana UI.",
    version="0.0.0",
    lifespan=lifespan,
    docs_url=docs[0],
    redoc_url=docs[1],
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

# Include routers
app.include_router(authentication.router)
app.include_router(home.router, prefix="/api")
app.include_router(recordings.router, prefix="/api")
app.include_router(transcriptions.router, prefix="/api")
app.include_router(transcription_event.router,prefix="/api")

# Test route
@app.get("/", include_in_schema=False)
async def root():
    logger.info("Health check endpoint '/' called")
    return {"message": "Hello from Pana API!!"}


# Uvicorn entry point
if __name__ == "__main__":
    logger.info("Starting uvicorn server on 0.0.0.0:8000")
    uvicorn.run(
        "api.server:app",
        host=str(CONFIG.SERVER_HOST),
        port=int(CONFIG.SERVER_PORT),
        reload=CONFIG.SERVER_RELOAD,
    )
