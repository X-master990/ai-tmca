import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import {
  Category,
  HolderLookup,
  RecordRow,
  createRecord,
  lookupHolder,
} from '../api/records';
import { PermissionsOut } from '../api/permissions';
import { ApiError } from '../api/client';

// 持證者選定後，這些欄位會從上次紀錄帶入（不含金額/日期/辦理項目/備註等個案專屬欄位）
const REUSABLE_FIELDS = [
  'tax_id',
  'invoice_title',
  'invoice_type',
  'holder_type',
  'use_zip',
  'use_address',
  'mail_zip',
  'mail_address',
  'mail_recipient',
  'mail_phone',
  'applicant_name',
  'applicant_id',
  'applicant_mobile',
  'applicant_phone',
  'applicant_fax',
  'onsite_name',
  'onsite_mobile',
  'onsite_phone',
  'onsite_ext',
  'onsite_fax',
] as const;

// 本地時區的今天 YYYY-MM-DD（避免 toISOString 的 UTC 位移）
function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// 舊到期日（YYYY-MM-DD）的次日 → 新授權期間起算日
function nextDayIso(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

interface Props {
  categories: Category[];
  permissions: PermissionsOut;
  defaultCategory?: string;
  onClose: () => void;
  onCreated: (rec: RecordRow) => void;
}

interface FieldDef {
  key: string;
  label: string;
  type?: 'text' | 'date' | 'number' | 'textarea';
  placeholder?: string;
}

const COMMON_FIELDS: FieldDef[] = [
  // holder_name 在 UI 中已被單獨拉出來（含 autocomplete），這裡不再放
  { key: 'tax_id', label: '統一編號' },
  { key: 'invoice_title', label: '發票抬頭' },
  { key: 'amount', label: '合約金額', type: 'number' },
  { key: 'apply_date', label: '申辦日期', type: 'date' },
  { key: 'period_start', label: '授權起始', type: 'date' },
  { key: 'period_end', label: '授權結束', type: 'date' },
  { key: 'action_type', label: '辦理項目', placeholder: '例：新件 / 續約' },
  { key: 'use_address', label: '營業地址 / 使用地址', type: 'textarea' },
  { key: 'mail_address', label: '寄送地址', type: 'textarea' },
  { key: 'mail_recipient', label: '收件人' },
  { key: 'applicant_name', label: '申請人 / 代辦人' },
  { key: 'qty', label: '台數 / 申報數', type: 'number' },
  { key: 'note', label: '備註', type: 'textarea' },
];

export default function NewRecordModal({
  categories,
  permissions,
  defaultCategory,
  onClose,
  onCreated,
}: Props) {
  // 該角色可建立的類型 = 該類型 editable_fields 非空
  const allowedCategories = useMemo(() => {
    return categories.filter(
      (c) => (permissions.editable_fields_by_category[c.code]?.length ?? 0) > 0,
    );
  }, [categories, permissions]);

  const [categoryCode, setCategoryCode] = useState<string>(
    defaultCategory && allowedCategories.some((c) => c.code === defaultCategory)
      ? defaultCategory
      : allowedCategories[0]?.code ?? '',
  );
  // 申請日期預設為今天（承辦新增多為當天送件）
  const [values, setValues] = useState<Record<string, string>>({ apply_date: todayIso() });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 持證者 autocomplete 狀態
  const [suggestions, setSuggestions] = useState<HolderLookup[]>([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [autofillFrom, setAutofillFrom] = useState<HolderLookup | null>(null);
  const lookupSeqRef = useRef(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showSuggest) setShowSuggest(false);
        else onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, showSuggest]);

  // 持證者欄 debounce 搜尋（300ms）
  useEffect(() => {
    const q = (values.holder_name ?? '').trim();
    // 已套用自動帶入後 + 使用者沒改名稱 → 不再彈
    if (autofillFrom && autofillFrom.holder_name === q) return;
    if (q.length < 1) {
      setSuggestions([]);
      setShowSuggest(false);
      return;
    }
    const seq = ++lookupSeqRef.current;
    setLookingUp(true);
    const handle = setTimeout(() => {
      lookupHolder(q, 5)
        .then((rows) => {
          if (seq !== lookupSeqRef.current) return; // 後面又有新查詢就丟棄
          setSuggestions(rows);
          setShowSuggest(rows.length > 0);
        })
        .catch(() => {
          /* ignore */
        })
        .finally(() => {
          if (seq === lookupSeqRef.current) setLookingUp(false);
        });
    }, 300);
    return () => clearTimeout(handle);
  }, [values.holder_name, autofillFrom]);

  function applySuggestion(s: HolderLookup) {
    setValues((prev) => {
      const next = { ...prev };
      next.holder_name = s.holder_name ?? '';
      for (const f of REUSABLE_FIELDS) {
        const v = (s as unknown as Record<string, string | null>)[f];
        if (v !== null && v !== undefined && v !== '') next[f] = String(v);
      }
      // 續約起算：新授權期間從「舊到期日的次日」開始（迄日留空，年限不固定由承辦填）
      const start = nextDayIso(s.period_end);
      if (start) next.period_start = start;
      return next;
    });
    setAutofillFrom(s);
    setShowSuggest(false);
  }

  function clearAutofill() {
    setAutofillFrom(null);
  }

  const editableForThisCategory = useMemo(() => {
    const list = permissions.editable_fields_by_category[categoryCode] ?? [];
    return new Set(list);
  }, [categoryCode, permissions]);

  function setVal(key: string, v: string) {
    setValues((prev) => ({ ...prev, [key]: v }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!categoryCode) {
      setError('請選類型');
      return;
    }
    if (!values.holder_name?.trim()) {
      setError('「持證者 / 主辦單位」必填');
      return;
    }

    const payload: Record<string, unknown> = { category_code: categoryCode };
    for (const [k, v] of Object.entries(values)) {
      const s = v.trim();
      if (s) payload[k] = s;
    }

    setSubmitting(true);
    try {
      const rec = await createRecord(payload);
      onCreated(rec);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : '送出失敗');
    } finally {
      setSubmitting(false);
    }
  }

  if (allowedCategories.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <div className="text-warn font-medium mb-3">⚠ 你沒有可新增的類型</div>
          <div className="text-sm text-soft mb-6">
            目前角色（{permissions.role}）對所有類型都沒有寫入權限。
            如有需要請聯絡管理員。
          </div>
          <button
            onClick={onClose}
            className="w-full bg-navy text-white py-2 rounded-lg hover:bg-teal"
          >
            關閉
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center p-6 overflow-y-auto">
      <form
        onSubmit={onSubmit}
        className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-3xl my-8"
      >
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-navy">➕ 新增案件</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-soft hover:text-warn text-2xl leading-none"
            aria-label="關閉"
          >
            ×
          </button>
        </div>

        <div className="mb-6">
          <label className="block text-sm text-soft mb-1">類型 *</label>
          <select
            value={categoryCode}
            onChange={(e) => setCategoryCode(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal"
            required
          >
            {allowedCategories.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name_zh}（{c.code}）
              </option>
            ))}
          </select>
        </div>

        {/* 持證者 / 主辦單位（autocomplete）— 單獨拉出，跨兩欄 */}
        <div className="mb-6 relative">
          <label className="block text-sm text-soft mb-1">
            持證者 / 主辦單位<span className="text-warn"> *</span>
            {!editableForThisCategory.has('holder_name') && (
              <span className="text-xs ml-1 text-slate-400">（此角色無權寫入）</span>
            )}
            {autofillFrom && (
              <span className="ml-2 text-xs text-ok">
                ✓ 已套用上次紀錄（id={autofillFrom.id}
                {autofillFrom.last_apply_date && `, ${autofillFrom.last_apply_date}`}）
                {autofillFrom.period_end && (
                  <span className="ml-1 text-soft">
                    · 上次到期 {autofillFrom.period_end} → 授權起算已自動帶 {nextDayIso(autofillFrom.period_end)}（迄日請自填）
                  </span>
                )}
                <button
                  type="button"
                  onClick={clearAutofill}
                  className="ml-2 underline text-soft hover:text-warn"
                >
                  取消標記
                </button>
              </span>
            )}
          </label>
          <input
            type="text"
            value={values.holder_name ?? ''}
            onChange={(e) => {
              if (autofillFrom && e.target.value !== autofillFrom.holder_name) {
                setAutofillFrom(null);
              }
              setVal('holder_name', e.target.value);
            }}
            onFocus={() => suggestions.length > 0 && !autofillFrom && setShowSuggest(true)}
            onBlur={() => setTimeout(() => setShowSuggest(false), 150)}
            placeholder="例：玉亭演唱會（打字會自動搜尋過往紀錄）"
            disabled={!editableForThisCategory.has('holder_name')}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal disabled:bg-slate-100 disabled:text-soft"
            autoComplete="off"
          />
          {lookingUp && (
            <div className="absolute right-3 top-9 text-xs text-soft">搜尋中…</div>
          )}
          {showSuggest && suggestions.length > 0 && (
            <div className="absolute left-0 right-0 mt-1 bg-white border border-slate-300 rounded-lg shadow-lg max-h-72 overflow-auto z-10">
              <div className="px-3 py-1.5 text-xs text-soft bg-slate-50 border-b">
                找到 {suggestions.length} 筆過往紀錄 — 點選即帶入聯絡 / 地址 / 抬頭
              </div>
              {suggestions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    applySuggestion(s);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-cyan/30 border-b border-slate-100 last:border-0"
                >
                  <div className="flex justify-between gap-3">
                    <span className="font-medium text-ink">{s.holder_name || '—'}</span>
                    <span className="text-xs text-soft font-mono shrink-0">
                      {s.tax_id || '無統編'} · {s.last_apply_date || '無申辦日'}
                    </span>
                  </div>
                  {(s.use_address || s.invoice_title) && (
                    <div className="text-xs text-soft mt-0.5 truncate">
                      {s.invoice_title && <span>抬頭：{s.invoice_title}　</span>}
                      {s.use_address && <span>地址：{s.use_address}</span>}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          {COMMON_FIELDS.map((f) => {
            const editable = editableForThisCategory.has(f.key);
            const required = f.key === 'holder_name';
            const colSpan = f.type === 'textarea' ? 'col-span-2' : '';
            return (
              <div key={f.key} className={colSpan}>
                <label className="block text-sm text-soft mb-1">
                  {f.label}
                  {required && <span className="text-warn"> *</span>}
                  {!editable && <span className="text-xs ml-1 text-slate-400">（此角色無權寫入）</span>}
                </label>
                {f.type === 'textarea' ? (
                  <textarea
                    rows={2}
                    value={values[f.key] ?? ''}
                    onChange={(e) => setVal(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    disabled={!editable}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal disabled:bg-slate-100 disabled:text-soft"
                  />
                ) : (
                  <input
                    type={f.type ?? 'text'}
                    value={values[f.key] ?? ''}
                    onChange={(e) => setVal(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    disabled={!editable}
                    required={required}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal disabled:bg-slate-100 disabled:text-soft"
                  />
                )}
              </div>
            );
          })}
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
            disabled={submitting}
            className="px-5 py-2 bg-navy text-white rounded-lg font-medium hover:bg-teal disabled:opacity-50"
          >
            {submitting ? '送出中…' : '送出 → 進總表'}
          </button>
        </div>
      </form>
    </div>
  );
}
