from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import os
import logging
from templates import messages

logger = logging.getLogger(__name__)

REQUIRED_CHANNELS = os.getenv("REQUIRED_CHANNELS", "").split(',')

def normalize_channel(channel):
    return channel.strip() if channel.strip().startswith('@') else '@' + channel.strip()

def subscription_required(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        missing_channels = []

        for channel in REQUIRED_CHANNELS:
            if not channel.strip():
                continue
            normalized_channel = normalize_channel(channel)
            try:
                member = context.bot.get_chat_member(chat_id=normalized_channel, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    missing_channels.append(normalized_channel)
            except Exception as e:
                logger.error(f"Error checking membership for {channel}: {e}")
                missing_channels.append(normalized_channel)

        if missing_channels:
            send_subscription_message(update, context, missing_channels)
            return
        else:
            return func(update, context, *args, **kwargs)

    return wrapper

def send_subscription_message(update: Update, context: CallbackContext, channels):
    keyboard = []
    channels_text_list = []

    for channel in channels:
        channel_name = channel.lstrip('@')
        keyboard.append([InlineKeyboardButton(f"اشترك في @{channel_name}", url=f"https://t.me/{channel_name}")])
        channels_text_list.append(f"➡️ @{channel_name}")

    keyboard.append([InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="verify_subscription")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    channels_list = "\n".join(channels_text_list)

    text = messages.SUBSCRIPTION_REQUIRED.format(channels_list=channels_list)

    try:
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup, parse_mode="MarkdownV2")
        elif update.callback_query:
            update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Error sending subscription message: {e}")

def verify_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    missing_channels = []

    for channel in REQUIRED_CHANNELS:
        if not channel.strip():
            continue
        normalized_channel = normalize_channel(channel)
        try:
            member = context.bot.get_chat_member(chat_id=normalized_channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                missing_channels.append(normalized_channel)
        except Exception as e:
            logger.error(f"Error verifying membership for {channel}: {e}")
            missing_channels.append(normalized_channel)

    if missing_channels:
        send_subscription_message(update, context, missing_channels)
    else:
        query.answer("✅ تم التحقق من اشتراكك! يمكنك الآن استخدام البوت.", show_alert=True)
        query.message.delete()
