# app/api/chat.py - FIXED VERSION

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import logging

from app.langchain_engine.query_router import get_query_router, QueryIntent
from app.langchain_engine.query_handlers import get_query_handlers
from app.langchain_engine.parsers import (
    get_analysis_parser,
    StockAnalysisOutput,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models

class ChatRequest(BaseModel):
    """Chat request model - ticker is now OPTIONAL!"""
    query: str = Field(..., min_length=3, max_length=500, description="User's question")
    ticker: Optional[str] = Field(None, description="Stock ticker (optional - will be auto-detected)")
    chat_history: Optional[List[Dict]] = Field(None, description="Previous conversation turns")
    structured: bool = Field(False, description="Return structured output (for analysis queries)")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "What's the latest news?",
                    "ticker": None
                },
                {
                    "query": "Should I buy AAPL stock?",
                    "ticker": "AAPL"
                },
                {
                    "query": "Analyze Apple stock",
                    "ticker": None
                }
            ]
        }


class Source(BaseModel):
    """News source reference."""
    title: str
    url: str = ""
    source: str = ""
    published_at: str = ""
    similarity: float = 0.0
    ticker: Optional[str] = None


class ChatResponse(BaseModel):
    """Enhanced chat response with routing info."""
    response: str
    ticker: Optional[str] = None
    signal: Optional[str] = None
    confidence: Optional[float] = None
    sources: List[Source] = []
    context_retrieved: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # New fields for debugging/transparency
    intent: Optional[str] = None
    handler: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Here are today's top news stories...",
                "ticker": None,
                "signal": None,
                "confidence": None,
                "sources": [],
                "context_retrieved": True,
                "timestamp": "2025-12-25T10:30:00",
                "intent": "top_news",
                "handler": "handle_top_news"
            }
        }


# Main Chat Endpoint with Intelligent Routing

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest = Body(...)):
    """
    🎯 INTELLIGENT CHAT ENDPOINT
    
    Automatically detects intent and routes to appropriate handler:
    - "What's the latest news?" → Top news handler
    - "Analyze AAPL" → Stock analysis handler
    - "Best stocks to buy?" → Recommendation handler
    - And more!
    
    No need to specify ticker for general queries!
    """
    try:
        logger.info(f"📥 Chat request: '{request.query[:60]}...'")
        
        # Step 1: Classify the query intent
        router_instance = get_query_router()
        context, handler_name = router_instance.route_query(request.query)
        
        logger.info(f"🎯 Detected intent: {context.intent}, Handler: {handler_name}")
        logger.info(f"📍 Extracted tickers: {context.tickers}")
        
        # Override ticker if provided explicitly
        if request.ticker:
            context.tickers = [request.ticker]
        
        # Step 2: Get the appropriate handler
        handlers = get_query_handlers()
        handler_method = getattr(handlers, handler_name)
        
        # Step 3: Process the query with the specialized handler
        result = handler_method(context, request.query)
        
        # Step 4: Convert sources to Source objects
        sources = []
        if 'sources' in result and result['sources']:
            for src in result['sources']:
                try:
                    sources.append(Source(
                        title=src.get('title', ''),
                        url=src.get('url', ''),
                        source=src.get('source', ''),
                        published_at=src.get('published_at', ''),
                        similarity=src.get('similarity', 0.0),
                        ticker=src.get('ticker')
                    ))
                except Exception as e:
                    logger.warning(f"Could not parse source: {e}")
        
        # Step 5: Build response
        # FIX: context.intent is already a string due to use_enum_values=True
        intent_str = context.intent if isinstance(context.intent, str) else context.intent.value
        
        return ChatResponse(
            response=result.get('response', "I couldn't process your request."),
            ticker=result.get('ticker'),
            signal=result.get('signal'),
            confidence=result.get('confidence'),
            sources=sources,
            context_retrieved=result.get('context_retrieved', False),
            timestamp=datetime.utcnow().isoformat(),
            intent=intent_str,
            handler=handler_name
        )
        
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            response=(
                "I encountered an error processing your request. "
                "Please try rephrasing your question or try again later.\n\n"
                "⚠️ **Disclaimer**: This is educational information only, not financial advice."
            ),
            context_retrieved=False,
            intent="error",
            handler="error"
        )


