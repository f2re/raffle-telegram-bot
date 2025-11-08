import asyncio
import sys
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.session import init_db
from app.handlers import start, payment, raffle, admin


async def on_startup(bot: Bot):
    """Actions on bot startup"""
    logger.info("Bot is starting...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Notify admin
    try:
        await bot.send_message(
            settings.ADMIN_USER_ID,
            "🤖 Бот запущен и готов к работе!"
        )
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

    logger.success("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Actions on bot shutdown"""
    logger.info("Bot is shutting down...")

    # Notify admin
    try:
        await bot.send_message(
            settings.ADMIN_USER_ID,
            "🤖 Бот остановлен"
        )
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

    logger.info("Bot shutdown complete")


async def main():
    """Main function to run the bot"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
    )
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level=settings.LOG_LEVEL,
    )

    logger.info("Starting Telegram Raffle Bot...")

    # Initialize bot and dispatcher
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(raffle.router)
    dp.include_router(admin.router)

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
