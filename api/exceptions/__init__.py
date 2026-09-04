"""Application exceptions and their handlers.

Raise these from services and routes instead of `HTTPException`:

    from api.exceptions import NotFoundError

    raise NotFoundError("Recording not found")

`register_exception_handlers(app)` turns them into the standard error envelope.
"""

from api.exceptions.base import (
    AppError,
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    UnprocessableError,
)
from api.exceptions.handlers import (
    error_docs,
    error_response,
    register_exception_handlers,
)

__all__ = [
    # Exceptions
    "AppError",
    "BadRequestError",
    "ConflictError",
    "ExternalServiceError",
    "ForbiddenError",
    "NotFoundError",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "UnprocessableError",
    # Registration and docs
    "error_docs",
    "error_response",
    "register_exception_handlers",
]
