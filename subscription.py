import os
from telegram import ParseMode
from templates.keyboards import get_channels_keyboard, get_payment_keyboard
from database import get_user_data

def check_subscription(handler):
    def wrapper(update, context):
        user_id = update.effective_user.id
        
        # تخطي التحقق لأمر /start
        if update.message and update.message.text == '/start':
            return handler(update, context)
        
        # التحقق من الاشتراك
        if not is_subscribed(context, user_id):
            send_subscription_message(update, context)
            return None
        
        # التحقق من المحاولات
        user_data = get_user_data(user_id)
        if user_data.get('trials', 0) <= 0:
            send_trial_expired_message(update, context)
            return None
            
        return handler(update, context)
    return wrapper

def is_subscribed(context, user_id):
    try:
        channels = [c.strip() for c in os.getenv('REQUIRED_CHANNELS', '').split(',') if c.strip()]
        for channel in channels:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

def send_subscription_message(update, context):
    channels = [c.strip() for c in os.getenv('REQUIRED_CHANNELS', '').split(',') if c.strip()]
    message = "📢 للاستمرار، يرجى الاشتراك في القنوات التالية:\n\n" + \
              "\n".join([f"🔹 @{channel}" for channel in channels]) + \
              "\n\nبعد الاشتراك، اضغط على زر التحقق"
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=get_channels_keyboard()
    )

def send_trial_expired_message(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❌ لقد استنفذت جميع محاولاتك المجانية",
        reply_markup=get_payment_keyboard()
    )
