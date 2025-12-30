import { useState, useCallback } from 'react';
import { sendChatMessage } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const sendMessage = useCallback(async (query, ticker = null, structured = false) => {
    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    try {
        // Send with chat history for context
        const response = await sendChatMessage(query, ticker, chatHistory, structured);
        

        const aiMessage = {
          id: Date.now() + 1,
          type: 'assistant',
          content: response.response,
          ticker: response.ticker,
          signal: response.signal,
          confidence: response.confidence,
          sources: response.sources || [],
          timestamp: response.timestamp,
          intent: response.intent,
          handler: response.handler,
          contextRetrieved: response.context_retrieved,
        };
        
        setMessages(prev => [...prev, aiMessage]);
        
        setChatHistory(prev => [
          ...prev,
          { role: 'user', content: query },
          { role: 'assistant', content: response.response }
        ]);
        
        return aiMessage;
        
      } catch (err) {
        const errorMessage = {
          id: Date.now() + 1,
          type: 'error',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString(),
        };
        
        setMessages(prev => [...prev, errorMessage]);
        setError(err.message);
        throw err;
        
      } finally {
        setIsLoading(false);
      }
    }, [chatHistory]);

    
    const clearMessages = useCallback(() => {
        setMessages([]);
        setChatHistory([]);
        setError(null);
      }, []);
    
      return {
        messages,
        isLoading,
        error,
        sendMessage,
        clearMessages,
      };
    };
  