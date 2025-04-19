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

# متغير لتخزين voice_id الخاص بكل مستخدم
user_voice_ids = {}

# أمر /start
def start(update, context):
    update.message.reply_text("أهلاً بك! أرسل مقطع صوتي لاستنساخ صوتك، ثم أرسل نص (200 حرف كحد أقصى) لتحويله إلى صوت.")

# استقبال الصوت للاستنساخ
def handle_audio(update, context):
    user_id = update.message.from_user.id
    file = update.message.voice or update.message.audio
    if not file:
        update.message.reply_text("أرسل مقطع صوتي فقط.")
        return

    try:
        file_path = bot.get_file(file.file_id).file_path
        audio_data = requests.get(file_path).content

        response = requests.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {API_KEY}'},
            files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
            data={'name': f'user_{user_id}_voice', 'consent': 'true'}
        )

        if response.status_code == 200:
            voice_id = response.json()['id']
            user_voice_ids[user_id] = voice_id
            update.message.reply_text("تم استنساخ صوتك بنجاح! أرسل الآن نصاً (200 حرف كحد أقصى).")
        else:
            error_msg = response.json().get('message', 'حدث خطأ غير معروف')
            update.message.reply_text(f"حدث خطأ أثناء استنساخ الصوت: {error_msg}")

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}")
        update.message.reply_text("حدث خطأ أثناء معالجة الملف الصوتي.")

# استقبال النصوص وتحويلها إلى صوت
def handle_text(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if len(text) > 200:
        update.message.reply_text("النص طويل جداً. الرجاء إرسال 200 حرف كحد أقصى.")
        return

    voice_id = user_voice_ids.get(user_id)
    if not voice_id:
        update.message.reply_text("أرسل مقطع صوتي أولاً لاستنساخ صوتك.")
        return

    try:
        response = requests.post(
            'https://api.sws.speechify.com/v1/audio/speech',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'voice_id': voice_id,
                'text': text,
                'output_format': 'mp3'
            }
        )

        if response.status_code == 200:
            audio_url = response.json()['url']
            update.message.reply_voice(audio_url)
        else:
            error_msg = response.json().get('message', 'حدث خطأ غير معروف')
            update.message.reply_text(f"حدث خطأ أثناء التحويل: {error_msg}")

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}")
        update.message.reply_text("حدث خطأ أثناء معالجة النص.")

# إعداد Webhook
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher = Updater(bot=bot, use_context=True).dispatcher
    
    # إضافة المعالجات
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    dispatcher.process_update(update)
    return 'ok'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
