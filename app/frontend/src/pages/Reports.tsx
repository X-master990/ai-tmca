import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { fetchReportSummary, ReportSummary } from '../api/reports';

const PALETTE = [
  '#0F3057', '#008891', '#C5832B', '#27ae60', '#C0392B', '#3D3D52',
  '#E0F0F2', '#7E57C2', '#FB8C00', '#5E35B1', '#6D4C41', '#43A047',
];

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <div className="text-xs text-soft uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-bold text-navy">{value}</div>
      {sub && <div className="text-xs text-soft mt-1">{sub}</div>}
    </div>
  );
}

function MonthlyBarChart({ monthly }: { monthly: ReportSummary['monthly'] }) {
  const max = Math.max(1, ...monthly.map((m) => m.issued_count));
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <div className="font-bold text-navy mb-3">每月核發數</div>
      <div className="flex items-end gap-2 h-40">
        {monthly.map((m) => {
          const h = (m.issued_count / max) * 100;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-xs font-mono text-soft h-4">
                {m.issued_count || ''}
              </div>
              <div
                className="w-full bg-teal rounded-t transition-all"
                style={{ height: `${h}%`, minHeight: m.issued_count ? 2 : 0 }}
                title={`${m.month} 月：${m.issued_count} 筆 · $${m.amount_sum.toLocaleString()}`}
              />
              <div className="text-xs text-soft">{m.month}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MonthlyAmountChart({ monthly }: { monthly: ReportSummary['monthly'] }) {
  const max = Math.max(1, ...monthly.map((m) => m.amount_sum));
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <div className="font-bold text-navy mb-3">每月收入</div>
      <div className="flex items-end gap-2 h-40">
        {monthly.map((m) => {
          const h = (m.amount_sum / max) * 100;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-xxs font-mono text-soft h-4">
                {m.amount_sum ? Math.round(m.amount_sum / 1000) + 'k' : ''}
              </div>
              <div
                className="w-full bg-gold rounded-t transition-all"
                style={{ height: `${h}%`, minHeight: m.amount_sum ? 2 : 0 }}
                title={`${m.month} 月：$${m.amount_sum.toLocaleString()}`}
              />
              <div className="text-xs text-soft">{m.month}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CategoryBars({ rows }: { rows: ReportSummary['by_category'] }) {
  const max = Math.max(1, ...rows.map((r) => r.issued_count));
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <div className="font-bold text-navy mb-3">各 category 核發數（年度）</div>
      <div className="space-y-2">
        {rows.map((r, i) => {
          const w = (r.issued_count / max) * 100;
          return (
            <div key={r.code} className="flex items-center gap-2 text-xs">
              <div className="w-32 text-right text-soft truncate">{r.name_zh}</div>
              <div className="flex-1 bg-slate-100 rounded h-5 overflow-hidden">
                <div
                  className="h-full flex items-center px-2 text-white text-xxs font-mono"
                  style={{
                    width: `${w}%`,
                    background: PALETTE[i % PALETTE.length],
                    minWidth: r.issued_count > 0 ? 28 : 0,
                  }}
                >
                  {r.issued_count > 0 ? r.issued_count : ''}
                </div>
              </div>
              <div className="w-20 text-right font-mono text-soft">
                ${r.amount_sum.toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RenewalCard({ renewal }: { renewal: ReportSummary['renewal'] }) {
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <div className="font-bold text-navy mb-3">續約率（本年到期）</div>
      <div className="text-4xl font-bold text-ok mb-2">
        {renewal.rate_percent === null ? '—' : `${renewal.rate_percent}%`}
      </div>
      <div className="text-xs text-soft space-y-1">
        <div>🟢 已續約：{renewal.renewed}</div>
        <div>🔴 未續約：{renewal.unrenewed}</div>
        <div>⚪ 其他：{renewal.other}</div>
      </div>
    </div>
  );
}

const ALLOWED_ROLES = new Set(['accountant', 'admin']);

export default function Reports() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const allowed = !!user && ALLOWED_ROLES.has(user.role);
  const [year, setYear] = useState(new Date().getFullYear());
  const [data, setData] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    let alive = true;
    setLoading(true);
    fetchReportSummary(year)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : '載入失敗'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [year, allowed]);

  if (!allowed) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-10">
        <div className="text-warn font-medium">⚠ 報表僅供會計 / admin 使用</div>
        <div className="text-soft text-sm">目前角色：{user?.role ?? '—'}</div>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-navy text-white rounded-lg hover:bg-teal">
          回首頁
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-soft hover:text-navy text-sm">
            ← 首頁
          </button>
          <h1 className="text-lg font-bold text-navy">📈 報表</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span>年份：</span>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value, 10) || year)}
            className="w-24 px-2 py-1 border border-slate-300 rounded text-sm"
          />
          <span className="text-soft">
            {user?.display_name} · <span className="text-teal">{user?.role}</span>
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 bg-slate-50">
        {loading && <div className="text-center text-soft py-10">載入中…</div>}
        {error && <div className="text-warn py-10 text-center">{error}</div>}
        {data && !loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                label={`${year} 年核發數`}
                value={data.totals.issued_this_year.toLocaleString()}
                sub={`歷史合計 ${data.totals.total_records.toLocaleString()} 筆`}
              />
              <StatCard
                label={`${year} 年收入`}
                value={`$${data.totals.amount_this_year.toLocaleString()}`}
              />
              <StatCard
                label="核發狀態（全部）"
                value={`${data.issuance.issued.toLocaleString()}`}
                sub={`已核發 / 待補 ${data.issuance.pending.toLocaleString()}`}
              />
              <StatCard
                label="續約率"
                value={data.renewal.rate_percent === null ? '—' : `${data.renewal.rate_percent}%`}
                sub={`${data.renewal.renewed} 綠 / ${data.renewal.unrenewed} 紅`}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <MonthlyBarChart monthly={data.monthly} />
              <MonthlyAmountChart monthly={data.monthly} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <CategoryBars rows={data.by_category} />
              </div>
              <RenewalCard renewal={data.renewal} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
