import asyncio
import sys
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.session import engine
from app.database.init_db import init_database, check_db_health
from app.handlers import start, payment, raffle, admin, withdrawal
from app.services.ton_monitor import start_ton_monitor
from app.services.ton_service import ton_service

# Global TON monitor instance
ton_monitor = None


async def on_startup(bot: Bot):
    """Actions on bot startup"""
    global ton_monitor

    logger.info("Bot is starting...")

    # Initialize database (creates all enums and tables)
    try:
        # Check if database is healthy
        is_healthy = await check_db_health(engine)

        if not is_healthy:
            logger.info("Database needs initialization...")
            await init_database(engine)
        else:
            logger.info("Database is already initialized and healthy")

        logger.success("✅ Database ready")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error("Bot cannot start until database is initialized successfully")
        sys.exit(1)

    # Start TON transaction monitor if TON_ONLY mode enabled
    if settings.TON_ONLY:
        try:
            ton_monitor = await start_ton_monitor(bot)
            logger.info("TON transaction monitor started")

            # Check wallet balance
            balance = await ton_service.get_balance()
            logger.info(f"TON wallet balance: {balance:.4f} TON")

            if balance < settings.TON_RESERVE_MIN:
                logger.warning(
                    f"TON wallet balance ({balance:.4f}) is below minimum reserve "
                    f"({settings.TON_RESERVE_MIN} TON)"
                )
        except Exception as e:
            logger.error(f"Failed to start TON monitor: {e}", exc_info=True)
            # Don't exit - allow bot to start even if TON monitor fails

    # Notify admins
    admin_ids = settings.get_admin_ids()
    if admin_ids:
        for admin_id in admin_ids:
            try:
                status_msg = "🤖 Бот запущен и готов к работе!"
                if settings.TON_ONLY:
                    balance = await ton_service.get_balance()
                    status_msg += f"\n\n💎 TON баланс: {balance:.4f} TON"
                    if balance < settings.TON_RESERVE_MIN:
                        status_msg += f"\n⚠️ Баланс ниже минимального резерва ({settings.TON_RESERVE_MIN} TON)"

                await bot.send_message(admin_id, status_msg)
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
    else:
        logger.warning("No admin IDs configured")

    logger.success("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Actions on bot shutdown"""
    global ton_monitor

    logger.info("Bot is shutting down...")

    # Stop TON monitor
    if ton_monitor:
        try:
            await ton_monitor.stop()
            logger.info("TON monitor stopped")
        except Exception as e:
            logger.error(f"Error stopping TON monitor: {e}")

    # Close TON service
    try:
        await ton_service.close()
        logger.info("TON service closed")
    except Exception as e:
        logger.error(f"Error closing TON service: {e}")

    # Notify admins
    admin_ids = settings.get_admin_ids()
    if admin_ids:
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    "🤖 Бот остановлен"
                )
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
    else:
        logger.warning("No admin IDs configured")

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
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
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
