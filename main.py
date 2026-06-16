"""
ربات اصلی با پشتیبانی از PostgreSQL، WebSocket و اعلانات
"""

import sys
import types
import logging
import os
from dotenv import load_dotenv

# تصحیح imghdr برای Python 3.13+
try:
    import imghdr
except ImportError:
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda f, h=None: None
    sys.modules['imghdr'] = imghdr

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

from config import (
    BOT_TOKEN, ADMIN_USER_ID, TOOBIT_API_KEY, TOOBIT_SECRET_KEY,
    DATABASE_URL, TOOBIT_WS_URL, ENABLE_PRICE_ALERTS
)
from database import Database
from trading_system import TradingSystem
from payment_gateway import PaymentGateway
from ui_helpers import KeyboardBuilder, TextFormatter, ValidationHelper
from price_updater import PriceUpdater
from alert_system import AlertSystem

# ====================== لاگینگ ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("toobit_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================== مقداردهی اولیه ======================
db = Database(DATABASE_URL)
trading_system = TradingSystem(TOOBIT_API_KEY, TOOBIT_SECRET_KEY, db)
payment_gateway = PaymentGateway(db)
price_updater = PriceUpdater(TOOBIT_WS_URL)

# ====================== State IDs ======================
(WAITING_AMOUNT, WAITING_SYMBOL, WAITING_QUANTITY, WAITING_PRICE,
 WAITING_PAYMENT_METHOD, WAITING_CONFIRMATION, WAITING_ALERT_PRICE) = range(7)

# ====================== توابع کمکی ======================
async def ensure_user_exists(user_id: int, user):
    if not await db.get_user(user_id):
        await db.add_user(
            user_id=user_id,
            username=user.username or "unknown",
            first_name=user.first_name or "کاربر",
            last_name=user.last_name or ""
        )

# ====================== دستورات اصلی ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_exists(user.id, user)
    text = f"""
🤖 **خوش آمدید به ربات معاملاتی Toobit!**

سلام {user.first_name} 👋

این ربات با **قیمت‌های لحظه‌ای** و **سیستم اعلانات** هوشمند در خدمت شماست.

🎯 از منوی زیر استفاده کنید:
"""
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 **راهنمای کامل**

**دستورات اصلی:**
/start - منوی اصلی
/help - راهنما
/wallet - کیف‌پول
/trading - مرکز ترید
/prices - قیمت‌ها
/subscription - اشتراک‌ها
/alerts - مدیریت اعلانات

**نکات مهم:**
💡 برای محافظت از حساب، API key خود را شاه نگذارید
💡 قبل از هر معامله، مبلغ و نماد را بررسی کنید
💡 فقط اصلی‌ترین ارزهای دیجیتال را معامله کنید
"""
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('main')
    )

# ====================== کیف‌پول ======================
async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    wallets = await db.get_all_wallets(user_id)
    total_usdt = sum(w['balance'] for w in wallets if w['currency'] == 'USDT')
    text = TextFormatter.wallet_info(wallets, total_usdt)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.wallet_menu()
    )

async def add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "💰 **افزودن موجودی**\n\nمبلغ مورد نظر را وارد کنید (USDT):"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('wallet')
    )
    return WAITING_AMOUNT

# ====================== ترید ======================
async def trading_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    text = f"""
📊 **مرکز معامله**

👤 **کاربر:** {user.get('first_name')}
⭐ **تیر:** {user.get('tier')}

برای شروع معامله، یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.trading_menu()
    )

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    popular_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
    keyboard = []
    for pair in popular_pairs:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f'buy_select_{pair}')])
    keyboard.append([InlineKeyboardButton("🔍 جستجو", callback_data='search_buy')])
    keyboard.append([InlineKeyboardButton("◀️ برگشت", callback_data='trading')])
    text = "🟢 **خرید**\n\nیکی از جفت‌ارزها را انتخاب کنید یا جستجو کنید:"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.replace('buy_select_', '')
    ticker = await trading_system.get_ticker(symbol)
    if not ticker:
        await query.edit_message_text("❌ نتوانستم قیمت را دریافت کنم")
        return
    text = f"""
🟢 **خرید {symbol}**

💵 **قیمت فعلی:** {ticker.get('price', 0):.8f}
📈 **تغییر 24 ساعت:** {ticker.get('changePercent24h', 0):+.2f}%

مقدار موردنظر را وارد کنید:
"""
    context.user_data['buy_symbol'] = symbol
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('trading')
    )
    return WAITING_QUANTITY

