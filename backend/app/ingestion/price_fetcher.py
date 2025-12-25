"""
Stock price fetcher using yfinance.
Supports both Indian (NSE/BSE) and international stocks.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ingestion.schemas import StockPriceCreate

logger = logging.getLogger(__name__)


class StockPriceFetcher:
    """Fetch stock prices using yfinance for Indian and international markets."""
    
    def __init__(self):
        """Initialize with exchange mappings."""
        # Indian exchanges suffix mapping
        self.indian_exchanges = {
            'NSE': '.NS',  # National Stock Exchange
            'BSE': '.BO',  # Bombay Stock Exchange
        }
        
    def _format_ticker(self, ticker: str, exchange: str = 'NSE') -> str:
        """
        Format ticker for yfinance based on exchange.
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE', 'AAPL')
            exchange: 'NSE', 'BSE', or 'US' (default: 'NSE')
            
        Returns:
            Formatted ticker for yfinance
            
        Examples:
            RELIANCE + NSE -> RELIANCE.NS
            RELIANCE + BSE -> RELIANCE.BO
            AAPL + US -> AAPL
        """
        ticker = ticker.upper().strip()
        
        # If ticker already has exchange suffix, return as is
        if '.NS' in ticker or '.BO' in ticker:
            return ticker
        
        # Check if it's a US/international stock (common tickers)
        us_stocks = {'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 
                     'META', 'NVDA', 'AMD', 'NFLX', 'DIS', 'BABA'}
        
        if ticker in us_stocks or exchange.upper() == 'US':
            return ticker
        
        # Default to NSE for Indian stocks
        exchange = exchange.upper()
        suffix = self.indian_exchanges.get(exchange, '.NS')
        return f"{ticker}{suffix}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_prices(self, ticker: str, days_back: int = 90, exchange: str = 'NSE') -> List[StockPriceCreate]:
        """
        Fetch historical stock prices.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'RELIANCE', 'AAPL')
            days_back: Number of days of history to fetch
            exchange: 'NSE', 'BSE', or 'US' (default: 'NSE')
            
        Returns:
            List of StockPriceCreate objects
        """
        prices = []
        
        try:
            # Format ticker for the exchange
            formatted_ticker = self._format_ticker(ticker, exchange)
            logger.info(f"Fetching prices for {formatted_ticker} (last {days_back} days)")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Fetch data from yfinance
            stock = yf.Ticker(formatted_ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"No price data found for {formatted_ticker}")
                
                # Try alternate exchange if NSE failed
                if exchange == 'NSE' and '.NS' in formatted_ticker:
                    logger.info(f"Retrying with BSE exchange...")
                    return self.fetch_prices(ticker, days_back, exchange='BSE')
                
                return []
            
            # Convert to our schema
            for date, row in hist.iterrows():
                try:
                    # Handle timezone-aware datetime from yfinance
                    date_naive = date.to_pydatetime()
                    if date_naive.tzinfo is not None:
                        date_naive = date_naive.replace(tzinfo=None)
                    
                    price = StockPriceCreate(
                        ticker=ticker.upper(),  # Store original ticker without suffix
                        date=date_naive,
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume'])
                    )
                    prices.append(price)
                    
                except Exception as e:
                    logger.error(f"Error parsing price data for {date}: {e}")
                    continue
            
            logger.info(f"Fetched {len(prices)} price records for {formatted_ticker}")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching prices for {ticker}: {e}")
            return []
    
    def fetch_current_price(self, ticker: str, exchange: str = 'NSE') -> Optional[float]:
        """
        Fetch current/latest price for a ticker.
        Useful for real-time quotes.
        
        Args:
            ticker: Stock ticker symbol
            exchange: 'NSE', 'BSE', or 'US'
            
        Returns:
            Current price as float, or None if not found
        """
        try:
            formatted_ticker = self._format_ticker(ticker, exchange)
            stock = yf.Ticker(formatted_ticker)
            
            # Try fast_info first (faster API)
            try:
                return float(stock.fast_info['lastPrice'])
            except:
                pass
            
            # Fallback to info
            info = stock.info
            
            # Try different price fields
            for price_field in ['currentPrice', 'regularMarketPrice', 'previousClose']:
                if price_field in info and info[price_field]:
                    return float(info[price_field])
            
            # Last resort: get latest from history
            hist = stock.history(period='1d')
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            logger.warning(f"No current price found for {formatted_ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            return None
    
    def get_stock_info(self, ticker: str, exchange: str = 'NSE') -> Dict:
        """
        Fetch basic stock information.
        Useful for validation and metadata.
        
        Args:
            ticker: Stock ticker symbol
            exchange: 'NSE', 'BSE', or 'US'
            
        Returns:
            Dictionary with stock information
        """
        try:
            formatted_ticker = self._format_ticker(ticker, exchange)
            stock = yf.Ticker(formatted_ticker)
            info = stock.info
            
            return {
                'ticker': ticker.upper(),
                'formatted_ticker': formatted_ticker,
                'name': info.get('longName', info.get('shortName', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'INR' if exchange in ['NSE', 'BSE'] else 'USD'),
                'exchange': info.get('exchange', exchange),
                'country': info.get('country', 'India' if exchange in ['NSE', 'BSE'] else 'US')
            }
            
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return {}
    
    def validate_ticker(self, ticker: str, exchange: str = 'NSE') -> bool:
        """
        Validate if a ticker exists and has data.
        
        Args:
            ticker: Stock ticker symbol
            exchange: 'NSE', 'BSE', or 'US'
            
        Returns:
            True if valid, False otherwise
        """
        try:
            formatted_ticker = self._format_ticker(ticker, exchange)
            stock = yf.Ticker(formatted_ticker)
            
            # Try to get recent data
            hist = stock.history(period='5d')
            
            if hist.empty:
                logger.warning(f"No data available for {formatted_ticker}")
                return False
            
            logger.info(f"✅ Ticker {formatted_ticker} is valid")
            return True
            
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False
    
    def get_market_status(self, exchange: str = 'NSE') -> Dict:
        """
        Get market status (open/closed) for the exchange.
        
        Args:
            exchange: 'NSE', 'BSE', or 'US'
            
        Returns:
            Dictionary with market status
        """
        try:
            # Use a major index to check market status
            index_ticker = {
                'NSE': '^NSEI',  # NIFTY 50
                'BSE': '^BSESN',  # SENSEX
                'US': '^GSPC'     # S&P 500
            }.get(exchange.upper(), '^NSEI')
            
            index = yf.Ticker(index_ticker)
            info = index.info
            
            return {
                'exchange': exchange.upper(),
                'is_open': info.get('regularMarketPrice') is not None,
                'last_update': datetime.now().isoformat(),
                'index_value': info.get('regularMarketPrice', 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching market status: {e}")
            return {'exchange': exchange, 'is_open': False}


# Helper function for easy usage
def fetch_indian_stock_prices(ticker: str, days_back: int = 90, exchange: str = 'NSE') -> List[StockPriceCreate]:
    """
    Convenience function to fetch Indian stock prices.
    
    Args:
        ticker: Indian stock ticker (e.g., 'RELIANCE', 'TCS')
        days_back: Number of days of history
        exchange: 'NSE' or 'BSE' (default: 'NSE')
    
    Returns:
        List of stock prices
    
    Example:
        prices = fetch_indian_stock_prices('RELIANCE', days_back=7)
    """
    fetcher = StockPriceFetcher()
    return fetcher.fetch_prices(ticker, days_back, exchange)


def fetch_us_stock_prices(ticker: str, days_back: int = 90) -> List[StockPriceCreate]:
    """
    Convenience function to fetch US stock prices.
    
    Args:
        ticker: US stock ticker (e.g., 'AAPL', 'MSFT')
        days_back: Number of days of history
    
    Returns:
        List of stock prices
    
    Example:
        prices = fetch_us_stock_prices('AAPL', days_back=7)
    """
    fetcher = StockPriceFetcher()
    return fetcher.fetch_prices(ticker, days_back, exchange='US')