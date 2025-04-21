import os
from functools import wraps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from templates import messages

REQUIRED_CHANNELS = os.getenv("REQUIRED_CHANNELS", "").split(",")

def is_user_subscribed(bot, user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Error checking membership for {channel}: {e}")
            return False
    return True

def check_subscription(func):
    @wraps(func)
    def wrapper(update, context):
        user = update.effective_user
        if not is_user_subscribed(context.bot, user.id):
            send_subscription_message(update, context)
            return
        return func(update, context)
    return wrapper

def send_subscription_message(update, context):
    keyboard = []
    for channel in REQUIRED_CHANNELS:
        btn = InlineKeyboardButton(f"اشترك في {channel.strip()}", url=f"https://t.me/{channel.strip().lstrip('@')}")
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="verify_subscription")])

    channels_list = "\n".join([f"• @{channel.strip().lstrip('@')}" for channel in REQUIRED_CHANNELS])

    try:
        update.message.reply_text(
            messages.SUBSCRIPTION_REQUIRED.format(channels_list=channels_list),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error sending subscription message: {e}")

def verify_subscription(update, context):
    query = update.callback_query
    user = query.from_user
    if is_user_subscribed(context.bot, user.id):
        query.answer("تم التحقق ✅ يمكنك استخدام البوت الآن")
        query.message.delete()
    else:
        query.answer("❌ لم يتم العثور على اشتراكك، يرجى الاشتراك أولاً", show_alert=True)
