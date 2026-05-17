import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ROLE_LABEL, useAuthStore } from '../store/auth';

export default function Home() {
  const { user, clear } = useAuthStore();
  const navigate = useNavigate();

  async function logout() {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch {
      /* ignore */
    }
    clear();
    navigate('/login', { replace: true });
  }

  if (!user) return null;

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-2xl w-full">
        <div className="flex justify-between items-start mb-8">
          <div>
            <div className="text-2xl mb-1">🎵</div>
            <h1 className="text-2xl font-bold text-navy">TMCA</h1>
            <div className="text-xs text-soft">音樂著作公開演出授權系統</div>
          </div>
          <button
            onClick={logout}
            className="text-sm text-soft hover:text-warn transition"
          >
            登出
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-6">
          <button
            onClick={() => navigate('/records')}
            className="bg-navy text-white py-3 rounded-lg font-medium hover:bg-teal transition text-base"
          >
            📊 進入總表
          </button>
          <button
            onClick={() => navigate('/renewals')}
            className="bg-white border border-navy text-navy py-3 rounded-lg font-medium hover:bg-cyan transition text-base"
          >
            🔁 續約管理
          </button>
          <button
            onClick={() => navigate('/search')}
            className="bg-white border border-navy text-navy py-3 rounded-lg font-medium hover:bg-cyan transition text-base"
          >
            🔍 搜尋
          </button>
          <button
            onClick={() => navigate('/reports')}
            className="bg-white border border-navy text-navy py-3 rounded-lg font-medium hover:bg-cyan transition text-base"
          >
            📈 報表
          </button>
        </div>

        <div className="border-t border-slate-200 pt-6 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-soft">帳號</span>
            <span className="font-mono text-ink">{user.username}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-soft">姓名</span>
            <span className="text-ink">{user.display_name ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-soft">角色</span>
            <span className="text-teal font-medium">{ROLE_LABEL[user.role]}</span>
          </div>
          {user.last_login_at && (
            <div className="flex justify-between">
              <span className="text-soft">上次登入</span>
              <span className="font-mono text-xs text-soft">
                {user.last_login_at}
              </span>
            </div>
          )}
        </div>

        <div className="mt-6 pt-6 border-t border-slate-200 flex gap-3 text-xs">
          <a href="/api/docs" className="text-teal hover:underline">
            📖 API 文件
          </a>
          <a href="/api/auth/me" className="text-teal hover:underline">
            🔑 /auth/me
          </a>
        </div>
      </div>
    </div>
  );
}
