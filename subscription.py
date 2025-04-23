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
        self.PAYMENT_CHANNEL = os.getenv('PAYMENT_CHANNEL', '@premium_support').strip()
        if not self.PAYMENT_CHANNEL.startswith('@'):
            self.PAYMENT_CHANNEL = '@' + self.PAYMENT_CHANNEL

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
        for channel in os.getenv('REQUIRED_CHANNELS', '').split(','):
            channel = channel.strip()
            if channel:
                channels.append(f'@{channel}' if not channel.startswith('@') else channel)
        logger.info(f"📢 القنوات المطلوبة: {channels}")
        return channels

    def check_all_limits(self, user_id, context, text_length=0):
        """فحص جميع القيود"""
        return all([
            self.check_required_channels(user_id, context),
            self.check_char_limit(user_id, context, text_length),
            self.check_voice_clone_limit(user_id, context)
        ])

    def check_voice_clone_limit(self, user_id, context=None, ignore_limit=False):
        """فحص حد استنساخ الصوت"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        if user_data.get('premium', {}).get('is_premium', False):
            return True
            
        if user_data.get('voice_cloned', False) and not ignore_limit:
            alert_msg = (
                "<b>⚠️ لقد وصلت إلى حد استنساخ الصوت</b>\n\n"
                "يمكنك استنساخ الصوت مرة واحدة فقط في النسخة المجانية\n"
                f"للترقية: {self.PAYMENT_CHANNEL}"
            )
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"فشل إرسال تحذير الصوت: {str(e)}")
            return False
        return True

    def check_required_channels(self, user_id, context=None):
        """فحص القنوات المطلوبة"""
        if not self.REQUIRED_CHANNELS:
            return True

        missing_channels = []
        for channel in self.REQUIRED_CHANNELS:
            try:
                if context:
                    member = context.bot.get_chat_member(channel, user_id)
                    if member.status in ['left', 'kicked']:
                        missing_channels.append(channel)
            except Exception as e:
                logger.error(f"خطأ في التحقق من القناة {channel}: {str(e)}")

        if missing_channels:
            channels_list = "\n".join(f"• {c}" for c in missing_channels)
            alert_msg = (
                "<b>📢 يجب الانضمام إلى القنوات التالية أولاً</b>\n\n"
                f"{channels_list}\n\n"
                "بعد الانضمام، اضغط /start مرة أخرى"
            )
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"فشل إرسال تحذير القنوات: {str(e)}")
            return False
        return True

    def check_char_limit(self, user_id, context=None, text_length=0):
        """فحص حد الأحرف"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        if user_data.get('premium', {}).get('is_premium', False):
            return True

        total_used = user_data.get('usage', {}).get('total_chars', 0)
        remaining = self.FREE_CHAR_LIMIT - total_used

        if remaining <= 0:
            alert_msg = (
                "<b>⚠️ لقد وصلت إلى الحد الأقصى للأحرف</b>\n\n"
                f"الحد المجاني: <code>{self.FREE_CHAR_LIMIT}</code> حرف\n"
                f"للترقية: {self.PAYMENT_CHANNEL}"
            )
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"فشل إرسال تحذير الأحرف: {str(e)}")
            return False

        if remaining <= self.FREE_CHAR_LIMIT * 0.2 and total_used > 0:
            alert_msg = (
                "<b>🔔 تنبيه: الأحرف المتبقية قليلة</b>\n\n"
                f"الأحرف المتبقية: <code>{remaining}</code>\n"
                f"الحد المجاني: <code>{self.FREE_CHAR_LIMIT}</code> حرف\n"
                f"للترقية: {self.PAYMENT_CHANNEL}"
            )
            try:
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"فشل إرسال تنبيه الأحرف: {str(e)}")

        return True

    def get_usage_stats(self, user_id):
        """الحصول على إحصائيات الاستخدام"""
        try:
            user_data = self.firebase.get_user_data(user_id) or {}
            
            if user_data.get('premium', {}).get('is_premium', False):
                remaining = user_data['premium'].get('remaining_chars', 0)
                used = user_data['usage'].get('total_chars', 0)
                total = remaining + used
                return {
                    'is_premium': True,
                    'total': total,
                    'used': used,
                    'remaining': remaining,
                    'percentage': (used / total) * 100 if total > 0 else 0
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
            logger.error(f"فشل جلب إحصائيات الاستخدام: {str(e)}")
            return {
                'is_premium': False,
                'total': self.FREE_CHAR_LIMIT,
                'used': 0,
                'remaining': self.FREE_CHAR_LIMIT,
                'percentage': 0
        }
