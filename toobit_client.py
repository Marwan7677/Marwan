import os
from dotenv import load_dotenv
from toobit_api.toobit_api import TooBitAPI

# بارگذاری فقط یک بار
load_dotenv(dotenv_path="/storage/emulated/0/toobittradebot/.env")

TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")

if not TOOBIT_API_KEY or not TOOBIT_SECRET_KEY:
    raise ValueError("❌ کلیدهای API در فایل .env پیدا نشد!")

# ایجاد کلاینت (singleton)
toobit_client = TooBitAPI(TOOBIT_API_KEY, TOOBIT_SECRET_KEY)

print("✅ کلاینت Toobit با موفقیت بارگذاری شد.")