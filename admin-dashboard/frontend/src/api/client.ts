import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/api/admin/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  telegramLogin: (authData: any) => 
    api.post('/api/admin/auth/telegram', authData),
  
  refreshToken: (refreshToken: string) => 
    api.post('/api/admin/auth/refresh', { refresh_token: refreshToken }),
  
  getCurrentUser: () => 
    api.get('/api/admin/auth/me'),
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => 
    api.get('/api/admin/dashboard/stats'),
  
  getActivity: (limit = 20) => 
    api.get('/api/admin/dashboard/activity', { params: { limit } }),
  
  getUserGrowthChart: (days = 30) => 
    api.get('/api/admin/dashboard/charts/user-growth', { params: { days } }),
  
  getDownloadsChart: (days = 30) => 
    api.get('/api/admin/dashboard/charts/downloads', { params: { days } }),
};

// Users API
export const usersAPI = {
  list: (params: {
    skip?: number;
    limit?: number;
    tier?: string;
    status?: string;
    search?: string;
  }) => api.get('/api/admin/users', { params }),
  
  get: (userId: number) => 
    api.get(`/api/admin/users/${userId}`),
  
  update: (userId: number, data: any) => 
    api.put(`/api/admin/users/${userId}`, data),
  
  ban: (userId: number, reason: string) => 
    api.post(`/api/admin/users/${userId}/ban`, { reason }),
  
  unban: (userId: number) => 
    api.post(`/api/admin/users/${userId}/unban`),
  
  sendMessage: (userId: number, message: string) => 
    api.post(`/api/admin/users/${userId}/message`, { message }),
  
  getHistory: (userId: number, limit = 50) => 
    api.get(`/api/admin/users/${userId}/history`, { params: { limit } }),
};

export default api;
