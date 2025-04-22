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
        logger.info(f"✅ تم تهيئة لوحة المشرفين \| عدد المشرفين: {len(self\.ADMIN_IDS)}")

    def _load_admin_ids(self):
        """تحميل معرّفات المشرفين مع التصفية والتحقق"""
        admin_ids = []
        for admin_id in os.getenv('ADMIN_IDS', '').split(','):
            admin_id = admin_id.strip()
            if admin_id.isdigit():
                admin_ids.append(int(admin_id))
            elif admin_id:
                logger.warning(f"⚠️ معرف مشرف غير صحيح: {admin_id}")
        return admin_ids

    def _validate_admins(self):
        """التحقق من وجود مشرفين مع تسجيل تحذير واضح"""
        if not self.ADMIN_IDS:
            logger.warning("⚠️ لم يتم تعيين أي مشرفين\! البوت لن يعمل بشكل صحيح بدون مشرفين")

    def is_admin(self, user_id):
        """التحقق من الصلاحية مع تسجيل مفصل"""
        is_admin = user_id in self.ADMIN_IDS
        if not is_admin:
            logger.warning(f"⚠️ محاولة وصول غير مصرح بها من المستخدم: {user_id}")
        return is_admin

    def get_admin_dashboard(self):
        """إنشاء لوحة تحكم متكاملة مع تحسين التنسيق"""
        buttons = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 تفعيل اشتراك", callback_data="admin_activate")],
            [InlineKeyboardButton("📢 إشعار عام", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔍 تفاصيل مستخدم", callback_data="admin_user_info")],
            [InlineKeyboardButton("🚪 إغلاق اللوحة", callback_data="admin_close")]
        ]
        return InlineKeyboardMarkup(buttons)

    def get_stats(self):
        """جلب الإحصائيات مع معالجة شاملة للأخطاء"""
        try:
            users = self.firebase.ref.child('users').get() or {}
            premium_count = 0
            active_today = 0
            total_chars = 0
            
            for user_id, user_data in users.items():
                if isinstance(user_data, dict):
                    # حساب المستخدمين المميزين
                    if user_data.get('premium', {}).get('is_premium', False):
                        premium_count += 1
                    
                    # حساب النشطاء اليوم
                    if self._is_active_today(user_data):
                        active_today += 1
                    
                    # حساب إجمالي الأحرف
                    total_chars += user_data.get('usage', {}).get('total_chars', 0)
            
            return {
                'total_users': len(users),
                'premium_users': premium_count,
                'active_today': active_today,
                'total_requests': total_chars
            }
        except Exception as e:
            logger.error(f"❌ فشل جلب الإحصائيات: {str(e)}", exc_info=True)
            return {
                'total_users': 0,
                'premium_users': 0,
                'active_today': 0,
                'total_requests': 0
            }

    def _is_active_today(self, user_data):
        """تحسين دقة التحقق من النشاط اليومي"""
        last_used = user_data.get('last_used')
        if not last_used:
            return False
            
        if isinstance(last_used, dict):  # Firebase timestamp
            return True
            
        try:
            last_active = datetime.fromtimestamp(last_used)
            return (datetime.now() - last_active).total_seconds() < 86400
        except:
            return False

    def handle_admin_actions(self, update, context):
        """معالجة إجراءات المشرف مع تحسينات الأمان"""
        query = update.callback_query
        query.answer()  # إعلام المستخدم بأن الإجراء تم استلامه
        
        if not self.is_admin(query.from_user.id):
            query.edit_message_text("⛔ ليس لديك صلاحية الوصول إلى هذه اللوحة", parse_mode=ParseMode.MARKDOWN_V2)
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
            query.edit_message_text("❌ حدث خطأ أثناء معالجة طلبك", parse_mode=ParseMode.MARKDOWN_V2)

    def _show_stats(self, query, context):
        """عرض الإحصائيات مع تنسيق محسن"""
        stats = self.get_stats()
        message = (
            "📊 \*إحصائيات البوت\*\n\n"
            f"• 👥 المستخدمون: `{stats['total_users']}`\n"
            f"• 💎 المميزون: `{stats['premium_users']}`\n"
            f"• 🔄 النشطون اليوم: `{stats['active_today']}`\n"
            f"• 📨 إجمالي الأحرف: `{stats['total_requests']:,}`"
        )
        query.edit_message_text(
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=self.get_admin_dashboard()
        )

    def _start_activation(self, query, context):
        """بدء عملية التفعيل مع تحسينات التدفق"""
        context.user_data['admin_action'] = 'activate'
        query.edit_message_text(
            "✍️ أرسل \*معرف المستخدم\* لتفعيل الاشتراك:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _start_broadcast(self, query, context):
        """بدء عملية البث مع توجيهات أوضح"""
        context.user_data['admin_action'] = 'broadcast'
        query.edit_message_text(
            "📩 أرسل الرسالة التي تريد بثها \*لجميع المستخدمين\*:\n\n"
            "⚠️ يمكنك استخدام تنسيق MarkdownV2:\n"
            "`\*عريض\*` `\_مائل\_` `\[رابط\]\(example\.com\)`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _start_user_info(self, query, context):
        """بدء طلب معلومات المستخدم مع واجهة محسنة"""
        context.user_data['admin_action'] = 'user_info'
        query.edit_message_text(
            "🆔 أرسل \*معرف المستخدم\* لعرض معلوماته:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« إلغاء", callback_data="admin_cancel")]
            ])
        )

    def _cancel_action(self, query, context):
        """إلغاء الإجراء الحالي مع تنظيف البيانات"""
        context.user_data.pop('admin_action', None)
        query.edit_message_text(
            "تم إلغاء الإجراء",
            reply_markup=self.get_admin_dashboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    def process_admin_message(self, update, context):
        """معالجة رسائل المشرف مع تحسينات التحقق"""
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            update.message.reply_text("⛔ ليس لديك صلاحية الوصول إلى هذه الميزة", parse_mode=ParseMode.MARKDOWN_V2)
            return
            
        action = context.user_data.get('admin_action')
        if not action:
            return
            
        text = update.message.text.strip()
        if not text:
            update.message.reply_text("⚠️ يرجى إرسال محتوى صالح", parse_mode=ParseMode.MARKDOWN_V2)
            return
            
        try:
            if action == 'activate':
                self._process_activation(update, text)
            elif action == 'broadcast':
                self._process_broadcast(update, text)
            elif action == 'user_info':
                self._process_user_info(update, text)
        except Exception as e:
            logger.error(f"فشل معالجة رسالة المشرف: {str(e)}", exc_info=True)
            update.message.reply_text("❌ حدث خطأ أثناء معالجة طلبك", parse_mode=ParseMode.MARKDOWN_V2)

    def _process_activation(self, update, user_id_str):
        """معالجة التفعيل مع تحسينات التحقق"""
        try:
            user_id = int(user_id_str)
            if self.premium.activate_premium(user_id, update.effective_user.id):
                update.message.reply_text(
                    f"✅ تم تفعيل الاشتراك المميز للمستخدم `{user_id}`",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                update.message.reply_text("❌ فشل في تفعيل الاشتراك", parse_mode=ParseMode.MARKDOWN_V2)
        except ValueError:
            update.message.reply_text(
                "⚠️ يجب إدخال \*معرف مستخدم\* صحيح \(أرقام فقط\)",
                parse_mode=ParseMode.MARKDOWN_V2
            )

    def _process_broadcast(self, update, message):
        """معالجة البث مع تحسينات الأداء والمراسلة"""
        try:
            users = self.firebase.ref.child('users').get() or {}
            if not users:
                update.message.reply_text("⚠️ لا يوجد مستخدمون لإرسال الإشعار", parse_mode=ParseMode.MARKDOWN_V2)
                return
                
            total = len(users)
            success = 0
            failed_users = []
            
            # إرسال أول رسالة تحضيرية
            progress_msg = update.message.reply_text(
                f"جاري إرسال الإشعار لـ {total} مستخدم\.\.\.\n\n"
                f"✅ تم إرسالها لـ 0 مستخدم\n"
                f"❌ فشل إرسالها لـ 0 مستخدم",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            for i, (uid, user_data) in enumerate(users.items(), 1):
                try:
                    # التعديل المطلوب: التحقق من اشتراك premium أو voice_id
                    if not user_data.get('premium', {}).get('is_premium') and not user_data.get('voice', {}).get('voice_id'):
                        failed_users.append(str(uid))
                        continue
                        
                    update.message.bot.send_message(
                        chat_id=uid,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
                    success += 1
                except Exception as e:
                    failed_users.append(str(uid))
                    logger.warning(f"فشل إرسال الإشعار لـ {uid}: {str(e)}")
                
                # تحديث حالة التقدم كل 10 مستخدمين
                if i % 10 == 0 or i == total:
                    try:
                        progress_msg.edit_text(
                            f"جاري إرسال الإشعار لـ {total} مستخدم\.\.\.\n\n"
                            f"✅ تم إرسالها لـ {success} مستخدم\n"
                            f"❌ فشل إرسالها لـ {len(failed_users)} مستخدم\n"
                            f"📊 إكتمل: {(i/total)*100:.1f}%",
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    except:
                        pass
            
            # إرسال النتيجة النهائية
            result_msg = (
                f"📊 \*نتيجة البث العام\*\n\n"
                f"• ✅ تم الإرسال بنجاح: `{success}`\n"
                f"• ❌ فشل الإرسال: `{len(failed_users)}`\n"
                f"• 📨 إجمالي المستهدفين: `{total}`"
            )
            
            if failed_users:
                result_msg += f"\n\n📋 قائمة المعرفات الفاشلة:\n`{', '.join(failed_users[:50])}`" + (
                    "\.\.\." if len(failed_users) > 50 else ""
                )
            
            update.message.reply_text(
                result_msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except Exception as e:
            logger.error(f"فشل كامل في عملية البث: {str(e)}", exc_info=True)
            update.message.reply_text("❌ حدث خطأ جسيم أثناء عملية البث", parse_mode=ParseMode.MARKDOWN_V2)

    def _format_last_active(self, user_data):
        """تنسيق وقت النشاط الأخير مع تحسينات الدقة"""
        last_used = user_data.get('last_used')
        if not last_used:
            return "لم يستخدم البوت بعد"
            
        if isinstance(last_used, dict):  # Firebase timestamp
            return "مستخدم نشط الآن"
            
        try:
            last_active = datetime.fromtimestamp(last_used)
            delta = datetime.now() - last_active
            
            if delta.days == 0:
                if delta.seconds < 60:
                    return "منذ ثواني"
                elif delta.seconds < 3600:
                    return f"منذ {delta.seconds//60} دقيقة"
                else:
                    return f"منذ {delta.seconds//3600} ساعة"
            elif delta.days < 7:
                return f"منذ {delta.days} يوم"
            else:
                return last_active.strftime('%Y\-%m\-%d')
        except:
            return "وقت غير معروف"

    def _process_user_info(self, update, user_id_str):
        """معالجة معلومات المستخدم مع عرض مفصل"""
        try:
            user_id = int(user_id_str)
            user_data = self.firebase.get_user_data(user_id)
            if not user_data:
                update.message.reply_text("⚠️ لا يوجد مستخدم بهذا المعرف", parse_mode=ParseMode.MARKDOWN_V2)
                return
                
            premium = user_data.get('premium', {})
            usage = user_data.get('usage', {})
            
            msg = (
                f"📋 \*معلومات المستخدم\*\n\n"
                f"• 🆔 المعرف: `{user_id}`\n"
                f"• 👤 الاسم: `{user_data.get('full_name', 'غير معروف')}`\n"
                f"• 📛 اليوزر: @{user_data.get('username', 'غير متوفر')}\n"
                f"• 💎 الحالة: `{'مميز ✅' if premium.get('is_premium') else 'عادي ⚠️'}`\n"
                f"• 📝 الأحرف المستخدمة: `{usage.get('total_chars', 0):,}`\n"
                f"• 🎤 صوت مستنسخ: `{'نعم' if user_data.get('voice', {}).get('voice_id') else 'لا'}`\n"
                f"• 🕒 آخر نشاط: `{self._format_last_active(user_data)}`\n"
                f"• 📅 تاريخ التسجيل: `{datetime.fromtimestamp(user_data.get('first_join', {}).get('.sv', 0)).strftime('%Y\-%m\-%d') if isinstance(user_data.get('first_join'), dict) else 'غير معروف'}`"
            )
            
            update.message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except ValueError:
            update.message.reply_text(
                "⚠️ يجب إدخال \*معرف مستخدم\* صحيح \(أرقام فقط\)",
                parse_mode=ParseMode.MARKDOWN_V2
            )
