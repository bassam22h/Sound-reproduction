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
        self.MAX_VOICE_CLONES = int(os.getenv('MAX_VOICE_CLONEOS', 1))
        self.REQUIRED_CHANNELS = [
            channel.strip() 
            for channel in os.getenv('REQUIRED_CHANNELS', '').split(',') 
            if channel.strip()
        ]

    def check_required_channels(self, user_id, context=None):
        """
        التحقق من اشتراك المستخدم في القنوات المطلوبة
        Returns:
            bool: True إذا كان مشتركاً أو لا توجد قنوات مطلوبة
        """
        if not self.REQUIRED_CHANNELS:
            return True

        try:
            for channel in self.REQUIRED_CHANNELS:
                try:
                    member = context.bot.get_chat_member(
                        chat_id=channel, 
                        user_id=user_id
                    )
                    if member.status in ['left', 'kicked']:
                        self._send_channel_alert(user_id, context)
                        return False
                except TelegramError as e:
                    logger.error(f"Failed to check channel {channel}: {str(e)}")
                    continue

            return True
        except Exception as e:
            logger.error(f"Error in check_required_channels: {str(e)}")
            return True

    def _send_channel_alert(self, user_id, context):
        """إرسال رسالة تنبيه للانضمام إلى القنوات"""
        if not context:
            return

        channels_list = "\n".join([f"• @{channel}" for channel in self.REQUIRED_CHANNELS])
        message = (
            "⚠️ *يجب الانضمام إلى القنوات التالية أولاً:*\n"
            f"{channels_list}\n\n"
            "بعد الانضمام، أرسل /start مرة أخرى"
        )
        
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except TelegramError as e:
            logger.error(f"Failed to send channel alert: {str(e)}")

    def check_voice_permission(self, user_id, context=None):
        """التحقق من إذن استنساخ الصوت"""
        user_data = self.firebase.get_user_data(user_id) or {}
        
        # للمستخدمين المميزين
        if user_data.get('premium', {}).get('is_premium', False):
            premium = user_data['premium']
            if premium.get('voice_clones_used', 0) >= int(os.getenv('MAX_VOICE_CLONES', 10)):
                if context:
                    context.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ لقد استنفذت عدد مرات تغيير الصوت المسموحة",
                        parse_mode=ParseMode.MARKDOWN
                    )
                return False
            return True
        
        # للمستخدمين المجانيين
        if user_data.get('voice_cloned', False):
            if context:
                context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ يمكنك استنساخ صوت واحد فقط في النسخة المجانية",
                    parse_mode=ParseMode.MARKDOWN
                )
            return False
            
        return True
        
    def check_audio_permission(self, user_id, context=None):
        """التحقق من إذن استخدام ميزة الصوت"""
        user_data = self.firebase.get_user_data(user_id)
        if user_data and user_data.get('voice_cloned'):
            if context:
                context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ لقد قمت بالفعل باستنساخ صوتك سابقاً",
                    parse_mode=ParseMode.MARKDOWN)
            return False
        return True
        
    def check_text_permission(self, user_id, text, context=None):
        """التحقق من إذن استخدام ميزة النص"""
        user_data = self.firebase.get_user_data(user_id) or {}
        usage = user_data.get('usage', {})
        
        if len(text) > self.MAX_FREE_CHARS:
            if context:
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ تجاوزت الحد المسموح ({self.MAX_FREE_CHARS} حرف)",
                    parse_mode=ParseMode.MARKDOWN)
            return False
            
        if (usage.get('requests', 0) >= self.MAX_FREE_TRIALS and 
            not user_data.get('premium', False)):
            if context:
                context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ لقد استنفذت محاولاتك المجانية",
                    parse_mode=ParseMode.MARKDOWN)
            return False
            
        return True

    def get_remaining_chars(self, user_id):
        """الحصول على عدد الأحرف المتبقية"""
        user_data = self.firebase.get_user_data(user_id) or {}
        if user_data.get('premium', False):
            return "غير محدود"
        
        usage = user_data.get('usage', {})
        used = usage.get('chars_used', 0)
        return max(0, self.MAX_FREE_CHARS - used)
