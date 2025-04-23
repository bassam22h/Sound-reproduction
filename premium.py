import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import logging
from firebase_admin import db
import math

logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, firebase):
        """Initialize Premium Manager with Firebase connection"""
        self.firebase = firebase
        self._load_config()
        self._validate_config()  # تمت إضافة هذه الدالة
        logger.info("✅ تم تهيئة مدير الاشتراك المميز بنجاح")

    def _load_config(self):
        """تحميل إعدادات الاشتراك من متغيرات البيئة"""
        self.CHARS_MONTHLY = self._safe_get_env('PREMIUM_CHARS_MONTHLY', 50000, int)
        self.MAX_PER_REQUEST = self._safe_get_env('PREMIUM_MAX_PER_REQUEST', 10000, int)
        self.PRICE = os.getenv('PREMIUM_PRICE', '5 دولار')
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@premium_support').strip()
        
        if not self.PAYMENT_CHANNEL.startswith('@'):
            self.PAYMENT_CHANNEL = '@' + self.PAYMENT_CHANNEL
            
        self.TRIAL_DAYS = self._safe_get_env('PREMIUM_TRIAL_DAYS', 0, int)
        if self.TRIAL_DAYS < 0:
            logger.warning("أيام التجربة لا يمكن أن تكون سالبة، تم التعيين إلى 0")
            self.TRIAL_DAYS = 0
            
        self.TRIAL_CHARS = self._safe_get_env('PREMIUM_TRIAL_CHARS', 0, int)
        if self.TRIAL_CHARS < 0:
            logger.warning("أحرف التجربة لا يمكن أن تكون سالبة، تم التعيين إلى 0")
            self.TRIAL_CHARS = 0

    def _validate_config(self):
        """Validates that all premium configuration is properly loaded
        
        Raises:
            ValueError: If any required configuration is missing or invalid
        """
        required_configs = {
            'PREMIUM_CHARS_MONTHLY': self.CHARS_MONTHLY,
            'PREMIUM_MAX_PER_REQUEST': self.MAX_PER_REQUEST,
            'PREMIUM_PRICE': self.PRICE,
            'PAYMENT_CHANNEL': self.PAYMENT_CHANNEL
        }
        
        for name, value in required_configs.items():
            if not value:
                raise ValueError(f"إعداد {name} مطلوب ولا يمكن أن يكون فارغًا")
                
        if not isinstance(self.CHARS_MONTHLY, int) or self.CHARS_MONTHLY <= 0:
            raise ValueError("PREMIUM_CHARS_MONTHLY يجب أن يكون عدد صحيح موجب")
            
        if not isinstance(self.MAX_PER_REQUEST, int) or self.MAX_PER_REQUEST <= 0:
            raise ValueError("PREMIUM_MAX_PER_REQUEST يجب أن يكون عدد صحيح موجب")

    def _safe_get_env(self, var_name, default, var_type):
        """قراءة متغير بيئة مع التحقق من النوع"""
        try:
            value = os.getenv(var_name, str(default))
            return var_type(value) if value is not None else default
        except (ValueError, TypeError) as e:
            logger.warning(f"قيمة غير صالحة لـ {var_name} ({value}), استخدام الافتراضي: {default}. الخطأ: {str(e)}")
            return default

    def activate_premium(self, user_id, admin_id=None, is_trial=False):
        """تفعيل اشتراك مميز أو تجريبي"""
        try:
            now = datetime.now()
            if is_trial and self.TRIAL_DAYS > 0:
                expiry_date = now + timedelta(days=self.TRIAL_DAYS)
                remaining_chars = self.TRIAL_CHARS
                plan_type = 'trial'
            else:
                expiry_date = now + timedelta(days=30)
                remaining_chars = self.CHARS_MONTHLY
                plan_type = 'premium'

            updates = {
                'premium': {
                    'is_premium': True,
                    'plan_type': plan_type,
                    'activated_on': {'.sv': 'timestamp'},
                    'expires_on': expiry_date.timestamp(),
                    'remaining_chars': remaining_chars,
                    'total_chars': remaining_chars,
                    'activated_by': 'admin' if admin_id else 'user',
                    'admin_id': admin_id
                },
                'voice_cloned': True
            }

            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"تم تفعيل الاشتراك للمستخدم {user_id} (نوع: {plan_type})")
            return True
        except Exception as e:
            logger.error(f"فشل تفعيل الاشتراك: {str(e)}", exc_info=True)
            return False

    def check_premium_status(self, user_id):
        """التحقق من حالة الاشتراك"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            premium = user_data.get('premium', {})
            
            if not premium.get('is_premium'):
                return False
                
            if datetime.now().timestamp() > premium.get('expires_on', 0):
                return self.deactivate_premium(user_id)
                
            if (premium.get('plan_type') != 'trial' and 
                premium.get('remaining_chars', 0) <= 0):
                return self.deactivate_premium(user_id)
                
            return True
        except Exception as e:
            logger.error(f"خطأ في التحقق من الحالة: {str(e)}", exc_info=True)
            return False

    def get_info_message(self, user_id):
        """إنشاء رسالة معلومات الاشتراك"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            
            if self.check_premium_status(user_id):
                premium = user_data.get('premium', {})
                expiry_date = datetime.fromtimestamp(premium.get('expires_on', 0))
                used_chars = premium.get('total_chars', 0) - premium.get('remaining_chars', 0)
                
                return (
                    "<b>💎 حسابك مميز</b>\n\n"
                    f"⏳ المتبقي: <code>{max(0, (expiry_date - datetime.now()).days)} يوم</code>\n"
                    f"📊 الاستخدام: <code>{used_chars:,}</code> / <code>{premium.get('total_chars', 0):,} حرف</code>\n"
                    f"{self._generate_progress_bar(used_chars, premium.get('total_chars', 0))}\n\n"
                    f"🔄 تجديد تلقائي: <code>{expiry_date.strftime('%Y-%m-%d')}</code>"
                )
            else:
                used_chars = user_data.get('usage', {}).get('total_chars', 0)
                free_limit = int(os.getenv('FREE_CHAR_LIMIT', 500))
                
                return (
                    "<b>💰 الاشتراك المميز</b>\n\n"
                    "<b>✨ المميزات:</b>\n"
                    f"- <code>{self.CHARS_MONTHLY:,} حرف شهرياً</code>\n"
                    "- استنساخ صوت غير محدود\n"
                    "- أولوية في المعالجة\n\n"
                    f"📊 استخدامك الحالي: <code>{used_chars:,}</code>/<code>{free_limit:,} حرف</code>\n"
                    f"{self._generate_progress_bar(used_chars, free_limit)}\n\n"
                    f"💵 السعر: <code>{self.PRICE}</code>\n"
                    f"للاشتراك: {self.PAYMENT_CHANNEL}"
                )
        except Exception as e:
            logger.error(f"فشل إنشاء رسالة المعلومات: {str(e)}", exc_info=True)
            return "⚠️ تعذر تحميل معلومات الاشتراك"

    def _generate_progress_bar(self, used, total, length=10):
        """إنشاء شريط تقدم مرئي"""
        if total <= 0:
            return ""
            
        percentage = min(100, max(0, (used / total) * 100))
        filled = math.floor((percentage / 100) * length)
        return f"{'🟦' * filled}{'⬜' * (length - filled)} {percentage:.1f}%"

    def get_upgrade_keyboard(self, user_id):
        """لوحة ترقية المستخدم"""
        buttons = [
            [InlineKeyboardButton("💳 اشتراك شهري", callback_data=f"premium_monthly_{user_id}")],
            [InlineKeyboardButton("🆓 تجربة مجانية", callback_data=f"premium_trial_{user_id}")] if self.TRIAL_DAYS > 0 else None,
            [InlineKeyboardButton("ℹ️ المميزات", callback_data=f"premium_info_{user_id}")]
        ]
        # إزالة أي أزرار فارغة (None)
        buttons = [btn for btn in buttons if btn is not None]
        return InlineKeyboardMarkup(buttons)

    def deduct_chars(self, user_id, chars_used):
        """خصم الأحرف المستخدمة"""
        if not isinstance(chars_used, int) or chars_used <= 0:
            logger.error(f"قيمة أحرف غير صالحة: {chars_used}")
            return False

        try:
            updates = {
                'usage/total_chars': db.Increment(chars_used),
                'last_used': {'.sv': 'timestamp'}
            }

            user_data = self.firebase.get_user_data(user_id) or {}
            if user_data.get('premium', {}).get('is_premium') and user_data.get('premium', {}).get('plan_type') != 'trial':
                updates['premium/remaining_chars'] = db.Increment(-chars_used)

            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"فشل خصم الأحرف: {str(e)}", exc_info=True)
            return False

    def deactivate_premium(self, user_id):
        """إلغاء الاشتراك المميز"""
        try:
            updates = {
                'premium/is_premium': False,
                'premium/deactivated_on': {'.sv': 'timestamp'},
                'premium/remaining_chars': 0
            }
            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"فشل إلغاء الاشتراك: {str(e)}", exc_info=True)
            return False
