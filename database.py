"""
database.py — SQLite asosida (Railway Volume bilan persistent)
"""
import sqlite3
import os
from typing import Optional, Dict, Any

DB_FILE = "/data/users.db"

class Database:
    def __init__(self):
        os.makedirs("/data", exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(DB_FILE)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     TEXT PRIMARY KEY,
                    username    TEXT DEFAULT '',
                    full_name   TEXT DEFAULT '',
                    phone       TEXT DEFAULT '',
                    lang        TEXT DEFAULT 'uz',
                    registered_at TEXT DEFAULT '',
                    analysis_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (str(user_id),)
            ).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "phone": row[3],
            "lang": row[4],
            "registered_at": row[5],
            "analysis_count": row[6]
        }

    def save_user(self, user_info: dict):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, full_name, phone, lang, registered_at, analysis_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    phone = excluded.phone,
                    lang = excluded.lang,
                    registered_at = excluded.registered_at
            """, (
                str(user_info["user_id"]),
                user_info.get("username", ""),
                user_info.get("full_name", ""),
                user_info.get("phone", ""),
                user_info.get("lang", "uz"),
                user_info.get("registered_at", ""),
                user_info.get("analysis_count", 0)
            ))
            conn.commit()

    def get_user_lang(self, user_id: int) -> Optional[str]:
        user = self.get_user(user_id)
        return user.get("lang") if user else None

    def set_user_lang(self, user_id: int, lang: str):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO users (user_id, lang) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang
            """, (str(user_id), lang))
            conn.commit()

    def increment_analysis(self, user_id: int) -> int:
        with self._conn() as conn:
            conn.execute("""
                UPDATE users SET analysis_count = analysis_count + 1
                WHERE user_id = ?
            """, (str(user_id),))
            conn.commit()
            row = conn.execute(
                "SELECT analysis_count FROM users WHERE user_id = ?", (str(user_id),)
            ).fetchone()
        return row[0] if row else 1

    def total_users(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

db = Database()
