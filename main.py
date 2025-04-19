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

        tg_file = bot.get_file(file.file_id)
        audio_data = requests.get(tg_file.file_path).content

        response = requests.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {API_KEY}'},
            files={'audio': ('voice.ogg', audio_data, 'audio/ogg')},
            data={'name': f'user_{user_id}_voice', 'consent': 'true'}
        )

        if response.status_code == 200:
            user_voice_ids[user_id] = response.json()['id']
            update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
        else:
            update.message.reply_text(f"❌ خطأ: {response.text[:200]}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
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
