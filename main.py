import tempfile
import os
import logging
import json
from flask import Flask, request, jsonify
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Dispatcher
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from firebase import FirebaseManager
from subscription import SubscriptionManager
from admin import AdminPanel

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask
app = Flask(__name__)

# كائنات عامة
bot = None
updater = None
dp = None
session = None
firebase = None
subscription = None
admin = None
API_KEY = None

def initialize_bot():
    global bot, updater, dp, session, firebase, subscription, admin, API_KEY
    
    # 1. إعداد اتصال requests
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount("https://", adapter)
    
    # 2. إعداد Firebase والإدارة
    firebase = FirebaseManager()
    subscription = SubscriptionManager(firebase)
    admin = AdminPanel(firebase)
    
    # 3. إعداد بوت التليجرام
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    API_KEY = os.getenv('SPEECHIFY_API_KEY')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    if not all([BOT_TOKEN, API_KEY, WEBHOOK_URL]):
        raise ValueError("Missing required environment variables")
    
    bot = Bot(token=BOT_TOKEN)
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # 4. تسجيل المعالجات
    register_handlers()
    
    # 5. تعيين ويب هوك
    set_webhook(BOT_TOKEN, WEBHOOK_URL)
    
    return app

def register_handlers():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

def set_webhook(bot_token, webhook_url):
    try:
        full_url = f"{webhook_url}/{bot_token}"
        bot.delete_webhook()
        success = bot.set_webhook(url=full_url)
        if success:
            logger.info(f"✅ تم تعيين الويب هوك بنجاح: {full_url}")
        else:
            logger.error("❌ فشل في تعيين الويب هوك")
    except Exception as e:
        logger.error(f"🚨 خطأ في تعيين الويب هوك: {str(e)}")

# ========== دوال معالجة الأوامر ==========
def start(update, context):
    user_id = update.effective_user.id
    if not subscription.check_required_channels(user_id, context):
        return
        
    welcome_msg = """
    🎤 *مرحباً بكم في بوت استنساخ الأصوات!*
    
    ✨ *الميزات المتاحة:*
    - استنسخ صوتك من عينة صوتية (10-30 ثانية)
    - حول النص إلى صوت باستخدام صوتك المستنسخ
    
    ⚠️ *القيود المفروضة:*
    - حد مجاني: 2 طلب لكل مستخدم
    - 100 حرف كحد أقصى لكل طلب
    
    أرسل /help للمزيد من المعلومات
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_msg,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # تسجيل المستخدم الجديد في Firebase
    user_data = {
        'first_join': {'.sv': 'timestamp'},
        'username': update.effective_user.username,
        'full_name': update.effective_user.full_name,
        'usage': {
            'requests': 0,
            'chars_used': 0
        }
    }
    firebase.save_user_data(user_id, 'metadata', user_data)

def help(update, context):
    help_msg = """
    📝 *كيفية استخدام البوت:*
    
    1. أرسل مقطعاً صوتياً (10-30 ثانية) لاستنساخ صوتك
    2. بعد نجاح الاستنساخ، أرسل النص الذي تريد تحويله إلى صوت
    
    ⚠️ *ملاحظات مهمة:*
    - يجب أن يكون المقطع الصوتي واضحاً
    - الحد الأقصى للنص 100 حرف في النسخة المجانية
    - يمكنك استخدام البوت مرتين فقط مجاناً
    
    💰 *للترقية إلى الإصدار المدفوع:* راسل الإدارة
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_msg,
        parse_mode=ParseMode.MARKDOWN
    )

