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

TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = "@RadiologyGroupChat"
CHANNEL_LOG = "@RadiologyGroupChat"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

queue = AnalysisQueue()

async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def t(lang, key):
    texts = {
        "uz": {
            "welcome":     "👋 *Radiology AI*ga xush kelibsiz!\n\nTilni tanlang:",
            "ask_name":    "📝 To'liq ismingizni kiriting:\n_Misol: Alisher Nazarov_",
            "ask_phone":   "📱 Telefon raqamingizni yuboring:",
            "registered":  "✅ Ro'yxatdan o'tdingiz!\n\nEndi MRT / MSKT / Rentgen rasmini yuboring 📸",
            "not_sub":     f"⚠️ Botdan foydalanish uchun kanalga obuna bo'ling:\n\n👉 {CHANNEL_ID}\n\nObuna bo'lgach /start bosing.",
            "send_photo":  "📸 MRT, MSKT yoki Rentgen rasmi yoki PDF faylini yuboring",
            "in_queue":    "⏳ Navbatga qo'shildi!\n🔢 Navbatingiz: #{pos}",
            "processing":  "🔬 Tahlil qilinmoqda...",
            "error":       "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
            "sub_btn":     "📢 Kanalga obuna bo'lish",
            "check_btn":   "✅ Obunani tekshirish",
            "phone_btn":   "📱 Raqamni ulashish",
            "name_err":    "⚠️ Iltimos, Ism va Familiyangizni kiriting\n_Misol: Alisher Nazarov_",
            "start_first": "⚠️ Avval /start bosib ro'yxatdan o'ting",
            "wrong_file":  "⚠️ Faqat rasm (JPEG/PNG) yoki PDF fayl yuboring.",
        },
        "ru": {
            "welcome":     "👋 Добро пожаловать в *Radiology AI*!\n\nВыберите язык:",
            "ask_name":    "📝 Введите полное имя:\n_Пример: Алишер Назаров_",
            "ask_phone":   "📱 Поделитесь номером телефона:",
            "registered":  "✅ Вы зарегистрированы!\n\nОтправьте снимок МРТ / КТ / Рентген 📸",
            "not_sub":     f"⚠️ Подпишитесь на канал:\n\n👉 {CHANNEL_ID}\n\nПосле подписки нажмите /start.",
            "send_photo":  "📸 Отправьте снимок МРТ, КТ, Рентген или PDF файл",
            "in_queue":    "⏳ Добавлено в очередь!\n🔢 Ваш номер: #{pos}",
            "processing":  "🔬 Анализируется...",
            "error":       "❌ Произошла ошибка. Попробуйте снова.",
            "sub_btn":     "📢 Подписаться на канал",
            "check_btn":   "✅ Проверить подписку",
            "phone_btn":   "📱 Поделиться номером",
            "name_err":    "⚠️ Введите Имя и Фамилию\n_Пример: Алишер Назаров_",
            "start_first": "⚠️ Сначала нажмите /start для регистрации",
            "wrong_file":  "⚠️ Отправьте только изображение (JPEG/PNG) или PDF файл.",
        },
        "en": {
            "welcome":     "👋 Welcome to *Radiology AI*!\n\nChoose language:",
            "ask_name":    "📝 Enter your full name:\n_Example: John Smith_",
            "ask_phone":   "📱 Share your phone number:",
            "registered":  "✅ Registration complete!\n\nSend your MRI / CT / X-Ray image 📸",
            "not_sub":     f"⚠️ Subscribe to our channel first:\n\n👉 {CHANNEL_ID}\n\nThen press /start.",
            "send_photo":  "📸 Send your MRI, CT scan, X-Ray image or PDF file",
            "in_queue":    "⏳ Added to queue!\n🔢 Your position: #{pos}",
            "processing":  "🔬 Analyzing...",
            "error":       "❌ An error occurred. Please try again.",
            "sub_btn":     "📢 Subscribe to channel",
            "check_btn":   "✅ Check subscription",
            "phone_btn":   "📱 Share phone number",
            "name_err":    "⚠️ Enter First and Last name\n_Example: John Smith_",
            "start_first": "⚠️ Please press /start to register first",
            "wrong_file":  "⚠️ Please send only image (JPEG/PNG) or PDF file.",
        },
    }
    return texts.get(lang, texts["uz"]).get(key, "")

