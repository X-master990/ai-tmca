import { useQuery } from '@tanstack/react-query';

interface HealthResp {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  db: { ok: boolean; message: string };
}

async function fetchHealth(): Promise<HealthResp> {
  const r = await fetch('/api/health');
  if (!r.ok) throw new Error('健康檢查失敗');
  return r.json();
}

export default function App() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 5000,
  });

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🎵</div>
          <h1 className="text-3xl font-bold text-navy">TMCA</h1>
          <div className="text-sm text-soft mt-2">音樂著作公開演出授權系統</div>
          <div className="text-xs text-slate-400 mt-1">社團法人台灣音樂著作權集體管理協會</div>
        </div>

        <div className="bg-cyan/30 rounded-lg p-5 mb-6">
          <div className="text-xs uppercase tracking-wide text-soft mb-2">Phase 0 · 專案骨架</div>
          <div className="text-sm text-ink">
            專案骨架已建置完成。下一步：Phase 1 認證 + 4 角色登入。
          </div>
        </div>

        <div className="border-t border-slate-200 pt-6">
          <h2 className="text-sm font-semibold text-navy mb-3">後端連線狀態</h2>
          {isLoading && <div className="text-soft">檢查中…</div>}
          {error && <div className="text-warn">無法連線到 /api/health：{String(error)}</div>}
          {data && (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-soft">服務</span>
                <span className="font-mono text-ink">{data.service} v{data.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-soft">狀態</span>
                <span className={data.status === 'ok' ? 'text-ok font-medium' : 'text-warn font-medium'}>
                  {data.status === 'ok' ? '● 正常' : '● 降級'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-soft">資料庫</span>
                <span className={data.db.ok ? 'text-ok font-medium' : 'text-warn font-medium'}>
                  {data.db.ok ? '● 連線' : `● ${data.db.message}`}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-soft">時間戳</span>
                <span className="font-mono text-xs text-soft">{data.timestamp}</span>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 pt-6 border-t border-slate-200 flex gap-3 text-xs">
          <a href="/api/docs" className="text-teal hover:underline">📖 API 文件</a>
          <a href="/api/health" className="text-teal hover:underline">🩺 Health 端點</a>
          <a href="/api/" className="text-teal hover:underline">🏠 API 首頁</a>
        </div>
      </div>
    </div>
  );
}
