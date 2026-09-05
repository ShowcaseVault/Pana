"""Repositories: the single point of external access.

A repository is the only place that talks to something outside the process --
the database, Redis, an HTTP API, an LLM. Dependencies arrive through the
constructor, so a service holds a repository and never a session or a client.

Import from here rather than from the individual modules:

    from api.repositories import UserRepository
"""

from api.repositories.diary_ai_repository import DiaryAIRepository
from api.repositories.diary_repository import DiaryRepository
from api.repositories.google_oauth_repository import GoogleOAuthRepository
from api.repositories.history_repository import HistoryRepository
from api.repositories.location_repository import LocationRepository
from api.repositories.recording_file_repository import RecordingFileRepository
from api.repositories.recording_repository import RecordingRepository
from api.repositories.refresh_token_repository import RefreshTokenRepository, hash_token
from api.repositories.transcription_repository import TranscriptionRepository
from api.repositories.user_repository import UserRepository

__all__ = [
    "DiaryAIRepository",
    "DiaryRepository",
    "GoogleOAuthRepository",
    "HistoryRepository",
    "LocationRepository",
    "RecordingFileRepository",
    "RecordingRepository",
    "RefreshTokenRepository",
    "TranscriptionRepository",
    "UserRepository",
    "hash_token",
]
