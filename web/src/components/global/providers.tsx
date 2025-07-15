"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import Cookies from 'js-cookie';

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
}

interface AuthContextType {
  accessToken: string | null;
  user: User | null;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = Cookies.get('alloy_access_token');
    if (token) {
      const decodedToken = parseJwt(token);
      if (decodedToken?.sub) {
        setUser({ email: decodedToken.sub });
        setAccessToken(token);
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((token: string, refreshToken: string) => {
    const decodedToken = parseJwt(token);
    if (decodedToken?.sub) {
      setUser({ email: decodedToken.sub });
      setAccessToken(token);
      Cookies.set('alloy_access_token', token, { expires: 1/48, secure: process.env.NODE_ENV === 'production' });
      Cookies.set('alloy_refresh_token', refreshToken, { expires: 7, secure: process.env.NODE_ENV === 'production' });
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    Cookies.remove('alloy_access_token');
    Cookies.remove('alloy_refresh_token');
    window.location.href = '/login';
  }, []);

  const value = {
    accessToken,
    user,
    login,
    logout,
    isAuthenticated: !!accessToken,
    isLoading,
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

export const AppProviders = ({ children }: { children: React.ReactNode }) => {
    return <AuthProvider>{children}</AuthProvider>
};