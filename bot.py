import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
import database as db
from handlers.common import router as common_router
from handlers.admin import router as admin_router
from handlers.delivery import router as delivery_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN .env faylida belgilanmagan!")

    await db.init_db()
    logger.info("Database initialized")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(delivery_router)

    logger.info("Honeymoon.uz bot ishga tushmoqda...")
    logger.info("Admin IDs: %s", ADMIN_IDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
