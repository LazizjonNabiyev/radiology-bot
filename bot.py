import asyncio
import logging
import base64
import httpx
import os
from datetime import datetime, date, timedelta
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from database import db, FREE_DAILY_LIMIT
from queue_manager import AnalysisQueue

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN          = os.getenv("BOT_TOKEN", "BOT_TOKENINGIZ")
SUBSCRIBE_CH   = os.getenv("SUBSCRIBE_CHANNEL", "@RadiologyGroupChat")
LOG_CH         = os.getenv("LOG_CHANNEL", "@RadialogyAIdrgdgdagaggggggggAFEW")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0"))   # sizning Telegram ID

# Payme/Click to'lov uchun
PAYME_MERCHANT = os.getenv("PAYME_MERCHANT_ID", "")
CLICK_MERCHANT = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SERVICE  = os.getenv("CLICK_SERVICE_ID", "")

# Premium narx (so'm)
PREMIUM_1M  = 29900   # 1 oy
PREMIUM_3M  = 79900   # 3 oy
PREMIUM_12M = 249900  # 1 yil

queue = AnalysisQueue()

# ─── SUBSCRIPTION ─────────────────────────────────────────────────────────────
async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=SUBSCRIBE_CH, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ─── TEXTS ────────────────────────────────────────────────────────────────────
def t(lang, key, **kw):
    texts = {
        "uz": {
            # Boshlang'ich
            "choose_lang":   "🌐 Tilni tanlang:",
            "ask_name":      "👤 Ism va familiyangizni kiriting:\n_Misol: Alisher Nazarov_",
            "ask_age":       "🎂 Yoshingizni kiriting:\n_Misol: 35_",
            "registered":    "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n📱 Asosiy menyu ochildi 👇",
            "not_sub":       f"⚠️ Botdan foydalanish uchun avval kanalga obuna bo'ling:\n\n👉 {SUBSCRIBE_CH}\n\nObuna bo'lgach /start bosing.",
            # Menyu
            "main_menu":     "🏠 *Asosiy menyu*\n\n👤 *{name}*\n🎂 Yosh: {age}\n\n💎 Status: {status}\n📊 Bugungi tahlillar: {today}/{limit}",
            "menu_analyze":  "🔬 Tahlil qilish",
            "menu_premium":  "💎 Premium",
            "menu_history":  "📋 Tarix",
            "menu_profile":  "👤 Profilim",
            "menu_contact":  "📞 Aloqa",
            # Tahlil
            "send_file":     "📸 *Tahlil uchun fayl yuboring:*\n\n• MRT, MSKT, Rentgen rasmi\n• PDF yoki Word hujjat\n\n📌 Aniq va sifatli rasm yuborish tavsiya etiladi.",
            "in_queue":      "⏳ *Navbatga qo'shildi!*\n🔢 Navbatingiz: *#{pos}*\n\nBirozdan keyin natija yuboriladi ⏱",
            "processing":    "🔬 *Tahlil qilinmoqda...*\n\nIltimos kuting, bu bir necha soniya oladi.",
            "error":         "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
            "no_text_doc":   "⚠️ Bu hujjatda o'qiladigan matn topilmadi.",
            # Limit
            "limit_reached": f"⛔ *Kunlik bepul limit tugadi!*\n\n📊 Bugun {FREE_DAILY_LIMIT} ta bepul tahlil ishlatdingiz.\n\n💎 *Premium* xarid qilib cheksiz foydalaning!\n\n🔄 Ertaga {FREE_DAILY_LIMIT} ta bepul tahlil qayta beriladi.",
            "free_left":     "📊 Bugungi bepul tahlil: *{left}/{limit}* ta qoldi",
            # Premium
            "premium_info":  (
                "💎 *Radiology AI Premium*\n\n"
                "✅ *Bepul:*\n"
                f"• Kuniga {FREE_DAILY_LIMIT} ta tahlil\n"
                "• Asosiy tahlil\n\n"
                "👑 *Premium afzalliklari:*\n"
                "• ♾️ Cheksiz tahlil\n"
                "• 🔬 Chuqurroq AI tahlil\n"
                "• ⚡ Navbatsiz (tezkor)\n"
                "• 📋 Tahlil tarixi (20 ta)\n"
                "• 💬 Shifokor maslahat\n\n"
                "💰 *Narxlar:*\n"
                f"• 1 oy — {PREMIUM_1M:,} so'm\n"
                f"• 3 oy — {PREMIUM_3M:,} so'm\n"
                f"• 1 yil — {PREMIUM_12M:,} so'm\n\n"
                "👇 Muddatni tanlang:"
            ),
            "pay_choose":    "💳 To'lov usulini tanlang:",
            "pay_payme":     "💳 Payme",
            "pay_click":     "💳 Click",
            "pay_card":      "💳 Karta raqami",
            "pay_manual":    (
                "💳 *Qo'lda to'lov*\n\n"
                "Quyidagi karta raqamiga o'tkazing:\n\n"
                "🏦 *{amount:,} so'm*\n"
                "💳 `9860 1901 1008 9898`\n"
                "👤 Egasi: Laziz Nabiyev\n\n"
                "✅ To'lovdan so'ng chekni @Technologeee ga yuboring.\n"
                "Premium 1 soat ichida yoqiladi."
            ),
            "premium_active": "💎 *Premium faol!*\n\nMuddati: *{until}* gacha\n\nBarcha imkoniyatlar ochiq ✅",
            "premium_none":   "❌ Sizda hozircha premium yo'q.",
            # Profil
            "profile":       (
                "👤 *Profilim*\n\n"
                "📛 Ism: *{name}*\n"
                "🎂 Yosh: *{age}*\n"
                "📱 Tel: `{phone}`\n"
                "🔹 Username: {username}\n"
                "🆔 ID: `{uid}`\n"
                "📅 Ro'yxat: {reg_date}\n\n"
                "📊 Jami tahlillar: *{total}*\n"
                "💎 Premium: {prem_status}"
            ),
            # Tarix
            "history_empty": "📋 Tahlil tarixi bo'sh.\n\nRasm yuboring — natija saqlanadi.",
            "history_title": "📋 *So'nggi tahlillar:*\n\n",
            "history_item":  "🔬 *{num}.* {date} — {type}\n",
            # Aloqa
            "contact_info":  (
                "📞 *Aloqa*\n\n"
                "❓ Savol yoki muammo bo'lsa:\n\n"
                "👨‍💻 Admin: @Technologeee\n"
                "📢 Kanal: {ch}\n"
                "📧 Email: lazizaxrorovich@gmail.com\n\n"
                "⏰ Ish vaqti: 09:00 — 22:00"
            ),
            # Umumiy
            "sub_btn":       "📢 Kanalga obuna bo'lish",
            "check_btn":     "✅ Obunani tekshirish",
            "back_btn":      "🔙 Orqaga",
            "name_err":      "⚠️ Ism va familiya kiriting\n_Misol: Alisher Nazarov_",
            "age_err":       "⚠️ Faqat raqam kiriting (1-120)\n_Misol: 35_",
            "start_first":   "⚠️ Avval /start bosib ro'yxatdan o'ting",
        },
        "ru": {
            "choose_lang":   "🌐 Выберите язык:",
            "ask_name":      "👤 Введите имя и фамилию:\n_Пример: Алишер Назаров_",
            "ask_age":       "🎂 Введите ваш возраст:\n_Пример: 35_",
            "registered":    "✅ Регистрация прошла успешно!\n\n📱 Главное меню открыто 👇",
            "not_sub":       f"⚠️ Подпишитесь на канал:\n\n👉 {SUBSCRIBE_CH}\n\nПосле подписки нажмите /start.",
            "main_menu":     "🏠 *Главное меню*\n\n👤 *{name}*\n🎂 Возраст: {age}\n\n💎 Статус: {status}\n📊 Анализов сегодня: {today}/{limit}",
            "menu_analyze":  "🔬 Анализ",
            "menu_premium":  "💎 Премиум",
            "menu_history":  "📋 История",
            "menu_profile":  "👤 Мой профиль",
            "menu_contact":  "📞 Контакт",
            "send_file":     "📸 *Отправьте файл для анализа:*\n\n• Снимок МРТ, КТ, Рентген\n• PDF или Word документ\n\n📌 Рекомендуется отправлять чёткие снимки.",
            "in_queue":      "⏳ *Добавлено в очередь!*\n🔢 Ваш номер: *#{pos}*\n\nРезультат придёт скоро ⏱",
            "processing":    "🔬 *Анализируется...*\n\nПожалуйста, подождите.",
            "error":         "❌ Произошла ошибка. Попробуйте снова.",
            "no_text_doc":   "⚠️ В документе не найден читаемый текст.",
            "limit_reached": f"⛔ *Дневной лимит исчерпан!*\n\n📊 Вы использовали {FREE_DAILY_LIMIT} бесплатных анализа.\n\n💎 Купите *Premium* для безлимитного использования!\n\n🔄 Завтра снова {FREE_DAILY_LIMIT} бесплатных.",
            "free_left":     "📊 Осталось бесплатных: *{left}/{limit}*",
            "premium_info":  (
                "💎 *Radiology AI Premium*\n\n"
                "✅ *Бесплатно:*\n"
                f"• {FREE_DAILY_LIMIT} анализа в день\n"
                "• Базовый анализ\n\n"
                "👑 *Преимущества Premium:*\n"
                "• ♾️ Безлимитные анализы\n"
                "• 🔬 Глубокий AI-анализ\n"
                "• ⚡ Без очереди\n"
                "• 📋 История (20 анализов)\n"
                "• 💬 Консультация врача\n\n"
                "💰 *Цены:*\n"
                f"• 1 месяц — {PREMIUM_1M:,} сум\n"
                f"• 3 месяца — {PREMIUM_3M:,} сум\n"
                f"• 1 год — {PREMIUM_12M:,} сум\n\n"
                "👇 Выберите срок:"
            ),
            "pay_choose":    "💳 Выберите способ оплаты:",
            "pay_payme":     "💳 Payme",
            "pay_click":     "💳 Click",
            "pay_card":      "💳 Номер карты",
            "pay_manual":    (
                "💳 *Оплата вручную*\n\n"
                "Переведите на карту:\n\n"
                "🏦 *{amount:,} сум*\n"
                "💳 `9860 1901 1008 9898`\n"
                "👤 Получатель: Laziz Nabiyev\n\n"
                "✅ После оплаты отправьте чек @Technologeee.\n"
                "Premium активируется в течение 1 часа."
            ),
            "premium_active": "💎 *Premium активен!*\n\nДействует до: *{until}*\n\nВсе возможности открыты ✅",
            "premium_none":   "❌ У вас нет активного Premium.",
            "profile":       (
                "👤 *Мой профиль*\n\n"
                "📛 Имя: *{name}*\n"
                "🎂 Возраст: *{age}*\n"
                "📱 Тел: `{phone}`\n"
                "🔹 Username: {username}\n"
                "🆔 ID: `{uid}`\n"
                "📅 Регистрация: {reg_date}\n\n"
                "📊 Всего анализов: *{total}*\n"
                "💎 Premium: {prem_status}"
            ),
            "history_empty": "📋 История пуста.\n\nОтправьте снимок — результат сохранится.",
            "history_title": "📋 *Последние анализы:*\n\n",
            "history_item":  "🔬 *{num}.* {date} — {type}\n",
            "contact_info":  (
                "📞 *Контакт*\n\n"
                "❓ Вопросы и проблемы:\n\n"
                "👨‍💻 Админ: @Technologeee\n"
                "📢 Канал: {ch}\n"
                "📧 Email: lazizaxrorovich@gmail.com\n\n"
                "⏰ Рабочее время: 09:00 — 22:00"
            ),
            "sub_btn":       "📢 Подписаться",
            "check_btn":     "✅ Проверить подписку",
            "back_btn":      "🔙 Назад",
            "name_err":      "⚠️ Введите Имя и Фамилию\n_Пример: Алишер Назаров_",
            "age_err":       "⚠️ Введите число (1-120)\n_Пример: 35_",
            "start_first":   "⚠️ Нажмите /start для регистрации",
        },
        "en": {
            "choose_lang":   "🌐 Choose language:",
            "ask_name":      "👤 Enter your full name:\n_Example: John Smith_",
            "ask_age":       "🎂 Enter your age:\n_Example: 35_",
            "registered":    "✅ Registration successful!\n\n📱 Main menu opened 👇",
            "not_sub":       f"⚠️ Subscribe to our channel first:\n\n👉 {SUBSCRIBE_CH}\n\nThen press /start.",
            "main_menu":     "🏠 *Main Menu*\n\n👤 *{name}*\n🎂 Age: {age}\n\n💎 Status: {status}\n📊 Today's analyses: {today}/{limit}",
            "menu_analyze":  "🔬 Analyze",
            "menu_premium":  "💎 Premium",
            "menu_history":  "📋 History",
            "menu_profile":  "👤 My Profile",
            "menu_contact":  "📞 Contact",
            "send_file":     "📸 *Send file for analysis:*\n\n• MRI, CT, X-Ray image\n• PDF or Word document\n\n📌 Clear, high-quality images recommended.",
            "in_queue":      "⏳ *Added to queue!*\n🔢 Your position: *#{pos}*\n\nResult coming soon ⏱",
            "processing":    "🔬 *Analyzing...*\n\nPlease wait a moment.",
            "error":         "❌ An error occurred. Please try again.",
            "no_text_doc":   "⚠️ No readable text found in this document.",
            "limit_reached": f"⛔ *Daily free limit reached!*\n\n📊 You've used {FREE_DAILY_LIMIT} free analyses today.\n\n💎 Get *Premium* for unlimited access!\n\n🔄 {FREE_DAILY_LIMIT} free analyses reset tomorrow.",
            "free_left":     "📊 Free analyses left: *{left}/{limit}*",
            "premium_info":  (
                "💎 *Radiology AI Premium*\n\n"
                "✅ *Free:*\n"
                f"• {FREE_DAILY_LIMIT} analyses/day\n"
                "• Basic analysis\n\n"
                "👑 *Premium benefits:*\n"
                "• ♾️ Unlimited analyses\n"
                "• 🔬 Deep AI analysis\n"
                "• ⚡ Priority queue\n"
                "• 📋 History (20 records)\n"
                "• 💬 Doctor consultation\n\n"
                "💰 *Pricing:*\n"
                f"• 1 month — {PREMIUM_1M:,} UZS\n"
                f"• 3 months — {PREMIUM_3M:,} UZS\n"
                f"• 1 year — {PREMIUM_12M:,} UZS\n\n"
                "👇 Choose duration:"
            ),
            "pay_choose":    "💳 Choose payment method:",
            "pay_payme":     "💳 Payme",
            "pay_click":     "💳 Click",
            "pay_card":      "💳 Card number",
            "pay_manual":    (
                "💳 *Manual payment*\n\n"
                "Transfer to this card:\n\n"
                "🏦 *{amount:,} UZS*\n"
                "💳 `9860 1901 1008 9898`\n"
                "👤 Recipient: Laziz Nabiyev\n\n"
                "✅ Send receipt to @Technologeee after payment.\n"
                "Premium activated within 1 hour."
            ),
            "premium_active": "💎 *Premium active!*\n\nValid until: *{until}*\n\nAll features unlocked ✅",
            "premium_none":   "❌ You don't have an active Premium.",
            "profile":       (
                "👤 *My Profile*\n\n"
                "📛 Name: *{name}*\n"
                "🎂 Age: *{age}*\n"
                "📱 Phone: `{phone}`\n"
                "🔹 Username: {username}\n"
                "🆔 ID: `{uid}`\n"
                "📅 Registered: {reg_date}\n\n"
                "📊 Total analyses: *{total}*\n"
                "💎 Premium: {prem_status}"
            ),
            "history_empty": "📋 History is empty.\n\nSend an image — results will be saved.",
            "history_title": "📋 *Recent analyses:*\n\n",
            "history_item":  "🔬 *{num}.* {date} — {type}\n",
            "contact_info":  (
                "📞 *Contact*\n\n"
                "❓ Questions or issues:\n\n"
                "👨‍💻 Admin: @RadiologyAIAdmin\n"
                "📢 Channel: {ch}\n"
                "📧 Email: info@radiologyai.uz\n\n"
                "⏰ Working hours: 09:00 — 22:00"
            ),
            "sub_btn":       "📢 Subscribe",
            "check_btn":     "✅ Check subscription",
            "back_btn":      "🔙 Back",
            "name_err":      "⚠️ Enter First and Last name\n_Example: John Smith_",
            "age_err":       "⚠️ Enter a number (1-120)\n_Example: 35_",
            "start_first":   "⚠️ Press /start to register first",
        },
    }
    val = texts.get(lang, texts["uz"]).get(key, "")
    if kw:
        try:
            val = val.format(**kw)
        except:
            pass
    return val

