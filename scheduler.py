import asyncio
import logging
from config import CHECK_INTERVAL
from api import TVMazeClient


class UpdateChecker:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def start(self):
        while True:
            logging.info("⏳ Проверка обновлений...")
            subs = self.db.get_all_subscriptions()
            unique_show_ids = set(sub[1] for sub in subs)

            # Собираем данные
            latest_episodes = {}
            for show_id in unique_show_ids:
                ep_data = await TVMazeClient.get_latest_episode(show_id)
                if ep_data:
                    latest_episodes[show_id] = ep_data
                await asyncio.sleep(0.5)  # Вежливость к API

            # Рассылаем
            for user_id, show_id, show_name, last_ep_id in subs:
                if show_id in latest_episodes:
                    ep = latest_episodes[show_id]
                    if ep['id'] != last_ep_id:
                        await self._send_notification(user_id, show_name, ep)
                        self.db.update_last_episode(user_id, show_id, ep['id'])

            logging.info(f"✅ Готово. Спим {CHECK_INTERVAL} сек.")
            await asyncio.sleep(CHECK_INTERVAL)

    async def _send_notification(self, user_id, show_name, ep):
        msg = (
            f"🔥 <b>Вышла новая серия!</b>\n"
            f"🎬 {show_name}\n"
            f"S{ep['season']} E{ep['number']} — {ep['name']}"
        )
        try:
            await self.bot.send_message(user_id, msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отправки {user_id}: {e}") 