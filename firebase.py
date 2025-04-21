import os
import firebase_admin
from firebase_admin import credentials, db

class FirebaseManager:
    def __init__(self):
        self.cred = self._get_firebase_credentials()
        if not firebase_admin._apps:
            firebase_admin.initialize_app(self.cred, {
                'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
            })
        self.ref = db.reference('/')
        
    def _get_firebase_credentials(self):
        """تهيئة بيانات اعتماد Firebase من متغيرات البيئة"""
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
        
    def save_user_data(self, user_id, data):
        """حفظ بيانات المستخدم (النسخة المحدثة)"""
        self.ref.child('users').child(str(user_id)).set(data)
        
    def get_user_data(self, user_id):
        """الحصول على جميع بيانات المستخدم"""
        return self.ref.child('users').child(str(user_id)).get()
        
    def update_usage(self, user_id, chars_used):
        """تحديث الاستخدام (النسخة المحدثة)"""
        updates = {
            'usage/total_chars': db.Increment(chars_used),
            'last_used': {'.sv': 'timestamp'}
        }
        self.ref.child('users').child(str(user_id)).update(updates)
        
    def update_voice_clone(self, user_id, voice_data):
        """تحديث بيانات الصوت المستنسخ"""
        updates = {
            'voice': voice_data,
            'voice_cloned': True,
            'last_voice_update': {'.sv': 'timestamp'}
        }
        self.ref.child('users').child(str(user_id)).update(updates)
        
    def activate_premium(self, user_id, premium_data):
        """تفعيل الاشتراك المميز"""
        self.ref.child('users').child(str(user_id)).child('premium').update(premium_data)
        
    def get_all_users(self):
        """الحصول على قائمة جميع المستخدمين"""
        return self.ref.child('users').get() or {}
