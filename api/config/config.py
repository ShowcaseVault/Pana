from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from prompts.audio_transcribe import AUDIO_TRANSCRIBE_PROMPT


class Settings(BaseSettings):
    """Application settings.

    Values are read from the environment (and `.env`), falling back to the
    defaults declared here. Field names match the environment variable names.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENV: str = "local"

    # Diary
    LOCATION_URL: str = (
        "https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={long}"
    )

    # Recordings: on-disk directory for uploaded audio, served at /recordings.
    RECORDINGS_DIR: str = "recordings"

    # Transcriptions
    AUDIO_TRANSCRIBE_PROMPT: str = AUDIO_TRANSCRIBE_PROMPT
    TRANSCRIPTION_MODEL: str = "whisper-large-v3"
    TRANSCRIPTION_MODEL_TURBO: str = "whisper-large-v3-turbo"
    TRANSCRIPTION_CONFIDENCE_THRESHOLD: float = 0.5

    # LLM1
    LLM1: str = "Groq"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL_SMALL: str = "llama-3.1-8b-instant"
    GROQ_MODEL_LARGE: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # LLM2
    LLM2: str = "Gemini"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Database
    POSTGRES_USER: str = "pana"
    POSTGRES_PASSWORD: str = "pana"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = "pana-db"

    # Redis
    REDIS_BROKER_URL: str = "redis://localhost:6379"
    REDIS_RESULT_BACKEND: str = "redis://localhost:6379"
    REDIS_PUBSUB_URL: str = "redis://localhost:6379"

    # SYSTEM
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_RELOAD: bool = True
    SHOW_DOCS: bool = True
    CLIENT_URL: str = "http://localhost:5173/home"

    # Authentication
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_AUTH_URL: str | None = None
    GOOGLE_TOKEN_URL: str | None = None

    # JWT / Sessions
    JWT_ACCESS_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ACCESS_COOKIE_NAME: str = "access_token"
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Sync database URL, assembled from the POSTGRES_* parts."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async (asyncpg) database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance.

    Cached so the environment is parsed once per process; use this as a FastAPI
    dependency or call it directly.
    """
    return Settings()


settings = get_settings()
