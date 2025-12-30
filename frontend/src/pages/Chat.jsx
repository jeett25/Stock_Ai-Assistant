import { useSearchParams } from 'react-router-dom';
import { ChatInterface } from '../components/chat/ChatInterface';

export const Chat = () => {
  const [searchParams] = useSearchParams();
  const ticker = searchParams.get('ticker');

  return (
    <div className="h-[calc(100vh-4rem)]">
      <ChatInterface initialTicker={ticker} />
    </div>
  );
};