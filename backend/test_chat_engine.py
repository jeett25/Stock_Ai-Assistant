"""
Test script for chat engine.
Tests all chat functionality including context retrieval, ticker extraction, and response quality.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import requests
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


def test_basic_chat():
    """Test 1: Basic chat functionality."""
    logger.info("="*60)
    logger.info("TEST 1: Basic Chat")
    logger.info("="*60)
    
    test_queries = [
        {"query": "What is the latest news about AAPL?", "ticker": "AAPL"},
        {"query": "Should I buy Microsoft stock?", "ticker": "MSFT"},
        {"query": "Tell me about GOOGL's technical indicators", "ticker": "GOOGL"},
    ]
    
    success = True
    
    for i, test_case in enumerate(test_queries, 1):
        logger.info(f"\n[Test {i}] Query: {test_case['query']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json=test_case,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Response generated successfully")
                logger.info(f"   Ticker: {data.get('ticker', 'None')}")
                logger.info(f"   Signal: {data.get('signal', 'None')}")
                logger.info(f"   Confidence: {data.get('confidence', 'None')}")
                logger.info(f"   Context retrieved: {data.get('context_retrieved', False)}")
                logger.info(f"   Sources: {len(data.get('sources', []))}")
                logger.info(f"\n   Response preview:")
                response_text = data.get('response', '')
                logger.info(f"   {response_text[:300]}...")
                
                # Check for disclaimer
                if "Disclaimer" in response_text or "⚠️" in response_text:
                    logger.info("   ✅ Disclaimer present")
                else:
                    logger.warning("   ⚠️  Disclaimer missing!")
                    
            else:
                logger.error(f"❌ Request failed: {response.status_code}")
                logger.error(f"   {response.text}")
                success = False
                
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            success = False
    
    return success


def test_ticker_extraction():
    """Test 2: Automatic ticker extraction."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Ticker Extraction")
    logger.info("="*60)
    
    test_cases = [
        {"query": "What's happening with Apple stock?", "expected": "AAPL"},
        {"query": "Tell me about $TSLA", "expected": "TSLA"},
        {"query": "How is Microsoft performing?", "expected": "MSFT"},
        {"query": "Is NVDA a good buy?", "expected": "NVDA"},
        {"query": "Should I invest in Amazon?", "expected": "AMZN"},
    ]
    
    success_count = 0
    
    for test_case in test_cases:
        query = test_case['query']
        expected = test_case['expected']
        
        logger.info(f"\n🔍 Query: {query}")
        logger.info(f"   Expected ticker: {expected}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"query": query},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                extracted = data.get('ticker')
                
                if extracted == expected:
                    logger.info(f"   ✅ Correctly extracted: {extracted}")
                    success_count += 1
                else:
                    logger.warning(f"   ⚠️  Extracted: {extracted} (expected: {expected})")
            else:
                logger.error(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
    
    logger.info(f"\n📊 Extraction success rate: {success_count}/{len(test_cases)}")
    return success_count >= len(test_cases) * 0.8  # 80% success threshold


def test_context_retrieval():
    """Test 3: Context retrieval quality."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Context Retrieval")
    logger.info("="*60)
    
    query = "What are analysts saying about AAPL earnings?"
    ticker = "AAPL"
    
    logger.info(f"Query: {query}")
    logger.info(f"Ticker: {ticker}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"query": query, "ticker": ticker},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            logger.info(f"\n✅ Context Retrieved Successfully:")
            logger.info(f"   Number of sources: {len(data.get('sources', []))}")
            logger.info(f"   Context retrieved: {data.get('context_retrieved', False)}")
            
            # Show sources
            sources = data.get('sources', [])
            if sources:
                logger.info(f"\n   Top news sources:")
                for i, source in enumerate(sources[:3], 1):
                    logger.info(f"\n   [{i}] {source.get('title', 'Untitled')[:60]}...")
                    logger.info(f"       Source: {source.get('source', 'Unknown')}")
                    logger.info(f"       Published: {source.get('published_at', 'Unknown')}")
                    logger.info(f"       Similarity: {source.get('similarity', 0):.3f}")
            else:
                logger.warning("   ⚠️  No sources retrieved")
            
            # Show technical analysis
            logger.info(f"\n   Technical Analysis:")
            logger.info(f"   Signal: {data.get('signal', 'None')}")
            logger.info(f"   Confidence: {data.get('confidence', 'None')}")
            
            # Check if response uses context
            response_text = data.get('response', '')
            context_indicators = ['according to', 'based on', 'the analysis shows', 'recent news']
            uses_context = any(indicator in response_text.lower() for indicator in context_indicators)
            
            if uses_context:
                logger.info("\n   ✅ Response appears to use retrieved context")
            else:
                logger.warning("\n   ⚠️  Response may not be using context effectively")
            
            logger.info(f"\n   Response preview:")
            logger.info(f"   {response_text[:400]}...")
            
            return True
                
        else:
            logger.error(f"❌ Failed: {response.status_code}")
            logger.error(f"   {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test 4: Edge cases and error handling."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Edge Cases")
    logger.info("="*60)
    
    edge_cases = [
        {
            "name": "No ticker provided",
            "query": "What's the stock market doing today?",
            "should_fail": False
        },
        {
            "name": "Invalid ticker",
            "query": "Tell me about XYZ123",
            "ticker": "XYZ123",
            "should_fail": False  # Should return "no data" message
        },
        {
            "name": "Very short query",
            "query": "Buy?",
            "ticker": "AAPL",
            "should_fail": False
        },
        {
            "name": "Ambiguous query",
            "query": "Is it good?",
            "should_fail": False
        },
    ]
    
    success_count = 0
    
    for test_case in edge_cases:
        logger.info(f"\n🧪 Test: {test_case['name']}")
        logger.info(f"   Query: {test_case['query']}")
        
        payload = {"query": test_case['query']}
        if 'ticker' in test_case:
            payload['ticker'] = test_case['ticker']
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                # Check if response is reasonable
                if len(response_text) > 50:  # Has substantial content
                    logger.info(f"   ✅ Handled gracefully")
                    logger.info(f"   Response: {response_text[:150]}...")
                    success_count += 1
                else:
                    logger.warning(f"   ⚠️  Response too short: {response_text}")
            else:
                if test_case['should_fail']:
                    logger.info(f"   ✅ Failed as expected: {response.status_code}")
                    success_count += 1
                else:
                    logger.error(f"   ❌ Unexpected failure: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
    
    logger.info(f"\n📊 Edge case handling: {success_count}/{len(edge_cases)}")
    return success_count >= len(edge_cases) * 0.75


def test_explain_endpoint():
    """Test 5: Explain indicator endpoint."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Explain Indicator Endpoint")
    logger.info("="*60)
    
    indicators = ["RSI", "MACD", "SMA"]
    ticker = "AAPL"
    
    success = True
    
    for indicator in indicators:
        logger.info(f"\n📊 Explaining {indicator} for {ticker}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/explain",
                json={"indicator": indicator, "ticker": ticker},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                explanation = data.get('explanation', '')
                
                logger.info(f"   ✅ Explanation generated")
                logger.info(f"   Length: {len(explanation)} characters")
                logger.info(f"   Preview: {explanation[:200]}...")
            else:
                logger.error(f"   ❌ Failed: {response.status_code}")
                success = False
                
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            success = False
    
    return success


def test_suggestions_endpoint():
    """Test 6: Query suggestions endpoint."""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Query Suggestions")
    logger.info("="*60)
    
    ticker = "AAPL"
    
    logger.info(f"Getting suggestions for {ticker}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/chat/suggestions/{ticker}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestions', [])
            
            logger.info(f"✅ Retrieved {len(suggestions)} suggestions:")
            for i, suggestion in enumerate(suggestions[:5], 1):
                logger.info(f"   {i}. {suggestion}")
            
            return len(suggestions) > 0
        else:
            logger.error(f"❌ Failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def test_response_quality():
    """Test 7: Response quality checks."""
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Response Quality")
    logger.info("="*60)
    
    query = "Should I buy AAPL stock right now?"
    ticker = "AAPL"
    
    logger.info(f"Query: {query}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"query": query, "ticker": ticker},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            
            checks = {
                "Has disclaimer": "⚠️" in response_text or "Disclaimer" in response_text,
                "Mentions data source": any(word in response_text.lower() for word in ['analysis', 'data', 'indicator', 'news']),
                "Discusses risks": any(word in response_text.lower() for word in ['risk', 'volatile', 'caution', 'uncertain']),
                "Avoids guarantees": not any(word in response_text.lower() for word in ['guarantee', 'definitely', 'certainly will', 'sure to']),
                "Reasonable length": 100 < len(response_text) < 2000,
                "Professional tone": not any(word in response_text.lower() for word in ['dump', 'moon', 'lambo']),
            }
            
            logger.info(f"\n✅ Response Quality Checks:")
            passed = 0
            for check, result in checks.items():
                status = "✅" if result else "❌"
                logger.info(f"   {status} {check}")
                if result:
                    passed += 1
            
            logger.info(f"\n   Score: {passed}/{len(checks)} ({passed/len(checks)*100:.0f}%)")
            
            if passed >= len(checks) * 0.8:
                logger.info(f"   ✅ Quality threshold met")
                return True
            else:
                logger.warning(f"   ⚠️  Quality below threshold")
                return False
                
        else:
            logger.error(f"❌ Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def run_all_tests():
    """Run complete Phase 5 test suite."""
    logger.info("\n" + "🧪 "*30)
    logger.info("PHASE 5 - CHAT ENGINE TEST SUITE")
    logger.info("🧪 "*30 + "\n")
    
    results = {
        "Basic Chat": test_basic_chat(),
        "Ticker Extraction": test_ticker_extraction(),
        "Context Retrieval": test_context_retrieval(),
        "Edge Cases": test_edge_cases(),
        "Explain Endpoint": test_explain_endpoint(),
        "Suggestions": test_suggestions_endpoint(),
        "Response Quality": test_response_quality(),
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
    
    logger.info(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Phase 5 is complete.")
        logger.info("\nThe chat engine is ready to:")
        logger.info("  • Answer questions about stocks")
        logger.info("  • Provide context-aware analysis")
        logger.info("  • Explain technical indicators")
        logger.info("  • Compare different stocks")
        logger.info("\nNext: Build the frontend in Phase 6!")
    else:
        logger.info(f"\n⚠️  {total - passed} test(s) failed. Review logs above.")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Chat Engine")
    parser.add_argument(
        '--test',
        choices=['basic', 'extract', 'context', 'edge', 'explain', 'suggestions', 'quality', 'all'],
        default='all',
        help='Which test to run'
    )
    
    args = parser.parse_args()
    
    if args.test == 'basic':
        test_basic_chat()
    elif args.test == 'extract':
        test_ticker_extraction()
    elif args.test == 'context':
        test_context_retrieval()
    elif args.test == 'edge':
        test_edge_cases()
    elif args.test == 'explain':
        test_explain_endpoint()
    elif args.test == 'suggestions':
        test_suggestions_endpoint()
    elif args.test == 'quality':
        test_response_quality()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)