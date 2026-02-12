import json
import logging

from openai import AsyncOpenAI

from src.config import settings
from src.db.models import Message

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

FILTER_PROMPT = """You are analyzing a chat conversation to find messages relevant to a specific target message.

Target message (the one that received a 👍 reaction):
ID: {target_id}
Text: "{target_text}"

Here are the surrounding messages from the chat:
{messages}

Your task:
1. Identify which messages are contextually related to the target message
2. Include messages that are part of the same discussion/topic
3. Exclude messages that are clearly about different topics happening in parallel

Return a JSON array of message IDs that are relevant to the target message's context.
Include the target message ID itself.

Example response format:
{{"relevant_ids": [123, 124, 125, 128, 130]}}

Only return the JSON, no other text."""


async def filter_relevant_messages(
    target_message: Message,
    context_messages: list[Message],
) -> list[int]:
    """
    Use OpenAI to filter messages that are relevant to the target message.
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

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes chat conversations.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.error("Empty response from OpenAI")
            return [target_message.message_id]

        result = json.loads(content)
        relevant_ids = result.get("relevant_ids", [target_message.message_id])

        logger.info(f"OpenAI filtered {len(relevant_ids)} relevant messages from {len(context_messages)}")
        return relevant_ids

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        # Fallback: return just the target message
        return [target_message.message_id]
