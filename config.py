import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("NO_BOT_TOKEN_ERROR")

admin_env = os.environ.get('ADMIN_ID')
ADMIN_ID = int(admin_env) if admin_env else None

DATABASE_URL = os.environ.get('DATABASE_URL')

TVMAZE_URL = "https://api.tvmaze.com"
CHECK_INTERVAL = 60 * 15