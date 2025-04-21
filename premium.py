import os
from datetime import datetime, timedelta
from firebase_admin import db
from telegram import ParseMode

class PremiumManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self.MAX_PREMIUM_CHARS = 50000  # 50,000 حرف كحد أقصى للاشتراك
        self.MAX_PREMIUM_PER_REQUEST = 2000  # 2,000 حرف لكل طلب
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@payment_channel')

    def activate_premium(self, user_id, duration_days=30):
        """تفعيل الاشتراك المدفوع للمستخدم"""
        expiry_date = datetime.now() + timedelta(days=duration_days)
        
        premium_data = {
            'is_premium': True,
            'activated_on': {'.sv': 'timestamp'},
            'expires_on': expiry_date.timestamp(),
            'total_chars_used': 0,
            'remaining_chars': self.MAX_PREMIUM_CHARS
        }
        
        self.firebase.ref.child('users').child(str(user_id)).child('premium').update(premium_data)
        return True

    def check_premium_status(self, user_id):
        """التحقق من حالة الاشتراك المدفوع"""
        user_data = self.firebase.get_user_data(user_id)
        if not user_data or 'premium' not in user_data:
            return False
            
        premium = user_data['premium']
        if not premium.get('is_premium', False):
            return False
            
        expiry_date = datetime.fromtimestamp(premium['expires_on'])
        if datetime.now() > expiry_date:
            self.deactivate_premium(user_id)
            return False
            
        return True

    def deactivate_premium(self, user_id):
        """إلغاء تفعيل الاشتراك المدفوع"""
        self.firebase.ref.child('users').child(str(user_id)).child('premium').update({
            'is_premium': False,
            'deactivated_on': {'.sv': 'timestamp'}
        })
        return True

    def get_premium_info(self, user_id):
        """الحصول على معلومات الاشتراك المدفوع"""
        if not self.check_premium_status(user_id):
            return None
            
        user_data = self.firebase.get_user_data(user_id)
        premium = user_data['premium']
        
        return {
            'activated_on': datetime.fromtimestamp(premium.get('activated_on', 0)),
            'expires_on': datetime.fromtimestamp(premium['expires_on']),
            'remaining_days': (datetime.fromtimestamp(premium['expires_on']) - datetime.now()).days,
            'remaining_chars': premium.get('remaining_chars', 0),
            'total_chars_used': premium.get('total_chars_used', 0)
        }

    def record_pre
