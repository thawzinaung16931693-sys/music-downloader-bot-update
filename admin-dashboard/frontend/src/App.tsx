import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';

import LoginPage from './pages/LoginPage';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/UsersPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="subscriptions" element={<ComingSoon title="Subscriptions" />} />
            <Route path="trials" element={<ComingSoon title="Trial Campaigns" />} />
            <Route path="analytics" element={<ComingSoon title="Analytics" />} />
            <Route path="settings" element={<ComingSoon title="Settings" />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

const ComingSoon: React.FC<{ title: string }> = ({ title }) => (
  <div className="flex items-center justify-center h-96">
    <div className="text-center">
      <h1 className="text-4xl font-black text-neon-cyan text-neon-glow mb-4">
        {title}
      </h1>
      <p className="text-gray-400 font-mono">Coming soon...</p>
    </div>
  </div>
);

export default App;
