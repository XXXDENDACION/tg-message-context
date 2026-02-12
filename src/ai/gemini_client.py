import json
import logging

import google.generativeai as genai

from src.config import settings
from src.db.models import Message

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

FILTER_PROMPT = """You are analyzing a chat conversation to find messages relevant to a specific target message.

Target message (the one that received a 👍 reaction):
ID: {target_id}
Text: "{target_text}"

Here are the surrounding messages from the chat (in chronological order):
{messages}

Your task:
1. Identify which messages are contextually related to the target message
2. Include messages that are part of the same discussion/topic/conversation flow
3. When in doubt, INCLUDE the message rather than exclude it
4. Only exclude messages that are CLEARLY about completely different unrelated topics

IMPORTANT: If all messages seem to be part of one conversation, include ALL of them.

Return ONLY a JSON object with message IDs that are relevant to the target message's context.
ALWAYS include the target message ID itself.

Response format (JSON only, no markdown):
{{"relevant_ids": [123, 124, 125, 128, 130]}}"""


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
