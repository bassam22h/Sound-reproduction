import os
import requests
from flask import Flask, request
from telegram import Bot
from telegram import InputFile

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN)

# إعداد Webhook مرة واحدة
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    return "Webhook set successfully!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if len(text) > 500:
            bot.send_message(chat_id=chat_id, text="عذرًا، الحد الأقصى للنص هو 500 حرف.")
            return "OK"

        # إعداد بيانات API Speechify
        api_url = "https://api.sws.speechify.com/v1/audio/speech"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        payload = {
            "text": text,
            "voice_id": "ar-ye-nasser",  # الصوت اليمني من Speechify (تأكد من معرف الصوت الخاص بك)
            "output_format": "mp3"
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            audio_url = response.json()["url"]

            audio_data = requests.get(audio_url)
            audio_file = f"voice_{chat_id}.mp3"
            with open(audio_file, "wb") as f:
                f.write(audio_data.content)

            bot.send_audio(chat_id=chat_id, audio=InputFile(audio_file))
            os.remove(audio_file)

        except Exception as e:
            bot.send_message(chat_id=chat_id, text=f"حدث خطأ أثناء تحويل النص: {e}")

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
