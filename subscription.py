from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import os
import logging

logger = logging.getLogger(__name__)

REQUIRED_CHANNELS = os.getenv("REQUIRED_CHANNELS", "").split(',')

def subscription_required(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        missing_channels = []

        for channel in REQUIRED_CHANNELS:
            if not channel.strip():
                continue
            try:
                member = context.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    missing_channels.append(channel.strip())
            except Exception as e:
                logger.error(f"Error checking membership for {channel}: {e}")
                missing_channels.append(channel.strip())

        if missing_channels:
            send_subscription_message(update, context, missing_channels)
            return
        else:
            return func(update, context, *args, **kwargs)

    return wrapper

def send_subscription_message(update: Update, context: CallbackContext, channels):
    keyboard = []

    for channel in channels:
        keyboard.append([InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.lstrip('@')}")])

    keyboard.append([InlineKeyboardButton("✅ تحقّق من الاشتراك", callback_data="verify_subscription")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "⚠️ لا يمكنك استخدام البوت قبل الاشتراك في القنوات التالية:\n\n"
        "انضم ثم اضغط على زر 'تحقّق من الاشتراك' بالأسفل.\n"
    )
    try:
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending subscription message: {e}")

def verify_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    missing_channels = []

    for channel in REQUIRED_CHANNELS:
        if not channel.strip():
            continue
        try:
            member = context.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                missing_channels.append(channel.strip())
        except Exception as e:
            logger.error(f"Error verifying membership for {channel}: {e}")
            missing_channels.append(channel.strip())

    if missing_channels:
        send_subscription_message(update, context, missing_channels)
    else:
        query.answer("✅ تم التحقق من اشتراكك! يمكنك الآن استخدام البوت.", show_alert=True)
        query.message.delete()
