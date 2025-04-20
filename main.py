import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from handlers import start, audio, text, error
from subscription import check_subscription

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # إعداد Updater مع exclusive=True لمنع التعارض
    updater = Updater(
        token=BOT_TOKEN,
        use_context=True,
        workers=1,
        request_kwargs={'read_timeout': 20, 'connect_timeout': 20}
    )
    
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

    # تشغيل البوت
    if os.getenv('WEBHOOK_MODE', 'false').lower() == 'true':
        PORT = int(os.getenv('PORT', 10000))
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            clean=True  # يوقف أي نسخ أخرى تعمل
        )
        print(f"✅ Bot running in webhook mode on port {PORT}")
    else:
        updater.start_polling(
            clean=True,  # يوقف أي نسخ أخرى تعمل
            timeout=20,
            read_latency=5
        )
        print("✅ Bot running in polling mode")

    updater.idle()

if __name__ == '__main__':
    main()
