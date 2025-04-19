import os
import requests
from flask import Flask, request
from telegram import Bot, InputFile

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN)

# خريطة لتخزين voice_id للمستخدمين
user_voice_ids = {}

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    return "Webhook set!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        message = data["message"]

        # استقبال النصوص
        if "text" in message:
            text = message["text"]
            if len(text) > 500:
                bot.send_message(chat_id=chat_id, text="عذرًا، الحد الأقصى 500 حرف.")
                return "OK"

            # تحقق لو عنده voice_id مستنسخ
            voice_id = user_voice_ids.get(chat_id, "ar-ye-nasser")

            api_url = "https://api.sws.speechify.com/v1/audio/speech"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            payload = {
                "text": text,
                "voice_id": voice_id,
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
                bot.send_message(chat_id=chat_id, text=f"خطأ أثناء التحويل: {e}")

        # استقبال مقطع صوتي للاستنساخ
        elif "voice" in message:
            file_id = message["voice"]["file_id"]
            file_info = bot.get_file(file_id)
            file_url = file_info.file_path
            local_file = f"{chat_id}_sample.ogg"
            voice_file = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_url}")

            with open(local_file, "wb") as f:
                f.write(voice_file.content)

            # رفع المقطع لـ Speechify
            api_url = "https://api.sws.speechify.com/v1/voices"
            headers = {
                "Authorization": f"Bearer {API_KEY}"
            }
            files = {
                "audio": open(local_file, "rb"),
            }
            data = {
                "name": f"User_{chat_id}_voice",
                "consent": "true"
            }

            try:
                response = requests.post(api_url, headers=headers, files=files, data=data)
                response.raise_for_status()
                new_voice_id = response.json()["id"]
                user_voice_ids[chat_id] = new_voice_id

                bot.send_message(chat_id=chat_id, text="تم استنساخ الصوت بنجاح! يمكنك الآن إرسال نصوص لتحويلها بهذا الصوت.")

            except Exception as e:
                bot.send_message(chat_id=chat_id, text=f"فشل في استنساخ الصوت: {e}")

            finally:
                os.remove(local_file)

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
