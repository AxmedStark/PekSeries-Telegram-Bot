import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from config import BOT_TOKEN, DATABASE_URL
from database import Database
from handlers import router
from scheduler import UpdateChecker

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Start bot"),
        BotCommand(command="add", description="➕ Add series"),
        BotCommand(command="list", description="📋 My list"),
        BotCommand(command="calendar", description="📅 Calendar"),
        BotCommand(command="help", description="ℹ️ Help")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def main():
    logging.basicConfig(level=logging.INFO)

    if not DATABASE_URL:
        raise ValueError("NO_DATABASE_URL_ERROR")

    db = Database(DATABASE_URL)

    await db.connect()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)
    dp["db"] = db

    await set_commands(bot)

    checker = UpdateChecker(bot, db)
    asyncio.create_task(checker.start())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())