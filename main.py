# patch_imghdr
import sys, types
if not hasattr(sys, 'imghdr'):
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda f, h=None: None
    sys.modules['imghdr'] = imghdr

import asyncio
import logging
from dotenv import load_dotenv
import config
from toobit_client import toobit_client
from database import init_db
from wallet import get_balance, add_balance, deduct_balance
from subscription import get_user_subscription, upgrade_subscription
from payment import request_deposit
from trading import place_limit_order_with_sltp
from payment_monitor import start_monitoring

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- توابع کمکی -------------------
def is_authorized(user_id: int) -> bool:
    return True if config.ADMIN_USER_ID == 0 else user_id == config.ADMIN_USER_ID

def validate_order_input(symbol, qty_str, price_str):
    if not config.is_valid_symbol(symbol):
        return False, "❌ جفت‌ارز پشتیبانی نمی‌شود"
    try:
        qty = float(qty_str)
        price = float(price_str)
        if qty <= 0 or price <= 0:
            return False, "❌ مقدار و قیمت باید مثبت باشند"
        if qty < config.get_min_qty(symbol):
            return False, f"❌ حداقل مقدار {config.get_min_qty(symbol)}"
        return True, ""
    except:
        return False, "❌ مقدار و قیمت باید عدد باشند"

# ------------------- هندلرهای اصلی -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    user = update.effective_user
    # ثبت کاربر در دیتابیس (ایجاد خودکار در wallet انجام می‌شود)
    keyboard = [
        [InlineKeyboardButton("💰 کیف پول", callback_data='wallet')],
        [InlineKeyboardButton("📊 قیمت", callback_data='price')],
        [InlineKeyboardButton("🛒 خرید ساده", callback_data='buy_simple')],
        [InlineKeyboardButton("🎯 خرید حرفه‌ای", callback_data='buy_advanced')],
        [InlineKeyboardButton("📋 سفارشات باز", callback_data='open_orders')],
        [InlineKeyboardButton("⭐ اشتراک", callback_data='subscription')],
        [InlineKeyboardButton("💳 شارژ", callback_data='deposit')],
        [InlineKeyboardButton("📈 سیگنال", callback_data='signal')],
        [InlineKeyboardButton("🪙 جفت‌ارزها", callback_data='pairs')],
        [InlineKeyboardButton("❓ راهنما", callback_data='help')]
    ]
    await update.message.reply_text(
        "🤖 به ربات پیشرفته Toobit خوش آمدید",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    bal = await get_balance(update.effective_user.id)
    tier = await get_user_subscription(update.effective_user.id)
    name = config.SUBSCRIPTION_TIERS[tier]["name"]
    await update.message.reply_text(f"💰 موجودی: {bal:.2f} USDT\n⭐ سطح: {name}")

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ /price BTCUSDT")
        return
    symbol = context.args[0].upper()
    if not config.is_valid_symbol(symbol):
        await update.message.reply_text("جفت‌ارز نامعتبر")
        return
    try:
        ticker = toobit_client.market_get_ticker(symbol=symbol)
        price = ticker.get('lastPrice', 'نامشخص')
        await update.message.reply_text(f"💵 قیمت {symbol}: {price}")
    except:
        await update.message.reply_text("❌ خطا")

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("❗ /buy SYMBOL QTY PRICE")
        return
    symbol, qty, price = context.args
    valid, msg = validate_order_input(symbol, qty, price)
    if not valid:
        await update.message.reply_text(msg)
        return
    try:
        order = toobit_client.place_order(symbol=symbol, side="BUY", type="LIMIT", quantity=qty, price=price)
        fee = float(qty) * float(price) * (config.BASE_FEE / 100)
        if not await deduct_balance(update.effective_user.id, fee):
            await update.message.reply_text("⚠️ موجودی کیف پول برای کارمزد کافی نیست")
            return
        await update.message.reply_text(f"✅ سفارش خرید ثبت شد. ID: {order.get('orderId')}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # مشابه buy فقط side=SELL
    pass

async def open_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        orders = toobit_client.get_open_orders()
        if not orders:
            await update.message.reply_text("📭 سفارش باز وجود ندارد")
            return
        text = "\n".join([f"{o['orderId']} | {o['symbol']}" for o in orders[:10]])
        await update.message.reply_text(f"📋 سفارشات باز:\n{text}")
    except:
        await update.message.reply_text("❌ خطا")

async def cancel_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ /cancel ORDER_ID")
        return
    try:
        toobit_client.cancel_order(orderId=context.args[0])
        await update.message.reply_text("✅ لغو شد")
    except:
        await update.message.reply_text("❌ خطا")

async def pairs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🪙 " + ", ".join(config.SYMBOLS_LIST[:30]))

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 سیگنال آزمایشی: BTCUSDT خرید در 48000")

# ------------------- منوهای جدید (کیف پول، اشتراک، شارژ) -------------------
async def wallet_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await balance_command(update, context)

DEPOSIT_STATE = 1

async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً به فرمت: 50 USDT txid123 وارد کنید")
    return DEPOSIT_STATE

async def deposit_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) != 3:
        await update.message.reply_text("فرمت اشتباه")
        return DEPOSIT_STATE
    amount, currency, txid = parts
    try:
        amount = float(amount)
    except:
        await update.message.reply_text("مبلغ نامعتبر")
        return DEPOSIT_STATE
    if currency.upper() not in config.SUPPORTED_DEPOSIT_TOKENS:
        await update.message.reply_text("ارز پشتیبانی نمی‌شود")
        return DEPOSIT_STATE
    result = await request_deposit(update.effective_user.id, amount, currency.upper(), txid)
    if result:
        await update.message.reply_text("✅ درخواست شارژ ثبت شد. پس از تأیید ادمین موجودی افزوده می‌شود.")
        await context.bot.send_message(config.ADMIN_USER_ID,
            f"درخواست شارژ:\nکاربر: {update.effective_user.id}\nمبلغ: {amount} {currency}\nTXID: {txid}")
    else:
        await update.message.reply_text("❌ خطا (شاید txid تکراری)")
    return ConversationHandler.END

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for tier, price in config.SUBSCRIPTION_PRICES_USDT.items():
        keyboard.append([InlineKeyboardButton(
            f"{config.SUBSCRIPTION_TIERS[tier]['name']} - {price} USDT",
            callback_data=f"sub_{tier}"
        )])
    await update.message.reply_text("⭐ انتخاب سطح اشتراک:", reply_markup=InlineKeyboardMarkup(keyboard))

async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tier = query.data.split("_")[1]
    price = config.SUBSCRIPTION_PRICES_USDT[tier]
    user_balance = await get_balance(query.from_user.id)
    if user_balance >= price:
        if await deduct_balance(query.from_user.id, price):
            success = await upgrade_subscription(query.from_user.id, tier)
            if success:
                await query.edit_message_text(f"✅ اشتراک {config.SUBSCRIPTION_TIERS[tier]['name']} فعال شد (۳۰ روز)")
            else:
                await query.edit_message_text("❌ خطا در فعالسازی")
        else:
            await query.edit_message_text("❌ خطا در کسر موجودی")
    else:
        await query.edit_message_text(f"❌ موجودی کافی نیست. نیاز به {price} USDT")

# ------------------- هندلر پیشرفته -------------------
ADV_ORDER_STATE = 1

async def adv_order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("فرمت: SYMBOL SIDE QTY PRICE SL TP\nمثال: BTCUSDT BUY 0.001 50000 49000 52000")
    return ADV_ORDER_STATE

async def adv_order_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 5:
        await update.message.reply_text("فرمت ناقص")
        return ADV_ORDER_STATE
    symbol, side, qty, price, sl, tp = parts[0], parts[1].upper(), parts[2], parts[3], parts[4], parts[5] if len(parts)>5 else None
    try:
        qty = float(qty); price = float(price); sl = float(sl) if sl else None; tp = float(tp) if tp else None
    except:
        await update.message.reply_text("مقادیر نامعتبر")
        return ADV_ORDER_STATE
    success, msg = await place_limit_order_with_sltp(update.effective_user.id, symbol, side, qty, price, sl, tp)
    await update.message.reply_text(f"نتیجه: {msg}")
    return ConversationHandler.END

# ------------------- CallbackQuery -------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'wallet':
        await balance_command(update, context)
    elif data == 'price':
        await query.edit_message_text("🔍 از /price BTCUSDT استفاده کنید")
    elif data == 'buy_simple':
        await query.edit_message_text("دستور: /buy BTCUSDT 0.001 25000")
    elif data == 'buy_advanced':
        await query.edit_message_text("دستور: /advanced")
    elif data == 'open_orders':
        await open_orders_command(update, context)
    elif data == 'subscription':
        await subscription_menu(update, context)
    elif data == 'deposit':
        await deposit_start(update, context)
    elif data == 'signal':
        await signal_command(update, context)
    elif data == 'pairs':
        await pairs_command(update, context)
    elif data == 'help':
        await update.message.reply_text("/help")
    elif data.startswith('sub_'):
        await subscription_callback(update, context)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ دستور نامعتبر")

# ------------------- راه‌اندازی -------------------
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_main())

