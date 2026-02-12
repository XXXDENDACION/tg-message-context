import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.groq_client import filter_relevant_messages
from src.config import settings
from src.db.repository import MessageRepository

logger = logging.getLogger(__name__)


class ContextService:
    """Service for extracting and publishing message context."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.repo = MessageRepository(session)

    async def process_reaction(self, chat_id: int, message_id: int) -> None:
        """
        Process a thumbs up reaction:
        1. Get context messages from DB
        2. Filter relevant ones with AI
        3. Publish to target channel
        """
        # Get target message
        target_message = await self.repo.get_message_by_id(chat_id, message_id)
        if not target_message:
            logger.warning(f"Message {message_id} not found in database")
            return

        # Get context messages
        context_messages = await self.repo.get_context_messages(
            chat_id=chat_id,
            target_message_id=message_id,
            count=settings.context_messages_count,
        )

        if not context_messages:
            logger.warning(f"No context messages found for {message_id}")
            return

        logger.info(f"Found {len(context_messages)} context messages")
        for msg in context_messages:
            logger.debug(f"  #{msg.message_id}: @{msg.username}: {msg.text[:30] if msg.text else '[empty]'}...")

        # Filter with AI
        relevant_ids = await filter_relevant_messages(target_message, context_messages)
        logger.info(f"AI returned {len(relevant_ids)} relevant IDs: {relevant_ids}")

        # Get only relevant messages
        relevant_messages = [
            msg for msg in context_messages if msg.message_id in relevant_ids
        ]
        logger.info(f"Matched {len(relevant_messages)} messages from context")

        if not relevant_messages:
            logger.warning("No relevant messages after filtering")
            return

        # Publish to channel
        await self._publish_to_channel(relevant_messages)

    async def _publish_to_channel(self, messages: list) -> None:
        """Publish filtered messages to target channel."""
        formatted_messages = []
        for msg in messages:
            username = f"@{msg.username}" if msg.username else "Unknown"
            text = msg.text or "[без текста]"
            formatted_messages.append(f"*{username}:* {text}")

        full_text = "\n".join(formatted_messages)

        # Telegram message limit is 4096 characters
        if len(full_text) > 4096:
            # Split into multiple messages
            await self._send_long_message(full_text)
        else:
            await self.bot.send_message(
                chat_id=settings.target_channel_id,
                text=full_text,
                parse_mode="Markdown",
            )

        logger.info(f"Published {len(messages)} messages to channel")

    async def _send_long_message(self, text: str) -> None:
        """Split and send a long message."""
        chunks = []
        current_chunk = ""

        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 > 4000:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line

        if current_chunk:
            chunks.append(current_chunk)

        for chunk in chunks:
            await self.bot.send_message(
                chat_id=settings.target_channel_id,
                text=chunk,
                parse_mode="Markdown",
            )