# ─── MAIN MENU KEYBOARD ───────────────────────────────────────────────────────
def main_menu_kb(lang):
    return ReplyKeyboardMarkup([
        [t(lang,"menu_analyze"), t(lang,"menu_premium")],
        [t(lang,"menu_history"), t(lang,"menu_profile")],
        [t(lang,"menu_contact")]
    ], resize_keyboard=True)

async def send_main_menu(bot_or_msg, user_id, lang, user_data, send_fn):
    is_prem = db.is_premium(user_id)
    today = db.get_today_count(user_id)
    status = "💎 Premium" if is_prem else "🆓 Bepul" if lang == "uz" else ("🆓 Бесплатно" if lang == "ru" else "🆓 Free")
    text = t(lang, "main_menu",
             name=user_data.get("full_name","—"),
             age=user_data.get("age","—"),
             status=status,
             today=today,
             limit=FREE_DAILY_LIMIT)
    await send_fn(text, reply_markup=main_menu_kb(lang), parse_mode="Markdown")

# ─── GEMINI: RASM ─────────────────────────────────────────────────────────────
async def analyze_image_gemini(image_bytes, lang, age="", is_premium=False):
    age_note_uz = f"Bemor yoshi: {age} yosh." if age and age != "—" else "Bemor yoshi ko'rsatilmagan."
    age_note_ru = f"Возраст пациента: {age} лет." if age and age != "—" else "Возраст пациента не указан."
    age_note_en = f"Patient age: {age} years old." if age and age != "—" else "Patient age not specified."

    prompts = {
        "uz": f"""Sen 25 yillik klinik tajribaga ega bo'lgan professor darajasidagi radiolog shifokorsan. {age_note_uz}

Quyidagi tibbiy tasvir senga yuborildi. Uni eng yuqori professional darajada tahlil qil.

MUHIM QOIDALAR:
- Har bir bo'limda KAM DEGANDA 3-5 ta aniq gap yoz
- Umumiy, bo'sh gaplar yozma — aniq klinik ma'lumot ber
- Ko'rsatkichlarni normallar bilan taqqoslab ko'rsat
- Foydalanuvchi bu xulosani o'qib, o'z ahvoli haqida TO'LIQ tushuncha olishi kerak
- Tibbiy terminlarni oddiy so'zlar bilan izohlat

Quyidagi formatda to'liq va batafsil javob yoz:

━━━━━━━━━━━━━━━━━━━━━━━━
🖼 *TASVIR TURI VA HUDUD*
━━━━━━━━━━━━━━━━━━━━━━━━
[Tekshiruv usuli (MRT/MSKT/Rentgen/UZI), qaysi organ/hudud, qaysi proeksiya (old/yon/qiyshiq), kontrast moddasi ishlatilganmi, tasvirning sifati qanday]

━━━━━━━━━━━━━━━━━━━━━━━━
🔬 *ANATOMIK TUZILMALAR VA ULARNING HOLATI*
━━━━━━━━━━━━━━━━━━━━━━━━
[Ko'rinayotgan har bir tuzilmani alohida tavsiflang:
• Suyaklar va bo'g'imlar — shakli, zichligi, yaxlitligi
• Yumshoq to'qimalar — hajmi, tuzilishi, chegaralari
• Organlar — o'lchami, konturi, ichki tuzilishi
• Tomirlar va bo'shliqlar — o'lchami, to'lishi
• Simmetriya va pozitsiya]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *BATAFSIL TOPILMALAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Har bir topilmani aniq tavsiflang:
• O'lchamlar (sm, mm) va normal ko'rsatkichlar bilan taqqoslash
• Zichlik yoki signal intensivligi (HU ko'rsatkichlari yoki MRT signali)
• Chegaralar — aniq/noaniq, tekis/notekis
• Shakl — yumaloq/oval/tartibsiz
• Joylashuv — qaysi qismda, qaysi tuzilmaga nisbatan
• O'zgarishlar xarakteri — o'tkir/surunkali belgilar]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *PATOLOGIK O'ZGARISHLAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Aniqlangan barcha g'ayritabiiy holatlar:
• Shishlar yoki o'smalar — o'lchami, chegarasi, xarakteri
• Yallig'lanish belgilari — shish, infiltratsiya, ekssudat
• Buzilishlar — yoriqlar, sinishlar, dislokatsiya
• Tomirlar holati — torayish, kengayish, tromboz
• Bosim belgilari — qo'shni organlarga ta'siri
• "Belirgin patologiya aniqlanmadi" — faqat haqiqatan normal bo'lsa]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *TAXMINIY TASHXIS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Eng ehtimoliy tashxislar ro'yxati ehtimollik darajasi bilan:
• Birinchi o'rinda eng kuchli tashxis — sababi bilan
• Ikkinchi o'rinda differensial tashxis — farqlari
• Uchinchi ehtimol — qo'shimcha tekshiruvlar zarur bo'lganda
Har bir tashxisni klinik belgilar bilan asoslang]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *KLINIK TAVSIYALAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Aniq va amaliy tavsiyalar:
• Qaysi mutaxassis shifokorga borish kerak (nevrolog/ortoped/onkolog/pulmonolog va h.k.)
• Qo'shimcha zarur tekshiruvlar (qon tahlillari, boshqa rasm usullari)
• Davo yoki profilaktika yo'nalishlari
• Darhol tibbiy yordam kerakmi — yoki rejalashtirilgan murojaat yetarlimi
• Dinamik kuzatuvga olish zarurmi]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Muhim: Bu Radiology AI sun'iy intellekti tomonidan tayyorlangan tahlil bo'lib, rasmiy tibbiy tashxis emas. Aniq tashxis, davo rejasi va dori buyurish uchun albatta litsenziyali shifokorga murojaat qiling._""",

        "ru": f"""Вы — профессор-радиолог с 25-летним клиническим опытом. {age_note_ru}

Вам был отправлен медицинский снимок. Проведите анализ на высшем профессиональном уровне.

ВАЖНЫЕ ПРАВИЛА:
- В каждом разделе пишите МИНИМУМ 3-5 конкретных предложений
- Никаких общих пустых фраз — давайте точную клиническую информацию
- Сравнивайте показатели с нормой
- Пациент должен получить ПОЛНОЕ понимание своего состояния
- Медицинские термины объясняйте простыми словами

Напишите полный подробный ответ в следующем формате:

━━━━━━━━━━━━━━━━━━━━━━━━
🖼 *ТИП СНИМКА И ОБЛАСТЬ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Метод исследования (МРТ/КТ/Рентген/УЗИ), орган/область, проекция, контраст, качество снимка]

━━━━━━━━━━━━━━━━━━━━━━━━
🔬 *АНАТОМИЧЕСКИЕ СТРУКТУРЫ И ИХ СОСТОЯНИЕ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Описание каждой структуры отдельно:
• Кости и суставы — форма, плотность, целостность
• Мягкие ткани — объём, структура, границы
• Органы — размер, контур, внутренняя структура
• Сосуды и полости — размер, заполнение
• Симметрия и положение]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *ДЕТАЛЬНЫЕ НАХОДКИ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Каждая находка с точным описанием:
• Размеры (см, мм) и сравнение с нормой
• Плотность или интенсивность сигнала (единицы HU или МРТ-сигнал)
• Границы — чёткие/нечёткие, ровные/неровные
• Форма — округлая/овальная/неправильная
• Локализация — в каком отделе, относительно каких структур
• Характер изменений — острые/хронические признаки]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *ПАТОЛОГИЧЕСКИЕ ИЗМЕНЕНИЯ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Все выявленные отклонения:
• Образования или опухоли — размер, границы, характер
• Признаки воспаления — отёк, инфильтрация, экссудат
• Повреждения — трещины, переломы, дислокация
• Состояние сосудов — сужение, расширение, тромбоз
• Признаки компрессии — влияние на соседние органы
• "Значимой патологии не выявлено" — только если действительно норма]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *ПРЕДВАРИТЕЛЬНЫЙ ДИАГНОЗ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Наиболее вероятные диагнозы с обоснованием:
• На первом месте — наиболее вероятный диагноз с причиной
• Дифференциальный диагноз — отличия
• Третий вариант — при необходимости доп. исследований
Каждый диагноз обоснован клиническими признаками]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *КЛИНИЧЕСКИЕ РЕКОМЕНДАЦИИ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Конкретные практические рекомендации:
• К какому специалисту обратиться (невролог/ортопед/онколог/пульмонолог и др.)
• Дополнительные необходимые исследования (анализы крови, другие методы визуализации)
• Направления лечения или профилактики
• Нужна ли экстренная медицинская помощь или плановое обращение
• Необходимость динамического наблюдения]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Важно: Это анализ, подготовленный искусственным интеллектом Radiology AI, и не является официальным медицинским заключением. Для точного диагноза, плана лечения и назначения препаратов обязательно обратитесь к лицензированному врачу._""",

        "en": f"""You are a professor-level radiologist with 25 years of clinical experience. {age_note_en}

A medical image has been sent to you. Analyze it at the highest professional level.

IMPORTANT RULES:
- Write MINIMUM 3-5 specific sentences in each section
- No vague general statements — provide precise clinical information
- Compare findings with normal values
- The patient must gain a COMPLETE understanding of their condition
- Explain medical terms in plain language

Write a full, detailed response in the following format:

━━━━━━━━━━━━━━━━━━━━━━━━
🖼 *IMAGE TYPE AND REGION*
━━━━━━━━━━━━━━━━━━━━━━━━
[Imaging modality (MRI/CT/X-Ray/Ultrasound), organ/region, projection, contrast use, image quality]

━━━━━━━━━━━━━━━━━━━━━━━━
🔬 *ANATOMICAL STRUCTURES AND THEIR STATUS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Describe each visible structure separately:
• Bones and joints — shape, density, integrity
• Soft tissues — volume, structure, borders
• Organs — size, contour, internal structure
• Vessels and cavities — caliber, filling
• Symmetry and position]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *DETAILED FINDINGS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Each finding with precise description:
• Measurements (cm, mm) compared to normal values
• Density or signal intensity (HU values or MRI signal characteristics)
• Margins — well-defined/ill-defined, smooth/irregular
• Shape — round/oval/irregular
• Location — which segment, relative to anatomical landmarks
• Nature of changes — acute/chronic signs]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *PATHOLOGICAL CHANGES*
━━━━━━━━━━━━━━━━━━━━━━━━
[All identified abnormalities:
• Masses or tumors — size, margins, characteristics
• Inflammatory signs — edema, infiltration, effusion
• Injuries — fractures, dislocations
• Vascular status — stenosis, aneurysm, thrombosis
• Compression signs — effect on adjacent organs
• "No significant pathology detected" — only if genuinely normal]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *PRELIMINARY DIAGNOSIS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Most likely diagnoses with justification:
• Primary diagnosis — most probable, with reasoning
• Differential diagnosis — distinguishing features
• Third possibility — if additional workup needed
Each diagnosis supported by clinical findings]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *CLINICAL RECOMMENDATIONS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Specific practical recommendations:
• Which specialist to consult (neurologist/orthopedist/oncologist/pulmonologist etc.)
• Additional required investigations (blood tests, other imaging)
• Treatment or prevention directions
• Is emergency care needed or scheduled appointment sufficient
• Need for dynamic monitoring]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Important: This analysis was prepared by Radiology AI artificial intelligence and is not an official medical report. For accurate diagnosis, treatment planning and prescriptions, always consult a licensed physician._""",
    }

    prompt = prompts.get(lang, prompts["uz"])
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 3000}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini image parse: {e}")
            return None
    logger.error(f"Gemini image API: {r.status_code} {r.text[:300]}")
    return None

