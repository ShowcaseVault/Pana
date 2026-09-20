import json
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from prompts.audio_transcribe import AUDIO_TRANSCRIBE_PROMPT
from prompts.voice_companion import VOICE_COMPANION_PROMPT

# Schemes an Origin header may carry. A browser sends http or https; a native
# WebView serves the app from its own scheme and sends that instead --
# `capacitor://localhost` on iOS, `http://localhost` on Android.
ORIGIN_SCHEMES = frozenset({"http", "https", "capacitor"})


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

    # ---- STT: speech in -------------------------------------------------
    # Groq (Whisper). Uploaded audio gets the accurate model; a live call gets
    # the turbo one, because a call is latency-bound, not accuracy-bound.
    STT_MODEL: str = "whisper-large-v3"
    STT_MODEL_REALTIME: str = "whisper-large-v3-turbo"
    # Below this, a transcript is treated as unreliable rather than as text.
    STT_CONFIDENCE_THRESHOLD: float = 0.5
    # Domain hint sent with the audio: names Whisper would otherwise mangle.
    STT_PROMPT: str = AUDIO_TRANSCRIBE_PROMPT

    # ---- LLM: the reply -------------------------------------------------
    # Groq. Same split as STT: the realtime model answers a caller.
    GROQ_API_KEY: str | None = None
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_MODEL_REALTIME: str = "openai/gpt-oss-120b"
    # A spoken reply that runs long is one the caller talks over. Capped on
    # the model, so nothing is generated and then thrown away.
    LLM_MAX_TOKENS: int = 600
    LLM_TEMPERATURE: float = 0.7
    # Who Pana is on a call: a friend who talks back, not a prompt-and-wait
    # assistant. See prompts/voice_companion.py.
    VOICE_LLM_PROMPT: str = VOICE_COMPANION_PROMPT

    # ---- TTS: speech out -------------------------------------------------
    # NVIDIA Magpie. The hosted build runs on Cloud Functions: TLS, plus the
    # function ID as call metadata. A self-hosted NIM
    # (docker-compose.magpie.yml) is a plain gRPC target with neither, so
    # pointing TTS_URI at it and clearing TTS_FUNCTION_ID is the whole switch.
    NVIDIA_API_KEY: str | None = None
    TTS_URI: str = "grpc.nvcf.nvidia.com:443"
    TTS_FUNCTION_ID: str | None = "877104f7-e885-42b9-8de8-f6e4c6303969"
    TTS_USE_SSL: bool = True
    TTS_VOICE: str = "Magpie-Multilingual.EN-US.Sofia"
    TTS_LANGUAGE: str = "en-US"
    # Synthesis rate. The trunk gets 8 kHz after voice_service/audio.py
    # resamples; 22.05 kHz is already past what a phone line carries, at half
    # the bytes per chunk of 44.1 kHz.
    TTS_SAMPLE_RATE: int = 22050

    # Asterisk ARI. Control channel for the voice service: it subscribes to the
    # Stasis app and drives record/playback on live calls. ARI can originate
    # calls, so http.conf binds it to loopback and it must stay there -- see
    # docs/telephony.md.
    ARI_BASE_URL: str = "http://127.0.0.1:8088"
    ARI_USERNAME: str = "pana"
    # Shared with the Asterisk container, which reads the same value from .env
    # and renders it into ari.conf. No default: both sides refuse to start
    # rather than fall back to a known password.
    ARI_PASSWORD: str | None = None
    ARI_APP_NAME: str = "pana-voice"
    # Generated speech, written by the voice service and read by Asterisk. Two
    # views of one directory: the host path this process writes to, and the
    # path inside the container, which is what a playback URI must name. Both
    # sides of the bind mount in docker-compose.asterisk.yml.
    VOICE_TTS_DIR: str = "var/voice"
    VOICE_TTS_CONTAINER_DIR: str = "/var/spool/pana-tts"

    # Keep each turn's recording instead of deleting it, and log its size. For
    # diagnosing a call where the caller cannot be heard: the file is what
    # Asterisk actually captured, which separates a media path problem (no
    # audio arrived) from a recognition one (audio arrived, words did not).
    # Off in normal operation -- these are recordings of real conversations.
    VOICE_KEEP_RECORDINGS: bool = False

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

    # LOGGING. Rotation is per file: LOG_MAX_BYTES is the size at which a file
    # rolls over, LOG_BACKUP_COUNT how many rolled files are kept alongside it.
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 3 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 3

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

    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Authentication
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_AUTH_URL: str | None = None
    GOOGLE_TOKEN_URL: str | None = None

    # Native apps sign in with their own Google client, so an id_token minted
    # for iOS or Android carries a different `aud` than the web client's. Each
    # platform's client ID is listed here to be accepted at verification;
    # empty until a mobile app exists.
    GOOGLE_MOBILE_CLIENT_IDS: Annotated[list[str], NoDecode] = []

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

    @field_validator("GOOGLE_MOBILE_CLIENT_IDS", mode="before")
    @classmethod
    def _split_mobile_client_ids(cls, value: object) -> object:
        """Accept a comma-separated string or a JSON list from the environment."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

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

        `capacitor` joins http and https because a native WebView serves the
        app from its own scheme -- `capacitor://localhost` on iOS -- and sends
        that as the Origin. Rejecting it would mean the mobile app could not be
        allowed through CORS at all.
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
            if parsed.scheme not in ORIGIN_SCHEMES or not parsed.netloc:
                raise ValueError(
                    f"Invalid origin {origin!r}: expected scheme://host[:port] "
                    f"with scheme one of {', '.join(sorted(ORIGIN_SCHEMES))}, "
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
