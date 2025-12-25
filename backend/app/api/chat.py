# app/api/chat.py - FIXED VERSION

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import logging

from app.langchain_engine.chat import ChatEngine
from app.langchain_engine.parsers import (
    get_analysis_parser,
    get_chat_parser,
    StockAnalysisOutput,
    ChatResponseOutput
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models

class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., min_length=3, max_length=500, description="User's question")
    ticker: Optional[str] = Field(None, description="Stock ticker (optional, will be extracted if not provided)")
    chat_history: Optional[List[Dict]] = Field(None, description="Previous conversation turns")
    structured: bool = Field(False, description="Return structured output (for analysis queries)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Should I buy AAPL stock?",
                "ticker": "AAPL",
                "structured": False
            }
        }


class Source(BaseModel):
    """News source reference."""
    title: str
    url: str
    source: str
    published_at: str
    similarity: float


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    ticker: Optional[str] = None
    signal: Optional[str] = None
    confidence: Optional[float] = None
    sources: List[Source] = []
    context_retrieved: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on the latest analysis...",
                "ticker": "AAPL",
                "signal": "BUY",
                "confidence": 0.67,
                "sources": [],
                "context_retrieved": True,
                "timestamp": "2025-12-15T10:30:00"
            }
        }


# Endpoints

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest = Body(...)):
    try:
        logger.info(f"Chat request: {request.query[:50]}... (structured={request.structured})")
        
        # Initialize chat engine
        engine = ChatEngine()
        
        # If structured output requested, enhance query with format instructions
        query = request.query
        if request.structured:
            parser = get_analysis_parser()
            query = f"{request.query}\n\n{parser.get_format_instructions()}"
        
        # Generate response
        result = engine.generate_response(
            query=query,
            ticker=request.ticker,
            chat_history=request.chat_history
        )
        
        # FIX: Properly map the result to ChatResponse
        # The result dict might have different keys, so we map them carefully
        
        # Extract sources and convert to Source objects if needed
        sources = []
        if 'sources' in result and result['sources']:
            for src in result['sources']:
                try:
                    sources.append(Source(
                        title=src.get('title', ''),
                        url=src.get('url', ''),
                        source=src.get('source', ''),
                        published_at=src.get('published_at', ''),
                        similarity=src.get('similarity', 0.0)
                    ))
                except Exception as e:
                    logger.warning(f"Could not parse source: {e}")
        
        # Build response with all required fields
        return ChatResponse(
            response=result.get('response', "I don't have enough data about this stock."),
            ticker=result.get('ticker'),
            signal=result.get('signal'),
            confidence=result.get('confidence'),
            sources=sources,
            context_retrieved=result.get('context_retrieved', False),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.post("/chat/analyze", response_model=StockAnalysisOutput)
async def analyze_stock(
    ticker: str = Body(..., embed=True),
    include_news: bool = Body(True, embed=True)
):
    try:
        logger.info(f"Analysis request for {ticker}")
        
        parser = get_analysis_parser()
        
        # Create analysis query with format instructions
        query = f"""
        Provide a comprehensive analysis of {ticker} stock based on:
        1. Technical indicators (RSI, MACD, Moving Averages)
        2. {"Recent news sentiment" if include_news else "Technical data only"}
        3. Current market trends
        
        {parser.get_format_instructions()}
        """
        
        engine = ChatEngine()
        result = engine.generate_response(query=query, ticker=ticker)
        
        # Parse to structured format
        try:
            structured = parser.parse(result['response'])
            return structured
        except Exception as parse_error:
            logger.warning(f"Could not parse structured output: {parse_error}")
            
            # Fallback: create structured output from raw response
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


@router.post("/chat/explain")
async def explain_indicator(
    indicator: str = Body(..., embed=True),
    ticker: str = Body(..., embed=True)
):
    """
    Explain a specific technical indicator.
    
    Simplified endpoint for indicator explanations.
    """
    try:
        query = f"Explain the {indicator} indicator for {ticker} in simple terms"
        
        engine = ChatEngine()
        result = engine.generate_response(query=query, ticker=ticker)
        
        return {
            "indicator": indicator,
            "ticker": ticker,
            "explanation": result.get('response', 'No explanation available'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Explain indicator error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error explaining indicator: {str(e)}"
        )


@router.post("/chat/compare")
async def compare_stocks(
    ticker1: str = Body(..., embed=True),
    ticker2: str = Body(..., embed=True)
):
    """
    Compare two stocks with structured analysis for each.
    """
    try:
        logger.info(f"Comparing {ticker1} vs {ticker2}")
        
        parser = get_analysis_parser()
        engine = ChatEngine()
        
        # Get structured analysis for both
        query_template = """
        Analyze {} stock comprehensively.
        
        {}
        """
        
        # Analyze first ticker
        result1 = engine.generate_response(
            query=query_template.format(ticker1, parser.get_format_instructions()),
            ticker=ticker1
        )
        
        # Analyze second ticker
        result2 = engine.generate_response(
            query=query_template.format(ticker2, parser.get_format_instructions()),
            ticker=ticker2
        )
        
        # Try to parse structured outputs
        try:
            analysis1 = parser.parse(result1['response'])
        except:
            analysis1 = None
            
        try:
            analysis2 = parser.parse(result2['response'])
        except:
            analysis2 = None
        
        return {
            "ticker1": ticker1,
            "ticker2": ticker2,
            "analysis1": analysis1.dict() if analysis1 else {
                "summary": result1.get('response', ''),
                "signal": result1.get('signal'),
                "confidence": result1.get('confidence')
            },
            "analysis2": analysis2.dict() if analysis2 else {
                "summary": result2.get('response', ''),
                "signal": result2.get('signal'),
                "confidence": result2.get('confidence')
            },
            "comparison_summary": f"Comparing {ticker1} and {ticker2} based on technical and fundamental analysis.",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Compare stocks error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing stocks: {str(e)}"
        )


@router.get("/chat/suggestions/{ticker}")
async def get_query_suggestions(ticker: str):
    """
    Get suggested questions for a ticker.
    Helps users know what they can ask.
    """
    suggestions = [
        f"What is the latest news about {ticker}?",
        f"Should I buy {ticker} stock?",
        f"Analyze {ticker} with technical indicators",
        f"What are the technical indicators saying about {ticker}?",
        f"Is {ticker} overvalued or undervalued?",
        f"What are the risks of investing in {ticker}?",
        f"How is {ticker} performing compared to its sector?",
        f"Explain the RSI indicator for {ticker}",
        f"What is the trend for {ticker}?",
        f"What are the bullish factors for {ticker}?",
        f"What are the bearish factors for {ticker}?",
    ]
    
    return {
        "ticker": ticker,
        "suggestions": suggestions
    }


@router.get("/chat/health")
async def health_check():
    """
    Health check endpoint for chat service.
    """
    try:
        # Test chat engine initialization
        engine = ChatEngine()
        
        return {
            "status": "healthy",
            "service": "chat_api",
            "model": engine.model,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )