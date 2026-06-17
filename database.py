"""
سیستم مدیریت دیتابیس ربات Toobit - نسخهٔ اصلاح شدهٔ
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

class Database:
    def __init__(self, db_path: str = "toobit_bot.db"):
        self.db_path = db_path
        self.init_tables()
        self.init_tiers()  # ✅ اضافه شده

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """ایجاد جداول دیتابیس"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tier TEXT DEFAULT 'free',
                wallet_balance REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                notification_enabled BOOLEAN DEFAULT 1,
                language TEXT DEFAULT 'fa'
            )
        ''')

        # جدول کیف‌پول
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                wallet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                currency TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, currency)
            )
        ''')

        # جدول تاریخچه تراکنش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDT',
                status TEXT DEFAULT 'pending',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول اشتراک‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier TEXT NOT NULL,
                price REAL NOT NULL,
                duration_days INTEGER DEFAULT 30,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول سفارشات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                toobit_order_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول تنظیمات اشتراک‌ها - ✅ اصلاح شده
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tier_config (
                tier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tier_name TEXT UNIQUE NOT NULL,
                price_monthly REAL NOT NULL,
                price_yearly REAL NOT NULL,
                max_daily_trades INTEGER DEFAULT 10,
                max_order_size REAL DEFAULT 100,
                min_order_size REAL DEFAULT 0.001,
                withdrawal_fee REAL DEFAULT 2.0,
                features TEXT DEFAULT '{}',
                description TEXT DEFAULT '',
                emoji TEXT DEFAULT '🔹'
            )
        ''')

        conn.commit()
        conn.close()

    # ==================== کاربران ====================
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = "") -> bool:
        """افزودن کاربر جدید"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            
            # کیف‌پول پیش‌فرض (USDT)
            cursor.execute('''
                INSERT OR IGNORE INTO wallets 
                (user_id, currency, balance)
                VALUES (?, ?, 0)
            ''', (user_id, 'USDT'))
            
            # کیف‌پول دوم (USD)
            cursor.execute('''
                INSERT OR IGNORE INTO wallets 
                (user_id, currency, balance)
                VALUES (?, ?, 0)
            ''', (user_id, 'USD'))
            
            # کیف‌پول سوم (IRR)
            cursor.execute('''
                INSERT OR IGNORE INTO wallets 
                (user_id, currency, balance)
                VALUES (?, ?, 0)
            ''', (user_id, 'IRR'))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"خطا در افزودن کاربر: {e}")
            return False
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """دریافت اطلاعات کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_user_tier(self, user_id: int, tier: str) -> bool:
        """بروزرسانی تیر کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE users SET tier = ? WHERE user_id = ?
            ''', (tier, user_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_user_tier(self, user_id: int) -> str:
        """دریافت تیر کاربر"""
        user = self.get_user(user_id)
        return user['tier'] if user else 'free'

    # ==================== کیف‌پول ====================
    def get_wallet_balance(self, user_id: int, currency: str = 'USDT') -> float:
        """دریافت موجودی کیف‌پول"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT balance FROM wallets 
            WHERE user_id = ? AND currency = ?
        ''', (user_id, currency))
        row = cursor.fetchone()
        conn.close()
        return float(row['balance']) if row else 0.0

    def add_wallet_balance(self, user_id: int, amount: float, currency: str = 'USDT') -> bool:
        """افزودن به موجودی کیف‌پول"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE wallets 
                SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency = ?
            ''', (amount, user_id, currency))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_all_wallets(self, user_id: int) -> List[Dict]:
        """دریافت تمام کیف‌پول‌های کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM wallets WHERE user_id = ?
        ''', (user_id,))
        wallets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return wallets

    # ==================== تراکنش‌ها ====================
    def add_transaction(self, user_id: int, tx_type: str, amount: float, 
                       currency: str = 'USDT', description: str = '') -> bool:
        """افزودن تراکنش"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO transactions 
                (user_id, type, amount, currency, description, status)
                VALUES (?, ?, ?, ?, ?, 'completed')
            ''', (user_id, tx_type, amount, currency, description))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """دریافت تراکنش‌های کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return transactions

    # ==================== سفارشات ====================
    def add_order(self, user_id: int, symbol: str, side: str, 
                 quantity: float, price: float) -> bool:
        """افزودن سفارش"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO orders 
                (user_id, symbol, side, quantity, price, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, symbol, side, quantity, price))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_user_orders(self, user_id: int, status: str = 'pending', limit: int = 50) -> List[Dict]:
        """دریافت سفارشات کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM orders 
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, status, limit))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    # ==================== تیرها - ✅ اصلاح شده ====================
    def init_tiers(self):
        """راه‌اندازی اولیه تیرها"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ✅ اصلاح شده: 10 مقدار برای 10 ستون
        tiers = [
            ('free', 0, 0, 5, 50, 0.001, 5.0, 
             '["قیمت"]', '', '🔹'),
            
            ('lite', 50000, 500000, 20, 200, 0.001, 3.0, 
             '["قیمت", "سفارش محدود", "کیف پول"]', 'لایت', '🥉'),
            
            ('pro', 150000, 1400000, 50, 500, 0.0001, 2.0, 
             '["قیمت", "سفارش نامحدود", "کیف پول", "تاریخچه"]', 'پرو', '🥈'),
            
            ('professional', 300000, 2800000, 200, 2000, 0.00001, 1.5, 
             '["همه", "API", "ربات", "پشتیبانی VIP"]', 'حرفه‌ای', '🏆'),
            
            ('gold', 500000, 4500000, 500, 5000, 0.000001, 1.0, 
             '["همه", "API", "ربات", "پشتیبانی 24/7"]', 'طلایی', '⭐'),
            
            ('diamond', 1000000, 9000000, -1, -1, 0, 0.5, 
             '["تمام امکانات", "اولویت بالا", "مشاور شخصی"]', 'الماس', '💎'),
        ]
        
        for tier in tiers:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO tier_config 
                    (tier_name, price_monthly, price_yearly, max_daily_trades, 
                     max_order_size, min_order_size, withdrawal_fee, features, 
                     description, emoji)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tier)
            except Exception as e:
                print(f"خطا در درج {tier[0]}: {e}")
        
        conn.commit()
        conn.close()

    def get_tier_config(self, tier_name: str) -> Optional[Dict]:
        """دریافت تنظیمات تیر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM tier_config WHERE tier_name = ?
        ''', (tier_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_tiers(self) -> List[Dict]:
        """دریافت تمام تیرها"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM tier_config ORDER BY price_monthly ASC
        ''')
        tiers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tiers

    # ==================== اشتراک‌ها ====================
    def add_subscription(self, user_id: int, tier: str, price: float, 
                        duration_days: int = 30) -> bool:
        """افزودن اشتراک"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            end_date = datetime.now() + timedelta(days=duration_days)
            cursor.execute('''
                INSERT INTO subscriptions 
                (user_id, tier, price, duration_days, start_date, end_date, is_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
            ''', (user_id, tier, price, duration_days, end_date))
            
            # بروزرسانی تیر کاربر
            cursor.execute('UPDATE users SET tier = ? WHERE user_id = ?', 
                         (tier, user_id))
            
            conn.commit()
            return True
        finally:
            conn.close()

    def get_active_subscription(self, user_id: int) -> Optional[Dict]:
        """دریافت اشتراک فعال کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND is_active = 1 AND end_date > CURRENT_TIMESTAMP
            ORDER BY start_date DESC LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


# ایجاد نمونهٔ global - ✅ اصلاح شده
try:
    db = Database()
    print("✅ دیتابیس مقداردهی شد")
except Exception as e:
    print(f"❌ خطا در مقداردهی دیتابیس: {e}")
    raise
