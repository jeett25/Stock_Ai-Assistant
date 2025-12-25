import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.news import NewsArticle
from app.rag.retriever import get_retriever
from app.rag.vector_store import VectorStoreManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_document_processing():
    """Test 1: Document processing and chunking."""
    logger.info("="*60)
    logger.info("TEST 1: Document Processing")
    logger.info("="*60)
    
    from app.rag.document_processor import DocumentProcessor
    
    db = SessionLocal()
    try:
        # Get a sample article
        article = db.query(NewsArticle).first()
        
        if not article:
            logger.error("No articles in database. Run data ingestion first.")
            return False
        
        processor = DocumentProcessor()
        chunks = processor.process_article(article)
        
        logger.info(f"✅ Article processed: {article.title[:60]}...")
        logger.info(f"   Generated {len(chunks)} chunks")
        
        if chunks:
            logger.info(f"\n   Sample chunk:")
            logger.info(f"   {chunks[0].page_content[:200]}...")
            logger.info(f"\n   Metadata: {chunks[0].metadata}")
        
        return len(chunks) > 0
        
    finally:
        db.close()


def test_embedding_generation():
    """Test 2: Embedding generation."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Embedding Generation")
    logger.info("="*60)
    
    from app.rag.embeddings import EmbeddingGenerator
    
    try:
        embedder = EmbeddingGenerator()
        
        # Test single embedding
        test_text = "Apple announces quarterly earnings beat expectations"
        embedding = embedder.generate_embedding(test_text)
        
        logger.info(f"✅ Generated embedding")
        logger.info(f"   Text: {test_text}")
        logger.info(f"   Dimension: {len(embedding)}")
        logger.info(f"   Sample values: {embedding[:5]}")
        
        return len(embedding) == embedder.get_embedding_dimension()
        
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
        return False


def test_vector_storage():
    """Test 3: Vector storage and retrieval."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Vector Storage")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        vector_store = VectorStoreManager(db)
        stats = vector_store.get_stats()
        
        logger.info(f"✅ Vector store statistics:")
        logger.info(f"   Total embeddings: {stats['total_embeddings']}")
        logger.info(f"   Articles with embeddings: {stats['articles_with_embeddings']}")
        logger.info(f"   Avg chunks per article: {stats['avg_chunks_per_article']:.1f}")
        
        return stats['total_embeddings'] > 0
        
    finally:
        db.close()


# test_rag_system.py - UPDATED SECTIONS

# Only showing the functions that need changes:

def test_semantic_search():
    """Test 4: Semantic search."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Semantic Search")
    logger.info("="*60)
    
    test_queries = [
        "earnings report",
        "stock price decline",
        "new product announcement"
    ]
    
    try:
        retriever = get_retriever(k=3)
        
        for query in test_queries:
            logger.info(f"\n🔍 Query: '{query}'")
            # CHANGED: Use invoke() instead of get_relevant_documents()
            docs = retriever.invoke(query)
            
            if docs:
                logger.info(f"   Found {len(docs)} relevant documents:")
                for i, doc in enumerate(docs, 1):
                    logger.info(f"\n   [{i}] Similarity: {doc.metadata.get('similarity', 0):.3f}")
                    logger.info(f"       Ticker: {doc.metadata.get('ticker')}")
                    logger.info(f"       Title: {doc.metadata.get('title', '')[:60]}...")
                    logger.info(f"       Content: {doc.page_content[:150]}...")
            else:
                logger.warning(f"   No documents found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ticker_filtered_search():
    """Test 5: Ticker-filtered search."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Ticker-Filtered Search")
    logger.info("="*60)
    
    ticker = "AAPL"
    query = "What is the latest news?"
    
    try:
        retriever = get_retriever(ticker=ticker, k=5)
        # CHANGED: Use invoke() instead of get_relevant_documents()
        docs = retriever.invoke(query)
        
        logger.info(f"🔍 Query: '{query}' (ticker: {ticker})")
        logger.info(f"   Found {len(docs)} documents")
        
        # Verify all results are from correct ticker
        for doc in docs:
            assert doc.metadata.get('ticker') == ticker, "Wrong ticker in results!"
        
        if docs:
            logger.info(f"\n   Top result:")
            logger.info(f"   Title: {docs[0].metadata.get('title')}")
            logger.info(f"   Source: {docs[0].metadata.get('source')}")
            logger.info(f"   Similarity: {docs[0].metadata.get('similarity', 0):.3f}")
            logger.info(f"   Content: {docs[0].page_content[:200]}...")
        
        logger.info(f"✅ Ticker filtering works correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ticker-filtered search failed: {e}")
        return False

def test_complete_pipeline():
    """Test 6: Complete RAG pipeline."""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Complete Pipeline")
    logger.info("="*60)
    
    from app.rag.pipeline import RAGPipeline
    
    db = SessionLocal()
    try:
        # Get an article without embeddings
        from sqlalchemy import and_, not_, exists
        from app.models.news import NewsEmbedding
        
        unprocessed = db.query(NewsArticle).filter(
            not_(exists().where(
                and_(
                    NewsEmbedding.article_id == NewsArticle.id
                )
            ))
        ).first()
        
        if not unprocessed:
            logger.info("✅ All articles already processed")
            return True
        
        logger.info(f"Processing article: {unprocessed.title[:60]}...")
        
        pipeline = RAGPipeline(db)
        success = pipeline.process_article(unprocessed)
        
        if success:
            logger.info("✅ Complete pipeline execution successful")
            logger.info(f"   Article {unprocessed.id} processed and stored")
        else:
            logger.error("❌ Pipeline execution failed")
        
        return success
        
    finally:
        db.close()


def run_all_tests():
    """Run complete RAG test suite."""
    logger.info("\n" + "🧪 "*30)
    logger.info("PHASE 4 - RAG SYSTEM TEST SUITE")
    logger.info("🧪 "*30 + "\n")
    
    results = {
        "Document Processing": test_document_processing(),
        "Embedding Generation": test_embedding_generation(),
        "Vector Storage": test_vector_storage(),
        "Semantic Search": test_semantic_search(),
        "Ticker Filtering": test_ticker_filtered_search(),
        "Complete Pipeline": test_complete_pipeline(),
    }
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Phase 4 is complete.")
        logger.info("\nYou can now:")
        logger.info("  • Search for relevant news using semantic search")
        logger.info("  • Retrieve context for LLM queries")
        logger.info("  • Build the chat interface in Phase 5")
    else:
        logger.info("\n⚠️  Some tests failed. Check logs above.")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test RAG System")
    parser.add_argument(
        '--test',
        choices=['process', 'embed', 'store', 'search', 'filter', 'pipeline', 'all'],
        default='all',
        help='Which test to run'
    )
    
    args = parser.parse_args()
    
    if args.test == 'process':
        test_document_processing()
    elif args.test == 'embed':
        test_embedding_generation()
    elif args.test == 'store':
        test_vector_storage()
    elif args.test == 'search':
        test_semantic_search()
    elif args.test == 'filter':
        test_ticker_filtered_search()
    elif args.test == 'pipeline':
        test_complete_pipeline()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)