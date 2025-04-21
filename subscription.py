import os
from telegram import ParseMode
from telegram.ext import CallbackContext
from database import get_user_data, update_user_data

def check_subscription(handler):
    def wrapper(update, context: CallbackContext):
        user_id = update.effective_user.id
        
        # تخطي التحقق لأمر /start
        if update.message and update.message.text == '/start':
            return handler(update, context)
        
        # التحقق من الاشتراك في القنوات
        if not is_subscribed(context, user_id):
            send_subscription_message(update, context)
            return None
        
        # التحقق من المحاولات المتبقية
        user_data = get_user_data(user_id)
        if user_data.get('trials', 0) <= 0:
            send_trial_expired_message(update, context)
            return None
        
        return handler(update, context)
    
    return wrapper

def is_subscribed(context, user_id):
    try:
        channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
        if not channels or channels[0] == '':
            return True
        
        for channel in channels:
            channel = channel.strip()
            if channel:
                member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
        return True
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

def send_subscription_message(update, context):
    from templates.keyboards import get_channels_keyboard
    
    channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
    message = "⚠️ يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
    message += "\n".join([f"- @{channel.strip()}" for channel in channels if channel.strip()])
    message += "\n\nبعد الاشتراك، اضغط على زر '✅ لقد اشتركت' للتحقق."
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_channels_keyboard()
    )

def send_trial_expired_message(update, context):
    from templates.keyboards import get_payment_keyboard
    
    message = "❌ لقد استنفذت جميع محاولاتك المجانية.\n"
    message += "للترقية إلى الإصدار المدفوع، يرجى استخدام الزر أدناه:"
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_payment_keyboard()
    )
