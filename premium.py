import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import logging
from firebase_admin import db
import math

logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self._load_config()
        self._validate_config()
        logger.info("✅ تم تهيئة مدير الاشتراك المميز بنجاح")

    def _load_config(self):
        """تحميل الإعدادات مع قيم افتراضية آمنة"""
        self.CHARS_MONTHLY = self._safe_env_to_int('PREMIUM_CHARS_MONTHLY', 50000)
        self.MAX_PER_REQUEST = self._safe_env_to_int('PREMIUM_MAX_PER_REQUEST', 10000)
        self.PRICE = os.getenv('PREMIUM_PRICE', '5 دولار')
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@premium_support')
        self.TRIAL_DAYS = self._safe_env_to_int('PREMIUM_TRIAL_DAYS', 0)
        self.TRIAL_CHARS = self._safe_env_to_int('PREMIUM_TRIAL_CHARS', 0)

    def _safe_env_to_int(self, var_name, default):
        """تحويل متغير بيئة إلى عدد صحيح بأمان"""
        try:
            return int(os.getenv(var_name, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"⚠️ قيمة غير صالحة لـ {var_name}, استخدام الافتراضي: {default}")
            return default

    def _validate_config(self):
        """التحقق من صحة الإعدادات"""
        if self.CHARS_MONTHLY <= 0:
            logger.error("❌ حد الأحرف الشهري يجب أن يكون أكبر من الصفر")
            raise ValueError("حد الأحرف الشهري غير صالح")

        if not self.PAYMENT_CHANNEL.startswith('@'):
            logger.warning("⚠️ قناة الدفع يجب أن تبدأ ب @")

    def activate_premium(self, user_id, admin_id=None, is_trial=False):
        """تفعيل الاشتراك المميز مع دعم التجربة المجانية"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            now = datetime.now()
            
            if is_trial and self.TRIAL_DAYS > 0:
                expiry_date = now + timedelta(days=self.TRIAL_DAYS)
                remaining_chars = self.TRIAL_CHARS
                plan_type = 'trial'
            else:
                expiry_date = now + timedelta(days=30)
                remaining_chars = self.CHARS_MONTHLY
                plan_type = 'premium'

            premium_data = {
                'is_premium': True,
                'plan_type': plan_type,
                'activated_on': {'.sv': 'timestamp'},
                'expires_on': expiry_date.timestamp(),
                'remaining_chars': remaining_chars,
                'total_chars': remaining_chars,
                'activated_by': 'admin' if admin_id else 'user',
                'admin_id': admin_id
            }

            # الحفاظ على بيانات الاستخدام الموجودة
            if 'usage' in user_data:
                premium_data['usage'] = user_data['usage']

            updates = {
                'premium': premium_data,
                'voice_cloned': True  # إلغاء حد الاستنساخ للمميزين
            }

            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            
            logger.info(f"✅ تم تفعيل الاشتراك المميز للمستخدم {user_id} (نوع: {plan_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل تفعيل الاشتراك المميز: {str(e)}", exc_info=True)
            return False

    def deactivate_premium(self, user_id):
        """إلغاء الاشتراك المميز مع الاحتفاظ بالسجلات"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            if not user_data.get('premium', {}).get('is_premium', False):
                return True

            updates = {
                'premium/is_premium': False,
                'premium/deactivated_on': {'.sv': 'timestamp'},
                'premium/remaining_chars': 0
            }

            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"✅ تم إلغاء الاشتراك المميز للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل إلغاء الاشتراك المميز: {str(e)}", exc_info=True)
            return False

    def check_premium_status(self, user_id):
        """التحقق من حالة الاشتراك مع التحديث التلقائي"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            premium = user_data.get('premium', {})
            
            if not premium.get('is_premium', False):
                return False
                
            # التحقق من انتهاء المدة
            expiry_timestamp = premium.get('expires_on', 0)
            if datetime.now().timestamp() > expiry_timestamp:
                self.deactivate_premium(user_id)
                return False
                
            # التحقق من استنفاذ الأحرف (للحسابات غير التجريبية)
            if (premium.get('plan_type') != 'trial' and 
                premium.get('remaining_chars', 0) <= 0):
                self.deactivate_premium(user_id)
                return False
                
            return True
        except Exception as e:
            logger.error(f"❌ فشل التحقق من حالة الاشتراك: {str(e)}")
            return False

    def get_info_message(self, user_id):
        """إنشاء رسالة معلومات ديناميكية"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            premium = user_data.get('premium', {})
            usage = user_data.get('usage', {})
            
            if self.check_premium_status(user_id):
                expiry_date = datetime.fromtimestamp(premium.get('expires_on', 0))
                remaining_days = (expiry_date - datetime.now()).days
                remaining_chars = premium.get('remaining_chars', 0)
                total_chars = premium.get('total_chars', remaining_chars)
                used_chars = total_chars - remaining_chars
                
                progress_bar = self._generate_progress_bar(used_chars, total_chars)
                
                return (
                    f"💎 *حسابك مميز* ({premium.get('plan_type', 'premium')})\n\n"
                    f"⏳ المتبقي: {remaining_days} يوم\n"
                    f"📊 الاستخدام: {used_chars:,} / {total_chars:,} حرف\n"
                    f"{progress_bar}\n\n"
                    f"🔄 تجديد تلقائي: {expiry_date.strftime('%Y-%m-%d')}"
                )
            else:
                free_limit = int(os.getenv('FREE_CHAR_LIMIT', 500))
                used_chars = usage.get('total_chars', 0)
                remaining = max(0, free_limit - used_chars)
                progress_bar = self._generate_progress_bar(used_chars, free_limit)
                
                return (
                    "💰 *الاشتراك المميز*\n\n"
                    "✨ المميزات:\n"
                    f"- {self.CHARS_MONTHLY:,} حرف شهرياً\n"
                    "- استنساخ صوت غير محدود\n"
                    "- أولوية في المعالجة\n\n"
                    f"📊 استخدامك الحالي: {used_chars:,} / {free_limit:,} حرف\n"
                    f"{progress_bar}\n\n"
                    f"💵 السعر: {self.PRICE}\n"
                    f"للاشتراك: {self.PAYMENT_CHANNEL}"
                )
        except Exception as e:
            logger.error(f"❌ فشل إنشاء رسالة المعلومات: {str(e)}")
            return "⚠️ تعذر تحميل معلومات الاشتراك"

    def _generate_progress_bar(self, used, total, length=10):
        """إنشاء شريط تقدم مرئي"""
        if total <= 0:
            return ""
            
        percentage = min(100, max(0, (used / total) * 100))
        filled = math.floor((percentage / 100) * length)
        empty = length - filled
        
        filled_emoji = '🟦'  # █
        empty_emoji = '⬜'    # ░
        
        return f"{filled_emoji * filled}{empty_emoji * empty} {percentage:.1f}%"

    def get_upgrade_keyboard(self, user_id):
        """إنشاء لوحة مفاتيح الترقية"""
        buttons = [
            [InlineKeyboardButton("💳 اشتراك شهري", callback_data=f"premium_monthly_{user_id}")],
            [InlineKeyboardButton("🆓 تجربة مجانية", callback_data=f"premium_trial_{user_id}")],
            [InlineKeyboardButton("ℹ️ المميزات", callback_data=f"premium_info_{user_id}")]
        ]
        return InlineKeyboardMarkup(buttons)

    def deduct_chars(self, user_id, chars_used):
        """خصم الأحرف المستخدمة مع التحقق من الحدود"""
        if not isinstance(chars_used, int) or chars_used <= 0:
            logger.error(f"❌ قيمة أحرف غير صالحة: {chars_used}")
            return False

        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            premium = user_data.get('premium', {})
            
            # لا تخصم للمستخدمين غير المميزين
            if not premium.get('is_premium', False):
                return True
                
            # لا تخصم للحسابات التجريبية (غير محدودة)
            if premium.get('plan_type') == 'trial':
                return True
                
            remaining = premium.get('remaining_chars', 0)
            if remaining < chars_used:
                logger.warning(f"⚠️ المستخدم {user_id} تجاوز حد الأحرف المتبقية")
                return False
                
            updates = {
                'premium/remaining_chars': db.Increment(-chars_used),
                'usage/total_chars': db.Increment(chars_used),
                'last_used': {'.sv': 'timestamp'}
            }
            
            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"✅ تم خصم {chars_used} حرف من المستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل خصم الأحرف: {str(e)}", exc_info=True)
            return False
