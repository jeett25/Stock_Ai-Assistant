from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.core.database import SessionLocal
from app.models.news import NewsArticle
from app.models.stock import StockPrice, Analysis
from app.ingestion.news_scraper import MultiSourceNewsScraper
from app.ingestion.price_fetcher import StockPriceFetcher
from app.ingestion.storage import store_news_articles, store_stock_prices
from app.analysis.technical import IndicatorCalculator
from app.analysis.signals import SignalGenerator
from app.analysis.storage import store_analysis, get_latest_analysis
from app.ingestion.storage import get_price_history

logger = logging.getLogger(__name__)

class AutoNewsAgent:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.scraper = MultiSourceNewsScraper()
    
    def get_or_fetch_news(
        self,
        ticker: Optional[str] = None,
        days_back: int = 7,
        min_articles: int = 3,
        force_refresh: bool = False
    ) -> List[NewsArticle]:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Step 1: Check database
            if not force_refresh:
                if ticker:
                    existing_articles = (
                        self.db.query(NewsArticle)
                        .filter(
                            NewsArticle.ticker == ticker.upper(),
                            NewsArticle.published_at >= cutoff_date
                        )
                        .order_by(NewsArticle.published_at.desc())
                        .all()
                    )
                else:
                    # Get recent news across all tickers
                    existing_articles = (
                        self.db.query(NewsArticle)
                        .filter(NewsArticle.published_at >= cutoff_date)
                        .order_by(NewsArticle.published_at.desc())
                        .limit(20)
                        .all()
                    )
                
                if len(existing_articles) >= min_articles:
                    logger.info(
                        f"✅ Found {len(existing_articles)} articles in DB "
                        f"for {'general' if not ticker else ticker}"
                    )
                    return existing_articles
                
                logger.info(
                    f"⚠️ Only {len(existing_articles)} articles in DB, "
                    f"need {min_articles}. Fetching fresh data..."
                )
            
            # Step 2: Fetch from web
            if ticker:
                logger.info(f"🌐 Scraping news for {ticker}...")
                fresh_articles = self.scraper.fetch_all_articles(ticker, days_back)
            else:
                logger.info(f"🌐 Scraping general market news...")
                fresh_articles = self.scraper.get_market_news('india', days_back)
            
            # Step 3: Store in database
            if fresh_articles:
                stored_count = store_news_articles(self.db, fresh_articles)
                logger.info(f"✅ Stored {stored_count} new articles")
                
                # Get from DB to return with IDs
                if ticker:
                    return (
                        self.db.query(NewsArticle)
                        .filter(
                            NewsArticle.ticker == ticker.upper(),
                            NewsArticle.published_at >= cutoff_date
                        )
                        .order_by(NewsArticle.published_at.desc())
                        .all()
                    )
                else:
                    return (
                        self.db.query(NewsArticle)
                        .filter(NewsArticle.published_at >= cutoff_date)
                        .order_by(NewsArticle.published_at.desc())
                        .limit(20)
                        .all()
                    )
            else:
                logger.warning("❌ No articles fetched from web")
                return []
                
        except Exception as e:
            logger.error(f"Error in AutoNewsAgent: {e}")
            import traceback
            traceback.print_exc()
            return []

