import tempfile
import os
import logging
import json
from flask import Flask, request
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
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

class VoiceCloneBot:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_requests_session()
        self.firebase = FirebaseManager()
        self.subscription = SubscriptionManager(self.firebase)
        self.admin = AdminPanel(self.firebase)
        
        self.BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.API_KEY = os.getenv('SPEECHIFY_API_KEY')
        self.bot = Bot(token=self.BOT_TOKEN)
        
        self.updater = Updater(token=self.BOT_TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
        self.register_handlers()
        
        # إعداد مسارات الويب هوك
        self.app.route(f'/{self.BOT_TOKEN}', methods=['POST'])(self.webhook)
        self.app.route('/')(self.index)
        
    def setup_requests_session(self):
        self.session = requests.Session()
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
        self.session.mount("https://", adapter)
    
    def register_handlers(self):
        self.dp.add_handler(CommandHandler("start", self.start))
        self.dp.add_handler(CommandHandler("help", self.help))
        self.dp.add_handler(CommandHandler("stats", self.stats))
        self.dp.add_handler(MessageHandler(Filters.voice | Filters.audio, self.handle_audio))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text))
        
    def start(self, update, context):
        user_id = update.effective_user.id
        if not self.subscription.check_required_channels(user_id, context):
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
        self.firebase.save_user_data(user_id, 'metadata', user_data)
        
    def help(self, update, context):
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
        
    def stats(self, update, context):
        user_id = update.effective_user.id
        if not self.admin.is_admin(user_id):
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⛔ ليس لديك صلاحية الوصول إلى هذه الميزة"
            )
            return
            
        stats = self.admin.get_stats()
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
        
    def handle_audio(self, update, context):
    user_id = update.effective_user.id
    
    # التحقق من الصلاحيات
    if not self.subscription.check_voice_permission(user_id, context):
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
            audio_data = self.session.get(tg_file.file_path, timeout=10).content

         if response.status_code == 200:
            voice_id = response.json().get('id')
            voice_data = {
                'voice_id': voice_id,
                'timestamp': {'.sv': 'timestamp'},
                'status': 'active'
            }
            
            # حفظ البيانات في Firebase
            if self.premium.check_premium_status(user_id):
                if not self.premium.record_voice_change(user_id):
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="⚠️ لقد استنفذت عدد مرات تغيير الصوت المسموحة",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                    
            self.firebase.update_voice_clone(user_id, voice_data)
            
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="✅ *تم استنساخ صوتك بنجاح!*",
                parse_mode=ParseMode.MARKDOWN
            )
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
            response = self.session.post(
                'https://api.sws.speechify.com/v1/voices',
                headers={'Authorization': f'Bearer {self.API_KEY}'},
                files=files,
                timeout=15
            )

            if response.status_code == 200:
                voice_id = response.json().get('id')
                
                # حفظ بيانات الصوت في Firebase
                voice_data = {
                    'voice_id': voice_id,
                    'timestamp': {'.sv': 'timestamp'},
                    'status': 'active'
                }
                self.firebase.save_user_data(user_id, 'voice', voice_data)
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="✅ *تم استنساخ صوتك بنجاح!*\nيمكنك الآن إرسال النص لتحويله إلى صوت.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                error_msg = response.json().get('message', 'Unknown error')
                context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=f"❌ *خطأ في API:* {error_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON response")
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="❌ حدث خطأ في معالجة الرد من الخادم"
            )
        except Exception as e:
            logger.error(f"Error in handle_audio: {str(e)}")
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="❌ حدث خطأ غير متوقع أثناء معالجة الصوت"
            )
            
    def handle_text(self, update, context):
        user_id = update.effective_user.id
        text = update.message.text

        # التحقق من الصلاحيات والقيود
        if not self.subscription.check_text_permission(user_id, text, context):
            return

        try:
            # الحصول على voice_id من Firebase
            user_data = self.firebase.get_user_data(user_id)
            voice_id = user_data.get('voice', {}).get('voice_id')
            
            if not voice_id:
                context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="❌ *يرجى استنساخ صوتك أولاً* بإرسال مقطع صوتي (10-30 ثانية).",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # إعداد بيانات الطلب
            payload = {
                "input": text,
                "voice_id": voice_id,
                "output_format": "mp3",
                "model": "simba-multilingual"
            }

            # إرسال الطلب إلى API
            response = self.session.post(
                'https://api.sws.speechify.com/v1/audio/stream',
                headers={
                    'Authorization': f'Bearer {self.API_KEY}',
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg'
                },
                json=payload,
                stream=True,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    # حفظ الملف الصوتي المؤقت
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                        for chunk in response.iter_content(chunk_size=4096):
                            if chunk:
                                temp_audio.write(chunk)
                        temp_audio_path = temp_audio.name

                    # إرسال الملف الصوتي للمستخدم
                    with open(temp_audio_path, 'rb') as audio_file:
                        context.bot.send_voice(
                            chat_id=update.effective_chat.id,
                            voice=audio_file
                        )

                    # تحديث إحصائيات الاستخدام في Firebase
                    self.firebase.increment_usage(user_id, len(text))
                    
                    # إرسال إشعار باستخدام الأحرف المتبقية
                    remaining = self.subscription.get_remaining_chars(user_id)
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"📊 *الأحرف المستخدمة:* {len(text)}\n*المتبقي لك:* {remaining}",
                        parse_mode=ParseMode.MARKDOWN
                    )

                    # حذف الملف المؤقت
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
    
    def webhook(self):
        update = Update.de_json(request.get_json(force=True), self.bot)
        self.dp.process_update(update)
        return 'ok'
        
    def index(self):
        return 'Bot is running!'
        
    def run(self):
        port = int(os.environ.get('PORT', 10000))
        self.app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    bot = VoiceCloneBot()
    bot.run()
