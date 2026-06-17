"""
ربات معاملاتی Toobit - ربات اصلی
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
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode

from database import db
from payment_gateway import PaymentGateway
from trading_system import TradingSystem
from ui_helpers import KeyboardBuilder, TextFormatter, ValidationHelper, StateManager
from config import BOT_TOKEN, TOOBIT_API_KEY, TOOBIT_SECRET_KEY, ADMIN_USER_ID

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

# ====================== سیستم‌ها ======================
payment_gateway = PaymentGateway(db)
trading_system = TradingSystem(TOOBIT_API_KEY, TOOBIT_SECRET_KEY, db)
state_manager = StateManager()

# ====================== State IDs ======================
(WAITING_AMOUNT, WAITING_SYMBOL, WAITING_QUANTITY, WAITING_PRICE, 
 WAITING_PAYMENT_METHOD, WAITING_CONFIRMATION) = range(6)


# ====================== توابع کمکی ======================
async def safe_delete_message(query, delay=0.5):
    """حذف ایمن پیام"""
    try:
        await query.message.delete()
    except:
        pass


async def ensure_user_exists(user_id: int, user):
    """اطمینان از وجود کاربر"""
    if not db.get_user(user_id):
        db.add_user(
            user_id=user_id,
            username=user.username or "unknown",
            first_name=user.first_name or "کاربر",
            last_name=user.last_name or ""
        )


# ====================== دستورات اصلی ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    user_id = user.id
    
    # ایجاد کاربر
    await ensure_user_exists(user_id, user)
    
    text = f"""
🤖 **خوش آمدید به ربات معاملاتی Toobit!**

سلام {user.first_name} 👋

این ربات به شما اجازه می‌دهد:
✅ معامله مستقیم با صرافی Toobit
✅ مدیریت کیف‌پول شخصی
✅ نمایش قیمت‌های لحظه‌ای
✅ ثبت و لغو سفارشات
✅ بهره‌برداری از پلان‌های حرفه‌ای

🎯 برای شروع از دکمه‌های زیر استفاده کنید:
"""
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    text = """
📖 **راهنمای کامل**

**دستورات اصلی:**
/start - منوی اصلی
/profile - نمایش پروفایل
/wallet - کیف‌پول
/trading - مرکز ترید
/orders - مدیریت سفارشات
/prices - قیمت‌ها
/subscription - اشتراک‌ها
/help - راهنما

**نکات مهم:**
💡 برای محافظت از حساب، API key خود را شاه نگذارید
💡 قبل از هر معامله، مبلغ و نماد را بررسی کنید
💡 فقط اصلی‌ترین ارزهای دیجیتال را معامله کنید

**دعم کاربران:**
📧 برای مساعدت، از منوی تنظیمات استفاده کنید
"""
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('main')
    )


# ====================== منوی کیف‌پول ======================
async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی کیف‌پول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    wallets = db.get_all_wallets(user_id)
    
    total_usdt = sum(w['balance'] for w in wallets if w['currency'] == 'USDT')
    
    text = TextFormatter.wallet_info(wallets, total_usdt)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.wallet_menu()
    )


async def add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """افزودن موجودی"""
    query = update.callback_query
    await query.answer()
    
    text = "💰 **افزودن موجودی**\n\nمبلغ مورد نظر را وارد کنید (USDT):"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('wallet')
    )
    
    state_manager.set_state(update.effective_user.id, 'waiting_amount')
    return WAITING_AMOUNT


# ====================== منوی ترید ======================
async def trading_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی ترید"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
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
    """خرید"""
    query = update.callback_query
    await query.answer()
    
    # دریافت جفت‌ارزهای محبوب
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
    """انتخاب جفت ارز برای خرید"""
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.replace('buy_select_', '')
    
    # دریافت قیمت فعلی
    ticker = trading_system.get_ticker(symbol)
    
    if not ticker:
        await query.edit_message_text("❌ نتوانستم قیمت را دریافت کنم")
        return
    
    text = f"""
🟢 **خرید {symbol}**

