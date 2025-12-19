import json
from datetime import datetime, timezone
from api.config.client import transcription_client
from api.config.config import settings as CONFIG

def compute_confidence(segment):
    seg_score = 0
    for seg in segment:
        logprob_score = min(1.0, max(0.0, 1 + seg["avg_logprob"]))
        no_speech_score = 1 - seg["no_speech_prob"]
        seg_score += round((logprob_score * 0.7 + no_speech_score * 0.3), 3)
    return seg_score / len(segment)

def transcribe_audio_file(file_path: str):
    """
    Transcribes the audio file using the configured client.
    """
    BASE_DIR = CONFIG.BASE_DIR
    file_name = BASE_DIR+"/"+file_path
    with open(file_name, "rb") as file:

        transcription = transcription_client.audio.transcriptions.create(
            file=file,
            model=CONFIG.TRANSCRIPTION_MODEL,
            response_format="verbose_json",
            timestamp_granularities=["word","segment"],
            language="en",
            temperature=0.0
        )

        confidence = compute_confidence(transcription.segments)
        transcription_text = transcription.text
        language = transcription.language
        transcribe_time = datetime.now(timezone.utc)
    
        transcription_data = {
            "text": transcription_text,
            "confidence": confidence,
            "language": language,
            "transcribe_time": transcribe_time,
            "words": [
                {
                    "start": s.get("start"),
                    "end": s.get("end"),
                    "text": s.get("word")
                }
                for s in (transcription.words if hasattr(transcription, "words") else [])
            ]
        }
    
    return transcription_data

