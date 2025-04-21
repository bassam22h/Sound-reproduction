import os
import json
import logging
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from database import get_user_data, save_voice_id

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

        # تحميل الملف الصوتي
        tg_file = context.bot.get_file(file.file_id)
        audio_data = session.get(tg_file.file_path, timeout=10).content

        # تحضير بيانات الموافقة
        consent_data = {
            "fullName": f"User_{user_id}",
            "email": f"user_{user_id}@bot.com"
        }

        # تحضير بيانات الطلب
        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',
            'consent': json.dumps(consent_data, ensure_ascii=False)
        }

        files = {
            'sample': ('voice_sample.ogg', audio_data, 'audio/ogg'),
            **{k: (None, str(v)) for k, v in data.items()}
        }

        # إرسال الطلب إلى API
        response = session.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}'},
            files=files,
            timeout=15
        )

        if response.status_code == 200:
            voice_id = response.json().get('id')
            save_voice_id(user_id, voice_id)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ تم استنساخ صوتك بنجاح! يمكنك الآن إرسال النص لتحويله إلى صوت."
            )
        else:
            error_msg = response.json().get('message', 'Unknown error')
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطأ في API: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}")
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ حدث خطأ غير متوقع أثناء معالجة الصوت"
        )
