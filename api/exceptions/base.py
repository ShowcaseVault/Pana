"""Application exceptions.

Business code raises these instead of `HTTPException`, so a service does not
have to know HTTP. The handlers in `api.exceptions.handlers` map each one onto a
status code and the standard error envelope.

Every exception carries a `status_code` and a default `message`; raising one
with no argument gives the default, and passing a string overrides it.
"""

from fastapi import status


class AppError(Exception):
    """Base for every expected application failure.

    Expected means "this is a normal outcome we chose to signal", not a bug --
    a missing row, a bad payload, an expired token. Handlers log these at
    warning level. Anything else reaching the app is a bug and is logged with a
    traceback by the catch-all handler.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Internal server error"

    def __init__(self, message: str | None = None, *, data: object = None) -> None:
        self.message = message or type(self).message
        # Optional structured detail (field errors, an upstream code). Goes into
        # the response body under "data" when present.
        self.data = data
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Bad request"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Not authenticated"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Forbidden"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Resource not found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    message = "Resource already exists"


class UnprocessableError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Request could not be processed"


class ExternalServiceError(AppError):
    """An upstream call failed: Google, Groq, or another third party.

    502 rather than 500: the failure is upstream, and the distinction matters
    when reading logs or deciding whether a retry is worth attempting.
    """

    status_code = status.HTTP_502_BAD_GATEWAY
    message = "Upstream service unavailable"


class ServiceUnavailableError(AppError):
    """A dependency this application owns is down: the database, Redis."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "Service temporarily unavailable"
