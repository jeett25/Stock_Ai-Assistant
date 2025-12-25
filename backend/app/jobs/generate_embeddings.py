import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.core.database import SessionLocal
from app.models.news import NewsArticle, NewsEmbedding
from app.rag.pipeline import RAGPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_embeddings_for_ticker(
    ticker: str,
    days_back: int = 7,
    force_reprocess: bool = False
) -> dict:
    logger.info(f"Generating embeddings for {ticker}")
    
    pipeline = RAGPipeline()
    stats = pipeline.process_ticker_articles(
        ticker=ticker,
        days_back=days_back,
        force_reprocess=force_reprocess
    )
    
    return stats


def generate_embeddings_for_all_tickers(
    days_back: int = 7,
    force_reprocess: bool = False
) -> dict:
    db = SessionLocal()
    
    try:
        # Get all tickers with articles
        tickers = db.query(NewsArticle.ticker).distinct().all()
        tickers = [t[0] for t in tickers]
        
        logger.info(f"Found {len(tickers)} tickers with articles")
        
        all_stats = {
            "tickers_processed": 0,
            "total_articles": 0,
            "total_success": 0,
            "total_failed": 0
        }
        
        for ticker in tickers:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {ticker}")
            logger.info('='*60)
            
            stats = generate_embeddings_for_ticker(
                ticker=ticker,
                days_back=days_back,
                force_reprocess=force_reprocess
            )
            
            all_stats["tickers_processed"] += 1
            all_stats["total_articles"] += stats.get("total", 0)
            all_stats["total_success"] += stats.get("success", 0)
            all_stats["total_failed"] += stats.get("failed", 0)
        
        logger.info("\n" + "="*60)
        logger.info("EMBEDDING GENERATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Tickers processed: {all_stats['tickers_processed']}")
        logger.info(f"Total articles: {all_stats['total_articles']}")
        logger.info(f"✅ Success: {all_stats['total_success']}")
        logger.info(f"❌ Failed: {all_stats['total_failed']}")
        logger.info("="*60)
        
        return all_stats
        
    finally:
        db.close()


def generate_embeddings_unprocessed_only() -> dict:
    logger.info("Processing unprocessed articles only")
    
    pipeline = RAGPipeline()
    stats = pipeline.process_all_unprocessed_articles()
    
    logger.info("\n" + "="*60)
    logger.info("UNPROCESSED ARTICLES SUMMARY")
    logger.info("="*60)
    logger.info(f"Total processed: {stats.get('total', 0)}")
    logger.info(f"✅ Success: {stats.get('success', 0)}")
    logger.info(f"❌ Failed: {stats.get('failed', 0)}")
    logger.info("="*60)
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate embeddings for news articles"
    )
    parser.add_argument(
        '--ticker',
        type=str,
        help='Process specific ticker (e.g., AAPL)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all tickers'
    )
    parser.add_argument(
        '--unprocessed',
        action='store_true',
        help='Process only articles without embeddings (recommended)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Process articles from last N days (default: 7)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if embeddings exist'
    )
    
    args = parser.parse_args()
    
    try:
        if args.unprocessed:
            # Most common use case
            generate_embeddings_unprocessed_only()
        elif args.ticker:
            generate_embeddings_for_ticker(
                ticker=args.ticker,
                days_back=args.days,
                force_reprocess=args.force
            )
        elif args.all:
            generate_embeddings_for_all_tickers(
                days_back=args.days,
                force_reprocess=args.force
            )
        else:
            # Default: process unprocessed
            logger.info("No option specified, processing unprocessed articles")
            generate_embeddings_unprocessed_only()
    
    except KeyboardInterrupt:
        logger.info("\nJob interrupted by user")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)