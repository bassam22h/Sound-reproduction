import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from handlers import start, audio, text, error

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start.start))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, audio.handle_audio))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text.handle_text))
    dp.add_error_handler(error.error_handler)

    PORT = int(os.getenv('PORT', 10000))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True
    )
    print(f"✅ البوت يعمل الآن على البورت {PORT}")
    updater.idle()

if __name__ == '__main__':
    main()
