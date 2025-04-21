from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import logging

logger = logging.getLogger(__name__)

# ضع هنا معرفات القنوات المطلوبة للاشتراك
REQUIRED_CHANNELS = ['YourChannel1', 'YourChannel2']  # بدون @

def subscription_required(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        missing_channels = []

        for channel in REQUIRED_CHANNELS:
            try:
                member = context.bot.get_chat_member(chat_id=f"@{channel}", user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    missing_channels.append(channel)
            except Exception as e:
                logger.error(f"Error checking membership for {channel}: {e}")
                missing_channels.append(channel)

        if missing_channels:
            send_subscription_message(update, context, missing_channels)
            return  # نوقف التنفيذ هنا
        else:
            return func(update, context, *args, **kwargs)

    return wrapper

def send_subscription_message(update: Update, context: CallbackContext, channels):
    """يرسل رسالة تحقق من الاشتراك مع أزرار الانضمام."""
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(
                text=f"اشترك في قناة {channel}",
                url=f"https://t.me/{channel}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="تحقّق من الاشتراك ✅",
            callback_data="check_subscription"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "✅ للاستخدام، الرجاء الاشتراك في القنوات التالية، ثم اضغط 'تحقق من الاشتراك':"

    try:
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending subscription message: {e}")
