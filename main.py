import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from handlers import start, audio, text, error
from subscription import check_subscription

async def main():
    # قراءة متغيرات البيئة
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # إنشاء التطبيق (بدلاً من Updater)
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # إضافة handlers
    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(MessageHandler(
        filters.VOICE | filters.AUDIO,
        check_subscription(audio.handle_audio)
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        check_subscription(text.handle_text)
    ))
    
    application.add_error_handler(error.error_handler)

    # بدء البوت
    if os.getenv('WEBHOOK_MODE', 'false').lower() == 'true':
        PORT = int(os.getenv('PORT', 10000))
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        await application.bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        print(f"✅ Bot started in webhook mode on port {PORT}")
    else:
        await application.run_polling()
        print("✅ Bot started in polling mode")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
