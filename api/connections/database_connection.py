"""Database engines and sessions.

Two engines live here. The async engine backs the API and is opened by the
application lifespan; the sync engine backs Celery tasks, which run outside that
lifespan and so create it lazily on first use.

Connection parameters come from `settings` at call time rather than being copied
into module constants, so a settings change is never shadowed by an import-time
snapshot.
"""

import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from api.config.config import settings

logger = logging.getLogger("database")

# Async globals (API)
engine: AsyncEngine | None = None
async_session: async_sessionmaker[AsyncSession] | None = None

# Sync globals (Celery)
sync_engine: Engine | None = None
SyncSession: sessionmaker[Session] | None = None

# Recycle below the usual 5 minute idle timeout of a proxy or a container
# network, and check a pooled connection before handing it out: a connection
# killed by a Postgres restart otherwise surfaces as a failed request.
POOL_KWARGS = {
    "pool_size": 10,
    "max_overflow": 5,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "pool_pre_ping": True,
}


async def create_database_if_not_exists() -> None:
    """Create the configured database if it is not there yet.

    Connects to the `postgres` maintenance database, because CREATE DATABASE
    cannot run from inside the database being created.
    """
    default_conn = None
    try:
        logger.debug("Checking and creating database if not exists")
        default_conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database="postgres",
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
        )

        db_exists = await default_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.POSTGRES_DB
        )
        if not db_exists:
            await default_conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            logger.debug("Database '%s' created", settings.POSTGRES_DB)
        else:
            logger.debug("Database '%s' already exists", settings.POSTGRES_DB)
    except Exception:
        logger.exception("Error creating database")
        raise
    finally:
        if default_conn is not None:
            await default_conn.close()


async def setup_engine_and_session() -> None:
    """Create the async engine and session factory, and verify the connection."""
    global engine, async_session

    try:
        logger.debug("Setting up async SQLAlchemy engine and session")
        engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False, **POOL_KWARGS)
        async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

        await check_connection()
        logger.debug(
            "Connected to database '%s' at %s:%s",
            settings.POSTGRES_DB,
            settings.POSTGRES_HOST,
            settings.POSTGRES_PORT,
        )
    except Exception:
        logger.exception("Error setting up the database engine")
        raise


async def check_connection() -> None:
    """Run `SELECT 1` against the async engine.

    Raises if the database is unreachable, so a broken configuration fails at
    startup rather than on the first request.
    """
    if engine is None:
        raise ConnectionError("Engine not set up. Call setup_engine_and_session() first.")

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.debug("Database connection check passed")


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session, committed on success.

    One request is one transaction: the session is committed once the route
    returns, and rolled back if it raises, so callers do not repeat a commit
    after every write. An explicit `await db.commit()` mid-request is still
    fine when a later step must not share the transaction; committing twice is
    harmless, as the second commit finds nothing pending.

    An exception is re-raised unchanged, so a constraint violation still reaches
    the route as the SQLAlchemy error it is.
    """
    if async_session is None:
        raise ConnectionError("Not connected to database. Call setup_engine_and_session() first.")

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def async_disconnect() -> bool:
    """Dispose the async engine and drop the session factory."""
    global engine, async_session

    try:
        logger.debug("Disconnecting from database and disposing engine")
        if engine is not None:
            await engine.dispose()
            engine = None
            async_session = None
            logger.debug("SQLAlchemy engine disposed")
        return True
    except Exception:
        logger.exception("Async disconnection error")
        return False


def setup_sync_engine() -> sessionmaker[Session]:
    """Create the sync engine and session factory on first use.

    Celery workers never run the application lifespan, so this is called lazily
    from `get_sync_db_session` instead of at startup.
    """
    global sync_engine, SyncSession

    if SyncSession is None:
        logger.debug("Setting up sync SQLAlchemy engine and session")
        sync_engine = create_engine(settings.DATABASE_URL, echo=False, **POOL_KWARGS)
        SyncSession = sessionmaker(bind=sync_engine)
    return SyncSession


@contextmanager
def get_sync_db_session() -> Generator[Session, None, None]:
    """Context manager yielding a sync session for Celery tasks.

    Usage:

        with get_sync_db_session() as db:
            ...

    The session is rolled back on an exception and closed either way, so a task
    cannot leak a connection back into the pool mid-transaction.

    Unlike the async dependency, this does not commit on exit. Tasks commit at
    their own checkpoints -- marking a transcription "processing" before a slow
    provider call, for instance -- and holding those in a single transaction
    until the task ends would hide the progress and keep the row locked for the
    whole call.
    """
    session = setup_sync_engine()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def sync_disconnect() -> None:
    """Dispose the sync engine. For worker shutdown hooks and tests."""
    global sync_engine, SyncSession

    if sync_engine is not None:
        sync_engine.dispose()
        sync_engine = None
        SyncSession = None
        logger.debug("Sync SQLAlchemy engine disposed")
