import asyncio
import logging
import re
from config import CHECK_INTERVAL
from api import TVMazeClient


class UpdateChecker:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def start(self):
        while True:
            logging.info("⏳ Проверка обновлений...")
            subs = await self.db.get_all_subscriptions()
            unique_show_ids = set(sub[1] for sub in subs)

            latest_episodes = {}
            for show_id in unique_show_ids:
                # Используем новый метод, который возвращает и постер
                ep_data = await TVMazeClient.get_latest_episode_with_info(show_id)
                if ep_data:
                    latest_episodes[show_id] = ep_data
                await asyncio.sleep(0.5)

            for user_id, show_id, show_name, last_ep_id in subs:
                if show_id in latest_episodes:
                    ep = latest_episodes[show_id]
                    if ep['id'] != last_ep_id:
                        await self._send_notification(user_id, show_name, ep)
                        await self.db.update_last_episode(user_id, show_id, ep['id'])

            logging.info(f"✅ Готово. Спим {CHECK_INTERVAL} сек.")
            await asyncio.sleep(CHECK_INTERVAL)

    async def _send_notification(self, user_id, show_name, ep):
        # Очистка Summary от HTML тегов (<p>, <b>)
        raw_summary = ep.get('summary', '')
        clean_summary = ""
        if raw_summary:
            clean_summary = re.sub(r'<[^>]+>', '', raw_summary)
            if len(clean_summary) > 200:
                clean_summary = clean_summary[:200] + "..."

        msg = (
            f"🔥 <b>Вышла новая серия!</b>\n"
            f"🎬 Сериал: <b>{show_name}</b>\n"
            f"🔢 {ep.get('season')} сезон, {ep.get('number')} серия\n"
            f"📝 <b>{ep.get('name')}</b>\n\n"
            f"<i>{clean_summary}</i>"
        )

        try:
            image_url = ep.get('show_image')
            if image_url:
                await self.bot.send_photo(user_id, photo=image_url, caption=msg, parse_mode="HTML")
            else:
                await self.bot.send_message(user_id, msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отправки {user_id}: {e}")