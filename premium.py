import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import logging
from firebase_admin import db

logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self.PREMIUM_CHARS_MONTHLY = int(os.getenv('PREMIUM_CHARS_MONTHLY', 50000))
        self.PREMIUM_MAX_PER_REQUEST = int(os.getenv('PREMIUM_MAX_PER_REQUEST', 10000))
        self.PREMIUM_PRICE = os.getenv('PREMIUM_PRICE', '2 دولار')
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@payment_channel')
        logger.info("تم تهيئة مدير الاشتراك المميز")

    def activate_premium(self, user_id, admin_id=None):
        """تفعيل الاشتراك لمدة 30 يوم"""
        expiry_date = datetime.now() + timedelta(days=30)
        
        premium_data = {
            'is_premium': True,
            'activated_on': {'.sv': 'timestamp'},
            'expires_on': expiry_date.timestamp(),
            'remaining_chars': self.PREMIUM_CHARS_MONTHLY,
            'price': self.PREMIUM_PRICE,
            'activated_by': admin_id
        }
        
        try:
            self.firebase.ref.child('users').child(str(user_id)).child('premium').update(premium_data)
            logger.info(f"تم تفعيل الاشتراك للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في التفعيل: {str(e)}")
            return False

    def check_premium_status(self, user_id):
        """التحقق من حالة الاشتراك"""
        user_data = self.firebase.get_user_data(user_id) or {}
        premium = user_data.get('premium', {})
        
        if not premium.get('is_premium', False):
            return False
            
        if datetime.now().timestamp() > premium.get('expires_on', 0):
            self.deactivate_premium(user_id)
            return False
            
        return True

    def deactivate_premium(self, user_id):
        """إلغاء الاشتراك"""
        try:
            self.firebase.ref.child('users').child(str(user_id)).child('premium').update({
                'is_premium': False,
                'deactivated_on': {'.sv': 'timestamp'}
            })
            return True
        except Exception as e:
            logger.error(f"خطأ في الإلغاء: {str(e)}")
            return False

    def get_info_message(self, user_id):
        """رسالة معلومات الاشتراك"""
        if self.check_premium_status(user_id):
            user_data = self.firebase.get_user_data(user_id)
            remaining = user_data['premium']['remaining_chars']
            expiry = datetime.fromtimestamp(user_data['premium']['expires_on'])
            
            return (
                f"💎 *حسابك مميز*\n\n"
                f"⏳ المتبقي: {remaining:,} حرف\n"
                f"📅 ينتهي في: {expiry.strftime('%Y-%m-%d')}\n"
                f"💵 السعر: {self.PREMIUM_PRICE}"
            )
        return (
            f"💰 *ترقية للاشتراك المميز*\n\n"
            f"✨ المميزات:\n"
            f"- {self.PREMIUM_CHARS_MONTHLY:,} حرف شهرياً\n"
            f"- استنساخ صوت غير محدود\n"
            f"- حد {self.PREMIUM_MAX_PER_REQUEST:,} حرف/طلب\n\n"
            f"للاشتراك راسل: {self.PAYMENT_CHANNEL}"
            )
