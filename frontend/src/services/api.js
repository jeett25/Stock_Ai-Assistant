import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});


apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);


apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);


export const healthCheck = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const databaseHealthCheck = async () => {
  const response = await apiClient.get('/health/db');
  return response.data;
};


/**
 * Main intelligent chat endpoint - auto-detects intent
 * @param {string} query - User's question
 * @param {string|null} ticker - Optional ticker (will be auto-detected if not provided)
 * @param {Array} chatHistory - Optional conversation history
 * @param {boolean} structured - Return structured output
 */
export const sendChatMessage = async (query, ticker = null, chatHistory = null, structured = false) => {
  const response = await apiClient.post('/chat', {
    query,
    ticker,
    chat_history: chatHistory,
    structured,
  });
  return response.data;
};

/**
 * Dedicated endpoint for structured stock analysis
 * @param {string} ticker - Stock ticker
 * @param {boolean} includeNews - Include news sentiment
 */
export const analyzeStock = async (ticker, includeNews = true) => {
  const response = await apiClient.post('/chat/analyze', {
    ticker,
    include_news: includeNews,
  });
  return response.data;
};


export const getQuerySuggestions = async () => {
  const response = await apiClient.get('/chat/suggestions');
  return response.data;
};


export const chatHealthCheck = async () => {
  const response = await apiClient.get('/chat/health');
  return response.data;
};


/**
 * Get latest analysis for a ticker
 * @param {string} ticker - Stock ticker
 */
export const getTickerAnalysis = async (ticker) => {
  const response = await apiClient.get(`/analysis/${ticker}`);
  return response.data;
};

/**
 * Get analysis history for a ticker
 * @param {string} ticker - Stock ticker
 * @param {number} days - Number of days of history (1-365)
 */
export const getTickerAnalysisHistory = async (ticker, days = 30) => {
  const response = await apiClient.get(`/analysis/${ticker}/history?days=${days}`);
  return response.data;
};

/**
 * Get simplified summary for a ticker
 * @param {string} ticker - Stock ticker
 */
export const getTickerSummary = async (ticker) => {
  const response = await apiClient.get(`/analysis/${ticker}/summary`);
  return response.data;
};

/**
 * Get dashboard overview with multiple stocks
 * @param {number} limit - Number of analyses to return (1-50)
 * @param {string|null} signalFilter - Filter by signal (BUY/SELL/HOLD)
 */
export const getDashboardOverview = async (limit = 10, signalFilter = null) => {
  let url = `/analysis/dashboard/overview?limit=${limit}`;
  if (signalFilter) {
    url += `&signal_filter=${signalFilter}`;
  }
  const response = await apiClient.get(url);
  return response.data;
};


export const getIndicatorsExplanation = async () => {
  const response = await apiClient.get('/analysis/indicators/explanation');
  return response.data;
};


/**
 * Get news articles for a ticker
 * @param {string} ticker - Stock ticker
 * @param {number} limit - Number of articles (1-50)
 * @param {number} days - Filter articles from last N days (1-365)
 */
export const getTickerNews = async (ticker, limit = 10, days = 30) => {
  const response = await apiClient.get(`/news/${ticker}?limit=${limit}&days=${days}`);
  return response.data;
};

/**
 * Get news sources breakdown for a ticker
 * @param {string} ticker - Stock ticker
 * @param {number} days - Analysis period in days (1-365)
 */
export const getNewsSources = async (ticker, days = 30) => {
  const response = await apiClient.get(`/news/${ticker}/sources?days=${days}`);
  return response.data;
};

/**
 * Search news articles by keyword
 * @param {string} query - Search query (min 3 characters)
 * @param {number} limit - Number of results (1-50)
 */
export const searchNews = async (query, limit = 10) => {
  const response = await apiClient.get(`/news/search/?q=${encodeURIComponent(query)}&limit=${limit}`);
  return response.data;
};


/**
 * Get historical prices for a ticker
 * @param {string} ticker - Stock ticker
 * @param {number} days - Number of trading days (1-365)
 */
export const getTickerPrices = async (ticker, days = 30) => {
  const response = await apiClient.get(`/prices/${ticker}?days=${days}`);
  return response.data;
};

/**
 * Get latest price with change information
 * @param {string} ticker - Stock ticker
 */
export const getLatestPrice = async (ticker) => {
  const response = await apiClient.get(`/prices/${ticker}/latest`);
  return response.data;
};

/**
 * Get price data for a specific date range
 * @param {string} ticker - Stock ticker
 * @param {string} startDate - Start date (YYYY-MM-DD)
 * @param {string} endDate - End date (YYYY-MM-DD)
 */
export const getPriceRange = async (ticker, startDate, endDate) => {
  const response = await apiClient.get(
    `/prices/${ticker}/range?start_date=${startDate}&end_date=${endDate}`
  );
  return response.data;
};

export const getAvailableTickers = async () => {
  const response = await apiClient.get('/prices/tickers/available');
  return response.data;
};


/**
 * Trigger data ingestion for a single ticker
 * @param {string} ticker - Stock ticker
 */
export const triggerIngestion = async (ticker) => {
  const response = await apiClient.post(`/ingest/${ticker}`);
  return response.data;
};

/**
 * Trigger batch ingestion for multiple tickers
 * @param {Array<string>} tickers - Array of stock tickers (max 10)
 */
export const triggerBatchIngestion = async (tickers) => {
  const response = await apiClient.post('/ingest/batch', tickers);
  return response.data;
};


export default apiClient;