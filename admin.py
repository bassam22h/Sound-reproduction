import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self, firebase, premium_manager):
        self.firebase = firebase
        self.premium = premium_manager
        self.ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
        logger.info(f"المشرفون المعتمدون: {self.ADMIN_IDS}")

    def is_admin(self, user_id):
        return user_id in self.ADMIN_IDS

    def get_dashboard(self):
        """لوحة تحكم المشرفين"""
        buttons = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 تفعيل اشتراك", callback_data="admin_activate")],
            [InlineKeyboardButton("📢 إشعار عام", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search")]
        ]
        return InlineKeyboardMarkup(buttons)

    def get_stats(self):
        """إحصائيات البوت"""
        users = self.firebase.ref.child('users').get() or {}
        premium_users = sum(1 for u in users.values() if u.get('premium', {}).get('is_premium', False))
    
        return {
            'total_users': len(users),
            'premium_users': premium_users,
            'total_requests': sum(u.get('usage', {}).get('total_chars', 0) for u in users.values())
        }
        return (
            f"📈 *إحصائيات البوت*\n\n"
            f"👥 المستخدمون: {stats['total']}\n"
            f"💎 المميزون: {stats['premium']}\n"
            f"📨 الطلبات: {stats['active']}"
        )

    def prepare_broadcast(self, update, context):
        """تهيئة إرسال إشعار عام"""
        context.user_data['action'] = 'broadcast'
        update.message.reply_text(
            "📢 أرسل الرسالة للإشعار العام:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
            ])
        )

    def send_broadcast(self, text):
        """تنفيذ البث للمستخدمين"""
        users = self.firebase.ref.child('users').get() or {}
        results = {'success': 0, 'failed': []}
        
        for user_id in users:
            try:
                self.firebase.send_message(user_id, text)
                results['success'] += 1
            except Exception as e:
                results['failed'].append(str(user_id))
                logger.error(f"فشل الإرسال لـ {user_id}: {str(e)}")
        
        return results
