import os
import logging
import io
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# إعداد اتصالات requests المحسنة
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=10
)
session.mount("https://", adapter)

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
    update.message.reply_text("مرحباً! أرسل مقطعاً صوتياً (10-30 ثانية، أقل من 5MB) لاستنساخ صوتك.")

def handle_audio(update, context):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            update.message.reply_text("الرجاء إرسال مقطع صوتي فقط.")
            return

        # التحقق من حجم الملف
        MAX_SIZE_MB = 5
        if file.file_size > MAX_SIZE_MB * 1024 * 1024:
            update.message.reply_text(f"❌ حجم الملف كبير جداً. الحد الأقصى {MAX_SIZE_MB}MB")
            return

        # تحميل الملف الصوتي
        try:
            tg_file = bot.get_file(file.file_id)
            audio_data = session.get(tg_file.file_path, timeout=10).content
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            update.message.reply_text("❌ فشل تحميل الملف الصوتي")
            return

        # التحقق من حجم البيانات الفعلي
        if len(audio_data) > 5 * 1024 * 1024:  # 5MB
            update.message.reply_text("❌ حجم البيانات الفعلي كبير جداً")
            return

        # إعداد الطلب
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json'
        }

        data = {
            'name': f'user_{user_id}_voice',
            'consent': 'true',
            'consent_type': 'audio_recording'
        }

        # إرسال الطلب
        try:
            response = session.post(
                'https://api.sws.speechify.com/v1/voices',
                headers=headers,
                files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
                data=data,
                timeout=15
            )

            # معالجة الاستجابة
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if 'id' in response_data:
                        user_voice_ids[user_id] = response_data['id']
                        update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
                        return
                    logger.error("No voice ID in response")
                except ValueError as e:
                    logger.error(f"JSON decode error: {str(e)}")
            
            logger.error(f"API Error: {response.status_code} - {response.text}")
            update.message.reply_text("❌ فشل في معالجة الصوت. الرجاء المحاولة بملف آخر")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            update.message.reply_text("❌ فشل الاتصال بالخادم")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع")

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
