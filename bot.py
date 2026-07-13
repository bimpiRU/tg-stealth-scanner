import asyncio
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import admin_router, osint_router, recon_router, scan_router, utils_router
from middlewares import AdminMiddleware, RateLimitMiddleware
from utils.logger import logger


from handlers.admin import set_bot_commands


async def on_startup(bot: Bot) -> None:
    logger.info("Bot started. Admin ID: %s", config.ADMIN_ID)
    await set_bot_commands(bot)
    await bot.send_message(
        config.ADMIN_ID,
        "👁 Stealth scanner is online and ready.",
    )


async def on_shutdown(bot: Bot) -> None:
    logger.info("Bot shutting down...")
    try:
        await bot.send_message(config.ADMIN_ID, "🛑 Stealth scanner is shutting down.")
    except Exception as exc:
        logger.warning("Could not send shutdown notification: %s", exc)
    await bot.session.close()


def main() -> None:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Global middleware: admin filter and rate limit
    dp.message.middleware(AdminMiddleware())
    dp.message.middleware(RateLimitMiddleware())

    dp.include_router(admin_router)
    dp.include_router(osint_router)
    dp.include_router(recon_router)
    dp.include_router(scan_router)
    dp.include_router(utils_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Graceful shutdown on SIGTERM/SIGINT
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(dp.stop_polling()))

    try:
        loop.run_until_complete(dp.start_polling(bot))
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
