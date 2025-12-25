from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
from typing import List, Optional
import json
import logging

from app.models.stock import Analysis

logger = logging.getLogger(__name__)


def _make_json_serializable(obj):
    """
    Convert non-serializable objects to JSON-compatible format.
    Handles datetime, date, and other common types.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    else:
        return obj


def store_analysis(
    db: Session,
    ticker: str,
    analysis_date: date,
    indicators: dict,
    signal_data: dict
) -> Optional[Analysis]:
    try:
        existing = db.query(Analysis).filter(
            Analysis.ticker == ticker,
            Analysis.date == analysis_date
        ).first()

        # Technical indicators
        rsi = indicators.get('rsi')
        macd_value = indicators.get('macd_value')
        macd_signal_val = indicators.get('macd_signal')
        macd_histogram = indicators.get('macd_histogram')
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')

        # Signal info
        signal = signal_data.get('signal')
        confidence = signal_data.get('confidence')

        # ✅ FIX: singular "reason"
        reason = json.dumps(signal_data.get('reasons', []))

        # ✅ FIX: Make indicators_data JSON serializable
        # This removes any datetime/date objects that can't be stored in JSONB
        indicators_serializable = _make_json_serializable(indicators)

        if existing:
            existing.rsi = rsi
            existing.macd_value = macd_value
            existing.macd_signal = macd_signal_val
            existing.macd_histogram = macd_histogram
            existing.sma_20 = sma_20
            existing.sma_50 = sma_50
            existing.signal = signal
            existing.confidence = confidence
            existing.reason = reason
            existing.indicators_data = indicators_serializable  # ✅ Fixed

            logger.info(f"Updated analysis for {ticker} on {analysis_date}")
            analysis = existing
        else:
            analysis = Analysis(
                ticker=ticker,
                date=analysis_date,
                rsi=rsi,
                macd_value=macd_value,
                macd_signal=macd_signal_val,
                macd_histogram=macd_histogram,
                sma_20=sma_20,
                sma_50=sma_50,
                signal=signal,
                confidence=confidence,
                reason=reason,                 # ✅ FIX
                indicators_data=indicators_serializable  # ✅ Fixed
            )
            db.add(analysis)
            logger.info(f"Created analysis for {ticker} on {analysis_date}")

        db.commit()
        return analysis

    except Exception as e:
        db.rollback()
        logger.error(f"Error storing analysis for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_latest_analysis(db: Session, ticker: str) -> Optional[Analysis]:
    """Get most recent analysis for a ticker."""
    return db.query(Analysis).filter(
        Analysis.ticker == ticker
    ).order_by(Analysis.date.desc()).first()


def get_analysis_history(
    db: Session,
    ticker: str,
    days: int = 30
) -> List[Analysis]:
    """Get analysis history for a ticker."""
    return db.query(Analysis).filter(
        Analysis.ticker == ticker
    ).order_by(Analysis.date.desc()).limit(days).all()


def get_all_latest_analyses(db: Session, limit: int = 10) -> List[Analysis]:
    from sqlalchemy import func
    
    subq = db.query(
        Analysis.ticker,
        func.max(Analysis.date).label('max_date')
    ).group_by(Analysis.ticker).subquery()
    
    # Join to get full records
    results = db.query(Analysis).join(
        subq,
        (Analysis.ticker == subq.c.ticker) &
        (Analysis.date == subq.c.max_date)
    ).order_by(Analysis.ticker).limit(limit).all()
    
    return results