import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { PendingIssuance, fetchCertData, generateCert } from '../api/issuance';
import { downloadBlob } from '../api/invoices';
import { ApiError } from '../api/client';

interface Props {
  record: PendingIssuance;
  onClose: () => void;
  onIssued: (recordId: number) => void; // 產出後通知父層（移除該列）
}

// 多行欄位（曲目/地址類）用 textarea
const MULTILINE = new Set(['曲目', '演出曲目', '使用地址', '營業地址', '地點地址', '網址']);

export default function CertModal({ record, onClose, onIssued }: Props) {
  const [fields, setFields] = useState<{ name: string; value: string }[]>([]);
  const [markIssued, setMarkIssued] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  // callback ref：第一個欄位不論 input/textarea 都掛得上（供載入後自動聚焦）
  const setFirst = useCallback((el: HTMLInputElement | HTMLTextAreaElement | null) => {
    firstRef.current = el;
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchCertData(record.id)
      .then((d) => alive && setFields(d.fields))
      .catch((e) => alive && setError(e instanceof ApiError ? e.detail : '載入證書欄位失敗'))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [record.id]);

  useEffect(() => {
    if (!loading) firstRef.current?.focus();
  }, [loading]);

  function setVal(name: string, v: string) {
    setFields((prev) => prev.map((f) => (f.name === name ? { ...f, value: v } : f)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const payload = {
        fields: Object.fromEntries(fields.map((f) => [f.name, f.value])),
        mark_issued: markIssued,
      };
      const { blob, filename } = await generateCert(record.id, payload);
      downloadBlob(blob, filename);
      onIssued(record.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : '產生證書失敗');
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
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <form
        onSubmit={onSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cert-modal-title"
        className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-2xl my-8"
      >
        <div className="flex justify-between items-center mb-1">
          <h2 id="cert-modal-title" className="text-xl font-bold text-navy">
            📄 產生證書
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
          {record.holder_name ?? record.cert_no ?? `#${record.id}`} ·
          以下欄位已自動帶入，可直接修改 —— 所見即所印。確認後下載證書 Word。
        </p>

        {loading ? (
          <div className="py-12 text-center text-soft">載入證書欄位中…</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4">
              {fields.map((f, i) => {
                const multiline = MULTILINE.has(f.name);
                return (
                  <div key={f.name} className={multiline ? 'col-span-2' : ''}>
                    <label className={labelCls}>{f.name}</label>
                    {multiline ? (
                      <textarea
                        ref={i === 0 ? setFirst : undefined}
                        rows={2}
                        className={inputCls}
                        value={f.value}
                        onChange={(e) => setVal(f.name, e.target.value)}
                      />
                    ) : (
                      <input
                        ref={i === 0 ? setFirst : undefined}
                        className={inputCls}
                        value={f.value}
                        onChange={(e) => setVal(f.name, e.target.value)}
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <label className="flex items-center gap-2 mt-5 text-sm text-ink">
              <input
                type="checkbox"
                checked={markIssued}
                onChange={(e) => setMarkIssued(e.target.checked)}
              />
              產出後標記為「已核發（綠）」
            </label>

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
                {busy ? '產生中…' : '⬇ 下載證書 Word'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
