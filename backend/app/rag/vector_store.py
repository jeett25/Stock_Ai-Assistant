from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
import logging

from app.models.news import NewsEmbedding, NewsArticle
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

class VectorStoreManager:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    def store_embedding(
        self,
        article_id: int,
        chunk_index: int,
        content: str,
        embedding: List[float],
        extra_metadata : Dict
    ) -> Optional[NewsEmbedding]:
        try:
            # Check if embedding already exists
            existing = self.db.query(NewsEmbedding).filter(
                NewsEmbedding.article_id == article_id,
                NewsEmbedding.chunk_index == chunk_index
            ).first()
            
            if existing:
                # Update existing
                existing.content = content
                existing.embedding = embedding
                existing.extra_metadata  = extra_metadata 
                logger.debug(f"Updated embedding for article {article_id}, chunk {chunk_index}")
            else:
                # Create new
                embedding_record = NewsEmbedding(
                    article_id=article_id,
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
                    extra_metadata =extra_metadata 
                )
                self.db.add(embedding_record)
                logger.debug(f"Created embedding for article {article_id}, chunk {chunk_index}")
            
            self.db.commit()
            return existing if existing else embedding_record
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing embedding: {e}")
            return None
    
    def store_embeddings_batch(
        self,
        embeddings_data : List[Dict]
    ) -> int:
        stored_count = 0
        
        for data in embeddings_data:
            result = self.store_embedding(
                article_id=data['article_id'],
                chunk_index=data['chunk_index'],
                content=data['content'],
                embedding=data['embedding'],
                extra_metadata =data['extra_metadata']
            )
            
            if result:
                stored_count += 1
        
        logger.info(f"Stored {stored_count}/{len(embeddings_data)} embeddings")
        return stored_count
    
    def search_similar(
        self,
        query_embedding: List[float],
        ticker: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar embeddings using cosine similarity.
        
        FIXED: Convert Python list to PostgreSQL vector string format.
        """
        try:
            # Convert Python list to PostgreSQL vector string format
            # Format: '[0.1, 0.2, 0.3]'
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Build query with optional ticker filter
            if ticker:
                query = text("""
                    SELECT 
                        e.id,
                        e.article_id,
                        e.chunk_index,
                        e.content,
                        e.extra_metadata ,
                        a.ticker,
                        a.title,
                        a.source,
                        a.url,
                        a.published_at,
                        1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM news_embeddings e
                    JOIN news_articles a ON e.article_id = a.id
                    WHERE a.ticker = :ticker
                    AND 1 - (e.embedding <=> CAST(:query_embedding AS vector)) > :threshold
                    ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                """)
                
                results = self.db.execute(
                    query,
                    {
                        "query_embedding": vector_str,  # Use string format
                        "ticker": ticker,
                        "threshold": similarity_threshold,
                        "limit": limit
                    }
                ).fetchall()
            else:
                query = text("""
                    SELECT 
                        e.id,
                        e.article_id,
                        e.chunk_index,
                        e.content,
                        e.extra_metadata ,
                        a.ticker,
                        a.title,
                        a.source,
                        a.url,
                        a.published_at,
                        1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM news_embeddings e
                    JOIN news_articles a ON e.article_id = a.id
                    WHERE a.ticker = :ticker
                    AND 1 - (e.embedding <=> CAST(:query_embedding AS vector)) > :threshold
                    ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                """)
                
                results = self.db.execute(
                    query,
                    {
                        "query_embedding": vector_str,  # Use string format
                        "threshold": similarity_threshold,
                        "limit": limit
                    }
                ).fetchall()
            
            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append({
                    "embedding_id": row[0],
                    "article_id": row[1],
                    "chunk_index": row[2],
                    "content": row[3],
                    "extra_metadata": row[4],
                    "ticker": row[5],
                    "title": row[6],
                    "source": row[7],
                    "url": row[8],
                    "published_at": row[9],
                    "similarity": float(row[10])
                })
            
            logger.info(f"Found {len(formatted_results)} similar chunks for ticker={ticker}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def get_article_embeddings(self, article_id: int) -> List[NewsEmbedding]:
        """Get all embeddings for a specific article."""
        return self.db.query(NewsEmbedding).filter(
            NewsEmbedding.article_id == article_id
        ).order_by(NewsEmbedding.chunk_index).all()
    
    def delete_article_embeddings(self, article_id: int) -> int:
        """Delete all embeddings for a specific article."""
        count = self.db.query(NewsEmbedding).filter(
            NewsEmbedding.article_id == article_id
        ).delete()
        
        self.db.commit()
        logger.info(f"Deleted {count} embeddings for article {article_id}")
        return count
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        total_embeddings = self.db.query(NewsEmbedding).count()
        
        articles_with_embeddings = self.db.query(
            NewsEmbedding.article_id
        ).distinct().count()
        
        return {
            "total_embeddings": total_embeddings,
            "articles_with_embeddings": articles_with_embeddings,
            "avg_chunks_per_article": (
                total_embeddings / articles_with_embeddings
                if articles_with_embeddings > 0 else 0
            )
        }