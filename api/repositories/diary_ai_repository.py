"""The LLM that turns a day's transcripts into a diary entry."""

import json
import logging
from typing import Any

from groq import AsyncGroq

from api.config.config import settings
from api.exceptions import ExternalServiceError
from prompts.diary_ai import DIARY_AI_PROMPT

logger = logging.getLogger("diary")


class DiaryAIRepository:
    """Asks the model for a diary entry and returns the parsed result."""

    def __init__(self, client: AsyncGroq) -> None:
        self.client = client

    async def write_entry(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a diary entry from the day's events.

        Raises `ExternalServiceError` when the model is unreachable or answers
        with something that is not the JSON object we asked for. The caller
        decides what a failed generation should look like to the user.
        """
        user_message = (
            "Here are my events for today:\n\n"
            f"{json.dumps({'events': events}, indent=2)}\n\n"
            "Please generate my diary entry."
        )

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": DIARY_AI_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                model=settings.GROQ_MODEL_LARGE,
                # The prompt asks for structured fields, so the model is held
                # to JSON rather than trusted to remember.
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.exception("Diary generation request failed")
            raise ExternalServiceError("Could not reach the diary model") from e

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except (TypeError, json.JSONDecodeError) as e:
            logger.error("Diary model returned unparseable content")
            raise ExternalServiceError("Diary model returned an invalid response") from e
