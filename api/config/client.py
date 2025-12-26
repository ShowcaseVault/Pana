from groq import AsyncGroq
from api.config.config import settings as CONFIG

transcription_client = AsyncGroq(api_key=CONFIG.GROQ_API_KEY)

llm_client = transcription_client