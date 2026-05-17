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

        <div className="bg-cyan/30 rounded-lg p-5 mb-6">
          <div className="text-xs uppercase tracking-wide text-soft mb-2">
            Phase 1 · 認證完成
          </div>
          <div className="text-sm text-ink">
            登入成功。下一步：Phase 2 將匯入 110-115 年總表，Phase 3 開啟類 Excel
            介面。
          </div>
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
