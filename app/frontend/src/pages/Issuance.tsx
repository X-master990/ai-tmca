import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Category, fetchCategories } from '../api/records';
import { PendingIssuance, fetchPendingIssuance } from '../api/issuance';
import CertModal from '../components/CertModal';
import { useAuthStore } from '../store/auth';

export default function Issuance() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const allowed = user?.role === 'issuer' || user?.role === 'admin';

  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<PendingIssuance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryCode, setCategoryCode] = useState('');
  const [filterQ, setFilterQ] = useState('');
  const [certFor, setCertFor] = useState<PendingIssuance | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const catName = useMemo(() => {
    const m: Record<string, string> = {};
    categories.forEach((c) => (m[c.code] = c.name_zh));
    return m;
  }, [categories]);

  useEffect(() => {
    if (!allowed) return;
    fetchCategories()
      .then(setCategories)
      .catch(() => {});
  }, [allowed]);

  async function reload() {
    setLoading(true);
    setError(null);
    setMsg(null); // 換類型/重載時清掉舊的成功提示，避免常駐誤導
    try {
      const rows = await fetchPendingIssuance({ category_code: categoryCode || undefined });
      setItems(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!allowed) return;
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryCode, allowed]);

  // 客戶端模糊過濾（在已抓回的資料上）
  const visible = useMemo(() => {
    if (!filterQ.trim()) return items;
    const q = filterQ.trim().toLowerCase();
    return items.filter((r) =>
      [r.holder_name, r.cert_no, r.use_address]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q)),
    );
  }, [items, filterQ]);

  function handleIssued(recordId: number) {
    setCertFor(null);
    setItems((prev) => prev.filter((r) => r.id !== recordId)); // 已轉綠 → 移出待核發
    setMsg('✅ 已產出證書並標記為已核發（綠）。');
  }

  if (!allowed) {
    return (
      <div className="p-10 text-warn">
        無權限（僅 核發 / admin）
        <button onClick={() => navigate('/')} className="ml-4 text-teal underline">
          回首頁
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* 頂列 */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-soft hover:text-navy text-sm">
          ← 首頁
        </button>
        <h1 className="text-lg font-bold text-navy">📑 核發證書</h1>
        <div className="text-xs text-soft ml-auto">
          {user?.display_name} · <span className="text-teal">{user?.role}</span>
        </div>
      </div>

      {/* 工具列 */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-soft">類型</span>
          <select
            value={categoryCode}
            onChange={(e) => setCategoryCode(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-teal"
          >
            <option value="">全部</option>
            {categories.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name_zh}
              </option>
            ))}
          </select>
        </label>

        <input
          type="text"
          value={filterQ}
          onChange={(e) => setFilterQ(e.target.value)}
          placeholder="🔍 持證者 / 證號 / 地址"
          className="flex-1 min-w-[200px] px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-teal"
        />

        <div className="text-xs text-soft">
          待核發 <span className="font-mono text-ink">{visible.length}</span> 筆
        </div>
      </div>

      {msg && <div className="px-6 py-2 text-xs bg-cyan/30 border-b border-slate-200">{msg}</div>}
      {error && (
        <div className="px-6 py-2 text-xs bg-red-50 text-warn border-b border-slate-200">{error}</div>
      )}

      {/* 表格 */}
      <div className="flex-1 overflow-auto p-4">
        <div className="bg-white rounded shadow-sm overflow-hidden">
          <table className="w-full text-sm border-collapse">
            <thead className="bg-cyan sticky top-0 z-10">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-32">類型</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-28">證號</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200">持證者</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200">使用地址</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-40">授權期間</th>
                <th className="px-3 py-2 text-center font-semibold text-navy border-b border-slate-200 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-soft">載入中…</td>
                </tr>
              )}
              {!loading && visible.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-soft">沒有待核發的紀錄</td>
                </tr>
              )}
              {!loading &&
                visible.map((r, i) => (
                  <tr key={r.id} className={i % 2 ? 'bg-slate-50' : ''}>
                    <td className="px-3 py-1.5 border-b border-slate-100 text-xs">
                      {catName[r.category_code] || r.category_code}
                    </td>
                    <td className="px-3 py-1.5 border-b border-slate-100 font-mono text-xs">
                      {r.cert_no || <span className="text-soft">—</span>}
                    </td>
                    <td className="px-3 py-1.5 border-b border-slate-100 truncate" title={r.holder_name ?? ''}>
                      {r.holder_name || <span className="text-soft">—</span>}
                    </td>
                    <td className="px-3 py-1.5 border-b border-slate-100 text-xs text-soft truncate" title={r.use_address ?? ''}>
                      {r.use_address || '—'}
                    </td>
                    <td className="px-3 py-1.5 border-b border-slate-100 font-mono text-xs">
                      {r.period_start || '—'} ~ {r.period_end || '—'}
                    </td>
                    <td className="px-3 py-1.5 border-b border-slate-100 text-center">
                      {r.has_cert ? (
                        <button
                          onClick={() => setCertFor(r)}
                          className="px-2 py-0.5 bg-teal text-white rounded text-xs hover:bg-navy transition whitespace-nowrap"
                          title="填證書資料並下載 Word（正面）"
                        >
                          📄 產證書
                        </button>
                      ) : (
                        <span className="text-xs text-soft" title="此類別無對應正面證書模板">
                          無證書模板
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {certFor && (
        <CertModal record={certFor} onClose={() => setCertFor(null)} onIssued={handleIssued} />
      )}
    </div>
  );
}
