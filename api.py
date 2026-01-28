import aiohttp
import re
from config import TVMAZE_URL
from async_lru import alru_cache

class TVMazeClient:
    @staticmethod
    @alru_cache(maxsize=100)
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
        url = f"{TVMAZE_URL}/shows/{show_id}?embed=previousepisode"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if '_embedded' not in data or 'previousepisode' not in data['_embedded']:
                            return None

                        ep_data = data['_embedded']['previousepisode']
                        image_url = None
                        if data.get('image') and data['image'].get('medium'):
                            image_url = data['image']['medium']
                        ep_data['show_image'] = image_url

                        premiered = data.get('premiered')
                        if premiered:
                            ep_data['show_year'] = premiered[:4]
                        else:
                            ep_data['show_year'] = ""

                        return ep_data
            except Exception:
                return None
        return None

    @staticmethod
    async def get_next_episode(show_id):
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