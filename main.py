import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, DATABASE_URL  # <-- Берем URL
from database import Database
from handlers import router
from scheduler import UpdateChecker


async def main():
    logging.basicConfig(level=logging.INFO)

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не задан! Проверь переменные окружения.")

    db = Database(DATABASE_URL)

    await db.connect()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)
    dp["db"] = db

    checker = UpdateChecker(bot, db)
    asyncio.create_task(checker.start())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

#test