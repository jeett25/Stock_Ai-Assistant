import { ExternalLink, FileText } from 'lucide-react';
import { formatDate } from '../../utils/helpers';

export const SourcesList = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-gray-600" />
        <h3 className="text-sm font-semibold text-gray-900">
          Sources ({sources.length})
        </h3>
      </div>
      <div className="space-y-2">
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 group-hover:text-primary-700 truncate">
                  {source.title}
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-600 flex-wrap">
                  {source.source && (
                    <>
                      <span>{source.source}</span>
                      <span>•</span>
                    </>
                  )}
                  {source.published_at && (
                    <>
                      <span>{formatDate(source.published_at)}</span>
                      <span>•</span>
                    </>
                  )}
                  {source.similarity !== undefined && source.similarity !== null && (
                    <span className="text-green-600 font-medium">
                      {(source.similarity * 100).toFixed(0)}% relevant
                    </span>
                  )}
                  {source.ticker && (
                    <>
                      <span>•</span>
                      <span className="text-primary-600 font-medium">{source.ticker}</span>
                    </>
                  )}
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-primary-600 flex-shrink-0" />
            </div>
          </a>
        ))}
      </div>
    </div>
  );
};
