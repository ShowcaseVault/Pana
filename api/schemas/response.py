"""The response envelope every endpoint returns.

One shape for success and failure alike:

    {"success": true,  "message": "...", "data": {...}}
    {"success": false, "message": "...", "data": null}

`ApiResponse[T]` is generic, so a route annotated
`-> ApiResponse[RecordingResponse]` documents its real payload in the OpenAPI
schema instead of a bare `Any`. Returning the model directly (rather than a
dict) is what lets FastAPI serialize and document it.
"""

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    """Page metadata for a listing endpoint."""

    page: int = Field(ge=1, description="Current page, 1-based")
    page_size: int = Field(ge=1, description="Items per page")
    total: int = Field(ge=0, description="Total items across all pages")
    total_pages: int = Field(ge=0, description="Total number of pages")

    @classmethod
    def build(cls, *, page: int, page_size: int, total: int) -> "Pagination":
        # Ceiling division without importing math; a total of 0 gives 0 pages.
        total_pages = -(-total // page_size) if page_size else 0
        return cls(page=page, page_size=page_size, total=total, total_pages=total_pages)


class ApiResponse[T](BaseModel):
    """Standard envelope. `T` is the payload type."""

    success: bool = True
    message: str | None = None
    data: T | None = None


class PaginatedResponse[T](ApiResponse[T]):
    """Envelope for listings: adds page metadata alongside the payload."""

    pagination: Pagination | None = None


class ErrorResponse(BaseModel):
    """Failure envelope. Declared separately so OpenAPI can document error
    responses without dragging the success payload type along."""

    success: bool = False
    message: str = "Internal server error"
    data: object | None = None


def success[T](
    data: T | None = None,
    message: str | None = None,
) -> ApiResponse[T]:
    """Build a success envelope.

    Prefer returning `ApiResponse(data=..., message=...)` directly in a route
    where the type is known; this helper exists for services and for call sites
    where the payload type is not worth spelling out.
    """
    return ApiResponse[T](success=True, message=message, data=data)


def paginated[T](
    data: T | None = None,
    message: str | None = None,
    pagination: Pagination | None = None,
) -> PaginatedResponse[T]:
    """Build a success envelope carrying page metadata."""
    return PaginatedResponse[T](success=True, message=message, data=data, pagination=pagination)
