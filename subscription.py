import os
import logging
from telegram import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self.FREE_CHAR_LIMIT = int(os.getenv('FREE_CHAR_LIMIT', 500))
        self.REQUIRED_CHANNELS = [
            channel.strip() 
            for channel in os.getenv('REQUIRED_CHANNELS', '').split(',') 
            if channel.strip()
        ]

    def check_all_limits(self, user_id, context, text_length=0):
        """تجمع جميع التحققات في دالة واحدة"""
        return all([
            self.check_required_channels(user_id, context),
            self.check_char_limit(user_id, context, text_length),
            self.check_voice_clone_limit(user_id, context)
        ])

    def check_voice_clone_limit(self, user_id, context=None, ignore_limit=False):
        user_data = self.firebase.get_user_data(user_id) or {}
        
        if user_data.get('premium', {}).get('is_premium', False):
            return True
        
        if user_data.get('voice_cloned', False) and not ignore_limit:
            self._send_alert(
                user_id,
                context,
                "⚠️ يمكنك استنساخ الصوت مرة واحدة فقط\n"
                f"للترقية راسل: {os.getenv('PAYMENT_CHANNEL')}"
            )
            return False
        
        return True

    def check_required_channels(self, user_id, context=None):
        if not self.REQUIRED_CHANNELS:
            return True

        for channel in self.REQUIRED_CHANNELS:
            try:
                chat_id = f"@{channel}" if not channel.startswith('@') else channel
                member = context.bot.get_chat_member(chat_id, user_id)
                if member.status in ['left', 'kicked']:
                    channels_list = "\n".join([f"@{c}" for c in self.REQUIRED_CHANNELS])
                    self._send_alert(
                        user_id,
                        context,
                        f"⚠️ يجب الانضمام إلى القنوات التالية أولاً:\n{channels_list}"
                    )
                    return False
            except TelegramError as e:
                logger.error(f"Error checking channel {channel}: {str(e)}")
                continue
        return True

    def check_char_limit(self, user_id, context=None, text_length=0):
        user_data = self.firebase.get_user_data(user_id) or {}
        if user_data.get('premium', {}).get('is_premium', False):
            return True

        total_used = user_data.get('usage', {}).get('total_chars', 0)
        remaining = self.FREE_CHAR_LIMIT - total_used

        if remaining <= 0:
            self._send_alert(
                user_id,
                context,
                f"⚠️ بلغت الحد الأقصى ({self.FREE_CHAR_LIMIT} حرف)\n"
                f"للترقية راسل: {os.getenv('PAYMENT_CHANNEL')}"
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

    def _send_alert(self, user_id, context, message):
        """إرسال رسالة تنبيه مع التحقق من السياق"""
        if context:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {str(e)}")
