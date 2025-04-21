from telegram import Update
from telegram.ext import CallbackContext
from templates.messages import WELCOME_MESSAGE
import os

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    trials = int(os.getenv('DEFAULT_TRIALS', 2))
    max_chars = os.getenv('MAX_CHARS_PER_TRIAL', 100)
    channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
    
    # تحضير رسالة الترحيب بدون تنسيق Markdown المعقد
    welcome_msg = f"""
مرحباً {user.first_name}! 👋

🎤 هذا البوت يمكنك من استنساخ صوتك وتحويل النص إلى صوتك الخاص.

🔹 لديك {trials} محاولات مجانية
🔹 كل محاولة بحد أقصى {max_chars} حرف
🔹 الاستنساخ مسموح به مرة واحدة فقط

📢 قنواتنا الرسمية:
{', '.join(f'@{c.strip()}' for c in channels if c.strip())}

🚀 أرسل لي مقطعاً صوتياً الآن (10-30 ثانية) لبدأ الاستنساخ!
"""
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_msg,
        parse_mode=None  # إلغاء تنسيق Markdown مؤقتاً
    )
