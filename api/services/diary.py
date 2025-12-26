import httpx

from typing import List, Dict, Any
from datetime import datetime

from api.models.recordings import Recording
from api.models.transcriptions import Transcription

from api.config.config import settings as CONFIG

async def get_location_by_lat_long(lat: float, long: float) -> str:
    headers = {
        "User-Agent": "PanaLocation/1.0"
    }
    location_url_full = CONFIG.LOCATION_URL.format(lat=lat, long=long)
    async with httpx.AsyncClient() as client:
        response = await client.get(location_url_full, headers=headers)
        data = response.json()
        return data.get("name")

async def ensure_all_transcriptions(
    recordings: List[Recording], 
    db: Any, 
    user_id: int
):
    from api.cruds.transcriptions import create_transcription
    from api.schemas.transcriptions import TranscriptionCreate
    from celery_service.tasks.transcription import transcribe_audio_task

    for recording in recordings:
        transcription = getattr(recording, "transcription", None)
        
        if not transcription:
            payload = TranscriptionCreate(recording_id=recording.id)
            new_trans = await create_transcription(db=db, payload=payload, user_id=user_id)
            if new_trans:
                transcribe_audio_task.apply_async(args=[new_trans.id], queue="high_priority")
        elif not transcription.transcribed_at:
            transcribe_audio_task.apply_async(args=[transcription.id], queue="high_priority")

async def generate_diary_from_recordings(
    db: Any,
    user_id: int,
    recordings: List[Recording], 
    transcriptions: List[Transcription]
) -> Dict[str, Any]:
    await ensure_all_transcriptions(recordings, db, user_id)

    """
    Very simple heuristic service that aggregates transcription texts
    and derives mood/content/actions placeholders.
    Replace with real LLM/service logic later.
    """
    texts: List[str] = []
    for r in recordings:
        if getattr(r, "transcription", None) and getattr(r.transcription, "text", None):
            texts.append(r.transcription.text)

    full_text = "\n\n".join(texts).strip()

    # Naive mood heuristic
    lowered = full_text.lower()
    if any(k in lowered for k in ["happy", "great", "good", "awesome", "excited"]):
        mood = "positive"
    elif any(k in lowered for k in ["sad", "bad", "tired", "angry", "frustrated"]):
        mood = "negative"
    else:
        mood = "neutral"

    # Naive actions extraction: list timestamps of recordings as actions
    actions = []
    for r in recordings:
        actions.append({
            "type": "recording",
            "recording_id": r.id,
            "recorded_at": r.recorded_at.isoformat() if isinstance(r.recorded_at, datetime) else str(r.recorded_at),
            "location": r.location_text,
        })

    content = full_text or ""

    return {
        "mood": mood,
        "content": content,
        "actions": actions,
    }
