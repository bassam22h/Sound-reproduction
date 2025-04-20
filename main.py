import os
from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from handlers import start, audio, text, error
from subscription import check_subscription

def main():
    # قراءة متغيرات البيئة
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # إضافة handlers مع التحقق من الاشتراك
    dp.add_handler(CommandHandler("start", start.start))
    dp.add_handler(MessageHandler(
        filters.VOICE | filters.AUDIO,
        check_subscription(audio.handle_audio)
    ))
    dp.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        check_subscription(text.handle_text)
    ))
    
    dp.add_error_handler(error.error_handler)

    # بدء البوت
    if os.getenv('WEBHOOK_MODE', 'false').lower() == 'true':
        PORT = int(os.getenv('PORT', 10000))
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        # إعداد ويب هوك
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=os.getenv('TELEGRAM_BOT_TOKEN'),
            webhook_url=WEBHOOK_URL,
            cert=None  # مهم لعدم استخدام SSL محلي
        )
        print(f"✅ Bot started in webhook mode on port {PORT}")
    else:
        updater.start_polling()
        print("✅ Bot started in polling mode")

    updater.idle()

if __name__ == '__main__':
    main()