# ─── GEMINI: MATN (PDF/DOCX) ──────────────────────────────────────────────────
async def analyze_text_gemini(doc_text, lang, age="", is_premium=False):
    age_note_uz = f"Bemor yoshi: {age} yosh." if age and age != "—" else "Bemor yoshi ko'rsatilmagan."
    age_note_ru = f"Возраст пациента: {age} лет." if age and age != "—" else "Возраст пациента не указан."
    age_note_en = f"Patient age: {age} years old." if age and age != "—" else "Patient age not specified."

    prompts = {
        "uz": f"""Sen professor darajasidagi klinik tibbiyot mutaxassisi va radiologsan. {age_note_uz}

Senga quyidagi tibbiy hujjat taqdim etildi. Uni eng yuqori professional darajada tahlil qil.

MUHIM QOIDALAR:
- Hujjatdagi BARCHA ma'lumotlarni ko'rib chiq
- Har bir bo'limda KAM DEGANDA 3-5 ta aniq gap yoz
- Ko'rsatkichlarni normal qiymatlar bilan taqqosla
- Foydalanuvchi TO'LIQ tushuncha olishi kerak
- Tibbiy terminlarni oddiy tilda izohlat

HUJJAT MATNI:
━━━━━━━━━━━━━━━━━━━━━━━━
{doc_text[:6000]}
━━━━━━━━━━━━━━━━━━━━━━━━

Quyidagi formatda to'liq javob yoz:

━━━━━━━━━━━━━━━━━━━━━━━━
📄 *HUJJAT TURI VA MAQSADI*
━━━━━━━━━━━━━━━━━━━━━━━━
[Hujjat nima: MRT/MSKT/Rentgen xulosa, qon tahlili, EKG, UZI xulosa yoki boshqa. Qaysi organ/sistema tekshirilgan. Tekshiruv sanasi va muassasa (agar ko'rsatilgan bo'lsa)]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *BARCHA KO'RSATKICHLAR VA QIYMATLAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Hujjatdagi har bir ko'rsatkichni alohida tahlil qil:
• Ko'rsatkich nomi — qiymati — normal diapazoni — baholash (normal/yuqori/past)
• O'lchamlar va ularning klinik ahamiyati
• Tasvirlovchi iboralar va ularning ma'nosi oddiy tilda
• Hamma raqamli va sifatli ko'rsatkichlar]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *NORMADAN CHETLANISHLAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Normadan chiqgan barcha ko'rsatkichlar:
• Qaysi ko'rsatkich normadan qanchaga og'ib ketgan
• Bu nima anglatadi — oddiy tilda tushuntir
• Qanchalik jiddiy: engil/o'rtacha/jiddiy
• Bir-biri bilan bog'liq o'zgarishlar
• "Barcha ko'rsatkichlar normal chegarada" — faqat haqiqatan shunday bo'lsa]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *TAXMINIY TASHXIS VA IZOHI*
━━━━━━━━━━━━━━━━━━━━━━━━
[Hujjat asosida:
• Eng kuchli tashxis — klinik asosi bilan
• Differensial tashxislar — farqlovchi belgilari bilan
• Qo'shimcha tekshiruv talab qiluvchi holatlar
• Agar hujjatda tayyor tashxis bo'lsa — uni izohla va oydinlashtir]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *AMALIY TAVSIYALAR*
━━━━━━━━━━━━━━━━━━━━━━━━
[Aniq va to'liq tavsiyalar:
• Qaysi mutaxassis shifokorga darhol/rejalashtirilgan murojaat qilish kerak
• Qo'shimcha zarur tekshiruvlar — nima uchun kerakligi bilan
• Kundalik hayotda nimalarga e'tibor berish (ovqatlanish, jismoniy faollik, cheklovlar)
• Dori-darmon haqida umumiy ma'lumot (aniq dori buyurmasdan)
• Keyingi nazorat tekshiruvi qachon o'tkazilishi kerak]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Muhim: Bu Radiology AI sun'iy intellekti tomonidan tayyorlangan tahlil bo'lib, rasmiy tibbiy tashxis emas. Aniq tashxis, davo rejasi va dori buyurish uchun albatta litsenziyali shifokorga murojaat qiling._""",

        "ru": f"""Вы — профессор-клиницист и радиолог высшей квалификации. {age_note_ru}

Вам предоставлен медицинский документ для профессионального анализа.

ВАЖНЫЕ ПРАВИЛА:
- Изучите ВСЕ данные документа
- В каждом разделе пишите МИНИМУМ 3-5 конкретных предложений
- Сравнивайте показатели с нормальными значениями
- Пациент должен получить ПОЛНОЕ понимание
- Объясняйте медицинские термины простым языком

ТЕКСТ ДОКУМЕНТА:
━━━━━━━━━━━━━━━━━━━━━━━━
{doc_text[:6000]}
━━━━━━━━━━━━━━━━━━━━━━━━

Напишите полный ответ в формате:

━━━━━━━━━━━━━━━━━━━━━━━━
📄 *ТИП ДОКУМЕНТА И ЦЕЛЬ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Что это: МРТ/КТ/Рентген заключение, анализы крови, ЭКГ, УЗИ или другое. Какой орган/система. Дата и учреждение (если указаны)]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *ВСЕ ПОКАЗАТЕЛИ И ЗНАЧЕНИЯ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Каждый показатель отдельно:
• Название — значение — норма — оценка (норма/выше/ниже)
• Размеры и их клиническое значение
• Описательные термины и их значение простым языком
• Все числовые и качественные показатели]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *ОТКЛОНЕНИЯ ОТ НОРМЫ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Все отклонившиеся показатели:
• Какой показатель и насколько отклонился от нормы
• Что это означает — простым языком
• Степень серьёзности: лёгкая/умеренная/значительная
• Взаимосвязанные изменения
• "Все показатели в норме" — только если действительно так]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *ПРЕДВАРИТЕЛЬНЫЙ ДИАГНОЗ*
━━━━━━━━━━━━━━━━━━━━━━━━
[На основании документа:
• Основной диагноз — с клиническим обоснованием
• Дифференциальные диагнозы — с отличительными признаками
• Состояния, требующие доп. обследования
• Если в документе готовый диагноз — объясните и уточните его]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ*
━━━━━━━━━━━━━━━━━━━━━━━━
[Конкретные и полные рекомендации:
• К какому специалисту срочно/планово обратиться
• Необходимые дополнительные исследования — с обоснованием
• На что обращать внимание в повседневной жизни (питание, активность, ограничения)
• Общая информация о лечении (без назначения конкретных препаратов)
• Когда проходить следующий контрольный осмотр]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Важно: Это анализ, подготовленный искусственным интеллектом Radiology AI, и не является официальным медицинским заключением. Для точного диагноза, плана лечения и назначения препаратов обязательно обратитесь к лицензированному врачу._""",

        "en": f"""You are a professor-level clinician and radiologist. {age_note_en}

A medical document has been provided for your professional analysis.

IMPORTANT RULES:
- Review ALL data in the document
- Write MINIMUM 3-5 specific sentences in each section
- Compare values against normal ranges
- Patient must gain COMPLETE understanding
- Explain medical terms in plain language

DOCUMENT TEXT:
━━━━━━━━━━━━━━━━━━━━━━━━
{doc_text[:6000]}
━━━━━━━━━━━━━━━━━━━━━━━━

Write a full response in this format:

━━━━━━━━━━━━━━━━━━━━━━━━
📄 *DOCUMENT TYPE AND PURPOSE*
━━━━━━━━━━━━━━━━━━━━━━━━
[What it is: MRI/CT/X-Ray report, blood work, ECG, ultrasound or other. Which organ/system. Date and facility (if indicated)]

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *ALL VALUES AND FINDINGS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Each parameter separately:
• Name — value — normal range — assessment (normal/high/low)
• Measurements and their clinical significance
• Descriptive terms explained in plain language
• All numerical and qualitative findings]

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *DEVIATIONS FROM NORMAL*
━━━━━━━━━━━━━━━━━━━━━━━━
[All abnormal values:
• Which parameter and how much it deviates from normal
• What this means — in plain language
• Severity: mild/moderate/significant
• Related changes
• "All values within normal limits" — only if genuinely true]

━━━━━━━━━━━━━━━━━━━━━━━━
🩺 *PRELIMINARY DIAGNOSIS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Based on the document:
• Primary diagnosis — with clinical reasoning
• Differential diagnoses — with distinguishing features
• Conditions requiring further workup
• If document has an existing diagnosis — explain and clarify it]

━━━━━━━━━━━━━━━━━━━━━━━━
💊 *PRACTICAL RECOMMENDATIONS*
━━━━━━━━━━━━━━━━━━━━━━━━
[Specific and complete recommendations:
• Which specialist to see urgently/as scheduled
• Additional required investigations — with rationale
• What to monitor in daily life (diet, activity, restrictions)
• General treatment information (without prescribing specific medications)
• When to schedule next follow-up]

━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ _Important: This analysis was prepared by Radiology AI artificial intelligence and is not an official medical report. For accurate diagnosis, treatment planning and prescriptions, always consult a licensed physician._""",
    }

    prompt = prompts.get(lang, prompts["uz"])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 3000}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini text parse: {e}")
            return None
    logger.error(f"Gemini text API: {r.status_code} {r.text[:300]}")
    return None

