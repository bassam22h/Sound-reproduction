from telegram import Update
from telegram.ext import CallbackContext
from firebase import FirebaseDB
import os

ADMIN_ID = int(os.getenv("ADMIN_ID"))
db = FirebaseDB()

def upgrade_user_command(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ لا تملك صلاحية.")

    try:
        user_id = int(context.args[0])
        success = db.upgrade_user(user_id)
        if success:
            update.message.reply_text("✅ تم ترقية المستخدم.")
        else:
            update.message.reply_text("❌ المستخدم غير موجود.")
    except:
        update.message.reply_text("❌ استخدم الأمر بهذا الشكل:
/upgrade 123456789")