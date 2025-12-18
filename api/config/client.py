from groq import Groq
from api.config.config import settings as CONFIG

transcription_client = Groq(api_key=CONFIG.GROQ_API_KEY)