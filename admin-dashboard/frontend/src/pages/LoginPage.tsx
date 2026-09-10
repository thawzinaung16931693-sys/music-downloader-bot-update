import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/client';

declare global {
  interface Window {
    Telegram?: any;
  }
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { setAuth, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }

    // Load Telegram Widget script
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', 'barlarlaraimusicdownloader_bot');
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '10');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');

    const container = document.getElementById('telegram-login-container');
    if (container) {
      container.appendChild(script);
    }

    // Define callback
    (window as any).onTelegramAuth = async (user: any) => {
      try {
        const response = await authAPI.telegramLogin(user);
        const { access_token, refresh_token } = response.data;

        // Get user info
        const userResponse = await authAPI.getCurrentUser();
        setAuth(userResponse.data, access_token, refresh_token);

        navigate('/dashboard');
      } catch (error) {
        console.error('Login failed:', error);
        alert('Login failed. You may not have admin access.');
      }
    };

    return () => {
      // Cleanup
      delete (window as any).onTelegramAuth;
    };
  }, [isAuthenticated, navigate, setAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 scanline pointer-events-none"></div>
      
      {/* Floating geometric shapes */}
      <div className="absolute top-20 left-20 w-40 h-40 border-4 border-neon-pink opacity-20 rotate-45 animate-pulse-slow"></div>
      <div className="absolute bottom-20 right-20 w-60 h-60 border-4 border-neon-cyan opacity-20 rotate-12 animate-pulse-slow"></div>
      <div className="absolute top-1/2 left-10 w-32 h-32 border-4 border-neon-purple opacity-20 -rotate-12 animate-pulse-slow"></div>

      <div className="card max-w-md w-full mx-4 z-10">
        <div className="text-center mb-8">
          <h1 
            className="text-5xl font-black text-neon-glow text-transparent bg-clip-text bg-gradient-to-r from-neon-pink via-neon-cyan to-neon-purple mb-4"
            data-text="ADMIN DASHBOARD"
          >
            ADMIN DASHBOARD
          </h1>
          <p className="text-neon-cyan text-xl font-mono">Bar Lar Lar Music Bot</p>
        </div>

        <div className="space-y-6">
          <div className="border-2 border-neon-cyan rounded-lg p-8 text-center hover:shadow-neon-cyan transition-all">
            <div className="mb-4">
              <svg 
                className="w-16 h-16 mx-auto text-neon-cyan" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" 
                />
              </svg>
            </div>
            
            <h2 className="text-2xl font-bold text-neon-pink mb-4">Secure Login</h2>
            <p className="text-gray-400 mb-6 font-mono text-sm">
              Authenticate with your Telegram account to access the admin panel
            </p>
            
            <div id="telegram-login-container" className="flex justify-center"></div>
          </div>

          <div className="text-center text-xs text-gray-500 font-mono">
            <p>🔒 Encrypted connection • OAuth 2.0</p>
            <p className="mt-2">Only authorized admins can access this panel</p>
          </div>
        </div>
      </div>

      {/* Corner decorations */}
      <div className="absolute top-0 left-0 w-32 h-32 border-l-4 border-t-4 border-neon-pink opacity-50"></div>
      <div className="absolute top-0 right-0 w-32 h-32 border-r-4 border-t-4 border-neon-cyan opacity-50"></div>
      <div className="absolute bottom-0 left-0 w-32 h-32 border-l-4 border-b-4 border-neon-purple opacity-50"></div>
      <div className="absolute bottom-0 right-0 w-32 h-32 border-r-4 border-b-4 border-neon-pink opacity-50"></div>
    </div>
  );
};

export default LoginPage;
