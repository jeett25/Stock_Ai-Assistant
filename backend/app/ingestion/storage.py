from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
import logging

from app.models.news import NewsArticle
from app.models.stock import StockPrice
from app.ingestion.schemas import NewsArticleCreate, StockPriceCreate

logger = logging.getLogger(__name__)


def store_news_articles(db: Session, articles: List[NewsArticleCreate]) -> int:
    """
    Store news articles in database.
    Skips duplicates (same URL).
    
    Returns:
        Number of successfully stored articles
    """
    stored_count = 0
    
    for article in articles:
        try:
            db_article = NewsArticle(
                ticker=article.ticker,
                title=article.title,
                content=article.content,
                url=str(article.url),
                source=article.source,
                published_at=article.published_at
            )
            
            db.add(db_article)
            db.commit()
            stored_count += 1
            
        except IntegrityError:
            # Duplicate URL, skip
            db.rollback()
            logger.debug(f"Skipping duplicate article: {article.url}")
            continue
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing article {article.url}: {e}")
            continue
    
    logger.info(f"Stored {stored_count}/{len(articles)} news articles")
    return stored_count


def store_stock_prices(db: Session, prices: List[StockPriceCreate]) -> int:
    """
    Store stock prices in database.
    Updates existing records if ticker+date already exists.
    
    Returns:
        Number of successfully stored/updated records
    """
    stored_count = 0
    
    for price in prices:
        try:
            # Check if record exists
            existing = db.query(StockPrice).filter(
                StockPrice.ticker == price.ticker,
                StockPrice.date == price.date.date()
            ).first()
            
            if existing:
                # Update existing record
                existing.open = price.open
                existing.high = price.high
                existing.low = price.low
                existing.close = price.close
                existing.volume = price.volume
            else:
                # Create new record
                db_price = StockPrice(
                    ticker=price.ticker,
                    date=price.date.date(),
                    open=price.open,
                    high=price.high,
                    low=price.low,
                    close=price.close,
                    volume=price.volume
                )
                db.add(db_price)
            
            db.commit()
            stored_count += 1
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing price for {price.ticker} on {price.date}: {e}")
            continue
    
    logger.info(f"Stored {stored_count}/{len(prices)} stock prices")
    return stored_count


def get_latest_news(db: Session, ticker: str, limit: int = 10) -> List[NewsArticle]:
    """Retrieve latest news articles for a ticker."""
    return db.query(NewsArticle)\
        .filter(NewsArticle.ticker == ticker)\
        .order_by(NewsArticle.published_at.desc())\
        .limit(limit)\
        .all()


def get_price_history(db: Session, ticker: str, days: int = 30) -> List[StockPrice]:
    """Retrieve price history for a ticker."""
    return db.query(StockPrice)\
        .filter(StockPrice.ticker == ticker)\
        .order_by(StockPrice.date.desc())\
        .limit(days)\
        .all()