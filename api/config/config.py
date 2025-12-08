import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config/.env"

load_dotenv(ENV_PATH)

class config:
    # SYSTEM
    SERVER_HOST="0.0.0.0"
    SERVER_PORT=8000
    SERVER_RELOAD=True
    SHOW_DOCS=True
    CLIENT_URL=os.getenv("CLIENT_URL", "http://localhost:5173")

    # Authentication
    GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID", None)
    GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET", None)
    GOOGLE_REDIRECT_URI=os.getenv("GOOGLE_REDIRECT_URI", None)
    GOOGLE_AUTH_URL=os.getenv("GOOGLE_AUTH_URL", None)
    GOOGLE_TOKEN_URL=os.getenv("GOOGLE_TOKEN_URL", None)

    # JWT / Sessions
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "my-secret-token")
    JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", JWT_SECRET_KEY)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
    ACCESS_COOKIE_NAME = os.getenv("ACCESS_COOKIE_NAME", "access_token")
    REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

    # Database
    POSTGRES_HOST='localhost'
    POSTGRES_PORT='5433'
    POSTGRES_USER='pana'
    POSTGRES_PASSWORD='pana'
    POSTGRES_DB='pana-db'
    # LLM1
    LLM1 = "Groq"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
    GROQ_MODEL_SMALL = "llama-3.1-8b-instant"
    GROQ_MODEL_LARGE = "meta-llama/llama-4-maverick-17b-128e-instruct"
    # LLM2
    LLM2 = "Gemini"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL = "gemini-2.5-flash"

settings = config()