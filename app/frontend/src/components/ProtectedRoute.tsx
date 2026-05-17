import { ReactNode, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { useAuthStore, User } from '../store/auth';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, user, setAuth, clear } = useAuthStore();
  const [checking, setChecking] = useState(!!token && !user);

  useEffect(() => {
    if (!token) return;
    if (user) return;
    let alive = true;
    (async () => {
      try {
        const me = await api<User>('/api/auth/me');
        if (alive) setAuth(token, me);
      } catch (err) {
        if (alive && err instanceof ApiError && err.status === 401) clear();
      } finally {
        if (alive) setChecking(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [token, user, setAuth, clear]);

  if (!token) return <Navigate to="/login" replace />;
  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center text-soft">
        驗證中…
      </div>
    );
  }
  return <>{children}</>;
}
