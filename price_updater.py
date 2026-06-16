"""
دریافت قیمت‌های لحظه‌ای از Toobit از طریق WebSocket + Fallback REST
"""

import asyncio
import json
import logging
from typing import Dict, Optional
import websockets
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class PriceUpdater:
    def __init__(self, ws_url: str, rest_base: str = "https://api.toobit.com"):
        self.ws_url = ws_url
        self.rest_base = rest_base
        self.prices: Dict[str, float] = {}
        self.last_update: Dict[str, datetime] = {}
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._ws_task = asyncio.create_task(self._websocket_loop())
        logger.info("PriceUpdater started")

    async def stop(self):
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        logger.info("PriceUpdater stopped")

    async def _websocket_loop(self):
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT', 'LTCUSDT']
                    subscribe_msg = {
                        "symbol": ",".join(symbols),
                        "topic": "realtimes",
                        "event": "sub",
                        "params": {
                            "limit": 10,
                            "binary": "false"
                        }
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"Subscribed to realtimes for: {symbols}")

                    async for message in ws:
                        data = json.loads(message)
                        # ساختار پاسخ Toobit: {"data": {"symbol": "BTCUSDT", "lastPrice": "..."}, ...}
                        if 'data' in data:
                            ticker = data['data']
                            symbol = ticker.get('symbol')
                            price = ticker.get('lastPrice')
                            if symbol and price:
                                self.prices[symbol] = float(price)
                                self.last_update[symbol] = datetime.now()
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)

    async def get_price(self, symbol: str) -> Optional[float]:
        symbol = symbol.upper()
        if symbol in self.prices and (datetime.now() - self.last_update.get(symbol, datetime.min)).seconds < 30:
            return self.prices[symbol]

        # Fallback REST
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.rest_base}/api/v3/ticker/price?symbol={symbol}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = float(data.get('price', 0))
                        if price:
                            self.prices[symbol] = price
                            self.last_update[symbol] = datetime.now()
                            return price
        except Exception as e:
            logger.error(f"REST fallback error for {symbol}: {e}")
        return None

    def get_all_prices(self) -> Dict[str, float]:
        return self.prices.copy()