from telegram import Update
from telegram.ext import CallbackContext
from templates.messages import WELCOME_MESSAGE
import os

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    trials = int(os.getenv('DEFAULT_TRIALS', 2))
    max_chars = os.getenv('MAX_CHARS_PER_TRIAL', 100)
    channels = ", ".join([f"@{c}" for c in os.getenv('REQUIRED_CHANNELS', '').split(',') if c])
    
    welcome_msg = WELCOME_MESSAGE.format(
        user_name=user.first_name,
        trials=trials,
        max_chars=max_chars,
        channels=channels
    )
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_msg,
        parse_mode='Markdown'
    )
