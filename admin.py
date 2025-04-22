import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from firebase_admin import db
from datetime import datetime

logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self, firebase, premium_manager):
        self.firebase = firebase
        self.premium = premium_manager
        self.ADMIN_IDS = self._load_admin_ids()
        self._validate_admins()
        logger.info(f"✅ تم تهيئة لوحة المشرفين | عدد المشرفين: {len(self.ADMIN_IDS)}")

    def _load_admin_ids(self):
        """تحميل معرّفات المشرفين مع التصفية"""
        return [
            int(admin_id.strip()) 
            for admin_id in os.getenv('ADMIN_IDS', '').split(',') 
            if admin_id.strip().isdigit()
        ]

    def _validate_admins(self):
        """التحقق من وجود مشرفين"""
        if not self.ADMIN_IDS:
            logger.warning("⚠️ لم يتم تعيين أي مشرفين!")

    def is_admin(self, user_id):
        """التحقق من الصلاحية مع التسجيل"""
        is_admin = user_id in self.ADMIN_IDS
        if not is_admin:
            logger.warning(f"⚠️ محاولة وصول غير مصرح بها من المستخدم: {user_id}")
        return is_admin

    def get_admin_dashboard(self):
        """إنشاء لوحة التحكم كاملة"""
        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 تفعيل اشتراك", callback_data="admin_activate")],
            [InlineKeyboardButton("📢 إشعار عام", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔍 تفاصيل مستخدم", callback_data="admin_user_info")],
            [InlineKeyboardButton("🚪 إغلاق اللوحة", callback_data="admin_close")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_stats(self):
        """جلب الإحصائيات مع التعامل مع الأخطاء"""
        try:
            users = self.firebase.ref.child('users').get() or {}
            return {
                'total_users': len(users),
                'premium_users': sum(1 for u in users.values() if u.get('premium', {}).get('is_premium', False)),
                'active_today': sum(1 for u in users.values() if self._is_active_today(u)),
                'total_requests': sum(u.get('usage', {}).get('total_chars', 0) for u in users.values())
            }
        except Exception as e:
            logger.error(f"❌ فشل جلب الإحصائيات: {str(e)}")
            return {
                'total_users': 0,
                'premium_users': 0,
                'active_today': 0,
                'total_requests': 0
            }

    def _is_active_today(self, user_data):
        """التحقق من النشاط خلال 24 ساعة"""
        last_used = user_data.get('last_used')
        if isinstance(last_used, dict):  # Firebase timestamp
            return True
        return last_used and (datetime.now().timestamp() - last_used) < 86400

    def handle_admin_actions(self, update, context):
        """معالجة مركزية لجميع الإجراءات"""
        query = update.callback_query
        action = query.data.split('_')[1]

        if action == "stats":
            self._show_stats(query, context)
        elif action == "activate":
            self._start_activation(query, context)
        elif action == "broadcast":
            self._start_broadcast(query, context)
        elif action == "user_info":
            self._start_user_info(query, context)
        elif action == "cancel":
            self._cancel_action(query, context)
        elif action == "close":
            query.delete_message()

    def _show_stats(self, query, context):
        """عرض الإحصائيات"""
        stats = self.get_stats()
        message = (
            "📊 *الإحصائيات*\n\n"
            f"👥 المستخدمون: {stats['total_users']}\n"
            f"💎 المميزون: {stats['premium_users']}\n"
            f"🔄 النشطون اليوم: {stats['active_today']}\n"
            f"📨 إجمالي الأحرف: {stats['total_requests']:,}"
        )
        query.edit_message_text(
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_admin_dashboard()
        )

    def _start_activation(self, query, context):
        """بدء عملية التفعيل"""
        context.user_data['admin_action'] = 'activate'
        query.edit_message_text(
            "أرسل معرف المستخدم لتفعيل الاشتراك:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _start_broadcast(self, query, context):
        """بدء عملية البث"""
        context.user_data['admin_action'] = 'broadcast'
        query.edit_message_text(
            "أرسل الرسالة التي تريد بثها:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _start_user_info(self, query, context):
        """بدء طلب معلومات المستخدم"""
        context.user_data['admin_action'] = 'user_info'
        query.edit_message_text(
            "أرسل معرف المستخدم:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _cancel_action(self, query, context):
        """إلغاء الإجراء الحالي"""
        context.user_data.pop('admin_action', None)
        query.edit_message_text(
            "تم الإلغاء",
            reply_markup=self.get_admin_dashboard()
        )

    def process_admin_message(self, update, context):
        """معالجة رسائل المشرف"""
        action = context.user_data.get('admin_action')
        text = update.message.text

        if action == 'activate':
            self._process_activation(update, text)
        elif action == 'broadcast':
            self._process_broadcast(update, text)
        elif action == 'user_info':
            self._process_user_info(update, text)

        context.user_data.pop('admin_action', None)

    def _process_activation(self, update, user_id_str):
        try:
            user_id = int(user_id_str)
            # تجاوز جميع الشروط للمشرفين
            if self.premium.activate_premium(user_id, update.effective_user.id):
                update.message.reply_text(f"✅ تم تفعيل الاشتراك للمستخدم {user_id}")
            else:
                update.message.reply_text("❌ فشل في التفعيل")
        except ValueError:
            update.message.reply_text("⚠️ يجب إدخال معرف مستخدم صحيح")

    def _process_broadcast(self, update, message):
        users = self.firebase.ref.child('users').get() or {}
        success = failed = 0
    
        for uid in users.keys():
            try:
                # إرسال الرسالة بدون تحقق من الشروط
                update.message.bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode=None  # إلغاء Markdown للبث العام
                )
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"فشل البث لـ {uid}: {str(e)}")
    
        update.message.reply_text(f"✅ تم الإرسال لـ {success} مستخدم\n❌ فشل لـ {failed} مستخدم")

    def _process_user_info(self, update, user_id_str):
        try:
            user_id = int(user_id_str)
            user_data = self.firebase.get_user_data(user_id) or {}
        
            msg = (
                f"🆔 المعرف: {user_id}\n"
                f"💎 الحالة: {'مميز' if user_data.get('premium', {}).get('is_premium') else 'عادي'}\n"
                f"📊 الأحرف المستخدمة: {user_data.get('usage', {}).get('total_chars', 0)}\n"
                f"🎤 صوت مستنسخ: {'نعم' if user_data.get('voice_cloned') else 'لا'}"
            )
            update.message.reply_text(msg)
        except ValueError:
            update.message.reply_text("⚠️ يجب إدخال معرف صحيح")
