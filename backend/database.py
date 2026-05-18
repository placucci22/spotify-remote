from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./pokemon_prices.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProductDB(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    name = Column(String)
    url = Column(String)
    price_brl = Column(Float)
    category = Column(String)
    set_name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    in_stock = Column(Boolean, default=True)
    seller = Column(String, nullable=True)
    scraped_at = Column(DateTime, default=datetime.now)


class USPriceDB(Base):
    __tablename__ = "us_prices"
    product_name = Column(String, primary_key=True)
    tcgplayer_price_usd = Column(Float, nullable=True)
    pokemon_center_price_usd = Column(Float, nullable=True)
    pricecharting_sealed_usd = Column(Float, nullable=True)
    pricecharting_used_usd = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)


class ExchangeRateDB(Base):
    __tablename__ = "exchange_rates"
    id = Column(String, primary_key=True, default="usd_brl")
    usd_brl = Column(Float)
    source = Column(String)
    updated_at = Column(DateTime, default=datetime.now)


class PriceHistoryDB(Base):
    __tablename__ = "price_history"
    id = Column(String, primary_key=True)
    product_name = Column(String)
    price_brl = Column(Float, nullable=True)
    price_usd = Column(Float, nullable=True)
    source = Column(String)
    recorded_at = Column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
