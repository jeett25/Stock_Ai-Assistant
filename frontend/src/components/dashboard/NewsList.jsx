import { ExternalLink, Calendar, Newspaper } from 'lucide-react';
import { formatDate } from '../../utils/helpers';

export const NewsList = ({ news, ticker }) => {
  if (!news || news.length === 0) {
    return (
      <div className="card p-6 text-center">
        <Newspaper className="w-12 h-12 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-600">No recent news available</p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      {ticker && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Latest News for {ticker}
        </h3>
      )}
      
      <div className="space-y-3">
        {news.map((article) => (
          <a
            key={article.id}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors group"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 group-hover:text-primary-700 line-clamp-2 mb-1">
                  {article.title}
                </h4>
                
                <div className="flex items-center gap-2 text-xs text-gray-600 flex-wrap">
                  <span className="font-medium">{article.source}</span>
                  
                  {article.ticker && (
                    <>
                      <span>•</span>
                      <span className="px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded font-medium">
                        {article.ticker}
                      </span>
                    </>
                  )}
                  
                  {article.published_at && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(article.published_at)}</span>
                      </div>
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
