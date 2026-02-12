import json
import logging

from groq import AsyncGroq

from src.config import settings
from src.db.models import Message

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=settings.groq_api_key)

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

Return a JSON object with message IDs that are relevant to the target message's context.
ALWAYS include the target message ID itself.

Example response format:
{{"relevant_ids": [123, 124, 125, 128, 130]}}

Only return the JSON, no other text."""


async def filter_relevant_messages(
    target_message: Message,
    context_messages: list[Message],
) -> list[int]:
    """
    Use Groq to filter messages that are relevant to the target message.
    Returns list of relevant message IDs.
    """
    # Format messages for the prompt
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

    logger.info(f"Sending {len(context_messages)} messages to Groq for filtering")
    logger.debug(f"Messages text:\n{messages_text}")

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes chat conversations. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        logger.info(f"Groq raw response: {content}")

        if not content:
            logger.error("Empty response from Groq")
            return [target_message.message_id]

        result = json.loads(content)
        relevant_ids = result.get("relevant_ids", [target_message.message_id])

        logger.info(f"Groq filtered {len(relevant_ids)} relevant messages from {len(context_messages)}")
        return relevant_ids

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        # Fallback: return just the target message
        return [target_message.message_id]
