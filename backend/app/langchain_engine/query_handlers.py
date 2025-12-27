from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.langchain_engine.query_router import QueryContext, QueryIntent
from app.langchain_engine.chat import ChatEngine
from app.rag.retriever import get_retriever
from app.analysis.storage import get_latest_analysis
from app.models.news import NewsArticle
from app.core.database import SessionLocal
from app.agents.auto_agents import get_news_agent, get_analysis_agent, get_orchestrator
from app.langchain_engine.llm_ticker_extractor import LLMTickerExtractor

logger = logging.getLogger(__name__)

class QueryHandlers:
    def __init__(self):
        self.chat_engine = ChatEngine()
        self.orchestrator = get_orchestrator()
        self.ticker_extractor = LLMTickerExtractor(self.chat_engine.llm)
    
    def handle_top_news(self, context: QueryContext, query: str) -> Dict:
        logger.info("Handling top news query with auto-fetch")
        
        db = SessionLocal()
        try:
            # Determine time period
            days_back = 1
            if context.time_period == 'this_week':
                days_back = 7
            elif context.time_period == 'this_month':
                days_back = 30
            elif context.time_period == 'recent':
                days_back = 3

            news_agent = get_news_agent(db)
            articles = news_agent.get_or_fetch_news(
                ticker=None,  # General news
                days_back=days_back,
                min_articles=5,  # Minimum articles needed
                force_refresh=False
            )
            
            if not articles:
                return {
                    'response': (
                        "I tried to fetch the latest news but couldn't find any articles. "
                        "This might be a temporary issue with news sources.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            # Format news for prompt
            news_text = self._format_news_list(articles)
            
            # Create custom prompt
            prompt = f"""
            The user asked: "{query}"
            
            Here are the latest news articles from the past {days_back} day(s):
            
            {news_text}
            
            Provide a summary of the top news stories, highlighting:
            1. Major market trends
            2. Significant company announcements
            3. Any notable events affecting stocks
            
            Keep it concise and informative.
            
            ⚠️ **Disclaimer**: This is educational information only, not financial advice.
            """
            
            # Generate response
            result = self.chat_engine.llm.invoke(prompt)
            
            # Format sources
            sources = [
                {
                    'title': article.title,
                    'url': article.url,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'ticker': article.ticker,
                    'similarity': 1.0
                }
                for article in articles
            ]
            
            return {
                'response': result.content,
                'sources': sources,
                'ticker': None,
                'signal': None,
                'confidence': None,
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def handle_stock_news(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"Handling stock news query with LLM extraction + auto-fetch")

        if not context.tickers:
            logger.info("🤖 Using LLM to extract ticker...")
            extraction = self.ticker_extractor.extract_tickers(query)
            
            if extraction.has_ticker and extraction.tickers:
                context.tickers = extraction.tickers
                logger.info(f"✅ LLM extracted: {extraction.tickers}")
            else:
                return {
                    'response': (
                        "I need to know which stock you're asking about. "
                        "Please mention a specific company name or ticker symbol.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
        
        ticker = context.tickers[0]
        db = SessionLocal()
        
        try:
            # Use AutoNewsAgent (auto-scrapes if needed)
            news_agent = get_news_agent(db)
            articles = news_agent.get_or_fetch_news(
                ticker=ticker,
                days_back=7,
                min_articles=3,
                force_refresh=False
            )
            
            if not articles:
                return {
                    'response': (
                        f"I tried to find news about {ticker} but couldn't get any recent articles. "
                        f"This could mean:\n"
                        f"1. The ticker might be incorrect\n"
                        f"2. There's limited news coverage for this stock\n"
                        f"3. News sources might be temporarily unavailable\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': ticker,
                    'context_retrieved': False
                }
            
            # Format news
            news_text = "\n\n".join([
                f"**{article.title}**\n"
                f"Source: {article.source}\n"
                f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"{article.content[:300] if article.content else 'No content'}..."
                for article in articles[:5]
            ])
            
            # Create prompt
            prompt = f"""
            The user asked: "{query}"
            
            Here is the latest news about {ticker}:
            
            {news_text}
            
            Summarize the key news and sentiment around {ticker}. Highlight:
            1. Major developments
            2. Overall sentiment (positive/negative/neutral)
            3. Potential impact on the stock
            
            ⚠️ **Disclaimer**: This is educational information only, not financial advice.
            """
            
            result = self.chat_engine.llm.invoke(prompt)
            
            sources = [
                {
                    'title': article.title,
                    'url': article.url,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'similarity': 1.0
                }
                for article in articles
            ]
            
            return {
                'response': result.content,
                'sources': sources,
                'ticker': ticker,
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def handle_stock_analysis(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"Handling stock analysis with LLM extraction + auto-pipeline")
    
        if not context.tickers:
            logger.info("🤖 Using LLM to extract ticker...")
            extraction = self.ticker_extractor.extract_tickers(query)
            
            if extraction.has_ticker and extraction.tickers:
                context.tickers = extraction.tickers
                logger.info(f"✅ LLM extracted: {extraction.tickers}")
            else:
                return {
                    'response': "Please specify which stock you want me to analyze.",
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
        
        ticker = context.tickers[0]
        db = SessionLocal()
        
        try:
            logger.info(f"🤖 Running automated pipeline for {ticker}...")
            
            data = self.orchestrator.get_complete_stock_data(
                ticker=ticker,
                force_refresh=False
            )
            
            if not data['success'] or not data['analysis']:
                error_details = ', '.join(data.get('errors', ['Unknown error']))
                return {
                    'response': (
                        f"I encountered issues analyzing {ticker}:\n"
                        f"{error_details}\n\n"
                        f"This could mean:\n"
                        f"1. Invalid ticker symbol\n"
                        f"2. No price data available\n"
                        f"3. Data source temporarily unavailable\n\n"
                        "Try asking about: AAPL, MSFT, GOOGL, RELIANCE, TCS, or INFY.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': ticker,
                    'context_retrieved': False
                }
            
            return self.chat_engine.generate_response(query=query, ticker=ticker)
            
        finally:
            db.close()
    
    def handle_stock_recommendation(self, context: QueryContext, query: str) -> Dict:
        logger.info("Handling stock recommendation query")
        
        db = SessionLocal()
        try:
            # Get latest analyses with BUY signals
            from app.models.stock import Analysis
            
            buy_signals = (
                db.query(Analysis)
                .filter(Analysis.signal.in_(['BUY', 'STRONG_BUY']))
                .order_by(desc(Analysis.confidence))
                .limit(5)
                .all()
            )
            
            if not buy_signals:
                return {
                    'response': (
                        "I don't have enough recent analysis data to recommend stocks. "
                        "Try asking about specific stocks like AAPL, MSFT, or RELIANCE, "
                        "and I'll analyze them for you.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only, not financial advice."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            # Format recommendations
            import json
            recommendations_text = "\n\n".join([
                f"**{analysis.ticker}**\n"
                f"- Signal: {analysis.signal}\n"
                f"- Confidence: {float(analysis.confidence):.1%}\n"
                f"- RSI: {float(analysis.rsi):.1f}\n"
                f"- Key Reasons: {json.loads(analysis.reason)[0] if analysis.reason else 'N/A'}"
                for analysis in buy_signals
            ])
            
            prompt = f"""
            The user asked: "{query}"
            
            Based on technical analysis, here are stocks with BUY signals:
            
            {recommendations_text}
            
            Provide a balanced recommendation discussing:
            1. Top 3 stocks with strongest signals
            2. Key factors supporting these recommendations
            3. Important risks to consider
            
            ⚠️ **Critical**: Emphasize this is NOT financial advice and users should do their own research.
            """
            
            result = self.chat_engine.llm.invoke(prompt)
            
            return {
                'response': result.content,
                'sources': [],
                'ticker': None,
                'recommendations': [analysis.ticker for analysis in buy_signals],
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def handle_price_prediction(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"Handling price prediction for {context.tickers}")
        
        if not context.tickers:
            return {
                'response': "Please specify which stock you want a price prediction for.",
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker = context.tickers[0]
        return self.handle_stock_analysis(context, query)
    
    def handle_compare_stocks(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"Handling comparison for {context.tickers} with auto-analysis")
        
        if len(context.tickers) < 2:
            return {
                'response': "Please specify two stocks to compare (e.g., 'Compare AAPL and MSFT').",
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker1, ticker2 = context.tickers[0], context.tickers[1]
        db = SessionLocal()
        
        try:
            # ✅ NEW: Auto-analyze both stocks
            analysis_agent = get_analysis_agent(db)
            
            logger.info(f"Auto-analyzing {ticker1}...")
            analysis1 = analysis_agent.get_latest_or_create(ticker1)
            
            logger.info(f"Auto-analyzing {ticker2}...")
            analysis2 = analysis_agent.get_latest_or_create(ticker2)
            
            if not analysis1 or not analysis2:
                missing = []
                if not analysis1:
                    missing.append(ticker1)
                if not analysis2:
                    missing.append(ticker2)
                
                return {
                    'response': (
                        f"I couldn't analyze {', '.join(missing)}. "
                        f"This might be due to insufficient data or invalid ticker symbols.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            import json
            comparison_text = f"""
            **{ticker1}**:
            - Signal: {analysis1.signal}
            - Confidence: {float(analysis1.confidence):.1%}
            - RSI: {float(analysis1.rsi):.1f}
            - Reasons: {json.loads(analysis1.reason)[0] if analysis1.reason else 'N/A'}
            
            **{ticker2}**:
            - Signal: {analysis2.signal}
            - Confidence: {float(analysis2.confidence):.1%}
            - RSI: {float(analysis2.rsi):.1f}
            - Reasons: {json.loads(analysis2.reason)[0] if analysis2.reason else 'N/A'}
            """
            
            prompt = f"""
            Compare {ticker1} and {ticker2} based on this technical analysis:
            
            {comparison_text}
            
            Provide a balanced comparison covering:
            1. Which has stronger technical signals
            2. Risk levels for each
            3. Key differences in their outlooks
            
            ⚠️ **Disclaimer**: This is educational information only, not financial advice.
            """
            
            result = self.chat_engine.llm.invoke(prompt)
            
            return {
                'response': result.content,
                'sources': [],
                'tickers': [ticker1, ticker2],
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def handle_explain_indicator(self, context: QueryContext, query: str) -> Dict:
        """Handle technical indicator explanation queries."""
        indicator = context.indicator or "technical indicators"
        
        prompt = f"""
        Explain {indicator} in simple terms that a beginner can understand.
        
        Cover:
        1. What it measures
        2. How to interpret it
        3. Common values to watch for
        4. Example: "If RSI is above 70, the stock might be overbought"
        
        Keep it under 150 words and use simple language.
        """
        
        result = self.chat_engine.llm.invoke(prompt)
        
        return {
            'response': result.content,
            'sources': [],
            'ticker': None,
            'context_retrieved': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_general_question(self, context: QueryContext, query: str) -> Dict:
        prompt = f"""
        Answer this question about investing/stock markets:
        
        "{query}"
        
        Provide an educational, balanced response. If it's about a specific stock,
        mention that you need more details to provide specific analysis.
        
        ⚠️ **Disclaimer**: This is educational information only, not financial advice.
        """
        
        result = self.chat_engine.llm.invoke(prompt)
        
        return {
            'response': result.content,
            'sources': [],
            'ticker': None,
            'context_retrieved': False,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_market_overview(self, context: QueryContext, query: str) -> Dict:
        logger.info("Handling market overview query with auto-fetch")
        
        db = SessionLocal()
        try:
            # ✅ NEW: Use orchestrator for market data
            data = self.orchestrator.get_market_overview_data(force_refresh=False)
            
            if not data['success']:
                return {
                    'response': (
                        "I couldn't fetch market overview data at the moment. "
                        "Please try again later.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            # Format overview
            stats = data.get('market_stats', {})
            news_count = len(data.get('news', []))
            
            overview_text = f"""
            Recent market data:
            - Total stocks analyzed: {stats.get('total_stocks', 0)}
            - BUY signals: {stats.get('buy_signals', 0)}
            - SELL signals: {stats.get('sell_signals', 0)}
            - HOLD signals: {stats.get('hold_signals', 0)}
            - Recent news articles: {news_count}
            """
            
            prompt = f"""
            Provide a market overview based on this data:
            
            {overview_text}
            
            Discuss:
            1. Overall market sentiment based on signal distribution
            2. What these signals suggest about the market
            3. General guidance for investors
            
            ⚠️ **Disclaimer**: This is educational information only, not financial advice.
            """
            
            result = self.chat_engine.llm.invoke(prompt)
            
            return {
                'response': result.content,
                'sources': [],
                'ticker': None,
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def _format_news_list(self, articles: List[NewsArticle]) -> str:
        """Format news articles for prompt."""
        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(
                f"{i}. **{article.title}** ({article.ticker})\n"
                f"   Source: {article.source} | "
                f"Published: {article.published_at.strftime('%Y-%m-%d')}\n"
                f"   {article.content[:200] if article.content else 'No content'}...\n"
            )
        return "\n".join(formatted)


# Singleton instance
_handlers = None

def get_query_handlers() -> QueryHandlers:
    """Get singleton QueryHandlers instance."""
    global _handlers
    if _handlers is None:
        _handlers = QueryHandlers()
    return _handlers