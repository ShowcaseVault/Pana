"""One log line per request.

A terminal watching a running server should answer "what is happening right
now" without being read closely. That means one line per request, not a
paragraph, and nothing at all for the traffic that carries no information --
static files, health checks, and the event stream a client holds open for
minutes at a time.

The line is deliberately narrow:

    POST /api/v1/recordings 201 1.24s

Method and path say what was asked, the status says how it went, and the
duration is the number worth watching. Anything more belongs in the log file,
not on screen.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("api.request")

# Paths that would log constantly while saying nothing. The event stream is the
# important one: it is a long-lived connection, so a line for it is a line
# about a client connecting, not about work being done.
QUIET_PREFIXES = ("/recordings/", "/static/", "/docs", "/redoc", "/openapi.json", "/favicon")
QUIET_EXACT = ("/", "/health")

# Above this, a request is worth noticing even when it succeeded.
SLOW_SECONDS = 1.0


def _is_quiet(path: str) -> bool:
    return path in QUIET_EXACT or path.startswith(QUIET_PREFIXES)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one line per request, at a level that matches the outcome."""

    async def dispatch(self, request: Request, call_next):
        if _is_quiet(request.url.path):
            return await call_next(request)

        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # The exception handlers own the traceback and the response. This
            # only records that the request died, so the timing line is not
            # silently missing for the one request most worth seeing.
            elapsed = time.perf_counter() - started
            logger.error("%s %s failed after %.2fs", request.method, request.url.path, elapsed)
            raise

        elapsed = time.perf_counter() - started

        # A failed request is already logged by the exception handlers, and
        # their line carries the reason, which this one cannot. So a 4xx is
        # logged here only at DEBUG: the pair would otherwise print every
        # failure twice, once with the cause and once without.
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.DEBUG
        elif elapsed >= SLOW_SECONDS:
            # Succeeded, but slowly enough to be worth noticing.
            level = logging.WARNING
        else:
            level = logging.INFO

        logger.log(
            level,
            "%s %s %d %.2fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )

        return response
