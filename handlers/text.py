import os
import logging
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from utils.temp_files import create_temp_file, delete_temp_file
from handlers.error import error_handler
from database import get_user_data, update_characters_used

logger = logging.getLogger(__name__)

async def handle_text(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        text = update.message.text
        max_chars = int(os.getenv('MAX_CHARS_PER_TRIAL', 100))

        # التحقق من طول النص
        if not text or len(text) > max_chars:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"الرجاء إرسال نص صالح (بحد أقصى {max_chars} حرف)."
            )
            return

        # التحقق من وجود صوت مستنسخ
        voice_id = context.user_data.get('voice_id')
        if not voice_id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ يرجى استنساخ صوتك أولاً بإرسال مقطع صوتي (10-30 ثانية)."
            )
            return

        # معالجة النص وتحويله إلى صوت...
        payload = {
            "input": text,
            "voice_id": voice_id,
            "output_format": "mp3",
            "model": "simba-multilingual"
        }

        response = await session.post(
            'https://api.sws.speechify.com/v1/audio/stream',
            headers={
                'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}',
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg'
            },
            json=payload
        )

        if response.status_code == 200:
            temp_file = await create_temp_file(response.content, suffix='.mp3')
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=open(temp_file, 'rb')
            )
            await delete_temp_file(temp_file)
            
            # تحديث عدد الأحرف المستخدمة
            update_characters_used(user_id, len(text))
        else:
            error_msg = response.json().get('message', response.text)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطأ في تحويل النص: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}")
        await error_handler(update, context, e)
