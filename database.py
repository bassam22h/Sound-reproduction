import os
import firebase_admin
from firebase_admin import credentials, db
import logging

# إعداد التسجيل
logger = logging.getLogger(__name__)

# تهيئة اتصال Firebase (بنمط Singleton)
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate({
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
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL') or 'https://copy-sounds-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        return db.reference()
    except Exception as e:
        logger.error(f"فشل تهيئة Firebase: {str(e)}")
        raise

firebase_db = initialize_firebase()

# دالة مساعدة للتعامل مع المستخدمين
def get_user_ref(user_id):
    return firebase_db.child('users').child(str(user_id))

def get_user_data(user_id):
    try:
        user_ref = get_user_ref(user_id)
        data = user_ref.get()
        if data:
            return data
        
        # إنشاء مستخدم جديد إذا لم يكن موجوداً
        new_user = {
            'trials': int(os.getenv('DEFAULT_TRIALS', 2)),
            'characters_used': 0,
            'voice_id': None,
            'is_premium': False,
            'created_at': {'.sv': 'timestamp'},
            'last_updated': {'.sv': 'timestamp'}
        }
        user_ref.set(new_user)
        return new_user
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {str(e)}")
        return None

def update_user_data(user_id, data):
    try:
        data['last_updated'] = {'.sv': 'timestamp'}
        get_user_ref(user_id).update(data)
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث بيانات المستخدم: {str(e)}")
        return False

def save_voice_id(user_id, voice_id):
    return update_user_data(user_id, {'voice_id': voice_id})

def get_voice_id(user_id):
    user_data = get_user_data(user_id)
    return user_data.get('voice_id') if user_data else None

def decrement_trials(user_id):
    try:
        user_ref = get_user_ref(user_id)
        current_trials = user_ref.child('trials').get() or 0
        user_ref.update({
            'trials': current_trials - 1,
            'last_updated': {'.sv': 'timestamp'}
        })
        return True
    except Exception as e:
        logger.error(f"خطأ في إنقاص المحاولات: {str(e)}")
        return False

def update_characters_used(user_id, chars_count):
    try:
        user_ref = get_user_ref(user_id)
        current_chars = user_ref.child('characters_used').get() or 0
        user_ref.update({
            'characters_used': current_chars + chars_count,
            'last_used': {'.sv': 'timestamp'},
            'last_updated': {'.sv': 'timestamp'}
        })
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث الأحرف المستخدمة: {str(e)}")
        return False
