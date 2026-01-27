import asyncpg
import logging

class Database:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        """Создает пул соединений к базе"""
        try:
            self.pool = await asyncpg.create_pool(self.dsn)
            await self._init_db()
            logging.info("✅ Успешное подключение к PostgreSQL")
        except Exception as e:
            logging.error(f"❌ Ошибка подключения к БД: {e}")
            raise e

    async def _init_db(self):
        """Создает таблицы, если их нет"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id BIGINT,
                    show_id BIGINT,
                    show_name TEXT,
                    last_episode_id BIGINT DEFAULT 0,
                    UNIQUE(user_id, show_id)
                )
            ''')

    async def add_subscription(self, user_id, show_id, show_name):
        try:
            # Используем $1, $2, $3 вместо ?
            await self.pool.execute(
                'INSERT INTO subscriptions (user_id, show_id, show_name, last_episode_id) VALUES ($1, $2, $3, 0)',
                user_id, show_id, show_name
            )
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def get_user_subscriptions(self, user_id):
        # fetch возвращает список записей
        rows = await self.pool.fetch('SELECT show_name, show_id FROM subscriptions WHERE user_id = $1', user_id)
        return rows # asyncpg возвращает объекты Record, они ведут себя как кортежи/словари

    async def get_all_subscriptions(self):
        rows = await self.pool.fetch('SELECT user_id, show_id, show_name, last_episode_id FROM subscriptions')
        return rows

    async def delete_subscription(self, user_id, show_name):
        result = await self.pool.execute(
            'DELETE FROM subscriptions WHERE user_id = $1 AND show_name = $2',
            user_id, show_name
        )
        # result возвращает строку типа "DELETE 1"
        return "DELETE 0" not in result

    async def update_last_episode(self, user_id, show_id, episode_id):
        await self.pool.execute(
            'UPDATE subscriptions SET last_episode_id = $1 WHERE user_id = $2 AND show_id = $3',
            episode_id, user_id, show_id
        )

    async def get_stats(self):
        users_count = await self.pool.fetchval('SELECT COUNT(DISTINCT user_id) FROM subscriptions')
        subs_count = await self.pool.fetchval('SELECT COUNT(*) FROM subscriptions')
        return users_count, subs_count