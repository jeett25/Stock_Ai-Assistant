import { useState } from 'react';
import { Send, Lightbulb } from 'lucide-react';

export const ChatInput = ({ onSend, isLoading, suggestions = [] }) => {
  const [message, setMessage] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setMessage(suggestion);
    setShowSuggestions(false);
  };

  const handleKeyDown = (e) => {
    // Submit on Ctrl/Cmd + Enter
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit(e);
    }
  };

  return (
    <div className="relative">
      {/* Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto z-10">
          <div className="p-2">
            <div className="flex items-center justify-between px-2 py-1 mb-1">
              <p className="text-xs font-semibold text-gray-600">
                Suggested Questions
              </p>
              <button
                onClick={() => setShowSuggestions(false)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Close
              </button>
            </div>
            <div className="space-y-1">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-primary-50 rounded transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}


      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about stocks, news, or market trends... (Ctrl+Enter to send)"
            className="input pr-10"
            disabled={isLoading}
          />
          
          {suggestions.length > 0 && (
            <button
              type="button"
              onClick={() => setShowSuggestions(!showSuggestions)}
              className={`
                absolute right-3 top-1/2 -translate-y-1/2 transition-colors
                ${showSuggestions ? 'text-primary-600' : 'text-gray-400 hover:text-primary-600'}
              `}
              title="Show suggestions"
            >
              <Lightbulb className="w-4 h-4" />
            </button>
          )}
        </div>

        <button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="btn-primary flex items-center gap-2 px-6"
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};