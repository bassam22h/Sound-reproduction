from telegram import Update
from telegram.ext import CallbackContext
from firebase import FirebaseDB
import os

FREE_LIMIT = int(os.getenv("FREE_CHAR_LIMIT", 1000))
db = FirebaseDB()

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    db.save_user(user.id, user.username)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"أهلاً {user.first_name}!

يمكنك استخدام البوت لنسخ الصوت إلى نص.

لديك {FREE_LIMIT} حرف مجاني، وبعدها تحتاج للترقية.",
    )

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    user_data = db.get_user(user_id)

    if not user_data:
        db.save_user(user_id, update.effective_user.username)
        user_data = db.get_user(user_id)

    is_premium = user_data.get("premium", False)
    used = user_data.get("used", 0)

    if not is_premium and (used + len(text)) > FREE_LIMIT:
        return update.message.reply_text("❌ لقد استهلكت الحد المسموح. قم بالترقية لاستخدام غير محدود.")

    db.update_usage(user_id, used + len(text))
    update.message.reply_text(f"✅ تم استقبال رسالتك: 
{text}

(استخدامك الحالي: {used + len(text)} حرف)")