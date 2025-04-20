from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """لوحة المفاتيح الرئيسية"""
    return ReplyKeyboardMarkup([
        ['🎤 استنساخ صوتي', '📝 تحويل نص إلى صوت'],
        ['ℹ️ معلومات الحساب', '🔗 قنواتنا']
    ], resize_keyboard=True)

def get_channels_keyboard():
    """لوحة مفاتيح للقنوات المطلوبة"""
    channels = os.getenv('REQUIRED_CHANNELS', '').split(',')
    keyboard = []
    for channel in channels:
        if channel.strip():
            keyboard.append([InlineKeyboardButton(
                f"القناة {channel.strip()}",
                url=f"https://t.me/{channel.strip()}"
            )])
    
    keyboard.append([InlineKeyboardButton("✅ لقد اشتركت", callback_data='check_subscription')])
    return InlineKeyboardMarkup(keyboard)

def get_payment_keyboard():
    """لوحة مفاتيح للدفع"""
    payment_channel = os.getenv('PAYMENT_CHANNEL', 'payment_channel')
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 ترقية إلى المدفوع", url=f"https://t.me/{payment_channel}")],
        [InlineKeyboardButton("🔄 تحديث الحالة", callback_data='refresh_status')]
    ])
