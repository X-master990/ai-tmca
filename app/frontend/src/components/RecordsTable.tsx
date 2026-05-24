import { useEffect, useMemo, useState } from 'react';
import { columnsFor, getCellValue, Category, RecordRow } from '../api/records';
import { PermissionsOut, patchRecord } from '../api/permissions';
import { downloadBlob, generateInvoices } from '../api/invoices';
import { useAuthStore } from '../store/auth';
import StatusDot from './StatusDot';

const STATUS_FIELDS = new Set(['renewal_status', 'issuance_status']);

interface Props {
  categories: Category[];
  recordsByCategory: Map<string, RecordRow[]>;
  permissions: PermissionsOut | null;
}

const ROW_CAP = 500;

const DATE_FIELDS = new Set(['issued_date', 'invoice_date', 'apply_date', 'period_start', 'period_end']);
const INT_FIELDS = new Set(['amount', 'qty', 'extra.audience_size', 'extra.floor_area']);

function formatVal(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'boolean') return v ? '✓' : '';
  return String(v);
}

function EditableCell({
  row,
  field,
  editable,
  width,
  onSave,
}: {
  row: RecordRow;
  field: string;
  editable: boolean;
  width: number;
  onSave: (newValue: unknown) => Promise<void>;
}) {
  const initial = formatVal(getCellValue(row, field));
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // 外部來源（undo / row 重新整理）改了底層資料時，把顯示值同步進來
  useEffect(() => {
    if (!editing && value !== initial) {
      setValue(initial);
      setErr(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial]);

  async function commit() {
    setEditing(false);
    if (value === initial) return;
    setBusy(true);
    setErr(null);
    try {
      let raw: unknown = value;
      if (value === '') raw = null;
      else if (INT_FIELDS.has(field)) raw = parseInt(value, 10);
      await onSave(raw);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '存檔失敗');
      setValue(initial);
    } finally {
      setBusy(false);
    }
  }

  if (!editable) {
    return (
      <td
        className="px-2 py-1 border border-slate-200 truncate text-soft"
        style={{ width, maxWidth: width, background: '#fafafa' }}
        title={initial}
      >
        {initial}
      </td>
    );
  }

  if (editing) {
    return (
      <td className="border border-teal" style={{ width, maxWidth: width, padding: 0 }}>
        <input
          autoFocus
          type={DATE_FIELDS.has(field) ? 'date' : 'text'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
            if (e.key === 'Escape') {
              setValue(initial);
              setEditing(false);
            }
          }}
          className="w-full h-full px-2 py-1 text-xs outline-none"
        />
      </td>
    );
  }

  return (
    <td
      className={`px-2 py-1 border truncate cursor-cell hover:bg-cyan/40 ${err ? 'bg-red-50 border-warn' : 'border-slate-200'}`}
      style={{ width, maxWidth: width }}
      title={err || initial}
      onDoubleClick={() => setEditing(true)}
    >
      {busy ? <span className="text-soft">⏳</span> : value}
    </td>
  );
}

