import sqlite3

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                show_id INTEGER,
                show_name TEXT,
                last_episode_id INTEGER DEFAULT 0,
                UNIQUE(user_id, show_id)
            )
        ''')
        # Миграция
        try:
            cursor.execute("ALTER TABLE subscriptions ADD COLUMN last_episode_id INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

    def add_subscription(self, user_id, show_id, show_name):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO subscriptions (user_id, show_id, show_name, last_episode_id) VALUES (?, ?, ?, 0)',
                (user_id, show_id, show_name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user_subscriptions(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT show_name, show_id FROM subscriptions WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_all_subscriptions(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, show_id, show_name, last_episode_id FROM subscriptions')
        rows = cursor.fetchall()
        conn.close()
        return rows

    def delete_subscription(self, user_id, show_name):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND show_name = ?', (user_id, show_name))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def update_last_episode(self, user_id, show_id, episode_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE subscriptions SET last_episode_id = ? WHERE user_id = ? AND show_id = ?',
                       (episode_id, user_id, show_id))
        conn.commit()
        conn.close()