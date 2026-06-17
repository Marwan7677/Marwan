"""
ربات معاملاتی Toobit - ربات اصلی (نسخهٔ نهایی)
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

from database import Database
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
db = Database("toobit_bot.db")  # ✅ اصلاح: ایجاد نمونهٔ Database
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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء العام"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update:
        try:
            if update.message:
                await update.message.reply_text("❌ خطای ناشناختهٔ رخ داد. لطفا بعدا تلاش کنید.")
            elif update.callback_query:
                await update.callback_query.answer("❌ خطا رخ داد", show_alert=True)
        except:
            pass


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
    
    # اگر از طریق callback آمده، edit کن
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_menu('main')
        )
    else:
        # اگر command آمده، reply کن
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


async def wallet_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تاریخچهٔ کیف‌پول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    transactions = db.get_user_transactions(user_id)
    
    text = TextFormatter.transaction_history(transactions[:10])  # آخرین 10 تراکنش
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('wallet')
    )


async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برداشت از کیف‌پول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    text = f"""
📤 **برداشت**

💰 **موجودی شما:** {user.get('wallet_balance', 0):.2f} تومان

مبلغ برداشت را وارد کنید:
"""
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('wallet')
    )
    
    state_manager.set_state(user_id, 'waiting_withdraw_amount')


async def transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتقال موجودی"""
    query = update.callback_query
    await query.answer()
    
    text = "💸 **انتقال موجودی**\n\nشناسهٔ کاربر دریافت‌کننده را وارد کنید:"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('wallet')
    )
    
    state_manager.set_state(update.effective_user.id, 'waiting_transfer_user')


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


async def sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فروش"""
    query = update.callback_query
    await query.answer()
    
    popular_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
    
    keyboard = []
    for pair in popular_pairs:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f'sell_select_{pair}')])
    
    keyboard.append([InlineKeyboardButton("🔍 جستجو", callback_data='search_sell')])
    keyboard.append([InlineKeyboardButton("◀️ برگشت", callback_data='trading')])
    
    text = "🔴 **فروش**\n\nیکی از جفت‌ارزها را انتخاب کنید یا جستجو کنید:"
    
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


async def sell_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب جفت ارز برای فروش"""
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.replace('sell_select_', '')
    
    # دریافت قیمت فعلی
    ticker = trading_system.get_ticker(symbol)
    
    if not ticker:
        await query.edit_message_text("❌ نتوانستم قیمت را دریافت کنم")
        return
    
    text = f"""
🔴 **فروش {symbol}**

💵 **قیمت فعلی:** {ticker.get('price', 0):.8f}
📈 **تغییر 24 ساعت:** {ticker.get('changePercent24h', 0):+.2f}%

مقدار موردنظر را وارد کنید:
"""
    
    state_manager.set_state(update.effective_user.id, 'selling', {'symbol': symbol})
    
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
    
    text = """
⭐ **پلان‌های اشتراک**

به یکی از پلان‌های زیر دسترسی پیدا کنید:
"""
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.subscription_menu()
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


async def completed_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سفارشات تکمیل شده"""
    query = update.callback_query
    await query.answer()
    
    try:
        orders = trading_system.get_completed_orders()
        
        if not orders:
            text = "📭 **هیچ سفارش تکمیل شده‌ای نیست**"
        else:
            text = "✅ **سفارشات تکمیل شده**\n\n"
            for order in orders[:5]:
                text += f"""
🏷️ {order['symbol']}
  {'🟢 خرید' if order['side'] == 'BUY' else '🔴 فروش'} - {order['quantity']} @ {order['price']}
  📅 {order.get('completed_at', 'نامشخص')[:10]}
