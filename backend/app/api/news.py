"""
News-related API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.news import NewsArticle
from app.api.schemas import NewsArticleResponse, NewsSourcesResponse

router = APIRouter()


@router.get("/news/{ticker}", response_model=List[NewsArticleResponse])
async def get_news_for_ticker(
    ticker: str,
    limit: int = Query(10, ge=1, le=50, description="Number of articles to return"),
    days: int = Query(30, ge=1, le=365, description="Filter articles from last N days"),
    db: Session = Depends(get_db)
):
    """
    Fetch latest news articles for a ticker.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    - **limit**: Maximum number of articles to return
    - **days**: Only return articles from last N days
    """
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query articles
    articles = db.query(NewsArticle).filter(
        NewsArticle.ticker == ticker.upper(),
        NewsArticle.published_at >= cutoff_date
    ).order_by(
        NewsArticle.published_at.desc()
    ).limit(limit).all()
    
    if not articles:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for ticker {ticker} in the last {days} days"
        )
    
    return articles


@router.get("/news/{ticker}/sources", response_model=NewsSourcesResponse)
async def get_news_sources(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: Session = Depends(get_db)
):
    """
    Get breakdown of news sources for a ticker.
    Shows which sources are providing the most coverage.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Count articles by source
    sources = db.query(
        NewsArticle.source,
        func.count(NewsArticle.id).label('count')
    ).filter(
        NewsArticle.ticker == ticker.upper(),
        NewsArticle.published_at >= cutoff_date
    ).group_by(
        NewsArticle.source
    ).order_by(
        func.count(NewsArticle.id).desc()
    ).all()
    
    if not sources:
        raise HTTPException(
            status_code=404,
            detail=f"No news sources found for ticker {ticker}"
        )
    
    total = sum(s[1] for s in sources)
    
    return {
        "ticker": ticker.upper(),
        "total_articles": total,
        "sources": [
            {
                "name": source,
                "article_count": count,
                "percentage": round((count / total) * 100, 1)
            }
            for source, count in sources
        ]
    }


@router.get("/news/search/")
async def search_news(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Search news articles by keyword.
    Searches in title and content.
    """
    # Use PostgreSQL's ILIKE for case-insensitive search
    articles = db.query(NewsArticle).filter(
        (NewsArticle.title.ilike(f"%{q}%")) |
        (NewsArticle.content.ilike(f"%{q}%"))
    ).order_by(
        NewsArticle.published_at.desc()
    ).limit(limit).all()
    
    if not articles:
        return {
            "query": q,
            "results": [],
            "count": 0
        }
    
    return {
        "query": q,
        "count": len(articles),
        "results": [
            {
                "id": a.id,
                "ticker": a.ticker,
                "title": a.title,
                "source": a.source,
                "published_at": a.published_at,
                "url": a.url
            }
            for a in articles
        ]
    }