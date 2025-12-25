from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app.models.news import NewsArticle
from app.rag.document_processor import DocumentProcessor
from app.rag.embeddings import EmbeddingGenerator
from app.rag.vector_store import VectorStoreManager
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, db: Session | None = None):
        self.db = db or SessionLocal()
        self.doc_processor = DocumentProcessor()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_store = VectorStoreManager(self.db)

    def process_article(
        self,
        article: NewsArticle,
        force_reprocess: bool = False
    ) -> bool:
        try:
            logger.info(f"Processing article {article.id} ({article.ticker})")

            existing = self.vector_store.get_article_embeddings(article.id)

            if existing and not force_reprocess:
                logger.info(
                    f"Article {article.id} already processed — skipping"
                )
                return True

            if existing and force_reprocess:
                self.vector_store.delete_article_embeddings(article.id)

            chunks = self.doc_processor.process_article(article)
            if not chunks:
                logger.warning(f"No chunks generated for article {article.id}")
                return False

            embedded_docs = self.embedding_gen.embed_documents(chunks)
            if not embedded_docs:
                logger.error(f"No embeddings generated for article {article.id}")
                return False

            embeddings_data = []
            for doc in embedded_docs:
                embeddings_data.append({
                    "article_id": article.id,
                    "chunk_index": doc.metadata["chunk_index"],
                    "content": doc.page_content,
                    "embedding": doc.metadata["embedding"],
                    "extra_metadata": {
                        k: v for k, v in doc.metadata.items()
                        if k != "embedding"
                    }
                })

            stored_count = self.vector_store.store_embeddings_batch(
                embeddings_data
            )

            logger.info(
                f"Article {article.id}: {stored_count} embeddings stored"
            )

            return stored_count > 0

        except Exception:
            logger.exception(
                f"Error processing article {article.id}"
            )
            return False

    def process_articles_batch(
        self,
        articles: List[NewsArticle],
        force_reprocess: bool = False
    ) -> Dict:
        logger.info(f"Processing batch of {len(articles)} articles")

        success_count = 0
        fail_count = 0
        skipped_count = 0

        for i, article in enumerate(articles, 1):
            logger.info(
                f"[{i}/{len(articles)}] Processing article {article.id}"
            )

            try:
                existing = self.vector_store.get_article_embeddings(article.id)

                if existing and not force_reprocess:
                    skipped_count += 1
                    continue

                if self.process_article(article, force_reprocess):
                    success_count += 1
                else:
                    fail_count += 1

            except Exception:
                logger.exception(
                    f"Failed processing article {article.id}"
                )
                fail_count += 1

        stats = {
            "total": len(articles),
            "success": success_count,
            "failed": fail_count,
            "skipped": skipped_count
        }

        logger.info(f"Batch processing complete: {stats}")
        return stats

    def process_ticker_articles(
        self,
        ticker: str,
        days_back: int = 30,
        force_reprocess: bool = False
    ) -> Dict:
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        articles = (
            self.db.query(NewsArticle)
            .filter(
                NewsArticle.ticker == ticker.upper(),
                NewsArticle.published_at >= cutoff_date
            )
            .all()
        )

        logger.info(
            f"Found {len(articles)} articles for {ticker} "
            f"(last {days_back} days)"
        )

        return self.process_articles_batch(articles, force_reprocess)
    
    def process_all_unprocessed_articles(self) -> Dict:
        from sqlalchemy import exists
        from app.models.news import NewsEmbedding

        unprocessed = (
            self.db.query(NewsArticle)
            .filter(
                ~exists().where(
                    NewsEmbedding.article_id == NewsArticle.id
                )
            )
            .all()
        )

        logger.info(
            f"Found {len(unprocessed)} unprocessed articles"
        )

        if not unprocessed:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0
            }

        return self.process_articles_batch(unprocessed)
