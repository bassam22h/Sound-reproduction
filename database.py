import os
import firebase_admin
from firebase_admin import credentials, firestore
import json

# تهيئة Firebase باستخدام متغيرات البيئة
firebase_config = {
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
}

# Initialize Firebase
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

def get_user_data(user_id):
    doc_ref = db.collection('users').document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        # إنشاء مستخدم جديد بمحاولتين
        new_user = {
            'trials': int(os.getenv('DEFAULT_TRIALS', 2)),
            'characters_used': 0,
            'is_premium': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(new_user)
        return new_user

def update_user_data(user_id, data):
    db.collection('users').document(str(user_id)).update(data)

def decrement_trials(user_id):
    user_data = get_user_data(user_id)
    if user_data['trials'] > 0:
        update_user_data(user_id, {'trials': firestore.Increment(-1)})

def update_characters_used(user_id, chars_count):
    update_user_data(user_id, {
        'characters_used': firestore.Increment(chars_count),
        'last_used': firestore.SERVER_TIMESTAMP
    })
