"""
سیستم بررسی و ارسال اعلانات قیمت
"""

import asyncio
import logging
from typing import Dict, List
from telegram import Bot

logger = logging.getLogger(__name__)


class AlertSystem:
    def __init__(self, db, price_updater, bot: Bot):
        self.db = db
        self.price_updater = price_updater
        self.bot = bot
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("AlertSystem started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AlertSystem stopped")

    async def _check_loop(self):
        while self._running:
            try:
                alerts = await self.db.get_active_alerts()
                for alert in alerts:
                    symbol = alert['symbol']
                    target = float(alert['target_price'])
                    direction = alert['direction']
                    current_price = await self.price_updater.get_price(symbol)
                    if current_price is None:
                        continue
                    triggered = False
                    if direction == 'above' and current_price >= target:
                        triggered = True
                    elif direction == 'below' and current_price <= target:
                        triggered = True

                    if triggered:
                        user_id = alert['user_id']
                        try:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=f"🔔 **اعلان قیمت**\n\n"
                                     f"💰 {symbol} به قیمت `{current_price:.2f}` رسید.\n"
                                     f"🎯 هدف شما: `{target:.2f}` ({direction})",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send alert to {user_id}: {e}")
                        await self.db.trigger_alert(alert['alert_id'])
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check error: {e}")
                await asyncio.sleep(30)