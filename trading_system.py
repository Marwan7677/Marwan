"""
سیستم ترید و مدیریت سفارشات
"""

from typing import Dict, List, Optional, Tuple
from toobit_api.toobit_api import TooBitAPI
import asyncio
from datetime import datetime


class TradingSystem:
    """مدیریت ترید و سفارشات"""
    
    def __init__(self, api_key: str, api_secret: str, db):
        self.client = TooBitAPI(api_key, api_secret)
        self.db = db
        self.cache_prices = {}
        self.cache_timestamp = {}

    # ==================== قیمت‌ها ====================
    def get_ticker(self, symbol: str, use_cache: bool = True) -> Optional[Dict]:
        """دریافت اطلاعات قیمتی"""
        try:
            ticker = self.client.market_get_ticker(symbol=symbol)
            
            if ticker:
                self.cache_prices[symbol] = {
                    'price': float(ticker.get('lastPrice', 0)),
                    'high24h': float(ticker.get('high24h', 0)),
                    'low24h': float(ticker.get('low24h', 0)),
                    'volume': float(ticker.get('volume', 0)),
                    'change24h': float(ticker.get('change24h', 0)),
                    'changePercent24h': float(ticker.get('changePercent24h', 0))
                }
                self.cache_timestamp[symbol] = datetime.now()
            
            return self.cache_prices.get(symbol)
        except Exception as e:
            print(f"خطا در دریافت قیمت {symbol}: {e}")
            return None

    def get_all_prices(self) -> Dict:
        """دریافت قیمت تمام ارزها"""
        try:
            tickers = self.client.market_get_tickers()
            prices = {}
            
            if isinstance(tickers, list):
                for ticker in tickers:
                    symbol = ticker.get('symbol')
                    prices[symbol] = {
                        'price': float(ticker.get('lastPrice', 0)),
                        'change24h': float(ticker.get('changePercent24h', 0))
                    }
            
            return prices
        except Exception as e:
            print(f"خطا در دریافت قیمت‌ها: {e}")
            return {}

    def get_price_string(self, symbol: str) -> str:
        """دریافت قیمت به صورت رشته"""
        ticker = self.get_ticker(symbol)
        if not ticker:
            return "نامشخص"
        
        price = ticker.get('price', 0)
        change = ticker.get('changePercent24h', 0)
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        
        emoji = "📈" if change >= 0 else "📉"
        return f"{emoji} {price:.8f} ({change_str})"

    # ==================== سفارشات ====================
    def place_order(self, user_id: int, symbol: str, side: str, 
                   quantity: float, price: float, order_type: str = 'LIMIT') -> Tuple[bool, str, Optional[Dict]]:
        """ثبت سفارش"""
        
        # بررسی محدودیت‌های تیر
        tier_config = self.db.get_tier_config(self.db.get_user_tier(user_id))
        if not tier_config:
            return False, "❌ تیر کاربر نامشخص است", None
        
        max_order_size = tier_config.get('max_order_size', 100)
        min_order_size = tier_config.get('min_order_size', 0.001)
        
        if max_order_size > 0 and quantity > max_order_size:
            return False, f"❌ حداکثر مقدار سفارش: {max_order_size}", None
        
        if quantity < min_order_size:
            return False, f"❌ حداقل مقدار سفارش: {min_order_size}", None
        
        try:
            order = self.client.place_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price
            )
            
            if order and order.get('orderId'):
                # ذخیره در دیتابیس
                self.db.add_order(user_id, symbol, side, quantity, price)
                
                return True, f"✅ سفارش {side} ثبت شد!", order
            else:
                return False, "❌ خطا در ثبت سفارش", None
        
        except Exception as e:
            return False, f"❌ خطا: {str(e)}", None

    def get_open_orders(self, user_id: int = None) -> List[Dict]:
        """دریافت سفارشات باز"""
        try:
            orders = self.client.get_open_orders()
            
            if orders and isinstance(orders, list):
                formatted = []
                for order in orders[:20]:
                    formatted.append({
                        'orderId': order.get('orderId'),
                        'symbol': order.get('symbol'),
                        'side': order.get('side'),
                        'quantity': float(order.get('origQty', 0)),
                        'price': float(order.get('price', 0)),
                        'status': order.get('status'),
                        'time': order.get('time')
                    })
                return formatted
            
            return []
        except Exception as e:
            print(f"خطا در دریافت سفارشات: {e}")
            return []

    def cancel_order(self, order_id: str, symbol: str) -> Tuple[bool, str]:
        """لغو سفارش"""
        try:
            result = self.client.cancel_order(orderId=order_id, symbol=symbol)
            if result:
                return True, f"✅ سفارش {order_id} لغو شد"
            return False, "❌ نتوانستم سفارش را لغو کنم"
        except Exception as e:
            return False, f"❌ خطا: {str(e)}"

    # ==================== موجودی ====================
    def get_account_balance(self) -> Dict:
        """دریافت موجودی حساب"""
        try:
            balance = self.client.account_get_balance()
            
            formatted = {}
            if balance and balance.get('balances'):
                for item in balance['balances']:
                    asset = item.get('asset')
                    free = float(item.get('free', 0))
                    locked = float(item.get('locked', 0))
                    
                    if free > 0 or locked > 0:
                        formatted[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': free + locked
                        }
            
            return formatted
        except Exception as e:
            print(f"خطا در دریافت موجودی: {e}")
            return {}

    def get_balance_string(self, asset: str = 'USDT') -> str:
        """دریافت موجودی به صورت رشته"""
        balance = self.get_account_balance()
        if asset in balance:
            free = balance[asset]['free']
            locked = balance[asset]['locked']
            return f"{free:.8f} (قفل شده: {locked:.8f})"
        return "0"

    # ==================== آمار ====================
    def get_portfolio_stats(self) -> Dict:
        """دریافت آمار پورتفولیو"""
        try:
            balance = self.get_account_balance()
            
            total_usdt = 0
            assets = {}
            
            for asset, amounts in balance.items():
                free = amounts['free']
                
                if asset == 'USDT':
                    total_usdt += free
                else:
                    # دریافت قیمت
                    ticker = self.get_ticker(f"{asset}USDT")
                    if ticker:
                        price = ticker.get('price', 0)
                        total_usdt += free * price
                        assets[asset] = {
                            'amount': free,
                            'price': price,
                            'value': free * price
                        }
            
            return {
                'total_usdt': total_usdt,
                'assets': assets,
                'asset_count': len(assets)
            }
        except Exception as e:
            print(f"خطا در محاسبه آمار: {e}")
            return {}

    # ==================== جفت‌ارزها ====================
    def get_all_pairs(self) -> List[str]:
        """دریافت لیست تمام جفت‌ارزها"""
        try:
            exchange_info = self.client.market_get_exchange_info()
            
            if exchange_info and exchange_info.get('symbols'):
                pairs = [s.get('symbol') for s in exchange_info['symbols'] 
                        if s.get('status') == 'TRADING']
                return sorted(pairs)
            
            return []
        except Exception as e:
            print(f"خطا در دریافت جفت‌ارزها: {e}")
            return []

    def search_pair(self, keyword: str) -> List[str]:
        """جستجوی جفت‌ارز"""
        all_pairs = self.get_all_pairs()
        keyword = keyword.upper()
        return [p for p in all_pairs if keyword in p]

    # ==================== تاریخچه ====================
    def get_user_trade_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """دریافت تاریخچه معاملات کاربر"""
        orders = self.db.get_user_orders(user_id, limit)
        
        formatted = []
        for order in orders:
            ticker = self.get_ticker(order.get('symbol'))
            current_price = ticker.get('price', 0) if ticker else 0
            
            formatted.append({
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'quantity': order.get('quantity'),
                'price': order.get('price'),
                'current_price': current_price,
                'status': order.get('status'),
                'created_at': order.get('created_at'),
                'profit_loss': (current_price - order.get('price', 0)) * order.get('quantity', 0)
            })
        
        return formatted

    # ==================== موارد نرخ ====================
    def get_trading_rules(self, symbol: str) -> Optional[Dict]:
        """دریافت قوانین ترید"""
        try:
            exchange_info = self.client.market_get_exchange_info()
            
            if exchange_info and exchange_info.get('symbols'):
                for s in exchange_info['symbols']:
                    if s.get('symbol') == symbol:
                        return {
                            'symbol': symbol,
                            'baseAsset': s.get('baseAsset'),
                            'quoteAsset': s.get('quoteAsset'),
                            'baseAssetPrecision': s.get('baseAssetPrecision'),
                            'quotePrecision': s.get('quotePrecision'),
                            'orderTypes': s.get('orderTypes', []),
                            'icebergAllowed': s.get('icebergAllowed', False),
                            'filters': s.get('filters', [])
                        }
            
            return None
        except Exception as e:
            print(f"خطا در دریافت قوانین: {e}")
            return None

    # ==================== اطلاعات بیشتر ====================
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[Dict]:
        """دریافت شمع‌های قیمتی"""
        try:
            klines = self.client.market_get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            formatted = []
            if klines and isinstance(klines, list):
                for kline in klines:
                    formatted.append({
                        'time': kline[0],
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    })
            
            return formatted
        except Exception as e:
            print(f"خطا در دریافت شمع‌ها: {e}")
            return []