async def async_main():
    await init_db()
    # ایجاد کاربر ادمین در دیتابیس (اگر وجود نداشته باشد)
    # می‌توانید در همین جا یک بررسی انجام دهید
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("sell", sell_command))
    app.add_handler(CommandHandler("open_orders", open_orders_command))
    app.add_handler(CommandHandler("cancel", cancel_order_command))
    app.add_handler(CommandHandler("pairs", pairs_command))
    app.add_handler(CommandHandler("wallet", wallet_info))
    app.add_handler(CommandHandler("subscribe", subscription_menu))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("advanced", adv_order_start))
    
    # مکالمه شارژ
    deposit_conv = ConversationHandler(
        entry_points=[CommandHandler("deposit", deposit_start)],
        states={DEPOSIT_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_receive)]},
        fallbacks=[]
    )
    app.add_handler(deposit_conv)
    
    # مکالمه سفارش پیشرفته
    adv_conv = ConversationHandler(
        entry_points=[CommandHandler("advanced", adv_order_start)],
        states={ADV_ORDER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adv_order_receive)]},
        fallbacks=[]
    )
    app.add_handler(adv_conv)
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.COMMAND, unknown))
    
    # اجرای مانیتور پرداخت در پس‌زمینه
    asyncio.create_task(start_monitoring())
    
    # شروع ربات (polling)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("🚀 ربات روشن شد")
    # نگه داشتن
    await asyncio.Event().wait()

if __name__ == "__main__":
    main()