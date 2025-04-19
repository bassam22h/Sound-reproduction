import os
import logging
import json
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
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

# إنشاء Application
application = Application.builder().token(BOT_TOKEN).build()

user_voice_ids = {}

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("مرحباً! أرسل مقطعاً صوتياً لاستنساخ صوتك.")

async def handle_audio(update: Update, context: CallbackContext):
    try:
        user_id = update.message.from_user.id
        file = update.message.voice or update.message.audio
        
        if not file:
            await update.message.reply_text("الرجاء إرسال مقطع صوتي فقط.")
            return

        tg_file = await bot.get_file(file.file_id)
        audio_data = (await session.get(tg_file.file_path, timeout=10)).content

        consent_data = {
            "fullName": f"User_{user_id}",
            "email": f"user_{user_id}@bot.com"
        }

        headers = {'Authorization': f'Bearer {API_KEY}'}
        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',
            'locale': 'ar-SA',
            'consent': json.dumps(consent_data)
        }
        files = {'sample': ('voice.ogg', audio_data, 'audio/ogg')}

        response = session.post(
            'https://api.sws.speechify.com/v1/voices',
            headers=headers,
            data=data,
            files=files,
            timeout=15
        )

        if response.status_code == 200:
            voice_id = response.json().get('id')
            user_voice_ids[user_id] = voice_id
            await update.message.reply_text("✅ تم استنساخ صوتك بنجاح!")
        else:
            await update.message.reply_text(f"❌ خطأ: {response.text}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")

async def handle_text(update: Update, context: CallbackContext):
    try:
        user_id = update.message.from_user.id
        text = update.message.text

        if not text or len(text) > 500:
            await update.message.reply_text("الرجاء إرسال نص صالح (500 حرف كحد أقصى).")
            return

        voice_id = user_voice_ids.get(user_id)
        if not voice_id:
            await update.message.reply_text("❌ يرجى استنساخ صوتك أولاً.")
            return

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "text": text,
            "voice_id": voice_id,
            "output_format": "mp3"
        }

        response = session.post(
            'https://api.sws.speechify.com/v1/audio/speech',
            headers=headers,
            json=payload,
            timeout=25
        )

        if response.status_code == 200:
            audio_url = response.json().get('url')
            if audio_url:
                await update.message.reply_voice(audio_url)
            else:
                await update.message.reply_text("❌ لم يتم إنشاء الصوت")
        else:
            await update.message.reply_text(f"❌ خطأ: {response.text}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")

# إضافة handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    json_data = await request.get_json()
    update = Update.de_json(json_data, bot)
    await application.update_queue.put(update)
    return 'ok'

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
