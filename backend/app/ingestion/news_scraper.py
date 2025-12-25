import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.ingestion.schemas import NewsArticleCreate

logger = logging.getLogger(__name__)


class NewsScraperBase:
    """Base class for news scrapers."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        
    def fetch_articles(self, ticker: str, days_back: int = 7) -> List[NewsArticleCreate]:
        """
        Fetch articles for a given ticker.
        Override this in subclasses.
        """
        raise NotImplementedError
        
    def _clean_text(self, text: str) -> str:
        """Remove extra whitespace and clean text."""
        if not text:
            return ""
        return " ".join(text.split()).strip()


class RSSNewsScaper(NewsScraperBase):
    """
    Generic RSS feed scraper.
    Works with most financial RSS feeds.
    """
    
    def __init__(self, source_name: str, rss_url_template: str):
        """
        Args:
            source_name: Name of the news source
            rss_url_template: RSS URL with {ticker} placeholder
                Example: "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        """
        super().__init__(source_name)
        self.rss_url_template = rss_url_template
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_articles(self, ticker: str, days_back: int = 7) -> List[NewsArticleCreate]:
        """Fetch articles from RSS feed."""
        articles = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        try:
            # Build URL with ticker
            url = self.rss_url_template.format(ticker=ticker)
            logger.info(f"Fetching RSS feed: {url}")
            
            # Parse RSS feed with custom headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # For some feeds, we need to fetch with requests first
            if 'moneycontrol' in url or 'economictimes' in url:
                response = requests.get(url, headers=headers, timeout=15)
                feed = feedparser.parse(response.content)
            else:
                feed = feedparser.parse(url)
            
            if feed.bozo:  # Feed parsing error
                logger.warning(f"RSS feed parsing warning for {url}: {feed.bozo_exception}")
            
            # Process entries
            for entry in feed.entries:
                try:
                    # Parse publication date
                    pub_date = self._parse_date(entry)
                    
                    # Skip old articles
                    if pub_date < cutoff_date:
                        continue
                    
                    # Extract content
                    content = self._extract_content(entry)
                    
                    article = NewsArticleCreate(
                        ticker=ticker.upper(),
                        title=self._clean_text(entry.get('title', '')),
                        content=content,
                        url=entry.get('link', ''),
                        source=self.source_name,
                        published_at=pub_date
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from {self.source_name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed for {ticker}: {e}")
            return []
    
    def _parse_date(self, entry: dict) -> datetime:
        """Parse publication date from RSS entry."""
        # Try different date fields
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            if hasattr(entry, date_field):
                time_struct = getattr(entry, date_field)
                if time_struct:
                    # Always return timezone-naive datetime in UTC
                    return datetime(*time_struct[:6])
        
        # Fallback to current time (timezone-naive)
        return datetime.utcnow()
    
    def _extract_content(self, entry: dict) -> str:
        """Extract article content from RSS entry."""
        # Try summary first
        if 'summary' in entry:
            return self._clean_text(entry.summary)
        
        # Try description
        if 'description' in entry:
            # Remove HTML tags
            soup = BeautifulSoup(entry.description, 'html.parser')
            return self._clean_text(soup.get_text())
        
        # Try content
        if 'content' in entry and entry.content:
            soup = BeautifulSoup(entry.content[0].value, 'html.parser')
            return self._clean_text(soup.get_text())
        
        return ""


class NewsAPIScaper(NewsScraperBase):
    """
    NewsAPI.org scraper for international coverage.
    Requires free API key from https://newsapi.org/
    """
    
    def __init__(self):
        super().__init__("NewsAPI")
        self.api_key = settings.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2/everything"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_articles(self, ticker: str, days_back: int = 7) -> List[NewsArticleCreate]:
        """Fetch articles from NewsAPI."""
        
        if not self.api_key:
            logger.warning("NEWS_API_KEY not set, skipping NewsAPI")
            return []
        
        articles = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        try:
            # Build query with company name
            company_names = self._get_company_name(ticker)
            query = f"{ticker} OR {company_names}"
            
            params = {
                'q': query,
                'apiKey': self.api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': cutoff_date.date().isoformat(),
                'pageSize': 20
            }
            
            logger.info(f"Fetching from NewsAPI for {ticker}")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'ok':
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            # Process articles
            for item in data.get('articles', []):
                try:
                    # Parse date and make timezone-naive
                    pub_date_str = item['publishedAt'].replace('Z', '+00:00')
                    pub_date = datetime.fromisoformat(pub_date_str)
                    # Convert to timezone-naive UTC
                    if pub_date.tzinfo is not None:
                        pub_date = pub_date.replace(tzinfo=None)
                    
                    article = NewsArticleCreate(
                        ticker=ticker.upper(),
                        title=self._clean_text(item.get('title', '')),
                        content=self._clean_text(item.get('description', '') or item.get('content', '')),
                        url=item.get('url', ''),
                        source=item.get('source', {}).get('name', 'NewsAPI'),
                        published_at=pub_date
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error parsing NewsAPI article: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from NewsAPI")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []
    
    def _get_company_name(self, ticker: str) -> str:
        """Map ticker to company name for better search results."""
        # Indian stocks mapping
        indian_stocks = {
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'HDFCBANK': 'HDFC Bank',
            'INFY': 'Infosys',
            'ICICIBANK': 'ICICI Bank',
            'HINDUNILVR': 'Hindustan Unilever',
            'ITC': 'ITC Limited',
            'SBIN': 'State Bank of India SBI',
            'BHARTIARTL': 'Bharti Airtel',
            'KOTAKBANK': 'Kotak Mahindra Bank',
            'BAJFINANCE': 'Bajaj Finance',
            'LT': 'Larsen & Toubro',
            'ASIANPAINT': 'Asian Paints',
            'MARUTI': 'Maruti Suzuki',
            'HCLTECH': 'HCL Technologies',
            'AXISBANK': 'Axis Bank',
            'WIPRO': 'Wipro',
            'TITAN': 'Titan Company',
            'ADANIENT': 'Adani Enterprises',
            'ADANIPORTS': 'Adani Ports',
        }
        
        # International stocks mapping
        intl_stocks = {
            'AAPL': 'Apple',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google Alphabet',
            'AMZN': 'Amazon',
            'TSLA': 'Tesla',
            'META': 'Meta Facebook',
            'NVDA': 'NVIDIA',
        }
        
        # Check both mappings
        ticker_upper = ticker.upper()
        return (indian_stocks.get(ticker_upper) or 
                intl_stocks.get(ticker_upper) or 
                ticker)


class MultiSourceNewsScraper:
    """
    Aggregates news from multiple Indian and international sources.
    Optimized for Indian market with global coverage.
    """
    
    def __init__(self):
        self.scrapers = [
            # Moneycontrol - Top Indian financial news site
            RSSNewsScaper(
                "Moneycontrol",
                "https://www.moneycontrol.com/rss/results.php"
            ),
            
            # Economic Times - Leading Indian business newspaper
            RSSNewsScaper(
                "Economic Times",
                "https://economictimes.indiatimes.com/rssfeedstopstories.cms"
            ),
            
            # Business Standard
            RSSNewsScaper(
                "Business Standard",
                "https://www.business-standard.com/rss/home_page_top_stories.rss"
            ),
            
            # Hindu Business Line
            RSSNewsScaper(
                "Business Line",
                "https://www.thehindubusinessline.com/portfolio/?service=rss"
            ),
            
            # Google News India - Search by ticker
            RSSNewsScaper(
                "Google News India",
                "https://news.google.com/rss/search?q={ticker}+stock&hl=en-IN&gl=IN&ceid=IN:en"
            ),
            
            # Yahoo Finance India
            RSSNewsScaper(
                "Yahoo Finance India",
                "https://in.finance.yahoo.com/news/rssindex"
            ),
            
            # LiveMint
            RSSNewsScaper(
                "LiveMint",
                "https://www.livemint.com/rss/markets"
            ),
            
            # NDTV Profit
            RSSNewsScaper(
                "NDTV Profit",
                "https://www.ndtvprofit.com/feed"
            ),
            
            # NewsAPI for international coverage (if API key is set)
            NewsAPIScaper(),
        ]
    
    def fetch_all_articles(self, ticker: str, days_back: int = 7) -> List[NewsArticleCreate]:
        """
        Fetch articles from all sources.
        Returns deduplicated list.
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE', 'TCS', 'AAPL')
            days_back: Number of days to look back for articles
            
        Returns:
            List of unique NewsArticleCreate objects
        """
        all_articles = []
        seen_urls = set()
        seen_titles = set()  # Also deduplicate by title for better results
        
        for scraper in self.scrapers:
            try:
                articles = scraper.fetch_articles(ticker, days_back)
                
                # Deduplicate by URL and title
                for article in articles:
                    url_str = str(article.url)
                    title_lower = article.title.lower()
                    
                    # Check if we've seen this article
                    if url_str not in seen_urls and title_lower not in seen_titles:
                        seen_urls.add(url_str)
                        seen_titles.add(title_lower)
                        all_articles.append(article)
                
            except Exception as e:
                logger.error(f"Error with scraper {scraper.source_name}: {e}")
                continue
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        logger.info(f"Total unique articles for {ticker}: {len(all_articles)}")
        return all_articles
    
    def get_market_news(self, market: str = "india", days_back: int = 7) -> List[NewsArticleCreate]:
        """
        Fetch general market news without specific ticker.
        
        Args:
            market: 'india' or 'global'
            days_back: Number of days to look back
            
        Returns:
            List of market news articles
        """
        all_articles = []
        seen_urls = set()
        
        # Select relevant scrapers based on market
        if market.lower() == "india":
            scrapers = [s for s in self.scrapers if s.source_name in [
                "Moneycontrol", "Economic Times", "Business Standard", 
                "Business Line", "LiveMint", "NDTV Profit"
            ]]
        else:
            scrapers = [s for s in self.scrapers if s.source_name == "NewsAPI"]
        
        for scraper in scrapers:
            try:
                # Use dummy ticker for general feeds
                articles = scraper.fetch_articles("MARKET", days_back)
                
                for article in articles:
                    url_str = str(article.url)
                    if url_str not in seen_urls:
                        seen_urls.add(url_str)
                        all_articles.append(article)
                
            except Exception as e:
                logger.error(f"Error fetching market news from {scraper.source_name}: {e}")
                continue
        
        all_articles.sort(key=lambda x: x.published_at, reverse=True)
        logger.info(f"Total market news articles ({market}): {len(all_articles)}")
        return all_articles