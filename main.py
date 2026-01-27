import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, DB_NAME
from database import Database
from handlers import router
from scheduler import UpdateChecker

async def main():
    logging.basicConfig(level=logging.INFO)

    # 1. Инициализация базы данных
    db = Database(DB_NAME)

    # 2. Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # 3. Подключаем роутер с хендлерами
    dp.include_router(router)

    # ВАЖНО: Внедряем базу данных в хендлеры
    # Теперь во всех функциях handlers.py аргумент `db` будет доступен автоматически
    dp["db"] = db

    # 4. Запускаем чекер обновлений
    checker = UpdateChecker(bot, db)
    asyncio.create_task(checker.start())

    # 5. Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())