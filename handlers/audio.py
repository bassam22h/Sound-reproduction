from telegram import Update
from telegram.ext import CallbackContext
from database import get_user_data, decrement_trials
import logging

logger = logging.getLogger(__name__)

def handle_audio(update: Update, context: CallbackContext):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="الرجاء إرسال مقطع صوتي فقط (بين 10-30 ثانية)."
            )
            return

        # استمرار باقي الكود بدون await
        tg_file = context.bot.get_file(file.file_id)
        audio_data = tg_file.download_as_bytearray()

        # معالجة الصوت...
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ تم استنساخ صوتك بنجاح!"
        )
        
        decrement_trials(user_id)

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}")
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ حدث خطأ أثناء معالجة الصوت"
        )
