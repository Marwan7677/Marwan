# db_manager.py - فایل مدیریت دیتابیس
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List

class DatabaseManager:
    def __init__(self, db_path: str = "toobit_bot.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    subscription_tier TEXT DEFAULT 'free',
                    subscription_expiry TIMESTAMP,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_admin INTEGER DEFAULT 0,
                    daily_trades_count INTEGER DEFAULT 0,
                    last_trade_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    user_id INTEGER PRIMARY KEY,
                    balance_usdt REAL DEFAULT 0.0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    txid TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'pending',
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL DEFAULT 0,
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
    
    # ========== متدهای کاربر ==========
    def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            conn.execute("""
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (?, ?, ?)
            """, (telegram_id, username, first_name))
            user_id = cursor.lastrowid
            conn.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (?, 0)", (user_id,))
            conn.commit()
            return user_id
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========== متدهای کیف پول ==========
    def get_balance(self, telegram_id: int) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT w.balance_usdt FROM wallets w
                JOIN users u ON u.id = w.user_id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else 0.0
    
    def add_balance(self, telegram_id: int, amount: float) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE wallets SET balance_usdt = balance_usdt + ?
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
            """, (amount, telegram_id))
            conn.commit()
            return True
    
    def deduct_balance(self, telegram_id: int, amount: float) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT w.balance_usdt FROM wallets w
                JOIN users u ON u.id = w.user_id
                WHERE u.telegram_id = ? AND w.balance_usdt >= ?
            """, (telegram_id, amount))
            if cursor.fetchone():
                conn.execute("""
                    UPDATE wallets SET balance_usdt = balance_usdt - ?
                    WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
                """, (amount, telegram_id))
                conn.commit()
                return True
            return False
    
    # ========== متدهای درخواست شارژ ==========
    def add_deposit_request(self, telegram_id: int, amount: float, currency: str, txid: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO deposits (user_id, amount, currency, txid)
                    VALUES ((SELECT id FROM users WHERE telegram_id = ?), ?, ?, ?)
                """, (telegram_id, amount, currency, txid))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_pending_deposits(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT d.*, u.telegram_id, u.username
                FROM deposits d
                JOIN users u ON u.id = d.user_id
                WHERE d.status = 'pending'
                ORDER BY d.requested_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def confirm_deposit(self, deposit_id: int, confirmed: bool) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            if confirmed:
                conn.execute("""
                    UPDATE deposits
                    SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                """, (deposit_id,))
            else:
                conn.execute("UPDATE deposits SET status = 'rejected' WHERE id = ?", (deposit_id,))
            
            if conn.total_changes > 0 and confirmed:
                cursor = conn.execute("SELECT user_id, amount FROM deposits WHERE id = ?", (deposit_id,))
                user_id, amount = cursor.fetchone()
                conn.execute("UPDATE wallets SET balance_usdt = balance_usdt + ? WHERE user_id = ?", (amount, user_id))
            
            conn.commit()
            return conn.total_changes > 0
    
    # ========== متدهای اشتراک ==========
    def get_user_subscription(self, telegram_id: int) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT subscription_tier, subscription_expiry
                FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            result = cursor.fetchone()
            if not result:
                return {"tier": "free", "expiry": None}
            tier, expiry = result
            if expiry and datetime.fromisoformat(expiry) > datetime.now():
                return {"tier": tier, "expiry": expiry}
            return {"tier": "free", "expiry": None}
    
    def upgrade_subscription(self, telegram_id: int, new_tier: str, days: int = 30) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            conn.execute("""
                UPDATE users
                SET subscription_tier = ?, subscription_expiry = ?
                WHERE telegram_id = ?
            """, (new_tier, expiry, telegram_id))
            conn.commit()
            return conn.total_changes > 0

# ایجاد یک نمونه واحد از دیتابیس منیجر برای کل پروژه
db = DatabaseManager()