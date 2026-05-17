import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import {
  search,
  searchAgents,
  SearchResponse,
  AgentsResponse,
} from '../api/search';
import { RecordRow } from '../api/records';
import StatusDot from '../components/StatusDot';

type Mode = 'global' | 'agents';

function RecordCard({ r }: { r: RecordRow }) {
  return (
    <div className="border border-slate-200 rounded p-3 text-xs bg-white hover:bg-cyan/20">
      <div className="flex justify-between mb-1">
        <span className="font-mono font-bold text-navy">{r.cert_no || '—'}</span>
        <span className="text-soft">{r.category_code}</span>
      </div>
      <div className="text-sm font-medium text-ink mb-1">{r.holder_name}</div>
      <div className="text-soft">
        {r.invoice_title && <>發票：{r.invoice_title} · </>}
        {r.tax_id && <>統編：{r.tax_id} · </>}
        {r.amount !== null && <>金額：${r.amount.toLocaleString()}</>}
      </div>
      <div className="text-soft mt-1">
        {r.use_address && <>📍 {r.use_address}</>}
      </div>
      <div className="flex gap-3 mt-2 text-xxs items-center">
        <span>核發 <StatusDot value={r.issuance_status} size={8} /></span>
        <span>續約 <StatusDot value={r.renewal_status} size={8} /></span>
        {r.period_end && <span className="text-soft">到期 {r.period_end}</span>}
      </div>
    </div>
  );
}

export default function SearchPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [mode, setMode] = useState<Mode>('global');
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [agentResult, setAgentResult] = useState<AgentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setAgentResult(null);
    try {
      if (mode === 'global') {
        setResult(await search(q.trim()));
      } else {
        setAgentResult(await searchAgents(q.trim()));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '搜尋失敗');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-soft hover:text-navy text-sm">
            ← 首頁
          </button>
          <h1 className="text-lg font-bold text-navy">🔍 搜尋</h1>
        </div>
        <span className="text-sm text-soft">
          {user?.display_name} · <span className="text-teal">{user?.role}</span>
        </span>
      </div>

      {/* Mode tabs */}
      <div className="bg-white border-b border-slate-200 px-6 py-2 flex gap-2">
        <button
          onClick={() => { setMode('global'); setResult(null); setAgentResult(null); }}
          className={`px-3 py-1.5 text-sm rounded transition ${
            mode === 'global' ? 'bg-navy text-white' : 'text-soft hover:bg-cyan'
          }`}
        >
          全域搜尋
        </button>
        <button
          onClick={() => { setMode('agents'); setResult(null); setAgentResult(null); }}
          className={`px-3 py-1.5 text-sm rounded transition ${
            mode === 'agents' ? 'bg-navy text-white' : 'text-soft hover:bg-cyan'
          }`}
        >
          代辦人查詢
        </button>
      </div>

      {/* Search bar */}
      <form onSubmit={onSubmit} className="bg-white border-b border-slate-200 px-6 py-3 flex gap-2">
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={
            mode === 'global'
              ? '證書編號 / 持證者 / 統編 / 發票號碼 / 地址 / 承辦人...'
              : '輸入代辦人姓名（申請人欄）'
          }
          className="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-teal"
        />
        <button
          type="submit"
          disabled={loading || !q.trim()}
          className="px-4 py-2 bg-navy text-white rounded font-medium hover:bg-teal disabled:opacity-50"
        >
          {loading ? '搜尋中...' : '搜尋'}
        </button>
      </form>

      <div className="flex-1 overflow-auto px-6 py-4 bg-slate-50">
        {error && <div className="text-warn py-4">{error}</div>}

        {/* Global search results */}
        {mode === 'global' && result && (
          <div>
            <div className="mb-4 text-sm text-soft">
              找到 <span className="font-mono text-ink font-bold">{result.total}</span> 筆
              {Object.keys(result.by_category).length > 0 && (
                <>
                  ：{Object.entries(result.by_category)
                    .sort((a, b) => b[1] - a[1])
                    .map(([code, n]) => `${code} ${n}`)
                    .join(' · ')}
                </>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {result.results.map((r) => (
                <RecordCard key={r.id} r={r} />
              ))}
            </div>
            {result.total === 0 && (
              <div className="py-10 text-center text-soft">無結果</div>
            )}
          </div>
        )}

        {/* Agent search results */}
        {mode === 'agents' && agentResult && (
          <div>
            <div className="mb-4 text-sm text-soft">
              代辦人「<span className="font-medium text-ink">{agentResult.query_name}</span>」找到{' '}
              <span className="font-mono font-bold text-ink">{agentResult.distinct_holders}</span> 個持證者、共{' '}
              <span className="font-mono font-bold text-ink">{agentResult.total_records}</span> 筆紀錄
            </div>
            <div className="space-y-4">
              {agentResult.groups.map((g) => (
                <div
                  key={`${g.applicant_name}-${g.holder_name}`}
                  className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm"
                >
                  <div className="flex justify-between items-center mb-2">
                    <div>
                      <span className="text-xs text-soft">代辦人</span>{' '}
                      <span className="font-medium">{g.applicant_name}</span>
                      <span className="mx-2 text-soft">→</span>
                      <span className="text-xs text-soft">持證者</span>{' '}
                      <span className="font-medium text-teal">{g.holder_name}</span>
                    </div>
                    <span className="text-xs text-soft">
                      {g.count} 筆 · {g.categories.join(', ')}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {g.records.map((r) => (
                      <RecordCard key={r.id} r={r} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {agentResult.groups.length === 0 && (
              <div className="py-10 text-center text-soft">無結果</div>
            )}
          </div>
        )}

        {!result && !agentResult && !error && !loading && (
          <div className="py-10 text-center text-soft text-sm">
            {mode === 'global'
              ? '輸入關鍵字搜尋。會跨 12 個 category 全欄位查詢。'
              : '輸入代辦人姓名，會列出該人代辦過的所有持證者。'}
          </div>
        )}
      </div>
    </div>
  );
}
