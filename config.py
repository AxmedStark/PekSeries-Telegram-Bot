import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables!")

TVMAZE_URL = "https://api.tvmaze.com"
CHECK_INTERVAL = 60 * 15
DB_NAME = "series_bot.db"