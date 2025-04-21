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
        
    def update_voice_clone(self, user_id, voice_data):
        """تحديث أو تغيير الصوت المستنسخ مع حذف القديم"""
        user_ref = self.ref.child('users').child(str(user_id))
        
        # حذف الصوت القديم إذا موجود
        user_ref.child('voice').delete()
        
        # إضافة الصوت الجديد
        user_ref.child('voice').set(voice_data)
        
        # تحديث حالة الاستنساخ
        user_ref.update({
            'voice_cloned': True,
            'last_voice_update': {'.sv': 'timestamp'}
        })
        
        return True
        
    def _get_firebase_credentials(self):
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
        
    def save_user_data(self, user_id, data_type, data):
        user_ref = self.ref.child('users').child(str(user_id))
        user_ref.child(data_type).set(data)
        
    def get_user_data(self, user_id):
        return self.ref.child('users').child(str(user_id)).get()
        
    def increment_usage(self, user_id, chars_used):
        user_ref = self.ref.child('users').child(str(user_id))
        user_ref.child('usage').child('chars_used').transaction(
            lambda current: (current or 0) + chars_used)
        user_ref.child('usage').child('requests').transaction(
            lambda current: (current or 0) + 1)
