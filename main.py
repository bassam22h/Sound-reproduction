import os
import asyncio
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from handlers import start, audio, text, error
from subscription import check_subscription

async def webhook_handler(request):
    return web.Response(text="Bot is running")

async def run_bot():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    PORT = int(os.getenv('PORT', 10000))
    
    # إنشاء تطبيق ويب لفتح المنفذ
    app = web.Application()
    app.router.add_get('/', webhook_handler)
    
    # إنشاء بوت التليجرام
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # تسجيل ال handlers
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

    # إعداد ويب هوك
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True
    )
    
    # تشغيل خادم الويب لفتح المنفذ
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print(f"✅ Bot running in webhook mode on port {PORT}")
    await asyncio.Event().wait()  # يبقي البوت نشطاً

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot stopped manually")
    except Exception as e:
        print(f"❌ Error: {e}")
