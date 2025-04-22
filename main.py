import os
import logging
import tempfile
import json
from flask import Flask, request, jsonify
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    Dispatcher,
    CallbackQueryHandler
)
from telegram.parsemode import ParseMode
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# تهيئة التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة التطبيق
app = Flask(__name__)

# تهيئة الكائنات العامة
bot = None
updater = None
dispatcher = None
session = None
firebase_manager = None
subscription_manager = None
admin_panel = None
premium_manager = None

def initialize_bot():
    global bot, updater, dispatcher, session
    global firebase_manager, subscription_manager, admin_panel, premium_manager

    # 1. تهيئة اتصال الطلبات
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 2. تهيئة Firebase
    try:
        from firebase import FirebaseManager
        firebase_manager = FirebaseManager()
    except Exception as e:
        logger.error(f"فشل تهيئة Firebase: {str(e)}")
        raise

    # 3. تهيئة المديرين
    from subscription import SubscriptionManager
    from admin import AdminPanel
    from premium import PremiumManager
    
    subscription_manager = SubscriptionManager(firebase_manager)
    premium_manager = PremiumManager(firebase_manager)
    admin_panel = AdminPanel(firebase_manager, premium_manager)

    # 4. التحقق من متغيرات البيئة
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    API_KEY = os.getenv('SPEECHIFY_API_KEY')

    if not all([BOT_TOKEN, WEBHOOK_URL, API_KEY]):
        missing = [var for var in ['BOT_TOKEN', 'WEBHOOK_URL', 'API_KEY'] if not os.getenv(var)]
        raise ValueError(f"متغيرات البيئة المفقودة: {', '.join(missing)}")

    # 5. تهيئة بوت التليجرام
    bot = Bot(token=BOT_TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dispatcher = updater.dispatcher

    # 6. تسجيل المعالجات
    register_handlers()

    # 7. تعيين ويب هوك
    set_webhook(BOT_TOKEN, WEBHOOK_URL)

    logger.info("✅ تم تهيئة البوت بنجاح")
    return app

def register_handlers():
    # الأوامر الأساسية
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("help", handle_help))
    dispatcher.add_handler(CommandHandler("stats", handle_stats))
    dispatcher.add_handler(CommandHandler("admin", handle_admin))
    dispatcher.add_handler(CommandHandler("premium", handle_premium))

    # معالجات الرسائل
    dispatcher.add_handler(MessageHandler(Filters.voice | Filters.audio, handle_audio))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # معالجات الضغطات
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # معالج الأخطاء
    dispatcher.add_error_handler(handle_errors)

def set_webhook(bot_token, webhook_url):
    """تعيين ويب هوك مع التحقق من الصحة"""
    try:
        webhook_url = webhook_url.rstrip('/')
        full_url = f"{webhook_url}/{bot_token}"
        
        # إزالة الويب هوك الحالي إذا كان موجوداً
        bot.delete_webhook()
        
        # تعيين الويب هوك الجديد
        success = bot.set_webhook(
            url=full_url,
            max_connections=40,
            allowed_updates=["message", "callback_query"]
        )
        
        if success:
            logger.info(f"✅ تم تعيين الويب هوك بنجاح: {full_url}")
        else:
            logger.error("❌ فشل تعيين الويب هوك")
    except Exception as e:
        logger.error(f"❌ خطأ في تعيين الويب هوك: {str(e)}")
        raise

def handle_errors(update, context):
    """معالجة الأخطاء العامة"""
    try:
        logger.error(f"حدث خطأ: {context.error}", exc_info=True)
        
        if update and update.effective_chat:
            error_msg = "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_msg
            )
    except Exception as e:
        logger.error(f"❌ فشل في معالجة الخطأ: {str(e)}")

