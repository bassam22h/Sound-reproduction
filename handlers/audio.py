import os
import json
import logging
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from database import save_voice_id
from subscription import check_subscription

logger = logging.getLogger(__name__)

@check_subscription
def handle_audio(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_id = user.id
        voice_file = update.message.voice or update.message.audio

        if not voice_file:
            update.message.reply_text("❌ لم يتم العثور على ملف صوتي صالح.")
            return

        # تحميل الملف الصوتي من تليجرام
        file = voice_file.get_file()
        audio_data = session.get(file.file_path, timeout=10).content

        # تحضير بيانات الإرسال
        consent_data = {
            "fullName": f"User_{user_id}",
            "email": f"user_{user_id}@bot.com"
        }

        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',
            'consent': json.dumps(consent_data, ensure_ascii=False)
        }

        files = {
            'sample': ('voice_sample.ogg', audio_data, 'audio/ogg'),
        }

        for key, value in data.items():
            files[key] = (None, str(value))

        response = session.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}'},
            files=files,
            timeout=15
        )

        if response.status_code == 200:
            voice_id = response.json().get('id')
            if voice_id:
                save_voice_id(user_id, voice_id)
                update.message.reply_text("✅ تم استنساخ صوتك بنجاح! يمكنك الآن إرسال نص لتحويله إلى صوت.")
            else:
                update.message.reply_text("❌ لم يتم الحصول على معرف الصوت من الخادم.")
        else:
            error_msg = response.json().get('message', 'Unknown error')
            update.message.reply_text(f"❌ خطأ في API: {error_msg}")

    except json.JSONDecodeError:
        logger.error("فشل فك تشفير استجابة JSON")
        update.message.reply_text("❌ حدث خطأ في معالجة الرد من الخادم.")
    except Exception as e:
        logger.error(f"خطأ في التعامل مع الصوت: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع أثناء معالجة الصوت.")
