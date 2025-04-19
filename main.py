import os
import telebot
import requests
from flask import Flask, request

# إعداد المتغيرات من البيئة
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# حد الأحرف
MAX_LENGTH = 500

# استقبال الرسائل النصية من المستخدم
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    text = message.text.strip()
    chat_id = message.chat.id

    if len(text) > MAX_LENGTH:
        bot.reply_to(message, f"النص طويل جدًا. الحد الأقصى {MAX_LENGTH} حرف.")
        return

    bot.send_message(chat_id, "جاري تحويل النص إلى صوت باللهجة اليمنية...")

    audio_url = generate_audio(text)
    if audio_url:
        bot.send_audio(chat_id, audio_url, caption="تم التحويل! استمع للصوت من هنا.")
    else:
        bot.send_message(chat_id, "حدث خطأ أثناء التحويل، حاول مجددًا.")

# دالة طلب التحويل من Speechify
def generate_audio(text):
    try:
        url = "https://api.sws.speechify.com/v1/audio/speech"
        headers = {
            "accept": "application/json",
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "voice_id": "ar_ye_male_speaker_1",  # صوت عربي يمني — استبدله حسب ID صوتك من المنصة
            "text": text,
            "output_format": "mp3"
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            audio_url = response.json().get("audio_url")
            return audio_url
        else:
            print("Error:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Exception:", e)
        return None

# إعداد Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

# نقطة البداية
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=10000)