# --- معالجات الأوامر ---
def handle_start(update, context):
    """معالجة أمر /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من القنوات المطلوبة أولاً
    if not subscription_manager.check_required_channels(user.id, context):
        return
    
    # ترحيب بالمستخدم
    welcome_msg = """
    🎤 \*مرحباً بك في بوت استنساخ الأصوات\!\*
    
    ✨ \*المميزات:\*
    \- استنساخ صوتك من عينة صوتية
    \- تحويل النص إلى صوت باستخدام صوتك
    
    💡 *كيف تبدأ؟*
    1. أرسل مقطعاً صوتياً (10-30 ثانية)
    2. انتظر تأكيد الاستنساخ
    3. أرسل النص لتحويله إلى صوت
    
    📌 \*الحدود:\*
    \- المستخدمون المجانيون: 500 حرف
    \- استنساخ صوت مرة واحدة فقط
    
    اكتب /help للمساعدة
    """
    
    try:
        context.bot.send_message(
            chat_id=chat.id,
            text=welcome_msg,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
        # تسجيل المستخدم الجديد
        register_new_user(user)
        
    except Exception as e:
        logger.error(f"فشل في معالجة أمر /start: {str(e)}")
        context.bot.send_message(
            chat_id=chat.id,
            text="❌ حدث خطأ أثناء معالجة طلبك"
        )

def register_new_user(user):
    """تسجيل مستخدم جديد في Firebase"""
    try:
        user_data = firebase_manager.get_user_data(user.id)
        
        if not user_data:
            new_user = {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'first_join': {'.sv': 'timestamp'},
                'usage': {
                    'total_chars': 0,
                    'voice_cloned': False
                },
                'language_code': user.language_code
            }
            
            firebase_manager.save_user_data(user.id, new_user)
            logger.info(f"تم تسجيل مستخدم جديد: {user.id}")
    except Exception as e:
        logger.error(f"فشل تسجيل مستخدم جديد: {str(e)}")

def handle_help(update, context):
    """معالجة أمر /help"""
    help_msg = """
    📝 \*دليل استخدام البوت\*
    
    🔹 \*الخطوات الأساسية:\*
    1\. أرسل مقطعاً صوتياً (10-30 ثانية)
    2\. انتظر تأكيد الاستنساخ
    3\. أرسل النص لتحويله إلى صوت
    
    🔹 \*الأوامر المتاحة:\*
    /start \- بدء استخدام البوت
    /help \- عرض هذه الرسالة
    /premium \- معلومات الاشتراك المميز
    
    🔹 \*الحدود:\*
    \- المستخدمون المجانيون: 500 حرف
    \- استنساخ صوت مرة واحدة فقط
    
    للاستفسارات: @support
    """
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_msg,
        parse_mode=ParseMode.MARKDOWN_V2
    )

def handle_stats(update, context):
    """معالجة أمر /stats (للمشرفين فقط)"""
    user_id = update.effective_user.id
    
    if not admin_panel.is_admin(user_id):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⛔ ليس لديك صلاحية الوصول إلى هذه الميزة"
        )
        return
    
    stats = admin_panel.get_stats()
    stats_msg = f"""
    📊 \*إحصائيات البوت\*
    
    👥 المستخدمون: {stats['total_users']}
    💎 المشتركون: {stats['premium_users']}
    🔄 النشطاء اليوم: {stats['active_today']}
    📨 إجمالي الأحرف: {stats['total_requests']:,}
    """
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=stats_msg,
        parse_mode=ParseMode.MARKDOWN_V2
    )

def handle_admin(update, context):
    """معالجة أمر /admin"""
    user_id = update.effective_user.id
    
    if not admin_panel.is_admin(user_id):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⛔ ليس لديك صلاحية الوصول إلى هذه الميزة"
        )
        return
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👨‍💻 لوحة تحكم المشرفين",
        reply_markup=admin_panel.get_admin_dashboard()
    )

def handle_premium(update, context):
    """معالجة أمر /premium"""
    user_id = update.effective_user.id
    message = premium_manager.get_info_message(user_id)
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=premium_manager.get_upgrade_keyboard(user_id)
    )

# --- معالجات الرسائل ---
def handle_audio(update, context):
    """معالجة الرسائل الصوتية"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من القيود
    if not subscription_manager.check_all_limits(user.id, context):
        return
    
    # معالجة الملف الصوتي
    try:
        file = update.message.voice or update.message.audio
        file_size = file.file_size / (1024 * 1024)  # حجم الملف بالميجابايت
        
        # التحقق من حجم الملف
        if file_size > 5:  # 5MB كحد أقصى
            context.bot.send_message(
                chat_id=chat.id,
                text="⚠️ الملف كبير جداً (الحد الأقصى 5MB)"
            )
            return
        
        # تنزيل الملف الصوتي
        file = context.bot.get_file(file.file_id)
        audio_data = session.get(file.file_path).content
        
        # استنساخ الصوت
        clone_voice(user.id, audio_data, context)
        
    except Exception as e:
        logger.error(f"فشل معالجة الملف الصوتي: {str(e)}")
        context.bot.send_message(
            chat_id=chat.id,
            text="❌ حدث خطأ أثناء معالجة الملف الصوتي"
        )

