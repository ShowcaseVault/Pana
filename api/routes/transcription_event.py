"""Server-sent events telling a client when its transcriptions finish.

One stream per user. The channel is keyed by user id, so Redis delivers only
the caller's events rather than the route filtering a firehose -- and a
listener never sees that anyone else is using the system.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.auth.dependencies import get_authorized_db_user
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import TranscriptionEventRepository

logger = logging.getLogger("pubsub")

router = APIRouter(prefix="/transcription-events", tags=["Event"])

# A stream with nothing to say still has to prove it is alive: proxies and load
# balancers close a connection that goes quiet. A comment line is valid SSE and
# is ignored by EventSource.
HEARTBEAT_SECONDS = 25


def get_event_repository() -> TranscriptionEventRepository:
    """One subscriber per request, with its own Redis connection."""
    return TranscriptionEventRepository()


@router.get("", responses=error_docs(401))
async def transcription_events(
    request: Request,
    user: User = Depends(get_authorized_db_user),
    events: TranscriptionEventRepository = Depends(get_event_repository),
) -> StreamingResponse:
    """Stream this user's transcription completions as they happen.

    Authentication is the usual dependency, which reads the access cookie or a
    bearer header. A browser's `EventSource` cannot set headers, so the cookie
    is what carries a web client here.
    """

    async def event_stream():
        subscription = events.listen(user.id).__aiter__()

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    # Waiting with a timeout rather than blocking forever is
                    # what lets a silent stream send a heartbeat and notice a
                    # client that went away.
                    event = await asyncio.wait_for(
                        subscription.__anext__(), timeout=HEARTBEAT_SECONDS
                    )
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                except StopAsyncIteration:
                    break

                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            # The client went away mid-wait. Nothing to report.
            pass
        finally:
            await subscription.aclose()
            logger.debug("Transcription event stream closed for user %s", user.id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # Proxies love to buffer a streaming response into uselessness.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
