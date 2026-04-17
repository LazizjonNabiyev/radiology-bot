import asyncio
import logging
import base64
import httpx
import os
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from database import db
from queue_manager import AnalysisQueue

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN          = os.getenv("BOT_TOKEN", "BOT_TOKENINGIZ")
SUBSCRIBE_CH   = os.getenv("SUBSCRIBE_CHANNEL", "@RadiologyGroupChat")
LOG_CH         = os.getenv("LOG_CHANNEL", "@RadialogyAI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

queue = AnalysisQueue()

# ─── SUBSCRIPTION ─────────────────────────────────────────────────────────────
async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=SUBSCRIBE_CH, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ─── TEXTS ────────────────────────────────────────────────────────────────────
def t(lang, key):
    texts = {
        "uz": {
            "welcome":     "👋 *Radiology AI*ga xush kelibsiz!\n\nTilni tanlang:",
            "ask_name":    "📝 To'liq ismingizni kiriting:\n_Misol: Alisher Nazarov_",
            "ask_age":     "🎂 Yoshingizni kiriting:\n_Misol: 35_",
            "ask_phone":   "📱 Telefon raqamingizni yuboring:",
            "registered":  "✅ Ro'yxatdan o'tdingiz!\n\nEndi MRT / MSKT / Rentgen rasmi yoki PDF hujjatini yuboring 📸",
            "not_sub":     f"⚠️ Botdan foydalanish uchun kanalga obuna bo'ling:\n\n👉 {SUBSCRIBE_CH}\n\nObuna bo'lgach /start bosing.",
            "send_file":   "📸 MRT, MSKT, Rentgen rasmi yoki PDF/DOC hujjat yuboring",
            "in_queue":    "⏳ Navbatga qo'shildi!\n🔢 Navbatingiz: #{pos}\n\nBirozdan keyin natija yuboriladi ⏱",
            "processing":  "🔬 Tahlil qilinmoqda...",
            "error":       "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
            "sub_btn":     "📢 Kanalga obuna bo'lish",
            "check_btn":   "✅ Obunani tekshirish",
            "phone_btn":   "📱 Raqamni ulashish",
            "name_err":    "⚠️ Ism va Familiyangizni kiriting\n_Misol: Alisher Nazarov_",
            "age_err":     "⚠️ Faqat raqam kiriting\n_Misol: 35_",
            "start_first": "⚠️ Avval /start bosib ro'yxatdan o'ting",
            "no_text_doc": "⚠️ Bu hujjatda o'qiladigan matn topilmadi.",
        },
        "ru": {
            "welcome":     "👋 Добро пожаловать в *Radiology AI*!\n\nВыберите язык:",
            "ask_name":    "📝 Введите полное имя:\n_Пример: Алишер Назаров_",
            "ask_age":     "🎂 Введите ваш возраст:\n_Пример: 35_",
            "ask_phone":   "📱 Поделитесь номером телефона:",
            "registered":  "✅ Вы зарегистрированы!\n\nОтправьте снимок МРТ / КТ / Рентген или PDF документ 📸",
            "not_sub":     f"⚠️ Подпишитесь на канал:\n\n👉 {SUBSCRIBE_CH}\n\nПосле подписки нажмите /start.",
            "send_file":   "📸 Отправьте снимок МРТ, КТ, Рентген или PDF/DOC документ",
            "in_queue":    "⏳ Добавлено в очередь!\n🔢 Ваш номер: #{pos}\n\nРезультат придёт скоро ⏱",
            "processing":  "🔬 Анализируется...",
            "error":       "❌ Произошла ошибка. Попробуйте снова.",
            "sub_btn":     "📢 Подписаться на канал",
            "check_btn":   "✅ Проверить подписку",
            "phone_btn":   "📱 Поделиться номером",
            "name_err":    "⚠️ Введите Имя и Фамилию\n_Пример: Алишер Назаров_",
            "age_err":     "⚠️ Введите только число\n_Пример: 35_",
            "start_first": "⚠️ Сначала нажмите /start для регистрации",
            "no_text_doc": "⚠️ В документе не найден читаемый текст.",
        },
        "en": {
            "welcome":     "👋 Welcome to *Radiology AI*!\n\nChoose language:",
            "ask_name":    "📝 Enter your full name:\n_Example: John Smith_",
            "ask_age":     "🎂 Enter your age:\n_Example: 35_",
            "ask_phone":   "📱 Share your phone number:",
            "registered":  "✅ Registration complete!\n\nSend your MRI / CT / X-Ray or PDF document 📸",
            "not_sub":     f"⚠️ Subscribe to our channel first:\n\n👉 {SUBSCRIBE_CH}\n\nThen press /start.",
            "send_file":   "📸 Send MRI, CT, X-Ray image or PDF/DOC document",
            "in_queue":    "⏳ Added to queue!\n🔢 Your position: #{pos}\n\nResult coming soon ⏱",
            "processing":  "🔬 Analyzing...",
            "error":       "❌ An error occurred. Please try again.",
            "sub_btn":     "📢 Subscribe to channel",
            "check_btn":   "✅ Check subscription",
            "phone_btn":   "📱 Share phone number",
            "name_err":    "⚠️ Enter First and Last name\n_Example: John Smith_",
            "age_err":     "⚠️ Enter numbers only\n_Example: 35_",
            "start_first": "⚠️ Please press /start to register first",
            "no_text_doc": "⚠️ No readable text found in this document.",
        },
    }
    return texts.get(lang, texts["uz"]).get(key, "")

# ─── GEMINI: RASM TAHLIL ──────────────────────────────────────────────────────
async def analyze_image_gemini(image_bytes: bytes, lang: str, age: str = "") -> str:
    age_note = f" Bemor yoshi: {age}." if age and age != "—" else ""

    prompts = {
        "uz": f"""Siz mutaxassis radiolog shifokor sifatida quyidagi tibbiy tasvirni tahlil qiling.{age_note}
Javobingiz FAQAT quyidagi formatda bo'lsin:

🖼 *Rasm turi:*
[MRT / MSKT / Rentgen; qaysi a'zo]

🔬 *Ko'rinayotgan tuzilmalar:*
[Anatomik tuzilmalar, to'qimalar]

📋 *Topilmalar:*
[Normal va patologik o'zgarishlar]

⚠️ *Diqqat:*
[Shubhali o'zgarishlar yoki "Belirgin patologiya aniqlanmadi"]

💊 *Tavsiya:*
[Qaysi mutaxassisga murojaat; qo'shimcha tekshiruvlar]

⚕️ _Bu AI tahlili, rasmiy tashxis emas. Aniq tashxis uchun shifokorga murojaat qiling._""",

        "ru": f"""Вы — опытный врач-радиолог. Проанализируйте медицинский снимок.{age_note}
Ответ ТОЛЬКО в этом формате:

🖼 *Тип снимка:*
[МРТ / КТ / Рентген; какой орган]

🔬 *Видимые структуры:*
[Анатомические структуры, ткани]

📋 *Находки:*
[Нормальные и патологические изменения]

⚠️ *Внимание:*
[Подозрительные изменения или "Значимой патологии не выявлено"]

💊 *Рекомендации:*
[К какому специалисту; дополнительные исследования]

⚕️ _Это AI-анализ, не официальный диагноз. Обратитесь к врачу._""",

        "en": f"""You are an experienced radiologist. Analyze this medical image.{age_note}
Reply ONLY in this format:

🖼 *Image Type:*
[MRI / CT / X-Ray; which organ]

🔬 *Visible Structures:*
[Anatomical structures, tissues]

📋 *Findings:*
[Normal and abnormal changes]

⚠️ *Concern:*
[Suspicious changes or "No significant pathology detected"]

💊 *Recommendation:*
[Which specialist; additional studies]

⚕️ _This is AI analysis, not an official diagnosis. Consult a physician._""",
    }

    prompt = prompts.get(lang, prompts["uz"])
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini image parse error: {e}")
            return None
    logger.error(f"Gemini image error: {r.status_code} {r.text[:300]}")
    return None

# ─── GEMINI: MATN (PDF/DOC) TAHLIL ───────────────────────────────────────────
async def analyze_text_gemini(doc_text: str, lang: str, age: str = "") -> str:
    age_note = f" Bemor yoshi: {age}." if age and age != "—" else ""

    prompts = {
        "uz": f"""Siz mutaxassis radiolog yoki tibbiyot eksperti sifatida quyidagi tibbiy hujjatni tahlil qiling.{age_note}
Hujjat matni:
---
{doc_text[:4000]}
---
Javobingiz FAQAT quyidagi formatda bo'lsin:

📄 *Hujjat turi:*
[MRT / MSKT / Rentgen xulosa yoki boshqa tibbiy hujjat]

📋 *Asosiy topilmalar:*
[Hujjatdagi muhim ma'lumotlar]

⚠️ *Diqqat:*
[Patologik o'zgarishlar yoki "Belirgin patologiya aniqlanmadi"]

💊 *Tavsiya:*
[Qaysi mutaxassisga murojaat; keyingi qadamlar]

⚕️ _Bu AI tahlili, rasmiy tashxis emas. Aniq tashxis uchun shifokorga murojaat qiling._""",

        "ru": f"""Вы — медицинский эксперт. Проанализируйте следующий медицинский документ.{age_note}
Текст документа:
---
{doc_text[:4000]}
---
Ответ ТОЛЬКО в этом формате:

📄 *Тип документа:*
[МРТ / КТ / Рентген заключение или другой документ]

📋 *Основные находки:*
[Важные данные из документа]

⚠️ *Внимание:*
[Патологические изменения или "Значимой патологии не выявлено"]

💊 *Рекомендации:*
[К какому специалисту; следующие шаги]

⚕️ _Это AI-анализ, не официальный диагноз. Обратитесь к врачу._""",

        "en": f"""You are a medical expert. Analyze the following medical document.{age_note}
Document text:
---
{doc_text[:4000]}
---
Reply ONLY in this format:

📄 *Document Type:*
[MRI / CT / X-Ray report or other document]

📋 *Key Findings:*
[Important information from the document]

⚠️ *Concern:*
[Pathological changes or "No significant pathology detected"]

💊 *Recommendation:*
[Which specialist; next steps]

⚕️ _This is AI analysis, not an official diagnosis. Consult a physician._""",
    }

    prompt = prompts.get(lang, prompts["uz"])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini text parse error: {e}")
            return None
    logger.error(f"Gemini text error: {r.status_code} {r.text[:300]}")
    return None

# ─── PDF MATN AJRATISH ────────────────────────────────────────────────────────
def extract_pdf_text(file_bytes: bytes) -> str:
    """PDF dan matn ajratish (pypdf)"""
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        return ""

def extract_docx_text(file_bytes: bytes) -> str:
    """DOCX dan matn ajratish (python-docx)"""
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f"DOCX extract error: {e}")
        return ""