"""
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_menu('orders')
        )
    except Exception as e:
        logger.error(f"خطا: {e}")
        await query.edit_message_text(f"❌ خطا: {str(e)}")


async def cancelled_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سفارشات لغو شده"""
    query = update.callback_query
    await query.answer()
    
    try:
        orders = trading_system.get_cancelled_orders()
        
        if not orders:
            text = "📭 **هیچ سفارش لغو شده‌ای نیست**"
        else:
            text = "❌ **سفارشات لغو شده**\n\n"
            for order in orders[:5]:
                text += f"""
🏷️ {order['symbol']}
  {'🟢 خرید' if order['side'] == 'BUY' else '🔴 فروش'} - {order['quantity']}
  📅 {order.get('cancelled_at', 'نامشخص')[:10]}
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


async def security_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات الأمان"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔐 تغییر رمز عبور", callback_data='change_password')],
        [InlineKeyboardButton("📱 تأیید دو مرحله‌ای", callback_data='two_factor')],
        [InlineKeyboardButton("📝 تاریخچهٔ لاگین", callback_data='login_history')],
        [InlineKeyboardButton("◀️ برگشت", callback_data='settings')]
    ]
    
    text = "🔐 **امنیت حساب**\n\nیکی از گزینه‌ها را انتخاب کنید:"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات الإشعارات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    status = "✅ فعال" if user.get('notification_enabled') else "❌ غیرفعال"
    
    keyboard = [
        [InlineKeyboardButton(f"🔔 اطلاع‌رسانی {status}", callback_data='toggle_notifications')],
        [InlineKeyboardButton("📊 اطلاع‌رسانی قیمت", callback_data='price_alerts')],
        [InlineKeyboardButton("◀️ برگشت", callback_data='settings')]
    ]
    
    text = f"🔔 **اطلاع‌رسانی**\n\nوضعیت: {status}"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الدعم والمساعدة"""
    query = update.callback_query
    await query.answer()
    
    text = """
📞 **پشتیبانی و راهنمایی**

❓ **سؤالات متداول:**
• چگونه ربات را شروع کنم؟
• چگونه موجودی اضافه کنم؟
• کدام تیر برای من بهتر است؟

📧 **تماس با ما:**
- ایمیل: support@toobit.com
- تلگرام: @ToobitSupport
- سایت: https://www.toobit.com

⏱️ **زمان پاسخگویی:** 24/7
"""
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.back_menu('settings')
    )


# ====================== Message Handler - ✅ نسخهٔ مصحح شدهٔ با تمام الحالات ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های عمومی - نسخهٔ مصحح شدهٔ"""
    user_id = update.effective_user.id
    state, data = state_manager.get_state(user_id)
    text = update.message.text
    
    # ✅ حالهٔ انتظار مبلغ (افزودن موجودی)
    if state == 'waiting_amount':
        valid, amount, error = ValidationHelper.validate_amount(text)
        if not valid:
            await update.message.reply_text(error)
            return
        
        state_manager.update_state_data(user_id, 'amount', amount)
        
        # نمایش روش‌های پرداخت
        response_text = f"💰 **مبلغ:** {amount} USDT\n\nروش پرداخت را انتخاب کنید:"
        await update.message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.payment_method_menu()
        )
        
        state_manager.set_state(user_id, 'waiting_payment_method', data)
    
    # ✅ حالهٔ خرید
    elif state == 'buying':
        symbol = data.get('symbol')
        valid, qty, error = ValidationHelper.validate_quantity(text, 0.001)
        
        if not valid:
            await update.message.reply_text(error)
            return
        
        state_manager.update_state_data(user_id, 'quantity', qty)
        
        # دریافت قیمت
        ticker = trading_system.get_ticker(symbol)
        if ticker:
            total = qty * ticker.get('price', 0)
            response_text = f"""
🟢 **تأیید خرید**

🏷️ **نماد:** {symbol}
📊 **مقدار:** {qty}
💵 **قیمت فعلی:** {ticker.get('price', 0):.8f}
💰 **مجموع:** {total:.2f}

آیا اطمینان دارید؟
"""
            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=KeyboardBuilder.confirm_menu()
            )
            
            state_manager.set_state(user_id, 'confirming_buy', data)
    
    # ✅ حالهٔ فروش
    elif state == 'selling':
        symbol = data.get('symbol')
        valid, qty, error = ValidationHelper.validate_quantity(text, 0.001)
        
        if not valid:
            await update.message.reply_text(error)
            return
        
        state_manager.update_state_data(user_id, 'quantity', qty)
        
        # دریافت قیمت
        ticker = trading_system.get_ticker(symbol)
        if ticker:
            total = qty * ticker.get('price', 0)
            response_text = f"""
🔴 **تأیید فروش**

🏷️ **نماد:** {symbol}
📊 **مقدار:** {qty}
💵 **قیمت فعلی:** {ticker.get('price', 0):.8f}
💰 **مجموع:** {total:.2f}

آیا اطمینان دارید؟
"""
            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=KeyboardBuilder.confirm_menu()
            )
            
            state_manager.set_state(user_id, 'confirming_sell', data)
    
    # ✅ حالهٔ برداشت
    elif state == 'waiting_withdraw_amount':
        valid, amount, error = ValidationHelper.validate_amount(text)
        if not valid:
            await update.message.reply_text(error)
            return
        
        state_manager.update_state_data(user_id, 'amount', amount)
        
        response_text = f"""
📤 **تأیید برداشت**

💰 **مبلغ:** {amount} تومان

آیا اطمینان دارید؟
"""
        await update.message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.confirm_menu()
        )
        
        state_manager.set_state(user_id, 'confirming_withdraw', data)
    
    # ✅ حالهٔ انتقال کاربر
    elif state == 'waiting_transfer_user':
        try:
            target_user_id = int(text)
            if not db.get_user(target_user_id):
                await update.message.reply_text("❌ کاربر یافت نشد")
                return
            
            state_manager.update_state_data(user_id, 'target_user_id', target_user_id)
            
            await update.message.reply_text(
                "💸 **مبلغ انتقال را وارد کنید:**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            state_manager.set_state(user_id, 'waiting_transfer_amount', data)
        except ValueError:
            await update.message.reply_text("❌ شناسهٔ کاربر نامعتبر است")
    
    # ✅ حالهٔ مبلغ انتقال
    elif state == 'waiting_transfer_amount':
        valid, amount, error = ValidationHelper.validate_amount(text)
        if not valid:
            await update.message.reply_text(error)
            return
        
        target_user_id = data.get('target_user_id')
        target_user = db.get_user(target_user_id)
        
        response_text = f"""
💸 **تأیید انتقال**

👤 **فرستنده:** {update.effective_user.first_name}
👤 **گیرنده:** {target_user.get('first_name')}
💰 **مبلغ:** {amount} تومان

آیا اطمینان دارید؟
"""
        await update.message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.confirm_menu()
        )
        
        state_manager.update_state_data(user_id, 'amount', amount)
        state_manager.set_state(user_id, 'confirming_transfer', data)
    
    # ✅ حالهٔ جستجو
    elif state == 'searching_pair':
        # جستجو در نمادهای دستیاب
        symbol = text.upper()
        ticker = trading_system.get_ticker(symbol)
        
        if ticker:
            response_text = TextFormatter.price_chart(symbol, ticker)
            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=KeyboardBuilder.back_menu('prices')
            )
        else:
            await update.message.reply_text(f"❌ نماد {symbol} یافت نشد")
        
        state_manager.clear_state(user_id)
    
    # ✅ حالهٔ پیش‌فرض
    else:
        await update.message.reply_text(
            "❌ دستور نامشناخته شده\n\nدستور /start را بزنید یا /help برای کمک",
            reply_markup=KeyboardBuilder.main_menu()
        )


# ====================== نمایندهٔ Callback برای صفحات اصلی ======================
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به منوی اصلی"""
    query = update.callback_query
    await query.answer()
    
    text = """
🤖 **منوی اصلی**

یکی از گزینه‌ها را انتخاب کنید:
"""
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu()
    )


# ====================== Main Function - نسخهٔ مصحح شدهٔ ======================
def main():
    """تابع اصلی"""
    logger.info("🚀 ربات شروع می‌شود...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ====================== Command Handlers ======================
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # ====================== Callback Handlers - Main Menu ======================
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main$"))
    
    # ====================== Callback Handlers - Wallet ======================
    app.add_handler(CallbackQueryHandler(wallet_callback, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(add_balance_callback, pattern="^add_balance$"))
    app.add_handler(CallbackQueryHandler(wallet_history_callback, pattern="^wallet_history$"))
    app.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(transfer_callback, pattern="^transfer$"))
    
    # ====================== Callback Handlers - Trading ======================
    app.add_handler(CallbackQueryHandler(trading_callback, pattern="^trading$"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_menu$"))
    app.add_handler(CallbackQueryHandler(sell_callback, pattern="^sell_menu$"))
    app.add_handler(CallbackQueryHandler(buy_select_callback, pattern="^buy_select_"))
    app.add_handler(CallbackQueryHandler(sell_select_callback, pattern="^sell_select_"))
    
    # ====================== Callback Handlers - Subscription ======================
    app.add_handler(CallbackQueryHandler(subscription_callback, pattern="^subscription$"))
    app.add_handler(CallbackQueryHandler(tier_info_callback, pattern="^tier_info$"))
    app.add_handler(CallbackQueryHandler(tier_selection_callback, pattern="^tier_"))
    
    # ====================== Callback Handlers - Prices ======================
    app.add_handler(CallbackQueryHandler(prices_callback, pattern="^prices$"))
    app.add_handler(CallbackQueryHandler(price_detail_callback, pattern="^price_detail_"))
    
    # ====================== Callback Handlers - Orders ======================
    app.add_handler(CallbackQueryHandler(orders_callback, pattern="^orders$"))
    app.add_handler(CallbackQueryHandler(open_orders_callback, pattern="^open_orders$"))
    app.add_handler(CallbackQueryHandler(completed_orders_callback, pattern="^completed_orders$"))
    app.add_handler(CallbackQueryHandler(cancelled_orders_callback, pattern="^cancelled_orders$"))
    
    # ====================== Callback Handlers - Settings ======================
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(profile_callback, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(security_callback, pattern="^security$"))
    app.add_handler(CallbackQueryHandler(notifications_callback, pattern="^notifications$"))
    app.add_handler(CallbackQueryHandler(support_callback, pattern="^support$"))
    
    # ====================== Help Callback ======================
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    
    # ====================== Message Handler ======================
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ====================== Error Handler ======================
    app.add_error_handler(error_handler)
    
    logger.info("✅ تمام دستورات ثبت شد")
    logger.info("🚀 ربات در حال اجراست...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