async def analyze_with_gemini(file_bytes, lang, mime_type="image/jpeg"):
    prompts = {
        "uz": (
            "Siz tajribali radiolog shifokor yordamchisisiz. "
            "Quyidagi tibbiy materialini (MRT/MSKT/Rentgen) tahlil qiling va FAQAT O'ZBEK TILIDA javob bering:\n\n"
            "🔬 *Rasm turi:*\n[Qaysi tekshiruv va qaysi a'zo]\n\n"
            "📋 *Asosiy topilmalar:*\n[Ko'rinayotgan tuzilmalar]\n\n"
            "⚠️ *Diqqat talab qiladi:*\n[G'ayritabiiy o'zgarishlar]\n\n"
            "💊 *Tavsiya:*\n[Qaysi mutaxassisga borish kerak]\n\n"
            "⚕️ _Bu AI tahlil, rasmiy tashxis emas. Aniq tashxis uchun shifokorga murojaat qiling._"
        ),
        "ru": (
            "Вы — ассистент радиолога. Проанализируйте медицинский материал (МРТ/КТ/Рентген) ТОЛЬКО НА РУССКОМ:\n\n"
            "🔬 *Тип снимка:*\n[Вид исследования и орган]\n\n"
            "📋 *Основные находки:*\n[Видимые структуры]\n\n"
            "⚠️ *Требует внимания:*\n[Аномальные изменения]\n\n"
            "💊 *Рекомендация:*\n[К какому врачу обратиться]\n\n"
            "⚕️ _Это AI-анализ, не официальный диагноз. Обратитесь к врачу._"
        ),
        "en": (
            "You are a radiology AI assistant. Analyze this medical material (MRI/CT/X-Ray) ONLY IN ENGLISH:\n\n"
            "🔬 *Image Type:*\n[Type of scan and organ]\n\n"
            "📋 *Key Findings:*\n[Visible structures]\n\n"
            "⚠️ *Areas of Concern:*\n[Abnormal changes]\n\n"
            "💊 *Recommendation:*\n[Which specialist to see]\n\n"
            "⚕️ _This is an AI analysis, not an official diagnosis. Consult a physician._"
        ),
    }
    prompt = prompts.get(lang, prompts["uz"])
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime_type, "data": b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(url, json=payload)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        logger.error(f"Gemini error {r.status_code}: {r.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"Gemini request failed: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "sub_btn"), url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton(t(lang, "check_btn"), callback_data="check_sub")]
        ])
        await update.message.reply_text(t(lang, "not_sub"), reply_markup=kb)
        return
    user_data = db.get_user(user_id)
    if user_data:
        await update.message.reply_text(t(user_data.get("lang", "uz"), "send_photo"), parse_mode="Markdown")
        return
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
        if user_data:
            await query.message.reply_text(t(user_data.get("lang", "uz"), "send_photo"))
        else:
            kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
            await query.message.reply_text(
                "✅ Tasdiqlandi! Tilni tanlang:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
            )
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    lang_map = {"O'zbek": "uz", "Русский": "ru", "English": "en"}
    for key, code in lang_map.items():
        if key in text:
            db.set_user_lang(user_id, code)
            context.user_data["reg_lang"] = code
            await update.message.reply_text(
                t(code, "ask_name"), parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
            )
            return
    user_data = db.get_user(user_id)
    if not user_data and "reg_lang" in context.user_data:
        lang = context.user_data["reg_lang"]
        if len(text.strip().split()) < 2:
            await update.message.reply_text(t(lang, "name_err"), parse_mode="Markdown")
            return
        context.user_data["full_name"] = text.strip()
        phone_btn = KeyboardButton(t(lang, "phone_btn"), request_contact=True)
        await update.message.reply_text(
            t(lang, "ask_phone"),
            reply_markup=ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True)
        )
        return
    if user_data:
        await update.message.reply_text(t(user_data.get("lang", "uz"), "send_photo"))
    else:
        await update.message.reply_text("🔄 /start bosing")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    lang = context.user_data.get("reg_lang", "uz")
    db.save_user({
        "user_id": user.id,
        "username": user.username or "",
        "full_name": context.user_data.get("full_name", user.first_name or ""),
        "phone": update.message.contact.phone_number,
        "lang": lang,
        "registered_at": datetime.utcnow().isoformat(),
        "analysis_count": 0
    })
    await update.message.reply_text(
        t(lang, "registered"), parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )

