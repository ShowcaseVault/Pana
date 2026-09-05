# Architecture

Every feature in this API is the same three layers, and the value being passed
changes shape at each boundary.

```
HTTP request
   │
   ▼
route      ── auth dependency, query/body parsing, envelope, job dispatch
   │            success(...) / paginated(...)
   ▼
service    ── the rules: ownership, defaults, fallbacks, ordering
   │            returns response schemas, never HTTP
   ▼
repository ── the only code that touches Postgres, Redis, disk, HTTP, the LLM
```

## What each layer owns

**Route.** Declares the endpoint, pulls the caller out of the token, and wraps
whatever the service returned in the response envelope. It builds no SQL and
raises no `HTTPException`. Where a background job follows a write, the route
dispatches it -- see [Committing before dispatch](#committing-before-dispatch).

**Service.** Holds the repositories it needs, injected through the constructor.
This is where a feature's decisions live: that an unwritten diary is not a 404,
that a missing recording and a recording someone else owns are the same answer,
that a listing with no date means today. Services raise the domain exceptions
in `api/exceptions/` and know nothing about status codes.

**Repository.** The single point of external access. A service never holds an
`AsyncSession`, a Redis connection, or a Groq client -- it holds a repository
that does. On a read path a repository returns the response schema and, when
paging, the total count; on a write path it returns the live ORM row, because
the caller is about to mutate it.

## The response envelope

Every endpoint returns `ApiResponse[T]` or `PaginatedResponse[T]` from
`api/schemas/response.py`, annotated as the return type so OpenAPI documents
the real payload.

```json
{ "success": true, "message": "Recordings retrieved successfully", "data": [ ... ],
  "pagination": { "page": 1, "page_size": 100, "total": 240, "total_pages": 3 } }
```

Pagination lives in the envelope rather than in a per-domain wrapper schema, so
`data` is always the resource and a client parses one shape everywhere. The
repository returns `(rows, total)`, the route turns `page`/`page_size`/`total`
into `Pagination.build(...)`.

Failures use the same envelope with `success=false` and a `data` field that
carries structured detail when there is any. One function builds it --
`error_response()` in `api/exceptions/handlers.py` -- and it builds the body
from the `ErrorResponse` model that `error_docs()` advertises in OpenAPI, so
what a client receives and what Swagger promises cannot drift apart.

## Errors

Services raise `NotFoundError`, `BadRequestError`, `ConflictError`,
`UnauthorizedError` and the rest from `api/exceptions/`. Each carries its own
status code, and registered handlers turn it into the envelope. Expected
failures log one warning line; an unhandled exception logs a full traceback and
returns a generic message, because exception text can name tables or
credentials.

## Committing before dispatch

Two endpoints hand work to Celery: recording upload and diary generation. Both
follow the same rule -- the service returns the ids of jobs that need running,
the route commits, and only then dispatches.

A worker is a separate process with its own connection. Enqueueing before the
commit races it against the transaction: the worker can look up a row that is
still uncommitted, or worse, one that a later rollback erases. So the service
never calls `apply_async` itself; it reports what needs queueing and lets the
route, which owns the transaction boundary, decide when it is safe.

## Soft delete

`deleted_at IS NULL` means live. Deleting sets the timestamp; the row and,
for recordings, the audio file both stay. A soft delete is reversible, and
removing the bytes would make that a lie.
