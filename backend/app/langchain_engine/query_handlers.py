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
from app.ingestion.news_scraper import MultiSourceNewsScraper

logger = logging.getLogger(__name__)

class QueryHandlers:
    def __init__(self):
        self.chat_engine = ChatEngine()
        self.orchestrator = get_orchestrator()
        self.ticker_extractor = LLMTickerExtractor(self.chat_engine.llm)
    
    def handle_top_news(self, context: QueryContext, query: str) -> Dict:

        logger.info("🔥 Handling top news query with FRESH data scraping")
        
        db = SessionLocal()
        try:
            # Determine time period
            days_back = 1  # Always get TODAY's news
            if context.time_period == 'this_week':
                days_back = 7
            elif context.time_period == 'this_month':
                days_back = 30
            elif context.time_period == 'recent':
                days_back = 3

            logger.info(f"🌐 Fetching fresh news from web sources...")
            scraper = MultiSourceNewsScraper()
            
            # Get news for top Indian stocks
            top_tickers = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
            all_fresh_articles = []
            
            for ticker in top_tickers:
                try:
                    articles = scraper.fetch_all_articles(ticker, days_back=1)
                    if articles:
                        from app.ingestion.storage import store_news_articles
                        store_news_articles(db, articles)
                        all_fresh_articles.extend(articles)
                        logger.info(f"✅ Scraped {len(articles)} articles for {ticker}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to scrape {ticker}: {e}")
                    continue
            

            try:
                market_news = scraper.get_market_news('india', days_back=1)
                if market_news:
                    from app.ingestion.storage import store_news_articles
                    store_news_articles(db, market_news)
                    all_fresh_articles.extend(market_news)
                    logger.info(f"✅ Scraped {len(market_news)} general market articles")
            except Exception as e:
                logger.warning(f"⚠️ Failed to scrape market news: {e}")
            
            if not all_fresh_articles:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                all_fresh_articles = (
                    db.query(NewsArticle)
                    .filter(NewsArticle.published_at >= cutoff_date)
                    .order_by(NewsArticle.published_at.desc())
                    .limit(15)
                    .all()
                )
                logger.info(f"⚠️ Using {len(all_fresh_articles)} articles from DB as fallback")
            
            if not all_fresh_articles:
                return {
                    'response': (
                        "I couldn't fetch the latest news at the moment. "
                        "Please try again in a few moments.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            all_fresh_articles.sort(key=lambda x: x.published_at, reverse=True)
            top_articles = all_fresh_articles[:10]
            
            articles_text = ""
            for i, article in enumerate(top_articles, 1):
                articles_text += f"""
    {i}. **{article.title}**
    Company: {article.ticker}
    Source: {article.source}
    Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}
    Summary: {article.content[:200] if article.content else 'No summary available'}...
    
    """
            
            prompt = f"""You are a financial news analyst. Here are today's top 10 stock market news articles:

    {articles_text}

    **Task**: Provide a professional summary of today's top news stories.

    **Format your response as:**

    📰 **Today's Top Market News**

    [Provide a brief 2-3 sentence overview of the overall market sentiment]

    **Key Stories:**

    1. [First story headline and key takeaway in 1-2 sentences]

    2. [Second story headline and key takeaway]

    3. [Third story headline and key takeaway]

    [Continue for all major stories]

    **Market Sentiment**: [Overall positive/negative/mixed and why]

    Keep each story summary concise (1-2 sentences). Focus on what investors need to know.

    ⚠️ **Disclaimer**: This is educational information only, not financial advice. Always do your own research and consult a financial advisor before making investment decisions.
    """
            
            logger.info("🤖 Generating LLM summary of news...")
            result = self.chat_engine.llm.invoke(prompt)
            
            sources = [
                {
                    'title': article.title,
                    'url': article.url,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'ticker': article.ticker,
                    'similarity': 1.0
                }
                for article in top_articles
            ]
            
            response_with_links = result.content + "\n\n---\n\n**📑 Full Articles:**\n\n"
            for i, article in enumerate(top_articles, 1):
                response_with_links += f"{i}. [{article.title}]({article.url})\n"
                response_with_links += f"   🏢 {article.ticker} | 📰 {article.source} | 📅 {article.published_at.strftime('%Y-%m-%d')}\n\n"
            
            return {
                'response': response_with_links,
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
        """Handle stock-specific news with FRESH scraping + LLM extraction."""
        logger.info(f"📰 Handling stock news query: '{query}'")


        if not context.tickers:
            logger.info("🤖 Using LLM to extract ticker from query...")
        extraction = self.ticker_extractor.extract_tickers(query)
        
        if extraction.has_ticker and extraction.tickers:
            context.tickers = extraction.tickers
            logger.info(f"✅ LLM extracted tickers: {extraction.tickers}")
        else:
            return {
                'response': (
                    "I need to know which stock you're asking about. "
                    "Please mention a specific company name or ticker symbol "
                    "(e.g., 'News about Apple', 'Latest on RELIANCE', 'TCS updates').\n\n"
                    "**Popular stocks**: AAPL, MSFT, GOOGL, RELIANCE, TCS, INFY\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
    
        ticker = context.tickers[0].upper()
        db = SessionLocal()
    
        try:
            logger.info(f"🌐 Fetching FRESH news for {ticker} from web...")
            scraper = MultiSourceNewsScraper()
            fresh_articles = scraper.fetch_all_articles(ticker, days_back=3)
        
            if fresh_articles:
                from app.ingestion.storage import store_news_articles
                stored = store_news_articles(db, fresh_articles)
                logger.info(f"✅ Stored {stored} fresh articles for {ticker}")
        

            cutoff_date = datetime.utcnow() - timedelta(days=7)
            all_articles = (
                db.query(NewsArticle)
                .filter(
                NewsArticle.ticker == ticker,
                NewsArticle.published_at >= cutoff_date
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(10)
                .all()
            )
        
            if not all_articles:
                return {
               'response': (
                    f"I couldn't find recent news about {ticker}. This could mean:\n"
                    f"1. The ticker might be spelled differently (check the exact symbol)\n"
                    f"2. Limited news coverage for this stock\n"
                    f"3. Try asking: 'Latest news on [company full name]'\n\n"
                    f"💡 **Tip**: Try 'What's the latest news?' for general market updates.\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': ticker,
                'context_retrieved': False
                }
        
            articles_text = ""
            for i, article in enumerate(all_articles, 1):
                articles_text += f"""
            {i}. **{article.title}**
            Source: {article.source}
            Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}
            Content: {article.content[:300] if article.content else 'No content'}...
            
            """
            prompt = f"""Analyze these recent news articles about {ticker}:

            {articles_text}

            **Task**: Provide a comprehensive news summary for {ticker}.

            **Format:**

            📰 **Latest News for {ticker}**

            **Quick Summary**: [2-3 sentence overview of recent developments]

            **Key Developments**:
            - [Major development 1]
            - [Major development 2]
            - [Major development 3]

            **Sentiment Analysis**: 
            - Overall sentiment: [Positive/Negative/Neutral]
            - Why: [Brief explanation]

            **Investor Takeaway**: [What this means for investors in 1-2 sentences]

            Keep it concise and factual. Focus on what matters to investors.

            ⚠️ **Disclaimer**: This is educational information only, not financial advice.
            """
            
            result = self.chat_engine.llm.invoke(prompt)
                
            response_with_links = result.content + "\n\n---\n\n**📑 Source Articles:**\n\n"
            for i, article in enumerate(all_articles, 1):
                    response_with_links += f"{i}. [{article.title}]({article.url})\n"
                    response_with_links += f"   📰 {article.source} | 📅 {article.published_at.strftime('%Y-%m-%d')}\n\n"
                
            sources = [
                    {
                        'title': article.title,
                        'url': article.url,
                        'source': article.source,
                        'published_at': article.published_at.isoformat(),
                        'similarity': 1.0
                    }
                    for article in all_articles
                ]
                
            return {
                'response': response_with_links,
                'sources': sources,
                'ticker': ticker,
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def handle_stock_analysis(self, context: QueryContext, query: str) -> Dict:
        logger.info(f"📊 Handling stock analysis: '{query}'")


        if not context.tickers:
            logger.info("🤖 Using LLM to extract ticker...")
        extraction = self.ticker_extractor.extract_tickers(query)
        
        if extraction.has_ticker and extraction.tickers:
            context.tickers = extraction.tickers
            logger.info(f"✅ LLM extracted: {extraction.tickers}")
        else:
            return {
                'response': (
                    "Please specify which stock you want me to analyze.\n\n"
                    "**Examples**: 'Analyze AAPL', 'Should I buy Reliance?', 'How is TCS doing?'\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
    
        ticker = context.tickers[0].upper()
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
                    f"**Error**: {error_details}\n\n"
                    f"**Possible reasons**:\n"
                    f"1. Invalid or unrecognized ticker symbol\n"
                    f"2. No price data available for this stock\n"
                    f"3. Data source temporarily unavailable\n\n"
                    f"💡 **Try these popular tickers**: AAPL, MSFT, GOOGL, RELIANCE, TCS, INFY\n\n"
                    "⚠️ **Disclaimer**: This is educational information only."
                ),
                'sources': [],
                'ticker': ticker,
                'context_retrieved': False
                }
        
            logger.info(f"📰 Fetching fresh news for {ticker}...")
            scraper = MultiSourceNewsScraper()
            fresh_news = scraper.fetch_all_articles(ticker, days_back=7)
        
            if fresh_news:
                from app.ingestion.storage import store_news_articles
                store_news_articles(db, fresh_news)
        

            cutoff_date = datetime.utcnow() - timedelta(days=7)
            news_articles = (
                db.query(NewsArticle)
                .filter(
                NewsArticle.ticker == ticker,
                NewsArticle.published_at >= cutoff_date
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(5)
                .all()
            )
        
            news_context = ""
            if news_articles:
                news_context = "**Recent News**:\n"
            for article in news_articles:
                news_context += f"• {article.title} ({article.source}, {article.published_at.strftime('%Y-%m-%d')})\n"
                if article.content:
                    news_context += f"  {article.content[:150]}...\n"
            else:
                news_context = "No recent news available."
        
            analysis = data['analysis']
            import json
        
            enhanced_query = f"""
            Provide a comprehensive analysis of {ticker} combining technical indicators and recent news.

        **Technical Analysis**:
        - Signal: {analysis.signal}
        - Confidence: {float(analysis.confidence):.1%}
        - RSI: {float(analysis.rsi) if analysis.rsi else 'N/A'}
        - MACD: {float(analysis.macd_histogram) if analysis.macd_histogram else 'N/A'}
        - Key Reasons: {json.loads(analysis.reason) if analysis.reason else []}

        {news_context}

        **Your Task**: 
        1. Explain what the technical signals mean
        2. Analyze how recent news affects the outlook
        3. Provide a clear recommendation (BUY/SELL/HOLD) with reasoning
        4. Mention key risks investors should consider

        Be specific and actionable. Format with clear sections.
        """
            
            return self.chat_engine.generate_response(
                query=enhanced_query,
                ticker=ticker
            )
        
        finally:
            db.close()
    
    def handle_stock_recommendation(self, context: QueryContext, query: str) -> Dict:
        
        logger.info("💡 Handling stock recommendation with fresh data")
    
        db = SessionLocal()
        try:
            top_tickers = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 
                      'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
            logger.info(f"🔄 Ensuring fresh analysis for {len(top_tickers)} stocks...")
            analysis_agent = get_analysis_agent(db)
        
            fresh_analyses = []
            for ticker in top_tickers:
                try:
                    analysis = analysis_agent.get_latest_or_create(ticker)
                    if analysis and analysis.signal in ['BUY', 'STRONG_BUY']:
                        fresh_analyses.append(analysis)
                        logger.info(f"✅ {ticker}: {analysis.signal}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to analyze {ticker}: {e}")
                    continue
        
            fresh_analyses.sort(key=lambda x: float(x.confidence), reverse=True)
            top_picks = fresh_analyses[:5]
        
            if not top_picks:
                return {
                'response': (
                    "I'm currently analyzing market conditions. Please try again in a moment, "
                    "or ask about specific stocks like:\n"
                    "• 'Analyze RELIANCE'\n"
                    "• 'Should I buy TCS?'\n"
                    "• 'How is AAPL doing?'\n\n"
                    "⚠️ **Disclaimer**: This is NOT financial advice."
                ),
                'sources': [],
                'ticker': None,
                'context_retrieved': False
            }
        
            import json
            recommendations_text = ""
            for i, analysis in enumerate(top_picks, 1):
                reasons = json.loads(analysis.reason) if analysis.reason else []
                recommendations_text += f"""
{i}. **{analysis.ticker}**
   - Signal: {analysis.signal}
   - Confidence: {float(analysis.confidence):.1%}
   - RSI: {float(analysis.rsi):.1f}
   - Analysis Date: {analysis.date}
   - Key Factor: {reasons[0] if reasons else 'Technical strength'}
   
"""
        
            prompt = f"""Based on fresh technical analysis, here are today's top stock picks with BUY signals:

{recommendations_text}

**Task**: Provide professional stock recommendations.

**Format**:

💼 **Top Stock Recommendations**

**Overview**: [Brief market context]

**Top 3 Picks**:

1. **[Ticker]** - [Why it's a good pick in 2-3 sentences]
   
2. **[Ticker]** - [Why it's a good pick]

3. **[Ticker]** - [Why it's a good pick]

**Important Considerations**:
- [Key risk factor 1]
- [Key risk factor 2]
- [Market condition to watch]

**Investment Strategy**: [Brief guidance on approach]

Be balanced - mention both opportunities AND risks.

⚠️ **CRITICAL DISCLAIMER**: This is educational analysis only, NOT financial advice. Markets are risky. Past performance doesn't guarantee future results. Always do your own research and consult a licensed financial advisor before investing.
"""
        
            result = self.chat_engine.llm.invoke(prompt)
        
            return {
            'response': result.content,
            'sources': [],
            'ticker': None,
            'recommendations': [a.ticker for a in top_picks],
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