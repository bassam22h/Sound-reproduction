from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import logging

logger = logging.getLogger(__name__)

# هنا تضع معرفات القنوات المطلوبة مثل ['@channel1', '@channel2']
REQUIRED_CHANNELS = ['@YourChannel1', '@YourChannel2']

def subscription_required(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        missing_channels = []

        for channel in REQUIRED_CHANNELS:
            try:
                member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
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
    """يرسل رسالة تحقق من الاشتراك مع أزرار الانضمام للقنوات وزر التحقق."""
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.lstrip('@')}")])

    # نضيف زر تحقق من الاشتراك
    keyboard.append([InlineKeyboardButton("✅ تحقّق من الاشتراك", callback_data="check_subscription")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "عذراً، يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:"
    try:
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending subscription message: {e}")

def check_subscription(update: Update, context: CallbackContext):
    """دالة لفحص حالة الاشتراك عندما يضغط المستخدم على زر التحقق"""
    query = update.callback_query
    user_id = query.from_user.id
    missing_channels = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                missing_channels.append(channel)
        except Exception as e:
            logger.error(f"Error checking membership for {channel}: {e}")
            missing_channels.append(channel)

    if not missing_channels:
        query.answer(text="✅ أنت مشترك! يمكنك الآن استخدام البوت.", show_alert=True)
        query.edit_message_text(text="✅ تم التحقق من الاشتراك، يمكنك الآن استخدام البوت!")
    else:
        query.answer(text="❌ لم تكمل الاشتراك في جميع القنوات.", show_alert=True)
        send_subscription_message(update, context, missing_channels)