def clone_voice(user_id, audio_data, context):
    """استنساخ الصوت باستخدام API"""
    try:
        # إعداد بيانات الطلب
        files = {
            'sample': ('voice.ogg', audio_data, 'audio/ogg'),
            'name': (None, f'user_{user_id}_voice'),
            'gender': (None, 'male')
        }
        
        # إرسال الطلب
        response = session.post(
            'https://api.speechify.com/v1/voices',
            headers={'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}'},
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            voice_id = response.json().get('id')
            
            # حفظ بيانات الصوت
            voice_data = {
                'voice_id': voice_id,
                'status': 'active',
                'timestamp': {'.sv': 'timestamp'}
            }
            
            firebase_manager.update_voice_clone(user_id, voice_data)
            
            context.bot.send_message(
                chat_id=user_id,
                text="✅ تم استنساخ صوتك بنجاح\! يمكنك الآن إرسال النصوص"
            )
        else:
            error = response.json().get('error', 'Unknown error')
            context.bot.send_message(
                chat_id=user_id,
                text=f"❌ فشل استنساخ الصوت: {error}"
            )
            
    except Exception as e:
        logger.error(f"فشل استنساخ الصوت: {str(e)}")
        context.bot.send_message(
            chat_id=user_id,
            text="❌ حدث خطأ أثناء استنساخ الصوت"
        )

def handle_text(update, context):
    """معالجة الرسائل النصية"""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    # تخطي الرسائل القصيرة جداً
    if len(text.strip()) < 3:
        return
    
    # التحقق من القيود
    if not subscription_manager.check_all_limits(user.id, context, len(text)):
        return
    
    # معالجة النص
    try:
        user_data = firebase_manager.get_user_data(user.id)
        voice_id = user_data.get('voice', {}).get('voice_id')
        
        if not voice_id:
            context.bot.send_message(
                chat_id=chat.id,
                text="❌ يرجى استنساخ صوتك أولاً بإرسال مقطع صوتي"
            )
            return
        
        # تحويل النص إلى صوت
        convert_text_to_speech(user.id, voice_id, text, context)
        
    except Exception as e:
        logger.error(f"فشل معالجة النص: {str(e)}")
        context.bot.send_message(
            chat_id=chat.id,
            text="❌ حدث خطأ أثناء معالجة النص"
        )

def convert_text_to_speech(user_id, voice_id, text, context):
    """تحويل النص إلى صوت باستخدام API"""
    try:
        payload = {
            "input": text,
            "voice_id": voice_id,
            "output_format": "mp3"
        }
        
        response = session.post(
            'https://api.speechify.com/v1/audio',
            headers={'Authorization': f'Bearer {os.getenv("SPEECHIFY_API_KEY")}'},
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            # حفظ الملف الصوتي مؤقتاً
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                temp_file = f.name
            
            # إرسال الملف الصوتي
            with open(temp_file, 'rb') as audio_file:
                context.bot.send_voice(
                    chat_id=user_id,
                    voice=audio_file
                )
            
            # تحديث الاستخدام
            firebase_manager.update_usage(user_id, len(text))
            
            # حذف الملف المؤقت
            os.unlink(temp_file)
            
        else:
            error = response.json().get('error', 'Unknown error')
            context.bot.send_message(
                chat_id=user_id,
                text=f"❌ فشل تحويل النص إلى صوت: {error}"
            )
            
    except Exception as e:
        logger.error(f"فشل تحويل النص إلى صوت: {str(e)}")
        context.bot.send_message(
            chat_id=user_id,
            text="❌ حدث خطأ أثناء تحويل النص إلى صوت"
        )

# --- معالجات الضغطات ---
def handle_callback_query(update, context):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    query.answer()
    
    data = query.data
    
    if data.startswith('admin_'):
        admin_panel.handle_admin_actions(update, context)
    elif data.startswith('premium_'):
        handle_premium_callback(update, context)

def handle_premium_callback(update, context):
    """معالجة ضغطات الاشتراك المميز"""
    query = update.callback_query
    data = query.data.split('_')
    
    if len(data) < 3:
        return
    
    action = data[1]
    user_id = int(data[2])
    
    if action == 'monthly':
        # تفعيل اشتراك شهري
        if premium_manager.activate_premium(user_id):
            query.edit_message_text(
                text="✅ تم تفعيل الاشتراك المميز بنجاح\!",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            query.edit_message_text(
                text="❌ فشل في التفعيل، يرجى المحاولة لاحقاً",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    elif action == 'trial':
        # تفعيل تجربة مجانية
        if premium_manager.activate_premium(user_id, is_trial=True):
            query.edit_message_text(
                text="🎁 تم تفعيل التجربة المجانية بنجاح\!",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            query.edit_message_text(
                text="❌ فشل في تفعيل التجربة",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    elif action == 'info':
        # عرض معلومات الاشتراك
        message = premium_manager.get_info_message(user_id)
        query.edit_message_text(
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=premium_manager.get_upgrade_keyboard(user_id)
        )

# --- مسارات الويب ---
@app.route('/')
def index():
    return "Bot is running!"

@app.route(f'/{os.getenv("TELEGRAM_BOT_TOKEN")}', methods=['POST'])
def webhook():
    """معالجة طلبات الويب هوك"""
    try:
        update = Update.de_json(request.get_json(), bot)
        dispatcher.process_update(update)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"خطأ في الويب هوك: {str(e)}")
        return jsonify({'status': 'error'}), 500

# --- تشغيل التطبيق ---
app = initialize_bot()

def create_app():
    return app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
