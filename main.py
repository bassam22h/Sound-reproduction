import os
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from handlers import start, audio, text, error
from subscription import check_subscription

def stop_previous_instances(bot_token):
    """إيقاف أي نسخ سابقة من البوت"""
    from telegram import Bot
    bot = Bot(token=bot_token)
    try:
        bot.delete_webhook()
        time.sleep(2)
    except:
        pass

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    stop_previous_instances(BOT_TOKEN)
    
    # إعداد Updater بدون pool_timeout
    updater = Updater(
        token=BOT_TOKEN,
        use_context=True,
        workers=1,
        request_kwargs={
            'read_timeout': 30,
            'connect_timeout': 30
        }
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
    
    # معالج أخطاء متزامن
    def sync_error_handler(update, context):
        try:
            error.error_handler(update, context)
        except Exception as e:
            print(f"⚠️ Error in error handler: {e}")
    
    dp.add_error_handler(sync_error_handler)

    # تشغيل البوت
    if os.getenv('WEBHOOK_MODE', 'false').lower() == 'true':
        PORT = int(os.getenv('PORT', 10000))
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            clean=True,
            drop_pending_updates=True
        )
        print(f"✅ Bot running in webhook mode on port {PORT}")
    else:
        updater.start_polling(
            clean=True,
            timeout=30,
            read_latency=5,
            drop_pending_updates=True
        )
        print("✅ Bot running in polling mode")

    updater.idle()

if __name__ == '__main__':
    main()
