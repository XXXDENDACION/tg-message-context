import json
import logging

import httpx

from src.config import settings
from src.db.models import Message

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FILTER_PROMPT = """Analyze this chat to find ONLY messages directly related to the target message.

TARGET MESSAGE (received 👍 reaction):
ID: {target_id}
Text: "{target_text}"

CHAT MESSAGES:
{messages}

STRICT RULES:
1. Include ONLY messages that DIRECTLY discuss the same specific topic as the target
2. A message is related if it:
   - Is a direct reply to the target or messages in the same thread
   - Mentions the same specific subject/person/action as the target
   - Is part of the immediate back-and-forth leading to the target
3. EXCLUDE messages that:
   - Are about different topics even if sent by same person
   - Are general chatter not related to the target's specific subject
   - Just happen to be nearby in time but discuss something else

BE STRICT. It's better to return fewer highly relevant messages than many loosely related ones.
Typical result: 2-6 messages, not all messages.

Return JSON with relevant message IDs (always include target ID {target_id}):
{{"relevant_ids": [123, 125, 130]}}"""


async def filter_relevant_messages(
    target_message: Message,
    context_messages: list[Message],
) -> list[int]:
    """
    Use OpenRouter (DeepSeek) to filter messages that are relevant to the target message.
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

    logger.info(f"Sending {len(context_messages)} messages to OpenRouter for filtering")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You analyze chat conversations and return JSON. Be strict in filtering.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        logger.info(f"OpenRouter raw response: {content}")

        if not content:
            logger.error("Empty response from OpenRouter")
            return [target_message.message_id]

        result = json.loads(content)
        relevant_ids = result.get("relevant_ids", [target_message.message_id])

        logger.info(f"OpenRouter filtered {len(relevant_ids)} relevant messages from {len(context_messages)}")
        return relevant_ids

    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return [target_message.message_id]
