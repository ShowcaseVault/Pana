"""Exception handlers.

Registering these gives every failure the same body as every success, so a
client parses one shape regardless of outcome:

    {"success": false, "message": "...", "data": null}

Four handlers cover everything the app can raise:

* `AppError`          -- expected failures raised by our own code.
* `HTTPException`     -- raised by FastAPI itself and by dependencies.
* `RequestValidationError` -- a malformed request body or query string.
* `Exception`         -- the catch-all, meaning a bug.

Logging follows severity: expected failures log a single warning line, bugs log
a full traceback. Nothing logs the response body twice.

Every handler returns through `error_response()`, the error counterpart of
`success()` in `api.schemas.response` -- one place builds the failure body, so
it cannot drift from what `error_docs()` documents.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.exceptions.base import AppError
from api.schemas.response import ErrorResponse

logger = logging.getLogger("api.errors")


def error_response(
    message: str,
    status_code: int,
    data: object = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a failure envelope -- the error counterpart of `success()`.

    The body is built from `ErrorResponse` rather than a literal dict, so the
    shape a client receives and the shape `error_docs()` advertises in OpenAPI
    cannot drift apart.

    `headers` exists for the failures that carry them: a 401 needs its
    `WWW-Authenticate`, and a 503 may carry `Retry-After`.
    """
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(message=message, data=data).model_dump(mode="json"),
        headers=headers,
    )


def _where(request: Request) -> str:
    """`METHOD /path` for log lines."""
    return f"{request.method} {request.url.path}"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to `app`. Called once from `create_app`."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Expected failure. One warning line, no traceback -- these are normal
        outcomes and a stack trace for every 404 buries the real errors."""
        logger.warning("%s -> %s: %s", _where(request), exc.status_code, exc.message)
        return error_response(exc.message, exc.status_code, data=exc.data)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """`HTTPException` from FastAPI internals or from a dependency.

        Handled here so a 401 raised by an auth dependency comes back in the
        same envelope as everything else, rather than as `{"detail": ...}`.
        """
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        data = None if isinstance(exc.detail, str) else exc.detail

        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error("%s -> %s: %s", _where(request), exc.status_code, message)
        else:
            logger.warning("%s -> %s: %s", _where(request), exc.status_code, message)

        return error_response(
            message,
            exc.status_code,
            data=data,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """A body or query string that did not match the schema.

        The per-field errors go in `data` so a form can highlight the offending
        inputs. `exc.errors()` can carry the raw input under `"input"`, which
        may be a password or a token, so only the location, message, and type
        are copied out.
        """
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        logger.warning("%s -> 422 validation: %s", _where(request), details)
        return error_response(
            "Validation failed",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            data=details,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Anything not handled above -- a bug.

        Full traceback to the log, generic message to the client: the exception
        text can name tables, file paths, or credentials.
        """
        logger.exception("Unhandled error on %s", _where(request))
        return error_response(
            "Internal server error",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Reusable OpenAPI `responses=` entries. Without these, Swagger documents only
# the success shape and shows FastAPI's default `{"detail": ...}` for errors,
# which is no longer what the app returns. Passing the model (rather than a raw
# `$ref`) lets FastAPI register the schema under components itself.
_ERROR_SCHEMA = ErrorResponse


def error_docs(*status_codes: int) -> dict[int, dict]:
    """OpenAPI `responses` entries for the given status codes.

    Usage on a route:

        @router.get("/{id}", responses=error_docs(401, 404))
    """
    labels = {
        400: "Bad request",
        401: "Not authenticated",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Validation failed",
        500: "Internal server error",
        502: "Upstream service unavailable",
        503: "Service temporarily unavailable",
    }
    return {
        code: {
            "description": labels.get(code, "Error"),
            "model": _ERROR_SCHEMA,
        }
        for code in status_codes
    }
