from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION
    }


@router.get("/health/db")
async def database_health_check(db: Session = Depends(get_db)):
    try:
        # Test basic query
        result = db.execute(text("SELECT 1")).scalar()
        
        # Test pgvector extension
        db.execute(text("SELECT '[1,2,3]'::vector"))
        
        # Count records in each table
        stock_count = db.execute(text("SELECT COUNT(*) FROM stock_prices")).scalar()
        news_count = db.execute(text("SELECT COUNT(*) FROM news_articles")).scalar()
        analysis_count = db.execute(text("SELECT COUNT(*) FROM analysis")).scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "pgvector": "enabled",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "stock_prices": stock_count,
                "news_articles": news_count,
                "analysis_records": analysis_count
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )