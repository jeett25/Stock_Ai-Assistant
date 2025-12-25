from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.core.database import Base

class NewsArticle(Base):
    """News article metadata and content."""
    
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)  # Full article text
    url = Column(Text, unique=True, nullable=False)  # Prevent duplicates
    source = Column(String(50))  # e.g., "Reuters", "Bloomberg"
    published_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to embeddings
    embeddings = relationship("NewsEmbedding", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<NewsArticle(ticker={self.ticker}, title={self.title[:50]})>"
    
class NewsEmbedding(Base):
    __tablename__ = "news_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order of chunks in article
    content = Column(Text, nullable=False)  # The actual text chunk
    
    # embedding = Column(Vector(1536))
    embedding = Column(Vector(384))
    
    # Metadata stored as JSON for flexibility
    extra_metadata = Column(JSONB, default={})
    article = relationship("NewsArticle", back_populates="embeddings")
    
    __table_args__ = (
        Index('ix_embeddings_article', 'article_id'),
        # Cosine similarity index for fast vector search
        Index('ix_embeddings_vector', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )
    
    def __repr__(self):
        return f"<NewsEmbedding(article_id={self.article_id}, chunk={self.chunk_index})>"