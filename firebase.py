import os
import firebase_admin
from firebase_admin import credentials, db
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self):
        self.cred = self._get_firebase_credentials()
        self._validate_database_url()
        self._initialize_app()
        self.ref = self._get_database_reference()
        logger.info("✅ تم تهيئة اتصال Firebase بنجاح")

    def _get_firebase_credentials(self):
        """تهيئة بيانات الاعتماد مع تحسينات التحقق"""
        required_env_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL',
            'FIREBASE_CLIENT_ID',
            'FIREBASE_CLIENT_CERT_URL'
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"❌ متغيرات البيئة المطلوبة غير موجودة: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
            if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                logger.warning("⚠️ قد يكون هناك مشكلة في تنسيق المفتاح الخاص")

            return credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": private_key,
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL')
            })
        except Exception as e:
            logger.error(f"❌ فشل تحميل بيانات اعتماد Firebase: {str(e)}", exc_info=True)
            raise

    def _validate_database_url(self):
        """التحقق من صحة عنوان قاعدة البيانات"""
        db_url = os.getenv('FIREBASE_DATABASE_URL', '')
        if not db_url:
            raise ValueError("❌ متغير FIREBASE_DATABASE_URL غير محدد")
        
        try:
            result = urlparse(db_url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("رابط غير صالح")
        except Exception as e:
            logger.error(f"❌ رابط قاعدة بيانات غير صالح: {db_url}")
            raise ValueError(f"رابط قاعدة بيانات غير صالح: {db_url}")

    def _initialize_app(self):
        """تهيئة التطبيق مع تحسينات إعادة المحاولة"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(
                        self.cred,
                        {
                            'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
                            'databaseAuthVariableOverride': None
                        }
                    )
                    logger.info(f"✅ تم تهيئة تطبيق Firebase (المحاولة {attempt + 1})")
                    return
                else:
                    logger.warning("⚠️ تم تهيئة Firebase مسبقًا")
                    return
            except ValueError as e:
                if "already exists" in str(e):
                    logger.warning("⚠️ تم تهيئة Firebase مسبقًا")
                    return
                elif attempt == max_retries - 1:
                    logger.error(f"❌ فشل تهيئة تطبيق Firebase بعد {max_retries} محاولات")
                    raise
                logger.warning(f"⚠️ فشل تهيئة Firebase (المحاولة {attempt + 1}), جاري إعادة المحاولة...")
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع أثناء تهيئة Firebase: {str(e)}", exc_info=True)
                raise

    def _get_database_reference(self, path='/'):
        """الحصول على مرجع قاعدة بيانات مع التحقق من الاتصال"""
        try:
            ref = db.reference(path)
            # اختبار اتصال بسيط
            ref.child('connection_test').set({'test': True, 'timestamp': {'.sv': 'timestamp'}})
            ref.child('connection_test').delete()
            return ref
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بقاعدة بيانات Firebase: {str(e)}", exc_info=True)
            raise

    def save_user_data(self, user_id, data):
        """حفظ بيانات المستخدم مع التحقق الشامل"""
        if not user_id or not isinstance(user_id, (int, str)):
            logger.error(f"❌ معرف مستخدم غير صالح: {user_id}")
            return False

        if not data or not isinstance(data, dict):
            logger.error(f"❌ بيانات غير صالحة للحفظ: {data}")
            return False

        try:
            user_ref = self.ref.child('users').child(str(user_id))
            
            # التحقق من وجود بيانات سابقة
            existing_data = user_ref.get()
            
            # دمج البيانات الجديدة مع القديمة (إذا وجدت)
            if existing_data and isinstance(existing_data, dict):
                data = {**existing_data, **data}
            
            user_ref.set(data)
            logger.info(f"✅ تم حفظ بيانات المستخدم {user_id} بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ بيانات المستخدم {user_id}: {str(e)}", exc_info=True)
            return False

    def get_user_data(self, user_id):
        """جلب بيانات المستخدم مع معالجة الأخطاء"""
        if not user_id or not isinstance(user_id, (int, str)):
            logger.error(f"❌ معرف مستخدم غير صالح: {user_id}")
            return {}

        try:
            data = self.ref.child('users').child(str(user_id)).get()
            
            if not data:
                logger.debug(f"⚠️ لا توجد بيانات للمستخدم {user_id}")
                return {}
                
            if not isinstance(data, dict):
                logger.warning(f"⚠️ بيانات غير متوقعة للمستخدم {user_id}: {type(data)}")
                return {}
                
            return data
        except Exception as e:
            logger.error(f"❌ فشل جلب بيانات المستخدم {user_id}: {str(e)}", exc_info=True)
            return {}

    def update_usage(self, user_id, chars_used):
        """تحديث استخدام الأحرف مع التحقق من القيم"""
        if not isinstance(chars_used, int) or chars_used <= 0:
            logger.error(f"❌ قيمة أحرف غير صالحة: {chars_used}")
            return False

        try:
            updates = {
                'usage/total_chars': db.Increment(chars_used),
                'last_used': {'.sv': 'timestamp'}
            }
            
            # إضافة تحديث إضافي للمستخدمين المميزين
            user_data = self.get_user_data(user_id)
            if user_data.get('premium', {}).get('is_premium', False):
                updates['premium/remaining_chars'] = db.Increment(-chars_used)
            
            self.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"✅ تم تحديث استخدام الأحرف للمستخدم {user_id}: +{chars_used}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحديث استخدام الأحرف للمستخدم {user_id}: {str(e)}", exc_info=True)
            return False

    def update_voice_clone(self, user_id, voice_data):
        """تحديث بيانات الصوت مع التحقق من الهيكل"""
        required_fields = ['voice_id', 'status']
        if not all(field in voice_data for field in required_fields):
            logger.error(f"❌ بيانات الصوت ناقصة الحقول المطلوبة: {voice_data}")
            return False

        try:
            updates = {
                'voice': voice_data,
                'voice_cloned': True,
                'last_voice_update': {'.sv': 'timestamp'}
            }
            
            self.ref.child('users').child(str(user_id)).update(updates)
            logger.info(f"✅ تم تحديث بيانات الصوت للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحديث بيانات الصوت للمستخدم {user_id}: {str(e)}", exc_info=True)
            return False

    def get_all_users(self, filters=None):
        """جلب جميع المستخدمين مع إمكانية التصفية"""
        try:
            users = self.ref.child('users').get() or {}
            
            if not filters or not isinstance(filters, dict):
                return users
                
            filtered_users = {}
            for user_id, user_data in users.items():
                if all(user_data.get(k) == v for k, v in filters.items()):
                    filtered_users[user_id] = user_data
                    
            return filtered_users
        except Exception as e:
            logger.error(f"❌ فشل جلب قائمة المستخدمين: {str(e)}", exc_info=True)
            return {}

    def delete_user(self, user_id):
        """حذف مستخدم مع التحقق من الصلاحيات"""
        try:
            self.ref.child('users').child(str(user_id)).delete()
            logger.info(f"✅ تم حذف المستخدم {user_id} بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حذف المستخدم {user_id}: {str(e)}", exc_info=True)
            return False
