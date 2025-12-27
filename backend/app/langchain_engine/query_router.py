from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Types of queries the system can handle."""
    TOP_NEWS = "top_news"  # "What's the latest news?", "Top news today"
    STOCK_NEWS = "stock_news"  # "News about AAPL", "Latest on Tesla"
    STOCK_ANALYSIS = "stock_analysis"  # "Analyze AAPL", "Should I buy TSLA?"
    STOCK_RECOMMENDATION = "stock_recommendation"  # "Best stocks to buy", "Top performers"
    PRICE_PREDICTION = "price_prediction"  # "Will AAPL go up?", "Price forecast"
    COMPARE_STOCKS = "compare_stocks"  # "AAPL vs MSFT", "Compare Apple and Google"
    EXPLAIN_INDICATOR = "explain_indicator"  # "What is RSI?", "Explain MACD"
    GENERAL_QUESTION = "general_question"  # "How does the stock market work?"
    MARKET_OVERVIEW = "market_overview"  # "How is the market doing?"


class QueryContext(BaseModel):
    """Extracted context from user query."""
    intent: QueryIntent
    tickers: List[str] = Field(default_factory=list)
    time_period: Optional[str] = None  # "today", "this week", "last month"
    indicator: Optional[str] = None  # For explain_indicator queries
    keywords: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0)
    
    class Config:
        use_enum_values = True


class QueryRouter:
    """
    Routes queries to appropriate handlers based on intent classification.
    """
    
    def __init__(self):
        # Intent patterns (regex patterns for each intent type)
        self.intent_patterns = {
            QueryIntent.TOP_NEWS: [
                r'(?i)(top|latest|recent|today\'?s?|breaking)\s+(news|headlines)',
                r'(?i)what\'?s?\s+(happening|new|the news)',
                r'(?i)show me\s+(latest|recent|today\'?s?)\s+news',
                r'(?i)news\s+(today|this week)',
            ],
            QueryIntent.STOCK_NEWS: [
                r'(?i)news\s+(about|on|for|regarding|of)\s+(\w+)',
                r'(?i)(\w+)\s+news',
                r'(?i)latest\s+(on|about|for|of)\s+(\w+)',
                r'(?i)what\'?s?\s+(happening|new|latest)\s+(with|on|about|for)\s+(\w+)',
                r'(?i)(recent|latest)\s+news\s+(about|on|for|of)\s+(\w+)',
            ],
            QueryIntent.STOCK_ANALYSIS: [
                r'(?i)(analyze|analysis|review)\s+(\w+)',
                r'(?i)should\s+i\s+(buy|sell|hold)\s+(\w+)',
                r'(?i)how\s+is\s+(\w+)\s+(doing|performing)',
                r'(?i)(\w+)\s+(stock\s+)?(analysis|outlook)',
                r'(?i)tell me about\s+(\w+)',
            ],
            QueryIntent.STOCK_RECOMMENDATION: [
                r'(?i)(best|top|good|recommended)\s+stocks',
                r'(?i)what\s+should\s+i\s+(buy|invest)',
                r'(?i)(recommend|suggest)\s+(stocks|investments)',
                r'(?i)stocks?\s+to\s+(buy|watch|invest)',
                r'(?i)top\s+performers?',
            ],
            QueryIntent.PRICE_PREDICTION: [
                r'(?i)(will|is)\s+(\w+)\s+(go up|rise|increase|go down|fall|drop)',
                r'(?i)(price\s+)?(forecast|prediction|target)\s+(for\s+)?(\w+)',
                r'(?i)where\s+(is|will)\s+(\w+)\s+go',
                r'(?i)(\w+)\s+price\s+(prediction|forecast)',
            ],
            QueryIntent.COMPARE_STOCKS: [
                r'(?i)(\w+)\s+(vs|versus|compared to|vs\.)\s+(\w+)',
                r'(?i)compare\s+(\w+)\s+(and|with|to)\s+(\w+)',
                r'(?i)difference\s+between\s+(\w+)\s+and\s+(\w+)',
            ],
            QueryIntent.EXPLAIN_INDICATOR: [
                r'(?i)(what|explain)\s+(is|the)?\s*(rsi|macd|sma|ema|bollinger|volume)',
                r'(?i)(rsi|macd|sma|ema|bollinger)\s+(indicator|meaning)',
                r'(?i)how\s+(does|to\s+read)\s+(rsi|macd|sma)',
            ],
            QueryIntent.MARKET_OVERVIEW: [
                r'(?i)how\s+(is|are)\s+the\s+(stock\s+)?market',
                r'(?i)market\s+(overview|status|condition|sentiment)',
                r'(?i)overall\s+market',
            ],
        }
        
        # Common ticker symbols with variations
        self.ticker_map = {
            # US Stocks
            'AAPL': ['apple', 'aapl'],
            'MSFT': ['microsoft', 'msft'],
            'GOOGL': ['google', 'googl', 'alphabet'],
            'AMZN': ['amazon', 'amzn'],
            'TSLA': ['tesla', 'tsla'],
            'META': ['meta', 'facebook', 'fb'],
            'NVDA': ['nvidia', 'nvda'],
            
            # Indian Stocks
            'RELIANCE': ['reliance', 'ril'],
            'TCS': ['tcs', 'tata consultancy'],
            'INFY': ['infosys', 'infy'],
            'HDFCBANK': ['hdfc bank', 'hdfcbank', 'hdfc'],
            'ICICIBANK': ['icici bank', 'icicibank', 'icici'],
            'SBIN': ['sbi', 'state bank', 'sbin'],
            'ITC': ['itc'],
            'BHARTIARTL': ['airtel', 'bharti'],
        }
    
    def classify_intent(self, query: str) -> QueryContext:
        query_lower = query.lower()
        
        # Check each intent pattern
        matched_intent = QueryIntent.GENERAL_QUESTION
        matched_confidence = 0.5
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    matched_intent = intent
                    matched_confidence = 0.9
                    break
            if matched_confidence > 0.5:
                break
        
        # Extract tickers
        tickers = self._extract_tickers(query)
        
        # Extract time period
        time_period = self._extract_time_period(query)
        
        # Extract indicator (for explain queries)
        indicator = self._extract_indicator(query)
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        context = QueryContext(
            intent=matched_intent,
            tickers=tickers,
            time_period=time_period,
            indicator=indicator,
            keywords=keywords,
            confidence=matched_confidence
        )
        
        logger.info(f"Classified query: intent={matched_intent}, tickers={tickers}")
        
        return context
    
    def _extract_tickers(self, query: str) -> List[str]:
        """Extract stock tickers from query."""
        query_upper = query.upper()
        found_tickers = []
        
        # Check for $ pattern (e.g., $AAPL)
        dollar_matches = re.findall(r'\$([A-Z]{1,5})', query_upper)
        found_tickers.extend(dollar_matches)
        
        # Check ticker map
        for ticker, variations in self.ticker_map.items():
            for variation in variations:
                if variation.lower() in query.lower():
                    if ticker not in found_tickers:
                        found_tickers.append(ticker)
                    break
        
        return found_tickers
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period from query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['today', 'today\'s']):
            return 'today'
        elif any(word in query_lower for word in ['this week', 'week']):
            return 'this_week'
        elif any(word in query_lower for word in ['this month', 'month']):
            return 'this_month'
        elif any(word in query_lower for word in ['yesterday']):
            return 'yesterday'
        elif any(word in query_lower for word in ['latest', 'recent']):
            return 'recent'
        
        return None
    
    def _extract_indicator(self, query: str) -> Optional[str]:
        """Extract technical indicator name from query."""
        query_lower = query.lower()
        
        indicators = ['rsi', 'macd', 'sma', 'ema', 'bollinger', 'volume', 'obv']
        
        for indicator in indicators:
            if indicator in query_lower:
                return indicator.upper()
        
        return None
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Simple keyword extraction (can be enhanced with NLP)
        query_lower = query.lower()
        
        important_words = [
            'buy', 'sell', 'hold', 'bullish', 'bearish', 
            'risk', 'growth', 'value', 'momentum',
            'earnings', 'revenue', 'profit', 'loss'
        ]
        
        keywords = [word for word in important_words if word in query_lower]
        
        return keywords
    
    def route_query(self, query: str) -> Tuple[QueryContext, str]:
        """
        Route query and return context + routing decision.
        
        Args:
            query: User's question
            
        Returns:
            Tuple of (QueryContext, handler_name)
        """
        context = self.classify_intent(query)
        
        # Determine which handler to use
        handler_map = {
            QueryIntent.TOP_NEWS: "handle_top_news",
            QueryIntent.STOCK_NEWS: "handle_stock_news",
            QueryIntent.STOCK_ANALYSIS: "handle_stock_analysis",
            QueryIntent.STOCK_RECOMMENDATION: "handle_stock_recommendation",
            QueryIntent.PRICE_PREDICTION: "handle_price_prediction",
            QueryIntent.COMPARE_STOCKS: "handle_compare_stocks",
            QueryIntent.EXPLAIN_INDICATOR: "handle_explain_indicator",
            QueryIntent.GENERAL_QUESTION: "handle_general_question",
            QueryIntent.MARKET_OVERVIEW: "handle_market_overview",
        }
        
        handler = handler_map.get(context.intent, "handle_general_question")
        
        logger.info(f"Routing to handler: {handler}")
        
        return context, handler


# Singleton instance
_router = None

def get_query_router() -> QueryRouter:
    """Get singleton QueryRouter instance."""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router