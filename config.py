"""
تنظیمات ربات Toobit
"""

import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# ====================== توکن‌های Bot ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))

# ====================== Toobit API ======================
TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")

# ====================== درگاه‌های پرداخت ======================
ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET", "")

# ====================== تنظیمات ربات ======================
BOT_NAME = "Toobit Trade Bot"
BOT_USERNAME = "toobittrade_bot"
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", 0))

# ====================== تنظیمات ترید ======================
MIN_ORDER_AMOUNT = float(os.getenv("MIN_ORDER_AMOUNT", 10.0))
MAX_ORDER_AMOUNT = float(os.getenv("MAX_ORDER_AMOUNT", 100000.0))
DEFAULT_LEVERAGE = float(os.getenv("DEFAULT_LEVERAGE", 1.0))

# ====================== فاصلهٔ زمانی برای کش کردن ======================
CACHE_DURATION = int(os.getenv("CACHE_DURATION", 30))  # ثانیه

# ====================== جفت‌ارزهای محبوب ======================
POPULAR_PAIRS = [
    'BTCUSDT',
    'ETHUSDT',
    'BNBUSDT',
    'ADAUSDT',
    'XRPUSDT',
    'DOGEUSDT',
    'LTCUSDT',
    'UNIUSDT',
    'LINKUSDT',
    'SUSHIUSDT',
]

# ====================== لایه‌های پیش‌فرض ======================
TIER_CONFIG = {
    'free': {
        'price_monthly': 0,
        'price_yearly': 0,
        'max_daily_trades': 5,
        'max_order_size': 50,
        'min_order_size': 0.001,
        'withdrawal_fee': 5.0,
        'features': ['قیمت'],
        'emoji': '🔹'
    },
    'lite': {
        'price_monthly': 50000,
        'price_yearly': 500000,
        'max_daily_trades': 20,
        'max_order_size': 200,
        'min_order_size': 0.001,
        'withdrawal_fee': 3.0,
        'features': ['قیمت', 'سفارش محدود', 'کیف پول'],
        'emoji': '🥉'
    },
    'pro': {
        'price_monthly': 150000,
        'price_yearly': 1400000,
        'max_daily_trades': 50,
        'max_order_size': 500,
        'min_order_size': 0.0001,
        'withdrawal_fee': 2.0,
        'features': ['قیمت', 'سفارش نامحدود', 'کیف پول', 'تاریخچه'],
        'emoji': '🥈'
    },
    'professional': {
        'price_monthly': 300000,
        'price_yearly': 2800000,
        'max_daily_trades': 200,
        'max_order_size': 2000,
        'min_order_size': 0.00001,
        'withdrawal_fee': 1.5,
        'features': ['همه', 'API', 'ربات', 'پشتیبانی VIP'],
        'emoji': '🏆'
    },
    'gold': {
        'price_monthly': 500000,
        'price_yearly': 4500000,
        'max_daily_trades': 500,
        'max_order_size': 5000,
        'min_order_size': 0.000001,
        'withdrawal_fee': 1.0,
        'features': ['همه', 'API', 'ربات', 'پشتیبانی 24/7'],
        'emoji': '⭐'
    },
    'diamond': {
        'price_monthly': 1000000,
        'price_yearly': 9000000,
        'max_daily_trades': -1,  # نامحدود
        'max_order_size': -1,     # نامحدود
        'min_order_size': 0,
        'withdrawal_fee': 0.5,
        'features': ['تمام امکانات', 'اولویت بالا', 'مشاور شخصی'],
        'emoji': '💎'
    }
}

# ====================== پیام‌های پیش‌فرض ======================
MESSAGES = {
    'welcome': '''🤖 خوش آمدید به ربات معاملاتی Toobit!

سلام {user_name} 👋

این ربات به شما اجازه می‌دهد:
✅ معامله مستقیم با صرافی Toobit
✅ مدیریت کیف‌پول شخصی
✅ نمایش قیمت‌های لحظه‌ای
✅ ثبت و لغو سفارشات
✅ بهره‌برداری از پلان‌های حرفه‌ای''',
    
    'help': '''📖 راهنمای کامل

**دستورات اصلی:**
/start - منوی اصلی
/help - راهنما
/wallet - کیف‌پول
/trading - مرکز ترید
/prices - قیمت‌ها
/subscription - اشتراک‌ها

**نکات مهم:**
💡 برای محافظت از حساب، API key خود را شاه نگذارید
💡 قبل از هر معامله، مبلغ و نماد را بررسی کنید
💡 فقط اصلی‌ترین ارزهای دیجیتال را معامله کنید''',
    
    'error': '❌ خطا: {}',
    'success': '✅ موفق: {}',
    'info': 'ℹ️ اطلاعات: {}',
    'warning': '⚠️ هشدار: {}',
}

# ====================== بررسی متغیرهای محیطی ======================
def validate_config():
    """بررسی تنظیمات"""
    errors = []
    
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN در فایل .env یافت نشد")
    
    if not TOOBIT_API_KEY:
        errors.append("❌ TOOBIT_API_KEY در فایل .env یافت نشد")
    
    if not TOOBIT_SECRET_KEY:
        errors.append("❌ TOOBIT_SECRET_KEY در فایل .env یافت نشد")
    
    if errors:
        print("\n".join(errors))
        return False
    
    return True


# ====================== تابع کمکی ======================
def get_tier_config(tier_name: str) -> dict:
    """دریافت تنظیمات تیر"""
    return TIER_CONFIG.get(tier_name, TIER_CONFIG['free'])


def get_message(key: str, **kwargs) -> str:
    """دریافت پیام"""
    msg = MESSAGES.get(key, "")
    if kwargs:
        msg = msg.format(**kwargs)
    return msg


# اعتبارسنجی در زمان import
if __name__ == "__main__":
    if validate_config():
        print("✅ تنظیمات صحیح است")
    else:
        print("❌ خطا در تنظیمات")
