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

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN          = os.getenv("BOT_TOKEN", "BOT_TOKENINGIZ")
SUBSCRIBE_CH   = os.getenv("SUBSCRIBE_CHANNEL", "@RadiologyGroupChat")   # foydalanuvchi obuna bo'ladigan kanal
LOG_CH         = os.getenv("LOG_CHANNEL", "@RadialogyAI")     # faqat admin ko'radigan log kanal
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

queue = AnalysisQueue()

# ─── SUBSCRIPTION CHECK ───────────────────────────────────────────────────────
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
            "registered":  "✅ Ro'yxatdan o'tdingiz!\n\nEndi MRT / MSKT / Rentgen rasmini yuboring 📸",
            "not_sub":     f"⚠️ Botdan foydalanish uchun kanalga obuna bo'ling:\n\n👉 {SUBSCRIBE_CH}\n\nObuna bo'lgach /start bosing.",
            "send_photo":  "📸 MRT, MSKT yoki Rentgen rasmini yuboring",
            "in_queue":    "⏳ Navbatga qo'shildi!\n🔢 Navbatingiz: #{pos}\n\nBirozdan keyin natija yuboriladi ⏱",
            "processing":  "🔬 Rasmingiz tahlil qilinmoqda...",
            "error":       "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
            "sub_btn":     "📢 Kanalga obuna bo'lish",
            "check_btn":   "✅ Obunani tekshirish",
            "phone_btn":   "📱 Raqamni ulashish",
            "name_err":    "⚠️ Ism va Familiyangizni kiriting\n_Misol: Alisher Nazarov_",
            "age_err":     "⚠️ Faqat raqam kiriting\n_Misol: 35_",
            "start_first": "⚠️ Avval /start bosib ro'yxatdan o'ting",
        },
        "ru": {
            "welcome":     "👋 Добро пожаловать в *Radiology AI*!\n\nВыберите язык:",
            "ask_name":    "📝 Введите полное имя:\n_Пример: Алишер Назаров_",
            "ask_age":     "🎂 Введите ваш возраст:\n_Пример: 35_",
            "ask_phone":   "📱 Поделитесь номером телефона:",
            "registered":  "✅ Вы зарегистрированы!\n\nОтправьте снимок МРТ / КТ / Рентген 📸",
            "not_sub":     f"⚠️ Подпишитесь на канал:\n\n👉 {SUBSCRIBE_CH}\n\nПосле подписки нажмите /start.",
            "send_photo":  "📸 Отправьте снимок МРТ, КТ или Рентген",
            "in_queue":    "⏳ Добавлено в очередь!\n🔢 Ваш номер: #{pos}\n\nРезультат придёт скоро ⏱",
            "processing":  "🔬 Снимок анализируется...",
            "error":       "❌ Произошла ошибка. Попробуйте снова.",
            "sub_btn":     "📢 Подписаться на канал",
            "check_btn":   "✅ Проверить подписку",
            "phone_btn":   "📱 Поделиться номером",
            "name_err":    "⚠️ Введите Имя и Фамилию\n_Пример: Алишер Назаров_",
            "age_err":     "⚠️ Введите только число\n_Пример: 35_",
            "start_first": "⚠️ Сначала нажмите /start для регистрации",
        },
        "en": {
            "welcome":     "👋 Welcome to *Radiology AI*!\n\nChoose language:",
            "ask_name":    "📝 Enter your full name:\n_Example: John Smith_",
            "ask_age":     "🎂 Enter your age:\n_Example: 35_",
            "ask_phone":   "📱 Share your phone number:",
            "registered":  "✅ Registration complete!\n\nSend your MRI / CT / X-Ray image 📸",
            "not_sub":     f"⚠️ Subscribe to our channel first:\n\n👉 {SUBSCRIBE_CH}\n\nThen press /start.",
            "send_photo":  "📸 Send your MRI, CT scan or X-Ray",
            "in_queue":    "⏳ Added to queue!\n🔢 Your position: #{pos}\n\nResult coming soon ⏱",
            "processing":  "🔬 Analyzing your image...",
            "error":       "❌ An error occurred. Please try again.",
            "sub_btn":     "📢 Subscribe to channel",
            "check_btn":   "✅ Check subscription",
            "phone_btn":   "📱 Share phone number",
            "name_err":    "⚠️ Enter First and Last name\n_Example: John Smith_",
            "age_err":     "⚠️ Enter numbers only\n_Example: 35_",
            "start_first": "⚠️ Please press /start to register first",
        },
    }
    return texts.get(lang, texts["uz"]).get(key, "")

