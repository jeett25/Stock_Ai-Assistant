import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatPrice, formatPercent, getSignalColor, getSignalEmoji } from '../../utils/helpers';
import { Link } from 'react-router-dom';

export const StockCard = ({ ticker, analysis, price }) => {
  if (!analysis) return null;

  const isPositive = price?.change > 0;
  const isNegative = price?.change < 0;
  const isNeutral = !price?.change || price?.change === 0;

  return (
    <Link
      to={`/chat?ticker=${ticker}`}
      className="card p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{ticker}</h3>
          <p className="text-sm text-gray-600">{analysis.date}</p>
        </div>
        
        {/* Signal Badge with Emoji */}
        <div className="flex items-center gap-1">
          <span className="text-lg">{getSignalEmoji(analysis.signal)}</span>
          <span className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(analysis.signal)}`}>
            {analysis.signal.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Price Info */}
      {price && (
        <div className="mb-3">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">
              {formatPrice(price.price)}
            </span>
            <div className={`flex items-center gap-1 text-sm font-medium ${
              isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-500'
            }`}>
              {isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : isNegative ? (
                <TrendingDown className="w-4 h-4" />
              ) : (
                <Minus className="w-4 h-4" />
              )}
              <span>{formatPrice(Math.abs(price.change))}</span>
              <span>({formatPercent(price.change_percent)})</span>
            </div>
          </div>
        </div>
      )}

      {/* Key Indicators */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-gray-50 rounded p-2">
          <p className="text-xs text-gray-600 mb-1">RSI</p>
          <p className="text-sm font-semibold text-gray-900">
            {analysis.rsi ? analysis.rsi.toFixed(1) : 'N/A'}
          </p>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <p className="text-xs text-gray-600 mb-1">Confidence</p>
          <p className="text-sm font-semibold text-gray-900">
            {analysis.confidence ? `${(analysis.confidence * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Top Reason */}
      {analysis.top_reason && (
        <p className="text-xs text-gray-600 line-clamp-2">
          {analysis.top_reason}
        </p>
      )}
    </Link>
  );
};
