"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import Cookies from 'js-cookie';
import { SWRConfig } from 'swr';
import { toast } from 'sonner';

// A simple JWT parser without adding extra dependencies
const parseJwt = (token: string) => {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (error) {
        console.error("Failed to parse JWT:", error);
        return null;
    }
};

interface User {
    email: string;
    full_name?: string;
}

interface AuthContextType {
  accessToken: string | null;
  user: User | null;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  apiUrl: string;
  authedFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children, apiUrl }: { children: React.ReactNode, apiUrl: string }) => {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = Cookies.get('alloy_access_token');
    if (token) {
      const decodedToken = parseJwt(token);
      if (decodedToken && decodedToken.sub) {
        setUser({ email: decodedToken.sub, full_name: decodedToken.full_name });
        setAccessToken(token);
      }
    }
    setIsLoading(false);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    Cookies.remove('alloy_access_token');
    Cookies.remove('alloy_refresh_token');
    window.location.href = '/login';
  }, []);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    const refreshToken = Cookies.get('alloy_refresh_token');
    if (!refreshToken) {
      logout();
      return null;
    }
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) throw new Error('Refresh failed, please log in again.');
      const { access_token: newAccessToken } = await res.json();
      const decodedToken = parseJwt(newAccessToken);
      setAccessToken(newAccessToken);
      if (decodedToken) setUser({ email: decodedToken.sub, full_name: decodedToken.full_name });
      Cookies.set('alloy_access_token', newAccessToken, { expires: 1 / 24, secure: process.env.NODE_ENV === 'production' });
      return newAccessToken;
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout();
      return null;
    }
  }, [apiUrl, logout]);

  const authedFetch = useCallback(async (url: string, options?: RequestInit): Promise<Response> => {
    let token = Cookies.get('alloy_access_token');
    if (!token) { logout(); throw new Error("User not authenticated"); }
    
    const res = await fetch(url, { ...options, headers: { ...options?.headers, 'Authorization': `Bearer ${token}` } });
    
    if (res.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        return fetch(url, { ...options, headers: { ...options?.headers, 'Authorization': `Bearer ${newToken}` } });
      } else {
        throw new Error("Session expired");
      }
    }
    return res;
  }, [logout, refreshAccessToken]);

  const login = useCallback((token: string, refreshToken: string) => {
    const decodedToken = parseJwt(token);
    if (decodedToken && decodedToken.sub) {
      setUser({ email: decodedToken.sub, full_name: decodedToken.full_name });
      setAccessToken(token);
      Cookies.set('alloy_access_token', token, { expires: 1 / 24, secure: process.env.NODE_ENV === 'production' }); // 1 hour
      Cookies.set('alloy_refresh_token', refreshToken, { expires: 7, secure: process.env.NODE_ENV === 'production' });
    }
  }, []);

  const value = {
    accessToken,
    user,
    login,
    logout,
    isAuthenticated: !!accessToken,
    isLoading,
    apiUrl,
    authedFetch,
  };

  const swrFetcher = async (url: string) => {
      const res = await authedFetch(url);
      if (!res.ok) {
          const errorData = await res.json().catch(() => ({ detail: `Request failed with status ${res.status}` }));
          throw new Error(errorData.detail);
      }
      return res.json();
  };

  return <AuthContext.Provider value={value}>
    <SWRConfig value={{ fetcher: swrFetcher, onError: (error) => {
      if (error.message !== 'Session expired' && error.message !== 'User not authenticated') { toast.error("Error", { description: error.message }); }
    }}}>{children}</SWRConfig>
  </AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AppProviders = ({ children, apiUrl }: { children: React.ReactNode; apiUrl: string }) => {
    return <AuthProvider apiUrl={apiUrl}>{children}</AuthProvider>
};