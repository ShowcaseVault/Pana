"""Diary business logic.

Turns a day's recordings into one written entry: make sure the audio has been
transcribed, hand the transcripts to the model, store what comes back.
"""

import logging
from datetime import date, datetime
from typing import Any

from api.config.config import settings
from api.exceptions import BadRequestError
from api.models.recordings import Recording
from api.repositories import (
    DiaryAIRepository,
    DiaryRepository,
    LocationRepository,
    TranscriptionRepository,
)
from api.schemas.diary import DiaryResponse

logger = logging.getLogger("diary")

# Shown when the day has no usable transcript. Not an error: a day with no
# clear recordings simply has nothing to write about.
EMPTY_DAY = {
    "mood": "neutral",
    "content": "No clear recordings or transcriptions available for today to generate a diary.",
    "actions": [],
}

# Shown when the model itself fails. The recordings are safe and regenerating
# is free, so the user is told to try again rather than shown an error page.
GENERATION_FAILED = {
    "mood": "unknown",
    "content": (
        "I had a few things to record today, but I'm having trouble reflecting "
        "on them right now. Please try again in a moment."
    ),
    "actions": [],
}


class DiaryService:
    """Read and generate a user's daily diary."""

    def __init__(
        self,
        *,
        diaries: DiaryRepository,
        transcriptions: TranscriptionRepository,
        location: LocationRepository,
        diary_ai: DiaryAIRepository,
    ) -> None:
        self.diaries = diaries
        self.transcriptions = transcriptions
        self.location = location
        self.diary_ai = diary_ai

    async def get(self, user_id: int, diary_date: date | None = None) -> DiaryResponse:
        """Return the diary for a day, written or not.

        A day with no diary yet is not a 404: the client shows the day either
        way, so an unwritten day comes back empty but with its recordings
        listed, which is what the screen needs to offer "generate".
        """
        target = diary_date or date.today()

        diary = await self.diaries.get_for_date(user_id, target)
        if diary is not None:
            return DiaryResponse.model_validate(diary)

        recordings = await self.diaries.recordings_for_date(user_id, target)
        return DiaryResponse(
            diary_date=target,
            recording_file_paths=[r.file_path for r in recordings],
        )

    async def generate(
        self, user_id: int, diary_date: date | None = None
    ) -> tuple[DiaryResponse, list[int]]:
        """Write or rewrite the diary for a day.

        Returns the diary and the ids of any transcriptions that need to run.
        The caller dispatches those: a Celery worker is another process and
        must not be handed work this request could still roll back.
        """
        target = diary_date or date.today()

        recordings = await self.diaries.recordings_for_date(user_id, target)
        if not recordings:
            # A diary is written from a day's recordings. Storing an entry for
            # a day with none creates a row that survives on its own and marks
            # the day as written in the calendar, which is the same orphan that
            # deleting the last recording is careful to remove.
            raise BadRequestError("There are no recordings for this day to write from")

        pending = await self._queue_missing_transcriptions(recordings)

        summary = await self._summarize(recordings)

        diary = await self.diaries.upsert(
            user_id=user_id,
            diary_date=target,
            mood=summary.get("mood"),
            content=summary.get("content"),
            actions=summary.get("actions"),
            recording_file_paths=[r.file_path for r in recordings],
        )
        return DiaryResponse.model_validate(diary), pending

    async def _queue_missing_transcriptions(self, recordings: list[Recording]) -> list[int]:
        """Return transcription ids that still need the worker to run.

        Covers both gaps: a recording with no transcription row at all gets one
        created, and a row that never finished is queued again. Without this a
        diary would silently omit audio that was uploaded but never processed.
        """
        pending: list[int] = []

        for recording in recordings:
            transcription = getattr(recording, "transcription", None)

            if transcription is None:
                created = await self.transcriptions.create(recording_id=recording.id)
                pending.append(created.id)
            elif transcription.status != "completed":
                pending.append(transcription.id)

        return pending

    async def _summarize(self, recordings: list[Recording]) -> dict[str, Any]:
        """Ask the model to write the day up, falling back to a safe entry."""
        events = await self._build_events(recordings)
        if not events:
            return EMPTY_DAY

        try:
            return await self.diary_ai.write_entry(events)
        except Exception:
            # A failed generation must not lose the day: the diary is still
            # written, with a message saying to try again.
            logger.exception("Diary generation failed, storing a placeholder entry")
            return GENERATION_FAILED

    async def _build_events(self, recordings: list[Recording]) -> list[dict[str, Any]]:
        """Turn the day's usable transcripts into the model's input."""
        events = []

        for recording in recordings:
            transcription = getattr(recording, "transcription", None)
            if transcription is None or not transcription.text:
                continue

            # A low-confidence transcript is more likely to mislead the model
            # than to help it, so it is left out entirely.
            if (transcription.confidence or 0) <= settings.TRANSCRIPTION_CONFIDENCE_THRESHOLD:
                continue

            events.append(
                {
                    "diary_date": self._as_iso(recording.recorded_at),
                    "text": transcription.text,
                    "location": await self._describe_location(recording),
                    "language": transcription.language or "unknown",
                }
            )

        return events

    async def _describe_location(self, recording: Recording) -> str:
        """Resolve a recording's coordinates to a place name.

        `location_text` holds raw "lat,long" from the client. If it is not
        coordinates, or the lookup fails, whatever the client sent is used --
        a place name it supplied is better than nothing.
        """
        raw = recording.location_text
        if not raw:
            return "Unknown Location"

        try:
            latitude, longitude = (float(part) for part in raw.split(",", 1))
        except ValueError:
            return raw

        return await self.location.name_for(latitude, longitude) or raw

    @staticmethod
    def _as_iso(value: Any) -> str:
        return value.isoformat() if isinstance(value, datetime) else str(value)
