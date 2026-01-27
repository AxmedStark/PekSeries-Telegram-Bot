import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables!")

ADMIN_ID = os.environ.get('ADMIN_ID')
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = None
    print("⚠️ ADMIN_ID не найден в переменных окружения! Админка работать не будет.")

TVMAZE_URL = "https://api.tvmaze.com"
CHECK_INTERVAL = 60 * 60  # 1 час
DB_NAME = "series_bot.db"