from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta, date

from app.core.database import get_db
from app.models.stock import StockPrice
from app.api.schemas import StockPriceResponse, LatestPriceResponse

router = APIRouter()


@router.get("/prices/{ticker}", response_model=List[StockPriceResponse])
async def get_prices_for_ticker(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """
    Fetch historical prices for a ticker.
    
    - **ticker**: Stock ticker symbol
    - **days**: Number of trading days to return
    """
    prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper()
    ).order_by(
        StockPrice.date.desc()
    ).limit(days).all()
    
    if not prices:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for ticker {ticker}"
        )
    
    # Return in chronological order (oldest to newest)
    return list(reversed(prices))


@router.get("/prices/{ticker}/latest", response_model=LatestPriceResponse)
async def get_latest_price(
    ticker: str,
    db: Session = Depends(get_db)
):
    """
    Get latest available price for a ticker with change information.
    """
    latest = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper()
    ).order_by(StockPrice.date.desc()).first()
    
    if not latest:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for ticker {ticker}"
        )
    
    # Calculate change
    change = float(latest.close) - float(latest.open)
    change_pct = (change / float(latest.open)) * 100
    
    return {
        "ticker": ticker.upper(),
        "date": latest.date,
        "price": float(latest.close),
        "open": float(latest.open),
        "high": float(latest.high),
        "low": float(latest.low),
        "change": round(change, 2),
        "change_percent": round(change_pct, 2),
        "volume": latest.volume
    }


@router.get("/prices/{ticker}/range")
async def get_price_range(
    ticker: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get price data for a specific date range.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )
    
    prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper(),
        StockPrice.date >= start_date,
        StockPrice.date <= end_date
    ).order_by(StockPrice.date.asc()).all()
    
    if not prices:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for {ticker} between {start_date} and {end_date}"
        )
    
    # Calculate summary statistics
    closes = [float(p.close) for p in prices]
    volumes = [p.volume for p in prices]
    
    return {
        "ticker": ticker.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "data_points": len(prices),
        "summary": {
            "highest_close": max(closes),
            "lowest_close": min(closes),
            "average_close": round(sum(closes) / len(closes), 2),
            "total_volume": sum(volumes),
            "average_volume": sum(volumes) // len(volumes)
        },
        "prices": [
            {
                "date": p.date,
                "open": float(p.open),
                "high": float(p.high),
                "low": float(p.low),
                "close": float(p.close),
                "volume": p.volume
            }
            for p in prices
        ]
    }


@router.get("/prices/tickers/available")
async def get_available_tickers(db: Session = Depends(get_db)):
    """
    Get list of all tickers with available price data.
    """
    tickers = db.query(
        StockPrice.ticker,
        func.count(StockPrice.id).label('data_points'),
        func.min(StockPrice.date).label('earliest_date'),
        func.max(StockPrice.date).label('latest_date')
    ).group_by(
        StockPrice.ticker
    ).order_by(
        StockPrice.ticker
    ).all()
    
    return {
        "count": len(tickers),
        "tickers": [
            {
                "ticker": t[0],
                "data_points": t[1],
                "date_range": {
                    "from": t[2],
                    "to": t[3]
                }
            }
            for t in tickers
        ]
    }