"""
سیستم مدیریت دیتابیس PostgreSQL با asyncpg
"""

import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def init_pool(self):
        """ایجاد connection pool و جداول"""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        await self._init_tables()
        logger.info("✅ PostgreSQL connection pool created")

    async def _init_tables(self):
        """ایجاد جداول با سینتکس PostgreSQL"""
        async with self.pool.acquire() as conn:
            # جدول کاربران
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tier TEXT DEFAULT 'free',
                    wallet_balance DECIMAL DEFAULT 0,
                    total_spent DECIMAL DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    notification_enabled BOOLEAN DEFAULT TRUE,
                    language TEXT DEFAULT 'fa'
                )
            ''')

            # جدول کیف‌پول
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    wallet_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    currency TEXT NOT NULL,
                    balance DECIMAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, currency)
                )
            ''')

            # جدول تراکنش‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    type TEXT NOT NULL,
                    amount DECIMAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    status TEXT DEFAULT 'pending',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # جدول اشتراک‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscription_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    tier TEXT NOT NULL,
                    price DECIMAL NOT NULL,
                    duration_days INTEGER DEFAULT 30,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    auto_renew BOOLEAN DEFAULT FALSE
                )
            ''')

            # جدول سفارشات
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity DECIMAL NOT NULL,
                    price DECIMAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    toobit_order_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')

            # جدول پرداخت‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    amount DECIMAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    method TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    purpose TEXT,
                    tier TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')

            # جدول تنظیمات تیرها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tier_config (
                    tier_id SERIAL PRIMARY KEY,
                    tier_name TEXT UNIQUE NOT NULL,
                    price_monthly DECIMAL NOT NULL,
                    price_yearly DECIMAL NOT NULL,
                    max_daily_trades INTEGER DEFAULT 10,
                    max_order_size DECIMAL DEFAULT 100,
                    min_order_size DECIMAL DEFAULT 0.001,
                    withdrawal_fee DECIMAL DEFAULT 2.0,
                    features TEXT DEFAULT '{}',
                    description TEXT,
                    emoji TEXT DEFAULT '🔹'
                )
            ''')

            # جدول اعلانات قیمت
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS price_alerts (
                    alert_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    target_price DECIMAL NOT NULL,
                    direction TEXT CHECK (direction IN ('above', 'below')),
                    is_active BOOLEAN DEFAULT TRUE,
                    triggered_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await self._init_default_tiers(conn)

    async def _init_default_tiers(self, conn):
    from config import TIER_CONFIG  # import داخل تابع برای جلوگیری از circular
    count = await conn.fetchval("SELECT COUNT(*) FROM tier_config")
    if count == 0:
        for tier_name, tier_data in TIER_CONFIG.items():
            await conn.execute('''
                INSERT INTO tier_config 
                (tier_name, price_monthly, price_yearly, max_daily_trades, 
                 max_order_size, min_order_size, withdrawal_fee, features, description, emoji)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''', tier_name, tier_data['price_monthly'], tier_data['price_yearly'],
               tier_data['max_daily_trades'], tier_data['max_order_size'],
               tier_data['min_order_size'], tier_data['withdrawal_fee'],
               str(tier_data['features']), tier_data.get('description', ''),
               tier_data.get('emoji', '🔹'))

    # ---------- کاربران ----------
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str = "") -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id, username, first_name, last_name)
                for currency in ['USDT', 'USD', 'IRR']:
                    await conn.execute('''
                        INSERT INTO wallets (user_id, currency, balance)
                        VALUES ($1, $2, 0)
                        ON CONFLICT (user_id, currency) DO NOTHING
                    ''', user_id, currency)
                return True
            except Exception as e:
                logger.error(f"Error adding user: {e}")
                return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def update_user_tier(self, user_id: int, tier: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET tier = $1 WHERE user_id = $2",
                tier, user_id
            )
            return result != "UPDATE 0"

    async def get_user_tier(self, user_id: int) -> str:
        user = await self.get_user(user_id)
        return user['tier'] if user else 'free'

    # ---------- کیف‌پول ----------
    async def get_wallet_balance(self, user_id: int, currency: str = 'USDT') -> float:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT balance FROM wallets WHERE user_id = $1 AND currency = $2",
                user_id, currency
            )
            return float(row['balance']) if row else 0.0

    async def get_all_wallets(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT currency, balance FROM wallets WHERE user_id = $1 AND balance > 0 ORDER BY currency",
                user_id
            )
            return [dict(row) for row in rows]

    async def update_wallet_balance(self, user_id: int, currency: str, amount: float) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE wallets 
                SET balance = balance + $1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $2 AND currency = $3
            ''', amount, user_id, currency)
            return True

    # ---------- تراکنش‌ها ----------
    async def add_transaction(self, user_id: int, type: str, amount: float,
                              currency: str = 'USDT', status: str = 'completed',
                              description: str = '') -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO transactions (user_id, type, amount, currency, status, description)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING transaction_id
            ''', user_id, type, amount, currency, status, description)
            return row['transaction_id'] if row else 0

    async def get_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM transactions 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]

    # ---------- اشتراک‌ها ----------
    async def create_subscription(self, user_id: int, tier: str, price: float,
                                  duration_days: int = 30, auto_renew: bool = False) -> int:
        async with self.pool.acquire() as conn:
            end_date = datetime.now() + timedelta(days=duration_days)
            row = await conn.fetchrow('''
                INSERT INTO subscriptions (user_id, tier, price, duration_days, end_date, auto_renew)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING subscription_id
            ''', user_id, tier, price, duration_days, end_date, auto_renew)
            await self.update_user_tier(user_id, tier)
            return row['subscription_id'] if row else 0

    async def get_active_subscription(self, user_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM subscriptions 
                WHERE user_id = $1 AND is_active = TRUE AND end_date > CURRENT_TIMESTAMP
                ORDER BY end_date DESC
                LIMIT 1
            ''', user_id)
            return dict(row) if row else None

    # ---------- سفارشات ----------
    async def add_order(self, user_id: int, symbol: str, side: str,
                        quantity: float, price: float) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO orders (user_id, symbol, side, quantity, price)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING order_id
            ''', user_id, symbol, side, quantity, price)
            return row['order_id'] if row else 0

    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM orders 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]

    # ---------- تیرها ----------
    async def get_tier_config(self, tier_name: str) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tier_config WHERE tier_name = $1",
                tier_name
            )
            return dict(row) if row else None

    async def get_all_tiers(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tier_config ORDER BY price_monthly ASC")
            return [dict(row) for row in rows]

    # ---------- اعلانات قیمت ----------
    async def add_price_alert(self, user_id: int, symbol: str, target_price: float, direction: str) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO price_alerts (user_id, symbol, target_price, direction)
                VALUES ($1, $2, $3, $4)
                RETURNING alert_id
            ''', user_id, symbol, target_price, direction)
            return row['alert_id'] if row else 0

    async def get_active_alerts(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM price_alerts 
                WHERE is_active = TRUE AND triggered_at IS NULL
            ''')
            return [dict(row) for row in rows]

    async def trigger_alert(self, alert_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE price_alerts SET is_active = FALSE, triggered_at = CURRENT_TIMESTAMP WHERE alert_id = $1",
                alert_id
            )

    async def get_user_alerts(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM price_alerts WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
            return [dict(row) for row in rows]

    # ---------- آمار سیستم ----------
    async def get_system_stats(self) -> Dict:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            new_users_today = await conn.fetchval("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
            total_orders = await conn.fetchval("SELECT COUNT(*) FROM orders")
            total_revenue = await conn.fetchval("SELECT COALESCE(SUM(price), 0) FROM subscriptions WHERE is_active = TRUE")
            tier_dist = await conn.fetch("SELECT tier, COUNT(*) FROM users GROUP BY tier")
            tier_distribution = {row[0]: row[1] for row in tier_dist}
            return {
                'total_users': total_users,
                'new_users_today': new_users_today,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'tier_distribution': tier_distribution
            }