# ─── GEMINI AI ────────────────────────────────────────────────────────────────
async def analyze_with_gemini(image_bytes: bytes, lang: str, user_age: str = "") -> str:
    age_note = f" Bemor yoshi: {user_age}." if user_age else ""

    prompts = {
        "uz": f"""Siz tajribali radiolog shifokor sifatida quyidagi tibbiy tasvirni tahlil qiling.{age_note}

Javobingiz FAQAT quyidagi formatda bo'lsin — boshqa hech narsa yozmang:

🖼 *Rasm turi:*
[MRT / MSKT / Rentgen yoki boshqa; qaysi a'zo yoki qaysi qism]

🔬 *Ko'rinayotgan tuzilmalar:*
[Anatomiyal tuzilmalar, to'qimalar, suyaklar, bo'shliqlar]

📋 *Topilmalar:*
[Normal va g'ayritabiiy o'zgarishlar, o'lchamlar, zichlik]

⚠️ *Diqqat talab qiladigan joylar:*
[Shubhali o'zgarishlar, patologik belgilar yoki "Belirgin patologiya aniqlanmadi"]

💊 *Tavsiya:*
[Qaysi mutaxassisga murojaat qilish, qo'shimcha tekshiruvlar]

⚕️ _Eslatma: Bu AI tahlili bo'lib, rasmiy tibbiy tashxis emas. Aniq tashxis uchun mutaxassis shifokorga murojaat qiling._""",

        "ru": f"""Вы — опытный врач-радиолог. Проанализируйте медицинский снимок ниже.{age_note}

Ответ ТОЛЬКО в следующем формате — больше ничего не пишите:

🖼 *Тип снимка:*
[МРТ / КТ / Рентген или другое; какой орган или область]

🔬 *Видимые структуры:*
[Анатомические структуры, ткани, кости, полости]

📋 *Находки:*
[Нормальные и патологические изменения, размеры, плотность]

⚠️ *Требует внимания:*
[Подозрительные изменения или "Значимой патологии не выявлено"]

💊 *Рекомендации:*
[К какому специалисту обратиться, дополнительные исследования]

⚕️ _Примечание: Это AI-анализ, не официальный медицинский диагноз. Обратитесь к врачу._""",

        "en": f"""You are an experienced radiologist. Analyze the medical image below.{age_note}

Reply ONLY in the following format — write nothing else:

🖼 *Image Type:*
[MRI / CT / X-Ray or other; which organ or region]

🔬 *Visible Structures:*
[Anatomical structures, tissues, bones, cavities]

📋 *Findings:*
[Normal and abnormal changes, measurements, density]

⚠️ *Areas of Concern:*
[Suspicious changes or "No significant pathology detected"]

💊 *Recommendation:*
[Which specialist to see, additional studies needed]

⚕️ _Note: This is an AI analysis, not an official medical diagnosis. Consult a qualified physician._""",
    }

    prompt = prompts.get(lang, prompts["uz"])
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1200,
            "topP": 0.8,
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini parse error: {e}")
            return None
    logger.error(f"Gemini API error: {r.status_code} — {r.text[:300]}")
    return None

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
    if user_data:
        await update.message.reply_text(t(user_data.get("lang","uz"),"send_photo"), parse_mode="Markdown")
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
            await query.message.reply_text(t(user_data.get("lang","uz"),"send_photo"))
        else:
            kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
            await query.message.reply_text("✅ Tasdiqlandi! Tilni tanlang:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    user = update.message.from_user

    # Til tanlash
    lang_map = {"O'zbek": "uz", "Русский": "ru", "English": "en"}
    for key, code in lang_map.items():
        if key in text:
            db.set_user_lang(user_id, code)
            context.user_data["reg_lang"] = code
            context.user_data["reg_step"] = "name"
            await update.message.reply_text(t(code,"ask_name"), parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
            return

    lang = context.user_data.get("reg_lang") or db.get_user_lang(user_id) or "uz"
    step = context.user_data.get("reg_step", "")
    user_data = db.get_user(user_id)

    # Ism kiritish
    if step == "name" and not user_data:
        if len(text.split()) < 2:
            await update.message.reply_text(t(lang,"name_err"), parse_mode="Markdown")
            return
        context.user_data["full_name"] = text
        context.user_data["reg_step"] = "age"
        await update.message.reply_text(t(lang,"ask_age"), parse_mode="Markdown")
        return

    # Yosh kiritish
    if step == "age" and not user_data:
        if not text.isdigit() or not (1 <= int(text) <= 120):
            await update.message.reply_text(t(lang,"age_err"), parse_mode="Markdown")
            return
        context.user_data["age"] = text
        context.user_data["reg_step"] = "phone"
        phone_btn = KeyboardButton(t(lang,"phone_btn"), request_contact=True)
        await update.message.reply_text(t(lang,"ask_phone"),
            reply_markup=ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True))
        return

    if user_data:
        await update.message.reply_text(t(user_data.get("lang","uz"),"send_photo"))
    else:
        await update.message.reply_text("🔄 /start bosing")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    lang = context.user_data.get("reg_lang", "uz")

    db.save_user({
        "user_id":      user_id,
        "username":     user.username or "",
        "full_name":    context.user_data.get("full_name", user.first_name or ""),
        "age":          context.user_data.get("age", "—"),
        "phone":        update.message.contact.phone_number,
        "lang":         lang,
        "registered_at": datetime.utcnow().isoformat(),
        "analysis_count": 0
    })
    context.user_data.clear()

    await update.message.reply_text(t(lang,"registered"), parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"sub_btn"),
            url=f"https://t.me/{SUBSCRIBE_CH.lstrip('@')}")]])
        await update.message.reply_text(t(lang,"not_sub"), reply_markup=kb)
        return

    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text(t("uz","start_first"))
        return

    lang = user_data.get("lang", "uz")
    pos = await queue.add_to_queue(
        user_id=user_id, message=update.message,
        context=context, user_data=user_data, lang=lang
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

        try:
            status_msg = await app.bot.send_message(chat_id=user_id, text=t(lang,"processing"))

            photo = message.photo[-1]
            file  = await app.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()

            age = user_data.get("age", "")
            if GEMINI_API_KEY:
                result = await analyze_with_gemini(bytes(image_bytes), lang, age)
            else:
                result = (
                    "⚠️ *GEMINI_API_KEY sozlanmagan!*\n\n"
                    "Railway → Variables ga qo'shing:\n"
                    "`GEMINI_API_KEY = AIzaSy...`\n\n"
                    "Bepul olish: https://aistudio.google.com"
                )

            if not result:
                result = t(lang, "error")

            # Foydalanuvchiga
            await app.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_msg.message_id,
                text=result,
                parse_mode="Markdown"
            )

            # ─── LOG KANALGA (faqat admin ko'radi) ───
            name     = user_data.get("full_name") or "—"
            username = f"@{user_data['username']}" if user_data.get("username") else "—"
            phone    = user_data.get("phone") or "—"
            age_str  = user_data.get("age") or "—"
            count    = db.increment_analysis(user_id)
            now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

            log_caption = (
                f"🧠 *Radiology AI — Tahlil #{count}*\n"
                f"{'─'*30}\n"
                f"👤 *Ism:* {name}\n"
                f"🎂 *Yosh:* {age_str}\n"
                f"📱 *Tel:* `{phone}`\n"
                f"🔹 *Username:* {username}\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"🕐 *Vaqt:* {now} UTC\n"
                f"{'─'*30}\n"
                f"📄 *AI natija:*\n{result[:900]}"
            )

            try:
                await app.bot.send_photo(
                    chat_id=LOG_CH,
                    photo=photo.file_id,
                    caption=log_caption,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Log kanal xatosi: {e}")

        except Exception as e:
            logger.error(f"Worker xato: {e}")
            try:
                await app.bot.send_message(chat_id=user_id, text=t(lang,"error"))
            except:
                pass
        finally:
            queue.task_done()
            await asyncio.sleep(4)  # Gemini rate limit: 15 req/min

async def post_init(app):
    asyncio.create_task(process_queue_worker(app))
    logger.info("✅ Bot va queue worker ishga tushdi")

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🤖 Radiology AI Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
