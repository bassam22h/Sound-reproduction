import os
from datetime import datetime, timedelta
from firebase_admin import db
from telegram import ParseMode
import logging

logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self._load_environment_vars()
        
    def _load_environment_vars(self):
        """تحميل جميع متغيرات البيئة من Render"""
        try:
            self.MAX_PREMIUM_CHARS = int(os.getenv('MAX_PREMIUM_CHARS', 50000))
            self.MAX_PREMIUM_PER_REQUEST = int(os.getenv('MAX_PREMIUM_PER_REQUEST', 2000))
            self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@payment_channel')
            self.MAX_VOICE_CLONES = int(os.getenv('MAX_VOICE_CLONES', 10))
            self.DEFAULT_PREMIUM_DAYS = int(os.getenv('DEFAULT_PREMIUM_DAYS', 30))
            self.PREMIUM_PRICE = os.getenv('PREMIUM_PRICE', '10 USD')
            
            logger.info("تم تحميل متغيرات البيئة للاشتراك المدفوع بنجاح")
        except Exception as e:
            logger.error(f"خطأ في تحميل متغيرات البيئة: {str(e)}")
            raise

    def activate_premium(self, user_id, duration_days=None, admin_id=None):
        """تفعيل الاشتراك المدفوع مع تسجيل المشرف المسؤول"""
        if duration_days is None:
            duration_days = self.DEFAULT_PREMIUM_DAYS
            
        expiry_date = datetime.now() + timedelta(days=duration_days)
        
        premium_data = {
            'is_premium': True,
            'activated_on': {'.sv': 'timestamp'},
            'expires_on': expiry_date.timestamp(),
            'total_chars_used': 0,
            'remaining_chars': self.MAX_PREMIUM_CHARS,
            'voice_clones_used': 0,
            'activated_by': admin_id,
            'duration_days': duration_days,
            'price': self.PREMIUM_PRICE
        }
        
        try:
            self.firebase.ref.child('users').child(str(user_id)).child('premium').update(premium_data)
            logger.info(f"تم تفعيل الاشتراك المدفوع للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في تفعيل الاشتراك المدفوع: {str(e)}")
            return False

    def check_premium_status(self, user_id):
        """التحقق من حالة الاشتراك مع تجديد تلقائي إذا انتهت المدة"""
        try:
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
        except Exception as e:
            logger.error(f"خطأ في التحقق من حالة الاشتراك: {str(e)}")
            return False

    def deactivate_premium(self, user_id):
        """إلغاء تفعيل الاشتراك مع الاحتفاظ بالسجل التاريخي"""
        try:
            user_ref = self.firebase.ref.child('users').child(str(user_id))
            
            # نقل البيانات إلى السجل التاريخي
            premium_data = user_ref.child('premium').get()
            if premium_data:
                user_ref.child('premium_history').push().set({
                    **premium_data,
                    'deactivated_on': {'.sv': 'timestamp'}
                })
            
            # إلغاء التفعيل
            user_ref.child('premium').update({
                'is_premium': False,
                'deactivated_on': {'.sv': 'timestamp'}
            })
            
            logger.info(f"تم إلغاء اشتراك المستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إلغاء الاشتراك: {str(e)}")
            return False

    def can_change_voice(self, user_id):
        """التحقق من إمكانية تغيير الصوت للمستخدم المميز"""
        if not self.check_premium_status(user_id):
            return False
            
        try:
            user_data = self.firebase.get_user_data(user_id)
            premium = user_data.get('premium', {})
            return premium.get('voice_clones_used', 0) < self.MAX_VOICE_CLONES
        except Exception as e:
            logger.error(f"خطأ في التحقق من تغيير الصوت: {str(e)}")
            return False

    def record_voice_change(self, user_id):
        """تسجيل تغيير الصوت مع التحقق من الحد المسموح"""
        if not self.check_premium_status(user_id):
            return False
            
        try:
            user_ref = self.firebase.ref.child('users').child(str(user_id)).child('premium')
            
            def update_count(current):
                if current is None:
                    return None
                    
                new_count = current.get('voice_clones_used', 0) + 1
                if new_count > self.MAX_VOICE_CLONES:
                    return None
                    
                current['voice_clones_used'] = new_count
                return current
                
            result = user_ref.transaction(update_count)
            if result:
                logger.info(f"تم تسجيل تغيير الصوت للمستخدم {user_id}")
            return result is not None
        except Exception as e:
            logger.error(f"خطأ في تسجيل تغيير الصوت: {str(e)}")
            return False

    def record_text_usage(self, user_id, chars_used):
        """تسجيل استخدام الأحرف للاشتراك المدفوع"""
        if not self.check_premium_status(user_id):
            return False
            
        try:
            user_ref = self.firebase.ref.child('users').child(str(user_id)).child('premium')
            
            def update_usage(current):
                if current is None:
                    return None
                    
                new_remaining = current['remaining_chars'] - chars_used
                if new_remaining < 0:
                    return None
                    
                return {
                    'remaining_chars': new_remaining,
                    'total_chars_used': current['total_chars_used'] + chars_used
                }
                
            result = user_ref.transaction(update_usage)
            return result is not None
        except Exception as e:
            logger.error(f"خطأ في تسجيل استخدام الأحرف: {str(e)}")
            return False

    def get_premium_info(self, user_id):
        """الحصول على معلومات الاشتراك المدفوع"""
        if not self.check_premium_status(user_id):
            return None
            
        try:
            user_data = self.firebase.get_user_data(user_id)
            premium = user_data['premium']
            
            return {
                'activated_on': datetime.fromtimestamp(premium.get('activated_on', 0)),
                'expires_on': datetime.fromtimestamp(premium['expires_on']),
                'remaining_days': (datetime.fromtimestamp(premium['expires_on']) - datetime.now()).days,
                'remaining_chars': premium.get('remaining_chars', 0),
                'total_chars_used': premium.get('total_chars_used', 0),
                'voice_clones_used': premium.get('voice_clones_used', 0),
                'max_voice_clones': self.MAX_VOICE_CLONES,
                'price': premium.get('price', self.PREMIUM_PRICE)
            }
        except Exception as e:
            logger.error(f"خطأ في جلب معلومات الاشتراك: {str(e)}")
            return None

    def get_payment_info_message(self, user_id):
        """إنشاء رسالة معلومات الدفع مع التفاصيل الكاملة"""
        premium_info = self.get_premium_info(user_id)
        
        if premium_info:
            message = f"""
            💎 *حسابك مفعل حاليًا كاشتراك مدفوع*

            ⏳ المتبقي من الاشتراك: {premium_info['remaining_days']} يوم
            📝 الأحرف المتبقية: {premium_info['remaining_chars']:,} / {self.MAX_PREMIUM_CHARS:,}
            🎤 تغييرات الصوت المستخدمة: {premium_info['voice_clones_used']} / {self.MAX_VOICE_CLONES}
            💰 سعر الاشتراك: {premium_info['price']}
            📅 تاريخ الانتهاء: {premium_info['expires_on'].strftime('%Y-%m-%d')}

            للتمديد، راسل: {self.PAYMENT_CHANNEL}
            """
        else:
            message = f"""
            💰 *ترقية إلى الإصدار المدفوع*

            ✨ *الميزات:*
            - {self.MAX_PREMIUM_CHARS:,} حرف شهريًا
            - {self.MAX_PREMIUM_PER_REQUEST:,} حرف كحد أقصى لكل طلب
            - تغيير الصوت حتى {self.MAX_VOICE_CLONES} مرات
            - أولوية في المعالجة

            💵 *السعر:* {self.PREMIUM_PRICE}
            📌 للاشتراك، راسل: {self.PAYMENT_CHANNEL}
            """
        
        return message.strip()
