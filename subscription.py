import os
import logging
from datetime import datetime
from telegram import ParseMode
from telegram.error import TelegramError
from firebase_admin import db

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self._load_settings()
        logger.info("تم تهيئة مدير الاشتراكات بنجاح")

    def _load_settings(self):
        """تحميل جميع الإعدادات من متغيرات Render"""
        self.FREE_CHAR_LIMIT = int(os.getenv('FREE_CHAR_LIMIT', 500))
        self.MAX_VOICE_CLONES = int(os.getenv('MAX_VOICE_CLONES', 1))
        self.REQUIRED_CHANNELS = [
            channel.strip() 
            for channel in os.getenv('REQUIRED_CHANNELS', '').split(',') 
            if channel.strip()
        ]

    def check_all_limits(self, user_id, context=None, text_length=0):
        """
        التحقق من جميع الحدود:
        1- القنوات المطلوبة
        2- الحد الأقصى للأحرف
        3- حد استنساخ الصوت
        """
        if not self.check_required_channels(user_id, context):
            return False
            
        if not self.check_char_limit(user_id, context, text_length):
            return False
            
        if not self.check_voice_clone_limit(user_id, context):
            return False
            
        return True

    def check_required_channels(self, user_id, context=None):
        """التحقق من الاشتراك في القنوات"""
        if not self.REQUIRED_CHANNELS:
            return True

        for channel in self.REQUIRED_CHANNELS:
            try:
                chat_id = f"@{channel}" if not channel.startswith('@') else channel
                member = context.bot.get_chat_member(chat_id, user_id)
                if member.status in ['left', 'kicked']:
                    self._send_alert(
                        user_id, 
                        context,
                        f"⚠️ يجب الانضمام إلى:\n{', '.join([f'@{c}' for c in self.REQUIRED_CHANNELS]}\nثم أعد المحاولة"
                    )
                    return False
            except TelegramError as e:
                logger.error(f"خطأ في القناة {channel}: {str(e)}")
                continue

        return True

    def check_char_limit(self, user_id, context=None, text_length=0):
        """التحقق من الحد الأقصى للأحرف (500 حرف دائمة)"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        # لا توجد حدود للمميزين
        if user_data.get('premium', {}).get('is_premium', False):
            return True
            
        total_used = user_data.get('usage', {}).get('total_chars', 0)
        remaining = max(0, self.FREE_CHAR_LIMIT - total_used)
        
        if remaining <= 0:
            self._send_alert(
                user_id,
                context,
                f"⚠️ بلغت الحد الأقصى ({self.FREE_CHAR_LIMIT} حرف)\n"
                f"للترقية راسل: {os.getenv('PAYMENT_CHANNEL', '@payment_channel')}"
            )
            return False
            
        if text_length > remaining:
            self._send_alert(
                user_id,
                context,
                f"⚠️ لديك {remaining} حرف متبقٍ فقط\n"
                f"الحد الأقصى: {self.FREE_CHAR_LIMIT} حرف"
            )
            return False
            
        return True

    def check_voice_clone_limit(self, user_id, context=None):
        """التحقق من حد استنساخ الصوت (مرة واحدة)"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        if user_data.get('premium', {}).get('is_premium', False):
            return True
            
        if user_data.get('voice_cloned', False):
            self._send_alert(
                user_id,
                context,
                f"⚠️ يمكنك استنساخ الصوت مرة واحدة فقط\n"
                f"للترقية راسل: {os.getenv('PAYMENT_CHANNEL', '@payment_channel')}"
            )
            return False
            
        return True

    def _send_alert(self, user_id, context, message):
        """إرسال رسالة تنبيه للمستخدم"""
        if context:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"فشل إرسال التنبيه: {str(e)}")

    def update_usage(self, user_id, chars_used):
        """تسجيل الأحرف المستخدمة"""
        try:
            updates = {
                'usage/total_chars': db.Increment(chars_used),
                'last_used': {'.sv': 'timestamp'}
            }
            self.firebase.ref.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الاستخدام: {str(e)}")
            return False
