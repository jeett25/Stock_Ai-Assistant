"""
Manual test script for data ingestion.
Run this to verify news and price fetching works.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.ingestion.news_scraper import MultiSourceNewsScraper
from app.ingestion.price_fetcher import StockPriceFetcher
from app.ingestion.storage import store_news_articles, store_stock_prices
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_news_ingestion(ticker: str = "AAPL"):
    """Test news scraping and storage."""
    logger.info(f"=== Testing News Ingestion for {ticker} ===")
    
    # Fetch news
    scraper = MultiSourceNewsScraper()
    articles = scraper.fetch_all_articles(ticker, days_back=7)
    
    logger.info(f"Fetched {len(articles)} articles")
    
    if not articles:
        logger.warning("No articles found!")
        return
    
    # Show sample
    logger.info("\n--- Sample Article ---")
    sample = articles[0]
    logger.info(f"Title: {sample.title}")
    logger.info(f"Source: {sample.source}")
    logger.info(f"URL: {sample.url}")
    logger.info(f"Published: {sample.published_at}")
    logger.info(f"Content preview: {sample.content[:200]}...")
    
    # Store in database
    db = SessionLocal()
    try:
        stored = store_news_articles(db, articles)
        logger.info(f"✅ Stored {stored} articles in database")
    finally:
        db.close()


def test_price_ingestion(ticker: str = "AAPL"):
    """Test price fetching and storage."""
    logger.info(f"\n=== Testing Price Ingestion for {ticker} ===")
    
    # Fetch prices
    fetcher = StockPriceFetcher()
    prices = fetcher.fetch_prices(ticker, days_back=90)
    
    logger.info(f"Fetched {len(prices)} price records")
    
    if not prices:
        logger.warning("No prices found!")
        return
    
    # Show sample
    logger.info("\n--- Sample Price Data ---")
    latest = prices[-1]  # Most recent
    logger.info(f"Date: {latest.date}")
    logger.info(f"Open: ${latest.open:.2f}")
    logger.info(f"High: ${latest.high:.2f}")
    logger.info(f"Low: ${latest.low:.2f}")
    logger.info(f"Close: ${latest.close:.2f}")
    logger.info(f"Volume: {latest.volume:,}")
    
    # Get current price
    current = fetcher.fetch_current_price(ticker)
    if current:
        logger.info(f"Current price: ${current:.2f}")
    
    # Store in database
    db = SessionLocal()
    try:
        stored = store_stock_prices(db, prices)
        logger.info(f"✅ Stored {stored} price records in database")
    finally:
        db.close()


def test_multiple_tickers():
    """Test ingestion for multiple tickers."""
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    logger.info("\n=== Testing Multiple Tickers ===")
    
    for ticker in tickers:
        logger.info(f"\n--- Processing {ticker} ---")
        
        try:
            test_news_ingestion(ticker)
            test_price_ingestion(ticker)
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test data ingestion")
    parser.add_argument('--ticker', type=str, default='AAPL', help='Stock ticker to test')
    parser.add_argument('--multiple', action='store_true', help='Test multiple tickers')
    
    args = parser.parse_args()
    
    if args.multiple:
        test_multiple_tickers()
    else:
        test_news_ingestion(args.ticker)
        test_price_ingestion(args.ticker)
    
    logger.info("\n=== Test Complete ===")