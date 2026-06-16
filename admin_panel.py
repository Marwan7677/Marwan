"""
پنل مدیریتی ربات - نسخه async با PostgreSQL
"""

from typing import Optional, List, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class AdminPanel:
    def __init__(self, admin_id: int, db):
        self.admin_id = admin_id
        self.db = db

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.admin_id

    async def get_system_stats(self) -> Dict:
        return await self.db.get_system_stats()

    async def get_stats_message(self) -> str:
        stats = await self.get_system_stats()
        text = f"""
📊 **آمار سیستم**

👥 **کاربران:**
  📈 کل کاربران: {stats['total_users']}
  ✨ کاربران جدید امروز: {stats['new_users_today']}

📋 **سفارشات:**
  🔹 کل سفارشات: {stats['total_orders']}

💰 **درآمد:**
  💵 کل درآمد فعال: {stats['total_revenue']:,.0f} تومان

📊 **توزیع تیرها:**
"""
        for tier, count in stats['tier_distribution'].items():
            text += f"  🔹 {tier}: {count} نفر\n"
        return text

    async def get_user_list(self, limit: int = 20) -> List[Dict]:
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, first_name, tier, created_at, wallet_balance
                FROM users
                ORDER BY created_at DESC
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]

    async def ban_user(self, user_id: int, reason: str = '') -> bool:
        async with self.db.pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_banned = TRUE WHERE user_id = $1", user_id)
            await self.db.add_transaction(user_id, 'ban', 0, description=f'مسدود: {reason}')
            return True

    async def unban_user(self, user_id: int) -> bool:
        async with self.db.pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_banned = FALSE WHERE user_id = $1", user_id)
            return True

    async def is_user_banned(self, user_id: int) -> bool:
        user = await self.db.get_user(user_id)
        return user.get('is_banned', False) if user else False

    async def upgrade_user_tier(self, user_id: int, tier: str, duration_days: int = 30) -> bool:
        tier_config = await self.db.get_tier_config(tier)
        if not tier_config:
            return False
        await self.db.update_user_tier(user_id, tier)
        await self.db.create_subscription(user_id, tier, 0, duration_days, auto_renew=False)
        return True

    async def get_revenue_report(self, days: int = 30) -> List[Dict]:
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(f'''
                SELECT 
                    DATE(created_at) as date,
                    COALESCE(SUM(CASE WHEN type='deposit' THEN amount ELSE 0 END), 0) as deposits,
                    COALESCE(SUM(CASE WHEN type='subscription' THEN price ELSE 0 END), 0) as subscriptions
                FROM (
                    SELECT created_at, 'deposit' as type, amount, 0 as price FROM payments WHERE status='completed'
                    UNION ALL
                    SELECT start_date, 'subscription', 0, price FROM subscriptions WHERE is_active=TRUE
                )
                WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '{days} days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            return [dict(row) for row in rows]

    async def get_banned_users(self) -> List[Dict]:
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, first_name, created_at
                FROM users
                WHERE is_banned = TRUE
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in rows]

    async def get_daily_report(self) -> str:
        stats = await self.get_system_stats()
        revenue = await self.get_revenue_report(days=1)
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

    async def get_user_info(self, user_id: int) -> str:
        user = await self.db.get_user(user_id)
        if not user:
            return "❌ کاربر یافت نشد"
        subscription = await self.db.get_active_subscription(user_id)
        wallets = await self.db.get_all_wallets(user_id)
        transactions = await self.db.get_transactions(user_id, 5)
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

    async def cleanup_old_orders(self, days: int = 90) -> int:
        async with self.db.pool.acquire() as conn:
            result = await conn.execute(f'''
                DELETE FROM orders
                WHERE DATE(created_at) < CURRENT_DATE - INTERVAL '{days} days'
                AND status IN ('cancelled', 'rejected')
            ''')
            return int(result.split()[1]) if result else 0

    def get_admin_menu(self) -> InlineKeyboardMarkup:
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