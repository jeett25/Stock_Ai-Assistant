# Converts news articles into chunked documents ready for embedding

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List , Dict , Optional
from datetime import datetime
import logging

from app.models.news import NewsArticle
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(
        self,
        chunk_size : int = None,
        chunk_overlap : int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=[
                    "\n\n",  # Paragraph breaks
                    "\n",    # Line breaks
                    ". ",    # Sentences
                    "! ",
                    "? ",
                    " ",     # Words
                    ""       # Characters
                ]
            )
    def article_to_document(self , article: NewsArticle) -> Document:
        full_text = f"{article.title}\n\n{article.content or ''}"
        
        metadata = {
            "article_id": article.id,
            "ticker": article.ticker,
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at.isoformat(),
            "created_at": article.created_at.isoformat(),
            # Add type for filtering
            "doc_type": "news_article"

        }
        return Document(
            page_content=full_text,
            metadata = metadata
        )
    
    def chunk_document(self , document : Document) -> List[Document]:
        chunks = self.text_splitter.split_documents([document])
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["chunk_size"] = len(chunk.page_content)
        
        logger.debug(f"Split document into {len(chunks)} chunks")
        return chunks
    
    def process_article(self , article : NewsArticle) -> List[Document]:
        doc = self.article_to_document(article)
        
        # Chunk it
        chunks = self.chunk_document(doc)
        
        logger.info(
            f"Processed article {article.id} ({article.ticker}): "
            f"{len(chunks)} chunks"
        )
        
        return chunks
    
    def process_articles_batch(self,articles: List[NewsArticle]) -> List[Document]:
        all_chunks = []
        
        for article in articles:
            try:
                chunks = self.process_article(article)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                continue
        
        logger.info(
            f"Batch processed {len(articles)} articles → "
            f"{len(all_chunks)} total chunks"
        )
        
        return all_chunks
    
    def validate_chunk(self, chunk: Document) -> bool:
        # Check minimum content length
        if len(chunk.page_content.strip()) < 50:
            logger.warning(f"Chunk too short: {len(chunk.page_content)} chars")
            return False
        
        # Check required metadata
        required_keys = ["article_id", "ticker", "source"]
        if not all(key in chunk.metadata for key in required_keys):
            logger.warning("Chunk missing required metadata")
            return False
        
        return True