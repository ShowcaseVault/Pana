"""Outbound HTTP client for third-party APIs.

One shared `httpx.AsyncClient` instead of one per call: a fresh client per
request opens a new TCP and TLS connection every time and throws the pool away,
which is the dominant cost of a small geocoding lookup.
"""

import logging

import httpx

from api.config.config import settings

logger = logging.getLogger("http")

http_client: httpx.AsyncClient | None = None

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)


def get_http_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client, creating it on first use."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=TIMEOUT,
            limits=LIMITS,
            headers={"User-Agent": settings.HTTP_USER_AGENT},
        )
        logger.debug("HTTP client created")
    return http_client


async def http_disconnect() -> None:
    """Close the shared HTTP client and its connection pool."""
    global http_client
    if http_client is not None:
        await http_client.aclose()
        http_client = None
        logger.debug("HTTP client closed")
