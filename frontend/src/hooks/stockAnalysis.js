import { useState, useEffect } from 'react';
import { getTickerAnalysis, getTickerSummary } from '../services/api';

export const useStockAnalysis = (ticker) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) return;

    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTickerAnalysis(ticker);
        setAnalysis(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [ticker]);

  return { analysis, loading, error };
};
