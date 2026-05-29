import { ApiError, api } from './client';
import { RecordRow } from './records';
import { useAuthStore } from '../store/auth';

export interface RenewalListResponse {
  year: number;
  month: number;
  category_code: string | null;
  summary: {
    未續約: number;
    已續約: number;
    其他: number;
    total: number;
  };
  unrenewed: RecordRow[];
  renewed: RecordRow[];
  other: RecordRow[];
}

export interface RecomputeResponse {
  rows_updated: number;
  elapsed_seconds: number;
  breakdown: { [k: string]: number };
  computed_at: string;
}

export const fetchRenewals = (month: number, year?: number, categoryCode?: string) => {
  const params = new URLSearchParams({ month: String(month) });
  if (year !== undefined) params.set('year', String(year));
  if (categoryCode) params.set('category_code', categoryCode);
  return api<RenewalListResponse>(`/api/renewals?${params.toString()}`);
};

export const recomputeRenewals = () =>
  api<RecomputeResponse>('/api/renewals/recompute', { method: 'POST' });

// 一鍵生成續約行：回傳新建立的續約紀錄
export const generateRenewal = (recordId: number) =>
  api<RecordRow>(`/api/renewals/${recordId}/generate`, { method: 'POST' });

// ── 續約函（電腦伴唱機）─────────────────────────────────────────
export interface RenewalLetterData {
  record_id: number;
  recipient: string;
  issue_date: string;
  pay_deadline: string;
  period_start: string;
  period_end: string;
  business_address: string;
  qty: number;
  amount: number;
}

// 表單送出用：全為字串（所見即所印），qty/amount 也以字串傳
export interface RenewalLetterPayload {
  record_id?: number;
  recipient: string;
  issue_date: string;
  pay_deadline: string;
  period_start: string;
  period_end: string;
  business_address: string;
  qty: string;
  amount: string;
}

// 取某筆續約函的表單預填值
export const fetchRenewalLetterData = (recordId: number) =>
  api<RenewalLetterData>(`/api/renewals/${recordId}/letter-data`);

// 產生續約函 Word：回 blob + 後端建議檔名
export async function generateRenewalLetter(
  payload: RenewalLetterPayload,
): Promise<{ blob: Blob; filename: string }> {
  const token = useAuthStore.getState().token;
  const res = await fetch('/api/renewals/letter', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
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
  const blob = await res.blob();
  // 從 Content-Disposition 的 filename*=UTF-8''… 取中文檔名
  const cd = res.headers.get('Content-Disposition') || '';
  let filename = `續約函_${new Date().toISOString().slice(0, 10)}.docx`;
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      filename = decodeURIComponent(star[1]);
    } catch {
      /* keep default */
    }
  }
  return { blob, filename };
}
