import { User, Bot, AlertCircle, Info } from 'lucide-react';
import { formatTime, getSignalColor, getIntentLabel } from '../../utils/helpers';

export const MessageBubble = ({ message }) => {
  const isUser = message.type === 'user';
  const isError = message.type === 'error';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`
        flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
        ${isUser ? 'bg-primary-600' : isError ? 'bg-red-600' : 'bg-gray-700'}
      `}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : isError ? (
          <AlertCircle className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      <div className={`flex-1 max-w-2xl ${isUser ? 'flex justify-end' : ''}`}>
        <div className={`
          rounded-lg px-4 py-3
          ${isUser ? 'bg-primary-600 text-white' : 'bg-white border border-gray-200'}
        `}>
          {!isUser && !isError && message.intent && (
            <div className="flex items-center gap-1 mb-2 text-xs text-gray-500">
              <Info className="w-3 h-3" />
              <span>{getIntentLabel(message.intent)}</span>
            </div>
          )}


          <div className={`
            text-sm whitespace-pre-wrap break-words
            ${isUser ? 'text-white' : 'text-gray-900'}
          `}>
            {message.content}
          </div>

          {!isUser && message.signal && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2 text-xs flex-wrap">
                <span className="text-gray-600">Signal:</span>
                <span className={`
                  px-2 py-1 rounded font-medium
                  ${getSignalColor(message.signal)}
                `}>
                  {message.signal.replace('_', ' ')}
                </span>
                {message.confidence !== null && message.confidence !== undefined && (
                  <span className="text-gray-500">
                    ({(message.confidence * 100).toFixed(0)}% confidence)
                  </span>
                )}
              </div>
            </div>
          )}


          {!isUser && message.ticker && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded font-medium">
                {message.ticker}
              </span>
            </div>
          )}


          {!isUser && message.contextRetrieved && (
            <div className="mt-2 flex items-center gap-1 text-xs text-green-600">
              <Info className="w-3 h-3" />
              <span>Retrieved from knowledge base</span>
            </div>
          )}


          <div className={`
            mt-2 text-xs
            ${isUser ? 'text-primary-100' : 'text-gray-500'}
          `}>
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    </div>
  );
};
