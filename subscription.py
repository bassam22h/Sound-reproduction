import os
from telegram import ParseMode
from templates.keyboards import get_channels_keyboard, get_payment_keyboard
from database import get_user_data, update_user_data

def check_subscription(handler):
    def wrapper(update, context):
        user_id = update.effective_user.id
        
        # تخطي التحقق للأوامر والاستثناءات
        if update.message and update.message.text and update.message.text.startswith('/'):
            return handler(update, context)
        
        # التحقق من الاشتراك
        subscribed, missing_channels = is_subscribed(context, user_id)
        if not subscribed:
            send_subscription_message(update, context, missing_channels)
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
        missing_channels = []
        
        for channel in channels:
            try:
                member = context.bot.get_chat_member(chat_id=f"@{channel}", user_id=user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    missing_channels.append(channel)
            except Exception as e:
                print(f"Error checking channel @{channel}: {e}")
                missing_channels.append(channel)
        
        return (len(missing_channels) == 0, missing_channels)
    except Exception as e:
        print(f"Subscription check error: {e}")
        return (False, [])

def send_subscription_message(update, context, missing_channels):
    message = "📢 للاستمرار، يرجى الاشتراك في القنوات التالية:\n\n" + \
              "\n".join([f"🔹 @{channel}" for channel in missing_channels]) + \
              "\n\nبعد الاشتراك، اضغط على زر التحقق في الأسفل"
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_channels_keyboard()
    )

def send_trial_expired_message(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""❌ لقد استنفذت جميع محاولاتك المجانية
للترقية إلى الإصدار المدفوع والحصول على مميزات إضافية:""",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_payment_keyboard()
    )

# دالة مساعدة لتحديث حالة الاشتراك
def update_subscription_status(user_id, status):
    update_user_data(user_id, {'is_subscribed': status})
