"""
Daily analysis job - calculates indicators and generates signals.
Run this once per day after market close.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import List
import logging

from app.core.database import SessionLocal
from app.models.stock import StockPrice
from app.ingestion.storage import get_price_history
from app.analysis.technical import IndicatorCalculator
from app.analysis.signals import SignalGenerator
from app.analysis.storage import store_analysis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_ticker(db: Session, ticker: str) -> bool:
    try:
        logger.info(f"Analyzing {ticker}...")
        
        # Get price history (need at least 50 days for reliable indicators)
        prices = get_price_history(db, ticker, days=200)
        
        if len(prices) < 50:
            logger.warning(f"Insufficient price data for {ticker}: {len(prices)} records")
            return False
        
        # Calculate indicators
        calculator = IndicatorCalculator()
        indicators = calculator.calculate_all_indicators(prices, ticker)
        
        if not indicators:
            logger.error(f"Failed to calculate indicators for {ticker}")
            return False
        
        # Generate signal
        signal_gen = SignalGenerator()
        signal_data = signal_gen.generate_signal(indicators)
        
        # Store results
        analysis_date = indicators['date']
        result = store_analysis(
            db,
            ticker,
            analysis_date,
            indicators,
            signal_data
        )
        
        if result:
            logger.info(
                f"✅ {ticker}: {signal_data['signal']} "
                f"(confidence: {signal_data['confidence']:.2f})"
            )
            logger.info(f"   Reasons: {', '.join(signal_data['reasons'][:3])}")
            return True
        else:
            logger.error(f"Failed to store analysis for {ticker}")
            return False
            
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_all_tickers_with_data(db: Session) -> List[str]:
    """
    Get list of all tickers that have price data.
    """
    tickers = db.query(StockPrice.ticker).distinct().all()
    return [t[0] for t in tickers]


def run_daily_analysis(tickers: List[str] = None):
    logger.info("=" * 60)
    logger.info("DAILY ANALYSIS JOB STARTED")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get tickers to analyze
        if tickers is None:
            tickers = get_all_tickers_with_data(db)
            logger.info(f"Found {len(tickers)} tickers with price data")
        else:
            logger.info(f"Analyzing {len(tickers)} specified tickers")
        
        if not tickers:
            logger.warning("No tickers to analyze!")
            return
        
        # Run analysis for each ticker
        success_count = 0
        fail_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
            
            if analyze_ticker(db, ticker):
                success_count += 1
            else:
                fail_count += 1
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("DAILY ANALYSIS COMPLETED")
        logger.info("=" * 60)
        logger.info(f"✅ Successful: {success_count}")
        logger.info(f"❌ Failed: {fail_count}")
        logger.info(f"📊 Total: {len(tickers)}")
        logger.info("=" * 60)
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run daily technical analysis")
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Specific tickers to analyze (e.g., AAPL MSFT GOOGL)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Analyze all tickers with price data'
    )
    
    args = parser.parse_args()
    
    if args.all:
        run_daily_analysis()
    elif args.tickers:
        run_daily_analysis(args.tickers)
    else:
        # Default: analyze common tickers
        run_daily_analysis(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])