# ─── HANDLERS ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang,"sub_btn"), url=f"https://t.me/{SUBSCRIBE_CH.lstrip('@')}")],
            [InlineKeyboardButton(t(lang,"check_btn"), callback_data="check_sub")]
        ])
        await update.message.reply_text(t(lang,"not_sub"), reply_markup=kb)
        return

    user_data = db.get_user(user_id)
    if user_data and user_data.get("registered"):
        await update.message.reply_text(t(user_data.get("lang","uz"),"send_file"), parse_mode="Markdown")
        return

    # Ro'yxatdan o'tish boshlash - DB ga step saqlash
    db.set_reg_step(user_id, "lang")
    kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
    await update.message.reply_text(
        "👋 *Radiology AI*\n\nTilni tanlang / Выберите язык / Choose language:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await check_subscription(context.bot, user_id):
        user_data = db.get_user(user_id)
        if user_data and user_data.get("registered"):
            await query.message.reply_text(t(user_data.get("lang","uz"),"send_file"))
        else:
            db.set_reg_step(user_id, "lang")
            kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
            await query.message.reply_text("✅ Tasdiqlandi! Tilni tanlang:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    # Ro'yxatdan o'tgan foydalanuvchi
    user_data = db.get_user(user_id)
    if user_data and user_data.get("registered"):
        await update.message.reply_text(t(user_data.get("lang","uz"),"send_file"))
        return

    # DB dan step va vaqtinchalik ma'lumotlarni olish
    reg = db.get_reg_data(user_id)
    step = reg.get("step", "lang")
    lang = reg.get("lang", "uz")

    # Til tanlash
    lang_map = {"O'zbek":"uz", "Русский":"ru", "English":"en"}
    for key, code in lang_map.items():
        if key in text:
            db.set_reg_data(user_id, {"step": "name", "lang": code})
            await update.message.reply_text(t(code,"ask_name"), parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
            return

    # Ism
    if step == "name":
        if len(text.split()) < 2:
            await update.message.reply_text(t(lang,"name_err"), parse_mode="Markdown")
            return
        db.set_reg_data(user_id, {"step": "age", "lang": lang, "full_name": text})
        await update.message.reply_text(t(lang,"ask_age"), parse_mode="Markdown")
        return

    # Yosh
    if step == "age":
        if not text.isdigit() or not (1 <= int(text) <= 120):
            await update.message.reply_text(t(lang,"age_err"), parse_mode="Markdown")
            return
        reg["age"] = text
        reg["step"] = "phone"
        db.set_reg_data(user_id, reg)
        phone_btn = KeyboardButton(t(lang,"phone_btn"), request_contact=True)
        await update.message.reply_text(t(lang,"ask_phone"),
            reply_markup=ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True))
        return

    await update.message.reply_text("🔄 /start bosing")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    reg = db.get_reg_data(user_id)
    lang = reg.get("lang", "uz")

    db.save_user({
        "user_id":        user_id,
        "username":       user.username or "",
        "full_name":      reg.get("full_name", user.first_name or "—"),
        "age":            reg.get("age", "—"),
        "phone":          update.message.contact.phone_number,
        "lang":           lang,
        "registered":     True,
        "registered_at":  datetime.utcnow().isoformat(),
        "analysis_count": 0
    })
    db.clear_reg_data(user_id)

    await update.message.reply_text(t(lang,"registered"), parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))

# ─── UMUMIY TEKSHIRUV ─────────────────────────────────────────────────────────
async def _check_user_ready(update, context):
    """Obuna va ro'yxatdan o'tishni tekshiradi. (user_data, lang) qaytaradi yoki None."""
    user_id = update.message.from_user.id

    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"sub_btn"),
            url=f"https://t.me/{SUBSCRIBE_CH.lstrip('@')}")]])
        await update.message.reply_text(t(lang,"not_sub"), reply_markup=kb)
        return None, None

    user_data = db.get_user(user_id)
    if not user_data or not user_data.get("registered"):
        await update.message.reply_text(t("uz","start_first"))
        return None, None

    return user_data, user_data.get("lang","uz")

