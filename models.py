from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String)
    subscription_tier = Column(String, default="free")  # free, lite, pro, gold, diamond
    subscription_expiry = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    toobit_api_key = Column(String, nullable=True)
    toobit_secret_key = Column(String, nullable=True)
    daily_trades_count = Column(Integer, default=0)
    last_trade_reset = Column(DateTime, default=datetime.utcnow)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    balance_usdt = Column(Float, default=0.0)   # موجودی کیف پول داخلی بر حسب USDT
    # می‌توان ارزهای دیگر اضافه کرد، ولی برای سادگی تمام ارزش به USDT تبدیل می‌شود

class Deposit(Base):
    __tablename__ = "deposits"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    currency = Column(String)          # USDT, TRX, ...
    txid = Column(String, unique=True) # هش تراکنش
    status = Column(String, default="pending") # pending, confirmed, rejected
    requested_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    side = Column(String)   # BUY / SELL
    order_id = Column(String)  # orderId از Toobit
    quantity = Column(Float)
    price = Column(Float)
    fee = Column(Float)
    status = Column(String)  # new, filled, cancelled, expired
    created_at = Column(DateTime, default=datetime.utcnow)