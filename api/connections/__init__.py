"""External connections: database, Redis (cache and pub/sub), LLM, HTTP.

Every outbound connection the application holds is created under this package,
so lifecycle and configuration live in one place rather than at the call sites.

Import what you need from here rather than from the individual modules:

    from api.connections import get_async_db_session, get_groq_client

Getters are for general use. The setup and disconnect functions are grouped
separately below: the application lifespan is the only thing that should call
them.
"""

from api.connections.database_connection import (
    async_disconnect,
    create_database_if_not_exists,
    get_async_db_session,
    get_sync_db_session,
    setup_engine_and_session,
    sync_disconnect,
)
from api.connections.database_creation import Base
from api.connections.http_connection import get_http_client, http_disconnect
from api.connections.llm_connection import get_groq_client, llm_disconnect
from api.connections.pubsub_connection import (
    get_async_redis_client,
    get_redis_client,
    pubsub_disconnect,
)
from api.connections.redis_connection import (
    get_cache_redis,
    redis_disconnect,
    setup_redis_client,
)

__all__ = [
    # Declarative base
    "Base",
    # Getters
    "get_async_db_session",
    "get_async_redis_client",
    "get_cache_redis",
    "get_groq_client",
    "get_http_client",
    "get_redis_client",
    "get_sync_db_session",
    # Lifecycle: for the application lifespan, not for routes or services
    "async_disconnect",
    "create_database_if_not_exists",
    "http_disconnect",
    "llm_disconnect",
    "pubsub_disconnect",
    "redis_disconnect",
    "setup_engine_and_session",
    "setup_redis_client",
    "sync_disconnect",
]