# ─── RASM HANDLER ─────────────────────────────────────────────────────────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data, lang = await _check_user_ready(update, context)
    if not user_data:
        return

    pos = await queue.add_to_queue(
        user_id=update.message.from_user.id,
        message=update.message,
        context=context,
        user_data=user_data,
        lang=lang,
        file_type="photo"
    )
    await update.message.reply_text(t(lang,"in_queue").replace("{pos}", str(pos)))

# ─── HUJJAT HANDLER (PDF / DOCX) ─────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data, lang = await _check_user_ready(update, context)
    if not user_data:
        return

    doc = update.message.document
    mime = doc.mime_type or ""
    file_name = doc.file_name or ""

    allowed = (
        "pdf" in mime or
        "msword" in mime or
        "officedocument.word" in mime or
        file_name.lower().endswith((".pdf", ".doc", ".docx"))
    )

    if not allowed:
        await update.message.reply_text(
            "⚠️ Faqat PDF yoki Word (DOC/DOCX) hujjatlar qabul qilinadi.\n"
            "Rasm yubormoqchi bo'lsangiz, galereya orqali yuboring 📸"
        )
        return

    pos = await queue.add_to_queue(
        user_id=update.message.from_user.id,
        message=update.message,
        context=context,
        user_data=user_data,
        lang=lang,
        file_type="document"
    )
    await update.message.reply_text(t(lang,"in_queue").replace("{pos}", str(pos)))

