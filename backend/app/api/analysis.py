from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json

from app.core.database import get_db
from app.models.stock import Analysis
from app.analysis.storage import (
    get_latest_analysis,
    get_analysis_history,
    get_all_latest_analyses
)

router = APIRouter()


class AnalysisResponse:
    """Response model for analysis."""
    ticker: str
    date: date
    signal: str
    confidence: float
    reasons: List[str]
    
    # Key indicators
    rsi: Optional[float]
    macd_value: Optional[float]
    macd_signal: Optional[float]
    sma_20: Optional[float]
    sma_50: Optional[float]
    
    # Full indicator data
    indicators: dict
    
    @classmethod
    def from_orm(cls, analysis: Analysis):
        """Convert SQLAlchemy model to response."""
        try:
            reasons = json.loads(analysis.reasons) if analysis.reasons else []
        except:
            reasons = []
        
        return {
            "ticker": analysis.ticker,
            "date": analysis.date,
            "signal": analysis.signal,
            "confidence": float(analysis.confidence) if analysis.confidence else 0.0,
            "reasons": reasons,
            "rsi": float(analysis.rsi) if analysis.rsi else None,
            "macd_value": float(analysis.macd_value) if analysis.macd_value else None,
            "macd_signal": float(analysis.macd_signal) if analysis.macd_signal else None,
            "sma_20": float(analysis.sma_20) if analysis.sma_20 else None,
            "sma_50": float(analysis.sma_50) if analysis.sma_50 else None,
            "indicators": analysis.indicators_data or {}
        }


@router.get("/analysis/{ticker}")
async def get_ticker_analysis(
    ticker: str,
    db: Session = Depends(get_db)
):
    analysis = get_latest_analysis(db, ticker.upper())
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for ticker {ticker}. Run analysis job first."
        )
    
    return AnalysisResponse.from_orm(analysis)


@router.get("/analysis/{ticker}/history")
async def get_ticker_analysis_history(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    history = get_analysis_history(db, ticker.upper(), days)
    
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis history found for {ticker}"
        )
    
    return {
        "ticker": ticker.upper(),
        "data_points": len(history),
        "history": [AnalysisResponse.from_orm(a) for a in history]
    }


@router.get("/analysis/{ticker}/summary")
async def get_ticker_summary(
    ticker: str,
    db: Session = Depends(get_db)
):
    analysis = get_latest_analysis(db, ticker.upper())
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for {ticker}"
        )
    
    try:
        reasons = json.loads(analysis.reasons) if analysis.reasons else []
    except:
        reasons = []
    
    # Determine recommendation text
    signal = analysis.signal
    confidence = float(analysis.confidence) if analysis.confidence else 0.0
    
    if signal == 'STRONG_BUY':
        recommendation = "Strong Buy - Multiple bullish indicators"
    elif signal == 'BUY':
        recommendation = "Buy - Some bullish indicators"
    elif signal == 'STRONG_SELL':
        recommendation = "Strong Sell - Multiple bearish indicators"
    elif signal == 'SELL':
        recommendation = "Sell - Some bearish indicators"
    else:
        recommendation = "Hold - Mixed or neutral signals"
    
    return {
        "ticker": ticker.upper(),
        "date": analysis.date,
        "signal": signal,
        "confidence": confidence,
        "recommendation": recommendation,
        "key_reasons": reasons[:3],  # Top 3 reasons
        "key_indicators": {
            "rsi": float(analysis.rsi) if analysis.rsi else None,
            "rsi_interpretation": (
                "Oversold" if analysis.rsi and analysis.rsi < 30 else
                "Overbought" if analysis.rsi and analysis.rsi > 70 else
                "Neutral"
            ) if analysis.rsi else None,
            "price_vs_sma20": (
                "Above" if analysis.sma_20 and 
                analysis.indicators_data.get('close_price', 0) > float(analysis.sma_20)
                else "Below"
            ) if analysis.sma_20 else None,
        },
        "disclaimer": "⚠️ This is NOT financial advice. For educational purposes only."
    }


@router.get("/analysis/dashboard/overview")
async def get_dashboard_overview(
    limit: int = Query(10, ge=1, le=50),
    signal_filter: Optional[str] = Query(None, description="Filter by signal (BUY/SELL/HOLD)"),
    db: Session = Depends(get_db)
):
    analyses = get_all_latest_analyses(db, limit)
    
    if not analyses:
        return {
            "count": 0,
            "analyses": [],
            "message": "No analyses available. Run analysis job first."
        }
    
    # Filter by signal if specified
    if signal_filter:
        signal_filter = signal_filter.upper()
        analyses = [a for a in analyses if a.signal == signal_filter]
    
    results = []
    for analysis in analyses:
        try:
            reasons = json.loads(analysis.reasons) if analysis.reasons else []
        except:
            reasons = []
        
        results.append({
            "ticker": analysis.ticker,
            "date": analysis.date,
            "signal": analysis.signal,
            "confidence": float(analysis.confidence) if analysis.confidence else 0.0,
            "top_reason": reasons[0] if reasons else "No specific reason",
            "rsi": float(analysis.rsi) if analysis.rsi else None,
        })
    
    # Summary stats
    signals_count = {}
    for r in results:
        signal = r['signal']
        signals_count[signal] = signals_count.get(signal, 0) + 1
    
    return {
        "count": len(results),
        "signal_distribution": signals_count,
        "analyses": results,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/analysis/indicators/explanation")
async def get_indicators_explanation():
    return {
        "indicators": {
            "RSI": {
                "name": "Relative Strength Index",
                "description": "Measures momentum on a scale of 0-100",
                "interpretation": {
                    "< 30": "Oversold - potential buy signal",
                    "30-70": "Neutral range",
                    "> 70": "Overbought - potential sell signal"
                },
                "period": "14 days (default)"
            },
            "MACD": {
                "name": "Moving Average Convergence Divergence",
                "description": "Shows relationship between two moving averages",
                "components": {
                    "MACD Line": "12-day EMA - 26-day EMA",
                    "Signal Line": "9-day EMA of MACD line",
                    "Histogram": "MACD - Signal"
                },
                "interpretation": {
                    "MACD crosses above signal": "Bullish signal",
                    "MACD crosses below signal": "Bearish signal"
                }
            },
            "SMA": {
                "name": "Simple Moving Average",
                "description": "Average price over a period",
                "common_periods": {
                    "20-day": "Short-term trend",
                    "50-day": "Medium-term trend",
                    "200-day": "Long-term trend"
                },
                "interpretation": {
                    "Price above SMA": "Bullish",
                    "Price below SMA": "Bearish"
                }
            },
            "Bollinger Bands": {
                "name": "Bollinger Bands",
                "description": "Volatility bands around a moving average",
                "components": {
                    "Upper Band": "SMA + (2 × standard deviation)",
                    "Middle Band": "20-day SMA",
                    "Lower Band": "SMA - (2 × standard deviation)"
                },
                "interpretation": {
                    "Price near upper band": "Overbought",
                    "Price near lower band": "Oversold",
                    "Bands narrowing": "Low volatility, potential breakout"
                }
            }
        },
        "signals": {
            "STRONG_BUY": "Multiple strong bullish indicators aligned",
            "BUY": "Some bullish indicators present",
            "HOLD": "Mixed or neutral signals",
            "SELL": "Some bearish indicators present",
            "STRONG_SELL": "Multiple strong bearish indicators aligned"
        },
        "disclaimer": "These are educational explanations. Always do your own research and consult a licensed financial advisor."
    }