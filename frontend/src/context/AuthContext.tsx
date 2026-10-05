import { getSessionToken, saveSessionToken, clearSessionToken } from '../services/session';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../services/api';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string, staffOnly?: boolean) => Promise<void>;
  register: (name: string, email: string, password: string, academic?: unknown) => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<User>;
  uploadAvatar: (file: File) => Promise<string>;
  removeAvatar: () => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => getSessionToken());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    const sessionToken = getSessionToken();
    setIsLoading(true);
    try {
      if (!sessionToken) { setUser(null); return; }
      const response = await api.get('/auth/me', { headers: { Authorization: `Bearer ${sessionToken}` } });
      if (getSessionToken() !== sessionToken) return;
      setUser(response.data);
    } catch {
      if (getSessionToken() !== sessionToken) return;
      clearSessionToken();
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string, staffOnly = false) => {
    const response = await api.post('/auth/login', { email, password, portal: staffOnly ? 'staff' : 'student' });
    const { access_token } = response.data;
    // Check the database-backed identity before committing the new session.
    const userRes = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` }
    });
    if (staffOnly && !['librarian', 'admin'].includes(userRes.data.role)) {
      throw new Error('This portal is restricted to library staff.');
    }
    saveSessionToken(access_token);
    setToken(access_token);
    setUser(userRes.data);
  };

  const register = async (name: string, email: string, password: string, academic?: unknown) => {
    await api.post('/auth/register', { name, email, password, academic });
  };

  const updateProfile = async (data: Partial<User>): Promise<User> => {
    const response = await api.put('/auth/profile', data);
    const updated = response.data;
    setUser(updated);
    return updated;
  };

  const uploadAvatar = async (file: File): Promise<string> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/users/profile-picture', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    const updated = response.data;
    setUser(updated);
    return updated.profile_image || '';
  };

  const removeAvatar = async (): Promise<void> => {
    const response = await api.delete('/users/profile-picture');
    setUser(response.data);
  };

  const logout = () => {
    clearSessionToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        register,
        updateProfile,
        uploadAvatar,
        removeAvatar,
        logout,
        isLoading,
        refreshUser: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
