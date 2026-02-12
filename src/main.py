import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from src.bot.handlers import router
from src.config import settings
from src.db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    logger.info("Starting bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize bot with default properties
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # Initialize dispatcher
    dp = Dispatcher()
    dp.include_router(router)

    # Start polling
    logger.info("Bot is running...")
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction"])


if __name__ == "__main__":
    asyncio.run(main())
