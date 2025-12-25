"""
Complete test script for Phase 2.
Tests all components: ingestion, storage, and API endpoints.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import requests
import time
from app.core.database import SessionLocal
from app.ingestion.news_scraper import MultiSourceNewsScraper
from app.ingestion.price_fetcher import StockPriceFetcher
from app.ingestion.storage import store_news_articles, store_stock_prices
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TEST_TICKERS = ["AAPL", "MSFT", "GOOGL"]


def test_health_checks():
    """Test 1: Verify API is running."""
    logger.info("=" * 60)
    logger.info("TEST 1: Health Checks")
    logger.info("=" * 60)
    
    try:
        # Basic health
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code == 200
        logger.info("✅ Basic health check passed")
        
        # Database health
        response = requests.get(f"{BASE_URL}/api/health/db", timeout=5)
        assert response.status_code == 200
        data = response.json()
        logger.info(f"✅ Database health check passed")
        logger.info(f"   Stats: {data['stats']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Health checks failed: {e}")
        return False


def test_data_ingestion():
    """Test 2: Ingest data for test tickers."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Data Ingestion")
    logger.info("=" * 60)
    
    db = SessionLocal()
    total_news = 0
    total_prices = 0
    
    try:
        for ticker in TEST_TICKERS:
            logger.info(f"\n📥 Ingesting data for {ticker}...")
            
            # Fetch and store news
            try:
                scraper = MultiSourceNewsScraper()
                articles = scraper.fetch_all_articles(ticker, days_back=7)
                news_count = store_news_articles(db, articles)
                total_news += news_count
                logger.info(f"   ✅ News: {news_count} articles")
            except Exception as e:
                logger.error(f"   ❌ News failed: {e}")
            
            # Fetch and store prices
            try:
                fetcher = StockPriceFetcher()
                prices = fetcher.fetch_prices(ticker, days_back=30)
                price_count = store_stock_prices(db, prices)
                total_prices += price_count
                logger.info(f"   ✅ Prices: {price_count} records")
            except Exception as e:
                logger.error(f"   ❌ Prices failed: {e}")
            
            time.sleep(1)  # Rate limiting
        
        logger.info(f"\n📊 Total ingested:")
        logger.info(f"   News articles: {total_news}")
        logger.info(f"   Price records: {total_prices}")
        
        return total_news > 0 and total_prices > 0
        
    finally:
        db.close()


def test_news_api():
    """Test 3: News API endpoints."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: News API Endpoints")
    logger.info("=" * 60)
    
    ticker = TEST_TICKERS[0]
    
    try:
        # Get news for ticker
        response = requests.get(f"{BASE_URL}/api/news/{ticker}?limit=5", timeout=5)
        assert response.status_code == 200
        articles = response.json()
        logger.info(f"✅ GET /api/news/{ticker}")
        logger.info(f"   Returned {len(articles)} articles")
        
        if articles:
            logger.info(f"   Latest: {articles[0]['title'][:60]}...")
        
        # Get news sources
        response = requests.get(f"{BASE_URL}/api/news/{ticker}/sources", timeout=5)
        assert response.status_code == 200
        sources = response.json()
        logger.info(f"✅ GET /api/news/{ticker}/sources")
        logger.info(f"   Sources: {len(sources['sources'])}")
        
        for source in sources['sources'][:3]:
            logger.info(f"      • {source['name']}: {source['article_count']} articles")
        
        # Search news
        response = requests.get(
            f"{BASE_URL}/api/news/search/?q=earnings&limit=3",
            timeout=5
        )
        assert response.status_code == 200
        results = response.json()
        logger.info(f"✅ GET /api/news/search/")
        logger.info(f"   Found {results['count']} results for 'earnings'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ News API tests failed: {e}")
        return False


def test_prices_api():
    """Test 4: Prices API endpoints."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Prices API Endpoints")
    logger.info("=" * 60)
    
    ticker = TEST_TICKERS[0]
    
    try:
        # Get historical prices
        response = requests.get(f"{BASE_URL}/api/prices/{ticker}?days=7", timeout=5)
        assert response.status_code == 200
        prices = response.json()
        logger.info(f"✅ GET /api/prices/{ticker}")
        logger.info(f"   Returned {len(prices)} price records")
        
        # Get latest price
        response = requests.get(f"{BASE_URL}/api/prices/{ticker}/latest", timeout=5)
        assert response.status_code == 200
        latest = response.json()
        logger.info(f"✅ GET /api/prices/{ticker}/latest")
        logger.info(f"   Price: ${latest['price']:.2f}")
        logger.info(f"   Change: {latest['change']:+.2f} ({latest['change_percent']:+.2f}%)")
        
        # Get available tickers
        response = requests.get(f"{BASE_URL}/api/prices/tickers/available", timeout=5)
        assert response.status_code == 200
        tickers = response.json()
        logger.info(f"✅ GET /api/prices/tickers/available")
        logger.info(f"   Available tickers: {tickers['count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Prices API tests failed: {e}")
        return False


def test_ingestion_api():
    """Test 5: Manual ingestion API."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Ingestion API")
    logger.info("=" * 60)
    
    try:
        # Trigger ingestion for single ticker
        ticker = "TSLA"
        response = requests.post(f"{BASE_URL}/api/ingest/{ticker}", timeout=5)
        assert response.status_code == 200
        result = response.json()
        logger.info(f"✅ POST /api/ingest/{ticker}")
        logger.info(f"   Status: {result['message']}")
        
        # Wait a bit for background task
        logger.info("   Waiting 5 seconds for ingestion...")
        time.sleep(5)
        
        # Verify data was ingested
        response = requests.get(f"{BASE_URL}/api/news/{ticker}?limit=1", timeout=5)
        if response.status_code == 200:
            logger.info(f"   ✅ Data verified in database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ingestion API test failed: {e}")
        return False


def run_all_tests():
    """Run complete test suite."""
    logger.info("\n" + "🧪 " * 30)
    logger.info("PHASE 2 - COMPLETE TEST SUITE")
    logger.info("🧪 " * 30 + "\n")
    
    results = {
        "Health Checks": test_health_checks(),
        "Data Ingestion": test_data_ingestion(),
        "News API": test_news_api(),
        "Prices API": test_prices_api(),
        "Ingestion API": test_ingestion_api(),
    }
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Phase 2 is complete.")
    else:
        logger.info("\n⚠️  Some tests failed. Check logs above.")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Phase 2 Implementation")
    parser.add_argument(
        '--test',
        choices=['health', 'ingestion', 'news', 'prices', 'api', 'all'],
        default='all',
        help='Which test to run'
    )
    
    args = parser.parse_args()
    
    if args.test == 'health':
        test_health_checks()
    elif args.test == 'ingestion':
        test_data_ingestion()
    elif args.test == 'news':
        test_news_api()
    elif args.test == 'prices':
        test_prices_api()
    elif args.test == 'api':
        test_ingestion_api()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)