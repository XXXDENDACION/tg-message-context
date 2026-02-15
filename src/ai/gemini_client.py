import json
import logging

import google.generativeai as genai

from src.config import settings
from src.db.models import Message

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

FILTER_PROMPT = """You filter chat messages. Return ONLY IDs of messages about the EXACT SAME topic as the target.

TARGET (ID: {target_id}): "{target_text}"

MESSAGES:
{messages}

EXAMPLE 1:
Target: "выходи к ване"
Messages:
- ID 1: "погода сегодня хорошая" → EXCLUDE (different topic)
- ID 2: "ты где?" → INCLUDE (same conversation about meeting)
- ID 3: "я на месте" → INCLUDE (same topic - location/meeting)
- ID 4: "выходи к ване" → INCLUDE (target)
Result: {{"relevant_ids": [2, 3, 4]}}

EXAMPLE 2:
Target: "баг пофиксил"
Messages:
- ID 10: "что на обед?" → EXCLUDE
- ID 11: "там ошибка в логине" → INCLUDE (about the bug)
- ID 12: "посмотри пожалуйста" → INCLUDE (about the bug)
- ID 13: "баг пофиксил" → INCLUDE (target)
Result: {{"relevant_ids": [11, 12, 13]}}

Return ONLY messages that a human would clearly group together as ONE conversation thread.
If unsure - EXCLUDE. Return 2-5 messages typically, rarely more.

JSON only: {{"relevant_ids": [...]}}"""


async def filter_relevant_messages(
    target_message: Message,
    context_messages: list[Message],
) -> list[int]:
    """
    Use Gemini to filter messages that are relevant to the target message.
    Returns list of relevant message IDs.
    """
    messages_text = "\n".join(
        f"ID: {msg.message_id} | @{msg.username or 'unknown'}: {msg.text}"
        for msg in context_messages
        if msg.text
    )

    prompt = FILTER_PROMPT.format(
        target_id=target_message.message_id,
        target_text=target_message.text or "[no text]",
        messages=messages_text,
    )

    logger.info(f"Sending {len(context_messages)} messages to Gemini for filtering")

    try:
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        content = response.text
        logger.info(f"Gemini raw response: {content}")

        if not content:
            logger.error("Empty response from Gemini")
            return [target_message.message_id]

        result = json.loads(content)
        relevant_ids = result.get("relevant_ids", [target_message.message_id])

        logger.info(f"Gemini filtered {len(relevant_ids)} relevant messages from {len(context_messages)}")
        return relevant_ids

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return [target_message.message_id]
