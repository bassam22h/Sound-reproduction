import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from handlers import start, audio, text, error
from subscription import check_subscription, verify_subscription

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    PORT = int(os.getenv('PORT', 10000))

    if not BOT_TOKEN or not WEBHOOK_URL:
        raise ValueError("TELEGRAM_BOT_TOKEN أو WEBHOOK_URL غير مضبوط في متغيرات البيئة")

    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CallbackQueryHandler(verify_subscription, pattern="^verify_subscription$"))
    dp.add_handler(CommandHandler("start", start.start))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, check_subscription(audio.handle_audio)))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_subscription(text.handle_text)))
    dp.add_error_handler(error.error_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True
    )

    updater.idle()

if __name__ == '__main__':
    main()
