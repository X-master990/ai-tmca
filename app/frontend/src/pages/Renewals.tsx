import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { RecordRow } from '../api/records';
import {
  fetchRenewals,
  recomputeRenewals,
  generateRenewal,
  RenewalListResponse,
} from '../api/renewals';
import StatusDot from '../components/StatusDot';

const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

function MiniRow({
  r,
  onGenerate,
  busy,
}: {
  r: RecordRow;
  onGenerate?: (r: RecordRow) => void;
  busy?: boolean;
}) {
  return (
    <tr className="border-b border-slate-100 hover:bg-cyan/30">
      <td className="px-2 py-1 font-mono text-xs">{r.cert_no || '—'}</td>
      <td className="px-2 py-1">{r.holder_name || '—'}</td>
      <td className="px-2 py-1 text-xs">{r.tax_id || '—'}</td>
      <td className="px-2 py-1 font-mono text-xs">{r.period_end}</td>
      <td className="px-2 py-1 text-xs">{r.officer || '—'}</td>
      <td className="px-2 py-1 text-xs">{r.applicant_mobile || r.applicant_phone || '—'}</td>
      {onGenerate && (
        <td className="px-2 py-1 text-xs text-center">
          <button
            onClick={() => onGenerate(r)}
            disabled={busy}
            className="px-2 py-0.5 bg-teal text-white rounded text-xs hover:bg-navy disabled:opacity-50 transition whitespace-nowrap"
            title="自動建立一筆「續約」紀錄（期間自舊到期次日起算一年，迄日可改）"
          >
            {busy ? '⏳' : '＋ 生成續約行'}
          </button>
        </td>
      )}
    </tr>
  );
}

const ALLOWED_ROLES = new Set(['officer_a', 'officer_b', 'admin']);

