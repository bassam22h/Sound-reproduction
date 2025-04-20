import os
import asyncio
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from database import get_user_data, update_user_data

def check_subscription(handler):
    async def wrapper(update, context: CallbackContext):
        user_id = update.effective_user.id
        
        # تخطي التحقق لأمر /start
        if update.message and update.message.text == '/start':
            return await handler(update, context)
        
        # التحقق من الاشتراك في القنوات
        if not await is_subscribed(update, context, user_id):
            await send_subscription_message(update, context)
            return
        
        # التحقق من المحاولات المتبقية
        user_data = get_user_data(user_id)
        if user_data.get('trials', 0) <= 0:
            await send_trial_expired_message(update, context)
            return
        
        # تنفيذ الوظيفة الأصلية
        return await handler(update, context)
    
    return wrapper

async def is_subscribed(update, context, user_id):
    try:
        channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
        if not channels or channels[0] == '':
            return True  # لا توجد قنوات مطلوبة
        
        for channel in channels:
            chat_member = await context.bot.get_chat_member(channel.strip(), user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

async def send_subscription_message(update, context):
    from templates.keyboards import get_channels_keyboard
    
    channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
    message = "⚠️ يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
    message += "\n".join([f"- @{channel.strip()}" for channel in channels if channel.strip()])
    message += "\n\nبعد الاشتراك، اضغط على زر '✅ لقد اشتركت' للتحقق."
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_channels_keyboard()
    )

async def send_trial_expired_message(update, context):
    from templates.keyboards import get_payment_keyboard
    
    message = "❌ لقد استنفذت جميع محاولاتك المجانية.\n"
    message += "للترقية إلى الإصدار المدفوع، يرجى استخدام الزر أدناه:"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_payment_keyboard()
    )