# Specialized Endpoints (still available for direct access)

@router.post("/chat/analyze", response_model=StockAnalysisOutput)
async def analyze_stock(
    ticker: str = Body(..., embed=True),
    include_news: bool = Body(True, embed=True)
):
    """
    Dedicated endpoint for structured stock analysis.
    Returns structured analysis with clear buy/sell/hold recommendation.
    """
    try:
        logger.info(f"📊 Analysis request for {ticker}")
        
        parser = get_analysis_parser()
        
        query = f"""
        Provide a comprehensive analysis of {ticker} stock based on:
        1. Technical indicators (RSI, MACD, Moving Averages)
        2. {"Recent news sentiment" if include_news else "Technical data only"}
        3. Current market trends
        
        {parser.get_format_instructions()}
        """
        
        # Use the router for consistency
        router_instance = get_query_router()
        handlers = get_query_handlers()
        
        from app.langchain_engine.query_router import QueryContext, QueryIntent
        context = QueryContext(
            intent=QueryIntent.STOCK_ANALYSIS,
            tickers=[ticker]
        )
        
        result = handlers.handle_stock_analysis(context, query)
        
        # Parse to structured format
        try:
            structured = parser.parse(result['response'])
            return structured
        except Exception as parse_error:
            logger.warning(f"Could not parse structured output: {parse_error}")
            
            # Fallback
            return StockAnalysisOutput(
                summary=result['response'][:200] + "...",
                bullish_factors=["See full response for details"],
                bearish_factors=["See full response for details"],
                risk_level="MEDIUM",
                recommendation=result.get('signal', 'HOLD'),
                confidence=result.get('confidence', 0.5),
                current_price=None,
                target_price=None,
                stop_loss=None
            )
        
    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing stock: {str(e)}"
        )


@router.get("/chat/suggestions")
async def get_query_suggestions():
    """
    Get example queries users can ask.
    Shows the power of the intelligent routing system!
    """
    suggestions = {
        "Top News": [
            "What's the latest news?",
            "Top news today",
            "Show me recent headlines",
            "What's happening in the market?"
        ],
        "Stock News": [
            "Latest news on AAPL",
            "What's happening with Tesla?",
            "News about Microsoft"
        ],
        "Stock Analysis": [
            "Analyze Apple stock",
            "Should I buy TSLA?",
            "How is Google performing?",
            "Tell me about MSFT"
        ],
        "Recommendations": [
            "Best stocks to buy today",
            "Recommend some stocks",
            "What stocks should I invest in?",
            "Top performers"
        ],
        "Price Predictions": [
            "Will AAPL go up?",
            "Price forecast for Tesla",
            "Where is Microsoft headed?"
        ],
        "Comparisons": [
            "Compare AAPL and MSFT",
            "Apple vs Google",
            "Tesla versus Ford"
        ],
        "Learn": [
            "What is RSI?",
            "Explain MACD indicator",
            "How does the stock market work?"
        ]
    }
    
    return {
        "categories": suggestions,
        "note": "You can ask questions naturally - the system will understand!"
    }


@router.get("/chat/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test components
        router_instance = get_query_router()
        handlers = get_query_handlers()
        
        # Test classification
        test_context, test_handler = router_instance.route_query("What's the latest news?")
        
        # FIX: Handle intent properly
        test_intent = test_context.intent if isinstance(test_context.intent, str) else test_context.intent.value
        
        return {
            "status": "healthy",
            "service": "intelligent_chat_api",
            "components": {
                "router": "operational",
                "handlers": "operational",
                "llm": handlers.chat_engine.model
            },
            "test_classification": {
                "query": "What's the latest news?",
                "detected_intent": test_intent,
                "handler": test_handler
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )