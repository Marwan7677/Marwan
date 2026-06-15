from datetime import datetime, timedelta
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User
from config import SUBSCRIPTION_TIERS, SUBSCRIPTION_PRICES_USDT
from wallet import get_or_create_wallet, deduct_balance

async def get_user_subscription(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user and user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
            return user.subscription_tier
        return "free"

async def upgrade_subscription(telegram_id: int, tier: str) -> bool:
    if tier not in SUBSCRIPTION_PRICES_USDT:
        return False
    price = SUBSCRIPTION_PRICES_USDT[tier]
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        # کیف پول کاربر را بیاور
        wallet = await get_or_create_wallet(user.id)
        if wallet.balance_usdt < price:
            return False
        wallet.balance_usdt -= price
        user.subscription_tier = tier
        user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
        await session.commit()
        return True