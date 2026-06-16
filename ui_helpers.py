"""
تابع‌های کمکی و رابط کاربری (UI Helpers)
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict, Tuple


class KeyboardBuilder:
    """سازندهٔ صفحه‌کلید"""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """منوی اصلی"""
        keyboard = [
            [InlineKeyboardButton("💰 کیف‌پول", callback_data='wallet'),
             InlineKeyboardButton("🛒 ترید", callback_data='trading')],
            [InlineKeyboardButton("📊 قیمت‌ها", callback_data='prices'),
             InlineKeyboardButton("📋 سفارشات", callback_data='orders')],
            [InlineKeyboardButton("⭐ اشتراک", callback_data='subscription'),
             InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')],
            [InlineKeyboardButton("❓ کمک", callback_data='help')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def wallet_menu() -> InlineKeyboardMarkup:
        """منوی کیف‌پول"""
        keyboard = [
            [InlineKeyboardButton("💵 افزودن موجودی", callback_data='add_balance'),
             InlineKeyboardButton("📤 برداشت", callback_data='withdraw')],
            [InlineKeyboardButton("📈 انتقال", callback_data='transfer'),
             InlineKeyboardButton("📋 تاریخچه", callback_data='wallet_history')],
            [InlineKeyboardButton("◀️ برگشت", callback_data='main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def trading_menu() -> InlineKeyboardMarkup:
        """منوی ترید"""
        keyboard = [
            [InlineKeyboardButton("🟢 خرید", callback_data='buy_menu'),
             InlineKeyboardButton("🔴 فروش", callback_data='sell_menu')],
            [InlineKeyboardButton("📊 قیمت لحظه‌ای", callback_data='instant_price'),
             InlineKeyboardButton("🔍 جستجو", callback_data='search_pair')],
            [InlineKeyboardButton("📈 تاریخچه", callback_data='trade_history'),
             InlineKeyboardButton("◀️ برگشت", callback_data='main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def orders_menu() -> InlineKeyboardMarkup:
        """منوی سفارشات"""
        keyboard = [
            [InlineKeyboardButton("🕐 سفارشات باز", callback_data='open_orders'),
             InlineKeyboardButton("✅ سفارشات تکمیل", callback_data='completed_orders')],
            [InlineKeyboardButton("🗑️ سفارشات لغو شده", callback_data='cancelled_orders')],
            [InlineKeyboardButton("◀️ برگشت", callback_data='main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def subscription_menu(current_tier: str = 'free') -> InlineKeyboardMarkup:
        """منوی اشتراک‌ها"""
        keyboard = [
            [InlineKeyboardButton("🥉 لایت", callback_data='tier_lite'),
             InlineKeyboardButton("🥈 پرو", callback_data='tier_pro')],
            [InlineKeyboardButton("🏆 حرفه‌ای", callback_data='tier_professional'),
             InlineKeyboardButton("⭐ طلایی", callback_data='tier_gold')],
            [InlineKeyboardButton("💎 الماس", callback_data='tier_diamond')],
            [InlineKeyboardButton("ℹ️ اطلاعات", callback_data='tier_info')],
            [InlineKeyboardButton("◀️ برگشت", callback_data='main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_method_menu() -> InlineKeyboardMarkup:
        """منوی روش‌های پرداخت"""
        keyboard = [
            [InlineKeyboardButton("💳 USDT", callback_data='pay_usdt')],
            [InlineKeyboardButton("🏦 انتقال بانکی", callback_data='pay_bank')],
            [InlineKeyboardButton("💰 کارت اعتباری", callback_data='pay_card')],
            [InlineKeyboardButton("ℹ️ کریپتو", callback_data='pay_crypto')],
            [InlineKeyboardButton("◀️ برگشت", callback_data='wallet')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def duration_menu(tier_name: str) -> InlineKeyboardMarkup:
        """منوی مدت اشتراک"""
        keyboard = [
            [InlineKeyboardButton("📅 یک ماهه", callback_data=f'duration_monthly_{tier_name}'),
             InlineKeyboardButton("📗 سه ماهه (5% تخفیف)", callback_data=f'duration_quarterly_{tier_name}')],
            [InlineKeyboardButton("📕 شش ماهه (10% تخفیف)", callback_data=f'duration_semi_{tier_name}'),
             InlineKeyboardButton("📙 سالانه (15% تخفیف)", callback_data=f'duration_yearly_{tier_name}')],
            [InlineKeyboardButton("◀️ برگشت", callback_data='subscription')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_menu() -> InlineKeyboardMarkup:
        """منوی تأیید"""
        keyboard = [
            [InlineKeyboardButton("✅ تایید", callback_data='confirm'),
             InlineKeyboardButton("❌ لغو", callback_data='cancel')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def yes_no_menu() -> InlineKeyboardMarkup:
        """منوی بله/خیر"""
        keyboard = [
            [InlineKeyboardButton("✅ بله", callback_data='yes'),
             InlineKeyboardButton("❌ خیر", callback_data='no')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_menu(back_to: str = 'main') -> InlineKeyboardMarkup:
        """دکمهٔ برگشت"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ برگشت", callback_data=back_to)]
        ])