export default function RecordsTable({ categories, recordsByCategory, permissions }: Props) {
  const { user } = useAuthStore();
  const canIssueInvoice = user?.role === 'admin' || user?.role === 'accountant';

  // 預設停在「該角色可編輯」的第一個類型；找不到則回到第一個
  const defaultCode = useMemo(() => {
    if (permissions) {
      const editable = categories.find(
        (c) => (permissions.editable_fields_by_category[c.code]?.length ?? 0) > 0,
      );
      if (editable) return editable.code;
    }
    return categories[0]?.code ?? '';
  }, [categories, permissions]);
  const [activeCode, setActiveCode] = useState<string>(defaultCode);
  const [filter, setFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [issuing, setIssuing] = useState(false);
  const [issueMsg, setIssueMsg] = useState<string | null>(null);
  const [, forceRefresh] = useState(0);

  const columns = useMemo(() => columnsFor(activeCode), [activeCode]);

  const fullList = useMemo(
    () => recordsByCategory.get(activeCode) || [],
    [activeCode, recordsByCategory],
  );

  const filtered = useMemo(() => {
    if (!filter.trim()) return fullList;
    const q = filter.toLowerCase();
    return fullList.filter((r) =>
      columns.some((c) => {
        const v = getCellValue(r, c.key);
        return v !== null && v !== undefined && String(v).toLowerCase().includes(q);
      }),
    );
  }, [fullList, filter, columns]);

  const activeRecords = useMemo(() => filtered.slice(0, ROW_CAP), [filtered]);

  const editableFields = useMemo(
    () => new Set(permissions?.editable_fields_by_category[activeCode] ?? []),
    [permissions, activeCode],
  );

  async function saveCell(row: RecordRow, field: string, newValue: unknown) {
    const updated = await patchRecord(row.id, { [field]: newValue });
    // 把回傳的 row 寫回 recordsByCategory（mutate in place）
    Object.assign(row, updated);
    forceRefresh((n) => n + 1);
  }

  // 可開立發票：金額 > 0 且尚未有發票號
  const issuableSelected = useMemo(
    () =>
      activeRecords.filter(
        (r) => selectedIds.has(r.id) && !r.invoice_no && (r.amount ?? 0) > 0,
      ),
    [activeRecords, selectedIds],
  );
  const blockedSelected = useMemo(
    () =>
      activeRecords.filter(
        (r) => selectedIds.has(r.id) && (r.invoice_no || (r.amount ?? 0) <= 0),
      ),
    [activeRecords, selectedIds],
  );

  function toggleOne(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleAllVisible() {
    setSelectedIds((prev) => {
      const allSel = activeRecords.every((r) => prev.has(r.id));
      const next = new Set(prev);
      if (allSel) activeRecords.forEach((r) => next.delete(r.id));
      else activeRecords.forEach((r) => next.add(r.id));
      return next;
    });
  }

  async function handleIssueInvoice() {
    if (issuableSelected.length === 0) return;
    if (!window.confirm(
      `將為 ${issuableSelected.length} 筆紀錄配發發票號碼並下載 Excel。\n此動作會直接寫入發票號（無法退回），確定？`,
    )) return;
    setIssuing(true);
    setIssueMsg(null);
    try {
      const result = await generateInvoices({
        record_ids: issuableSelected.map((r) => r.id),
        invoice_type: '二聯式',
      });
      downloadBlob(result.blob, result.filename);
      setIssueMsg(`✅ 已開 ${result.count} 張：${result.firstNo} ~ ${result.lastNo}`);
      // 重新拉這些 record 的狀態太麻煩，直接 mutate：清掉勾選並重抓
      const issuedIds = new Set(issuableSelected.map((r) => r.id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        issuedIds.forEach((id) => next.delete(id));
        return next;
      });
      // 觸發整頁刷新 — 簡單做法：reload
      // 不 reload，改 mutate 行：給每筆塞一個假發票號做樂觀更新（後端會在下次刷新時帶真實號）
      // 真實號其實已經回來在 result，但這裡沒做配對；先標記成「綠 / 已開」讓 UI 即時反映
      activeRecords.forEach((r) => {
        if (issuedIds.has(r.id)) {
          r.issuance_status = '綠';
          if (!r.invoice_no) r.invoice_no = '(剛開立)'; // 提示用，重新整理後會帶回真實號
          r.invoice_date = new Date().toISOString().slice(0, 10);
        }
      });
      forceRefresh((n) => n + 1);
    } catch (e) {
      setIssueMsg(`❌ ${e instanceof Error ? e.message : '開立失敗'}`);
    } finally {
      setIssuing(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex flex-wrap gap-1">
        {categories.map((c) => (
          <button
            key={c.code}
            onClick={() => setActiveCode(c.code)}
            className={`px-3 py-1.5 text-xs rounded transition ${
              activeCode === c.code
                ? 'bg-navy text-white'
                : 'bg-slate-100 text-soft hover:bg-cyan'
            }`}
          >
            {c.name_zh}
            <span className="ml-1 opacity-60">({c.record_count})</span>
          </button>
        ))}
      </div>

      {/* Filter + permission status */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex items-center gap-3">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="🔍 全欄位搜尋..."
          className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-teal"
        />
        <div className="text-xs text-soft">
          {filter.trim()
            ? <>篩出 <span className="font-mono text-ink">{filtered.length}</span> 筆</>
            : <>共 <span className="font-mono text-ink">{fullList.length}</span> 筆</>}
          {filtered.length > ROW_CAP && <>，僅顯示前 {ROW_CAP} 筆</>}
        </div>
        <div className="text-xs">
          {editableFields.size === 0 ? (
            <span className="text-warn">👁 唯讀</span>
          ) : (
            <span className="text-ok">✏️ 可編 {editableFields.size} 欄</span>
          )}
        </div>
        {canIssueInvoice && (
          <>
            <div className="text-xs text-soft">
              已選 <span className="font-mono text-ink">{selectedIds.size}</span>
              {selectedIds.size > 0 && (
                <span className="ml-1">
                  · 可開 <span className="font-mono text-ok">{issuableSelected.length}</span>
                  {blockedSelected.length > 0 && (
                    <span className="ml-1 text-warn">
                      · 跳過 {blockedSelected.length}（已有號或金額≤0）
                    </span>
                  )}
                </span>
              )}
            </div>
            <button
              disabled={issuing || issuableSelected.length === 0}
              onClick={handleIssueInvoice}
              className="px-3 py-1 bg-teal text-white text-xs rounded hover:bg-navy disabled:bg-slate-300 disabled:cursor-not-allowed transition"
              title={
                issuableSelected.length === 0
                  ? '請勾選至少一筆「未開發票且金額 > 0」的紀錄'
                  : ''
              }
            >
              {issuing ? '⏳ 開立中…' : `🧾 開立發票 (${issuableSelected.length})`}
            </button>
          </>
        )}
      </div>
      {issueMsg && (
        <div className="px-4 py-1.5 text-xs bg-cyan/30 border-b border-slate-200">
          {issueMsg}
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto bg-white">
        <table className="text-xs border-collapse" style={{ tableLayout: 'fixed' }}>
          <thead className="sticky top-0 z-10 bg-cyan">
            <tr>
              {canIssueInvoice && (
                <th
                  className="px-2 py-2 text-center font-semibold text-navy border border-slate-300"
                  style={{ width: 36, minWidth: 36 }}
                >
                  <input
                    type="checkbox"
                    checked={
                      activeRecords.length > 0 &&
                      activeRecords.every((r) => selectedIds.has(r.id))
                    }
                    onChange={toggleAllVisible}
                    title="全選/全消"
                  />
                </th>
              )}
              {columns.map((c) => (
                <th
                  key={c.key}
                  className="px-2 py-2 text-left font-semibold text-navy border border-slate-300 whitespace-nowrap"
                  style={{ width: c.width, minWidth: c.width }}
                >
                  {c.label}
                  {editableFields.has(c.key) && (
                    <span className="ml-1 text-ok" title="可編輯">✏️</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {activeRecords.map((r, i) => (
              <tr
                key={r.id}
                className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}
              >
                {canIssueInvoice && (() => {
                  const issuable = !r.invoice_no && (r.amount ?? 0) > 0;
                  const reason = r.invoice_no
                    ? `已有發票號 ${r.invoice_no}（不會重複開立）`
                    : (r.amount ?? 0) <= 0
                      ? '金額 ≤ 0，不會開立'
                      : '勾選開立';
                  return (
                    <td
                      className="px-2 py-1 border border-slate-200 text-center"
                      style={{
                        width: 36,
                        maxWidth: 36,
                        background: issuable ? undefined : '#f1f5f9',
                      }}
                      title={reason}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(r.id)}
                        onChange={() => toggleOne(r.id)}
                        style={{ opacity: issuable ? 1 : 0.45 }}
                      />
                    </td>
                  );
                })()}
                {columns.map((c) => {
                  const field = c.key;
                  // id 欄位永遠唯讀
                  if (field === 'id') {
                    return (
                      <td
                        key={field}
                        className="px-2 py-1 border border-slate-200 truncate text-soft font-mono"
                        style={{ width: c.width, maxWidth: c.width }}
                      >
                        {r.id}
                      </td>
                    );
                  }
                  // 狀態燈：圓點顯示，不可編
                  if (STATUS_FIELDS.has(field)) {
                    const v = (r as unknown as { [k: string]: string | null })[field];
                    return (
                      <td
                        key={field}
                        className="px-2 py-1 border border-slate-200 text-center"
                        style={{ width: c.width, maxWidth: c.width }}
                      >
                        <StatusDot value={v} />
                      </td>
                    );
                  }
                  return (
                    <EditableCell
                      key={field}
                      row={r}
                      field={field}
                      editable={editableFields.has(field)}
                      width={c.width}
                      onSave={(v) => saveCell(r, field, v)}
                    />
                  );
                })}
              </tr>
            ))}
            {activeRecords.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length + (canIssueInvoice ? 1 : 0)}
                  className="px-4 py-8 text-center text-soft"
                >
                  無資料
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
