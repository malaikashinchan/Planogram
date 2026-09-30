import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import authService from '../services/authService';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const expiryTimerRef = useRef(null);

  // ─────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────

  const clearAuth = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    if (expiryTimerRef.current) {
      clearTimeout(expiryTimerRef.current);
      expiryTimerRef.current = null;
    }
  }, []);

  /**
   * Decode the JWT payload (no signature verification — backend does that).
   * Returns the `exp` field in milliseconds, or null if malformed.
   */
  const getTokenExpiry = (rawToken) => {
    try {
      const payloadBase64 = rawToken.split('.')[1];
      const payload = JSON.parse(atob(payloadBase64));
      return payload.exp ? payload.exp * 1000 : null; // convert s → ms
    } catch {
      return null;
    }
  };

  /**
   * Schedule a proactive logout 30 seconds before the JWT expires.
   * This prevents the silent cookie-fallback collision.
   */
  const scheduleTokenExpiry = useCallback((rawToken) => {
    if (expiryTimerRef.current) {
      clearTimeout(expiryTimerRef.current);
    }
    const expiry = getTokenExpiry(rawToken);
    if (!expiry) return;

    const now = Date.now();
    const msUntilExpiry = expiry - now - 30_000; // 30s before expiry

    if (msUntilExpiry <= 0) {
      // Already expired or about to expire — clear immediately
      clearAuth();
      return;
    }

    expiryTimerRef.current = setTimeout(() => {
      console.warn('[AuthContext] JWT is about to expire — clearing session to prevent role collision');
      clearAuth();
    }, msUntilExpiry);
  }, [clearAuth]);

  // ─────────────────────────────────────────────────────────
  // Startup: validate stored token with backend
  // ─────────────────────────────────────────────────────────

  const fetchUser = useCallback(async () => {
    if (!token) {
      clearAuth();
      setLoading(false);
      return;
    }

    // Proactively check if the JWT is already expired client-side
    const expiry = getTokenExpiry(token);
    if (expiry && Date.now() > expiry) {
      console.warn('[AuthContext] Stored JWT is expired — clearing stale session');
      clearAuth();
      setLoading(false);
      return;
    }

    try {
      const userData = await authService.getMe();
      if (userData && userData.email && Array.isArray(userData.roles) && userData.roles.length > 0) {
        setUser(userData);
        setIsAuthenticated(true);
        scheduleTokenExpiry(token);
      } else {
        console.warn('[AuthContext] getMe returned invalid user data');
        clearAuth();
      }
    } catch (error) {
      console.error('[AuthContext] Failed to fetch user profile:', error);
      clearAuth();
    } finally {
      setLoading(false);
    }
  }, [token, clearAuth, scheduleTokenExpiry]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // ─────────────────────────────────────────────────────────
  // Global 401 handler (axios interceptor fires this)
  // ─────────────────────────────────────────────────────────

  useEffect(() => {
    const handleUnauthorized = () => {
      console.warn('[AuthContext] auth:unauthorized event — clearing session');
      clearAuth();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [clearAuth]);

  // ─────────────────────────────────────────────────────────
  // Login / Logout
  // ─────────────────────────────────────────────────────────

  const login = (newToken, userData) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
    setIsAuthenticated(true);
    scheduleTokenExpiry(newToken);
  };

  const logout = async (callApi = true) => {
    if (callApi) {
      try {
        await authService.logout();
      } catch (e) {
        console.error('[AuthContext] Logout API failed:', e);
      }
    }
    clearAuth();
  };

  const value = {
    user,
    token,
    isAuthenticated,
    loading,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
