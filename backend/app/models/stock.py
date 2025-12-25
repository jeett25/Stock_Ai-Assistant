from sqlalchemy import Column, Integer, String, Date, Numeric, BigInteger, Text, UniqueConstraint, Index
from datetime import date
from decimal import Decimal
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

class StockPrice(Base):
    

    """Daily OHLCV stock price data."""
    __tablename__ = "stock_prices"
     
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2), nullable=False)
    volume = Column(BigInteger)
    
     #Ensure one record per ticker per day
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uix_ticker_date'),
        Index('ix_ticker_date', 'ticker', 'date'),
    )
    def __repr__(self):
        return f"<StockPrice(ticker={self.ticker}, date={self.date}, close={self.close})>"

class Analysis(Base):
    __tablename__ = "analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Technical indicators- Momentum 
    rsi = Column(Numeric(5, 2))
    macd_value = Column(Numeric(10, 4))
    macd_signal = Column(Numeric(10, 4))
    macd_histogram = Column(Numeric(10, 4))
    sma_20 = Column(Numeric(10, 2))
    sma_50 = Column(Numeric(10, 2))
    
    # Trading signals
    signal = Column(String(10))  # BUY, SELL, HOLD
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    reason = Column(Text)  # Human-readable explanation
    
    indicators_data = Column(JSONB, default={})
    
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uix_analysis_ticker_date'),
        Index('ix_analysis_ticker_date', 'ticker', 'date'),
    )
    
    def __repr__(self):
        return f"<Analysis(ticker={self.ticker}, date={self.date}, signal={self.signal})>"