import os
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from handlers import start, audio, text, error
from subscription import check_subscription

def ensure_single_instance(bot_token):
    """يتأكد من عدم وجود نسخ أخرى تعمل"""
    from telegram import Bot
    bot = Bot(token=bot_token)
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(3)  # انتظر 3 ثوانٍ لضمان الإغلاق
    except Exception as e:
        print(f"⚠️ Warning: {e}")

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # الخطوة الحاسمة: إيقاف أي نسخ متعارضة
    ensure_single_instance(BOT_TOKEN)
    
    # إعداد البوت بشكل مبسط
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # تسجيل ال handlers
    dp.add_handler(CommandHandler("start", start.start))
    dp.add_handler(MessageHandler(
        Filters.voice | Filters.audio,
        check_subscription(audio.handle_audio)
    ))
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        check_subscription(text.handle_text)
    ))
    
    dp.add_error_handler(error.error_handler)

    # تشغيل البوت (ويب هوك فقط)
    PORT = int(os.getenv('PORT', 10000))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True
    )
    print(f"✅ البوت يعمل على الويب هوك (البورت: {PORT})")
    print(f"✅ عنوان الويب هوك: {WEBHOOK_URL}/{BOT_TOKEN}")
    
    updater.idle()

if __name__ == '__main__':
    main()
