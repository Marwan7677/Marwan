# 📦 فهرست فایل‌های ربات Toobit

## ✨ فایل‌های اصلی

### 🤖 Core Bot Files
```
main_bot.py                  - ربات اصلی و معالج‌های دستور و callback
├── دستورات: /start, /help, /wallet, /trading
├── منوهای inline: wallet, trading, prices, subscription
└── مدیریت وضعیت کاربران
```

### 💾 Database & Storage
```
database.py                  - سیستم مدیریت دیتابیس SQLite
├── جداول: users, wallets, transactions
├── جداول: subscriptions, orders, payments
├── توابع CRUD کاملِ
└── مدیریت اشتراک‌ها
```

### 💰 Payment Gateway
```
payment_gateway.py          - سیستم درگاه‌های پرداخت
├── USDT Wallet
├── انتقال بانکی
├── کارت اعتباری
├── Zarinpal و PayPal
└── مدیریت تراکنش‌ها
```

### 📊 Trading System
```
trading_system.py           - سیستم ترید و مدیریت سفارشات
├── دریافت قیمت‌های لحظه‌ای
├── ثبت و لغو سفارشات
├── مدیریت موجودی
├── تاریخچه معاملات
└── آمار پورتفولیو
```

### 🎨 UI & Helpers
```
ui_helpers.py               - کمک‌کننده‌های رابط کاربری
├── KeyboardBuilder - ساخت کیبوردهای inline
├── TextFormatter - قالب‌بندی متون
├── ValidationHelper - اعتبارسنجی داده‌ها
└── StateManager - مدیریت وضعیت کاربران
```

### ⚙️ Configuration
```
config.py                   - تنظیمات ربات
├── توکن‌های API
├── تنظیمات درگاه‌های پرداخت
├── تنظیمات ترید
└── جداول تیرهای پیش‌فرض
```

### 👨‍💼 Admin Panel
```
admin_panel.py              - پنل مدیریتی
├── آمار سیستم
├── مدیریت کاربران
├── مسدود/رفع مسدودی
├── گزارش درآمد
└── ابزار debugging
```

### 🛠️ Utilities
```
utilities.py                - توابع کمکی
├── CurrencyConverter - تبدیل ارز
├── PasswordManager - مدیریت رمزهای عبور
├── TextValidator - اعتبارسنجی متون
├── NumberFormatter - قالب‌بندی اعداد
├── DateTimeHelper - مدیریت تاریخ و زمان
├── RateLimiter - محدود‌کننده‌ی سرعت
├── CacheHelper - سیستم کش
└── Logger - لاگینگ سفارشی
```

## 📋 فایل‌های تنظیم

```
.env.example                - نمونهٔ متغیرهای محیطی
requirements.txt            - لیست وابستگی‌های Python
setup.py                    - اسکریپت راه‌اندازی خودکار
```

## 📚 فایل‌های مستندات

```
README.md                   - راهنمای کامل ربات
FILES_LIST.md              - این فایل
INSTALLATION.md            - دستورالعمل نصب تفصیلی
```

## 🗄️ فایل‌های خودکار (بعد از اجرا)

```
toobit_bot.db              - دیتابیس SQLite
toobit_bot.log             - فایل لاگ رویدادها
backups/                   - فایل‌های پشتیبانی
logs/                      - فایل‌های لاگ اضافی
data/                      - داده‌های موقتی
```

---

## 🚀 شروع سریع (Quick Start)

### 1️⃣  نصب (5 دقیقه)
```bash
# پایتون 3.9+ را بررسی کنید
python --version

# وابستگی‌ها را نصب کنید
pip install -r requirements.txt

# یا اسکریپت خودکار را اجرا کنید
python setup.py
```

### 2️⃣  تنظیم .env (3 دقیقه)
```bash
# فایل .env را کپی کنید
cp .env.example .env

# و مقادیر الزامی را اضافه کنید:
nano .env
```

