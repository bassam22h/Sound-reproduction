import re
from telegram import ParseMode

def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_markdown(context, chat_id, text):
    clean_text = escape_markdown(text)
    context.bot.send_message(chat_id=chat_id, text=clean_text, parse_mode=ParseMode.MARKDOWN_V2)