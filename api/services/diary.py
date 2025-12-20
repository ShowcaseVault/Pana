from typing import List, Dict, Any
from datetime import datetime

from api.models.recordings import Recording


def generate_diary_from_recordings(recordings: List[Recording]) -> Dict[str, Any]:
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
