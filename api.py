import aiohttp
import re
from config import TVMAZE_URL


class TVMazeClient:
    @staticmethod
    async def search_show(query):
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

    @staticmethod
    async def get_latest_episode_with_info(show_id):
        """Возвращает данные о серии + постер сериала"""
        # Запрашиваем шоу И прошлую серию одним запросом
        url = f"{TVMAZE_URL}/shows/{show_id}?embed=previousepisode"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Берем картинку сериала (если есть)
                        image_url = None
                        if data.get('image') and data['image'].get('medium'):
                            image_url = data['image']['medium']

                        if '_embedded' in data and 'previousepisode' in data['_embedded']:
                            ep_data = data['_embedded']['previousepisode']
                            ep_data['show_image'] = image_url  # Добавляем картинку к данным серии
                            return ep_data
            except Exception:
                return None
        return None

    @staticmethod
    async def get_next_episode(show_id):
        """Ищет следующую запланированную серию"""
        url = f"{TVMAZE_URL}/shows/{show_id}?embed=nextepisode"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if '_embedded' in data and 'nextepisode' in data['_embedded']:
                            return data['_embedded']['nextepisode']
            except Exception:
                pass
        return None