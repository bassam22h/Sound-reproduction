import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import requests

# إعداد المتغيرات
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
API_KEY = os.getenv('SPEECHIFY_API_KEY')

# إعدادات البوت
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

# Dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)

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

    file_path = bot.get_file(file.file_id).file_path
    audio_data = requests.get(file_path).content

    response = requests.post(
        'https://api.sws.speechify.com/v1/voices',
        headers={'x-api-key': API_KEY},
        files={'audio': ('voice.ogg', audio_data)},
        data={'name': f'user_{user_id}_voice', 'consent': 'true'}
    )

    if response.status_code == 200:
        voice_id = response.json()['id']
        user_voice_ids[user_id] = voice_id
        update.message.reply_text("تم استنساخ صوتك بنجاح! أرسل الآن نصاً (200 حرف كحد أقصى).")
    else:
        update.message.reply_text("حدث خطأ أثناء استنساخ الصوت.")

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

    response = requests.post(
        'https://api.sws.speechify.com/v1/audio/speech',
        headers={'x-api-key': API_KEY, 'Content-Type': 'application/json'},
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
        update.message.reply_text("حدث خطأ أثناء التحويل.")

# إضافة الأوامر والمعالجات
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# إعداد Webhook
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

# نقطة البداية
if __name__ == '__main__':
    bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=10000)