**الزامی‌ها:**
- `BOT_TOKEN` - از @BotFather
- `TOOBIT_API_KEY` - از Toobit
- `TOOBIT_SECRET_KEY` - از Toobit

### 3️⃣  اجرا (1 دقیقه)
```bash
python main_bot.py
```

اگر ببینید:
```
✅ ربات شروع شد
🚀 ربات در حال اجراست...
```

تبریک! 🎉

### 4️⃣  استفاده
```
تلگرام → ربات → /start
```

---

## 📊 ارتباط بین فایل‌ها

```
main_bot.py
├── imports: database.py
├── imports: payment_gateway.py
├── imports: trading_system.py
├── imports: ui_helpers.py
├── imports: config.py
├── imports: admin_panel.py
└── imports: utilities.py

database.py
├── creates: toobit_bot.db
└── manages: all data storage

payment_gateway.py
├── uses: database.py
├── creates: payment records
└── manages: transactions

trading_system.py
├── uses: database.py
├── uses: Toobit API
└── manages: orders & prices

ui_helpers.py
├── provides: keyboards
├── provides: text formatting
└── provides: state management
```

---

## 🔐 فایل‌های حساس

⚠️ **هرگز این فایل‌ها را در اینترنت منتشر نکنید:**
- `.env` - متغیرهای محیطی (API keys)
- `toobit_bot.db` - دیتابیسِ کاربران و تراکنش‌ها
- `toobit_bot.log` - لاگ‌های سیستم

✅ **شامل کنید در .gitignore:**
```
.env
*.db
*.log
__pycache__/
.pytest_cache/
backups/
```

---

## 📈 سایز فایل‌ها

| فایل | سایز تقریبی |
|------|-----------|
| main_bot.py | ~15 KB |
| database.py | ~12 KB |
| payment_gateway.py | ~10 KB |
| trading_system.py | ~10 KB |
| ui_helpers.py | ~18 KB |
| admin_panel.py | ~15 KB |
| utilities.py | ~20 KB |
| config.py | ~8 KB |

**کل کد:** ~108 KB (بدون dependency)

---

## ✅ Checklist فایل‌ها

**بررسی اینکه تمام فایل‌ها وجود دارند:**

```
☐ main_bot.py
☐ database.py
☐ payment_gateway.py
☐ trading_system.py
☐ ui_helpers.py
☐ config.py
☐ admin_panel.py
☐ utilities.py
☐ setup.py
☐ requirements.txt
☐ .env.example
☐ README.md
```

---

## 🔄 ترتیب اجرا

```
1. setup.py (نصب)
   ↓
2. .env (تنظیم)
   ↓
3. database.py (دیتابیس)
   ↓
4. main_bot.py (ربات)
   ├── imports: config.py
   ├── imports: database.py
   ├── imports: trading_system.py
   ├── imports: payment_gateway.py
   ├── imports: ui_helpers.py
   ├── imports: admin_panel.py
   └── imports: utilities.py
   ↓
5. آماده برای استفاده! 🎉
```

---

## 🆘 اگر مشکلی داشتید

```bash
# 1. خطای import
python -c "import database; print('OK')"

# 2. مشکل وابستگی
pip list | grep -E "telegram|toobit|dotenv"

# 3. بررسی .env
cat .env | grep -E "BOT_TOKEN|TOOBIT"

# 4. خطای دیتابیس
python -c "from database import db; print('Database OK')"

# 5. بررسی لاگ‌ها
tail -f toobit_bot.log
```

---

## 📞 پشتیبانی

❓ **سؤالی دارید?**
- README.md را بخوانید
- لاگ‌ها را بررسی کنید
- GitHub Issues را چک کنید
- مجتمع را تماس بگیرید

---

**نسخهٔ: 1.0.0**
**آخرین به‌روزرسانی: ۲۰۲۵**
**وضعیت: ✅ فعال**
