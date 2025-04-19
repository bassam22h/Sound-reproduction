import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# إعدادات البوت
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('SPEECHIFY_API_KEY')
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

user_voice_ids = {}

def start(update, context):
    update.message.reply_text("مرحباً! أرسل مقطعاً صوتياً لاستنساخ صوتك.")

def handle_audio(update, context):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            update.message.reply_text("الرجاء إرسال مقطع صوتي فقط.")
            return

        # 1. تحميل الملف الصوتي
        tg_file = bot.get_file(file.file_id)
        audio_data = requests.get(tg_file.file_path, timeout=10).content

        # 2. إعداد الطلب مع تحسينات حاسمة
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json',
            'Content-Type': 'multipart/form-data'
        }

        # 3. جميع الصيغ الممكنة للموافقة
        consent_attempts = [
            {'consent': 'true', 'consent_type': 'recording'},  # الصيغة الأكثر شيوعاً
            {'consent': '1', 'consent_verified': 'yes'},
            {'consent': 'accepted'},
            {'consent': 'yes', 'agree_to_terms': 'true'}
        ]

        for attempt in consent_attempts:
            data = {'name': f'user_{user_id}_voice', **attempt}
            
            try:
                # 4. إرسال الطلب مع التحكم الكامل
                response = requests.post(
                    'https://api.sws.speechify.com/v1/voices',
                    headers=headers,
                    files={'audio': ('voice_recording.ogg', audio_data, 'audio/ogg')},
                    data=data,
                    timeout=15
                )

                # 5. تحليل الاستجابة بشكل أقوى
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if 'id' in response_data:
                            user_voice_ids[user_id] = response_data['id']
                            update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
                            return
                    except ValueError:
                        continue

                # 6. تسجيل تفاصيل الخطأ
                logger.error(f"Attempt failed: {attempt} | Status: {response.status_code} | Response: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                continue

        # 7. إذا فشلت جميع المحاولات
        update.message.reply_text("❌ تعذر استنساخ الصوت. الرجاء المحاولة لاحقاً أو مراجعة الدعم الفني.")
        logger.critical(f"All consent attempts failed for user {user_id}")

    except Exception as e:
        logger.error(f"Critical error: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع في النظام.")

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    updater = Updater(bot=bot, use_context=True)
    
    # إضافة المعالجات
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
    
    dp.process_update(update)
    return 'ok'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
