import os
import logging
import json
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# إعداد اتصالات requests محسنة
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
    update.message.reply_text(
        "مرحباً! أرسل مقطعاً صوتياً (10-30 ثانية) لاستنساخ صوتك.\n"
        "⚠️ سيتم استخدام بيانات وهمية للاختبار"
    )

def handle_audio(update, context):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            update.message.reply_text("الرجاء إرسال مقطع صوتي فقط.")
            return

        # التحقق من حجم الملف (5MB كحد أقصى)
        MAX_SIZE_MB = 5
        if file.file_size > MAX_SIZE_MB * 1024 * 1024:
            update.message.reply_text(f"❌ حجم الملف كبير جداً. الحد الأقصى {MAX_SIZE_MB}MB")
            return

        # تحميل الملف الصوتي
        try:
            tg_file = bot.get_file(file.file_id)
            audio_data = session.get(tg_file.file_path, timeout=10).content
        except Exception as e:
            logger.error(f"فشل التحميل: {str(e)}")
            update.message.reply_text("❌ فشل تحميل الملف الصوتي")
            return

        # إعداد بيانات الموافقة الافتراضية (وهمية)
        consent_data = {
            "fullName": f"Telegram_User_{user_id}",  # اسم وهمي
            "email": f"user_{user_id}@speechify.dummy"  # بريد وهمي متوافق مع الشروط
        }

        # إعداد الطلب
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json'
        }

        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',  # أو 'female' أو 'notSpecified'
            'locale': 'ar-SA',  # كود اللغة العربية
            'consent': json.dumps(consent_data)  # تحويل الـ JSON إلى string
        }

        files = {
            'sample': ('voice.ogg', audio_data, 'audio/ogg')  # المفتاح يجب أن يكون 'sample'
        }

        # إرسال الطلب
        try:
            response = session.post(
                'https://api.sws.speechify.com/v1/voices',
                headers=headers,
                data=data,
                files=files,
                timeout=15
            )

            # معالجة الاستجابة
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if 'id' in response_data:
                        user_voice_ids[user_id] = response_data['id']
                        update.message.reply_text("✅ تم استنساخ صوتك بنجاح! أرسل الآن النص لتحويله إلى صوت.")
                        return
                    else:
                        logger.error("لا يوجد معرف صوت في الاستجابة")
                except ValueError:
                    logger.error("استجابة JSON غير صالحة")
            
            logger.error(f"خطأ API: {response.status_code} - {response.text}")
            update.message.reply_text("❌ فشل في معالجة الصوت. الرجاء المحاولة لاحقاً")

        except requests.exceptions.RequestException as e:
            logger.error(f"فشل الاتصال: {str(e)}")
            update.message.reply_text("❌ فشل الاتصال بالخادم")

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
