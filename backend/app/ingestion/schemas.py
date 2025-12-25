from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime , date
from typing import Optional , List


class NewsArticleCreate(BaseModel):
    """Schema for creating a news article."""
    
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    title: str = Field(..., min_length=1, description="Article title")
    content: Optional[str] = Field(None, description="Article content/summary")
    url: HttpUrl = Field(..., description="Article URL")
    source: str = Field(..., description="News source name")
    published_at: datetime = Field(..., description="Publication timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "title": "Apple announces new product line",
                "content": "Apple Inc. today announced...",
                "url": "https://example.com/article",
                "source": "Reuters",
                "published_at": "2025-12-15T10:00:00Z"
            }
        }


class StockPriceCreate(BaseModel):
    """Schema for creating stock price record."""
    
    ticker: str = Field(..., min_length=1, max_length=10)
    date: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "date": "2025-12-15",
                "open": 195.50,
                "high": 197.25,
                "low": 194.80,
                "close": 196.75,
                "volume": 45000000
            }
        }
