import asyncio
import logging
import aiohttp
from typing import List, Dict
from datetime import datetime
from sqlalchemy import select
from models import Deposit
from database import AsyncSessionLocal
from wallet import add_balance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRON_ADDRESS = 'TUcuhhn72Bvs6VATeGr4evcqfnMwqdLh84'  # آدرس خود را وارد کنید
TRONGRID_API_KEY = '12c8fc56-e525-4c2e-a09e-230f1137d175'
USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

async def is_transaction_processed(txid: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Deposit).where(Deposit.txid == txid))
        return result.scalar_one_or_none() is not None

async def mark_transaction_processed(txid: str, user_id: int, amount: float):
    async with AsyncSessionLocal() as session:
        deposit = Deposit(
            user_id=user_id,
            amount=amount,
            currency="USDT",
            txid=txid,
            status="confirmed",
            confirmed_at=datetime.utcnow()
        )
        session.add(deposit)
        await session.commit()

async def get_transaction_history(address: str, limit: int = 50) -> List[Dict]:
    url = f'https://api.trongrid.io/v1/accounts/{address}/transactions'
    params = {'only_confirmed': 'true', 'limit': limit, 'only_to': 'true'}
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY} if TRONGRID_API_KEY else {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', [])
        except Exception as e:
            logger.error(f"خطا در دریافت تاریخچه: {e}")
    return []

async def check_new_transactions():
    logger.info(f"بررسی تراکنش‌های جدید برای {TRON_ADDRESS}...")
    transactions = await get_transaction_history(TRON_ADDRESS, limit=50)
    for tx in transactions:
        txid = tx.get('txID')
        if not txid:
            continue
        if await is_transaction_processed(txid):
            continue
        # بررسی مقدار و کاربر (در این نسخه ساده، فقط لاگ می‌شود)
        # شما باید از داده‌های تراکنش user_id را استخراج کنید (مثلاً از memo)
        logger.info(f"تراکنش جدید: {txid}")
        # مثال: فرض کاربر 123456789 و مبلغ 10 USDT
        # await mark_transaction_processed(txid, user_id, amount)
        # await add_balance(user_id, amount)

async def start_monitoring(interval_seconds: int = 30):
    logger.info("شروع مانیتورینگ خودکار واریز TRON...")
    while True:
        try:
            await check_new_transactions()
        except Exception as e:
            logger.error(f"خطا: {e}")
        await asyncio.sleep(interval_seconds)