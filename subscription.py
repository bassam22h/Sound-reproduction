import os
import logging
from telegram import ParseMode
from telegram.error import TelegramError, BadRequest
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self._validate_environment()
        logger.info("✅ تم تهيئة مدير الاشتراكات بنجاح")

    def _validate_environment(self):
        """التحقق من صحة متغيرات البيئة"""
        self.FREE_CHAR_LIMIT = self._safe_get_env('FREE_CHAR_LIMIT', 500, int)
        self.MAX_VOICE_CLONES = self._safe_get_env('MAX_VOICE_CLONES', 1, int)
        self.REQUIRED_CHANNELS = self._parse_channels()
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@premium_support')
        
        if not self.PAYMENT_CHANNEL.startswith('@'):
            logger.warning("⚠️ قناة الدفع يجب أن تبدأ ب @")

    def _safe_get_env(self, var_name, default, var_type):
        """الحصول على متغير بيئة مع التحقق من النوع"""
        try:
            value = os.getenv(var_name, str(default))
            return var_type(value)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ قيمة غير صالحة لـ {var_name}, استخدام القيمة الافتراضية {default}")
            return default

    def _parse_channels(self):
        """تحليل قائمة القنوات المطلوبة"""
        channels = []
        raw_channels = os.getenv('REQUIRED_CHANNELS', '')
        
        for channel in raw_channels.split(','):
            channel = channel.strip()
            if channel:
                if not channel.startswith('@'):
                    channel = f'@{channel}'
                channels.append(channel.lower())
        
        logger.info(f"📢 القنوات المطلوبة: {channels}")
        return channels

    def check_all_limits(self, user_id, context, text_length=0):
        """فحص جميع القيود مع تحسين الأداء"""
        checks = [
            self.check_required_channels(user_id, context),
            self.check_char_limit(user_id, context, text_length),
            self.check_voice_clone_limit(user_id, context)
        ]
        return all(checks)

    def check_voice_clone_limit(self, user_id, context=None, ignore_limit=False):
        """فحص حد استنساخ الصوت مع تحسينات الرسائل"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        # التحقق من حالة الاشتراك المميز أولاً
        if user_data.get('premium', {}).get('is_premium', False):
            return True
        
        # التحقق من حد الاستنساخ
        if user_data.get('voice_cloned', False) and not ignore_limit:
            alert_msg = (
                "⚠️ *لقد وصلت إلى حد استنساخ الصوت*\n\n"
                "يمكنك استنساخ الصوت مرة واحدة فقط في النسخة المجانية.\n"
                f"للترقية إلى الإصدار المدفوع: {self.PAYMENT_CHANNEL}"
            )
            
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
            except BadRequest as e:
                logger.error(f"❌ فشل إرسال تحذير حد الصوت: {str(e)}")
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع في إرسال تحذير الصوت: {str(e)}")
            
            return False
        return True

    def check_required_channels(self, user_id, context=None):
        """فحص القنوات المطلوبة مع تحسينات الأداء"""
        if not self.REQUIRED_CHANNELS:
            return True

        missing_channels = []
        
        for channel in self.REQUIRED_CHANNELS:
            try:
                if context:
                    member = context.bot.get_chat_member(channel, user_id)
                    if member.status in ['left', 'kicked']:
                        missing_channels.append(channel)
            except TelegramError as e:
                logger.error(f"❌ خطأ في التحقق من القناة {channel}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع في التحقق من القنوات: {str(e)}")
                continue

        if missing_channels:
            channels_list = "\n".join([f"• {c}" for c in missing_channels])
            alert_msg = (
                "📢 *يجب الانضمام إلى القنوات التالية أولاً*\n\n"
                f"{channels_list}\n\n"
                "بعد الانضمام، اضغط /start مرة أخرى"
            )
            
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"❌ فشل إرسال تحذير القنوات: {str(e)}")
            
            return False
        return True

    def check_char_limit(self, user_id, context=None, text_length=0):
        """فحص حد الأحرف مع تحسينات الرسائل"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        # تخطي الحد للمستخدمين المميزين
        if user_data.get('premium', {}).get('is_premium', False):
            return True

        total_used = user_data.get('usage', {}).get('total_chars', 0)
        remaining = self.FREE_CHAR_LIMIT - total_used

        if remaining <= 0:
            alert_msg = (
                "⚠️ *لقد وصلت إلى الحد الأقصى للأحرف*\n\n"
                f"الحد المجاني: {self.FREE_CHAR_LIMIT} حرف\n"
                f"للترقية إلى الإصدار المدفوع: {self.PAYMENT_CHANNEL}"
            )
            
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
            except BadRequest as e:
                logger.error(f"❌ فشل إرسال تحذير حد الأحرف: {str(e)}")
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع في إرسال تحذير الأحرف: {str(e)}")
            
            return False

        # تحذير عندما يتبقى 20% فقط من الحد
        warning_threshold = self.FREE_CHAR_LIMIT * 0.2
        if remaining <= warning_threshold and remaining > 0:
            alert_msg = (
                "🔔 *تنبيه: الأحرف المتبقية قليلة*\n\n"
                f"الأحرف المتبقية: {remaining}\n"
                f"الحد المجاني: {self.FREE_CHAR_LIMIT} حرف\n"
                f"للترقية إلى الإصدار المدفوع: {self.PAYMENT_CHANNEL}"
            )
            
            try:
                if context and total_used > 0:  # لا ترسل للمستخدمين الجدد
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"❌ فشل إرسال تنبيه الأحرف المتبقية: {str(e)}")

        return True

    def get_usage_stats(self, user_id):
        """الحصول على إحصائيات الاستخدام مع معالجة الأخطاء"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            
            if user_data.get('premium', {}).get('is_premium', False):
                total = user_data['premium'].get('remaining_chars', 0)
                used = user_data['usage'].get('total_chars', 0)
                return {
                    'is_premium': True,
                    'total': total + used,
                    'used': used,
                    'remaining': total,
                    'percentage': (used / (total + used)) * 100 if (total + used) > 0 else 0
                }
            else:
                used = user_data.get('usage', {}).get('total_chars', 0)
                remaining = max(0, self.FREE_CHAR_LIMIT - used)
                return {
                    'is_premium': False,
                    'total': self.FREE_CHAR_LIMIT,
                    'used': used,
                    'remaining': remaining,
                    'percentage': (used / self.FREE_CHAR_LIMIT) * 100 if self.FREE_CHAR_LIMIT > 0 else 0
                }
        except Exception as e:
            logger.error(f"❌ فشل جلب إحصائيات الاستخدام: {str(e)}")
            return {
                'is_premium': False,
                'total': self.FREE_CHAR_LIMIT,
                'used': 0,
                'remaining': self.FREE_CHAR_LIMIT,
                'percentage': 0
            }

    def _send_alert(self, user_id, context, message):
        """إرسال تنبيه مع التحسينات"""
        if not context or not user_id or not message:
            return False

        try:
            context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
                disable_notification=True
            )
            return True
        except BadRequest as e:
            logger.error(f"❌ فشل إرسال التنبيه: {str(e)}")
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في إرسال التنبيه: {str(e)}")
        
        return False
