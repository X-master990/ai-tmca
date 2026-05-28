import { useAuthStore } from '../store/auth';
import { ApiError } from './client';
import { downloadBlob } from './invoices';

async function fetchXlsx(url: string): Promise<Blob> {
  const token = useAuthStore.getState().token;
  const res = await fetch(url, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    credentials: 'include',
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = JSON.parse(await res.text());
      detail = data.detail || data.message || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.blob();
}

function todayTag(): string {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

/** 匯出某類別的全部總表資料(完整欄位)。 */
export async function exportRecords(code: string, label: string): Promise<void> {
  const blob = await fetchXlsx(`/api/exports/records?category_code=${encodeURIComponent(code)}`);
  downloadBlob(blob, `總表_${label}_${todayTag()}.xlsx`);
}

/** 匯出某年月的續約名單(含續約狀態)。 */
export async function exportRenewals(month: number, year: number, code?: string): Promise<void> {
  const qs = new URLSearchParams({ month: String(month), year: String(year) });
  if (code) qs.set('category_code', code);
  const blob = await fetchXlsx(`/api/exports/renewals?${qs.toString()}`);
  downloadBlob(blob, `續約名單_${year}-${String(month).padStart(2, '0')}.xlsx`);
}

/** 匯出全文搜尋結果。 */
export async function exportSearch(q: string): Promise<void> {
  const blob = await fetchXlsx(`/api/exports/search?q=${encodeURIComponent(q)}`);
  downloadBlob(blob, `搜尋_${q}_${todayTag()}.xlsx`);
}
