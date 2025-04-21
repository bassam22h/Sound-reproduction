import os
import logging
from telegram import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self.MAX_FREE_TRIALS = int(os.getenv('DEFAULT_TRIALS', 2))
        self.MAX_FREE_CHARS = int(os.getenv('MAX_CHARS_PER_TRIAL', 100))
        self.REQUIRED_CHANNELS = [
            channel.strip() 
            for channel in os.getenv('REQUIRED_CHANNELS', '').split(',') 
            if channel.strip()
        ]
        logger.info(f"تم تهيئة مدير الاشتراكات - القنوات المطلوبة: {self.REQUIRED_CHANNELS}")

    def check_permissions(self, user_id, context=None):
        """
        التحقق الشامل من الصلاحيات (القنوات + الاستخدام)
        """
        if not self.check_required_channels(user_id, context):
            return False
            
        if not self.check_usage_limits(user_id, context):
            return False
            
        return True

    def check_required_channels(self, user_id, context=None):
        """التحقق من الاشتراك في القنوات المطلوبة"""
        if not self.REQUIRED_CHANNELS:
            return True

        try:
            for channel in self.REQUIRED_CHANNELS:
                try:
                    chat_id = f"@{channel}" if not channel.startswith('@') else channel
                    member = context.bot.get_chat_member(
                        chat_id=chat_id,
                        user_id=user_id
                    )
                    if member.status in ['left', 'kicked']:
                        self._send_channel_alert(user_id, context)
                        return False
                except TelegramError as e:
                    logger.error(f"خطأ في التحقق من القناة {channel}: {str(e)}")
                    continue

            return True
        except Exception as e:
            logger.error(f"خطأ عام في التحقق من القنوات: {str(e)}")
            return True

    def check_usage_limits(self, user_id, context=None):
        """التحقق من الحدود المجانية فقط"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        # التحقق من الحدود المجانية
        if user_data.get('premium', {}).get('is_premium', False):
            return True  # المستخدم المميز لا توجد عليه قيود
            
        usage = user_data.get('usage', {})
        
        if usage.get('requests', 0) >= self.MAX_FREE_TRIALS:
            if context:
                context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ لقد استنفذت محاولاتك المجانية",
                    parse_mode=ParseMode.MARKDOWN
                )
            return False
            
        return True

    def _send_channel_alert(self, user_id, context):
        """إرسال تنبيه الانضمام للقنوات"""
        if not context:
            return

        try:
            channels_list = "\n".join([f"- @{channel}" for channel in self.REQUIRED_CHANNELS])
            message = (
                "⚠️ يجب الانضمام إلى القنوات التالية أولاً:\n"
                f"{channels_list}\n\n"
                "بعد الانضمام، أعد المحاولة"
            )
            
            context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"فشل إرسال تنبيه القنوات: {str(e)}")

    def get_free_usage(self, user_id):
        """الحصول على بيانات الاستخدام المجاني"""
        user_data = self.firebase.get_user_data(user_id) or {}
        if user_data.get('premium', {}).get('is_premium', False):
            return {
                'is_premium': True,
                'remaining': 'غير محدود'
            }
            
        usage = user_data.get('usage', {})
        return {
            'is_premium': False,
            'remaining_trials': max(0, self.MAX_FREE_TRIALS - usage.get('requests', 0)),
            'remaining_chars': max(0, self.MAX_FREE_CHARS - usage.get('chars_used', 0))
        }
