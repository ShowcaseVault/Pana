import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from api.config.redis_client import get_redis_client

router = APIRouter(prefix="/transcription-events", tags=["Event"])
redis_client = get_redis_client()

@router.get("/")
async def transcription_complete(request: Request):
    
    async def event_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe("transcription_completed")

        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
        finally:
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )