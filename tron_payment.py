# tron_payment.py
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any

class TronPaymentMonitor:
    def __init__(self, api_key: str, webhook_url: str = None):
        self.api_key = api_key
        self.webhook_url = webhook_url
        self.base_url = "https://api.trongrid.io"
        self.headers = {
            "TRON-PRO-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    async def get_account_info(self, address: str) -> Dict[str, Any]:
        """گرفتن اطلاعات یک آدرس ترون (موجودی TRX و توکن‌ها)"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/accounts/{address}",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def check_usdt_balance(self, address: str) -> float:
        """بررسی موجودی USDT-TRC20 یک آدرس"""
        # کنترکت USDT در شبکه ترون
        usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        payload = {
            "contract_address": usdt_contract,
            "function_selector": "balanceOf(address)",
            "parameter": address,
            "owner_address": address,
            "visible": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/wallet/triggerconstantcontract",
                json=payload,
                headers=self.headers
            ) as response:
                data = await response.json()
                # تبدیل از کوچکترین واحد (با 6 رقم اعشار)
                if "constant_result" in data:
                    balance = int(data["constant_result"][0], 16) / 1_000_000
                    return balance
                return 0.0
    
    async def get_transaction_history(self, address: str, limit: int = 20) -> list:
        """دریافت تاریخچه تراکنش‌های آدرس"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/v1/accounts/{address}/transactions",
                params={"limit": limit, "only_confirmed": True},
                headers=self.headers
            ) as response:
                data = await response.json()
                return data.get("data", [])
    
    async def monitor_address(self, address: str, expected_amount: float, 
                              check_interval: int = 30, max_wait: int = 3600):
        """
        مانیتور کردن یک آدرس تا زمان دریافت مبلغ مشخص
        address: آدرس ترون کاربر
        expected_amount: مبلغ مورد انتظار به USDT
        check_interval: فاصله بین هر چک (ثانیه)
        max_wait: حداکثر زمان انتظار (ثانیه)
        """
        start_time = datetime.now()
        checked_txids = set()
        
        while (datetime.now() - start_time).seconds < max_wait:
            transactions = await self.get_transaction_history(address)
            
            for tx in transactions:
                txid = tx.get("txID")
                
                # اگر این تراکنش قبلاً بررسی شده، رد شو
                if txid in checked_txids:
                    continue
                
                # بررسی تراکنش‌های USDT
                if "raw_data" in tx and "contract" in tx["raw_data"]:
                    for contract in tx["raw_data"]["contract"]:
                        if contract.get("type") == "TransferContract":
                            # اینجا باید بررسی کنی که مبلغ و USDT بودن رو چک کنی
                            # کد کامل‌تر نیاز به دیکد کردن داده‌ها دارد
                            pass
            
            checked_txids.update([tx.get("txID") for tx in transactions if tx.get("txID")])
            await asyncio.sleep(check_interval)
        
        return None
    
    async def generate_deposit_address(self, user_id: int) -> str:
        """
        تولید آدرس جدید برای هر کاربر (با استفاده از کلید عمومی صرافی)
        در عمل باید از یک کلید مستر برای تولید آدرس‌های یکتا استفاده کنی
        """
        # اینجا باید آدرس جدیدی برای کاربر تولید کنی
        # برای شروع می‌توانی از یک آدرس ثابت استفاده کنی
        return "TRpR1vXhCvLJxNv6qX8jXxvR7qX9yXpXxX"  # آدرس نمونه


# نمونه استفاده در ربات
async def process_tron_deposit(user_telegram_id: int, amount: float, txid: str):
    """
    پردازش واریز ارز دیجیتال
    """
    # اضافه کردن مبلغ به کیف پول کاربر
    db.add_balance(user_telegram_id, amount)
    
    # ثبت تراکنش در دیتابیس
    db.add_deposit_request(user_telegram_id, amount, "USDT", txid)
    
    # اینجا می‌توانی به کاربر پیام بدی
    await bot.send_message(user_telegram_id, f"✅ واریز {amount} USDT با موفقیت انجام شد.")