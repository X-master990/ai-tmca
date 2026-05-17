import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { useAuthStore, User } from '../store/auth';

interface LoginResponse {
  access_token: string;
  expires_in: number;
  user: User;
}

export default function Login() {
  const navigate = useNavigate();
  const { token, setAuth } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const r = await api<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setAuth(r.access_token, r.user);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : '登入失敗');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form
        onSubmit={onSubmit}
        className="bg-white rounded-2xl shadow-lg p-10 max-w-md w-full"
      >
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🎵</div>
          <h1 className="text-2xl font-bold text-navy">TMCA</h1>
          <div className="text-xs text-soft mt-1">音樂著作公開演出授權系統</div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-soft mb-1">帳號</label>
            <input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-soft mb-1">密碼</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
              required
            />
          </div>

          {error && (
            <div className="text-sm text-warn bg-red-50 px-3 py-2 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-navy text-white py-2 rounded-lg font-medium hover:bg-teal disabled:opacity-50 transition"
          >
            {submitting ? '登入中…' : '登入'}
          </button>
        </div>

        <div className="mt-6 pt-6 border-t border-slate-200 text-xs text-soft">
          <div className="font-medium mb-1">測試帳號（預設密碼 Tmca0001!）</div>
          <div className="font-mono">
            officer_a / officer_b / accountant / issuer / admin
          </div>
        </div>
      </form>
    </div>
  );
}
