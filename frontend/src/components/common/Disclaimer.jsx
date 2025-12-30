import { AlertTriangle } from 'lucide-react';

export const Disclaimer = ({ className = '' }) => {
  return (
    <div className={`bg-yellow-50 border border-yellow-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-yellow-900 mb-1">
            Important Disclaimer
          </h3>
          <p className="text-xs text-yellow-800 leading-relaxed">
            This is educational information only, not financial advice. Stock markets are risky. 
            Past performance doesn't guarantee future results. Always do your own research and 
            consult a licensed financial advisor before making investment decisions.
          </p>
        </div>
      </div>
    </div>
  );
};