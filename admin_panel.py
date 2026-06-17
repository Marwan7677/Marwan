"""
پنل مدیریتی ربات
"""

from typing import Optional, List, Dict
from database import db
from ui_helpers import TextFormatter, KeyboardBuilder
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


class AdminPanel:
    """پنل مدیریتی ربات"""
    
    def __init__(self, admin_id: int):
        self.admin_id = admin_id

    def is_admin(self, user_id: int) -> bool:
        """بررسی اینکه آیا کاربر مدیر است"""
        return user_id == self.admin_id

    # ==================== آمار سیستم ====================
    def get_system_stats(self) -> Dict:
        """دریافت آمار سیستم"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # تعداد کاربران
        cursor.execute('SELECT COUNT(*) as count FROM users')
        total_users = cursor.fetchone()['count']
        
        # تعداد کاربران فعال امروز
        cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE DATE(created_at) = DATE('now')
        ''')
        new_users_today = cursor.fetchone()['count']
        
        # تعداد سفارشات
        cursor.execute('SELECT COUNT(*) as count FROM orders')
        total_orders = cursor.fetchone()['count']
        
        # کل درآمد از اشتراک‌ها
        cursor.execute('SELECT SUM(price) as total FROM subscriptions WHERE is_active = 1')
        total_revenue = cursor.fetchone()['total'] or 0
        
        # توزیع کاربران بر اساس تیر
        cursor.execute('''
            SELECT tier, COUNT(*) as count 
            FROM users 
            GROUP BY tier
            ORDER BY count DESC
        ''')
        tier_distribution = {row['tier']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'tier_distribution': tier_distribution
        }

    def get_stats_message(self) -> str:
        """دریافت پیام آمار"""
        stats = self.get_system_stats()
        
        text = """
📊 **آمار سیستم**

👥 **کاربران:**
  📈 کل کاربران: {total_users}
  ✨ کاربران جدید امروز: {new_users_today}

📋 **سفارشات:**
  🔹 کل سفارشات: {total_orders}

💰 **درآمد:**
  💵 کل درآمد فعال: {total_revenue:,.0f} تومان

📊 **توزیع تیرها:**
""".format(**stats)
        
        for tier, count in stats['tier_distribution'].items():
            text += f"  🔹 {tier}: {count} نفر\n"
        
        return text

    # ==================== مدیریت کاربران ====================
    def get_user_list(self, limit: int = 20) -> List[Dict]:
        """دریافت لیست کاربران"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, first_name, tier, created_at, wallet_balance
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users

    def ban_user(self, user_id: int, reason: str = '') -> bool:
        """مسدود‌کردن کاربر"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET is_banned = 1
                WHERE user_id = ?
            ''', (user_id,))
            
            # ثبت دلیل
            db.add_transaction(user_id, 'ban', 0, description=f'مسدود: {reason}')
            
            conn.commit()
            return True
        finally:
            conn.close()

    def unban_user(self, user_id: int) -> bool:
        """رفع مسدودیت کاربر"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET is_banned = 0
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def is_user_banned(self, user_id: int) -> bool:
        """بررسی اینکه آیا کاربر مسدود است"""
        user = db.get_user(user_id)
        return user.get('is_banned', False) if user else False

    def upgrade_user_tier(self, user_id: int, tier: str, duration_days: int = 30) -> bool:
        """ارتقاء تیر کاربر بدون پرداخت"""
        tier_config = db.get_tier_config(tier)
        if not tier_config:
            return False
        
        db.update_user_tier(user_id, tier)
        db.create_subscription(user_id, tier, 0, duration_days, auto_renew=False)
        
        return True

    # ==================== مدیریت درآمد ====================
    def get_revenue_report(self, days: int = 30) -> Dict:
        """دریافت گزارش درآمد"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT 
                DATE(created_at) as date,
                SUM(CASE WHEN type='deposit' THEN amount ELSE 0 END) as deposits,
                SUM(CASE WHEN type='subscription' THEN price ELSE 0 END) as subscriptions
            FROM (
                SELECT created_at, 'deposit' as type, amount, 0 as price FROM payments WHERE status='completed'
                UNION ALL
                SELECT start_date, 'subscription', 0, price FROM subscriptions WHERE is_active=1
            )
            WHERE DATE(created_at) >= DATE('now', '-{days} days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''')
        
        report = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return report

    # ==================== دستورات سریع ====================
    def broadcast_message(self, message: str) -> int:
        """ارسال پیام تودهٔ به تمام کاربران"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
        users = cursor.fetchall()
        conn.close()
        
        return len(users)  # بازگشت تعداد کاربران

    def get_banned_users(self) -> List[Dict]:
        """دریافت لیست کاربران مسدود"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, first_name, created_at
            FROM users
            WHERE is_banned = 1
            ORDER BY created_at DESC
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users

    # ==================== گزارش‌ها ====================
    def get_daily_report(self) -> str:
        """دریافت گزارش روزانه"""
        stats = self.get_system_stats()
        revenue = self.get_revenue_report(days=1)
        
        text = f"""
