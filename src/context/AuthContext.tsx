import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { login as apiLogin, register as apiRegister, logout as apiLogout, getProfile } from '../api/auth';
import { clearToken, getToken, refreshSession } from '../api/client';
import { wsClient } from '../api/websocket';

interface AuthContextType {
  user: any;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const session = await refreshSession();
        setUser(session.user);
        wsClient.connect(session.user.id, session.access_token);
      } catch { clearToken(); }
      setLoading(false);
    };
    initAuth();
  }, []);

  useEffect(() => {
    if (!user) return;
    const reconnect = () => { const token = getToken(); if (token) wsClient.connect(user.id, token); };
    window.addEventListener('hp:token-refreshed', reconnect);
    const interval = window.setInterval(() => { refreshSession().catch(() => { clearToken(); setUser(null); wsClient.disconnect(); }); }, 8 * 60 * 1000);
    return () => { clearInterval(interval); window.removeEventListener('hp:token-refreshed', reconnect); };
  }, [user?.id]);

  useEffect(() => {
    const expireSession = () => {
      setUser(null);
      wsClient.disconnect();
    };
    window.addEventListener('hp:session-expired', expireSession);
    return () => window.removeEventListener('hp:session-expired', expireSession);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setError(null);
      const res = await apiLogin(email, password);
      setUser(res.user);
      if (res.access_token) {
        wsClient.connect(res.user.id, res.access_token);
      }
    } catch (err: any) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw new Error(message);
    }
  };

  const register = async (data: any) => {
    try {
      setError(null);
      const res = await apiRegister(data);
      setUser(res.user);
      if (res.access_token) {
        wsClient.connect(res.user.id, res.access_token);
      }
    } catch (err: any) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
      throw new Error(message);
    }
  };

  const logout = async () => {
    await apiLogout();
    clearToken(); setUser(null); wsClient.disconnect();
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshProfile: async () => { setUser(await getProfile()); },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
