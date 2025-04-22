import firebase_admin
from firebase_admin import credentials, firestore
import os

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": os.getenv("FB_TYPE"),
        "project_id": os.getenv("FB_PROJECT_ID"),
        "private_key_id": os.getenv("FB_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FB_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FB_CLIENT_EMAIL"),
        "client_id": os.getenv("FB_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FB_CLIENT_CERT_URL")
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()

class FirebaseDB:
    def save_user(self, user_id, username):
        ref = db.collection("users").document(str(user_id))
        if not ref.get().exists:
            ref.set({"id": user_id, "username": username or "-", "used": 0, "premium": False})

    def get_user(self, user_id):
        ref = db.collection("users").document(str(user_id)).get()
        return ref.to_dict() if ref.exists else None

    def update_usage(self, user_id, used):
        db.collection("users").document(str(user_id)).update({"used": used})

    def upgrade_user(self, user_id):
        ref = db.collection("users").document(str(user_id))
        if ref.get().exists:
            ref.update({"premium": True})
            return True
        return False

    def get_all_users(self):
        docs = db.collection("users").stream()
        return [doc.to_dict() for doc in docs]