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
        """تحميل معرّفات المشرفين"""
        admin_ids = []
        for admin_id in os.getenv('ADMIN_IDS', '').split(','):
            admin_id = admin_id.strip()
            if admin_id.isdigit():
                admin_ids.append(int(admin_id))
            elif admin_id:
                logger.warning(f"⚠️ معرف مشرف غير صحيح: {admin_id}")
        return admin_ids

    def _validate_admins(self):
        """التحقق من وجود مشرفين"""
        if not self.ADMIN_IDS:
            logger.warning("⚠️ لم يتم تعيين أي مشرفين! البوت لن يعمل بشكل صحيح بدون مشرفين")

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
        """جلب إحصائيات البوت"""
        try:
            users = self.firebase.ref.child('users').get() or {}
            stats = {
                'total_users': len(users),
                'premium_users': sum(1 for u in users.values() if isinstance(u, dict) and u.get('premium', {}).get('is_premium')),
                'active_today': sum(1 for u in users.values() if self._is_active_today(u)),
                'total_requests': sum(u.get('usage', {}).get('total_chars', 0) for u in users.values() if isinstance(u, dict))
            }
            return stats
        except Exception as e:
            logger.error(f"❌ فشل جلب الإحصائيات: {str(e)}", exc_info=True)
            return {'total_users': 0, 'premium_users': 0, 'active_today': 0, 'total_requests': 0}

    def _is_active_today(self, user_data):
        """التحقق من النشاط اليومي"""
        last_used = user_data.get('last_used')
        if isinstance(last_used, dict):
            return True
        try:
            return (datetime.now() - datetime.fromtimestamp(last_used)).total_seconds() < 86400
        except:
            return False

    def handle_admin_actions(self, update, context):
        """معالجة إجراءات المشرف"""
        query = update.callback_query
        query.answer()
        
        if not self.is_admin(query.from_user.id):
            query.edit_message_text("⛔ ليس لديك صلاحية الوصول إلى هذه اللوحة", parse_mode=ParseMode.HTML)
            return
            
        action = query.data.split('_')[1]
        try:
            if action == "stats":
                self._show_stats(query, context)
            elif action == "activate":
                self._start_activation(query, context)
            elif action == "broadcast":
                self._start_broadcast(query, context)
            elif action == "user_info":
                self._start_user_info(query, context)
            elif action == "close":
                query.delete_message()
            elif action == "cancel":
                self._cancel_action(query, context)
        except Exception as e:
            logger.error(f"فشل معالجة إجراء المشرف: {str(e)}", exc_info=True)
            query.edit_message_text("❌ حدث خطأ أثناء معالجة طلبك", parse_mode=ParseMode.HTML)

    def _show_stats(self, query, context):
        """عرض الإحصائيات"""
        stats = self.get_stats()
        message = (
            "<b>📊 إحصائيات البوت</b>\n\n"
            f"• 👥 <code>المستخدمون: {stats['total_users']}</code>\n"
            f"• 💎 <code>المميزون: {stats['premium_users']}</code>\n"
            f"• 🔄 <code>النشطون اليوم: {stats['active_today']}</code>\n"
            f"• 📨 <code>إجمالي الأحرف: {stats['total_requests']:,}</code>"
        )
        query.edit_message_text(
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_admin_dashboard()
        )

    def _start_activation(self, query, context):
        """بدء تفعيل اشتراك"""
        context.user_data['admin_action'] = 'activate'
        query.edit_message_text(
            "✍️ أرسل <b>معرف المستخدم</b> لتفعيل الاشتراك:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« إلغاء", callback_data="admin_cancel")]])
        )

    def _start_broadcast(self, query, context):
        """بدء بث إشعار"""
        context.user_data['admin_action'] = 'broadcast'
        query.edit_message_text(
            "📩 أرسل الرسالة التي تريد بثها <b>لجميع المستخدمين</b>:\n\n"
            "⚠️ يمكنك استخدام تنسيق HTML:\n"
            "<code>&lt;b&gt;عريض&lt;/b&gt; &lt;i&gt;مائل&lt;/i&gt; &lt;a href='example.com'&gt;رابط&lt;/a&gt;</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« إلغاء", callback_data="admin_cancel")]])
        )

    def _process_broadcast(self, update, message):
        """معالجة البث العام"""
        try:
            users = self.firebase.ref.child('users').get() or {}
            if not users:
                update.message.reply_text("⚠️ لا يوجد مستخدمون لإرسال الإشعار", parse_mode=ParseMode.HTML)
                return

            total = len(users)
            progress_msg = update.message.reply_text(
                f"جاري إرسال الإشعار لـ {total} مستخدم...\n\n"
                f"✅ تم إرسالها لـ 0 مستخدم\n"
                f"❌ فشل إرسالها لـ 0 مستخدم",
                parse_mode=ParseMode.HTML
            )

            success = 0
            failed_users = []
            for i, (uid, user_data) in enumerate(users.items(), 1):
                try:
                    if not user_data.get('premium', {}).get('is_premium') and not user_data.get('voice', {}).get('voice_id'):
                        failed_users.append(str(uid))
                        continue
                        
                    update.message.bot.send_message(
                        chat_id=uid,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                    success += 1
                except Exception as e:
                    failed_users.append(str(uid))
                    logger.warning(f"فشل إرسال الإشعار لـ {uid}: {str(e)}")

                if i % 10 == 0 or i == total:
                    progress_msg.edit_text(
                        f"جاري إرسال الإشعار لـ {total} مستخدم...\n\n"
                        f"✅ تم إرسالها لـ {success} مستخدم\n"
                        f"❌ فشل إرسالها لـ {len(failed_users)} مستخدم\n"
                        f"📊 إكتمل: {(i/total)*100:.1f}%",
                        parse_mode=ParseMode.HTML
                    )

            result_msg = (
                "<b>📊 نتيجة البث العام</b>\n\n"
                f"• ✅ تم الإرسال بنجاح: <code>{success}</code>\n"
                f"• ❌ فشل الإرسال: <code>{len(failed_users)}</code>\n"
                f"• 📨 إجمالي المستهدفين: <code>{total}</code>"
            )
            update.message.reply_text(result_msg, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"فشل كامل في عملية البث: {str(e)}", exc_info=True)
            update.message.reply_text("❌ حدث خطأ جسيم أثناء عملية البث", parse_mode=ParseMode.HTML)

    def _process_user_info(self, update, user_id_str):
        """عرض معلومات المستخدم"""
        try:
            user_id = int(user_id_str)
            user_data = self.firebase.get_user_data(user_id) or {}
            
            msg = (
                "<b>📋 معلومات المستخدم</b>\n\n"
                f"• 🆔 المعرف: <code>{user_id}</code>\n"
                f"• 👤 الاسم: <code>{user_data.get('full_name', 'غير معروف')}</code>\n"
                f"• 📛 اليوزر: @{user_data.get('username', 'غير متوفر')}\n"
                f"• 💎 الحالة: <code>{'مميز ✅' if user_data.get('premium', {}).get('is_premium') else 'عادي ⚠️'}</code>\n"
                f"• 📝 الأحرف المستخدمة: <code>{user_data.get('usage', {}).get('total_chars', 0):,}</code>\n"
                f"• 🎤 صوت مستنسخ: <code>{'نعم' if user_data.get('voice', {}).get('voice_id') else 'لا'}</code>\n"
                f"• 🕒 آخر نشاط: <code>{self._format_last_active(user_data)}</code>\n"
                f"• 📅 تاريخ التسجيل: <code>{self._format_join_date(user_data)}</code>"
            )
            update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            
        except ValueError:
            update.message.reply_text("⚠️ يجب إدخال <b>معرف مستخدم</b> صحيح (أرقام فقط)", parse_mode=ParseMode.HTML)

    def _format_last_active(self, user_data):
        """تنسيق تاريخ آخر نشاط"""
        last_used = user_data.get('last_used')
        if isinstance(last_used, dict):
            return "مستخدم نشط الآن"
        try:
            delta = datetime.now() - datetime.fromtimestamp(last_used)
            if delta.days == 0:
                if delta.seconds < 60: return "منذ ثواني"
                elif delta.seconds < 3600: return f"منذ {delta.seconds//60} دقيقة"
                else: return f"منذ {delta.seconds//3600} ساعة"
            elif delta.days < 7: return f"منذ {delta.days} يوم"
            else: return datetime.fromtimestamp(last_used).strftime('%Y-%m-%d')
        except:
            return "وقت غير معروف"

    def _format_join_date(self, user_data):
        """تنسيق تاريخ التسجيل"""
        join_date = user_data.get('first_join')
        if isinstance(join_date, dict):
            return datetime.now().strftime('%Y-%m-%d')
        try:
            return datetime.fromtimestamp(join_date).strftime('%Y-%m-%d')
        except:
            return "غير معروف"