def stats(update, context):
    user_id = update.effective_user.id
    if not admin.is_admin(user_id):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⛔ ليس لديك صلاحية الوصول إلى هذه الميزة"
        )
        return
        
    stats = admin.get_stats()
    stats_msg = f"""
    📊 *إحصائيات البوت:*
    
    👥 عدد المستخدمين: {stats['total_users']}
    📨 عدد الطلبات: {stats['total_requests']}
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=stats_msg,
        parse_mode=ParseMode.MARKDOWN
    )

# ========== معالجة الرسائل ==========
def handle_audio(update, context):
    user_id = update.effective_user.id
    if not subscription.check_voice_permission(user_id, context):
        return

    try:
        file = update.message.voice or update.message.audio
        if not file:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ الرجاء إرسال مقطع صوتي فقط (بين 10-30 ثانية)."
            )
            return

        # تحميل الملف الصوتي
        tg_file = context.bot.get_file(file.file_id)
        audio_data = session.get(tg_file.file_path, timeout=10).content

        # إعداد بيانات الموافقة
        consent_data = {
            "fullName": f"User_{user_id}",
            "email": f"user_{user_id}@bot.com"
        }

        # إعداد بيانات الطلب
        data = {
            'name': f'user_{user_id}_voice',
            'gender': 'male',
            'consent': json.dumps(consent_data, ensure_ascii=False)
        }

        files = {
            'sample': ('voice_sample.ogg', audio_data, 'audio/ogg'),
        }

        for key, value in data.items():
            files[key] = (None, str(value))

        # إرسال الطلب إلى API
        response = session.post(
            'https://api.sws.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {API_KEY}'},
            files=files,
            timeout=15
        )

        if response.status_code == 200:
            voice_id = response.json().get('id')
            voice_data = {
                'voice_id': voice_id,
                'timestamp': {'.sv': 'timestamp'},
                'status': 'active'
            }
            
            if hasattr(subscription, 'premium') and subscription.premium.check_premium_status(user_id):
                if not subscription.premium.record_voice_change(user_id):
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="⚠️ لقد استنفذت عدد مرات تغيير الصوت المسموحة",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                    
            firebase.update_voice_clone(user_id, voice_data)
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ *تم استنساخ صوتك بنجاح!*",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            error_msg = response.json().get('message', 'Unknown error')
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ *خطأ في API:* {error_msg}",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in handle_audio: {str(e)}")
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ حدث خطأ غير متوقع أثناء معالجة الصوت"
        )

def handle_text(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    if not subscription.check_text_permission(user_id, text, context):
        return

    try:
        user_data = firebase.get_user_data(user_id)
        voice_id = user_data.get('voice', {}).get('voice_id')
        
        if not voice_id:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="❌ *يرجى استنساخ صوتك أولاً* بإرسال مقطع صوتي (10-30 ثانية).",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        payload = {
            "input": text,
            "voice_id": voice_id,
            "output_format": "mp3",
            "model": "simba-multilingual"
        }

        response = session.post(
            'https://api.sws.speechify.com/v1/audio/stream',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg'
            },
            json=payload,
            stream=True,
            timeout=30
        )

        if response.status_code == 200:
            try:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            temp_audio.write(chunk)
                    temp_audio_path = temp_audio.name

                with open(temp_audio_path, 'rb') as audio_file:
                    context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio_file
                    )

                firebase.increment_usage(user_id, len(text))
                
                remaining = subscription.get_remaining_chars(user_id)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"📊 *الأحرف المستخدمة:* {len(text)}\n*المتبقي لك:* {remaining}",
                    parse_mode=ParseMode.MARKDOWN
                )

                os.unlink(temp_audio_path)

            except Exception as e:
                logger.error(f"Streaming audio processing error: {str(e)}", exc_info=True)
                context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="❌ حدث خطأ أثناء معالجة الصوت المتدفق"
                )

        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', response.text)
            except json.JSONDecodeError:
                error_msg = response.text
                
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"❌ *خطأ في تحويل النص:* {error_msg}",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}", exc_info=True)
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="❌ حدث خطأ غير متوقع أثناء معالجة النص"
        )

# ========== مسارات الويب ==========
@app.route(f'/{os.getenv("TELEGRAM_BOT_TOKEN")}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dp.process_update(update)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error'}), 500

@app.route('/')
def index():
    return 'Bot is running!'

# ========== التشغيل الرئيسي ==========
def create_app():
    return initialize_bot()

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
