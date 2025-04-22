import os
import firebase_admin
from firebase_admin import credentials, db
import logging

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self):
        self.cred = self._get_firebase_credentials()
        self._validate_credentials()
        self._initialize_app()
        self.ref = db.reference('/')
        logger.info("✅ تم تهيئة Firebase بنجاح")

    def _get_firebase_credentials(self):
        """تهيئة بيانات الاعتماد مع التحقق من المتغيرات"""
        required_env_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL',
            'FIREBASE_CLIENT_ID',
            'FIREBASE_CLIENT_CERT_URL',
            'FIREBASE_DATABASE_URL'
        ]
        
        for var in required_env_vars:
            if not os.getenv(var):
                logger.error(f"❌ متغير البيئة المطلوب غير موجود: {var}")

        return credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL')
        })

    def _validate_credentials(self):
        """التحقق من صحة بيانات الاعتماد"""
        if not all([
            self.cred.project_id,
            self.cred.private_key,
            self.cred.client_email
        ]):
            raise ValueError("❌ بيانات اعتماد Firebase غير صالحة")

    def _initialize_app(self):
        """تهيئة التطبيق مع منع التهيئة المكررة"""
        if not firebase_admin._apps:
            firebase_admin.initialize_app(self.cred, {
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
            })

    def save_user_data(self, user_id, data):
        """حفظ بيانات المستخدم مع التحقق من المدخلات"""
        if not user_id or not data:
            logger.error("❌ معرّف المستخدم أو البيانات فارغة")
            return False

        try:
            self.ref.child('users').child(str(user_id)).set(data)
            logger.info(f"✅ تم حفظ بيانات المستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ البيانات: {str(e)}")
            return False

    def get_user_data(self, user_id):
        """جلب بيانات المستخدم مع التعامل مع الأخطاء"""
        try:
            data = self.ref.child('users').child(str(user_id)).get()
            return data if data else {}
        except Exception as e:
            logger.error(f"❌ فشل جلب بيانات المستخدم {user_id}: {str(e)}")
            return {}

    def update_usage(self, user_id, chars_used):
        """تحديث الاستخدام مع العمليات الحسابية الآمنة"""
        if not isinstance(chars_used, int) or chars_used <= 0:
            logger.error(f"❌ قيمة الأحرف غير صالحة: {chars_used}")
            return False

        try:
            updates = {
                'usage/total_chars': db.Increment(chars_used),
                'last_used': {'.sv': 'timestamp'}
            }
            self.ref.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحديث الاستخدام: {str(e)}")
            return False

    def update_voice_clone(self, user_id, voice_data):
        """تحديث بيانات الصوت مع التحقق الشامل"""
        required_fields = ['voice_id', 'status']
        if not all(field in voice_data for field in required_fields):
            logger.error(f"❌ بيانات الصوت ناقصة: {voice_data}")
            return False

        try:
            updates = {
                'voice': voice_data,
                'voice_cloned': True,
                'last_voice_update': {'.sv': 'timestamp'}
            }
            self.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"✅ تم تحديث الصوت للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحديث الصوت: {str(e)}")
            return False