# ====================== اشتراک ======================
async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    text = f"""
⭐ **پلان‌های اشتراک**

🎯 **تیر فعلی:** {user.get('tier')}

برای مشاهدهٔ جزئیات هر پلان، روی آن کلیک کنید:
"""
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.subscription_menu(user.get('tier'))
    )

async def tier_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tiers = await db.get_all_tiers()
    text = TextFormatter.subscription_table(tiers)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('subscription')
    )

async def tier_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tier_name = query.data.replace('tier_', '')
    tier = await db.get_tier_config(tier_name)
    if not tier:
        await query.answer("❌ تیر یافت نشد", show_alert=True)
        return
    text = f"""
{tier.get('emoji')} **{tier.get('tier_name')}**

💵 **قیمت:**
  📅 {tier.get('price_monthly'):,.0f} تومان / ماه
  📗 {tier.get('price_yearly'):,.0f} تومان / سال

📊 **محدودیت‌ها:**
  🔹 سفارشات روزانه: {tier.get('max_daily_trades') if tier.get('max_daily_trades') > 0 else '∞'}
  🔹 حداکثر حجم: {tier.get('max_order_size') if tier.get('max_order_size') > 0 else '∞'}
  🔹 حداقل حجم: {tier.get('min_order_size')}
  🔹 هزینهٔ برداشت: {tier.get('withdrawal_fee')}%

✨ **ویژگی‌ها:**
{tier.get('description')}

برای خریج، مدت زمان را انتخاب کنید:
"""
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.duration_menu(tier_name)
    )

# ====================== قیمت‌ها ======================
async def prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    popular = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
    keyboard = []
    for symbol in popular:
        ticker = await trading_system.get_ticker(symbol)
        if ticker:
            price = ticker.get('price', 0)
            change = ticker.get('changePercent24h', 0)
            change_emoji = "📈" if change >= 0 else "📉"
            label = f"{change_emoji} {symbol} {price:.0f}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f'price_detail_{symbol}')])
    keyboard.append([InlineKeyboardButton("🔍 جستجو", callback_data='search_price')])
    keyboard.append([InlineKeyboardButton("◀️ برگشت", callback_data='main')])
    text = "📊 **قیمت‌های لحظه‌ای**\n\nیکی از ارزها را انتخاب کنید:"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def price_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.replace('price_detail_', '')
    ticker = await trading_system.get_ticker(symbol)
    if not ticker:
        await query.edit_message_text("❌ نتوانستم قیمت را دریافت کنم")
        return
    text = TextFormatter.price_chart(symbol, ticker)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('prices')
    )

# ====================== اعلانات قیمت ======================
async def alerts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    alerts = await db.get_user_alerts(user_id)
    text = "🔔 **اعلانات قیمت شما**\n\n"
    if alerts:
        for alert in alerts:
            status = "✅ فعال" if alert['is_active'] else "❌ غیرفعال"
            text += f"• {alert['symbol']} -> {alert['target_price']} ({alert['direction']}) - {status}\n"
    else:
        text += "هیچ اعلانی ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("➕ افزودن اعلان جدید", callback_data='add_alert')],
        [InlineKeyboardButton("◀️ برگشت", callback_data='main')]
    ]
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔔 **تنظیم اعلان قیمت**\n\n"
        "لطفاً جفت‌ارز (مثلاً BTCUSDT) را وارد کنید:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('alerts')
    )
    context.user_data['alert_step'] = 'symbol'
    return WAITING_SYMBOL

