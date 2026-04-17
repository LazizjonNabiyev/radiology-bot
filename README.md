# 🚀 Radiology AI Bot — Deploy Qo'llanmasi

## Bepul Server: Railway.app

Railway — 24/7 ishlaydi, oyiga $5 kredit bepul (bot uchun yetarli)

### 1-qadam: GitHub ga yuklash

```bash
git init
git add .
git commit -m "Radiology AI bot"
git branch -M main
git remote add origin https://github.com/USERNAME/radiology-bot.git
git push -u origin main
```

### 2-qadam: Railway setup

1. https://railway.app ga kiring
2. "New Project" → "Deploy from GitHub repo"
3. Repo ni tanlang
4. "Variables" bo'limiga o'ting:
   - `BOT_TOKEN` = telegram bot tokeningiz
   - `ANTHROPIC_API_KEY` = claude api key

### 3-qadam: Anthropic API Key (BEPUL)

1. https://console.anthropic.com ga kiring
2. "API Keys" → "Create Key"
3. Bepul $5 kredit bor (taxminan 500-1000 tahlil)
4. Ko'proq kerak bo'lsa: pay-as-you-go (1000 tahlil ≈ $0.5-1)

---

## 10,000-20,000 foydalanuvchi uchun maslahatlar

### Hozirgi arxitektura (0-5,000 users):
- Railway bepul tier ✅
- JSON database ✅  
- Async queue ✅

### 5,000-20,000 users:
- Railway Hobby plan ($5/oy)
- JSON → SQLite ga o'ting (database.py ni yangilang)
- Claude API rate limit: 50 req/min (yetarli)

### 20,000+ users:
- Railway Pro yoki VPS (Hetzner $4/oy)
- SQLite → PostgreSQL
- Redis queue (asyncio.Queue o'rniga)

---

## Queue tizimi qanday ishlaydi?

```
User 1 rasm yubordi → Navbat #1 → Tahlil qilinmoqda...
User 2 rasm yubordi → Navbat #2 → Kutmoqda...
User 3 rasm yubordi → Navbat #3 → Kutmoqda...

Worker: #1 tahlil → natija yuborildi → #2 ga o'tdi → ...
```

Hech kim "API limit" xatosi ko'rmaydi — hammasi navbatda kutadi.

---

## Kanal obuna tekshiruvi

Bot `@RadiologyAI` kanalini tekshiradi.
Agar foydalanuvchi obuna bo'lmasa → obuna tugmasi chiqadi.
Obuna bo'lgandan keyin → ro'yxatdan o'tish yoki rasm yuborish.

---

## Ro'yxatdan o'tish jarayoni

1. /start → obuna tekshirish
2. Til tanlash (UZ/RU/EN)
3. To'liq ism kiritish (Ism Familiya)
4. Telefon raqam ulashish
5. ✅ Ro'yxatdan o'tdi → rasm yuborishi mumkin

---

## Ishga tushirish (local test)

```bash
pip install -r requirements.txt
cp .env.example .env
# .env ni to'ldiring
python bot.py
```
