import os
from telegram import Update
from telegram.ext import CallbackContext
from templates.keyboards import get_channels_keyboard

async def verify_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    channels = [c.strip() for c in os.getenv('REQUIRED_CHANNELS', '').split(',') if c.strip()]
    
    not_subscribed = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=f"@{channel}", user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Error checking channel @{channel}: {e}")
            not_subscribed.append(channel)
    
    if not_subscribed:
        await query.edit_message_text(
            text=f"❌ لم تشترك بعد في:\n" + "\n".join([f"@{c}" for c in not_subscribed]),
            reply_markup=get_channels_keyboard()
        )
    else:
        await query.edit_message_text(
            text="✅ تم التحقق بنجاح! يمكنك الآن استخدام البوت",
            reply_markup=None
        )
        # هنا يمكنك تحديث حالة المستخدم في قاعدة البيانات
        # update_user_subscription_status(user_id, True)
