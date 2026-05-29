import { FormEvent, useEffect, useRef, useState } from 'react';
import { RecordRow } from '../api/records';
import {
  RenewalLetterPayload,
  fetchRenewalLetterData,
  generateRenewalLetter,
} from '../api/renewals';
import { downloadBlob } from '../api/invoices';
import { ApiError } from '../api/client';

const UNIT_FEE = 3675; // 電腦伴唱機 每台每年含稅標準費

interface Props {
  record: RecordRow;
  onClose: () => void;
}

const EMPTY: RenewalLetterPayload = {
  recipient: '',
  issue_date: '',
  pay_deadline: '',
  period_start: '',
  period_end: '',
  business_address: '',
  qty: '',
  amount: '',
};

export default function RenewalLetterModal({ record, onClose }: Props) {
  const [form, setForm] = useState<RenewalLetterPayload>({ ...EMPTY, record_id: record.id });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recipientRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchRenewalLetterData(record.id)
      .then((d) => {
        if (!alive) return;
        setForm({
          record_id: d.record_id,
          recipient: d.recipient,
          issue_date: d.issue_date,
          pay_deadline: d.pay_deadline,
          period_start: d.period_start,
          period_end: d.period_end,
          business_address: d.business_address,
          qty: String(d.qty ?? ''),
          amount: String(d.amount ?? ''),
        });
      })
      .catch((e) => alive && setError(e instanceof ApiError ? e.detail : '載入預填資料失敗'))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [record.id]);

  // 載入完成後把焦點移到受文者欄（鍵盤/輔助技術可及性）
  useEffect(() => {
    if (!loading) recipientRef.current?.focus();
  }, [loading]);

  // record_id 為 number，不開放給字串 setter，避免型別陷阱
  function set(key: Exclude<keyof RenewalLetterPayload, 'record_id'>, v: string) {
    setForm((prev) => ({ ...prev, [key]: v }));
  }

  // 依目前台數套用標準費（台數×3675）到應付金額
  function applyStandardFee() {
    const n = parseInt(form.qty, 10);
    if (!Number.isNaN(n) && n > 0) set('amount', String(n * UNIT_FEE));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.recipient.trim()) {
      setError('「受文者」必填');
      return;
    }
    setBusy(true);
    try {
      const { blob, filename } = await generateRenewalLetter(form);
      downloadBlob(blob, filename);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : '產生續約函失敗');
    } finally {
      setBusy(false);
    }
  }

  const labelCls = 'block text-sm text-soft mb-1';
  const inputCls =
    'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal';

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center p-6 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose(); // 點背景遮罩關閉
      }}
    >
      <form
        onSubmit={onSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="renewal-letter-title"
        className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-2xl my-8"
      >
        <div className="flex justify-between items-center mb-2">
          <h2 id="renewal-letter-title" className="text-xl font-bold text-navy">
            📄 生成續約函（電腦伴唱機）
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-soft hover:text-warn text-2xl leading-none"
            aria-label="關閉"
          >
            ×
          </button>
        </div>
        <p className="text-xs text-soft mb-6">
          以下欄位已自動帶入，可直接修改 —— 所見即所印。確認後下載 Word（不會改動總表資料）。
        </p>

        {loading ? (
          <div className="py-12 text-center text-soft">載入預填資料中…</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className={labelCls}>
                  受文者（店名 / 持證者）<span className="text-warn"> *</span>
                </label>
                <input
                  ref={recipientRef}
                  className={inputCls}
                  value={form.recipient}
                  onChange={(e) => set('recipient', e.target.value)}
                  required
                />
              </div>

              <div>
                <label className={labelCls}>發文日期</label>
                <input
                  className={inputCls}
                  value={form.issue_date}
                  onChange={(e) => set('issue_date', e.target.value)}
                  placeholder="例：115年5月29日"
                />
              </div>
              <div>
                <label className={labelCls}>繳費期限</label>
                <input
                  className={inputCls}
                  value={form.pay_deadline}
                  onChange={(e) => set('pay_deadline', e.target.value)}
                  placeholder="例：115年6月30日"
                />
              </div>

              <div>
                <label className={labelCls}>授權起（含「年 月 日」）</label>
                <input
                  className={inputCls}
                  value={form.period_start}
                  onChange={(e) => set('period_start', e.target.value)}
                  placeholder="例：115 年 06 月 01 日"
                />
              </div>
              <div>
                <label className={labelCls}>授權迄</label>
                <input
                  className={inputCls}
                  value={form.period_end}
                  onChange={(e) => set('period_end', e.target.value)}
                  placeholder="例：116 年 05 月 31 日"
                />
              </div>

              <div className="col-span-2">
                <label className={labelCls}>營業地址</label>
                <textarea
                  rows={2}
                  className={inputCls}
                  value={form.business_address}
                  onChange={(e) => set('business_address', e.target.value)}
                />
              </div>

              <div>
                <label className={labelCls}>申報台數</label>
                <input
                  className={inputCls}
                  value={form.qty}
                  onChange={(e) => set('qty', e.target.value)}
                  inputMode="numeric"
                />
              </div>
              <div>
                <label className={labelCls}>
                  應付金額（含稅）
                  <button
                    type="button"
                    onClick={applyStandardFee}
                    className="ml-2 text-xs text-teal underline hover:text-navy"
                    title="依目前台數套用標準費（台數 × 3,675）"
                  >
                    套用 台數×3,675
                  </button>
                </label>
                <input
                  className={inputCls}
                  value={form.amount}
                  onChange={(e) => set('amount', e.target.value)}
                  inputMode="numeric"
                />
              </div>
            </div>

            {error && (
              <div className="mt-4 text-sm text-warn bg-red-50 px-3 py-2 rounded">{error}</div>
            )}

            <div className="mt-6 flex gap-3 justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 border border-slate-300 rounded-lg text-soft hover:bg-slate-50"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={busy}
                className="px-5 py-2 bg-navy text-white rounded-lg font-medium hover:bg-teal disabled:opacity-50"
              >
                {busy ? '產生中…' : '⬇ 下載續約函 Word'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