# ─── PDF / DOCX MATN ──────────────────────────────────────────────────────────
def extract_pdf_text(file_bytes):
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return "".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception as e:
        logger.error(f"PDF: {e}")
        return ""

def extract_docx_text(file_bytes):
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f"DOCX: {e}")
        return ""

# ─── TO'LOV LINKLARI ──────────────────────────────────────────────────────────
def payme_link(amount, order_id):
    if not PAYME_MERCHANT:
        return None
    import base64 as b64
    params = f"m={PAYME_MERCHANT};ac.order_id={order_id};a={amount * 100}"
    encoded = b64.b64encode(params.encode()).decode()
    return f"https://checkout.paycom.uz/{encoded}"

def click_link(amount, order_id):
    if not CLICK_MERCHANT or not CLICK_SERVICE:
        return None
    return (f"https://my.click.uz/services/pay?service_id={CLICK_SERVICE}"
            f"&merchant_id={CLICK_MERCHANT}&amount={amount}&transaction_param={order_id}")

# ─── HANDLERS ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

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
        lang = user_data.get("lang","uz")
        await send_main_menu(None, user_id, lang, user_data,
            lambda *a, **kw: update.message.reply_text(*a, **kw))
        return

    db.set_reg_data(user_id, {"step": "lang"})
    kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await check_subscription(context.bot, user_id):
        user_data = db.get_user(user_id)
        if user_data and user_data.get("registered"):
            lang = user_data.get("lang","uz")
            await send_main_menu(None, user_id, lang, user_data,
                lambda *a, **kw: query.message.reply_text(*a, **kw))
        else:
            db.set_reg_data(user_id, {"step": "lang"})
            kb = [["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]]
            await query.message.reply_text("✅ Tasdiqlandi! Tilni tanlang:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)

# ─── TO'LOV CALLBACK ──────────────────────────────────────────────────────────
async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    lang = (db.get_user(user_id) or {}).get("lang","uz")

    # prem:1m / prem:3m / prem:12m
    if data.startswith("prem:"):
        period = data.split(":")[1]
        amounts = {"1m": PREMIUM_1M, "3m": PREMIUM_3M, "12m": PREMIUM_12M}
        amount = amounts.get(period, PREMIUM_1M)
        order_id = f"{user_id}_{period}_{int(datetime.utcnow().timestamp())}"

        buttons = []
        pl = payme_link(amount, order_id)
        cl = click_link(amount, order_id)
        if pl:
            buttons.append([InlineKeyboardButton("💳 Payme", url=pl)])
        if cl:
            buttons.append([InlineKeyboardButton("💳 Click", url=cl)])
        buttons.append([InlineKeyboardButton("🏦 " + t(lang,"pay_card"), callback_data=f"manual:{period}")])
        buttons.append([InlineKeyboardButton(t(lang,"back_btn"), callback_data="show_premium")])

        await query.message.edit_text(
            t(lang,"pay_choose"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("manual:"):
        period = data.split(":")[1]
        amounts = {"1m": PREMIUM_1M, "3m": PREMIUM_3M, "12m": PREMIUM_12M}
        amount = amounts.get(period, PREMIUM_1M)
        await query.message.edit_text(
            t(lang,"pay_manual", amount=amount),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang,"back_btn"), callback_data="show_premium")
            ]])
        )

    elif data == "show_premium":
        amounts = {"1m": PREMIUM_1M, "3m": PREMIUM_3M, "12m": PREMIUM_12M}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 1 oy — 29,900 so'm" if lang=="uz" else ("📅 1 мес — 29 900 сум" if lang=="ru" else "📅 1 month — 29,900 UZS"), callback_data="prem:1m")],
            [InlineKeyboardButton("📅 3 oy — 79,900 so'm" if lang=="uz" else ("📅 3 мес — 79 900 сум" if lang=="ru" else "📅 3 months — 79,900 UZS"), callback_data="prem:3m")],
            [InlineKeyboardButton("📅 1 yil — 249,900 so'm" if lang=="uz" else ("📅 1 год — 249 900 сум" if lang=="ru" else "📅 1 year — 249,900 UZS"), callback_data="prem:12m")],
        ])
        await query.message.edit_text(t(lang,"premium_info"), parse_mode="Markdown", reply_markup=kb)

