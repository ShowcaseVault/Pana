import json
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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

    # Outbound HTTP. Nominatim rejects requests without an identifying agent.
    HTTP_USER_AGENT: str = "PanaLocation/1.0"

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
    REDIS_CACHE_URL: str = "redis://localhost:6379/3"

    # Cache
    # L1 lives in the process (per-worker); L2 is shared across workers via Redis.
    CACHE_ENABLED: bool = True
    CACHE_KEY_PREFIX: str = "pana"
    CACHE_L1_MAXSIZE: int = 500
    CACHE_L1_TTL: int = 60
    CACHE_L2_TTL: int = 3600

    # SYSTEM
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # API. Every application router is mounted under API_PREFIX/API_VERSION,
    # so a breaking change ships as a new version rather than in place.
    APP_NAME: str = "Pana-API"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    API_VERSION: str = "v1"
    SERVER_RELOAD: bool = True
    SHOW_DOCS: bool = True
    CLIENT_URL: str = "http://localhost:5173/home"

    # CORS: browser origins allowed to call this API.
    # NoDecode: pydantic-settings would otherwise JSON-decode a list field
    # inside the env source, before any validator runs, so a plain
    # comma-separated value could never be parsed.
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

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
    def API_ROOT(self) -> str:
        """Base path shared by every application router, e.g. `/api/v1`."""
        return f"{self.API_PREFIX.rstrip('/')}/{self.API_VERSION.strip('/')}"

    @field_validator("API_PREFIX")
    @classmethod
    def _check_api_prefix(cls, value: str) -> str:
        """Require a leading slash and no trailing one, so joins stay predictable."""
        if not value.startswith("/"):
            raise ValueError(f"API_PREFIX must start with '/', got {value!r}")
        return value.rstrip("/") or "/"

    @field_validator("API_VERSION")
    @classmethod
    def _check_api_version(cls, value: str) -> str:
        """Expect a bare version segment such as `v1`, not a path."""
        version = value.strip("/")
        if not version or "/" in version:
            raise ValueError(f"API_VERSION must be a single segment like 'v1', got {value!r}")
        return version

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string from the environment.

        A JSON list is still accepted, so both
        `ALLOWED_ORIGINS=http://a,http://b` and `["http://a","http://b"]` work.
        """
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def _check_origins(cls, origins: list[str]) -> list[str]:
        """Reject values a browser will not accept as an Origin.

        An origin is scheme + host + optional port, nothing more. A wildcard, a
        trailing path, or a missing scheme all silently break CORS at runtime,
        so they fail here instead.
        """
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must list at least one origin")

        for origin in origins:
            if origin == "*":
                raise ValueError(
                    "ALLOWED_ORIGINS cannot be '*': credentials are enabled and "
                    "browsers reject a wildcard origin on credentialed requests. "
                    "List the frontend origins explicitly."
                )

            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError(
                    f"Invalid origin {origin!r}: expected scheme://host[:port], "
                    "e.g. http://localhost:5173"
                )
            if parsed.path or parsed.query or parsed.fragment:
                raise ValueError(
                    f"Invalid origin {origin!r}: an origin carries no path, "
                    f"try {parsed.scheme}://{parsed.netloc}"
                )

        return origins

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
