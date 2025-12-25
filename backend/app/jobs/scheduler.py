"""
Job scheduler for automated daily tasks.
Uses APScheduler to run jobs at specific times.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from app.jobs.daily_analysis import run_daily_analysis
from app.ingestion.news_scraper import MultiSourceNewsScraper
from app.ingestion.price_fetcher import StockPriceFetcher
from app.ingestion.storage import store_news_articles, store_stock_prices
from app.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Manages scheduled background jobs.
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        # Updated for Indian market - major Nifty 50 stocks
        self.common_tickers = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
            'BAJFINANCE', 'LT', 'ASIANPAINT', 'MARUTI', 'HCLTECH',
            # Add international stocks if needed
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'
        ]
    
    def ingest_data_job(self):
        """
        Job to ingest news and prices.
        Run this in the morning before market opens.
        """
        logger.info("Starting scheduled data ingestion...")
        db = SessionLocal()
        
        try:
            for ticker in self.common_tickers:
                try:
                    # Determine exchange based on ticker
                    is_indian = ticker in ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 
                                          'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN', 
                                          'BHARTIARTL', 'KOTAKBANK', 'BAJFINANCE', 
                                          'LT', 'ASIANPAINT', 'MARUTI', 'HCLTECH']
                    exchange = 'NSE' if is_indian else 'US'
                    
                    # Fetch news
                    scraper = MultiSourceNewsScraper()
                    articles = scraper.fetch_all_articles(ticker, days_back=1)
                    store_news_articles(db, articles)
                    
                    # Fetch prices
                    fetcher = StockPriceFetcher()
                    prices = fetcher.fetch_prices(ticker, days_back=2, exchange=exchange)
                    store_stock_prices(db, prices)
                    
                    logger.info(f"✅ Ingested data for {ticker}")
                    
                except Exception as e:
                    logger.error(f"Error ingesting {ticker}: {e}")
                    continue
        finally:
            db.close()
        
        logger.info("Scheduled data ingestion completed")
    
    def analysis_job(self):
        """
        Job to run technical analysis.
        Run this after market close (e.g., 5 PM EST).
        """
        logger.info("Starting scheduled analysis...")
        run_daily_analysis(self.common_tickers)
        logger.info("Scheduled analysis completed")
    
    def start(self):
        """
        Start the scheduler with configured jobs.
        Times adjusted for Indian market (IST timezone).
        """
        # Job 1: Data ingestion at 9 AM IST (before NSE market opens at 9:15 AM)
        self.scheduler.add_job(
            self.ingest_data_job,
            CronTrigger(hour=9, minute=0, timezone='Asia/Kolkata'),
            id='daily_data_ingestion',
            name='Daily Data Ingestion',
            replace_existing=True
        )
        
        # Job 2: Analysis at 4 PM IST (after NSE market closes at 3:30 PM)
        self.scheduler.add_job(
            self.analysis_job,
            CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
            id='daily_analysis',
            name='Daily Technical Analysis',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Job scheduler started")
        logger.info("Scheduled jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name}: {job.next_run_time}")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Job scheduler stopped")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> JobScheduler:
    """Get or create scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler