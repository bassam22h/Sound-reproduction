import os from flask import Flask, request from telegram import Bot, Update from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters import requests

app = Flask(name)

BOT_TOKEN = os.getenv('BOT_TOKEN') WEBHOOK_URL = os.getenv('WEBHOOK_URL') API_KEY = os.getenv('SPEECHIFY_API_KEY')

bot = Bot(token=BOT_TOKEN) dispatcher = Dispatcher(bot, None, workers=0)

تخزين voice_id لكل مستخدم مؤقتًا

user_voices = {}

استقبال /start

def start(update, context): update.message.reply_text("أهلاً! أرسل مقطع صوتي (10-30 ثانية) لاستنساخ صوتك، ثم أرسل نصًا (200 حرف كحد أقصى) لتحويله للصوت.")

استقبال مقطع صوتي

def handle_voice(update, context): user_id = update.message.from_user.id file = bot.getFile(update.message.voice.file_id) file_path = f"temp/{user_id}.ogg" file.download(file_path)

with open(file_path, 'rb') as audio_file:
    response = requests.post(
        'https://api.sws.speechify.com/v1/voices',
        headers={
            'Authorization': f'Bearer {API_KEY}'
        },
        files={'file': audio_file},
        data={'name': f'user_{user_id}', 'consent': 'true'}
    )

os.remove(file_path)

if response.status_code == 200:
    voice_id = response.json().get('id')
    user_voices[user_id] = voice_id
    update.message.reply_text("تم استنساخ صوتك بنجاح! الآن أرسل نصًا (200 حرف كحد أقصى) لتحويله إلى صوت.")
else:
    update.message.reply_text("حدث خطأ أثناء استنساخ الصوت. جرّب مرة أخرى.")

استقبال نص وتحويله لصوت

def handle_text(update, context): user_id = update.message.from_user.id text = update.message.text.strip()

if len(text) > 200:
    update.message.reply_text("النص طويل جدًا. الرجاء إرسال نص لا يتجاوز 200 حرف.")
    return

voice_id = user_voices.get(user_id)
if not voice_id:
    update.message.reply_text("أرسل مقطع صوتي أولًا لاستنساخ صوتك.")
    return

response = requests.post(
    'https://api.sws.speechify.com/v1/audio/speech',
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        'text': text,
        'voice_id': voice_id,
        'output_format': 'mp3'
    }
)

if response.status_code == 200:
    audio_url = response.json().get('url')
    update.message.reply_voice(audio_url)
else:
    update.message.reply_text("حدث خطأ أثناء التحويل. تأكد من إرسال نص صحيح.")

إعداد الهاندلرز

dispatcher.add_handler(CommandHandler('start', start)) dispatcher.add_handler(MessageHandler(Filters.voice, handle_voice)) dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

Webhook endpoint

@app.route(f'/{BOT_TOKEN}', methods=['POST']) def webhook(): update = Update.de_json(request.get_json(force=True), bot) dispatcher.process_update(update) return 'ok'

if name == 'main': bot.set_webhook(f'{WEBHOOK_URL}/{BOT_TOKEN}') app.run(host='0.0.0.0', port=10000)

