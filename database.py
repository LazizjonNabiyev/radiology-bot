"""
database.py — foydalanuvchilarni saqlash
JSON fayl asosida (bepul, server talab qilmaydi)
Kelajakda SQLite yoki PostgreSQL ga o'tish mumkin
"""

import json
import os
from typing import Optional, Dict, Any

DB_FILE = "users.json"


class Database:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f:
                json.dump({}, f)

    def _load(self) -> dict:
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data: dict):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data.get(str(user_id))

    def save_user(self, user_info: dict):
        data = self._load()
        user_id = str(user_info["user_id"])
        data[user_id] = user_info
        self._save(data)

    def get_user_lang(self, user_id: int) -> Optional[str]:
        user = self.get_user(user_id)
        return user.get("lang") if user else None

    def set_user_lang(self, user_id: int, lang: str):
        data = self._load()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        data[uid]["lang"] = lang
        self._save(data)

    def increment_analysis(self, user_id: int) -> int:
        data = self._load()
        uid = str(user_id)
        count = data.get(uid, {}).get("analysis_count", 0) + 1
        if uid in data:
            data[uid]["analysis_count"] = count
        self._save(data)
        return count

    def total_users(self) -> int:
        return len(self._load())


db = Database()
