import { ApiError, api } from './client';
import { useAuthStore } from '../store/auth';

export interface PendingIssuance {
  id: number;
  category_code: string;
  cert_no: string | null;
  holder_name: string | null;
  use_address: string | null;
  period_start: string | null;
  period_end: string | null;
  qty: number | null;
  issuance_status: string;
  has_cert: boolean;
}

export interface CertField {
  name: string;
  value: string;
}

export interface CertData {
  record_id: number;
  category_code: string;
  template: string | null;
  fields: CertField[];
}

export const fetchPendingIssuance = (params: { category_code?: string; q?: string } = {}) => {
  const usp = new URLSearchParams();
  if (params.category_code) usp.set('category_code', params.category_code);
  if (params.q) usp.set('q', params.q);
  const qs = usp.toString();
  return api<PendingIssuance[]>(`/api/issuance/pending${qs ? `?${qs}` : ''}`);
};

export const fetchCertData = (recordId: number) =>
  api<CertData>(`/api/issuance/${recordId}/cert-data`);

// 產生證書 Word：回 blob + 後端建議檔名
export async function generateCert(
  recordId: number,
  payload: { fields: Record<string, string>; mark_issued: boolean },
): Promise<{ blob: Blob; filename: string }> {
  const token = useAuthStore.getState().token;
  const res = await fetch(`/api/issuance/${recordId}/cert`, {
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
  const cd = res.headers.get('Content-Disposition') || '';
  let filename = `證書_${new Date().toISOString().slice(0, 10)}.docx`;
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