# ─── TEXT HANDLER ─────────────────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    user = update.message.from_user

    user_data = db.get_user(user_id)
    if user_data and user_data.get("registered"):
        lang = user_data.get("lang","uz")
        txt = text

        if txt == t(lang,"menu_analyze"):
            await update.message.reply_text(t(lang,"send_file"), parse_mode="Markdown")

        elif txt == t(lang,"menu_premium"):
            is_prem = db.is_premium(user_id)
            if is_prem:
                until = user_data.get("premium_until","—")
                await update.message.reply_text(
                    t(lang,"premium_active", until=until), parse_mode="Markdown")
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "📅 1 oy — 29,900 so'm" if lang=="uz" else ("📅 1 мес — 29 900 сум" if lang=="ru" else "📅 1 month — 29,900 UZS"),
                        callback_data="prem:1m")],
                    [InlineKeyboardButton(
                        "📅 3 oy — 79,900 so'm" if lang=="uz" else ("📅 3 мес — 79 900 сум" if lang=="ru" else "📅 3 months — 79,900 UZS"),
                        callback_data="prem:3m")],
                    [InlineKeyboardButton(
                        "📅 1 yil — 249,900 so'm" if lang=="uz" else ("📅 1 год — 249 900 сум" if lang=="ru" else "📅 1 year — 249,900 UZS"),
                        callback_data="prem:12m")],
                ])
                await update.message.reply_text(
                    t(lang,"premium_info"), parse_mode="Markdown", reply_markup=kb)

        elif txt == t(lang,"menu_history"):
            history = db.get_history(user_id)
            if not history:
                await update.message.reply_text(t(lang,"history_empty"))
            else:
                msg = t(lang,"history_title")
                for i, h in enumerate(history[:10], 1):
                    msg += t(lang,"history_item",
                             num=i, date=h.get("date","—"), type=h.get("type","—"))
                await update.message.reply_text(msg, parse_mode="Markdown")

        elif txt == t(lang,"menu_profile"):
            u = user_data
            is_prem = db.is_premium(user_id)
            prem_until = u.get("premium_until","")
            prem_str = f"💎 {prem_until} gacha" if is_prem else ("❌ Yo'q" if lang=="uz" else ("❌ Нет" if lang=="ru" else "❌ None"))
            username = f"@{u.get('username')}" if u.get("username") else "—"
            reg_date = u.get("registered_at","—")[:10] if u.get("registered_at") else "—"
            await update.message.reply_text(
                t(lang,"profile",
                  name=u.get("full_name","—"),
                  age=u.get("age","—"),
                  phone=u.get("phone","—"),
                  username=username,
                  uid=user_id,
                  reg_date=reg_date,
                  total=u.get("analysis_count",0),
                  prem_status=prem_str),
                parse_mode="Markdown"
            )

        elif txt == t(lang,"menu_contact"):
            await update.message.reply_text(
                t(lang,"contact_info", ch=SUBSCRIBE_CH), parse_mode="Markdown")

        else:
            await update.message.reply_text(t(lang,"send_file"), parse_mode="Markdown")
        return

    # ── RO'YXATDAN O'TISH ────────────────────────────────────────────────────
    reg = db.get_reg_data(user_id)
    step = reg.get("step","lang")
    lang = reg.get("lang","uz")

    # Til tanlash
    lang_map = {"O'zbek":"uz","Русский":"ru","English":"en"}
    for key, code in lang_map.items():
        if key in text:
            db.set_reg_data(user_id, {"step":"name","lang":code})
            await update.message.reply_text(t(code,"ask_name"), parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
            return

    if step == "name":
        if len(text.split()) < 2:
            await update.message.reply_text(t(lang,"name_err"), parse_mode="Markdown")
            return
        reg["full_name"] = text
        reg["step"] = "age"
        db.set_reg_data(user_id, reg)
        await update.message.reply_text(t(lang,"ask_age"), parse_mode="Markdown")
        return

    if step == "age":
        if not text.isdigit() or not (1 <= int(text) <= 120):
            await update.message.reply_text(t(lang,"age_err"), parse_mode="Markdown")
            return
        reg["age"] = text
        # Username avtomatik olamiz
        reg["username"] = user.username or ""
        reg["step"] = "done"
        db.set_reg_data(user_id, reg)
        # Telefon so'raymiz
        phone_btn = KeyboardButton("📱 Raqamni ulashish" if lang=="uz" else ("📱 Поделиться" if lang=="ru" else "📱 Share"), request_contact=True)
        await update.message.reply_text(
            "📱 Telefon raqamingizni yuboring:" if lang=="uz" else ("📱 Поделитесь номером:" if lang=="ru" else "📱 Share your phone number:"),
            reply_markup=ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True))
        return

    await update.message.reply_text("🔄 /start bosing")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    reg = db.get_reg_data(user_id)
    lang = reg.get("lang","uz")

    user_info = {
        "user_id":        user_id,
        "username":       reg.get("username", user.username or ""),
        "full_name":      reg.get("full_name", user.first_name or "—"),
        "age":            reg.get("age","—"),
        "phone":          update.message.contact.phone_number,
        "lang":           lang,
        "registered":     True,
        "registered_at":  datetime.utcnow().isoformat(),
        "analysis_count": 0,
        "today_free_count": 0,
        "last_free_date": "",
    }
    db.save_user(user_info)
    db.clear_reg_data(user_id)

    await update.message.reply_text(
        t(lang,"registered"), parse_mode="Markdown",
        reply_markup=main_menu_kb(lang)
    )

