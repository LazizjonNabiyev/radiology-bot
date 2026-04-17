"""
database.py
Foydalanuvchilar + ro'yxatdan o'tish holati JSON da saqlanadi.
context.user_data ishlatilmaydi - chunki Railway restart bo'lsa yo'qoladi.
"""
import json, os
from typing import Optional, Dict, Any

USERS_FILE = "users.json"
REG_FILE   = "reg_temp.json"   # vaqtinchalik ro'yxatdan o'tish holati

class Database:
    def _load(self, path) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save(self, path, data: dict):
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── FOYDALANUVCHILAR ──────────────────────────────────────────────────────
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._load(USERS_FILE).get(str(user_id))

    def save_user(self, info: dict):
        data = self._load(USERS_FILE)
        data[str(info["user_id"])] = info
        self._save(USERS_FILE, data)

    def get_user_lang(self, user_id: int) -> Optional[str]:
        u = self.get_user(user_id)
        return u.get("lang") if u else None

    def set_user_lang(self, user_id: int, lang: str):
        data = self._load(USERS_FILE)
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        data[uid]["lang"] = lang
        self._save(USERS_FILE, data)

    def increment_analysis(self, user_id: int) -> int:
        data = self._load(USERS_FILE)
        uid = str(user_id)
        count = data.get(uid, {}).get("analysis_count", 0) + 1
        if uid in data:
            data[uid]["analysis_count"] = count
        self._save(USERS_FILE, data)
        return count

    # ── RO'YXATDAN O'TISH HOLATI (DB DA) ─────────────────────────────────────
    def get_reg_data(self, user_id: int) -> dict:
        return self._load(REG_FILE).get(str(user_id), {"step": "lang"})

    def set_reg_step(self, user_id: int, step: str):
        data = self._load(REG_FILE)
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        data[uid]["step"] = step
        self._save(REG_FILE, data)

    def set_reg_data(self, user_id: int, reg_data: dict):
        data = self._load(REG_FILE)
        data[str(user_id)] = reg_data
        self._save(REG_FILE, data)

    def clear_reg_data(self, user_id: int):
        data = self._load(REG_FILE)
        data.pop(str(user_id), None)
        self._save(REG_FILE, data)

db = Database()
