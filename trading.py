import asyncio
from toobit_client import toobit_client
from config import get_min_qty, BASE_FEE, SUBSCRIPTION_TIERS
from wallet import deduct_balance, add_balance
from subscription import get_user_subscription
from models import Trade
from database import AsyncSessionLocal
from datetime import datetime

async def place_limit_order_with_sltp(user_telegram_id: int, symbol: str, side: str,
                                      quantity: float, price: float,
                                      sl_price: float = None, tp_price: float = None):
    # دریافت سطح اشتراک و تخفیف
    tier = await get_user_subscription(user_telegram_id)
    discount = SUBSCRIPTION_TIERS[tier]["fee_discount"]
    effective_fee = BASE_FEE * (100 - discount) / 100
    
    estimated_fee = quantity * price * (effective_fee / 100)
    if not await deduct_balance(user_telegram_id, estimated_fee):
        return False, "موجودی کیف پول برای کارمزد کافی نیست"
    
    try:
        order = toobit_client.place_order(symbol=symbol, side=side, type="LIMIT",
                                          quantity=quantity, price=price)
        order_id = order.get("orderId")
        async with AsyncSessionLocal() as session:
            trade = Trade(
                user_id=user_telegram_id,
                symbol=symbol,
                side=side,
                order_id=order_id,
                quantity=quantity,
                price=price,
                fee=estimated_fee,
                status="new"
            )
            session.add(trade)
            await session.commit()
        if sl_price or tp_price:
            # اینجا می‌توان OCO یا Stop Limit اضافه کرد
            pass
        return True, order_id
    except Exception as e:
        await add_balance(user_telegram_id, estimated_fee)
        return False, str(e)