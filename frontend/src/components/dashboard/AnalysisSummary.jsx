import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { formatDate } from '../../utils/helpers';

export const AnalysisSummary = ({ data }) => {
  if (!data) return null;

  const signals = data.signal_distribution || {};
  const total = data.count || 0;

  const signalConfig = {
    'STRONG_BUY': { label: 'Strong Buy', color: 'bg-green-600', icon: TrendingUp },
    'BUY': { label: 'Buy', color: 'bg-green-500', icon: TrendingUp },
    'HOLD': { label: 'Hold', color: 'bg-yellow-500', icon: Minus },
    'SELL': { label: 'Sell', color: 'bg-red-500', icon: TrendingDown },
    'STRONG_SELL': { label: 'Strong Sell', color: 'bg-red-600', icon: TrendingDown },
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">
          Market Overview
        </h3>
      </div>

      {total > 0 ? (
        <>
          {/* Signal Distribution */}
          <div className="space-y-3 mb-4">
            {Object.entries(signalConfig).map(([signal, config]) => {
              const count = signals[signal] || 0;
              if (count === 0) return null;
              
              const percentage = (count / total) * 100;
              const Icon = config.icon;

              return (
                <div key={signal}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-gray-600" />
                      <span className="text-sm font-medium text-gray-700">
                        {config.label}
                      </span>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      {count}
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${config.color} transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Total Count */}
          <div className="pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total Analyzed</span>
              <span className="text-lg font-bold text-gray-900">{total}</span>
            </div>
          </div>

          {/* Last Updated */}
          {data.timestamp && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Last updated: {formatDate(data.timestamp)}
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-6">
          <p className="text-sm text-gray-600">
            No analysis data available
          </p>
        </div>
      )}
    </div>
  );
};