💵 **قیمت فعلی:** {ticker.get('price', 0):.8f}
📈 **تغییر 24 ساعت:** {ticker.get('changePercent24h', 0):+.2f}%

مقدار موردنظر را وارد کنید:
"""
    
    state_manager.set_state(update.effective_user.id, 'buying', {'symbol': symbol})
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('trading')
    )


# ====================== منوی اشتراک ======================
async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی اشتراک‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
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
    """اطلاعات تیرها"""
    query = update.callback_query
    await query.answer()
    
    tiers = db.get_all_tiers()
    text = TextFormatter.subscription_table(tiers)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('subscription')
    )


async def tier_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب تیر برای خرید"""
    query = update.callback_query
    await query.answer()
    
    tier_name = query.data.replace('tier_', '')
    tier = db.get_tier_config(tier_name)
    
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


# ====================== منوی قیمت‌ها ======================
async def prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی قیمت‌ها"""
    query = update.callback_query
    await query.answer()
    
    # دریافت قیمت‌های محبوب
    popular = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
    
    keyboard = []
    for symbol in popular:
        ticker = trading_system.get_ticker(symbol)
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
    """جزئیات قیمت"""
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.replace('price_detail_', '')
    ticker = trading_system.get_ticker(symbol)
    
    if not ticker:
        await query.edit_message_text("❌ نتوانستم قیمت را دریافت کنم")
        return
    
    text = TextFormatter.price_chart(symbol, ticker)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('prices')
    )


# ====================== منوی سفارشات ======================
async def orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی سفارشات"""
    query = update.callback_query
    await query.answer()
    
    text = "📋 **سفارشات**\n\nیکی از گزینه‌ها را انتخاب کنید:"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.orders_menu()
    )


async def open_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سفارشات باز"""
    query = update.callback_query
    await query.answer()
    
    try:
        orders = trading_system.get_open_orders()
        
        if not orders:
            text = "📭 **هیچ سفارش بازی نیست**"
        else:
            text = "🕐 **سفارشات باز**\n\n"
            for order in orders[:5]:
                text += f"""
🏷️ {order['symbol']}
  {'🟢 خرید' if order['side'] == 'BUY' else '🔴 فروش'} - {order['quantity']} @ {order['price']}
  ⏱️ {order['status']}
"""
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_menu('orders')
        )
    except Exception as e:
        logger.error(f"خطا: {e}")
        await query.edit_message_text(f"❌ خطا: {str(e)}")


# ====================== منوی تنظیمات ======================
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تنظیمات"""
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل", callback_data='profile')],
        [InlineKeyboardButton("🔐 امنیت", callback_data='security')],
        [InlineKeyboardButton("🔔 اطلاع‌رسانی", callback_data='notifications')],
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
    """نمایش پروفایل"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    tier = db.get_tier_config(user.get('tier'))
    subscription = db.get_active_subscription(user_id)
    
    text = TextFormatter.user_profile(user, tier, subscription)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('settings')
    )


# ====================== Message Handler ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های عمومی"""
    user_id = update.effective_user.id
    state, data = state_manager.get_state(user_id)
    
    if state == 'waiting_amount':
        valid, amount, error = ValidationHelper.validate_amount(update.message.text)
        if not valid:
            await update.message.reply_text(error)
            return
        
        state_manager.update_state_data(user_id, 'amount', amount)
        
        # نمایش روش‌های پرداخت
        text = f"💰 **مبلغ:** {amount} USDT\n\nروش پرداخت را انتخاب کنید:"
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.payment_method_menu()
        )
        
        state_manager.set_state(user_id, 'waiting_payment_method', data)


# ====================== Main Function ======================
def main():
    """تابع اصلی"""
    logger.info("🚀 ربات شروع می‌شود...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers
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
    
    app.add_handler(CallbackQueryHandler(orders_callback, pattern="^orders$"))
    app.add_handler(CallbackQueryHandler(open_orders_callback, pattern="^open_orders$"))
    
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(profile_callback, pattern="^profile$"))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    logger.info("✅ تمام دستورات ثبت شد")
    logger.info("🚀 ربات در حال اجراست...")
    
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
