import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AdminUser {
  telegram_user_id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  role: string;
  permissions?: any;
}

interface AuthState {
  user: AdminUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  
  setAuth: (user: AdminUser, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  updateUser: (user: AdminUser) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        });
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      updateUser: (user) => {
        set({ user });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
