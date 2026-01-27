from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from api import TVMazeClient

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("/add <название> - подписаться\n/list - список\n/del <название> - удалить")


@router.message(Command("add"))
async def cmd_add(message: Message, db):  # db прилетит сюда через middleware (см. main.py)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Пример: /add Lost")

    query = args[1]
    msg = await message.answer("Ищу...")

    # Используем наш класс API
    sid, name, url = await TVMazeClient.search_show(query)

    if sid:
        if db.add_subscription(message.from_user.id, sid, name):
            await msg.edit_text(f"Подписался на {name}!")
        else:
            await msg.edit_text("Уже подписан.")
    else:
        await msg.edit_text("Не нашел.")


@router.message(Command("list"))
async def cmd_list(message: Message, db):
    subs = db.get_user_subscriptions(message.from_user.id)
    if not subs:
        return await message.answer("Пусто.")
    await message.answer("\n".join([f"• {s[0]}" for s in subs]))


@router.message(Command("del"))
async def cmd_del(message: Message, db):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Пример: /del Lost")

    if db.delete_subscription(message.from_user.id, args[1]):
        await message.answer(f"Удалил {args[1]}")
    else:
        await message.answer("Не нашел.")