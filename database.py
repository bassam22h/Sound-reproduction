import os
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError
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
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL'),
                "databaseURL": os.getenv('FIREBASE_DATABASE_URL')
            })
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        logger.error(f"فشل تهيئة Firebase: {str(e)}")
        raise

db = initialize_firebase()

# دالة مساعدة للتعامل مع المستندات
def get_user_ref(user_id):
    return db.collection('users').document(str(user_id))

def get_user_data(user_id):
    try:
        doc = get_user_ref(user_id).get()
        if doc.exists:
            return doc.to_dict()
        
        # إنشاء مستخدم جديد إذا لم يكن موجوداً
        new_user = {
            'trials': int(os.getenv('DEFAULT_TRIALS', 2)),
            'characters_used': 0,
            'voice_id': None,
            'is_premium': False,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        get_user_ref(user_id).set(new_user)
        return new_user
        
    except FirebaseError as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return None

def update_user_data(user_id, data):
    try:
        data['last_updated'] = firestore.SERVER_TIMESTAMP
        get_user_ref(user_id).update(data)
        return True
    except FirebaseError as e:
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
        user_ref.update({
            'trials': firestore.Increment(-1),
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        return True
    except FirebaseError as e:
        logger.error(f"خطأ في إنقاص المحاولات: {str(e)}")
        return False

def update_characters_used(user_id, chars_count):
    try:
        user_ref = get_user_ref(user_id)
        user_ref.update({
            'characters_used': firestore.Increment(chars_count),
            'last_used': firestore.SERVER_TIMESTAMP,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        return True
    except FirebaseError as e:
        logger.error(f"خطأ في تحديث الأحرف المستخدمة: {str(e)}")
        return False
