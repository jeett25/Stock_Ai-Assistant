# app/langchain_engine/output_parsers.py

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from typing import List, Optional


class StockAnalysisOutput(BaseModel):
    """Structured output for stock analysis."""
    
    summary: str = Field(description="Brief summary of the analysis (2-3 sentences)")
    bullish_factors: List[str] = Field(description="List of bullish indicators")
    bearish_factors: List[str] = Field(description="List of bearish indicators")
    risk_level: str = Field(description="Risk level: LOW, MEDIUM, HIGH")
    recommendation: str = Field(description="BUY, SELL, or HOLD")
    confidence: float = Field(description="Confidence score 0-1", ge=0.0, le=1.0)
    
    # FIXED: These were in the example but not in the actual model fields
    current_price: Optional[float] = Field(None, description="Current stock price")
    target_price: Optional[float] = Field(None, description="Target price estimate")
    stop_loss: Optional[float] = Field(None, description="Recommended stop loss price")
    
    # Validators to ensure data quality
    @validator('risk_level')
    def validate_risk_level(cls, v):
        allowed = ['LOW', 'MEDIUM', 'HIGH']
        if v.upper() not in allowed:
            raise ValueError(f'risk_level must be one of {allowed}')
        return v.upper()
    
    @validator('recommendation')
    def validate_recommendation(cls, v):
        allowed = ['BUY', 'SELL', 'HOLD']
        if v.upper() not in allowed:
            raise ValueError(f'recommendation must be one of {allowed}')
        return v.upper()
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "AAPL shows strong momentum with RSI at 45 (neutral). Price is above the 20-day SMA indicating positive trend.",
                "bullish_factors": [
                    "Above 20-day SMA", 
                    "MACD bullish crossover",
                    "Strong earnings report"
                ],
                "bearish_factors": [
                    "High volatility", 
                    "Resistance at $200",
                    "Overbought RSI"
                ],
                "risk_level": "MEDIUM",
                "recommendation": "HOLD",
                "confidence": 0.7,
                "current_price": 195.50,
                "target_price": 210.00,
                "stop_loss": 185.00
            }
        }


class NewsAnalysisOutput(BaseModel):
    """Structured output for news sentiment analysis."""
    
    sentiment: str = Field(description="Overall sentiment: POSITIVE, NEGATIVE, NEUTRAL")
    sentiment_score: float = Field(description="Sentiment score from -1 (negative) to +1 (positive)", ge=-1.0, le=1.0)
    key_topics: List[str] = Field(description="Main topics/themes in the news")
    impact_level: str = Field(description="Expected market impact: HIGH, MEDIUM, LOW")
    summary: str = Field(description="Brief summary of news sentiment")
    
    @validator('sentiment')
    def validate_sentiment(cls, v):
        allowed = ['POSITIVE', 'NEGATIVE', 'NEUTRAL']
        if v.upper() not in allowed:
            raise ValueError(f'sentiment must be one of {allowed}')
        return v.upper()
    
    @validator('impact_level')
    def validate_impact(cls, v):
        allowed = ['HIGH', 'MEDIUM', 'LOW']
        if v.upper() not in allowed:
            raise ValueError(f'impact_level must be one of {allowed}')
        return v.upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "sentiment": "POSITIVE",
                "sentiment_score": 0.65,
                "key_topics": ["Earnings beat", "New product launch", "Market expansion"],
                "impact_level": "HIGH",
                "summary": "Recent news is predominantly positive with strong earnings and product announcements driving optimism."
            }
        }


class ChatResponseOutput(BaseModel):
    """Structured output for general chat responses."""
    
    answer: str = Field(description="Main answer to the user's question")
    key_points: List[str] = Field(description="Key points or takeaways (3-5 bullet points)")
    disclaimer: str = Field(
        default="This is educational information only, not financial advice. Always consult a financial advisor.",
        description="Disclaimer message"
    )
    requires_followup: bool = Field(
        default=False,
        description="Whether the response suggests asking follow-up questions"
    )
    suggested_questions: Optional[List[str]] = Field(
        None,
        description="Suggested follow-up questions"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Based on current technical indicators, AAPL is showing...",
                "key_points": [
                    "RSI at 45 indicates neutral momentum",
                    "Price above 20-day SMA suggests uptrend",
                    "Volume is below average"
                ],
                "disclaimer": "This is educational information only, not financial advice.",
                "requires_followup": True,
                "suggested_questions": [
                    "What are the key risks for AAPL?",
                    "How does AAPL compare to its sector?"
                ]
            }
        }

def get_analysis_parser() -> PydanticOutputParser:
    """Get parser for structured analysis output."""
    return PydanticOutputParser(pydantic_object=StockAnalysisOutput)


def get_news_parser() -> PydanticOutputParser:
    """Get parser for news sentiment analysis."""
    return PydanticOutputParser(pydantic_object=NewsAnalysisOutput)


def get_chat_parser() -> PydanticOutputParser:
    """Get parser for general chat responses."""
    return PydanticOutputParser(pydantic_object=ChatResponseOutput)


