import logging
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import ParseMode
import admin, subscription, premium
from firebase import FirebaseDB
import os

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get('PORT', 8443))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

firebase = FirebaseDB()

updater = Updater(token=TOKEN, use_context=True)
dp = updater.dispatcher

# أوامر المستخدم
dp.add_handler(CommandHandler("start", subscription.start))
dp.add_handler(MessageHandler(Filters.text & (~Filters.command), subscription.handle_message))

# لوحات الأزرار
dp.add_handler(CallbackQueryHandler(admin.handle_callback))

# أوامر المشرف
dp.add_handler(CommandHandler("admin", admin.admin_panel))
dp.add_handler(CommandHandler("broadcast", admin.broadcast_command))
dp.add_handler(CommandHandler("upgrade", premium.upgrade_user_command))

# بدء التشغيل على Render
updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN,
                      webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")

updater.idle()