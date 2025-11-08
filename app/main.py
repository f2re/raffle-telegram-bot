import asyncio
import sys
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.session import init_db
from app.handlers import start, payment, raffle, admin, withdrawal


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
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            env_msg = "🧪 TEST MODE" if settings.is_test_environment else "🚀 PRODUCTION"
            await bot.send_message(
                admin_ids[0],
                f"🤖 Бот запущен и готов к работе!\n\nРежим: {env_msg}"
            )
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

    logger.success("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Actions on bot shutdown"""
    logger.info("Bot is shutting down...")

    # Notify admin
    try:
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            await bot.send_message(
                admin_ids[0],
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

    # Log environment mode
    env_mode = "🧪 TEST" if settings.is_test_environment else "🚀 PRODUCTION"
    logger.info(f"Environment: {env_mode}")
    if settings.is_test_environment:
        logger.warning("⚠️  Running in TEST mode with Telegram Test Server bot token")
        logger.warning("⚠️  Payments will use test stars (no real money)")

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,  # Automatically selects test or production token
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(raffle.router)
    dp.include_router(withdrawal.router)
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
