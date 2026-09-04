"""LLM provider clients.

Clients are created on first use rather than at import, so importing a module
that transcribes audio does not require a configured API key. Each client is
built once and reused, keeping the underlying HTTP connection pool alive across
requests.
"""

import logging

from groq import AsyncGroq

from api.config.config import settings

logger = logging.getLogger("llm")

groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return the shared Groq client, creating it on first use.

    Serves both transcription and diary generation; they differ by model, not by
    connection.
    """
    global groq_client
    if groq_client is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set")
        groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        logger.info("Groq client created")
    return groq_client


async def llm_disconnect() -> None:
    """Close the shared LLM client and its connection pool."""
    global groq_client
    if groq_client is not None:
        await groq_client.close()
        groq_client = None
        logger.info("Groq client closed")
