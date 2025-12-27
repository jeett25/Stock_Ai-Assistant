from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
import logging
import json

logger = logging.getLogger(__name__)


class TickerExtraction(BaseModel):
    """Structured output for ticker extraction."""
    
    tickers: List[str] = Field(
        description="List of stock ticker symbols mentioned (e.g., ['AAPL', 'MSFT']). Return empty list if none found."
    )
    company_names: List[str] = Field(
        description="Full company names corresponding to tickers (e.g., ['Apple Inc.', 'Microsoft'])"
    )
    has_ticker: bool = Field(
        description="True if query mentions specific stocks, False if general market query"
    )
    is_comparison: bool = Field(
        description="True if query asks to compare multiple stocks"
    )
    query_type: str = Field(
        description="Type: 'stock_specific', 'general_market', 'comparison', or 'unclear'"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "tickers": ["AAPL", "MSFT"],
                "company_names": ["Apple Inc.", "Microsoft Corporation"],
                "has_ticker": True,
                "is_comparison": True,
                "query_type": "comparison"
            }
        }


class LLMTickerExtractor:
    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=TickerExtraction)
    
    def extract_tickers(self, query: str) -> TickerExtraction:
        try:
            # Create prompt for LLM
            prompt = self._create_extraction_prompt(query)
            
            # Call LLM
            logger.info(f"🤖 Using LLM to extract tickers from: '{query[:60]}...'")
            response = self.llm.invoke(prompt)
            
            # Parse response
            extraction = self._parse_llm_response(response.content)
            
            logger.info(
                f"✅ Extracted: {extraction.tickers} "
                f"(type: {extraction.query_type})"
            )
            
            return extraction
            
        except Exception as e:
            logger.error(f"Error in LLM ticker extraction: {e}")
            # Fallback to empty extraction
            return TickerExtraction(
                tickers=[],
                company_names=[],
                has_ticker=False,
                is_comparison=False,
                query_type="unclear"
            )
    
    def _create_extraction_prompt(self, query: str) -> str:
        """Create prompt for ticker extraction."""
        
        prompt = f"""You are a stock market expert. Extract ticker symbols from the user's query.

**Important Guidelines:**

1. **Indian Stocks (NSE)**: Use Indian ticker format
   - Reliance → RELIANCE
   - Tata Consultancy → TCS
   - Infosys → INFY
   - HDFC Bank → HDFCBANK
   - State Bank of India → SBIN
   - Larsen & Toubro / L&T → LT
   - EIH Hotel / EIH → EIHOTEL
   - Asian Paints → ASIANPAINT
   - Maruti Suzuki → MARUTI
   - Tata Motors → TATAMOTORS
   - Bharti Airtel / Airtel → BHARTIARTL
   - ITC → ITC
   - Axis Bank → AXISBANK
   - Kotak Bank → KOTAKBANK
   - Bajaj Finance → BAJFINANCE
   - Wipro → WIPRO
   - HCL Tech → HCLTECH
   - Sun Pharma → SUNPHARMA
   - Dr. Reddy's → DRREDDY
   - Cipla → CIPLA
   - Adani Beverages → ABDL
   - Any uppercase word that looks like a ticker → Use as-is

2. **US Stocks**: Use standard US tickers
   - Apple → AAPL
   - Microsoft → MSFT
   - Google / Alphabet → GOOGL
   - Amazon → AMZN
   - Tesla → TSLA
   - Meta / Facebook → META
   - Nvidia → NVDA

3. **If ticker is already mentioned**: Use it EXACTLY as-is (e.g., "ABDL" → ABDL, "EIHOTEL" → EIHOTEL)

4. **General queries**: If asking about "the market" or "stocks" in general → has_ticker=false, empty tickers list

5. **Comparison queries**: If comparing multiple stocks → is_comparison=true

**User Query**: "{query}"

**Response Format**: Return ONLY a JSON object with these exact fields:
{{
  "tickers": ["TICKER1", "TICKER2"],
  "company_names": ["Company Name 1", "Company Name 2"],
  "has_ticker": true,
  "is_comparison": false,
  "query_type": "stock_specific"
}}

**Examples**:

Query: "What's analysis on ABDL?"
Response: {{"tickers": ["ABDL"], "company_names": ["Adani Beverages"], "has_ticker": true, "is_comparison": false, "query_type": "stock_specific"}}

Query: "Tell me about LT"
Response: {{"tickers": ["LT"], "company_names": ["Larsen & Toubro"], "has_ticker": true, "is_comparison": false, "query_type": "stock_specific"}}

Query: "Compare Apple and Microsoft"
Response: {{"tickers": ["AAPL", "MSFT"], "company_names": ["Apple Inc.", "Microsoft"], "has_ticker": true, "is_comparison": true, "query_type": "comparison"}}

Query: "What's the latest news?"
Response: {{"tickers": [], "company_names": [], "has_ticker": false, "is_comparison": false, "query_type": "general_market"}}

CRITICAL: Respond ONLY with the JSON object. No markdown code blocks, no explanations, just the raw JSON.
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> TickerExtraction:
        """Parse LLM response to TickerExtraction object."""
        try:
            # Clean the response
            response_clean = response.strip()
            
            # Remove markdown code blocks if present
            if "```json" in response_clean:
                response_clean = response_clean.split("```json")[1].split("```")[0]
            elif "```" in response_clean:
                response_clean = response_clean.split("```")[1].split("```")[0]
            
            # Remove any leading/trailing whitespace
            response_clean = response_clean.strip()
            
            # Parse JSON
            data = json.loads(response_clean)
            
            # Check if it's the schema itself (contains 'properties', 'example', etc.)
            if 'properties' in data or 'example' in data:
                logger.warning("LLM returned schema instead of extraction, using example data")
                # Try to extract from example if present
                if 'example' in data:
                    data = data['example']
                else:
                    # Return empty extraction
                    return TickerExtraction(
                        tickers=[],
                        company_names=[],
                        has_ticker=False,
                        is_comparison=False,
                        query_type="unclear"
                    )
            
            # Validate required fields exist
            required_fields = ['tickers', 'company_names', 'has_ticker', 'is_comparison', 'query_type']
            if not all(field in data for field in required_fields):
                logger.warning(f"Missing required fields in response: {data}")
                # Fill in missing fields with defaults
                data.setdefault('tickers', [])
                data.setdefault('company_names', [])
                data.setdefault('has_ticker', False)
                data.setdefault('is_comparison', False)
                data.setdefault('query_type', 'unclear')
            
            return TickerExtraction(**data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {response[:200]}")
            # Return empty extraction
            return TickerExtraction(
                tickers=[],
                company_names=[],
                has_ticker=False,
                is_comparison=False,
                query_type="unclear"
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return TickerExtraction(
                tickers=[],
                company_names=[],
                has_ticker=False,
                is_comparison=False,
                query_type="unclear"
            )


class HybridTickerExtractor:
    def __init__(self, llm, regex_extractor_func):
        """
        Args:
            llm: LangChain LLM instance
            regex_extractor_func: Function that does regex-based extraction
                                  (e.g., QueryRouter._extract_tickers)
        """
        self.llm_extractor = LLMTickerExtractor(llm)
        self.regex_extractor = regex_extractor_func
    
    def extract_tickers(
        self, 
        query: str, 
        use_llm: bool = True
    ) -> Dict:
        result = {
            'tickers': [],
            'company_names': [],
            'has_ticker': False,
            'is_comparison': False,
            'query_type': 'unclear',
            'extraction_method': 'none'
        }
        
        # Method 1: LLM extraction (preferred)
        if use_llm:
            try:
                llm_result = self.llm_extractor.extract_tickers(query)
                
                if llm_result.has_ticker and llm_result.tickers:
                    result['tickers'] = llm_result.tickers
                    result['company_names'] = llm_result.company_names
                    result['has_ticker'] = llm_result.has_ticker
                    result['is_comparison'] = llm_result.is_comparison
                    result['query_type'] = llm_result.query_type
                    result['extraction_method'] = 'llm'
                    
                    logger.info(f"✅ LLM extraction successful: {result['tickers']}")
                    return result
                    
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to regex: {e}")
        
        # Method 2: Regex fallback
        try:
            regex_tickers = self.regex_extractor(query)
            
            if regex_tickers:
                result['tickers'] = regex_tickers
                result['has_ticker'] = True
                result['query_type'] = 'stock_specific'
                result['is_comparison'] = len(regex_tickers) > 1
                result['extraction_method'] = 'regex'
                
                logger.info(f"✅ Regex extraction successful: {result['tickers']}")
            else:
                logger.info("ℹ️ No tickers found")
                
        except Exception as e:
            logger.error(f"Regex extraction also failed: {e}")
        
        return result

def create_ticker_extractor(llm):
    return LLMTickerExtractor(llm)


def extract_tickers_with_llm(query: str, llm) -> TickerExtraction:
    extractor = LLMTickerExtractor(llm)
    return extractor.extract_tickers(query)