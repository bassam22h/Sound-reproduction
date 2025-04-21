import logging
from telegram import Update
from telegram.ext import CallbackContext
from templates.messages import ERROR_MESSAGE

logger = logging.getLogger(__name__)

def error_handler(update: Update, context: CallbackContext):
    try:
        logger.error(msg="حدث خطأ في المعالج", exc_info=context.error)
        
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ERROR_MESSAGE,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
