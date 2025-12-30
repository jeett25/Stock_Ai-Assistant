export const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  export const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };
  export const formatPercent = (value) => {
    if (value === null || value === undefined) return 'N/A';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };
  export const formatPrice = (price) => {
    if (price === null || price === undefined) return 'N/A';
    return `$${parseFloat(price).toFixed(2)}`;
  };
  
  export const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    if (num >= 1000000000) return `${(num / 1000000000).toFixed(2)}B`;
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
    return num.toString();
  };

  export const getSignalColor = (signal) => {
    const colors = {
      'STRONG_BUY': 'text-green-700 bg-green-50',
      'BUY': 'text-green-600 bg-green-50',
      'HOLD': 'text-yellow-700 bg-yellow-50',
      'SELL': 'text-red-600 bg-red-50',
      'STRONG_SELL': 'text-red-700 bg-red-50',
    };
    return colors[signal] || 'text-gray-600 bg-gray-50';
  };

  export const getSignalBadge = (signal) => {
    const variants = {
      'STRONG_BUY': 'success',
      'BUY': 'success',
      'HOLD': 'warning',
      'SELL': 'danger',
      'STRONG_SELL': 'danger',
    };
    return variants[signal] || 'default';
  };
  
  export const getSignalEmoji = (signal) => {
    const emojis = {
      'STRONG_BUY': '🚀',
      'BUY': '📈',
      'HOLD': '⏸️',
      'SELL': '📉',
      'STRONG_SELL': '🔻',
    };
    return emojis[signal] || '➖';
  };
  

  export const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };
  

  export const truncate = (text, length = 100) => {
    if (!text) return '';
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
  };
  
  export const extractTicker = (text) => {
    // Match 1-5 uppercase letters that are word-bounded
    const match = text.match(/\b[A-Z]{1,5}\b/);
    return match ? match[0] : null;
  };

  export const isValidTicker = (ticker) => {
    if (!ticker) return false;
    return /^[A-Z]{1,5}$/.test(ticker);
  };
  
  export const areMarketsOpen = () => {
    const now = new Date();
  
    const istTime = new Date(
      now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
    );
  
    const day = istTime.getDay();   // 0 = Sun, 6 = Sat
    const hour = istTime.getHours();
    const minutes = istTime.getMinutes();
  
    // Market closed on Saturday & Sunday
    if (day === 0 || day === 6) return false;
  
    // Market opens at 9:15
    if (hour < 9 || (hour === 9 && minutes < 15)) return false;
  
    // Market closes at 3:30
    if (hour > 15 || (hour === 15 && minutes > 30)) return false;
  
    return true;
  };
  

  export const getMarketStatus = () => {
    return areMarketsOpen() 
      ? { text: 'Market Open', color: 'text-green-600' }
      : { text: 'Market Closed', color: 'text-gray-600' };
  };
  
  export const getIntentLabel = (intent) => {
    const labels = {
      'top_news': 'Latest News',
      'stock_news': 'Stock News',
      'stock_analysis': 'Analysis',
      'price_prediction': 'Prediction',
      'recommendation': 'Recommendation',
      'comparison': 'Comparison',
      'education': 'Educational',
      'general': 'General Query',
    };
    return labels[intent] || intent;
  };
  

  export const getRSIStatus = (rsi) => {
    if (!rsi) return { text: 'N/A', color: 'text-gray-600' };
    if (rsi < 30) return { text: 'Oversold', color: 'text-green-600' };
    if (rsi > 70) return { text: 'Overbought', color: 'text-red-600' };
    return { text: 'Neutral', color: 'text-gray-600' };
  };
  