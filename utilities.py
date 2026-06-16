"""
توابع کمکی و ابزار پشتیبانی (Utilities)
"""

import re
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """تبدیل‌کنندهٔ ارزها"""
    
    # نرخ تقریبی (به‌روزرسانی شود)
    RATES = {
        'USDT': {'IRR': 47000},
        'USD': {'IRR': 47000},
        'EUR': {'IRR': 51000},
        'GBP': {'IRR': 59000},
    }
    
    @staticmethod
    def convert(amount: float, from_currency: str, to_currency: str) -> float:
        """تبدیل ارز"""
        if from_currency == to_currency:
            return amount
        
        rates = CurrencyConverter.RATES.get(from_currency, {})
        rate = rates.get(to_currency, 1)
        
        return amount * rate
    
    @staticmethod
    def get_rate(from_currency: str, to_currency: str) -> float:
        """دریافت نرخ تبدیل"""
        return CurrencyConverter.RATES.get(from_currency, {}).get(to_currency, 1)


class PasswordManager:
    """مدیریت رمزهای عبور"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """هش کردن رمز عبور"""
        salt = secrets.token_hex(32)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"
    
    @staticmethod
    def verify_password(password: str, hash_str: str) -> bool:
        """بررسی رمز عبور"""
        try:
            salt, hash_hex = hash_str.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == hash_hex
        except:
            return False
    
    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """تولید رمز عبور تصادفی"""
        return secrets.token_urlsafe(length)


class TextValidator:
    """اعتبارسنجی متون"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """بررسی ایمیل معتبر"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """بررسی شماره تلفن معتبر"""
        phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        return re.match(r'^[0-9]{7,15}$', phone) is not None
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """پاک‌سازی متن از کاراکترهای خطرناک"""
        # حذف HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # حذف Unicode نامعتبر
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        return text.strip()
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """بررسی username معتبر"""
        pattern = r'^[a-zA-Z0-9_-]{3,16}$'
        return re.match(pattern, username) is not None


class NumberFormatter:
    """قالب‌بندی اعداد"""
    
    @staticmethod
    def format_currency(amount: float, currency: str = 'USDT') -> str:
        """قالب‌بندی ارز"""
        if currency == 'IRR':
            return f"{amount:,.0f} ریال"
        elif currency in ['USDT', 'USD']:
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.8f} {currency}"
    
    @staticmethod
    def format_number(number: float, decimals: int = 2) -> str:
        """قالب‌بندی عدد"""
        return f"{number:,.{decimals}f}"
    
    @staticmethod
    def format_percentage(percentage: float) -> str:
        """قالب‌بندی درصد"""
        emoji = "📈" if percentage >= 0 else "📉"
        return f"{emoji} {percentage:+.2f}%"
    
    @staticmethod
    def shorten_number(number: float) -> str:
        """کوتاه‌کردن عدد بزرگ"""
        if number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        else:
            return f"{number:.0f}"


class DateTimeHelper:
    """کمک‌کننده‌های تاریخ و زمان"""
    
    @staticmethod
    def get_persian_date(date_obj = None) -> str:
        """تبدیل تاریخ میلادی به شمسی"""
        if date_obj is None:
            date_obj = datetime.now()
        
        # تقریب ساده (بهتر است از کتابخانه jdatetime استفاده کنید)
        j_year = date_obj.year - 622
        j_month = date_obj.month
        j_day = date_obj.day
        
        return f"{j_year}/{j_month:02d}/{j_day:02d}"
    
    @staticmethod
    def get_time_diff(date_obj) -> str:
        """دریافت تفاوت زمانی"""
        diff = datetime.now() - date_obj
        
        if diff.days > 0:
            return f"{diff.days} روز پیش"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} ساعت پیش"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} دقیقه پیش"
        else:
            return "چند ثانیه پیش"
    
    @staticmethod
    def get_subscription_expire_days(expire_date: str) -> int:
        """دریافت روزهای باقی‌مانده برای انقضای اشتراک"""
        expire = datetime.fromisoformat(expire_date)
        diff = (expire - datetime.now()).days
        return max(diff, 0)
    
    @staticmethod
    def is_expired(expire_date: str) -> bool:
        """بررسی انقضا"""
        expire = datetime.fromisoformat(expire_date)
        return datetime.now() > expire


class SymbolValidator:
    """اعتبارسنجی نمادهای معاملاتی"""
    
    # نمادهای پشتیبانی‌شده
    VALID_SYMBOLS = {
        'BTCUSDT': {'base': 'BTC', 'quote': 'USDT'},
        'ETHUSDT': {'base': 'ETH', 'quote': 'USDT'},
        'BNBUSDT': {'base': 'BNB', 'quote': 'USDT'},
        'ADAUSDT': {'base': 'ADA', 'quote': 'USDT'},
        'XRPUSDT': {'base': 'XRP', 'quote': 'USDT'},
        'DOGEUSDT': {'base': 'DOGE', 'quote': 'USDT'},
        'LTCUSDT': {'base': 'LTC', 'quote': 'USDT'},
        'UNIUSDT': {'base': 'UNI', 'quote': 'USDT'},
        'LINKUSDT': {'base': 'LINK', 'quote': 'USDT'},
        'SUSHIUSDT': {'base': 'SUSHI', 'quote': 'USDT'},
    }
    
    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        """بررسی نماد معتبر"""
        return symbol.upper() in SymbolValidator.VALID_SYMBOLS
    
    @staticmethod
    def get_base_asset(symbol: str) -> Optional[str]:
        """دریافت دارایی پایه"""
        symbol = symbol.upper()
        return SymbolValidator.VALID_SYMBOLS.get(symbol, {}).get('base')
    
    @staticmethod
    def get_quote_asset(symbol: str) -> Optional[str]:
        """دریافت دارایی نقل‌قول"""
        symbol = symbol.upper()
        return SymbolValidator.VALID_SYMBOLS.get(symbol, {}).get('quote')


class RateLimiter:
    """محدود‌کننده‌ی سرعت"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window  # ثانیه
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """بررسی اینکه درخواست مجاز است"""
        now = datetime.now()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # حذف درخواست‌های قدیمی‌تر از time_window
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if (now - req_time).seconds < self.time_window
        ]
        
        # بررسی حد درخواست
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # اضافهٔ درخواست جدید
        self.requests[user_id].append(now)
        return True
    
    def get_remaining_time(self, user_id: int) -> int:
        """دریافت زمان باقی‌مانده"""
        if user_id not in self.requests or not self.requests[user_id]:
            return 0
        
        oldest = self.requests[user_id][0]
        elapsed = (datetime.now() - oldest).seconds
        
        return max(0, self.time_window - elapsed)


