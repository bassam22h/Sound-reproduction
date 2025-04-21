import os
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """لوحة المفاتيح الرئيسية"""
    return ReplyKeyboardMarkup([
        ['🎤 استنساخ صوتي', '📝 تحويل نص إلى صوت'],
        ['ℹ️ معلومات الحساب', '🔗 قنواتنا']
    ], resize_keyboard=True)

def get_channels_keyboard():
    """لوحة مفاتيح للقنوات المطلوبة"""
    try:
        channels = [c.strip() for c in os.getenv('REQUIRED_CHANNELS', '').split(',') if c.strip()]
        keyboard = []
        
        for channel in channels:
            keyboard.append([
                InlineKeyboardButton(
                    f"اشترك في @{channel}",
                    url=f"https://t.me/{channel.lstrip('@')}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                "✅ لقد اشتركت", 
                callback_data='check_subscription'
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    except Exception as e:
        print(f"Error in get_channels_keyboard: {e}")
        return InlineKeyboardMarkup([])

def get_payment_keyboard():
    """لوحة مفاتيح للدفع"""
    try:
        payment_channel = os.getenv('PAYMENT_CHANNEL', 'payment_channel').strip('@')
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💳 ترقية إلى المدفوع", 
                    url=f"https://t.me/{payment_channel}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 تحديث الحالة", 
                    callback_data='refresh_status'
                )
            ]
        ])
    except Exception as e:
        print(f"Error in get_payment_keyboard: {e}")
        return InlineKeyboardMarkup([])
