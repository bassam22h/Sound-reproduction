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

        # تحميل الملف الصوتي
        tg_file = bot.get_file(file.file_id)
        audio_data = session.get(tg_file.file_path, timeout=10).content

        # الطريقة المضمونة لإرسال البيانات
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json'
        }

        # المحاولة بجميع الصيغ الممكنة للموافقة
        consent_attempts = [
            {'consent': 'true', 'consent_type': 'explicit'},  # الأكثر شيوعاً
            {'consent': '1', 'consent_verified': 'true'},     # البديل الرقمي
            {'consent': 'agreed'},                           # صيغة بديلة
            {'consent': 'yes', 'terms_accepted': 'true'},     # صيغة أخرى
            {'consent': 'approved'},                          # كحل أخير
            {}  # محاولة بدون أي معاملات موافقة (في حال كان السيرفر يتجاهلها)
        ]

        for attempt in consent_attempts:
            try:
                # إعداد البيانات مع المحاولة الحالية
                data = {'name': f'user_{user_id}_voice', **attempt}
                
                # إرسال الطلب بطريقتين مختلفتين
                for use_json in [False, True]:
                    try:
                        if use_json:
                            # المحاولة بإرسال البيانات كـ JSON
                            response = session.post(
                                'https://api.sws.speechify.com/v1/voices',
                                headers={**headers, 'Content-Type': 'application/json'},
                                json=data,
                                files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
                                timeout=15
                            )
                        else:
                            # المحاولة بإرسال البيانات كـ form-data
                            response = session.post(
                                'https://api.sws.speechify.com/v1/voices',
                                headers=headers,
                                data=data,
                                files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
                                timeout=15
                            )

                        # معالجة الاستجابة
                        if response.status_code == 200:
                            voice_id = response.json().get('id')
                            if voice_id:
                                user_voice_ids[user_id] = voice_id
                                update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
                                return
                            
                        logger.info(f"Attempt: {attempt} | Method: {'JSON' if use_json else 'Form'} | Status: {response.status_code} | Response: {response.text}")

                    except Exception as e:
                        logger.error(f"Attempt failed: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"Consent attempt failed: {str(e)}")
                continue

        # إذا فشلت جميع المحاولات
        update.message.reply_text("❌ تعذر استنساخ الصوت. الرجاء التواصل مع الدعم الفني.")
        logger.critical("All consent attempts failed")

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