class TextFormatter:
    """فرمت‌کننده‌ی متون"""

    @staticmethod
    def user_profile(user: Dict, tier_config: Dict, subscription: Dict = None) -> str:
        """نمایش پروفایل کاربر"""
        text = f"""
🧑 **پروفایل شما**

👤 **نام:** {user.get('first_name', 'نامشخص')} {user.get('last_name', '')}
🆔 **ID:** `{user.get('user_id')}`
📅 **عضویت:** {user.get('created_at', 'نامشخص')[:10]}

⭐ **تیر فعلی:** {tier_config.get('emoji', '')} {user.get('tier', 'رایگان')}
💰 **موجودی کیف‌پول:** {user.get('wallet_balance', 0):.2f} تومان
💸 **کل خریج:** {user.get('total_spent', 0):.2f} تومان
"""
        if subscription and subscription.get('is_active'):
            text += f"\n📌 **انقضای اشتراک:** {subscription.get('end_date', 'نامشخص')[:10]}"
        
        return text

    @staticmethod
    def wallet_info(wallets: List[Dict], total_usdt: float = 0) -> str:
        """نمایش اطلاعات کیف‌پول"""
        text = "💰 **کیف‌پول شما**\n\n"
        
        if wallets:
            for wallet in wallets:
                emoji = "💵" if wallet['currency'] == 'USDT' else "💳"
                text += f"{emoji} **{wallet['currency']}:** {wallet['balance']:.8f}\n"
        else:
            text = "❌ **کیف‌پول خالی است**"
        
        if total_usdt > 0:
            text += f"\n📊 **کل ارزش:** ${total_usdt:.2f}"
        
        return text

    @staticmethod
    def subscription_table(tiers: List[Dict]) -> str:
        """نمایش جدول اشتراک‌ها"""
        text = "⭐ **پلان‌های اشتراک**\n\n"
        
        for tier in tiers:
            text += f"""
{tier.get('emoji', '🔹')} **{tier.get('tier_name', 'Unknown')}**
💵 {tier.get('price_monthly', 0):,.0f} تومان/ماه
📊 **محدودیت‌ها:**
  • سفارشات روزانه: {tier.get('max_daily_trades', '∞')}
  • حداکثر حجم: {tier.get('max_order_size', '∞')}
  • هزینهٔ برداشت: {tier.get('withdrawal_fee', 0)}%

"""
        return text

    @staticmethod
    def order_details(order: Dict, ticker: Dict = None) -> str:
        """نمایش جزئیات سفارش"""
        text = f"""
📋 **جزئیات سفارش**

🏷️ **نماد:** {order.get('symbol')}
↔️ **نوع:** {'🟢 خرید' if order.get('side') == 'BUY' else '🔴 فروش'}
📊 **مقدار:** {order.get('quantity')} {order.get('symbol', '')[:3]}
💵 **قیمت:** {order.get('price')}
⏱️ **وضعیت:** {order.get('status', 'نامشخص')}
📅 **تاریخ:** {order.get('created_at', 'نامشخص')[:19]}
"""
        if ticker:
            change = ticker.get('changePercent24h', 0)
            change_emoji = "📈" if change >= 0 else "📉"
            text += f"\n{change_emoji} **تغییر 24 ساعت:** {change:+.2f}%"
        
        return text

    @staticmethod
    def price_chart(symbol: str, ticker: Dict) -> str:
        """نمایش نمودار قیمت"""
        price = ticker.get('price', 0)
        change = ticker.get('changePercent24h', 0)
        high = ticker.get('high24h', 0)
        low = ticker.get('low24h', 0)
        volume = ticker.get('volume', 0)
        
        change_emoji = "📈" if change >= 0 else "📉"
        
        text = f"""
📊 **قیمت {symbol}**

💵 **قیمت فعلی:** `{price:.8f}`
{change_emoji} **تغییر 24 ساعت:** `{change:+.2f}%`

📈 **بالاترین 24 ساعت:** `{high:.8f}`
📉 **پایین‌ترین 24 ساعت:** `{low:.8f}`
📦 **حجم 24 ساعت:** `{volume:,.0f}`
"""
        return text

    @staticmethod
    def transaction_history(transactions: List[Dict]) -> str:
        """نمایش تاریخچه تراکنش‌ها"""
        text = "📋 **تاریخچه تراکنش‌ها**\n\n"
        
        if transactions:
            for tx in transactions:
                emoji_map = {
                    'deposit': '⬇️',
                    'withdraw': '⬆️',
                    'refund': '🔄',
                    'trade': '💱'
                }
                emoji = emoji_map.get(tx.get('type', 'unknown'), '💰')
                
                text += f"{emoji} {tx.get('type')} | {tx.get('amount')} {tx.get('currency')}\n"
                text += f"   📅 {tx.get('created_at', 'نامشخص')[:10]}\n"
                text += f"   ℹ️ {tx.get('description', 'بدون توضیح')}\n\n"
        else:
            text += "❌ **هیچ تراکنشی یافت نشد**"
        
        return text

    @staticmethod
    def error_message(error: str) -> str:
        """پیام خطا"""
        return f"❌ **خطا:** {error}"

    @staticmethod
    def success_message(message: str) -> str:
        """پیام موفقیت"""
        return f"✅ **موفق:** {message}"

    @staticmethod
    def info_message(message: str) -> str:
        """پیام اطلاعات"""
        return f"ℹ️ **اطلاعات:** {message}"


