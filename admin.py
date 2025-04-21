import os
from telegram import ParseMode

class AdminPanel:
    def __init__(self, firebase):
        self.firebase = firebase
        self.ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_USER_ID', '').split(',')]
        
    def is_admin(self, user_id):
        return user_id in self.ADMIN_IDS
        
    def get_stats(self):
        users_ref = self.firebase.ref.child('users')
        return {
            'total_users': len(users_ref.get() or {}),
            'total_requests': sum(
                user.get('usage', {}).get('requests', 0)
                for user in (users_ref.get() or {}).values()
            )
        }
        
    def activate_premium(self, user_id, months=1):
        if not self.is_admin(user_id):
            return False
            
        user_ref = self.firebase.ref.child('users').child(str(user_id))
        user_ref.update({
            'premium': True,
            'premium_expiry': firebase.database.ServerValue.TIMESTAMP + months*30*24*60*60
        })
        return True
