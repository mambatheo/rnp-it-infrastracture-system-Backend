import { useMemo } from 'react';

const BASE = 'http://localhost:8000/api/v1';

/**
 * Reads auth state from localStorage and exposes helpers.
 * No Context needed — keeps it simple and works across components.
 */
export function useAuth() {
  const token  = localStorage.getItem('access_token');
  const role   = localStorage.getItem('role');
  const rawUser = localStorage.getItem('user');

  const user = useMemo(() => {
    try { return rawUser ? JSON.parse(rawUser) : null; }
    catch { return null; }
  }, [rawUser]);

  const isAuthenticated = !!token;

  /** Check if current user has one of the given roles */
  const can = (...roles) => roles.includes(role);

  const logout = async () => {
    try {
      await fetch(`${BASE}/accounts/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    } catch { /* ignore */ }
    localStorage.clear();
    window.location.href = '/login';
  };

  return { user, role, isAuthenticated, can, logout };
}

export default useAuth;
