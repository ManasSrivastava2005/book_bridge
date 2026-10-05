import { getSessionToken, clearSessionToken } from './session';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to every request
api.interceptors.request.use((config) => {
  const token = getSessionToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses (expired token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // A rejected login is handled by its form; do not navigate away from it.
      if (error.config?.url === '/auth/login') return Promise.reject(error);
      const currentToken = getSessionToken();
      // An old in-flight request must not sign out a newer login.
      if (currentToken && error.config?.headers?.Authorization !== `Bearer ${currentToken}`) return Promise.reject(error);
      clearSessionToken();
      window.location.href = /^\/(admin(?:\/|$)|librarian\/login)/.test(window.location.pathname)
        ? '/librarian/login' : '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
