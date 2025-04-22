import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import logging
from firebase_admin import db

logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self._validate_env_vars()
        logger.info("تم تهيئة مدير الاشتراك المميز")

    def _validate_env_vars(self):
        """التحقق من وجود المتغيرات المطلوبة"""
        required_vars = [
            'PREMIUM_CHARS_MONTHLY',
            'PREMIUM_MAX_PER_REQUEST',
            'PREMIUM_PRICE',
            'PAYMENT_CHANNEL'
        ]
        for var in required_vars:
            if not os.getenv(var):
                logger.warning(f"⚠️ متغير البيئة {var} غير محدد!")

        self.PREMIUM_CHARS_MONTHLY = int(os.getenv('PREMIUM_CHARS_MONTHLY', 50000))
        self.PREMIUM_MAX_PER_REQUEST = int(os.getenv('PREMIUM_MAX_PER_REQUEST', 10000))
        self.PREMIUM_PRICE = os.getenv('PREMIUM_PRICE', '5 دولار')
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@premium_support')

    def activate_premium(self, user_id, admin_id=None):
        """تفعيل الاشتراك مع تسجيل سبب التفعيل"""
        expiry_date = datetime.now() + timedelta(days=30)
        
        premium_data = {
            'is_premium': True,
            'activated_on': {'.sv': 'timestamp'},
            'expires_on': expiry_date.timestamp(),
            'remaining_chars': self.PREMIUM_CHARS_MONTHLY,
            'activated_by': 'admin' if admin_id else 'user',
            'admin_id': admin_id
        }
        
        try:
            self.firebase.ref.child('users').child(str(user_id)).child('premium').update(premium_data)
            logger.info(f"تم تفعيل الاشتراك للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في التفعيل: {str(e)}")
            return False

    def check_premium_status(self, user_id):
        """التحقق من الحالة مع تجديد تلقائي إذا انتهت المدة"""
        user_data = self.firebase.get_user_data(user_id) or {}
        premium = user_data.get('premium', {})
        
        if not premium.get('is_premium', False):
            return False
            
        if datetime.now().timestamp() > premium.get('expires_on', 0):
            self.deactivate_premium(user_id)
            return False
            
        return True

    def deactivate_premium(self, user_id):
        """إلغاء الاشتراك مع الاحتفاظ بالسجلات"""
        try:
            updates = {
                'is_premium': False,
                'deactivated_on': {'.sv': 'timestamp'},
                'remaining_chars': 0
            }
            self.firebase.ref.child('users').child(str(user_id)).child('premium').update(updates)
            return True
        except Exception as e:
            logger.error(f"خطأ في الإلغاء: {str(e)}")
            return False

    def get_info_message(self, user_id):
        """رسالة ديناميكية بناءً على حالة المستخدم"""
        if self.check_premium_status(user_id):
            user_data = self.firebase.get_user_data(user_id) or {}
            premium_data = user_data.get('premium', {})
            expiry_date = datetime.fromtimestamp(premium_data.get('expires_on', 0)).strftime('%Y-%m-%d')
            return (
                f"💎 *حسابك مميز حتى {expiry_date}*\n\n"
                f"📊 الأحرف المتبقية: {premium_data.get('remaining_chars', 0):,}"
            )
        else:
            return (
                "💰 *الاشتراك المميز*\n\n"
                "✨ المميزات:\n"
                f"- {self.PREMIUM_CHARS_MONTHLY:,} حرف شهرياً\n"
                "- استنساخ صوت غير محدود\n\n"
                f"💵 السعر: {self.PREMIUM_PRICE}\n"
                f"للاشتراك: {self.PAYMENT_CHANNEL}"
            )