# ─── QUEUE WORKER ─────────────────────────────────────────────────────────────
async def process_queue_worker(app):
    while True:
        task = await queue.get_next()
        if task is None:
            await asyncio.sleep(2)
            continue

        user_id   = task["user_id"]
        message   = task["message"]
        user_data = task["user_data"]
        lang      = task["lang"]
        file_type = task.get("file_type", "photo")

        try:
            status_msg = await app.bot.send_message(chat_id=user_id, text=t(lang,"processing"))
            age = user_data.get("age","")
            result = None

            # ── RASM ──
            if file_type == "photo":
                photo = message.photo[-1]
                file  = await app.bot.get_file(photo.file_id)
                image_bytes = bytes(await file.download_as_bytearray())
                if GEMINI_API_KEY:
                    result = await analyze_image_gemini(image_bytes, lang, age)

            # ── HUJJAT (PDF/DOCX) ──
            elif file_type == "document":
                doc  = message.document
                file = await app.bot.get_file(doc.file_id)
                file_bytes = bytes(await file.download_as_bytearray())
                mime = doc.mime_type or ""
                name = doc.file_name or ""

                if "pdf" in mime or name.lower().endswith(".pdf"):
                    doc_text = extract_pdf_text(file_bytes)
                else:
                    doc_text = extract_docx_text(file_bytes)

                if not doc_text:
                    await app.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=status_msg.message_id,
                        text=t(lang,"no_text_doc")
                    )
                    queue.task_done()
                    continue

                if GEMINI_API_KEY:
                    result = await analyze_text_gemini(doc_text, lang, age)

            if not GEMINI_API_KEY:
                result = (
                    "⚠️ *GEMINI_API_KEY sozlanmagan!*\n\n"
                    "Railway → Variables:\n`GEMINI_API_KEY = AIzaSy...`\n\n"
                    "Bepul: https://aistudio.google.com"
                )

            if not result:
                result = t(lang,"error")

            # Foydalanuvchiga natija
            await app.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_msg.message_id,
                text=result,
                parse_mode="Markdown"
            )

            # Log kanalga
            name_str = user_data.get("full_name") or "—"
            username = f"@{user_data['username']}" if user_data.get("username") else "—"
            phone    = user_data.get("phone") or "—"
            age_str  = user_data.get("age") or "—"
            count    = db.increment_analysis(user_id)
            now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            ftype_label = "📄 Hujjat" if file_type == "document" else "🖼 Rasm"

            log_caption = (
                f"🧠 *Radiology AI — Tahlil #{count}*\n"
                f"{'─'*28}\n"
                f"👤 *Ism:* {name_str}\n"
                f"🎂 *Yosh:* {age_str}\n"
                f"📱 *Tel:* `{phone}`\n"
                f"🔹 *Username:* {username}\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"{ftype_label}\n"
                f"🕐 {now} UTC\n"
                f"{'─'*28}\n"
                f"📄 *Natija:*\n{result[:900]}"
            )

            try:
                if file_type == "photo":
                    await app.bot.send_photo(
                        chat_id=LOG_CH, photo=message.photo[-1].file_id,
                        caption=log_caption, parse_mode="Markdown"
                    )
                else:
                    await app.bot.send_document(
                        chat_id=LOG_CH, document=message.document.file_id,
                        caption=log_caption, parse_mode="Markdown"
                    )
            except Exception as e:
                logger.warning(f"Log kanal xatosi: {e}")

        except Exception as e:
            logger.error(f"Worker xato: {e}", exc_info=True)
            try:
                await app.bot.send_message(chat_id=user_id, text=t(lang,"error"))
            except:
                pass
        finally:
            queue.task_done()
            await asyncio.sleep(4)

async def post_init(app):
    asyncio.create_task(process_queue_worker(app))
    logger.info("✅ Bot va queue worker ishga tushdi")

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🤖 Radiology AI Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
