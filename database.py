"""
database.py — To'liq DB (foydalanuvchilar, reg holati, tahlil tarixi, to'lov)
"""
import json, os
from typing import Optional, Dict, Any, List
from datetime import datetime, date

# Persistent storage
# Railway da Volume ulash: Settings → Volumes → mount path: /data
# Volume yo'q bo'lsa — bot ishlayotgan papkada saqlaydi
def _get_data_dir():
    # 1. Muhit o'zgaruvchisi berilgan bo'lsa
    if os.getenv("DATA_DIR"):
        d = os.getenv("DATA_DIR")
        os.makedirs(d, exist_ok=True)
        return d
    # 2. Railway volume ulangan bo'lsa
    if os.path.isdir("/data") and os.access("/data", os.W_OK):
        return "/data"
    # 3. Fallback — bot papkasi
    return "."

_DATA_DIR    = _get_data_dir()
USERS_FILE   = os.path.join(_DATA_DIR, "users.json")
REG_FILE     = os.path.join(_DATA_DIR, "reg_temp.json")
HISTORY_FILE = os.path.join(_DATA_DIR, "history.json")

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

    def get_stats(self) -> dict:
        """Umumiy statistika"""
        users = self._load(USERS_FILE)
        history = self._load(HISTORY_FILE)
        
        total_users = len(users)
        premium_users = sum(1 for u in users.values() if u.get("premium_until", "") >= date.today().isoformat())
        free_users = total_users - premium_users
        
        total_analyses = sum(u.get("analysis_count", 0) for u in users.values())
        
        # Bugun ro'yxatdan o'tganlar
        today = date.today().isoformat()
        today_registered = sum(
            1 for u in users.values()
            if (u.get("registered_at") or "")[:10] == today
        )
        
        # Bugun tahlil qilganlar
        today_active = sum(
            1 for u in users.values()
            if u.get("last_free_date") == today and u.get("today_free_count", 0) > 0
        )
        
        # Tillar bo'yicha
        langs = {"uz": 0, "ru": 0, "en": 0}
        for u in users.values():
            lang = u.get("lang", "uz")
            if lang in langs:
                langs[lang] += 1
        
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "free_users": free_users,
            "total_analyses": total_analyses,
            "today_registered": today_registered,
            "today_active": today_active,
            "langs": langs,
        }

db = Database()
