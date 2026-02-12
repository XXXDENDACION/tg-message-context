from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Message
from src.models.message import MessageDTO


class MessageRepository:
    """Repository for message CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_message(self, dto: MessageDTO) -> Message:
        """Save a new message to database."""
        message = Message(
            message_id=dto.message_id,
            chat_id=dto.chat_id,
            user_id=dto.user_id,
            username=dto.username,
            text=dto.text,
            reply_to_message_id=dto.reply_to_message_id,
            timestamp=dto.timestamp,
        )
        self.session.add(message)
        await self.session.commit()
        return message

    async def get_message_by_id(self, chat_id: int, message_id: int) -> Message | None:
        """Get a specific message by chat_id and message_id."""
        result = await self.session.execute(
            select(Message).where(
                and_(Message.chat_id == chat_id, Message.message_id == message_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_context_messages(
        self,
        chat_id: int,
        target_message_id: int,
        count: int = 20,
    ) -> list[Message]:
        """
        Get context messages around a target message.
        If target message is a reply, starts from the original message.
        Otherwise gets messages before the target.
        """
        import logging
        logger = logging.getLogger(__name__)

        # First, get the target message
        target = await self.get_message_by_id(chat_id, target_message_id)
        if not target:
            logger.warning(f"Target message {target_message_id} not found in DB")
            return []

        # If it's a reply, find the root message and get messages from there
        if target.reply_to_message_id:
            root_message_id = await self._find_root_message(chat_id, target.reply_to_message_id)
            logger.info(f"Message is a reply, found root: {root_message_id}")

            # Get messages from root to target + some after
            result = await self.session.execute(
                select(Message)
                .where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.message_id >= root_message_id,
                    )
                )
                .order_by(Message.message_id.asc())
                .limit(count)
            )
        else:
            # Get messages BEFORE and including the target
            logger.info(f"Getting {count} messages before message {target_message_id}")
            result = await self.session.execute(
                select(Message)
                .where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.message_id <= target_message_id,
                    )
                )
                .order_by(Message.message_id.desc())
                .limit(count)
            )

        messages = list(result.scalars().all())
        # Sort by message_id ascending for proper order
        messages.sort(key=lambda m: m.message_id)

        logger.info(f"Retrieved {len(messages)} context messages from DB")
        return messages

    async def _find_root_message(self, chat_id: int, message_id: int) -> int:
        """Recursively find the root message of a reply chain."""
        message = await self.get_message_by_id(chat_id, message_id)
        if not message or not message.reply_to_message_id:
            return message_id
        return await self._find_root_message(chat_id, message.reply_to_message_id)

    async def get_messages_in_range(
        self,
        chat_id: int,
        from_message_id: int,
        to_message_id: int,
    ) -> list[Message]:
        """Get all messages between two message IDs."""
        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.message_id >= from_message_id,
                    Message.message_id <= to_message_id,
                )
            )
            .order_by(Message.message_id.asc())
        )
        return list(result.scalars().all())

    async def message_exists(self, chat_id: int, message_id: int) -> bool:
        """Check if a message already exists in the database."""
        result = await self.get_message_by_id(chat_id, message_id)
        return result is not None
