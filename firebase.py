import os
import firebase_admin
from firebase_admin import credentials, db
import logging

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self):
        self.cred = self._get_firebase_credentials()
        self._initialize_app()
        self.ref = db.reference('/')
        logger.info("✅ تم تهيئة Firebase بنجاح")

    def _get_firebase_credentials(self):
        """تهيئة بيانات الاعتماد بدون تحقق غير ضروري"""
        try:
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
        except Exception as e:
            logger.error(f"❌ فشل تحميل بيانات الاعتماد: {str(e)}")
            raise

    def _initialize_app(self):
        """تهيئة التطبيق مع التحقق من التهيئة المسبقة"""
        if not firebase_admin._apps:
            try:
                firebase_admin.initialize_app(
                    self.cred,
                    {'databaseURL': os.getenv('FIREBASE_DATABASE_URL')}
                )
            except ValueError as e:
                if "already exists" in str(e):
                    logger.warning("⚠️ تم تهيئة Firebase مسبقًا")
                else:
                    raise

    # ... (ابقاء باقي الدوال كما هي دون تغيير)
    def save_user_data(self, user_id, data):
        """حفظ بيانات المستخدم"""
        try:
            self.ref.child('users').child(str(user_id)).set(data)
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ البيانات: {str(e)}")
            return False

    def get_user_data(self, user_id):
        """جلب بيانات المستخدم"""
        try:
            return self.ref.child('users').child(str(user_id)).get() or {}
        except Exception as e:
            logger.error(f"❌ فشل جلب البيانات: {str(e)}")
            return {}

    def update_usage(self, user_id, chars_used):
        """تحديث الاستخدام"""
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
        """تحديث بيانات الصوت"""
        try:
            updates = {
                'voice': voice_data,
                'voice_cloned': True,
                'last_voice_update': {'.sv': 'timestamp'}
            }
            self.ref.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحديث الصوت: {str(e)}")
            return False
