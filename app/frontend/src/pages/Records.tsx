import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Category,
  RecordRow,
  fetchCategories,
  fetchRecords,
  undoLastEdit,
} from '../api/records';
import { PermissionsOut, fetchPermissions } from '../api/permissions';
import { ApiError } from '../api/client';
import { useAuthStore } from '../store/auth';
import RecordsTable from '../components/RecordsTable';
import NewRecordModal from '../components/NewRecordModal';

const YEAR_ALL = 'all';

function adYearFromIso(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const y = parseInt(iso.slice(0, 4), 10);
  return Number.isFinite(y) ? y : null;
}

export default function Records() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [recordsByCategory, setRecordsByCategory] = useState<Map<string, RecordRow[]> | null>(null);
  const [permissions, setPermissions] = useState<PermissionsOut | null>(null);
  const [progress, setProgress] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<string>(YEAR_ALL);
  const [showNewModal, setShowNewModal] = useState(false);
  const [undoing, setUndoing] = useState(false);
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null);

  // 該角色至少對一個 category 有寫入權限 → 顯示「新增」按鈕
  const canCreate = useMemo(() => {
    if (!permissions) return false;
    return Object.values(permissions.editable_fields_by_category).some(
      (fields) => fields.length > 0,
    );
  }, [permissions]);

  // 從所有 records 抽出有資料的年份（依 issued_date 西元年），由近到遠排
  const availableYears = useMemo(() => {
    if (!recordsByCategory) return [];
    const ys = new Set<number>();
    for (const list of recordsByCategory.values()) {
      for (const r of list) {
        const y = adYearFromIso(r.issued_date);
        if (y !== null) ys.add(y);
      }
    }
    return Array.from(ys).sort((a, b) => b - a);
  }, [recordsByCategory]);

  // 套年份篩選後的 map
  const filteredByCategory = useMemo(() => {
    if (!recordsByCategory) return null;
    if (selectedYear === YEAR_ALL) return recordsByCategory;
    const targetAd = parseInt(selectedYear, 10);
    const out = new Map<string, RecordRow[]>();
    for (const [code, list] of recordsByCategory) {
      out.set(code, list.filter((r) => adYearFromIso(r.issued_date) === targetAd));
    }
    return out;
  }, [recordsByCategory, selectedYear]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setProgress('載入 categories 與 permissions…');
        const [cats, perms] = await Promise.all([
          fetchCategories(),
          fetchPermissions(),
        ]);
        if (!alive) return;
        setCategories(cats);
        setPermissions(perms);

        setProgress(`載入 records (0 / ${cats.length})…`);
        const map = new Map<string, RecordRow[]>();
        let done = 0;
        await Promise.all(
          cats.map(async (c) => {
            const recs = await fetchRecords(c.code);
            map.set(c.code, recs);
            done += 1;
            if (alive) setProgress(`載入 records (${done} / ${cats.length})…`);
          }),
        );
        if (!alive) return;
        setRecordsByCategory(map);
        setProgress('');
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : '載入失敗');
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function handleUndo() {
    if (undoing) return;
    setUndoing(true);
    setToast(null);
    try {
      const result = await undoLastEdit();
      setRecordsByCategory((prev) => {
        if (!prev) return prev;
        const list = prev.get(result.record.category_code);
        if (!list) return prev;
        const idx = list.findIndex((r) => r.id === result.record_id);
        if (idx === -1) return prev;
        const newList = [...list];
        newList[idx] = result.record;
        const next = new Map(prev);
        next.set(result.record.category_code, newList);
        return next;
      });
      const also = result.also_reverted.length
        ? `（連同 ${result.also_reverted.join('、')} 一起還原）`
        : '';
      setToast({
        kind: 'ok',
        msg: `↶ 已還原 id=${result.record_id} 的 ${result.field}：${result.previous_value ?? '空'} → ${result.restored_value ?? '空'}${also}`,
      });
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : '還原失敗';
      setToast({ kind: 'err', msg });
    } finally {
      setUndoing(false);
      setTimeout(() => setToast(null), 5000);
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isUndo =
        (e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z';
      if (!isUndo) return;
      e.preventDefault();
      e.stopPropagation();
      handleUndo();
    }
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [undoing]);

  if (error) {
    return (
      <div className="p-10 text-warn">
        錯誤：{error}
        <button onClick={() => navigate('/')} className="ml-4 text-teal underline">
          回首頁
        </button>
      </div>
    );
  }

  if (!categories || !recordsByCategory || !filteredByCategory) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-soft">{progress || '載入中…'}</div>
      </div>
    );
  }

  const filteredTotal = Array.from(filteredByCategory.values()).reduce(
    (a, b) => a + b.length,
    0,
  );

  return (
    <div className="h-screen flex flex-col">
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-soft hover:text-navy text-sm"
          >
            ← 首頁
          </button>
          <h1 className="text-lg font-bold text-navy">🎵 TMCA 總表</h1>

          <label className="flex items-center gap-1.5 text-sm">
            <span className="text-soft">核發年份</span>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-teal"
            >
              <option value={YEAR_ALL}>全部</option>
              {availableYears.map((y) => (
                <option key={y} value={String(y)}>
                  {y - 1911} 年（{y}）
                </option>
              ))}
            </select>
          </label>

          <div className="text-xs text-soft">共 {filteredTotal} 筆</div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleUndo}
            disabled={undoing}
            title="還原本人 30 分鐘內最近一筆編輯（Ctrl+Z / ⌘Z）"
            className="px-3 py-1.5 border border-slate-300 text-soft rounded text-sm hover:bg-slate-100 hover:text-ink transition disabled:opacity-50"
          >
            {undoing ? '⏳ 還原中…' : '↶ 還原 (Ctrl+Z)'}
          </button>
          {canCreate && (
            <button
              onClick={() => setShowNewModal(true)}
              className="px-3 py-1.5 bg-teal text-white rounded text-sm font-medium hover:bg-navy transition"
            >
              ➕ 新增案件
            </button>
          )}
          <div className="text-sm text-soft">
            {user?.display_name} · <span className="text-teal">{user?.role}</span>
          </div>
        </div>
      </div>
      {toast && (
        <div
          className={`px-6 py-2 text-sm border-b ${
            toast.kind === 'ok'
              ? 'bg-cyan/40 border-slate-200 text-navy'
              : 'bg-red-50 border-warn/30 text-warn'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {showNewModal && permissions && (
        <NewRecordModal
          categories={categories}
          permissions={permissions}
          onClose={() => setShowNewModal(false)}
          onCreated={(rec) => {
            // 直接把新 record 插進對應 category 的 map（不重打 API）
            setRecordsByCategory((prev) => {
              if (!prev) return prev;
              const next = new Map(prev);
              const list = next.get(rec.category_code) ?? [];
              next.set(rec.category_code, [rec, ...list]);
              return next;
            });
            setShowNewModal(false);
          }}
        />
      )}
      <div style={{ flex: 1, minHeight: 0 }}>
        <RecordsTable
          categories={categories}
          recordsByCategory={filteredByCategory}
          permissions={permissions}
          onDeleted={(id, code) => {
            setRecordsByCategory((prev) => {
              if (!prev) return prev;
              const list = prev.get(code);
              if (!list) return prev;
              const next = new Map(prev);
              next.set(code, list.filter((r) => r.id !== id));
              return next;
            });
          }}
          onRestored={(rec) => {
            setRecordsByCategory((prev) => {
              if (!prev) return prev;
              const next = new Map(prev);
              const list = next.get(rec.category_code) ?? [];
              next.set(rec.category_code, [rec, ...list.filter((r) => r.id !== rec.id)]);
              return next;
            });
          }}
        />
      </div>
    </div>
  );
}
