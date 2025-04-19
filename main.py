import os
import logging
import json
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ===== إعداد اتصالات HTTP محسنة =====
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=20,
    pool_maxsize=20
)
session.mount("https://", adapter)
session.mount("http://", adapter)

# ===== إعداد التسجيل =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== إعدادات البوت =====
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('SPEECHIFY_API_KEY')
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

# ===== تخزين البيانات =====
user_voice_ids = {}

# ===== معالجة الأوامر =====
def start(update, context):
    update.message.reply_text(
        "مرحباً! 👋\n"
        "1. أرسل مقطعاً صوتياً (10-30 ثانية) لاستنساخ صوتك\n"
        "2. ثم أرسل النص لتحويله إلى صوتك المستنسخ\n"
        "⚠️ سيتم استخدام بيانات وهمية للاختبار"
    )

# ===== معالجة المقاطع الصوتية =====
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
            logger.info(f"تم تحميل الملف الصوتي للمستخدم {user_id}")
        except Exception as e:
            logger.error(f"فشل تحميل الملف: {str(e)}")
            update.message.reply_text("❌ فشل تحميل الملف الصوتي")
            return

        # إعداد بيانات الموافقة
        consent_data = {
            "fullName": f"Telegram_User_{user_id}",
            "email": f"user_{user_id}@speechify.dummy"
        }

        # إعداد طلب API
        headers = {'Authorization': f'Bearer {API_KEY}'}
        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',
            'locale': 'ar-SA',
            'consent': json.dumps(consent_data)
        }
        files = {'sample': ('voice.ogg', audio_data, 'audio/ogg')}

        # إرسال الطلب
        try:
            response = session.post(
                'https://api.sws.speechify.com/v1/voices',
                headers=headers,
                data=data,
                files=files,
                timeout=20
            )
            logger.info(f"استجابة استنساخ الصوت: {response.status_code}")

            if response.status_code == 200:
                voice_id = response.json().get('id')
                if voice_id:
                    user_voice_ids[user_id] = voice_id
                    update.message.reply_text("✅ تم استنساخ صوتك بنجاح! أرسل الآن النص لتحويله إلى صوت.")
                    logger.info(f"تم حفظ voice_id للمستخدم {user_id}: {voice_id}")
                else:
                    logger.error("لا يوجد voice_id في الاستجابة")
                    update.message.reply_text("❌ خطأ في معالجة الاستجابة")
            else:
                error_msg = response.text[:200] if response.text else f"خطأ {response.status_code}"
                logger.error(f"خطأ API: {error_msg}")
                update.message.reply_text(f"❌ فشل الاستنساخ: {error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"فشل الاتصال: {str(e)}")
            update.message.reply_text("❌ فشل الاتصال بخادم الاستنساخ")

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع")

# ===== معالجة النصوص =====
def handle_text(update, context):
    try:
        user_id = update.message.from_user.id
        text = update.message.text.strip()

        if not text or len(text) > 500:  # زيادة الحد إلى 500 حرف
            update.message.reply_text("الرجاء إرسال نص صالح (500 حرف كحد أقصى).")
            return

        voice_id = user_voice_ids.get(user_id)
        if not voice_id:
            update.message.reply_text("❌ لم يتم العثور على صوت مستنسخ. أرسل مقطعًا صوتيًا أولاً.")
            return

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        # التعديل الرئيسي هنا: تغيير هيكل الطلب حسب وثائق API
        payload = {
            'input': {  # الحقل المطلوب حسب السجلات
                'text': text,
                'voice_id': voice_id,
                'output_format': 'mp3'
            }
        }

        logger.info(f"إرسال طلب تحويل النص: {payload}")

        response = session.post(
            'https://api.sws.speechify.com/v1/audio/speech',
            headers=headers,
            json=payload,
            timeout=30
        )

        logger.info(f"استجابة تحويل النص: {response.status_code} - {response.text}")

        if response.status_code == 200:
            try:
                response_data = response.json()
                if 'url' in response_data:
                    update.message.reply_voice(response_data['url'])
                elif 'audio_url' in response_data:  # بعض APIs تستخدم تسميات مختلفة
                    update.message.reply_voice(response_data['audio_url'])
                else:
                    logger.error("لا يوجد رابط صوت في الاستجابة")
                    update.message.reply_text("❌ لم يتم إنشاء الصوت")
            except ValueError as e:
                logger.error(f"خطأ في تحليل JSON: {str(e)}")
                update.message.reply_text("❌ خطأ في معالجة الاستجابة")
        else:
            error_msg = response.text[:200] if response.text else f"خطأ {response.status_code}"
            logger.error(f"خطأ تحويل النص: {error_msg}")
            update.message.reply_text(f"❌ فشل التحويل: {error_msg}")

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع")

# ===== Webhook Route =====
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        updater = Updater(bot=bot, use_context=True)
        
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
        
        dp.process_update(update)
        return 'ok'
    except Exception as e:
        logger.error(f"خطأ في webhook: {str(e)}")
        return 'error', 500

# ===== التشغيل الرئيسي =====
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
