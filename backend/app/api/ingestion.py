"""
API endpoints to trigger data ingestion.
Useful for manual refreshes or testing.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ingestion.news_scraper import MultiSourceNewsScraper
from app.ingestion.price_fetcher import StockPriceFetcher
from app.ingestion.storage import store_news_articles, store_stock_prices
from app.api.schemas import IngestionStatusResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def run_ingestion_job(ticker: str, db: Session) -> dict:
    """
    Background task to ingest news and prices.
    """
    errors = []
    news_count = 0
    price_count = 0
    
    try:
        # Fetch news
        logger.info(f"Starting news ingestion for {ticker}")
        scraper = MultiSourceNewsScraper()
        articles = scraper.fetch_all_articles(ticker, days_back=7)
        news_count = store_news_articles(db, articles)
        
    except Exception as e:
        error_msg = f"News ingestion failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    try:
        # Fetch prices
        logger.info(f"Starting price ingestion for {ticker}")
        fetcher = StockPriceFetcher()
        prices = fetcher.fetch_prices(ticker, days_back=90)
        price_count = store_stock_prices(db, prices)
        
    except Exception as e:
        error_msg = f"Price ingestion failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    return {
        "news_count": news_count,
        "price_count": price_count,
        "errors": errors
    }


@router.post("/ingest/{ticker}", response_model=IngestionStatusResponse)
async def trigger_ingestion(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger data ingestion for a ticker.
    Runs in background to avoid timeout.
    
    **Note**: This endpoint will return immediately. 
    Check logs or database to verify completion.
    """
    ticker = ticker.upper()
    
    # Validate ticker format (basic check)
    if not ticker.isalpha() or len(ticker) > 10:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format"
        )
    
    # Add background task
    background_tasks.add_task(run_ingestion_job, ticker, db)
    
    return {
        "success": True,
        "ticker": ticker,
        "news_articles_added": 0,  # Will be updated in background
        "price_records_added": 0,
        "errors": [],
        "message": f"Ingestion started for {ticker}. Check logs for progress."
    }


@router.post("/ingest/batch")
async def trigger_batch_ingestion(
    tickers: list[str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger ingestion for multiple tickers.
    
    Example request body:
```json
    ["AAPL", "MSFT", "GOOGL"]
```
    """
    if len(tickers) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 tickers per batch request"
        )
    
    # Validate all tickers
    validated_tickers = []
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if ticker.isalpha() and len(ticker) <= 10:
            validated_tickers.append(ticker)
    
    if not validated_tickers:
        raise HTTPException(
            status_code=400,
            detail="No valid tickers provided"
        )
    
    # Add background tasks
    for ticker in validated_tickers:
        background_tasks.add_task(run_ingestion_job, ticker, db)
    
    return {
        "success": True,
        "tickers": validated_tickers,
        "count": len(validated_tickers),
        "message": f"Batch ingestion started for {len(validated_tickers)} tickers"
    }