class ValidationHelper:
    """کمک‌کننده‌ی اعتبارسنجی"""

    @staticmethod
    def validate_amount(amount: str) -> Tuple[bool, float, str]:
        """اعتبارسنجی مبلغ"""
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                return False, 0, "❌ مبلغ باید مثبت باشد"
            return True, amount_float, ""
        except ValueError:
            return False, 0, "❌ مبلغ را درست وارد کنید"

    @staticmethod
    def validate_symbol(symbol: str, valid_symbols: List[str]) -> Tuple[bool, str]:
        """اعتبارسنجی نماد"""
        symbol = symbol.upper()
        if symbol not in valid_symbols:
            return False, f"❌ نماد {symbol} پشتیبانی نمی‌شود"
        return True, symbol

    @staticmethod
    def validate_quantity(quantity: str, min_qty: float) -> Tuple[bool, float, str]:
        """اعتبارسنجی مقدار"""
        try:
            qty = float(quantity)
            if qty < min_qty:
                return False, 0, f"❌ حداقل مقدار: {min_qty}"
            return True, qty, ""
        except ValueError:
            return False, 0, "❌ مقدار را درست وارد کنید"


class StateManager:
    """مدیریت وضعیت کاربران"""

    def __init__(self):
        self.user_states = {}

    def set_state(self, user_id: int, state: str, data: Dict = None):
        """تعیین وضعیت"""
        self.user_states[user_id] = {
            'state': state,
            'data': data or {}
        }

    def get_state(self, user_id: int) -> Tuple[str, Dict]:
        """دریافت وضعیت"""
        if user_id in self.user_states:
            s = self.user_states[user_id]
            return s.get('state', 'none'), s.get('data', {})
        return 'none', {}

    def clear_state(self, user_id: int):
        """پاک‌کردن وضعیت"""
        if user_id in self.user_states:
            del self.user_states[user_id]

    def update_state_data(self, user_id: int, key: str, value):
        """بروزرسانی داده‌های وضعیت"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {'state': 'none', 'data': {}}
        
        self.user_states[user_id]['data'][key] = value
