import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.connections import get_async_redis_client

router = APIRouter(prefix="/transcription-events", tags=["Event"])


@router.get("/")
async def transcription_complete(request: Request):

    async def event_generator():
        # A subscriber owns its connection for the life of the subscription,
        # so this client is per-request and closed when the stream ends.
        redis_client = get_async_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("transcription_completed")

        try:
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break

                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.close()
            await redis_client.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
