import { Header } from './Header';
export const Layout = ({ children }) => {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />
        <main className="flex-1">
          {children}
        </main>
        <footer className="bg-white border-t border-gray-200 py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-center text-sm text-gray-600">
              © 2025 Stock Assistant. Built for educational purposes only.
            </p>
          </div>
        </footer>
      </div>
    );
  };