class NotificationManager:
    """مدیریت اطلاع‌رسانی"""
    
    @staticmethod
    def create_alert(user_id: int, alert_type: str, message: str) -> dict:
        """ایجاد هشدار"""
        return {
            'user_id': user_id,
            'type': alert_type,
            'message': message,
            'created_at': datetime.now().isoformat(),
            'read': False
        }
    
    @staticmethod
    def format_alert(alert: dict) -> str:
        """قالب‌بندی هشدار"""
        type_emoji = {
            'price': '📊',
            'order': '📋',
            'payment': '💳',
            'subscription': '⭐',
            'warning': '⚠️',
            'success': '✅'
        }
        
        emoji = type_emoji.get(alert.get('type'), '📢')
        return f"{emoji} {alert.get('message')}"


class Logger:
    """لاگینگ سفارشی"""
    
    @staticmethod
    def log_action(user_id: int, action: str, details: str = '') -> None:
        """ثبت اقدام کاربر"""
        logger.info(f"[User {user_id}] {action} - {details}")
    
    @staticmethod
    def log_error(error: Exception, context: str = '') -> None:
        """ثبت خطا"""
        logger.error(f"[ERROR] {context} - {str(error)}", exc_info=True)
    
    @staticmethod
    def log_transaction(user_id: int, tx_type: str, amount: float, currency: str) -> None:
        """ثبت تراکنش"""
        logger.info(f"[TX] User {user_id} - {tx_type} {amount} {currency}")


class PaginationHelper:
    """کمک‌کننده‌ی صفحه‌بندی"""
    
    @staticmethod
    def paginate(items: List, page: int = 1, per_page: int = 10) -> Tuple[List, dict]:
        """صفحه‌بندی لیست"""
        total = len(items)
        pages = (total + per_page - 1) // per_page
        
        start = (page - 1) * per_page
        end = start + per_page
        
        page_items = items[start:end]
        
        info = {
            'current_page': page,
            'total_pages': pages,
            'total_items': total,
            'per_page': per_page
        }
        
        return page_items, info


class CacheHelper:
    """کمک‌کننده‌ی کش"""
    
    def __init__(self, ttl: int = 300):  # 5 دقیقه
        self.cache = {}
        self.ttl = ttl
    
    def set(self, key: str, value) -> None:
        """ذخیره در کش"""
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=self.ttl)
        }
    
    def get(self, key: str):
        """دریافت از کش"""
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if datetime.now() > item['expires_at']:
            del self.cache[key]
            return None
        
        return item['value']
    
    def clear(self) -> None:
        """پاک‌کردن کش"""
        self.cache.clear()


# نمونه‌های global
rate_limiter = RateLimiter(max_requests=20, time_window=60)
cache = CacheHelper(ttl=300)
