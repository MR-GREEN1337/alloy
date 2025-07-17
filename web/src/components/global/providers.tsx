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
    full_name?: string;
}

interface AuthContextType {
  accessToken: string | null;
  user: User | null;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  apiUrl: string; // Add apiUrl to the context
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

  const login = useCallback((token: string, refreshToken: string) => {
    const decodedToken = parseJwt(token);
    if (decodedToken && decodedToken.sub) {
      setUser({ email: decodedToken.sub, full_name: decodedToken.full_name });
      setAccessToken(token);
      Cookies.set('alloy_access_token', token, { expires: 1/24, secure: process.env.NODE_ENV === 'production' }); // 1 hour
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
    apiUrl, // Provide the runtime URL to the context
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

export const AppProviders = ({ children, apiUrl }: { children: React.ReactNode; apiUrl: string }) => {
    return <AuthProvider apiUrl={apiUrl}>{children}</AuthProvider>
};