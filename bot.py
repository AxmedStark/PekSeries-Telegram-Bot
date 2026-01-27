import os
import asyncio
import logging
import sqlite3
import re
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import aiohttp
from datetime import datetime

BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Error handling to help you debug
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables!")

TVMAZE_URL = "https://api.tvmaze.com"
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    # !!! НОВОЕ !!! Добавили колонку last_episode_id
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS subscriptions
                   (
                       user_id
                       INTEGER,
                       show_id
                       INTEGER,
                       show_name
                       TEXT,
                       last_episode_id
                       INTEGER
                       DEFAULT
                       0,
                       UNIQUE
                   (
                       user_id,
                       show_id
                   )
                       )
                   ''')

    # Миграция для старой базы (если ты уже запускал бота)
    # Пытаемся добавить колонку, если её нет
    try:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN last_episode_id INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Колонка уже есть

    conn.commit()
    conn.close()


def add_subscription(user_id, show_id, show_name):
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    try:
        # При добавлении сразу ставим 0, чтобы при первой проверке бот нашел новую серию
        cursor.execute('INSERT INTO subscriptions (user_id, show_id, show_name, last_episode_id) VALUES (?, ?, ?, 0)',
                       (user_id, show_id, show_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_all_subscriptions():
    """Получает все подписки всех пользователей для проверки"""
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, show_id, show_name, last_episode_id FROM subscriptions')
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_last_episode(user_id, show_id, episode_id):
    """Обновляет ID последней серии, чтобы не спамить"""
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE subscriptions SET last_episode_id = ? WHERE user_id = ? AND show_id = ?',
                   (episode_id, user_id, show_id))
    conn.commit()
    conn.close()


# ... (функции get_subscriptions и delete_subscription остаются без изменений, см. прошлый код) ...
def get_subscriptions(user_id):
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT show_name, show_id FROM subscriptions WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_subscription(user_id, show_name):
    conn = sqlite3.connect('series_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND show_name = ?', (user_id, show_name))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# --- API ---
async def search_tvmaze(query):
    # (Код поиска без изменений)
    async with aiohttp.ClientSession() as session:
        link_match = re.search(r'tvmaze\.com/shows/(\d+)', query)
        if link_match:
            show_id = link_match.group(1)
            url = f"{TVMAZE_URL}/shows/{show_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['id'], data['name'], data['url']
        else:
            url = f"{TVMAZE_URL}/search/shows"
            params = {'q': query}
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        show = data[0]['show']
                        return show['id'], show['name'], show['url']
    return None, None, None


# !!! НОВОЕ !!! ФУНКЦИЯ ПРОВЕРКИ ОБНОВЛЕНИЙ
async def check_updates():
    while True:
        logging.info("⏳ Начинаю проверку новых серий...")
        subs = get_all_subscriptions()

        # Чтобы не дергать API для одного и того же сериала много раз,
        # сначала соберем уникальные ID сериалов, которые надо проверить
        unique_show_ids = set(sub[1] for sub in subs)

        # Словарь для хранения инфы о новых сериях: {show_id: episode_data}
        latest_episodes = {}

        async with aiohttp.ClientSession() as session:
            for show_id in unique_show_ids:
                # Запрашиваем инфу о сериале и ВКЛЮЧАЕМ предыдущий эпизод (previousepisode)
                url = f"{TVMAZE_URL}/shows/{show_id}?embed=previousepisode"
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Если есть инфа о предыдущем эпизоде
                            if '_embedded' in data and 'previousepisode' in data['_embedded']:
                                latest_episodes[show_id] = data['_embedded']['previousepisode']
                except Exception as e:
                    logging.error(f"Ошибка при проверке show_id {show_id}: {e}")

                # Небольшая пауза, чтобы не дудосить API
                await asyncio.sleep(0.5)

        # Теперь рассылаем уведомления
        for user_id, show_id, show_name, last_ep_id in subs:
            if show_id in latest_episodes:
                ep_data = latest_episodes[show_id]
                current_ep_id = ep_data['id']

                # Если ID серии изменился и он больше старого — значит вышла новая!
                if current_ep_id != last_ep_id:
                    season = ep_data.get('season')
                    number = ep_data.get('number')
                    title = ep_data.get('name')

                    msg = (
                        f"🔥 <b>Вышла новая серия!</b>\n"
                        f"🎬 Сериал: <b>{show_name}</b>\n"
                        f"🔢 Сезон {season}, Серия {number}\n"
                        f"📝 Название: {title}"
                    )

                    try:
                        await bot.send_message(user_id, msg, parse_mode="HTML")
                        # Запоминаем, что об этой серии сообщили
                        update_last_episode(user_id, show_id, current_ep_id)
                    except Exception as e:
                        logging.error(f"Не удалось отправить сообщение юзеру {user_id}: {e}")

        logging.info("✅ Проверка завершена. Следующая через час.")
        await asyncio.sleep(CHECK_INTERVAL)


# --- ХЕНДЛЕРЫ (те же самые) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("/add <название> - подписаться\n/list - список\n/del <название> - удалить")


@dp.message(Command("add"))
async def cmd_add(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("Пример: /add Lost")

    query = args[1]
    msg = await message.answer("Ищу...")
    sid, name, url = await search_tvmaze(query)

    if sid:
        if add_subscription(message.from_user.id, sid, name):
            await msg.edit_text(f"Подписался на {name}!")
        else:
            await msg.edit_text("Уже подписан.")
    else:
        await msg.edit_text("Не нашел.")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    subs = get_subscriptions(message.from_user.id)
    if not subs: return await message.answer("Пусто.")
    await message.answer("\n".join([f"• {s[0]}" for s in subs]))


@dp.message(Command("del"))
async def cmd_del(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("Пример: /del Lost")
    if delete_subscription(message.from_user.id, args[1]):
        await message.answer(f"Удалил {args[1]}")
    else:
        await message.answer("Не нашел.")


# --- ЗАПУСК ---
async def main():
    init_db()

    # !!! НОВОЕ !!!
    # Запускаем функцию проверки в фоновом режиме
    asyncio.create_task(check_updates())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

