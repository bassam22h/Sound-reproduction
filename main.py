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

        # 1. التحقق من حجم الملف قبل التحميل
        MAX_SIZE_MB = 5  # 5MB كحد أقصى حسب وثائق API
        if file.file_size > MAX_SIZE_MB * 1024 * 1024:
            update.message.reply_text(f"❌ حجم الملف كبير جداً. الحد الأقصى {MAX_SIZE_MB}MB")
            return

        # 2. تحميل الملف الصوتي مع التحكم بالوقت
        try:
            tg_file = bot.get_file(file.file_id)
            audio_data = requests.get(tg_file.file_path, timeout=10).content
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            update.message.reply_text("❌ فشل تحميل الملف الصوتي")
            return

        # 3. التحقق من حجم البيانات الفعلي
        if len(audio_data) > 100 * 1024 * 1024:  # 100MB
            update.message.reply_text("❌ حجم البيانات الفعلي كبير جداً")
            return

        # 4. إعداد الطلب الأمثل
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json'
        }

        # 5. أفضل صيغة للموافقة (حسب آخر وثائق API)
        data = {
            'name': f'user_{user_id}_voice',
            'consent': 'true',
            'consent_type': 'audio_recording',
            'source': 'telegram_bot'
        }

        # 6. إرسال الطلب مع التعامل مع الملف بشكل صحيح
        try:
            response = requests.post(
                'https://api.sws.speechify.com/v1/voices',
                headers=headers,
                files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
                data=data,
                timeout=15
            )

            # 7. معالجة الاستجابة بدقة
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if 'id' in response_data:
                        user_voice_ids[user_id] = response_data['id']
                        update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
                        return
                    else:
                        logger.error("No voice ID in response")
                except ValueError:
                    logger.error("Invalid JSON response")
            
            logger.error(f"API Error: {response.status_code} - {response.text}")
            update.message.reply_text("❌ فشل في معالجة الصوت. الرجاء المحاولة بملف آخر")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            update.message.reply_text("❌ فشل الاتصال بالخادم")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع")

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
