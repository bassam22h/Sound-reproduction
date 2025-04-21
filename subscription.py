import os
from telegram import ParseMode

class SubscriptionManager:
    def __init__(self, firebase):
        self.firebase = firebase
        self.MAX_FREE_TRIALS = int(os.getenv('DEFAULT_TRIALS', 2))
        self.MAX_FREE_CHARS = int(os.getenv('MAX_CHARS_PER_TRIAL', 100))
        self.REQUIRED_CHANNELS = os.getenv('REQUIRED_CHANNELS', '').split(',')
        
    def check_required_channels(self, user_id, context=None):
        if not self.REQUIRED_CHANNELS:
            return True
            
        # كود التحقق من الاشتراك في القنوات المطلوبة
        # ...
        
    def check_audio_permission(self, user_id, context=None):
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
