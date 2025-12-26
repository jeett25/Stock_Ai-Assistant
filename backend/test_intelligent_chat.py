#!/usr/bin/env python
"""
Test script for the intelligent chat routing system.

Run this to see how different queries are classified and routed.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.langchain_engine.query_router import get_query_router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_query_classification():
    """Test the query classification system."""
    
    router = get_query_router()
    
    # Test queries
    test_queries = [
        # Top News
        "What's the latest news?",
        "Show me today's top headlines",
        "Recent market news",
        
        # Stock News
        "Latest news on Apple",
        "What's happening with TSLA?",
        "News about Microsoft",
        
        # Stock Analysis
        "Analyze AAPL stock",
        "Should I buy Tesla?",
        "How is Google performing?",
        "Tell me about Microsoft",
        
        # Recommendations
        "Best stocks to buy",
        "Recommend some stocks",
        "What should I invest in?",
        "Top performers today",
        
        # Price Prediction
        "Will AAPL go up?",
        "Price forecast for Tesla",
        "Where is Microsoft headed?",
        
        # Comparisons
        "Compare Apple and Microsoft",
        "AAPL vs TSLA",
        "Difference between Google and Amazon",
        
        # Indicators
        "What is RSI?",
        "Explain MACD",
        "How to read moving averages?",
        
        # Market Overview
        "How is the market doing?",
        "Overall market sentiment",
        
        # General
        "How does stock market work?",
        "What is a good P/E ratio?",
    ]
    
    print("\n" + "="*80)
    print("QUERY CLASSIFICATION TEST")
    print("="*80 + "\n")
    
    results = {}
    
    for query in test_queries:
        context, handler = router.route_query(query)
        
        # Group by intent
        intent_key = context.intent.value
        if intent_key not in results:
            results[intent_key] = []
        
        results[intent_key].append({
            'query': query,
            'tickers': context.tickers,
            'handler': handler,
            'time_period': context.time_period,
            'indicator': context.indicator
        })
    
    # Print results grouped by intent
    for intent, queries in results.items():
        print(f"\n📌 {intent.upper().replace('_', ' ')}")
        print("-" * 80)
        
        for item in queries:
            print(f"\n  Query: \"{item['query']}\"")
            print(f"  Handler: {item['handler']}")
            
            if item['tickers']:
                print(f"  Tickers: {', '.join(item['tickers'])}")
            if item['time_period']:
                print(f"  Time Period: {item['time_period']}")
            if item['indicator']:
                print(f"  Indicator: {item['indicator']}")
    
    print("\n" + "="*80)
    print(f"✅ Tested {len(test_queries)} queries")
    print(f"✅ Detected {len(results)} different intents")
    print("="*80 + "\n")


def test_ticker_extraction():
    """Test ticker extraction specifically."""
    
    router = get_query_router()
    
    print("\n" + "="*80)
    print("TICKER EXTRACTION TEST")
    print("="*80 + "\n")
    
    test_cases = [
        ("Should I buy Apple?", ["AAPL"]),
        ("Latest news on $TSLA", ["TSLA"]),
        ("Compare Microsoft and Google", ["MSFT", "GOOGL"]),
        ("What about Reliance Industries?", ["RELIANCE"]),
        ("HDFC Bank vs ICICI Bank", ["HDFCBANK", "ICICIBANK"]),
        ("News about Tesla and Amazon", ["TSLA", "AMZN"]),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_tickers in test_cases:
        context = router.classify_intent(query)
        
        # Check if extracted tickers match expected
        if set(context.tickers) == set(expected_tickers):
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"{status}")
        print(f"  Query: \"{query}\"")
        print(f"  Expected: {expected_tickers}")
        print(f"  Got: {context.tickers}")
        print()
    
    print("="*80)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80 + "\n")


def interactive_test():
    """Interactive testing mode."""
    
    router = get_query_router()
    
    print("\n" + "="*80)
    print("INTERACTIVE MODE - Test Your Own Queries")
    print("="*80)
    print("\nType 'quit' to exit\n")
    
    while True:
        try:
            query = input("Enter query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            context, handler = router.route_query(query)
            
            print(f"\n  🎯 Intent: {context.intent.value}")
            print(f"  🔧 Handler: {handler}")
            
            if context.tickers:
                print(f"  📊 Tickers: {', '.join(context.tickers)}")
            if context.time_period:
                print(f"  ⏰ Time Period: {context.time_period}")
            if context.indicator:
                print(f"  📈 Indicator: {context.indicator}")
            if context.keywords:
                print(f"  🔑 Keywords: {', '.join(context.keywords)}")
            
            print(f"  ✨ Confidence: {context.confidence:.2f}\n")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test intelligent chat routing")
    parser.add_argument(
        '--mode',
        choices=['classify', 'ticker', 'interactive', 'all'],
        default='all',
        help='Test mode'
    )
    
    args = parser.parse_args()
    
    if args.mode in ['classify', 'all']:
        test_query_classification()
    
    if args.mode in ['ticker', 'all']:
        test_ticker_extraction()
    
    if args.mode == 'interactive':
        interactive_test()
    
    if args.mode == 'all':
        print("\n💡 Tip: Run with --mode interactive to test your own queries!\n")