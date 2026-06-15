from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, Wallet

async def get_or_create_wallet(user_id: int) -> Wallet:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(user_id=user_id, balance_usdt=0.0)
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet

async def add_balance(user_id: int, amount_usdt: float):
    async with AsyncSessionLocal() as session:
        wallet = await get_or_create_wallet(user_id)
        wallet.balance_usdt += amount_usdt
        await session.commit()

async def deduct_balance(user_id: int, amount_usdt: float) -> bool:
    async with AsyncSessionLocal() as session:
        wallet = await get_or_create_wallet(user_id)
        if wallet.balance_usdt >= amount_usdt:
            wallet.balance_usdt -= amount_usdt
            await session.commit()
            return True
        return False

async def get_balance(user_id: int) -> float:
    wallet = await get_or_create_wallet(user_id)
    return wallet.balance_usdt