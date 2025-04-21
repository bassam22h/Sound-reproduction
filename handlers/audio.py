import os
import logging
import json
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from database import get_user_data
from handlers.error import error_handler

logger = logging.getLogger(__name__)

def handle_audio(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="الرجاء إرسال مقطع صوتي فقط (بين 10-30 ثانية)."
            )
            return

        # التحقق من المحاولات المتبقية
        user_data = get_user_data(user_id)
        if user_data.get('trials', 0) <= 0:
            return

        # استمرار معالجة الصوت...
        tg_file = await context.bot.get_file(file.file_id)
        audio_data = (await session.get(tg_file.file_path)).content

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
            **{k: (None, str(v)) for k, v in data.items()}
        }

        response = await session.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}'},
            files=files
        )

        if response.status_code == 200:
            voice_id = response.json().get('id')
            context.user_data['voice_id'] = voice_id
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ تم استنساخ صوتك بنجاح! يمكنك الآن إرسال النص لتحويله إلى صوت."
            )
            # خصم محاولة
            from database import decrement_trials
            decrement_trials(user_id)
        else:
            error_msg = response.json().get('message', 'Unknown error')
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطأ في API: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}")
        await error_handler(update, context, e)
