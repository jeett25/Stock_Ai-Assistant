
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

logger = logging.getLogger(__name__)


class QueryHandlers:
    """
    Collection of specialized handlers for different query intents.
    """
    
    def __init__(self):
        self.chat_engine = ChatEngine()
    
    def handle_top_news(self, context: QueryContext, query: str) -> Dict:
        logger.info("Handling top news query")
        
        db = SessionLocal()
        try:
            # Determine time period
            days_back = 1  # Default to today
            if context.time_period == 'this_week':
                days_back = 7
            elif context.time_period == 'this_month':
                days_back = 30
            elif context.time_period == 'recent':
                days_back = 3
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get latest news articles
            articles = (
                db.query(NewsArticle)
                .filter(NewsArticle.published_at >= cutoff_date)
                .order_by(desc(NewsArticle.published_at))
                .limit(10)
                .all()
            )
            
            if not articles:
                return {
                    'response': (
                        "I don't have any recent news articles in the database. "
                        "This could mean the data ingestion hasn't run yet.\n\n"
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
        logger.info(f"Handling stock news query for {context.tickers}")
        
        if not context.tickers:
            return {
                'response': (
                    "I need to know which stock you're asking about. "
                    "Please mention a ticker symbol or company name.\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker = context.tickers[0]
        
        # Use RAG to get relevant news
        retriever = get_retriever(ticker=ticker, k=5)
        docs = retriever.invoke(f"latest news about {ticker}")
        
        if not docs:
            return {
                'response': (
                    f"I don't have any recent news about {ticker} in the database.\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': ticker,
                'context_retrieved': False
            }
        
        # Format news
        news_text = "\n\n".join([
            f"**{doc.metadata.get('title')}**\n"
            f"Source: {doc.metadata.get('source')}\n"
            f"Published: {doc.metadata.get('published_at')}\n"
            f"{doc.page_content[:300]}..."
            for doc in docs
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
                'title': doc.metadata.get('title'),
                'url': doc.metadata.get('url'),
                'source': doc.metadata.get('source'),
                'published_at': doc.metadata.get('published_at'),
                'similarity': doc.metadata.get('similarity', 0.0)
            }
            for doc in docs
        ]
        
        return {
            'response': result.content,
            'sources': sources,
            'ticker': ticker,
            'context_retrieved': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_stock_analysis(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"Handling stock analysis for {context.tickers}")
        
        if not context.tickers:
            return {
                'response': "Please specify which stock you want me to analyze.",
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker = context.tickers[0]
        
        # Use the original generate_response method (it's perfect for this)
        return self.chat_engine.generate_response(query=query, ticker=ticker)
    
    def handle_stock_recommendation(self, context: QueryContext, query: str) -> Dict:
        logger.info("Handling stock recommendation query")
        
        db = SessionLocal()
        try:
            # Get latest analyses with BUY signals
            from app.models.stock import Analysis
            
            buy_signals = (
                db.query(Analysis)
                .filter(Analysis.signal == 'BUY')
                .order_by(desc(Analysis.confidence))
                .limit(5)
                .all()
            )
            
            if not buy_signals:
                return {
                    'response': (
                        "I don't have enough analysis data to recommend stocks at this time. "
                        "Please try asking about specific stocks instead.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only, not financial advice."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            # Format recommendations
            recommendations_text = "\n\n".join([
                f"**{analysis.ticker}**\n"
                f"- Signal: {analysis.signal}\n"
                f"- Confidence: {analysis.confidence:.1%}\n"
                f"- RSI: {analysis.rsi:.1f}\n"
                f"- Key Reasons: {analysis.reason[:200]}..."
                for analysis in buy_signals
            ])
            
            # Get news for top recommendation
            top_ticker = buy_signals[0].ticker
            retriever = get_retriever(ticker=top_ticker, k=3)
            news_docs = retriever.invoke(f"latest news {top_ticker}")
            
            news_text = "\n".join([
                f"- {doc.metadata.get('title')}"
                for doc in news_docs[:3]
            ])
            
            prompt = f"""
            The user asked: "{query}"
            
            Based on technical analysis, here are stocks with BUY signals:
            
            {recommendations_text}
            
            Recent news for top recommendation ({top_ticker}):
            {news_text}
            
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
        """Handle price prediction queries."""
        logger.info(f"Handling price prediction for {context.tickers}")
        
        if not context.tickers:
            return {
                'response': "Please specify which stock you want a price prediction for.",
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker = context.tickers[0]
        
        # Get analysis and news
        return self.chat_engine.generate_response(
            query=f"What is the price outlook for {ticker}? Where do you see the price going?",
            ticker=ticker
        )
    
    def handle_compare_stocks(self, context: QueryContext, query: str) -> Dict:
        """Handle stock comparison queries."""
        logger.info(f"Handling comparison for {context.tickers}")
        
        if len(context.tickers) < 2:
            return {
                'response': "Please specify two stocks to compare (e.g., 'Compare AAPL and MSFT').",
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
        ticker1, ticker2 = context.tickers[0], context.tickers[1]
        
        # Get analysis for both
        db = SessionLocal()
        try:
            analysis1 = get_latest_analysis(db, ticker1)
            analysis2 = get_latest_analysis(db, ticker2)
            
            if not analysis1 or not analysis2:
                return {
                    'response': f"I don't have enough data to compare {ticker1} and {ticker2}.",
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            comparison_text = f"""
            **{ticker1}**:
            - Signal: {analysis1.signal}
            - Confidence: {analysis1.confidence:.1%}
            - RSI: {analysis1.rsi:.1f}
            
            **{ticker2}**:
            - Signal: {analysis2.signal}
            - Confidence: {analysis2.confidence:.1%}
            - RSI: {analysis2.rsi:.1f}
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
        """Handle general questions about investing/markets."""
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
        """Handle market overview queries."""
        logger.info("Handling market overview query")
        
        db = SessionLocal()
        try:
            # Get summary stats across all analyses
            from app.models.stock import Analysis
            
            total = db.query(Analysis).count()
            buy_count = db.query(Analysis).filter(Analysis.signal == 'BUY').count()
            sell_count = db.query(Analysis).filter(Analysis.signal == 'SELL').count()
            hold_count = db.query(Analysis).filter(Analysis.signal == 'HOLD').count()
            
            overview_text = f"""
            Market signals across {total} stocks:
            - BUY signals: {buy_count} ({buy_count/total*100:.1f}%)
            - SELL signals: {sell_count} ({sell_count/total*100:.1f}%)
            - HOLD signals: {hold_count} ({hold_count/total*100:.1f}%)
            """
            
            prompt = f"""
            Provide a market overview based on this signal distribution:
            
            {overview_text}
            
            Discuss:
            1. Overall market sentiment
            2. What these signals suggest
            3. General advice for investors
            
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