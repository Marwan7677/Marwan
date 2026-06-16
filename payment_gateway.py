"""
سیستم درگاه‌های پرداخت - نسخه async
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from enum import Enum


class PaymentMethod(Enum):
    USDT_WALLET = "usdt_wallet"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    CRYPTO = "crypto"


class PaymentGateway:
    def __init__(self, db):
        self.db = db
        self.pending_payments = {}

    async def init_payment_table(self):
        async with self.db.pool.acquire() as conn:
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

    async def create_wallet_payment(self, user_id: int, amount: float,
                                   purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        payment_id = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', payment_id, user_id, amount, 'USDT', 'usdt_wallet',
               'pending', purpose, tier, expires_at)
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

    def _generate_wallet_address(self, user_id: int) -> str:
        return f"wallet_{user_id}_{uuid.uuid4().hex[:8]}"

    async def create_bank_payment(self, user_id: int, amount: float,
                                 purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        payment_id = str(uuid.uuid4())
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', payment_id, user_id, amount, 'IRR', 'bank_transfer',
               'pending', purpose, tier)
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

    async def create_card_payment(self, user_id: int, amount: float,
                                 purpose: str = 'wallet_charge', tier: str = None) -> Dict:
        payment_id = str(uuid.uuid4())
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO payments 
                (payment_id, user_id, amount, currency, method, status, purpose, tier)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', payment_id, user_id, amount, 'IRR', 'credit_card',
               'pending', purpose, tier)
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

    async def check_payment_status(self, payment_id: str) -> Dict:
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", payment_id)
            if not row:
                return {'status': 'not_found'}
            return dict(row)

    async def verify_payment(self, payment_id: str, transaction_hash: str = None) -> Tuple[bool, str]:
        payment = await self.check_payment_status(payment_id)
        if payment.get('status') == 'completed':
            return True, 'پرداخت قبلاً تایید شده است'
        if payment.get('status') == 'not_found':
            return False, 'سند پرداخت یافت نشد'
        async with self.db.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE payments 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE payment_id = $1
                ''', payment_id)
                user_id = payment.get('user_id')
                amount = payment.get('amount')
                currency = payment.get('currency')
                purpose = payment.get('purpose')
                tier = payment.get('tier')
                await self.db.update_wallet_balance(user_id, currency, amount)
                await self.db.add_transaction(user_id, 'deposit', amount, currency,
                                             'completed', f'پرداخت: {purpose}')
                if purpose == 'subscription' and tier:
                    await self.db.create_subscription(user_id, tier, amount)
                return True, f'✅ پرداخت تأیید شد! {amount} {currency} به حساب اضافه شد'
            except Exception as e:
                return False, f'❌ خطا در تأیید پرداخت: {str(e)}'

    def calculate_subscription_price(self, tier_name: str, duration: str = 'monthly') -> float:
        tier = self.db.get_tier_config(tier_name)
        if not tier:
            return 0.0
        if duration == 'monthly':
            return tier.get('price_monthly', 0)
        elif duration == 'yearly':
            return tier.get('price_yearly', 0)
        return 0.0

    def get_discount(self, duration: str) -> float:
        discounts = {'monthly': 0, 'quarterly': 5, 'semi_annual': 10, 'yearly': 15}
        return discounts.get(duration, 0)

    async def get_payment_history(self, user_id: int, limit: int = 10) -> list:
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM payments 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]

    async def setup_auto_renewal(self, user_id: int, subscription_id: int, payment_method: str) -> bool:
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE subscriptions 
                SET auto_renew = TRUE
                WHERE subscription_id = $1 AND user_id = $2
            ''', subscription_id, user_id)
            return True

    async def request_refund(self, payment_id: str, reason: str = '') -> Tuple[bool, str]:
        payment = await self.check_payment_status(payment_id)
        if payment.get('status') != 'completed':
            return False, 'فقط پرداخت‌های تأیید شده می‌توانند استرداد شوند'
        if payment.get('completed_at'):
            from datetime import datetime as dt
            completed = dt.fromisoformat(payment['completed_at'])
            if (dt.now() - completed).days > 7:
                return False, 'مهلت درخواست بازگشت وجه تمام شده است'
        async with self.db.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE payments 
                    SET status = 'refunded'
                    WHERE payment_id = $1
                ''', payment_id)
                user_id = payment.get('user_id')
                amount = payment.get('amount')
                currency = payment.get('currency')
                await self.db.update_wallet_balance(user_id, currency, -amount)
                await self.db.add_transaction(user_id, 'refund', amount, currency,
                                             'completed', f'بازگشت وجه: {reason}')
                return True, f'✅ {amount} {currency} به حساب‌تان بازگردانده شد'
            except Exception as e:
                return False, f'❌ خطا: {str(e)}'