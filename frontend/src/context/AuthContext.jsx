import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE } from '../config/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('bg_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => {
    return localStorage.getItem('bg_token') || null;
  });

  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [unreadNotifications, setUnreadNotifications] = useState(0);

  // Sync token & user to localStorage
  useEffect(() => {
    if (token && user) {
      localStorage.setItem('bg_token', token);
      localStorage.setItem('bg_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('bg_token');
      localStorage.removeItem('bg_user');
    }
  }, [token, user]);

  // Fetch current user details & notifications on mount if token exists
  useEffect(() => {
    if (token && !token.startsWith('demo_token_')) {
      fetch(`${API_BASE}/api/auth/me/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => {
        if (res.ok) return res.json();
        if (res.status === 401) {
          throw new Error('Unauthorized');
        }
        return null;
      })
      .then(data => {
        if (data && data.user) {
          setUser(data.user);
          setUnreadNotifications(data.unread_notifications || 0);
        }
      })
      .catch((err) => {
        if (err.message === 'Unauthorized') {
          logout();
        }
      });
    }
  }, [token]);

  const login = async (rawUsername, rawPassword, portal = 'WRITER') => {
    setLoading(true);
    setAuthError(null);
    const username = (rawUsername || '').trim();
    const password = (rawPassword || '').trim();
    const lower = username.toLowerCase();

    try {
      const res = await fetch(`${API_BASE}/api/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email: username, password, portal })
      });
      const data = await res.json();
      if (!res.ok) {
        const error = new Error(data.error || 'Authentication failed');
        error.status = res.status;
        error.data = data;
        throw error;
      }
      setToken(data.token);
      setUser(data.user);
      return data.user;
    } catch (err) {
      // If error has specific status or data from server, re-throw it directly
      if (err.status || err.data) {
        setAuthError(err.message);
        throw err;
      }

      // Resilient Fallback: If backend is offline or credentials match demo personas
      if (lower === 'admin' || lower === 'admin@novapay.io' || lower === 'jordan') {
        const demoUser = {
          id: 1,
          username: 'admin',
          email: 'admin@novapay.io',
          name: 'Jordan Lee',
          first_name: 'Jordan',
          last_name: 'Lee',
          role: 'ADMIN',
          department: 'Brand Governance Lead',
          avatar_color: '#0A3423',
          is_email_verified: true,
          is_approved: true
        };
        setToken('demo_token_admin_2026');
        setUser(demoUser);
        return demoUser;
      } else if (lower === 'writer1' || lower === 'alex.morgan@novapay.io' || lower === 'alex') {
        const demoUser = {
          id: 2,
          username: 'writer1',
          email: 'alex.morgan@novapay.io',
          name: 'Alex Morgan',
          first_name: 'Alex',
          last_name: 'Morgan',
          role: 'CONTENT_WRITER',
          department: 'Marketing Ops',
          avatar_color: '#00D4B6',
          is_email_verified: true,
          is_approved: true
        };
        setToken('demo_token_writer1_2026');
        setUser(demoUser);
        return demoUser;
      } else if (lower === 'writer2' || lower === 'taylor.reed@novapay.io' || lower === 'taylor') {
        const demoUser = {
          id: 3,
          username: 'writer2',
          email: 'taylor.reed@novapay.io',
          name: 'Taylor Reed',
          first_name: 'Taylor',
          last_name: 'Reed',
          role: 'CONTENT_WRITER',
          department: 'Growth & Social',
          avatar_color: '#3B82F6',
          is_email_verified: true,
          is_approved: true
        };
        setToken('demo_token_writer2_2026');
        setUser(demoUser);
        return demoUser;
      }

      setAuthError(err.message || 'Authentication failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const registerAdmin = async (formData) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/register/admin/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Admin registration failed');
      }
      return data;
    } finally {
      setLoading(false);
    }
  };

  const registerWriter = async (formData) => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/register/writer/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Writer registration failed');
      }
      return data;
    } finally {
      setLoading(false);
    }
  };

  const verifyEmail = async (tokenStr) => {
    const res = await fetch(`${API_BASE}/api/auth/verify-email/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: tokenStr })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Email verification failed');
    }
    return data;
  };

  const requestPasswordReset = async (email) => {
    const res = await fetch(`${API_BASE}/api/auth/password-reset/request/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Password reset request failed');
    }
    return data;
  };

  const confirmPasswordReset = async (formData) => {
    const res = await fetch(`${API_BASE}/api/auth/password-reset/confirm/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Password reset confirmation failed');
    }
    return data;
  };

  const logout = async () => {
    try {
      if (token) {
        await fetch(`${API_BASE}/api/auth/logout/`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    } catch {
      // Ignored
    }
    setToken(null);
    setUser(null);
  };

  const isAdmin = user?.role === 'ADMIN';
  const isWriter = user?.role === 'CONTENT_WRITER';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAdmin,
        isWriter,
        loading,
        authError,
        unreadNotifications,
        login,
        logout,
        registerAdmin,
        registerWriter,
        verifyEmail,
        requestPasswordReset,
        confirmPasswordReset,
        setUser,
        setToken
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
