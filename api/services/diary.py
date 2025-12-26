import json
import httpx

from typing import List, Dict, Any, Optional
from datetime import datetime

from api.models.recordings import Recording
from api.models.transcriptions import Transcription

from api.config.config import settings as CONFIG
from api.config.client import llm_client
from prompts.diary_ai import DIARY_AI_PROMPT

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
        elif not transcription.status == "completed":
            transcribe_audio_task.apply_async(args=[transcription.id], queue="high_priority")

async def generate_diary_from_recordings(
    db: Any,
    user_id: int,
    recordings: List[Recording], 
    transcriptions: List[Transcription]
) -> Dict[str, Any]:
    await ensure_all_transcriptions(recordings, db, user_id)

    events_data = []

    for r in recordings:
        transcription = getattr(r, "transcription", None)
        
        # Skip if no transcription or below confidence threshold
        if not transcription or not transcription.text:
            continue
            
        if (transcription.confidence or 0) <= CONFIG.TRANSCRIPTION_CONFIDENCE_THRESHOLD:
            continue

        # Resolve location
        location_resolved = "Unknown Location"
        if r.location_text and "," in r.location_text:
            try:
                lat_str, lon_str = r.location_text.split(",")
                location_resolved = await get_location_by_lat_long(float(lat_str), float(lon_str))
            except Exception:
                location_resolved = r.location_text # Fallback to raw coords if resolution fails

        events_data.append({
            "diary_date": r.recorded_at.isoformat() if isinstance(r.recorded_at, datetime) else str(r.recorded_at),
            "text": transcription.text,
            "location": location_resolved,
            "language": transcription.language or "unknown"
        })

    if not events_data:
        return {
            "mood": "neutral",
            "content": "No clear recordings or transcriptions available for today to generate a diary.",
            "actions": []
        }

    # Construct Prompt
    input_json = json.dumps({"events": events_data}, indent=2)
    user_message = f"Here are my events for today:\n\n{input_json}\n\nPlease generate my diary entry."

    try:
        response = await llm_client.chat.completions.create(
            messages=[
                {"role": "system", "content": DIARY_AI_PROMPT},
                {"role": "user", "content": user_message}
            ],
            model=CONFIG.GROQ_MODEL_LARGE,
            response_format={"type": "json_object"}
        )
        
        ai_content = response.choices[0].message.content
        return json.loads(ai_content)
        
    except Exception as e:
        return {
            "mood": "unknown",
            "content": f"I had a few things to record today, but I'm having trouble reflecting on them right now. (Error: {str(e)})",
            "actions": [{"type": "system", "description": "AI generation failed", "time": datetime.now().isoformat(), "location": "System"}]
        }
