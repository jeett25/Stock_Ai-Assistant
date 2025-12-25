from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Optional, Generator
from datetime import datetime
import logging
import json

from app.core.config import settings
from app.langchain_engine.prompts import (
    create_chat_prompt_template,
    format_news_context,
    format_analysis_context
)
from app.rag.retriever import get_retriever
from app.analysis.storage import get_latest_analysis
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

class ChatEngine:
    def __init__(self,model: str = None,temperature: float = None,streaming: bool = False):
        
        self.model = model or settings.GROQ_MODEL 
        self.temperature = temperature or settings.LLM_TEMPERATURE
        
        self.llm = ChatGroq(
            model=self.model,
            temperature=self.temperature,
            groq_api_key=settings.GROQ_API_KEY,  
            streaming=streaming,
            max_tokens=2048  # Adjust based on your needs
        )
         # self.model = model or settings.LLM_MODEL
        # self.temperature = temperature or settings.LLM_TEMPERATURE
        # 
        # # Initialize LLM
        # callbacks = [StreamingStdOutCallbackHandler()] if streaming else None
        # 
        # self.llm = ChatOpenAI(
        #     model=self.model,
        #     temperature=self.temperature,
        #     openai_api_key=settings.OPENAI_API_KEY,
        #     streaming=streaming,
        #     callbacks=callbacks
        # self.prompt_template = create_chat_prompt_template()
        
        # logger.info(f"ChatEngine initialized with model: {self.model}")
        # )
        
        self.prompt_template = create_chat_prompt_template()
        
        logger.info(f"ChatEngine initialized with Groq model: {self.model}")
        
        
    def extract_ticker(self, query: str) -> Optional[str]:
        query_upper = query.upper()
        
        # Common tickers (expanded with Indian stocks)
        common_tickers = {
            # US Stocks
            'AAPL': ['APPLE', 'AAPL'],
            'MSFT': ['MICROSOFT', 'MSFT'],
            'GOOGL': ['GOOGLE', 'GOOGL', 'ALPHABET'],
            'AMZN': ['AMAZON', 'AMZN'],
            'TSLA': ['TESLA', 'TSLA'],
            'META': ['META', 'FACEBOOK', 'FB'],
            'NVDA': ['NVIDIA', 'NVDA'],

            # Indian Stocks (NSE)
            'RELIANCE': ['RELIANCE', 'RELIANCE INDUSTRIES', 'RIL'],
            'TCS': ['TCS', 'TATA CONSULTANCY SERVICES'],
            'INFY': ['INFOSYS', 'INFY'],
            'HDFCBANK': ['HDFC BANK', 'HDFCBANK'],
            'ICICIBANK': ['ICICI BANK', 'ICICIBANK'],
            'SBIN': ['SBI', 'STATE BANK OF INDIA', 'SBIN'],
            'HINDUNILVR': ['HINDUSTAN UNILEVER', 'HUL', 'HINDUNILVR'],
            'ITC': ['ITC', 'ITC LIMITED'],
            'LT': ['LARSEN', 'L&T', 'LARSEN AND TOUBRO', 'LT'],
            'AXISBANK': ['AXIS BANK', 'AXISBANK'],
            'KOTAKBANK': ['KOTAK', 'KOTAK MAHINDRA BANK', 'KOTAKBANK'],
            'BHARTIARTL': ['AIRTEL', 'BHARTI AIRTEL', 'BHARTIARTL'],
            'ASIANPAINT': ['ASIAN PAINTS', 'ASIANPAINT'],
            'MARUTI': ['MARUTI', 'MARUTI SUZUKI'],
            'TATAMOTORS': ['TATA MOTORS', 'TATAMOTORS'],
            'SUNPHARMA': ['SUN PHARMA', 'SUNPHARMACEUTICAL', 'SUNPHARMA'],
        }
        for ticker, keywords in common_tickers.items():
            for keyword in keywords:
                if keyword in query_upper:
                    logger.info(f"Extracted ticker: {ticker} from query")
                    return ticker
        import re
        dollar_pattern = r'\$([A-Z]{1,5})'
        match = re.search(dollar_pattern, query_upper)
        if match:
            ticker = match.group(1)
            logger.info(f"Extracted ticker from $ pattern: {ticker}")
            return ticker
        
        logger.warning("No ticker found in query")
        return None
    
    def retrieve_context(self,query: str,ticker: Optional[str] = None) -> Dict:
        context = {
            'news_documents': [],
            'analysis': None,
            'ticker': ticker
        }
        
        try:
            # Get relevant news using RAG
            retriever = get_retriever(ticker=ticker, k=5)
            
            docs = retriever.invoke(query)
            context['news_documents'] = [
                {
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                }
                for doc in docs
            ]
            
            logger.info(f"Retrieved {len(docs)} relevant news documents")
            
            if ticker:
                db = SessionLocal()
                try:
                    analysis_record = get_latest_analysis(db, ticker)
                    if analysis_record:
                        context['analysis'] = {
                            'ticker': analysis_record.ticker,
                            'date': analysis_record.date,
                            'signal': analysis_record.signal,
                            'confidence': float(analysis_record.confidence) if analysis_record.confidence else 0.0,
                            'rsi': float(analysis_record.rsi) if analysis_record.rsi else None,
                            'macd_histogram': float(analysis_record.macd_histogram) if analysis_record.macd_histogram else None,
                            'sma_20': float(analysis_record.sma_20) if analysis_record.sma_20 else None,
                            'reasons': json.loads(analysis_record.reason) if analysis_record.reason else [],
                            'indicators': analysis_record.indicators_data or {}
                        }
                        logger.info(f"Retrieved analysis for {ticker}")
                finally:
                    db.close()
        
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
        
        return context
    
    def generate_response(
        self,
        query: str,
        ticker: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Dict:
        
        try:
            # Extract ticker if not provided
            if not ticker:
                ticker = self.extract_ticker(query)
            
            # Retrieve context
            context = self.retrieve_context(query, ticker)
            
            # Check if we have enough context
            if not ticker:
                return {
                    'response': (
                        "I need to know which stock you're asking about. "
                        "Please mention a ticker symbol (e.g., AAPL, MSFT, GOOGL) "
                        "or company name in your question.\n\n"
                        "⚠️ **Disclaimer**: This is educational information only, not financial advice."
                    ),
                    'sources': [],
                    'ticker': None,
                    'context_retrieved': False
                }
            
            if not context['analysis'] and not context['news_documents']:
                return {
                    'response': (
                        f"I don't have enough data about {ticker} to provide analysis. "
                        f"This could mean:\n"
                        f"1. The ticker symbol is incorrect\n"
                        f"2. We haven't ingested data for this stock yet\n"
                        f"3. The analysis hasn't been run\n\n"
                        f"Try asking about: AAPL, MSFT, GOOGL, AMZN, or TSLA.\n\n"
                        f"⚠️ **Disclaimer**: This is educational information only, not financial advice."
                    ),
                    'sources': [],
                    'ticker': ticker,
                    'context_retrieved': False
                }
            
            news_context = format_news_context(context['news_documents'])
            analysis_context = format_analysis_context(context['analysis']) if context['analysis'] else {}
            
            # Build prompt
            prompt_values = {
                'ticker': ticker,
                'query': query,
                'news_context': news_context,
                'current_date': datetime.now().strftime("%Y-%m-%d"),
                **analysis_context
            }
            for key in ['signal', 'confidence', 'rsi', 'rsi_interpretation', 
                       'macd_interpretation', 'ma_interpretation', 'reasons']:
                if key not in prompt_values:
                    prompt_values[key] = "Not available"
            
            # Generate prompt
            formatted_prompt = self.prompt_template.format_messages(**prompt_values)
            
            # Call LLM (Groq)
            logger.info(f"Generating response for query: {query[:50]}...")
            response = self.llm.invoke(formatted_prompt)
            
            # Extract sources
            sources = [
                {
                    'title': doc['metadata'].get('title', 'Untitled'),
                    'url': doc['metadata'].get('url', ''),
                    'source': doc['metadata'].get('source', 'Unknown'),
                    'published_at': doc['metadata'].get('published_at', ''),
                    'similarity': doc['metadata'].get('similarity', 0)
                }
                for doc in context['news_documents']
            ]
            
            return {
                'response': response.content,
                'sources': sources,
                'ticker': ticker,
                'signal': context['analysis'].get('signal') if context['analysis'] else None,
                'confidence': context['analysis'].get('confidence') if context['analysis'] else None,
                'context_retrieved': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'response': (
                    "I encountered an error processing your request. "
                    "Please try rephrasing your question or try again later.\n\n"
                    "⚠️ **Disclaimer**: This is educational information only, not financial advice."
                ),
                'sources': [],
                'ticker': ticker,
                'context_retrieved': False,
                'error': str(e)
            }
    
    def generate_response_stream(
        self,
        query: str,
        ticker: Optional[str] = None
    ) -> Generator[str, None, None]:
        # =====================================================================
        # NEW: Groq supports streaming natively
        # =====================================================================
        try:
            if not ticker:
                ticker = self.extract_ticker(query)
            
            context = self.retrieve_context(query, ticker)
            
            if not ticker or (not context['analysis'] and not context['news_documents']):
                # Return non-streaming response for error cases
                result = self.generate_response(query, ticker)
                yield result['response']
                return
            
            # Format context
            news_context = format_news_context(context['news_documents'])
            analysis_context = format_analysis_context(context['analysis']) if context['analysis'] else {}
            
            prompt_values = {
                'ticker': ticker,
                'query': query,
                'news_context': news_context,
                'current_date': datetime.now().strftime("%Y-%m-%d"),
                **analysis_context
            }
            
            for key in ['signal', 'confidence', 'rsi', 'rsi_interpretation', 
                       'macd_interpretation', 'ma_interpretation', 'reasons']:
                if key not in prompt_values:
                    prompt_values[key] = "Not available"
            
            formatted_prompt = self.prompt_template.format_messages(**prompt_values)
            
            # Stream response from Groq
            for chunk in self.llm.stream(formatted_prompt):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield "Error generating response. Please try again."
        
        # =====================================================================
        # COMMENTED OUT: Original non-streaming placeholder
        # =====================================================================
        # # Note: Streaming implementation would require async setup
        # # For MVP, we'll return complete response
        # # This is a placeholder for future enhancement
        # 
        # result = self.generate_response(query, ticker)
        # yield result['response']
            

            