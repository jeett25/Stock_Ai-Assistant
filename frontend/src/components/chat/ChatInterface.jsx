import { useEffect, useRef, useState } from 'react';
import { useChat } from '../../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { SourcesList } from './SourcesList';
import { Loader } from '../common/Loader';
import { ErrorMessage } from '../common/ErrorMessage';
import { Disclaimer } from '../common/Disclaimer';
import { getQuerySuggestions } from '../../services/api';
import { MessageSquare, Trash2 } from 'lucide-react';

export const ChatInterface = ({ initialTicker = null }) => {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef(null);
  const [suggestions, setSuggestions] = useState([]);
  const [currentTicker, setCurrentTicker] = useState(initialTicker);
  const [lastSources, setLastSources] = useState([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    getQuerySuggestions()
      .then(data => {
        const allSuggestions = [];
        if (data.categories) {
          Object.values(data.categories).forEach(categoryArray => {
            allSuggestions.push(...categoryArray);
          });
        }
        setSuggestions(allSuggestions.slice(0, 10)); // Take first 10
      })
      .catch(err => {
        console.error('Error loading suggestions:', err);
        setSuggestions([]);
      });
  }, []);

  useEffect(() => {
    const lastAssistantMessage = messages
      .slice()
      .reverse()
      .find(msg => msg.type === 'assistant');
    
    if (lastAssistantMessage?.sources) {
      setLastSources(lastAssistantMessage.sources);
    }
  }, [messages]);

  const handleSendMessage = async (message) => {
    try {
      const response = await sendMessage(message, currentTicker);
      
      if (response.ticker && response.ticker !== currentTicker) {
        setCurrentTicker(response.ticker);
      }
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      clearMessages();
      setLastSources([]);
      setCurrentTicker(initialTicker);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">
              Stock Assistant Chat
            </h2>
            {currentTicker && (
              <span className="px-2 py-1 bg-primary-50 text-primary-700 text-xs font-medium rounded">
                {currentTicker}
              </span>
            )}
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-sm text-gray-600 hover:text-red-600 flex items-center gap-1 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Start a Conversation
              </h3>
              <p className="text-gray-600 mb-6">
                Ask me anything about stocks, news, technical indicators, or market trends.
                I'll automatically understand what you need!
              </p>
              
              {/* Example Questions */}
              <div className="max-w-md mx-auto space-y-2">
                <p className="text-sm font-medium text-gray-700 mb-3">
                  Try these examples:
                </p>
                {[
                  "What's the latest news?",
                  "Analyze Apple stock",
                  "Should I buy Tesla?",
                  "Compare AAPL and MSFT",
                ].map((example, index) => (
                  <button
                    key={index}
                    onClick={() => handleSendMessage(example)}
                    className="block w-full text-left px-4 py-3 bg-white border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors text-sm text-gray-700"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              
              {isLoading && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                    <Loader size="small" text="Thinking..." />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {lastSources.length > 0 && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <SourcesList sources={lastSources} />
          </div>
        </div>
      )}

      {error && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <ErrorMessage message={error} onClose={() => {}} />
          </div>
        </div>
      )}

      <div className="bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <ChatInput
            onSend={handleSendMessage}
            isLoading={isLoading}
            suggestions={suggestions}
          />
          
          <div className="mt-3">
            <Disclaimer />
          </div>
        </div>
      </div>
    </div>
  );
};
