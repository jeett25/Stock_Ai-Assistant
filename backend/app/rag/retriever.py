# app/rag/retriever.py

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from typing import List, Optional
import logging

from app.rag.embeddings import EmbeddingGenerator
from app.rag.vector_store import VectorStoreManager
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class NewsRetriever(BaseRetriever):
    embedding_gen: EmbeddingGenerator
    vector_store: VectorStoreManager
    ticker: Optional[str] = None
    k: int = 5
    similarity_threshold: float = 0.7

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> List[Document]:
        """Retrieve relevant documents for a query."""
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_gen.generate_embedding(query)

            # Search for similar documents
            results = self.vector_store.search_similar(
                query_embedding=query_embedding,
                ticker=self.ticker,
                limit=self.k,
                similarity_threshold=self.similarity_threshold
            )

            # Convert results to Document objects
            documents: List[Document] = []

            for result in results:
                documents.append(
                    Document(
                        page_content=result["content"],
                        metadata={
                            "article_id": result["article_id"],
                            "ticker": result["ticker"],
                            "title": result["title"],
                            "source": result["source"],
                            "url": result["url"],
                            "published_at": str(result["published_at"]),
                            "similarity": result["similarity"],
                            "chunk_index": result["chunk_index"],
                        }
                    )
                )

            logger.info(
                f"Retrieved {len(documents)} documents "
                f"for query='{query[:50]}...'"
            )

            return documents

        except Exception:
            logger.exception("Error retrieving documents")
            return []

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> List[Document]:
        """Async version of _get_relevant_documents."""
        return self._get_relevant_documents(query, run_manager=run_manager)


def get_retriever(
    ticker: Optional[str] = None,
    k: int = 5,
    similarity_threshold: float = 0.7
) -> NewsRetriever:
    db = SessionLocal()

    return NewsRetriever(
        embedding_gen=EmbeddingGenerator(),
        vector_store=VectorStoreManager(db),
        ticker=ticker,
        k=k,
        similarity_threshold=similarity_threshold
    )