export default function Renewals() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const allowed = !!user && ALLOWED_ROLES.has(user.role);
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [data, setData] = useState<RenewalListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recomputeMsg, setRecomputeMsg] = useState<string | null>(null);
  const [genBusyId, setGenBusyId] = useState<number | null>(null);

  async function handleGenerate(r: RecordRow) {
    if (
      !window.confirm(
        `生成續約行？\n${r.holder_name ?? r.cert_no ?? ''}（到期 ${r.period_end}）\n\n` +
          '系統會新建一筆「續約」紀錄：授權期間自舊到期日次日起算、預設一年（迄日可改），' +
          '並帶入聯絡/地址/抬頭等資料。金額、證書編號、發票需之後在總表補。',
      )
    )
      return;
    setGenBusyId(r.id);
    setRecomputeMsg(null);
    try {
      const nw = await generateRenewal(r.id);
      setRecomputeMsg(
        `✅ 已生成續約行 id=${nw.id}（授權 ${nw.period_start} ~ ${nw.period_end}）。請至總表補金額/證書編號。`,
      );
      await load(month, year); // 重載：舊筆已轉「已續約」移出本名單
    } catch (e) {
      setRecomputeMsg(e instanceof Error ? `❌ ${e.message}` : '生成失敗');
    } finally {
      setGenBusyId(null);
    }
  }

  async function load(m: number, y: number) {
    setLoading(true);
    setError(null);
    try {
      const r = await fetchRenewals(m, y);
      setData(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!allowed) return;
    load(month, year);
  }, [month, year, allowed]);

  async function doRecompute() {
    setRecomputeMsg('計算中…');
    try {
      const r = await recomputeRenewals();
      setRecomputeMsg(
        `✅ 已更新 ${r.rows_updated} 筆 / ${r.elapsed_seconds}s · ${JSON.stringify(r.breakdown)}`,
      );
      await load(month, year);
    } catch (e) {
      setRecomputeMsg(e instanceof Error ? `❌ ${e.message}` : '失敗');
    }
  }

  if (!allowed) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-10">
        <div className="text-warn font-medium">⚠ 續約管理僅供承辦 / admin 使用</div>
        <div className="text-soft text-sm">目前角色：{user?.role ?? '—'}</div>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-navy text-white rounded-lg hover:bg-teal">
          回首頁
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-soft hover:text-navy text-sm"
          >
            ← 首頁
          </button>
          <h1 className="text-lg font-bold text-navy">🔁 續約管理</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {user?.role === 'admin' && (
            <button
              onClick={doRecompute}
              className="px-3 py-1.5 bg-teal text-white rounded text-xs hover:bg-navy"
              title="手動觸發續約狀態重算"
            >
              🔄 重新計算
            </button>
          )}
          <span className="text-soft">
            {user?.display_name} · <span className="text-teal">{user?.role}</span>
          </span>
        </div>
      </div>

      {recomputeMsg && (
        <div className="bg-cream px-6 py-2 text-xs text-soft border-b border-slate-200">
          {recomputeMsg}
        </div>
      )}

      {/* Year + Month controls */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-3">
        <span className="text-sm text-soft">年份：</span>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(parseInt(e.target.value, 10) || year)}
          className="w-24 px-2 py-1 border border-slate-300 rounded text-sm"
        />
        <span className="text-sm text-soft ml-4">月份：</span>
        <div className="flex flex-wrap gap-1">
          {MONTHS.map((m) => (
            <button
              key={m}
              onClick={() => setMonth(m)}
              className={`px-3 py-1.5 text-xs rounded transition ${
                month === m
                  ? 'bg-navy text-white'
                  : 'bg-slate-100 text-soft hover:bg-cyan'
              }`}
            >
              {m}月
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto px-6 py-4 bg-slate-50">
        {loading && <div className="text-soft py-10 text-center">載入中…</div>}
        {error && <div className="text-warn py-10 text-center">錯誤：{error}</div>}
        {data && !loading && (
          <>
            <div className="mb-4 text-sm text-soft">
              {data.year} 年 {data.month} 月到期合計{' '}
              <span className="font-mono text-ink">{data.summary.total}</span> 筆 ·
              <StatusDot value="紅" />{' '}
              <span className="text-warn font-medium">未續約 {data.summary.未續約}</span> ·
              <StatusDot value="綠" />{' '}
              <span className="text-ok font-medium">已續約 {data.summary.已續約}</span>
              {data.summary.其他 > 0 && (
                <>
                  {' '}·  <StatusDot value="灰" /> 其他 {data.summary.其他}
                </>
              )}
            </div>

            {/* 未續約 */}
            <div className="bg-white rounded-lg shadow-sm border border-red-200 mb-6">
              <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2 rounded-t-lg">
                <StatusDot value="紅" />
                <span className="font-bold text-warn">
                  未續約名單（{data.unrenewed.length}）
                </span>
              </div>
              {data.unrenewed.length === 0 ? (
                <div className="px-4 py-6 text-sm text-soft text-center">無</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-soft">
                    <tr>
                      <th className="px-2 py-2 text-left">證書編號</th>
                      <th className="px-2 py-2 text-left">持證者</th>
                      <th className="px-2 py-2 text-left">統一編號</th>
                      <th className="px-2 py-2 text-left">到期日</th>
                      <th className="px-2 py-2 text-left">承辦</th>
                      <th className="px-2 py-2 text-left">聯絡</th>
                      <th className="px-2 py-2 text-center">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.unrenewed.map((r) => (
                      <MiniRow
                        key={r.id}
                        r={r}
                        onGenerate={handleGenerate}
                        busy={genBusyId === r.id}
                      />
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* 已續約 */}
            <div className="bg-white rounded-lg shadow-sm border border-green-200">
              <div className="bg-green-50 border-b border-green-200 px-4 py-2 flex items-center gap-2 rounded-t-lg">
                <StatusDot value="綠" />
                <span className="font-bold text-ok">
                  已續約名單（{data.renewed.length}）
                </span>
              </div>
              {data.renewed.length === 0 ? (
                <div className="px-4 py-6 text-sm text-soft text-center">無</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-soft">
                    <tr>
                      <th className="px-2 py-2 text-left">證書編號</th>
                      <th className="px-2 py-2 text-left">持證者</th>
                      <th className="px-2 py-2 text-left">統一編號</th>
                      <th className="px-2 py-2 text-left">到期日</th>
                      <th className="px-2 py-2 text-left">承辦</th>
                      <th className="px-2 py-2 text-left">聯絡</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.renewed.map((r) => (
                      <MiniRow key={r.id} r={r} />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
