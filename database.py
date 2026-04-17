"""
database.py — To'liq DB (foydalanuvchilar, reg holati, tahlil tarixi, to'lov)
"""
import json, os
from typing import Optional, Dict, Any, List
from datetime import datetime, date

USERS_FILE   = "users.json"
REG_FILE     = "reg_temp.json"
HISTORY_FILE = "history.json"

FREE_DAILY_LIMIT = 3   # kuniga bepul tahlil soni

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

    # ── KUNLIK LIMIT ──────────────────────────────────────────────────────────
    def get_today_count(self, user_id: int) -> int:
        """Bugun nechta bepul tahlil qilingan"""
        u = self.get_user(user_id)
        if not u:
            return 0
        today = date.today().isoformat()
        if u.get("last_free_date") != today:
            return 0
        return u.get("today_free_count", 0)

    def increment_today(self, user_id: int):
        data = self._load(USERS_FILE)
        uid = str(user_id)
        today = date.today().isoformat()
        u = data.get(uid, {})
        if u.get("last_free_date") != today:
            u["last_free_date"] = today
            u["today_free_count"] = 1
        else:
            u["today_free_count"] = u.get("today_free_count", 0) + 1
        data[uid] = u
        self._save(USERS_FILE, data)

    def is_premium(self, user_id: int) -> bool:
        u = self.get_user(user_id)
        if not u:
            return False
        exp = u.get("premium_until")
        if not exp:
            return False
        return exp >= date.today().isoformat()

    def set_premium(self, user_id: int, until_date: str):
        """until_date: '2026-05-18' formatda"""
        data = self._load(USERS_FILE)
        uid = str(user_id)
        if uid in data:
            data[uid]["premium_until"] = until_date
            data[uid]["premium"] = True
        self._save(USERS_FILE, data)

    def can_analyze(self, user_id: int) -> tuple:
        """(True/False, remaining_free) — tahlil qila oladimi?"""
        if self.is_premium(user_id):
            return True, 999
        today_count = self.get_today_count(user_id)
        remaining = FREE_DAILY_LIMIT - today_count
        return remaining > 0, remaining

    # ── RO'YXATDAN O'TISH HOLATI ──────────────────────────────────────────────
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

    # ── TAHLIL TARIXI ─────────────────────────────────────────────────────────
    def add_history(self, user_id: int, entry: dict):
        data = self._load(HISTORY_FILE)
        uid = str(user_id)
        if uid not in data:
            data[uid] = []
        data[uid].insert(0, entry)
        data[uid] = data[uid][:20]   # oxirgi 20 ta
        self._save(HISTORY_FILE, data)

    def get_history(self, user_id: int) -> List[dict]:
        return self._load(HISTORY_FILE).get(str(user_id), [])

db = Database()
