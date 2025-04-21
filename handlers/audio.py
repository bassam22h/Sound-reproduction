import os
import json
import logging
from telegram import Update
from telegram.ext import CallbackContext
from utils.requests import session
from database import save_voice_id  # حذفنا get_user_data

logger = logging.getLogger(__name__)

def handle_audio(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        voice_file = update.message.voice or update.message.audio

        if not voice_file:
            update.message.reply_text("❌ لم يتم العثور على ملف صوتي صالح.")
            return
        
        file = voice_file.get_file()
        file_path = f'temp_{user.id}.ogg'
        file.download(file_path)
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = session.post(os.getenv('AUDIO_UPLOAD_ENDPOINT'), files=files)
        
        if response.status_code == 200:
            data = response.json()
            voice_id = data.get('voice_id')
            if voice_id:
                save_voice_id(user.id, voice_id)
                update.message.reply_text("✅ تم حفظ الصوت بنجاح! يمكنك الآن تحويل النصوص إلى صوتك.")
            else:
                update.message.reply_text("❌ لم يتم الحصول على معرف الصوت.")
        else:
            update.message.reply_text("❌ حدث خطأ أثناء رفع الملف.")
        
    except Exception as e:
        logger.error(f"خطأ في التعامل مع الصوت: {str(e)}")
        update.message.reply_text("❌ حدث خطأ أثناء معالجة الملف الصوتي.")
