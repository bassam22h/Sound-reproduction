from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from firebase import FirebaseDB
import os

ADMIN_ID = int(os.getenv("ADMIN_ID"))
db = FirebaseDB()

def admin_panel(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ ليس لديك صلاحية الوصول.")

    keyboard = [
        [InlineKeyboardButton("عرض الإحصاءات", callback_data="stats")],
        [InlineKeyboardButton("إرسال إشعار عام", callback_data="broadcast")],
        [InlineKeyboardButton("تفعيل اشتراك مستخدم", callback_data="upgrade")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("لوحة التحكم:", reply_markup=reply_markup)

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        return query.answer("❌ لا تملك صلاحية.", show_alert=True)

    if data == "stats":
        users = db.get_all_users()
        total = len(users)
        premium = sum(1 for u in users if u.get("premium"))
        query.message.edit_text(f"عدد المستخدمين: {total}
المدفوعين: {premium}")

    elif data == "broadcast":
        context.user_data["awaiting_broadcast"] = True
        query.message.edit_text("أرسل الآن الرسالة التي تريد نشرها لجميع المستخدمين.")

    elif data == "upgrade":
        context.user_data["awaiting_upgrade"] = True
        query.message.edit_text("أرسل الآن معرف المستخدم لتفعيله كمدفوع.")

def broadcast_command(update: Update, context: CallbackContext):
    if context.user_data.get("awaiting_broadcast"):
        context.user_data["awaiting_broadcast"] = False
        msg = update.message.text
        users = db.get_all_users()
        success = 0
        for user in users:
            try:
                context.bot.send_message(chat_id=user["id"], text=msg)
                success += 1
            except:
                continue
        update.message.reply_text(f"✅ تم إرسال الرسالة إلى {success} مستخدم.")

def upgrade_user(update: Update, context: CallbackContext):
    if context.user_data.get("awaiting_upgrade"):
        context.user_data["awaiting_upgrade"] = False
        uid = update.message.text
        if db.upgrade_user(uid):
            update.message.reply_text("✅ تم التفعيل بنجاح.")
        else:
            update.message.reply_text("❌ حدث خطأ، تأكد من المعرف.")