import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
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

# Dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)
user_voice_ids = {}

def start(update, context):
    update.message.reply_text("مرحباً! أرسل مقطعاً صوتياً (10-30 ثانية) لاستنساخ صوتك.")

def handle_audio(update, context):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            update.message.reply_text("الرجاء إرسال مقطع صوتي فقط.")
            return

        # تحميل الملف الصوتي
        tg_file = bot.get_file(file.file_id)
        audio_data = requests.get(tg_file.file_path).content

        # إعداد الطلب مع التركيز على معلمة consent
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Accept': 'application/json'
        }

        # الحل الجديد: إرسال consent كـ "1" أو "yes" بدلاً من true/True
        
        data = {
    'name': f'user_{user_id}_voice',
    'consent': "true"  # أو جرب "1" أو "yes"
}

# أو جرب إرسالها كـ JSON بدلاً من form-data
response = requests.post(
    'https://api.sws.speechify.com/v1/voices',
    headers=headers,
    files={'audio': ('voice.ogg', audio_data)},
    data=data,
    # أو جرب:
    # json={'name': data['name'], 'consent': data['consent'], 'audio': audio_data}
)

        logger.info(f"API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            voice_id = response.json().get('id')
            if voice_id:
                user_voice_ids[user_id] = voice_id
                update.message.reply_text("✅ تم استنساخ صوتك بنجاح! أرسل الآن النص الذي تريد تحويله إلى صوت.")
            else:
                update.message.reply_text("❌ لم يتم الحصول على معرف الصوت من الاستجابة.")
        else:
            error_msg = f"خطأ في الخادم: {response.status_code}"
            try:
                error_details = response.json()
                error_msg = error_details.get('message', 
                             error_details.get('error', str(error_details)))
            except:
                error_msg = response.text[:200] or error_msg
            update.message.reply_text(f"❌ {error_msg}")

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع أثناء معالجة طلبك.")
def handle_text(update, context):
    try:
        user_id = update.message.from_user.id
        text = update.message.text

        if not text or len(text) > 200:
            update.message.reply_text("الرجاء إرسال نص لا يزيد عن 200 حرف.")
            return

        voice_id = user_voice_ids.get(user_id)
        if not voice_id:
            update.message.reply_text("الرجاء إرسال مقطع صوتي أولاً لاستنساخ صوتك.")
            return

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'voice_id': voice_id,
            'text': text,
            'output_format': 'mp3'
        }

        response = requests.post(
            'https://api.sws.speechify.com/v1/audio/speech',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            audio_url = response.json().get('url')
            if audio_url:
                update.message.reply_voice(audio_url)
            else:
                update.message.reply_text("❌ لم يتم الحصول على رابط الصوت من الاستجابة.")
        else:
            error_msg = f"خطأ في الخادم: {response.status_code}"
            try:
                error_msg = response.json().get('message', error_msg)
            except:
                error_msg = response.text[:200] or error_msg
            update.message.reply_text(f"❌ {error_msg}")

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}", exc_info=True)
        update.message.reply_text("❌ حدث خطأ غير متوقع أثناء معالجة النص.")

# إعداد المعالجات
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

if __name__ == '__main__':
    # تأكد من أن المتغيرات البيئية مضبوطة
    if not all([BOT_TOKEN, API_KEY]):
        logger.error("❌ المفاتيح المطلوبة غير مضبوطة!")
        exit(1)
        
    logger.info("✅ بدء تشغيل البوت...")
    app.run(host="0.0.0.0", port=10000)
