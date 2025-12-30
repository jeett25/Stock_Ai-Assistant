import { Link } from 'react-router-dom';
import { MessageSquare, BarChart3, TrendingUp, Shield, Zap, Brain } from 'lucide-react';
import { Disclaimer } from '../components/common/Disclaimer';

export const Home = () => {
  const features = [
    {
      icon: Brain,
      title: 'Intelligent Routing',
      description: 'Ask naturally - our AI automatically detects what you need and routes to the right handler.',
    },
    {
      icon: MessageSquare,
      title: 'AI-Powered Chat',
      description: 'Get context-aware answers based on real data, news, and technical analysis.',
    },
    {
      icon: BarChart3,
      title: 'Technical Analysis',
      description: 'View RSI, MACD, moving averages, and other indicators with clear explanations.',
    },
    {
      icon: TrendingUp,
      title: 'Real-Time Data',
      description: 'Stay updated with latest news from multiple trusted sources and live market data.',
    },
    {
      icon: Zap,
      title: 'Fast & Responsive',
      description: 'Get instant answers and analysis powered by efficient backend processing.',
    },
    {
      icon: Shield,
      title: 'Educational Focus',
      description: 'Learn about market concepts and indicators without pushy recommendations.',
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-primary-50 to-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 text-primary-700 rounded-full text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Powered by AI Intelligence
            </div>
            
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
              Your AI Stock Market Assistant
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              Get real-time analysis, news, and insights powered by AI. 
              Ask questions naturally and get intelligent, context-aware responses.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/chat"
                className="btn-primary px-8 py-3 text-lg inline-flex items-center gap-2 justify-center"
              >
                <MessageSquare className="w-5 h-5" />
                Start Chatting
              </Link>
              <Link
                to="/dashboard"
                className="btn-secondary px-8 py-3 text-lg inline-flex items-center gap-2 justify-center"
              >
                <BarChart3 className="w-5 h-5" />
                View Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            Features
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            Everything you need to make informed investment decisions with AI-powered intelligence
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="text-center">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon className="w-8 h-8 text-primary-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-primary-600 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-primary-100 mb-8">
            Start analyzing stocks with AI-powered insights today. No signup required.
          </p>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 bg-white text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-primary-50 transition-colors"
          >
            <MessageSquare className="w-5 h-5" />
            Launch Chat Assistant
          </Link>
        </div>
      </div>

      {/* Disclaimer Section */}
      <div className="py-12 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <Disclaimer />
        </div>
      </div>
    </div>
  );
};
