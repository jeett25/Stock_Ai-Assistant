from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_core.prompts.chat import SystemMessagePromptTemplate , HumanMessagePromptTemplate
from typing import List , Dict

SYSTEM_PROMPT = """You are a stock market analysis assistant. Your role is to provide educational , informative analysis based on REAL DATA provided to you.

**CRITICAL RULES:**
1. **Base ALL responses on the provided context** (news articles, technical indicators, analysis)
2. **If information is not in the context, explicitly say "I don't have information about that"**
3. **NEVER invent stock prices, news, or data**
4. **Always include the disclaimer at the end of every response**
5. **Explain technical terms in simple language**
6. **Discuss both risks and opportunities**
7. **Be objective - don't push any particular investment decision**

**What you can do:**
- Analyze trends based on provided news
- Explain technical indicators(RSI , MACD , etc.)
- Discuss What signals mean 
- Compare different time frames 
- Answer questions about market concepts
- Suggest Future Prices based on analysis and news only.
- Recommend specific buy/sell actions

**What you cannot do:**
- Guarantee returns 
- Replace professional financial advice
- Access real-time prices (unless provided in context)

**Response Style:**
- Clear and concise
- Use bullet points for multiple points
- Cite sources when referencing news (e.g., "According to Yahoo Finance...")
- Acknowledge uncertainty
- Use educational tone

**MANDATORY DISCLAIMER (include at end of EVERY response):**
⚠️ **Disclaimer**: This is educational information only, not financial advice. Stock markets are risky. Past performance doesn't guarantee future results. Always do your own research and consult a licensed financial advisor before making investment decisions.
"""

def create_chat_prompt_template() -> ChatPromptTemplate:
    
    system_message = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT)
    context_template = """**CONTEXT PROVIDED TO YOU:**

**Technical Analysis for {ticker}:**
- **Signal**: {signal} (Confidence: {confidence})
- **RSI**: {rsi} {rsi_interpretation}
- **MACD**: {macd_interpretation}
- **Price vs Moving Averages**: {ma_interpretation}
- **Key Reasons**: {reasons}

**Recent News Articles:**
{news_context}

**Current Date**: {current_date}

---

Now answer the user's question based ONLY on the above context. If the information isn't available, say so clearly."""
    
    context_message = HumanMessagePromptTemplate.from_template(context_template)
    
    # User query template
    user_template = """**User Question**: {query}"""
    user_message = HumanMessagePromptTemplate.from_template(user_template)
    
    prompt = ChatPromptTemplate.from_messages([
        system_message,
        context_message,
        user_message
    ])
    
    return prompt


def create_conversation_prompt_template()-> ChatPromptTemplate:
    system_message = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT)
    
    # Context template
    context_template = """**CONTEXT PROVIDED TO YOU:**

                        **Technical Analysis for {ticker}:**
                        - **Signal**: {signal} (Confidence: {confidence})
                        - **RSI**: {rsi} {rsi_interpretation}
                        - **Key Reasons**: {reasons}

                        **Recent News:**
                        {news_context}

                        **Current Date**: {current_date}
                        """
    
    context_message = HumanMessagePromptTemplate.from_template(context_template)
    
    history_placeholder = MessagesPlaceholder(variable_name="chat_history")
    
    # Current user query
    user_template = """**User Question**: {query}"""
    user_message = HumanMessagePromptTemplate.from_template(user_template)
    
    prompt = ChatPromptTemplate.from_messages([
        system_message,
        context_message,
        history_placeholder,
        user_message
    ])
    
    return prompt

def format_news_context(news_documents : List[Dict]) -> str:
    if not news_documents:
        return "No recent news articles available."
    
    formatted = []
    for i, doc in enumerate(news_documents, 1):
        metadata = doc.get('extra_metadata', {})
        content = doc.get('page_content', '')
    
        formatted.append(
            f"[{i}] **{metadata.get('title', 'Untitled')}**\n"
            f"   Source: {metadata.get('source', 'Unknown')}\n"
            f"   Published: {metadata.get('published_at', 'Unknown')}\n"
            f"   URL: {metadata.get('url', '')}\n"
            f"   Content: {content[:300]}...\n"
        )
    
    return "\n".join(formatted)


def format_analysis_context(analysis: Dict)-> Dict:
    rsi = analysis.get('rsi')
    if rsi:
        if rsi < 30:
            rsi_interpretation = "(Oversold - potential buy zone)"
        elif rsi > 70:
            rsi_interpretation = "(Overbought - potential sell zone)"
        else:
            rsi_interpretation = "(Neutral range)"
    else:
        rsi_interpretation = "(Not available)"
    
    macd_histogram = analysis.get('macd_histogram')
    if macd_histogram:
        if macd_histogram > 0:
            macd_interpretation = "Bullish crossover (MACD above signal line)"
        else:
            macd_interpretation = "Bearish crossover (MACD below signal line)"
    else:
        macd_interpretation = "Not available"
    
    sma_20 = analysis.get('sma_20')
    close_price = analysis.get('indicators', {}).get('close_price')
    
    if sma_20 and close_price:
        if close_price > sma_20:
            ma_interpretation = f"Price (${close_price:.2f}) is above 20-day SMA (${sma_20:.2f}) - Short-term bullish"
        else:
            ma_interpretation = f"Price (${close_price:.2f}) is below 20-day SMA (${sma_20:.2f}) - Short-term bearish"
    else:
        ma_interpretation = "Not available"
    
    return {
        'signal': analysis.get('signal', 'UNKNOWN'),
        'confidence': f"{analysis.get('confidence', 0):.0%}",
        'rsi': f"{rsi:.1f}" if rsi else "N/A",
        'rsi_interpretation': rsi_interpretation,
        'macd_interpretation': macd_interpretation,
        'ma_interpretation': ma_interpretation,
        'reasons': ', '.join(analysis.get('reasons', ['No specific reasons'])[:3])
    }


EXPLAIN_INDICATOR_PROMPT = """Explain the following technical indicator in simple terms:

Indicator: {indicator_name}
Current Value: {current_value}
Interpretation: {interpretation}

Keep your explanation:
- Simple (no jargon)
- Under 100 words
- Focused on what it means for traders
"""

COMPARE_TICKERS_PROMPT = """Compare these two stocks based on the provided data:

**Stock 1: {ticker1}**
{analysis1}

**Stock 2: {ticker2}**
{analysis2}

Provide a brief comparison focusing on:
1. Signal strength
2. Risk factors
3. Key differences

Keep it objective and under 150 words.
"""