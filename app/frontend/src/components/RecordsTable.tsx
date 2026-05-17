import { useMemo, useState } from 'react';
import { COLUMNS, Category, RecordRow } from '../api/records';
import { PermissionsOut, patchRecord } from '../api/permissions';

interface Props {
  categories: Category[];
  recordsByCategory: Map<string, RecordRow[]>;
  permissions: PermissionsOut | null;
}

const ROW_CAP = 500;

const DATE_FIELDS = new Set(['issued_date', 'invoice_date', 'apply_date', 'period_start', 'period_end']);
const INT_FIELDS = new Set(['amount', 'qty']);

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
  const initial = formatVal((row as unknown as { [k: string]: unknown })[field]);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
  const [activeCode, setActiveCode] = useState<string>(categories[0]?.code ?? '');
  const [filter, setFilter] = useState('');
  const [, forceRefresh] = useState(0);

  const fullList = useMemo(
    () => recordsByCategory.get(activeCode) || [],
    [activeCode, recordsByCategory],
  );

  const filtered = useMemo(() => {
    if (!filter.trim()) return fullList;
    const q = filter.toLowerCase();
    return fullList.filter((r) =>
      COLUMNS.some((c) => {
        const v = (r as unknown as { [k: string]: unknown })[c.key as string];
        return v !== null && v !== undefined && String(v).toLowerCase().includes(q);
      }),
    );
  }, [fullList, filter]);

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
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto bg-white">
        <table className="text-xs border-collapse" style={{ tableLayout: 'fixed' }}>
          <thead className="sticky top-0 z-10 bg-cyan">
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key as string}
                  className="px-2 py-2 text-left font-semibold text-navy border border-slate-300 whitespace-nowrap"
                  style={{ width: c.width, minWidth: c.width }}
                >
                  {c.label}
                  {editableFields.has(c.key as string) && (
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
                {COLUMNS.map((c) => {
                  const field = c.key as string;
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
                <td colSpan={COLUMNS.length} className="px-4 py-8 text-center text-soft">
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
