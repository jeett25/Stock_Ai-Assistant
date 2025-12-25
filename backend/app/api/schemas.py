"""
API response schemas (Pydantic models for serialization).
"""

from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime, date
from typing import List, Optional


class NewsArticleResponse(BaseModel):
    """Response model for news article."""
    id: int
    ticker: str
    title: str
    content: Optional[str] = None
    url: str
    source: str
    published_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allows SQLAlchemy model conversion
        json_schema_extra = {
            "example": {
                "id": 1,
                "ticker": "AAPL",
                "title": "Apple announces new product",
                "content": "Apple Inc. today...",
                "url": "https://example.com/article",
                "source": "Reuters",
                "published_at": "2025-12-15T10:00:00",
                "created_at": "2025-12-15T10:05:00"
            }
        }


class StockPriceResponse(BaseModel):
    """Response model for stock price."""
    id: int
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "ticker": "AAPL",
                "date": "2025-12-15",
                "open": 195.50,
                "high": 197.25,
                "low": 194.80,
                "close": 196.75,
                "volume": 45000000
            }
        }


class LatestPriceResponse(BaseModel):
    """Response model for latest price with change info."""
    ticker: str
    date: date
    price: float
    open: float
    high: float
    low: float
    change: float
    change_percent: float
    volume: int


class NewsSourcesResponse(BaseModel):
    """Response model for news sources breakdown."""
    ticker: str
    total_articles: int
    sources: List[dict]


class IngestionStatusResponse(BaseModel):
    """Response for ingestion job status."""
    success: bool
    ticker: str
    news_articles_added: int
    price_records_added: int
    errors: List[str] = []