# ─── FAYLNI QABUL QILISH ──────────────────────────────────────────────────────
async def _check_ready_and_limit(update, context):
    """(user_data, lang, is_premium) yoki None qaytaradi"""
    user_id = update.message.from_user.id

    if not await check_subscription(context.bot, user_id):
        lang = db.get_user_lang(user_id) or "uz"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"sub_btn"),
            url=f"https://t.me/{SUBSCRIBE_CH.lstrip('@')}")]])
        await update.message.reply_text(t(lang,"not_sub"), reply_markup=kb)
        return None, None, None

    user_data = db.get_user(user_id)
    if not user_data or not user_data.get("registered"):
        await update.message.reply_text(t("uz","start_first"))
        return None, None, None

    lang = user_data.get("lang","uz")
    is_prem = db.is_premium(user_id)
    can, left = db.can_analyze(user_id)

    if not can:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("💎 Premium", callback_data="show_premium")
        ]])
        await update.message.reply_text(t(lang,"limit_reached"), parse_mode="Markdown", reply_markup=kb)
        return None, None, None

    # Bepul foydalanuvchiga qolgan limit haqida eslatma
    if not is_prem:
        await update.message.reply_text(
            t(lang,"free_left", left=left-1, limit=FREE_DAILY_LIMIT),
            parse_mode="Markdown"
        )

    return user_data, lang, is_prem

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data, lang, is_prem = await _check_ready_and_limit(update, context)
    if not user_data:
        return
    pos = await queue.add_to_queue(
        user_id=update.message.from_user.id, message=update.message,
        context=context, user_data=user_data, lang=lang,
        file_type="photo", is_premium=is_prem
    )
    await update.message.reply_text(t(lang,"in_queue").replace("{pos}",str(pos)), parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data, lang, is_prem = await _check_ready_and_limit(update, context)
    if not user_data:
        return
    doc = update.message.document
    mime = doc.mime_type or ""
    name = doc.file_name or ""
    allowed = ("pdf" in mime or "msword" in mime or "officedocument.word" in mime
               or name.lower().endswith((".pdf",".doc",".docx")))
    if not allowed:
        await update.message.reply_text(
            "⚠️ Faqat PDF yoki Word (DOC/DOCX) hujjatlar.\n📸 Rasm uchun galereya orqali yuboring.")
        return
    pos = await queue.add_to_queue(
        user_id=update.message.from_user.id, message=update.message,
        context=context, user_data=user_data, lang=lang,
        file_type="document", is_premium=is_prem
    )
    await update.message.reply_text(t(lang,"in_queue").replace("{pos}",str(pos)), parse_mode="Markdown")

# ─── ADMIN: PREMIUM BERISH ────────────────────────────────────────────────────
async def admin_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    # /premium 12345678 1m
    try:
        args = context.args
        target_id = int(args[0])
        period = args[1]  # 1m, 3m, 12m
        days = {"1m":30,"3m":90,"12m":365}.get(period,30)
        until = (date.today() + timedelta(days=days)).isoformat()
        db.set_premium(target_id, until)
        await update.message.reply_text(f"✅ Premium berildi: {target_id}\nMuddati: {until}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: /premium USER_ID 1m\n{e}")

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
        file_type = task.get("file_type","photo")
        is_prem   = task.get("is_premium", False)

        try:
            status_msg = await app.bot.send_message(chat_id=user_id, text=t(lang,"processing"), parse_mode="Markdown")
            age = user_data.get("age","")
            result = None
            doc_type = "Rasm" if file_type == "photo" else "Hujjat"

            if file_type == "photo":
                photo = message.photo[-1]
                file  = await app.bot.get_file(photo.file_id)
                image_bytes = bytes(await file.download_as_bytearray())
                if GEMINI_API_KEY:
                    result = await analyze_image_gemini(image_bytes, lang, age, is_prem)

            elif file_type == "document":
                doc  = message.document
                file = await app.bot.get_file(doc.file_id)
                file_bytes = bytes(await file.download_as_bytearray())
                mime = doc.mime_type or ""
                name = doc.file_name or ""
                doc_type = "PDF" if "pdf" in mime or name.lower().endswith(".pdf") else "Word"
                text_content = extract_pdf_text(file_bytes) if "pdf" in mime or name.lower().endswith(".pdf") else extract_docx_text(file_bytes)
                if not text_content:
                    await app.bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t(lang,"no_text_doc"))
                    db.increment_today(user_id)
                    queue.task_done()
                    continue
                if GEMINI_API_KEY:
                    result = await analyze_text_gemini(text_content, lang, age, is_prem)

            if not GEMINI_API_KEY:
                result = "⚠️ *GEMINI_API_KEY yo'q!*\nRailway Variables ga qo'shing:\nhttps://aistudio.google.com"

            if not result:
                result = t(lang,"error")

            # Limit hisobiga qo'shish
            db.increment_today(user_id)

            # Foydalanuvchiga natija
            await app.bot.edit_message_text(
                chat_id=user_id, message_id=status_msg.message_id,
                text=result, parse_mode="Markdown"
            )

            # Tarixga saqlash
            db.add_history(user_id, {
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "type": doc_type,
                "result_preview": result[:200]
            })

            # Log kanalga
            count    = db.increment_analysis(user_id)
            name_str = user_data.get("full_name","—")
            username = f"@{user_data['username']}" if user_data.get("username") else "—"
            phone    = user_data.get("phone","—")
            age_str  = user_data.get("age","—")
            now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            prem_label = "💎 Premium" if is_prem else "🆓 Bepul"

            log_caption = (
                f"🧠 *Radiology AI — #{count}*\n"
                f"{'─'*28}\n"
                f"👤 *Ism:* {name_str}\n"
                f"🎂 *Yosh:* {age_str}\n"
                f"📱 *Tel:* `{phone}`\n"
                f"🔹 *Username:* {username}\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"📄 *Tur:* {doc_type} | {prem_label}\n"
                f"🕐 {now} UTC\n"
                f"{'─'*28}\n"
                f"📄 *Natija:*\n{result[:900]}"
            )

            try:
                if file_type == "photo":
                    await app.bot.send_photo(chat_id=LOG_CH, photo=message.photo[-1].file_id,
                        caption=log_caption, parse_mode="Markdown")
                else:
                    await app.bot.send_document(chat_id=LOG_CH, document=message.document.file_id,
                        caption=log_caption, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Log kanal: {e}")

        except Exception as e:
            logger.error(f"Worker: {e}", exc_info=True)
            try:
                await app.bot.send_message(chat_id=user_id, text=t(lang,"error"))
            except:
                pass
        finally:
            queue.task_done()
            await asyncio.sleep(4)

async def post_init(app):
    asyncio.create_task(process_queue_worker(app))
    logger.info("✅ Bot ishga tushdi")

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", admin_premium))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(payment_callback, pattern="^(prem:|manual:|show_premium)"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🤖 Radiology AI Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
