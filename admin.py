import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from firebase_admin import db

logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self, firebase, premium_manager):
        self.firebase = firebase
        self.premium = premium_manager
        self._load_admin_ids()
        logger.info(f"تم تهيئة لوحة المشرفين - المشرفون: {self.ADMIN_IDS}")

    def _load_admin_ids(self):
        """تحميل معرّفات المشرفين من متغيرات البيئة"""
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids if id.strip()]
        
    def is_admin(self, user_id):
        """التحقق من صلاحية المشرف"""
        return user_id in self.ADMIN_IDS

    def get_admin_dashboard(self):
        """إنشاء لوحة تحكم المشرفين"""
        buttons = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 تفعيل اشتراك", callback_data="admin_activate")],
            [InlineKeyboardButton("📢 إشعار عام", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔍 تفاصيل مستخدم", callback_data="admin_user_info")],
            [InlineKeyboardButton("🚪 إغلاق اللوحة", callback_data="admin_close")]
        ]
        return InlineKeyboardMarkup(buttons)

    def get_stats(self):
        """جمع الإحصائيات من Firebase"""
        users = self.firebase.ref.child('users').get() or {}
        stats = {
            'total_users': len(users),
            'premium_users': sum(1 for u in users.values() if u.get('premium', {}).get('is_premium', False)),
            'active_today': sum(1 for u in users.values() if self._is_active_today(u)),
            'total_requests': sum(u.get('usage', {}).get('total_chars', 0) for u in users.values())
        }
        return stats

    def _is_active_today(self, user_data):
        """التحقق من نشاط المستخدم اليوم"""
        from datetime import datetime
        last_used = user_data.get('last_used', 0)
        if isinstance(last_used, dict):  # Firebase timestamp
            return True  # نعتبره نشط إذا كان لديه timestamp
        return datetime.now().timestamp() - last_used < 86400

    def handle_admin_actions(self, update, context):
        """معالجة ضغطات أزرار المشرفين"""
        query = update.callback_query
        action = query.data.split('_')[1]
        
        if action == "stats":
            stats = self.get_stats()
            msg = (
                "📊 *إحصائيات البوت*\n\n"
                f"👥 المستخدمون: {stats['total_users']}\n"
                f"💎 المشتركون المميزون: {stats['premium_users']}\n"
                f"🔄 النشطون اليوم: {stats['active_today']}\n"
                f"📨 إجمالي الأحرف المستخدمة: {stats['total_requests']:,}"
            )
            query.edit_message_text(
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_admin_dashboard()
            )
            
        elif action == "activate":
            context.user_data['admin_action'] = 'activate'
            query.edit_message_text(
                "أرسل معرف المستخدم لتفعيل الاشتراك المميز:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
                ])
            )
            
        elif action == "broadcast":
            context.user_data['admin_action'] = 'broadcast'
            query.edit_message_text(
                "أرسل الرسالة التي تريد بثها لجميع المستخدمين:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
                ])
            )
            
        elif action == "user_info":
            context.user_data['admin_action'] = 'user_info'
            query.edit_message_text(
                "أرسل معرف المستخدم لرؤية تفاصيله:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
                ])
            )
            
        elif action == "cancel":
            self._cancel_action(context)
            query.edit_message_text(
                "تم الإلغاء",
                reply_markup=self.get_admin_dashboard()
            )
            
        elif action == "close":
            query.delete_message()

    def process_admin_message(self, update, context):
        """معالجة الرسائل النصية من المشرف"""
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            return
            
        action = context.user_data.get('admin_action')
        text = update.message.text
        
        if action == 'activate':
            self._process_activation(update, text)
            
        elif action == 'broadcast':
            self._process_broadcast(update, text)
            
        elif action == 'user_info':
            self._process_user_info(update, text)
            
        self._cancel_action(context)

    def _process_activation(self, update, user_id_str):
        """معالجة تفعيل الاشتراك"""
        try:
            target_user_id = int(user_id_str)
            if self.premium.activate_premium(target_user_id, update.effective_user.id):
                update.message.reply_text(
                    f"✅ تم تفعيل الاشتراك المميز للمستخدم {target_user_id}",
                    reply_markup=self.get_admin_dashboard()
                )
            else:
                update.message.reply_text(
                    "❌ فشل في التفعيل. تأكد من صحة المعرف",
                    reply_markup=self.get_admin_dashboard()
                )
        except ValueError:
            update.message.reply_text(
                "⚠️ يجب إدخال معرف مستخدم صحيح (أرقام فقط)",
                reply_markup=self.get_admin_dashboard()
            )

    def _process_broadcast(self, update, message):
        """تنفيذ عملية البث"""
        users = self.firebase.ref.child('users').get() or {}
        success = failed = 0
        
        for uid, user_data in users.items():
            try:
                update.message.bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"فشل البث لـ {uid}: {str(e)}")
                
        update.message.reply_text(
            f"✅ تم الإرسال لـ {success} مستخدم\n❌ فشل الإرسال لـ {failed} مستخدم",
            reply_markup=self.get_admin_dashboard()
        )

    def _process_user_info(self, update, user_id_str):
        """عرض معلومات المستخدم"""
        try:
            user_id = int(user_id_str)
            user_data = self.firebase.get_user_data(user_id) or {}
            
            if not user_data:
                update.message.reply_text("⚠️ لا يوجد مستخدم بهذا المعرف")
                return
                
            premium_status = "مميز ✅" if user_data.get('premium', {}).get('is_premium') else "عادي ⚠️"
            msg = (
                f"🆔 معرف المستخدم: {user_id}\n"
                f"💎 حالة الاشتراك: {premium_status}\n"
                f"📝 الأحرف المستخدمة: {user_data.get('usage', {}).get('total_chars', 0)}\n"
                f"🕒 آخر نشاط: {self._format_last_active(user_data)}"
            )
            
            update.message.reply_text(
                msg,
                reply_markup=self.get_admin_dashboard()
            )
        except ValueError:
            update.message.reply_text("⚠️ يجب إدخال معرف مستخدم صحيح")

    def _format_last_active(self, user_data):
        """تنسيق وقت آخر نشاط"""
        from datetime import datetime
        last_used = user_data.get('last_used')
        if isinstance(last_used, dict):  # Firebase timestamp
            return "اليوم"
        elif last_used:
            return datetime.fromtimestamp(last_used).strftime('%Y-%m-%d %H:%M')
        return "غير معروف"

    def _cancel_action(self, context):
        """إلغاء الإجراء الحالي"""
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
