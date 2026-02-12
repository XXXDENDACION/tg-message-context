import logging
from datetime import datetime

from aiogram import Bot, Router
from aiogram.types import Message, MessageReactionUpdated

from src.config import settings
from src.db.database import async_session
from src.db.repository import MessageRepository
from src.models.message import MessageDTO
from src.services.context_service import ContextService

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def handle_message(message: Message) -> None:
    """Save every message to the database."""
    if message.chat.id != settings.source_chat_id:
        return

    if not message.text:
        return

    async with async_session() as session:
        repo = MessageRepository(session)

        # Check if message already exists
        if await repo.message_exists(message.chat.id, message.message_id):
            return

        dto = MessageDTO(
            message_id=message.message_id,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else 0,
            username=message.from_user.username if message.from_user else None,
            text=message.text,
            reply_to_message_id=(
                message.reply_to_message.message_id if message.reply_to_message else None
            ),
            timestamp=message.date or datetime.utcnow(),
        )

        await repo.save_message(dto)
        logger.info(f"New message saved: #{message.message_id} from @{dto.username or 'unknown'}: {dto.text[:50]}{'...' if len(dto.text or '') > 50 else ''}")


@router.message_reaction()
async def handle_reaction(event: MessageReactionUpdated, bot: Bot) -> None:
    """Handle reaction events - trigger context extraction on thumbs up."""
    if event.chat.id != settings.source_chat_id:
        return

    # Check for thumbs up reaction (new reactions)
    new_reactions = event.new_reaction or []
    has_thumbs_up = any(
        getattr(reaction, "emoji", None) == "👍" for reaction in new_reactions
    )

    if not has_thumbs_up:
        return

    logger.info(f"Thumbs up detected on message {event.message_id}")

    async with async_session() as session:
        context_service = ContextService(session, bot)
        await context_service.process_reaction(
            chat_id=event.chat.id,
            message_id=event.message_id,
        )