async def _add_to_queue(update, context, user_id, user_data, lang):
    pos = await queue.add_to_queue(
        user_id=user_id, message=update.message,
        context=context, user_data=user_data, lang=lang
    )
    await update.message.reply_text(t(lang, "in_queue").replace("{pos}", str(pos)))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "sub_btn"), url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]])
        await update.message.reply_text(t(lang, "not_sub"), reply_markup=kb)
        return
    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text(t("uz", "start_first"))
        return
    lang = user_data.get("lang", "uz")
    await _add_to_queue(update, context, user_id, user_data, lang)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            t(lang, "sub_btn"), url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]])
        await update.message.reply_text(t(lang, "not_sub"), reply_markup=kb)
        return
    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text(t("uz", "start_first"))
        return
    lang = user_data.get("lang", "uz")
    mime = update.message.document.mime_type or ""
    allowed = ["application/pdf", "image/jpeg", "image/png", "image/jpg", "image/webp"]
    if mime not in allowed:
        await update.message.reply_text(t(lang, "wrong_file"))
        return
    await _add_to_queue(update, context, user_id, user_data, lang)

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
        status_msg = None
        try:
            status_msg = await app.bot.send_message(chat_id=user_id, text=t(lang, "processing"))

            # Fayl turini aniqlash
            if message.photo:
                tg_file = await app.bot.get_file(message.photo[-1].file_id)
                file_bytes = bytes(await tg_file.download_as_bytearray())
                mime_type = "image/jpeg"
                log_file_id = message.photo[-1].file_id
                is_photo = True
            elif message.document:
                tg_file = await app.bot.get_file(message.document.file_id)
                file_bytes = bytes(await tg_file.download_as_bytearray())
                mime_type = message.document.mime_type or "application/pdf"
                log_file_id = message.document.file_id
                is_photo = False
            else:
                raise ValueError("Na rasm, na hujjat topilmadi")

            if not GEMINI_API_KEY:
                result = (
                    "⚠️ *GEMINI\\_API\\_KEY sozlanmagan\\!*\n\n"
                    "Railway Variables ga `GEMINI_API_KEY` qo'shing\\.\n"
                    "Bepul olish: https://aistudio\\.google\\.com"
                )
            else:
                result = await analyze_with_gemini(file_bytes, lang, mime_type)

            if not result:
                result = t(lang, "error")

            await app.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_msg.message_id,
                text=result,
                parse_mode="Markdown"
            )

            # Kanal log
            name     = user_data.get("full_name", "Unknown")
            username = f"@{user_data['username']}" if user_data.get("username") else "—"
            phone    = user_data.get("phone", "—")
            count    = db.increment_analysis(user_id)
            caption  = (
                f"🧠 *Radiology AI Report*\n\n"
                f"👤 {name}\n🔹 {username}\n📱 {phone}\n🆔 `{user_id}`\n"
                f"📊 Tahlil №{count}\n"
                f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"📄 *Natija:*\n{result[:700]}"
            )
            try:
                if is_photo:
                    await app.bot.send_photo(
                        chat_id=CHANNEL_LOG, photo=log_file_id,
                        caption=caption, parse_mode="Markdown"
                    )
                else:
                    await app.bot.send_document(
                        chat_id=CHANNEL_LOG, document=log_file_id,
                        caption=caption, parse_mode="Markdown"
                    )
            except Exception as e:
                logger.warning(f"Kanal log xatosi: {e}")

        except Exception as e:
            logger.error(f"Worker xato: {e}", exc_info=True)
            try:
                if status_msg:
                    await app.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=status_msg.message_id,
                        text=t(lang, "error")
                    )
                else:
                    await app.bot.send_message(chat_id=user_id, text=t(lang, "error"))
            except:
                pass
        finally:
            queue.task_done()
            await asyncio.sleep(4)

async def post_init(app):
    asyncio.create_task(process_queue_worker(app))
    logger.info("✅ Queue worker ishga tushdi")

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
