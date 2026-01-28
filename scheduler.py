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
        logging.info("🚀 Planner started")
        while True:
            try:
                logging.info("⏳ Check updates...")

                subs = await self.db.get_all_subscriptions()
                unique_show_ids = set(sub[1] for sub in subs)

                latest_episodes = {}
                for show_id in unique_show_ids:
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

                logging.info(f"✅ Check completed. Next check in {CHECK_INTERVAL} sec.")

            except Exception as e:
                logging.error(f"⚠️ Critic error in planner: {e}")
                await asyncio.sleep(60)
                continue

            await asyncio.sleep(CHECK_INTERVAL)

    async def _send_notification(self, user_id, show_name, ep):
        raw_summary = ep.get('summary', '')
        clean_summary = ""
        if raw_summary:
            clean_summary = re.sub(r'<[^>]+>', '', raw_summary)
            if len(clean_summary) > 200:
                clean_summary = clean_summary[:200] + "..."

        year = ep.get('show_year', '')
        year_str = f" ({year})" if year else ""

        msg = (
            f"🔥 <b>New Episode!</b>\n"
            f"🎬 Series: <b>{show_name}{year_str}</b>\n"
            f"🔢 Season {ep.get('season')} - Episode{ep.get('number')}\n"
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
            logging.error(f"Send error {user_id}: {e}")