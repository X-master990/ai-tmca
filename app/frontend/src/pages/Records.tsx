import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Category, RecordRow, fetchCategories, fetchRecords } from '../api/records';
import { useAuthStore } from '../store/auth';
import RecordsTable from '../components/RecordsTable';

export default function Records() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [recordsByCategory, setRecordsByCategory] = useState<Map<string, RecordRow[]> | null>(null);
  const [progress, setProgress] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setProgress('載入 categories…');
        const cats = await fetchCategories();
        if (!alive) return;
        setCategories(cats);

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

  if (!categories || !recordsByCategory) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-soft">{progress || '載入中…'}</div>
      </div>
    );
  }

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
          <div className="text-xs text-soft">
            共 {Array.from(recordsByCategory.values()).reduce((a, b) => a + b.length, 0)} 筆
          </div>
        </div>
        <div className="text-sm text-soft">
          {user?.display_name} · <span className="text-teal">{user?.role}</span>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <RecordsTable categories={categories} recordsByCategory={recordsByCategory} />
      </div>
    </div>
  );
}
