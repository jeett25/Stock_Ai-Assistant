# from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from typing import List, Optional
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        # if not settings.OPENAI_API_KEY:
        #     raise ValueError(
        #         "OPENAI_API_KEY not set in environment. "
        #     )
        
        # self.embeddings = OpenAIEmbeddings(
        #     openai_api_key=settings.OPENAI_API_KEY,
        #     model=settings.EMBEDDING_MODEL,
        #     chunk_size=100  
        # )
        
        # logger.info(f"Initialized embeddings with model: {settings.EMBEDDING_MODEL}")
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU available
                    encode_kwargs={'normalize_embeddings': True}  # For better similarity search
                )
                
                # Embedding dimension for this model is 384 (vs 1536 for OpenAI)
                self.embedding_dimension = 384
                
                logger.info(
                    f"Initialized HuggingFace embeddings with model: "
                    f"sentence-transformers/all-MiniLM-L6-v2 (dimension: {self.embedding_dimension})"
                )
                
            except Exception as e:
                logger.error(f"Error initializing HuggingFace embeddings: {e}")
                raise
    
    def generate_embedding(self , text: str) -> List[float]:
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e :
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32,  # Reduced from 100 for local processing
        delay_between_batches: float = 0.0  # No delay needed for local processing
    ) -> List[List[float]]:
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            try:
                logger.info(
                    f"Generating embeddings batch {batch_num}/{total_batches} "
                    f"({len(batch)} texts)"
                )
                
                # Generate embeddings for batch
                embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(embeddings)
                
                # Rate limiting
                if batch_num < total_batches:
                    time.sleep(delay_between_batches)
                
            except Exception as e:
                logger.error(f"Error in batch {batch_num}: {e}")
                # Return None for failed embeddings
                all_embeddings.extend([None] * len(batch))
        
        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def embed_documents(self , documents : List[Document]) -> List[Document]:
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings_batch(texts)
        
        embedded_docs = []
        for doc, embedding in zip(documents, embeddings):
            if embedding is not None:
                # Create new document with embedding in metadata
                embedded_doc = Document(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "embedding": embedding
                    }
                )
                embedded_docs.append(embedded_doc)
            else:
                logger.warning(
                    f"Skipping document due to embedding failure: "
                    f"{doc.metadata.get('article_id')}"
                )
        
        logger.info(
            f"Successfully embedded {len(embedded_docs)}/{len(documents)} documents"
        )
        
        return embedded_docs
    
    def get_embedding_dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION
    
    # def estimate_cost(self, num_tokens: int) -> float:
    #     cost_per_1m_tokens = 0.020
    #     estimated_cost = (num_tokens / 1_000_000) * cost_per_1m_tokens
    #     return estimated_cost

    
    