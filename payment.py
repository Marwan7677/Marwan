from datetime import datetime
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Deposit, User
from wallet import add_balance

async def request_deposit(telegram_id: int, amount: float, currency: str, txid: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        deposit = Deposit(
            user_id=user.id,
            amount=amount,
            currency=currency,
            txid=txid,
            status="pending"
        )
        session.add(deposit)
        await session.commit()
        return True

async def confirm_deposit(deposit_id: int, admin_confirm: bool):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Deposit).where(Deposit.id == deposit_id))
        deposit = result.scalar_one_or_none()
        if deposit and deposit.status == "pending":
            if admin_confirm:
                deposit.status = "confirmed"
                deposit.confirmed_at = datetime.utcnow()
                await add_balance(deposit.user_id, deposit.amount)  # فرض می‌کنیم amount بر حسب USDT است
            else:
                deposit.status = "rejected"
            await session.commit()
            return True
        return False