class AutoAnalysisAgent:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.price_fetcher = StockPriceFetcher()
        self.indicator_calculator = IndicatorCalculator()
        self.signal_generator = SignalGenerator()
    
    def get_or_create_analysis(
        self,
        ticker: str,
        target_date: date = None,
        force_refresh: bool = False
    ) -> Optional[Analysis]:
        try:
            ticker = ticker.upper()
            target_date = target_date or date.today()
            
            # Step 1: Check if analysis exists
            if not force_refresh:
                existing = self.db.query(Analysis).filter(
                    Analysis.ticker == ticker,
                    Analysis.date == target_date
                ).first()
                
                if existing:
                    logger.info(f"✅ Found existing analysis for {ticker} on {target_date}")
                    return existing
            
            logger.info(f"📊 Creating new analysis for {ticker}...")
            
            # Step 2: Ensure we have enough price data
            prices = self._ensure_price_data(ticker, days_needed=200)
            
            if len(prices) < 50:
                logger.error(f"❌ Insufficient price data: {len(prices)} records")
                return None
            
            # Step 3: Calculate indicators
            logger.info(f"🔢 Calculating indicators for {ticker}...")
            indicators = self.indicator_calculator.calculate_all_indicators(
                prices,
                ticker
            )
            
            if not indicators:
                logger.error(f"❌ Failed to calculate indicators")
                return None
            
            # Step 4: Generate signals
            logger.info(f"🎯 Generating trading signals...")
            signal_data = self.signal_generator.generate_signal(indicators)
            
            # Step 5: Store analysis
            logger.info(f"💾 Storing analysis...")
            analysis = store_analysis(
                self.db,
                ticker,
                target_date,
                indicators,
                signal_data
            )
            
            if analysis:
                logger.info(
                    f"✅ Analysis complete for {ticker}: "
                    f"{signal_data['signal']} (confidence: {signal_data['confidence']:.2f})"
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AutoAnalysisAgent for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _ensure_price_data(
        self,
        ticker: str,
        days_needed: int = 200
    ) -> List[StockPrice]:
        try:
            # Check existing data
            existing_prices = get_price_history(self.db, ticker, days_needed)
            
            # Check if we have enough recent data
            if existing_prices:
                most_recent = max(p.date for p in existing_prices)
                days_old = (date.today() - most_recent).days
                
                if len(existing_prices) >= 50 and days_old <= 1:
                    logger.info(
                        f"✅ Found {len(existing_prices)} price records "
                        f"(most recent: {most_recent})"
                    )
                    return existing_prices
            
            # Need fresh data
            logger.info(f"🌐 Fetching price data for {ticker}...")
            indian_tickers = {
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
                'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
                'BAJFINANCE', 'LT', 'ASIANPAINT', 'MARUTI', 'HCLTECH'
            }
            exchange = 'NSE' if ticker in indian_tickers else 'US'
            
            # Fetch prices
            fresh_prices = self.price_fetcher.fetch_prices(
                ticker,
                days_back=days_needed,
                exchange=exchange
            )
            
            if fresh_prices:
                stored_count = store_stock_prices(self.db, fresh_prices)
                logger.info(f"✅ Stored {stored_count} price records")
                
                # Retrieve from DB
                return get_price_history(self.db, ticker, days_needed)
            else:
                logger.warning(f"⚠️ No prices fetched for {ticker}")
                return existing_prices or []
                
        except Exception as e:
            logger.error(f"Error ensuring price data for {ticker}: {e}")
            return []
    
    def get_latest_or_create(self, ticker: str) -> Optional[Analysis]:
        # Try to get latest
        latest = get_latest_analysis(self.db, ticker)
        
        if latest:
            # Check if it's recent (within last day)
            if (date.today() - latest.date).days <= 1:
                logger.info(f"✅ Using recent analysis from {latest.date}")
                return latest
        
        # Create new analysis
        return self.get_or_create_analysis(ticker, target_date=date.today())
    
    
class AgentOrchestrator:

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.news_agent = AutoNewsAgent(self.db)
        self.analysis_agent = AutoAnalysisAgent(self.db)
    
    def get_complete_stock_data(
        self,
        ticker: str,
        force_refresh: bool = False
    ) -> Dict:
        logger.info(f"🤖 Running complete data pipeline for {ticker}...")
        
        result = {
            'ticker': ticker.upper(),
            'timestamp': datetime.utcnow().isoformat(),
            'news': [],
            'analysis': None,
            'success': False,
            'errors': []
        }
        
        try:
            # Step 1: Get or fetch news
            logger.info("📰 Step 1/2: Getting news...")
            news_articles = self.news_agent.get_or_fetch_news(
                ticker=ticker,
                days_back=7,
                min_articles=3,
                force_refresh=force_refresh
            )
            result['news'] = news_articles
            
            # Step 2: Get or create analysis
            logger.info("📊 Step 2/2: Getting analysis...")
            analysis = self.analysis_agent.get_or_create_analysis(
                ticker=ticker,
                force_refresh=force_refresh
            )
            result['analysis'] = analysis
            
            if analysis:
                result['success'] = True
                logger.info(
                    f"✅ Complete data ready for {ticker}: "
                    f"{len(news_articles)} articles, "
                    f"signal={analysis.signal}"
                )
            else:
                result['errors'].append("Analysis failed")
                logger.warning(f"⚠️ Analysis failed for {ticker}")
            
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def get_market_overview_data(self, force_refresh: bool = False) -> Dict:
        logger.info("🤖 Getting market overview data...")
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'news': [],
            'market_stats': None,
            'success': False
        }
        
        try:
            # Get general news
            news_articles = self.news_agent.get_or_fetch_news(
                ticker=None,
                days_back=3,
                min_articles=5,
                force_refresh=force_refresh
            )
            result['news'] = news_articles
            
            # Get market stats from all analyses
            all_analyses = (
                self.db.query(Analysis)
                .filter(Analysis.date >= date.today() - timedelta(days=7))
                .all()
            )
            
            if all_analyses:
                buy_count = sum(1 for a in all_analyses if 'BUY' in a.signal)
                sell_count = sum(1 for a in all_analyses if 'SELL' in a.signal)
                hold_count = sum(1 for a in all_analyses if a.signal == 'HOLD')
                
                result['market_stats'] = {
                    'total_stocks': len(all_analyses),
                    'buy_signals': buy_count,
                    'sell_signals': sell_count,
                    'hold_signals': hold_count
                }
            
            result['success'] = True
            logger.info(f"✅ Market overview ready: {len(news_articles)} articles")
            
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
        
        return result


_news_agent = None
_analysis_agent = None
_orchestrator = None


def get_news_agent(db: Session = None) -> AutoNewsAgent:
    global _news_agent
    if _news_agent is None or db is not None:
        _news_agent = AutoNewsAgent(db)
    return _news_agent


def get_analysis_agent(db: Session = None) -> AutoAnalysisAgent:
    global _analysis_agent
    if _analysis_agent is None or db is not None:
        _analysis_agent = AutoAnalysisAgent(db)
    return _analysis_agent


def get_orchestrator(db: Session = None) -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None or db is not None:
        _orchestrator = AgentOrchestrator(db)
    return _orchestrator