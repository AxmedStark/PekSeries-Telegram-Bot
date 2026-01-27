import aiohttp
import re
from config import TVMAZE_URL


class TVMazeClient:
    @staticmethod
    async def search_show(query):
        async with aiohttp.ClientSession() as session:
            # search by link
            link_match = re.search(r'tvmaze\.com/shows/(\d+)', query)

            if link_match:
                show_id = link_match.group(1)
                url = f"{TVMAZE_URL}/shows/{show_id}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['id'], data['name'], data['url']
            else:
                # search by name
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
    async def get_latest_episode(show_id):
        url = f"{TVMAZE_URL}/shows/{show_id}?embed=previousepisode"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if '_embedded' in data and 'previousepisode' in data['_embedded']:
                            return data['_embedded']['previousepisode']
            except Exception:
                return None
        return None