async def handle_alert_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get('alert_step')
    if step == 'symbol':
        symbol = update.message.text.upper()
        context.user_data['alert_symbol'] = symbol
        context.user_data['alert_step'] = 'price'
        await update.message.reply_text(
            f"💰 قیمت هدف برای {symbol} را وارد کنید (عدد):",
            reply_markup=KeyboardBuilder.back_menu('alerts')
        )
        return WAITING_ALERT_PRICE
    elif step == 'price':
        try:
            target = float(update.message.text)
            context.user_data['alert_price'] = target
            context.user_data['alert_step'] = 'direction'
            keyboard = [
                [InlineKeyboardButton("📈 بالاتر از", callback_data='alert_above')],
                [InlineKeyboardButton("📉 پایین‌تر از", callback_data='alert_below')],
                [InlineKeyboardButton("◀️ لغو", callback_data='alerts')]
            ]
            await update.message.reply_text(
                f"🎯 قیمت هدف: {target}\n"
                "چه زمانی اعلان بفرستم؟",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_CONFIRMATION
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
            return WAITING_ALERT_PRICE
    return ConversationHandler.END

async def alert_direction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction = 'above' if query.data == 'alert_above' else 'below'
    user_id = update.effective_user.id
    symbol = context.user_data.get('alert_symbol')
    target = context.user_data.get('alert_price')
    if not symbol or not target:
        await query.edit_message_text("❌ خطا: اطلاعات ناقص")
        return
    alert_id = await db.add_price_alert(user_id, symbol, target, direction)
    if alert_id:
        await query.edit_message_text(
            f"✅ اعلان با موفقیت ثبت شد!\n"
            f"🔔 {symbol} -> {target} ({direction})",
            reply_markup=KeyboardBuilder.back_menu('alerts')
        )
    else:
        await query.edit_message_text("❌ خطا در ثبت اعلان")
    context.user_data.clear()

# ====================== تنظیمات ======================
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل", callback_data='profile')],
        [InlineKeyboardButton("🔔 اعلانات قیمت", callback_data='alerts')],
        [InlineKeyboardButton("🔐 امنیت", callback_data='security')],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
        [InlineKeyboardButton("◀️ برگشت", callback_data='main')]
    ]
    text = "⚙️ **تنظیمات**\n\nیکی از بخش‌ها را انتخاب کنید:"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    tier = await db.get_tier_config(user.get('tier'))
    subscription = await db.get_active_subscription(user_id)
    text = TextFormatter.user_profile(user, tier, subscription)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('settings')
    )

# ====================== هندلر پیام ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # اینجا می‌توانید منطق دریافت مبلغ و ... را پیاده کنید
    pass

# ====================== Main ======================
async def main():
    await db.init_pool()
    await price_updater.start()

    app = Application.builder().token(BOT_TOKEN).build()
    alert_system = AlertSystem(db, price_updater, app.bot)
    if ENABLE_PRICE_ALERTS:
        await alert_system.start()

    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CallbackQueryHandler(wallet_callback, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(add_balance_callback, pattern="^add_balance$"))

    app.add_handler(CallbackQueryHandler(trading_callback, pattern="^trading$"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_menu$"))
    app.add_handler(CallbackQueryHandler(buy_select_callback, pattern="^buy_select_"))

    app.add_handler(CallbackQueryHandler(subscription_callback, pattern="^subscription$"))
    app.add_handler(CallbackQueryHandler(tier_info_callback, pattern="^tier_info$"))
    app.add_handler(CallbackQueryHandler(tier_selection_callback, pattern="^tier_"))

    app.add_handler(CallbackQueryHandler(prices_callback, pattern="^prices$"))
    app.add_handler(CallbackQueryHandler(price_detail_callback, pattern="^price_detail_"))

    app.add_handler(CallbackQueryHandler(alerts_callback, pattern="^alerts$"))
    app.add_handler(CallbackQueryHandler(add_alert_callback, pattern="^add_alert$"))
    app.add_handler(CallbackQueryHandler(alert_direction_callback, pattern="^alert_"))

    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(profile_callback, pattern="^profile$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ConversationHandler برای اعلانات
    alert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_alert_callback, pattern="^add_alert$")],
        states={
            WAITING_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_input)],
            WAITING_ALERT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_input)],
            WAITING_CONFIRMATION: [CallbackQueryHandler(alert_direction_callback, pattern="^alert_")]
        },
        fallbacks=[CallbackQueryHandler(alerts_callback, pattern="^alerts$")]
    )
    app.add_handler(alert_conv)

    logger.info("✅ ربات با PostgreSQL و WebSocket شروع شد")
    await app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
