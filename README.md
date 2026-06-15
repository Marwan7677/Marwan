# ربات معاملاتی Toobit (tooobittradebot)

ربات تلگرامی برای معامله در صرافی Toobit

## نحوه راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 2. تنظیم فایل .env
فایل `.env` را باز کنید و مقادیر را بررسی کنید (کلیدها از قبل داخلش هستند).

### 3. اجرای ربات
```bash
python main.py
```

## دستورات ربات
- `/start` - منوی اصلی
- `/balance` - موجودی
- `/price BTCUSDT` - قیمت لحظه‌ای
- `/buy BTCUSDT 0.001 25000` - خرید
- `/sell BTCUSDT 0.001 26000` - فروش
- `/open_orders` - سفارشات باز
- `/cancel <orderId>` - لغو سفارش
- `/pairs` - لیست جفت‌ارزها

---

**نکته امنیتی:** کلیدهای API را به هیچ‌کس ندهید و در محیط production از فایل .env محافظت کنید.
