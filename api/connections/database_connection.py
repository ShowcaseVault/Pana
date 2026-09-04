import logging
from collections.abc import AsyncGenerator
from typing import Any

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.config.config import settings

CONFIG = settings

logger = logging.getLogger("database")

# Database config loaded from .env
POSTGRES_HOST = CONFIG.POSTGRES_HOST
POSTGRES_PORT = int(CONFIG.POSTGRES_PORT)
POSTGRES_USER = CONFIG.POSTGRES_USER
POSTGRES_PASSWORD = CONFIG.POSTGRES_PASSWORD
POSTGRES_DB = CONFIG.POSTGRES_DB

# Globals
engine: Any | None = None
async_session: async_sessionmaker | None = None
connection: asyncpg.Connection | None = None

# Sync Globals (for Celery)
sync_engine: Any | None = None
SyncSession: sessionmaker | None = None


async def create_database_if_not_exists() -> None:
    """
    Connect to the default DB and create the target DB if it doesn't exist.
    """
    try:
        logger.info("Checking and creating database if not exists")
        default_conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database="postgres",
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )

        db_exists = await default_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", POSTGRES_DB
        )
        if not db_exists:
            await default_conn.execute(f'CREATE DATABASE "{POSTGRES_DB}"')
            logger.info("Database '%s' created", POSTGRES_DB)
        else:
            logger.info("Database '%s' already exists", POSTGRES_DB)

        await default_conn.close()
    except Exception:
        logger.exception("Error creating database")
        raise


async def setup_engine_and_session() -> None:
    """
    Set up the async SQLAlchemy engine and session factory.
    """
    global engine, async_session, connection

    db_url = CONFIG.ASYNC_DATABASE_URL

    try:
        logger.info("Setting up async SQLAlchemy engine and session")
        engine = create_async_engine(db_url, echo=False)
        async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

        # Optional direct connection check
        connection = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        logger.info(
            "Connected to database '%s' at %s:%s",
            POSTGRES_DB,
            POSTGRES_HOST,
            POSTGRES_PORT,
        )

    except Exception:
        logger.exception("Error setting up engine or connection")
        raise


async def check_connection() -> None:
    """
    Run a simple SQL command to check if DB is reachable.
    """
    if not engine:
        raise ConnectionError("Engine not set up.")

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("DB connection check passed")
    except Exception as e:
        logger.error("DB connection check failed: %s", e)


async def get_async_db_session() -> AsyncGenerator[Any, None]:
    """
    Get an async DB session (with commit/rollback handling).
    """
    if not async_session:
        raise ConnectionError("Not connected to database. Call setup_engine_and_session() first.")

    async with async_session() as session:
        try:
            # Caller is responsible for commit/rollback
            logger.debug("Yielding async DB session")
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise ConnectionError(f"Database session error: {str(e)}") from e
        except Exception as e:
            raise e


async def async_disconnect() -> bool:
    """
    Cleanly close connections and dispose engine.
    """
    global connection, engine

    try:
        logger.info("Disconnecting from database and disposing engine")
        if connection:
            await connection.close()
            connection = None
            logger.info("Asyncpg connection closed")

        if engine:
            await engine.dispose()
            engine = None
            logger.info("SQLAlchemy engine disposed")

        logger.info("Disconnected from database")
        return True
    except Exception:
        logger.exception("Async disconnection error")
        return False


def get_sync_db_session():
    """
    Get a synchronous DB session for Celery tasks.
    """
    global sync_engine, SyncSession

    if not sync_engine:
        db_url = CONFIG.DATABASE_URL
        sync_engine = create_engine(db_url, echo=False)
        SyncSession = sessionmaker(bind=sync_engine)

    session = SyncSession()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
