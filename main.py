import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from handlers import start, audio, text, error
from subscription import check_subscription, verify_subscription

def main():
    # تحميل متغيرات البيئة
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN في متغيرات البيئة")

    # تهيئة البوت
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # معالج تحقق الاشتراك عند الضغط على زر "تحقق"
    dp.add_handler(CallbackQueryHandler(
        verify_subscription,
        pattern="^verify_subscription$"
    ))

    # تسجيل معالجات الأوامر مع تطبيق التحقق من الاشتراك
    dp.add_handler(CommandHandler(
        "start",
        start.start
    ))

    # معالجات الرسائل الصوتية والمقاطع الصوتية مع التحقق من الاشتراك
    dp.add_handler(MessageHandler(
        Filters.voice | Filters.audio,
        check_subscription(audio.handle_audio)
    ))

    # معالجات النصوص (غير الأوامر) مع التحقق من الاشتراك
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        check_subscription(text.handle_text)
    ))

    # معالج الأخطاء
    dp.add_error_handler(error.error_handler)

    # إعدادات التشغيل
    PORT = int(os.getenv('PORT', 10000))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')

    if WEBHOOK_URL:
        # تشغيل الويب هوك (موصى به على Render)
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True
        )
        print(f"✅ البوت يعمل على الويب هوك (البورت: {PORT})")
    else:
        # وضع البولينج (للتجارب المحلية فقط)
        updater.start_polling()
        print("✅ البوت يعمل في وضع البولينج (للتطوير فقط)")

    updater.idle()

if __name__ == '__main__':
    main()
