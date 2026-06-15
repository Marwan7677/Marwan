import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///toobit_bot.db")
MERCHANT_ID = os.getenv("MERCHANT_ID", "")

SUBSCRIPTION_TIERS = {
    "free": {"name": "رایگان", "fee_discount": 0, "max_daily_trades": 5, "signal_access": False},
    "lite": {"name": "لایت", "fee_discount": 10, "max_daily_trades": 20, "signal_access": True},
    "pro": {"name": "حرفه‌ای", "fee_discount": 25, "max_daily_trades": 100, "signal_access": True},
    "gold": {"name": "طلایی", "fee_discount": 40, "max_daily_trades": 500, "signal_access": True},
    "diamond": {"name": "الماس", "fee_discount": 60, "max_daily_trades": 9999, "signal_access": True},
}

SUBSCRIPTION_PRICES_USDT = {
    "lite": 10,
    "pro": 25,
    "gold": 50,
    "diamond": 100,
}

BASE_FEE = 0.1  # 0.1%
SUPPORTED_DEPOSIT_TOKENS = ["USDT", "TRX", "BTC", "ETH"]

PAIRS_CONFIG = {
    "BTCUSDT": {"base": "BTC", "quote": "USDT", "min_qty": 0.00001, "step": 0.00001},
    "BTCUSDC": {"base": "BTC", "quote": "USDC", "min_qty": 0.00001, "step": 0.00001},
    "ETHUSDT": {"base": "ETH", "quote": "USDT", "min_qty": 0.001, "step": 0.001},
    "APTUSDT": {"base": "APT", "quote": "USDT", "min_qty": 0.01, "step": 0.01},
}
DEFAULT_SYMBOL = "BTCUSDT"
SYMBOLS_LIST = list(PAIRS_CONFIG.keys())

def get_pair_config(symbol: str):
    return PAIRS_CONFIG.get(symbol.upper())

def is_valid_symbol(symbol: str) -> bool:
    return symbol.upper() in PAIRS_CONFIG

def get_min_qty(symbol: str) -> float:
    cfg = get_pair_config(symbol)
    return cfg["min_qty"] if cfg else 0.0

def get_step(symbol: str) -> float:
    cfg = get_pair_config(symbol)
    return cfg["step"] if cfg else 0.0