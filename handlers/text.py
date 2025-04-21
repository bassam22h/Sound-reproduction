import os
import json
import logging
import tempfile
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from utils.temp_files import create_temp_file, delete_temp_file
from handlers.error import error_handler
from database import get_user_data, update_characters_used
from subscription import check_subscription

logger = logging.getLogger(__name__)

@check_subscription
def handle_text(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        text = update.message.text
        max_chars = int(os.getenv('MAX_CHARS_PER_TRIAL', 100))

        # تحقق من النص
        if not text or len(text) > max_chars:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"الرجاء إرسال نص صالح (بحد أقصى {max_chars} حرف)."
            )
            return

        # تحقق من وجود معرف الصوت
        user_data = get_user_data(user_id)
        voice_id = user_data.get('voice_id') if user_data else None
        if not voice_id:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ يرجى استنساخ صوتك أولاً بإرسال مقطع صوتي (10-30 ثانية)."
            )
            return

        # إرسال الطلب لتحويل النص إلى صوت
        payload = {
            "input": text,
            "voice_id": voice_id,
            "output_format": "mp3",
            "model": "simba-multilingual"
        }

        response = session.post(
            'https://api.sws.speechify.com/v1/audio/stream',
            headers={
                'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}',
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg'
            },
            json=payload,
            stream=True,
            timeout=30
        )

        if response.status_code == 200:
            try:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            temp_audio.write(chunk)
                    temp_audio_path = temp_audio.name

                with open(temp_audio_path, 'rb') as audio_file:
                    context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio_file
                    )

                os.unlink(temp_audio_path)

                # تحديث عدد الأحرف المستخدمة
                update_characters_used(user_id, len(text))

            except Exception as e:
                logger.error(f"Streaming audio processing error: {str(e)}", exc_info=True)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ حدث خطأ أثناء معالجة الصوت المتدفق"
                )

        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', response.text)
            except json.JSONDecodeError:
                error_msg = response.text

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطأ في تحويل النص: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}", exc_info=True)
        error_handler(update, context, e)
