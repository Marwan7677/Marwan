"""
سیستم درگاه‌های پرداخت
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from enum import Enum


class PaymentMethod(Enum):
    """روش‌های پرداخت"""
    USDT_WALLET = "usdt_wallet"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    CRYPTO = "crypto"


class PaymentGateway:
    """مدیریت درگاه‌های پرداخت"""
    
    def __init__(self, db):
        self.db = db
        self.pending_payments = {}
        self.init_payment_table()

    def init_payment_table(self):
        """ایجاد جدول پرداخت‌ها"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDT',
                method TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                purpose TEXT,
                tier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    # ==================== USDT/Wallet ====================
    def create_wallet_payment(self, user_id: int, amount: float, 
                             purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        """ایجاد درخواست پرداخت از کیف‌پول USDT"""
        payment_id = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payment_id, user_id, amount, 'USDT', 'usdt_wallet', 
                 'pending', purpose, tier, expires_at))
            conn.commit()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'amount': amount,
                'method': 'USDT Wallet',
                'description': f'درخواست پرداخت {amount} USDT',
                'wallet_address': self._generate_wallet_address(user_id),
                'expires_at': expires_at,
                'message': 'لطفا مبلغ درخواستی را به آدرس فوق ارسال کنید'
            }
        finally:
            conn.close()

    def _generate_wallet_address(self, user_id: int) -> str:
        """تولید آدرس کیف‌پول"""
        return f"wallet_{user_id}_{uuid.uuid4().hex[:8]}"

    # ==================== درگاه بانکی ====================
    def create_bank_payment(self, user_id: int, amount: float, 
                           purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        """ایجاد درخواست پرداخت بانکی"""
        payment_id = str(uuid.uuid4())
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payment_id, user_id, amount, 'IRR', 'bank_transfer', 
                 'pending', purpose, tier))
            conn.commit()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'amount': amount,
                'currency': 'IRR',
                'method': 'Bank Transfer',
                'bank_info': {
                    'account_owner': 'Toobit Trade Bot',
                    'account_number': '1234567890123456',
                    'bank_name': 'بانک ملی',
                    'sheba': 'IR0012000000000001234567890'
                },
                'description': f'انتقال {int(amount)} ریال به حساب بانکی',
                'reference': payment_id
            }
        finally:
            conn.close()

    # ==================== کارت اعتباری ====================
    def create_card_payment(self, user_id: int, amount: float, 
                           purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        """ایجاد درخواست پرداخت با کارت اعتباری"""
        payment_id = str(uuid.uuid4())
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payment_id, user_id, amount, 'IRR', 'credit_card', 
                 'pending', purpose, tier))
            conn.commit()
            
            # در حالت واقعی باید به درگاه پرداخت واقعی متصل شود
            payment_url = f"https://payment.toobitbot.ir/pay/{payment_id}"
            
            return {
                'success': True,
                'payment_id': payment_id,
                'amount': amount,
                'currency': 'IRR',
                'method': 'Credit Card',
                'payment_url': payment_url,
                'description': f'پرداخت {int(amount)} ریال با کارت اعتباری',
                'message': 'برای تکمیل پرداخت بر روی لینک زیر کلیک کنید'
            }
        finally:
            conn.close()

    # ==================== بررسی پرداخت ====================
    def check_payment_status(self, payment_id: str) -> Dict:
        """بررسی وضعیت پرداخت"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM payments WHERE payment_id = ?', (payment_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'status': 'not_found'}
        
        payment = dict(row)
        return payment

    def verify_payment(self, payment_id: str, transaction_hash: str = None) -> Tuple[bool, str]:
        """تأیید پرداخت"""
        payment = self.check_payment_status(payment_id)
        
        if payment.get('status') == 'completed':
            return True, 'پرداخت قبلاً تایید شده است'
        
        if payment.get('status') == 'not_found':
            return False, 'سند پرداخت یافت نشد'
        
        # در حالت واقعی باید تراکنش را تأیید کنید
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payments 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
            ''', (payment_id,))
            conn.commit()
            
            # افزودن موجودی به کیف‌پول کاربر
            user_id = payment.get('user_id')
            amount = payment.get('amount')
            currency = payment.get('currency')
            purpose = payment.get('purpose')
            tier = payment.get('tier')
            
            self.db.update_wallet_balance(user_id, currency, amount)
            self.db.add_transaction(user_id, 'deposit', amount, currency, 
                                   'completed', f'پرداخت: {purpose}')
            
            # اگر برای اشتراک بود
            if purpose == 'subscription' and tier:
                self.db.create_subscription(user_id, tier, amount)
            
            return True, f'✅ پرداخت تأیید شد! {amount} {currency} به حساب اضافه شد'
        
        except Exception as e:
            return False, f'❌ خطا در تأیید پرداخت: {str(e)}'
        finally:
            conn.close()

    # ==================== محاسبه قیمت ====================
    def calculate_subscription_price(self, tier_name: str, duration: str = 'monthly') -> float:
        """محاسبه قیمت اشتراک"""
        tier = self.db.get_tier_config(tier_name)
        if not tier:
            return 0.0
        
        if duration == 'monthly':
            return tier.get('price_monthly', 0)
        elif duration == 'yearly':
            return tier.get('price_yearly', 0)
        
        return 0.0

    def get_discount(self, duration: str) -> float:
        """دریافت درصد تخفیف"""
        discounts = {
            'monthly': 0,
            'quarterly': 5,
            'semi_annual': 10,
            'yearly': 15
        }
        return discounts.get(duration, 0)

    # ==================== تاریخچه پرداخت ====================
    def get_payment_history(self, user_id: int, limit: int = 10) -> list:
        """دریافت تاریخچه پرداخت‌ها"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payments 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        payments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return payments

    # ==================== تمدید خودکار ====================
    def setup_auto_renewal(self, user_id: int, subscription_id: int, 
                          payment_method: str) -> bool:
        """تنظیم تمدید خودکار اشتراک"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE subscriptions 
                SET auto_renew = 1
                WHERE subscription_id = ? AND user_id = ?
            ''', (subscription_id, user_id))
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== استرداد وجه ====================
    def request_refund(self, payment_id: str, reason: str = '') -> Tuple[bool, str]:
        """درخواست بازگشت وجه"""
        payment = self.check_payment_status(payment_id)
        
        if payment.get('status') != 'completed':
            return False, 'فقط پرداخت‌های تأیید شده می‌توانند استرداد شوند'
        
        # بررسی زمان (مثلاً 7 روز)
        if payment.get('completed_at'):
            from datetime import datetime as dt
            completed = dt.fromisoformat(payment['completed_at'])
            if (dt.now() - completed).days > 7:
                return False, 'مهلت درخواست بازگشت وجه تمام شده است'
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payments 
                SET status = 'refunded'
                WHERE payment_id = ?
            ''', (payment_id,))
            conn.commit()
            
            # بازگشت وجه به کیف‌پول
            user_id = payment.get('user_id')
            amount = payment.get('amount')
            currency = payment.get('currency')
            
            self.db.update_wallet_balance(user_id, currency, -amount)
            self.db.add_transaction(user_id, 'refund', amount, currency, 
                                   'completed', f'بازگشت وجه: {reason}')
            
            return True, f'✅ {amount} {currency} به حساب‌تان بازگردانده شد'
        
        except Exception as e:
            return False, f'❌ خطا: {str(e)}'
        finally:
            conn.close()
