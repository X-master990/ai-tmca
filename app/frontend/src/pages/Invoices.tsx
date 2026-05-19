import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Category, fetchCategories } from '../api/records';
import {
  PendingInvoice,
  downloadBlob,
  fetchPendingInvoices,
  generateInvoices,
} from '../api/invoices';
import { useAuthStore } from '../store/auth';

const FMT = new Intl.NumberFormat('zh-Hant-TW');

export default function Invoices() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<PendingInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [categoryCode, setCategoryCode] = useState<string>('');
  const [filterQ, setFilterQ] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [invoiceType, setInvoiceType] = useState<'二聯式' | '三聯式'>('二聯式');
  const [issuing, setIssuing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const allowed = user?.role === 'admin' || user?.role === 'accountant';

  useEffect(() => {
    if (!allowed) return;
    fetchCategories()
      .then(setCategories)
      .catch((e) => setError(e instanceof Error ? e.message : '載入類型失敗'));
  }, [allowed]);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchPendingInvoices({
        category_code: categoryCode || undefined,
        q: filterQ.trim() || undefined,
      });
      setItems(rows);
      setSelectedIds((prev) => {
        const next = new Set<number>();
        const ids = new Set(rows.map((r) => r.id));
        prev.forEach((id) => {
          if (ids.has(id)) next.add(id);
        });
        return next;
      });
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

  // 客戶端模糊搜尋（在已抓回來的資料上即時過濾，避免每打一字就打 API）
  const visible = useMemo(() => {
    if (!filterQ.trim()) return items;
    const q = filterQ.trim().toLowerCase();
    return items.filter((r) =>
      [r.holder_name, r.invoice_title, r.tax_id, r.note, r.product]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q)),
    );
  }, [items, filterQ]);

  const totalAmount = useMemo(
    () => visible.filter((r) => selectedIds.has(r.id)).reduce((sum, r) => sum + (r.amount ?? 0), 0),
    [visible, selectedIds],
  );

  function toggleOne(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleAll() {
    setSelectedIds((prev) => {
      const allSel = visible.every((r) => prev.has(r.id));
      const next = new Set(prev);
      if (allSel) visible.forEach((r) => next.delete(r.id));
      else visible.forEach((r) => next.add(r.id));
      return next;
    });
  }

  async function handleIssue() {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (!window.confirm(
      `將為 ${ids.length} 筆紀錄配發發票號並下載 Excel。\n發票型式：${invoiceType}\n總金額（含稅）：${FMT.format(totalAmount)}\n\n此動作會直接寫入發票號（無法退回），確定？`,
    )) return;

    setIssuing(true);
    setMsg(null);
    try {
      const result = await generateInvoices({
        record_ids: ids,
        invoice_type: invoiceType,
      });
      downloadBlob(result.blob, result.filename);
      setMsg(`✅ 已開 ${result.count} 張：${result.firstNo} ~ ${result.lastNo}`);
      setSelectedIds(new Set());
      await reload();
    } catch (e) {
      setMsg(`❌ ${e instanceof Error ? e.message : '開立失敗'}`);
    } finally {
      setIssuing(false);
    }
  }

  if (!allowed) {
    return (
      <div className="p-10 text-warn">
        無權限（僅 admin / accountant）
        <button onClick={() => navigate('/')} className="ml-4 text-teal underline">回首頁</button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* 頂列 */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-soft hover:text-navy text-sm">← 首頁</button>
        <h1 className="text-lg font-bold text-navy">🧾 開立發票</h1>
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
              <option key={c.code} value={c.code}>{c.name_zh}</option>
            ))}
          </select>
        </label>

        <input
          type="text"
          value={filterQ}
          onChange={(e) => setFilterQ(e.target.value)}
          placeholder="🔍 抬頭 / 持證者 / 統編 / 備註"
          className="flex-1 min-w-[200px] px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-teal"
        />

        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-soft">發票型式</span>
          <select
            value={invoiceType}
            onChange={(e) => setInvoiceType(e.target.value as '二聯式' | '三聯式')}
            className="border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-teal"
          >
            <option value="二聯式">二聯式</option>
            <option value="三聯式">三聯式</option>
          </select>
        </label>

        <div className="text-xs text-soft">
          共 <span className="font-mono text-ink">{visible.length}</span> 筆 ·
          已選 <span className="font-mono text-ink">{selectedIds.size}</span> ·
          合計（含稅）<span className="font-mono text-ink">{FMT.format(totalAmount)}</span>
        </div>

        <button
          disabled={issuing || selectedIds.size === 0}
          onClick={handleIssue}
          className="px-4 py-1.5 bg-teal text-white text-sm rounded font-medium hover:bg-navy disabled:bg-slate-300 disabled:cursor-not-allowed transition"
        >
          {issuing ? '⏳ 開立中…' : `🧾 開立發票 (${selectedIds.size})`}
        </button>
      </div>

      {msg && (
        <div className="px-6 py-2 text-xs bg-cyan/30 border-b border-slate-200">{msg}</div>
      )}
      {error && (
        <div className="px-6 py-2 text-xs bg-red-50 text-warn border-b border-slate-200">{error}</div>
      )}

      {/* 表格 */}
      <div className="flex-1 overflow-auto p-4">
        <div className="bg-white rounded shadow-sm overflow-hidden">
          <table className="w-full text-sm border-collapse">
            <thead className="bg-cyan sticky top-0 z-10">
              <tr>
                <th className="px-2 py-2 text-center font-semibold text-navy border-b border-slate-200 w-10">
                  <input
                    type="checkbox"
                    checked={visible.length > 0 && visible.every((r) => selectedIds.has(r.id))}
                    onChange={toggleAll}
                    title="全選 / 全消"
                  />
                </th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-20">發票型式</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200">抬頭</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-28">統一編號</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200 w-44">品名</th>
                <th className="px-3 py-2 text-right font-semibold text-navy border-b border-slate-200 w-24">未稅單價</th>
                <th className="px-3 py-2 text-right font-semibold text-navy border-b border-slate-200 w-24">總金額</th>
                <th className="px-3 py-2 text-left font-semibold text-navy border-b border-slate-200">備註</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-soft">載入中…</td></tr>
              )}
              {!loading && visible.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-soft">沒有待開發票的紀錄</td></tr>
              )}
              {!loading && visible.map((r, i) => (
                <tr
                  key={r.id}
                  onClick={() => toggleOne(r.id)}
                  className={`cursor-pointer hover:bg-cyan/30 ${
                    selectedIds.has(r.id) ? 'bg-cyan/50' : i % 2 ? 'bg-slate-50' : ''
                  }`}
                >
                  <td className="px-2 py-1.5 text-center border-b border-slate-100">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(r.id)}
                      onChange={() => toggleOne(r.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td className="px-3 py-1.5 border-b border-slate-100">{r.invoice_type}</td>
                  <td className="px-3 py-1.5 border-b border-slate-100 truncate" title={r.invoice_title ?? ''}>
                    {r.invoice_title || <span className="text-soft">—</span>}
                  </td>
                  <td className="px-3 py-1.5 border-b border-slate-100 font-mono text-xs">
                    {r.tax_id || <span className="text-soft">—</span>}
                  </td>
                  <td className="px-3 py-1.5 border-b border-slate-100 text-xs">{r.product}</td>
                  <td className="px-3 py-1.5 border-b border-slate-100 text-right font-mono">
                    {FMT.format(r.untaxed_unit_price)}
                  </td>
                  <td className="px-3 py-1.5 border-b border-slate-100 text-right font-mono font-medium">
                    {FMT.format(r.amount ?? 0)}
                  </td>
                  <td className="px-3 py-1.5 border-b border-slate-100 text-xs text-soft truncate" title={r.note ?? ''}>
                    {r.note || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
