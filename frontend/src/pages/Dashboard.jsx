import { useEffect, useState } from 'react';
import { getDashboardOverview, getTickerNews, getLatestPrice } from '../services/api';
import { StockCard } from '../components/dashboard/StockCard';
import { AnalysisSummary } from '../components/dashboard/AnalysisSummary';
import { NewsList } from '../components/dashboard/NewsList';
import { Loader } from '../components/common/Loader';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Disclaimer } from '../components/common/Disclaimer';
import { RefreshCw, Filter } from 'lucide-react';

export const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [prices, setPrices] = useState({});
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [signalFilter, setSignalFilter] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch dashboard overview with optional signal filter
      const overviewData = await getDashboardOverview(10, signalFilter);
      setDashboardData(overviewData);

      // Fetch prices for each ticker
      if (overviewData.analyses && overviewData.analyses.length > 0) {
        const pricePromises = overviewData.analyses.map(async (analysis) => {
          try {
            const priceData = await getLatestPrice(analysis.ticker);
            return { ticker: analysis.ticker, price: priceData };
          } catch (err) {
            console.error(`Error fetching price for ${analysis.ticker}:`, err);
            return { ticker: analysis.ticker, price: null };
          }
        });

        const priceResults = await Promise.all(pricePromises);
        const pricesMap = {};
        priceResults.forEach(({ ticker, price }) => {
          pricesMap[ticker] = price;
        });
        setPrices(pricesMap);

        // Fetch recent news (from first ticker)
        const firstTicker = overviewData.analyses[0].ticker;
        try {
          const newsData = await getTickerNews(firstTicker, 5, 30);
          setNews(newsData);
        } catch (err) {
          console.error('Error fetching news:', err);
          setNews([]);
        }
      }

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [signalFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader size="large" text="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorMessage message={error} />
        <button
          onClick={fetchDashboardData}
          className="btn-primary mt-4 mx-auto flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Overview of analyzed stocks and market trends
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Signal Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-600" />
            <select
              value={signalFilter || ''}
              onChange={(e) => setSignalFilter(e.target.value || null)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white"
            >
              <option value="">All Signals</option>
              <option value="STRONG_BUY">Strong Buy</option>
              <option value="BUY">Buy</option>
              <option value="HOLD">Hold</option>
              <option value="SELL">Sell</option>
              <option value="STRONG_SELL">Strong Sell</option>
            </select>
          </div>
          
          <button
            onClick={fetchDashboardData}
            className="btn-secondary flex items-center gap-2"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Stock Cards */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stock Cards Section */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Analyzed Stocks
              {signalFilter && (
                <span className="ml-2 text-sm font-normal text-gray-600">
                  (Filtered: {signalFilter.replace('_', ' ')})
                </span>
              )}
            </h2>
            
            {dashboardData?.analyses && dashboardData.analyses.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {dashboardData.analyses.map((analysis) => (
                  <StockCard
                    key={analysis.ticker}
                    ticker={analysis.ticker}
                    analysis={analysis}
                    price={prices[analysis.ticker]}
                  />
                ))}
              </div>
            ) : (
              <div className="card p-8 text-center">
                <p className="text-gray-600 mb-2">
                  {signalFilter 
                    ? `No stocks with ${signalFilter.replace('_', ' ')} signal found.`
                    : 'No stock analysis available yet.'
                  }
                </p>
                <p className="text-sm text-gray-500">
                  {signalFilter
                    ? 'Try a different filter or refresh the data.'
                    : 'Run the analysis job to see data here.'
                  }
                </p>
              </div>
            )}
          </div>

          {/* News Section */}
          {news.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Recent News
              </h2>
              <NewsList news={news} />
            </div>
          )}
        </div>

        {/* Right Column - Summary & Disclaimer */}
        <div className="lg:col-span-1 space-y-6">
          {/* Summary Section */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Market Summary
            </h2>
            <AnalysisSummary data={dashboardData} />
          </div>

          {/* Disclaimer */}
          <Disclaimer />
        </div>
      </div>
    </div>
  );
};