📋 **گزارش روزانهٔ امروز**

👥 کاربران جدید: {stats['new_users_today']}
📈 کل کاربران: {stats['total_users']}
📊 سفارشات جدید: {stats['total_orders']}
💰 درآمد امروز: {revenue[0]['deposits'] + revenue[0]['subscriptions'] if revenue else 0:,.0f} تومان

تیرهای محبوب:
"""
        for tier, count in sorted(stats['tier_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]:
            text += f"  🔹 {tier}: {count}\n"
        
        return text

    # ==================== ابزار debugging ====================
    def get_user_info(self, user_id: int) -> str:
        """دریافت اطلاعات کاملِ کاربر"""
        user = db.get_user(user_id)
        if not user:
            return "❌ کاربر یافت نشد"
        
        subscription = db.get_active_subscription(user_id)
        wallets = db.get_all_wallets(user_id)
        transactions = db.get_transactions(user_id, 5)
        
        text = f"""
🔍 **اطلاعات کاملِ کاربر**

**پروفایل:**
  🆔 ID: {user.get('user_id')}
  👤 نام: {user.get('first_name')} {user.get('last_name')}
  📱 username: @{user.get('username')}
  ⭐ تیر: {user.get('tier')}
  📅 عضویت: {user.get('created_at')}
  🚫 مسدود: {'✅ بله' if user.get('is_banned') else '❌ خیر'}

**کیف‌پول:**
"""
        for wallet in wallets:
            text += f"  💵 {wallet['currency']}: {wallet['balance']}\n"
        
        if subscription and subscription.get('is_active'):
            text += f"""
**اشتراک:**
  📌 تیر: {subscription.get('tier')}
  📅 انقضا: {subscription.get('end_date')}
  🔄 تمدید خودکار: {'✅ بله' if subscription.get('auto_renew') else '❌ خیر'}
"""
        
        text += "\n**آخرین تراکنش‌ها:**\n"
        for tx in transactions:
            text += f"  🔹 {tx.get('type')}: {tx.get('amount')} {tx.get('currency')}\n"
        
        return text

    # ==================== ابزار نگهداری ====================
    def cleanup_old_orders(self, days: int = 90) -> int:
        """حذف سفارشات قدیمی"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            DELETE FROM orders
            WHERE DATE(created_at) < DATE('now', '-{days} days')
            AND status IN ('cancelled', 'rejected')
        ''')
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count

    def backup_database(self, backup_path: str = 'backup.db') -> bool:
        """تهیهٔ پشتیبانی از دیتابیس"""
        import shutil
        try:
            shutil.copy(db.db_path, backup_path)
            return True
        except Exception as e:
            print(f"خطا در پشتیبانی: {e}")
            return False

    # ==================== منوی مدیریت ====================
    def get_admin_menu(self) -> InlineKeyboardMarkup:
        """منوی مدیریتی"""
        keyboard = [
            [InlineKeyboardButton("📊 آمار", callback_data='admin_stats'),
             InlineKeyboardButton("👥 کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💰 درآمد", callback_data='admin_revenue'),
             InlineKeyboardButton("🚫 مسدودها", callback_data='admin_banned')],
            [InlineKeyboardButton("📢 پیام تودهٔ", callback_data='admin_broadcast'),
             InlineKeyboardButton("🔧 ابزار", callback_data='admin_tools')],
            [InlineKeyboardButton("◀️ بازگشت", callback_data='main')]
        ]
        return InlineKeyboardMarkup(keyboard)


# ایجاد نمونهٔ global (به‌روزرسانی‌شده در config)
# admin_panel = AdminPanel(admin_id=ADMIN_USER_ID)
