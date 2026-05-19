import { ApiError, api } from './client';
import { useAuthStore } from '../store/auth';

export interface PendingInvoice {
  id: number;
  category_code: string;
  holder_name: string | null;
  invoice_type: string | null;
  invoice_title: string | null;
  tax_id: string | null;
  product: string;
  amount: number | null;
  untaxed_unit_price: number;
  note: string | null;
}

export async function fetchPendingInvoices(params: {
  category_code?: string;
  q?: string;
} = {}): Promise<PendingInvoice[]> {
  const usp = new URLSearchParams();
  if (params.category_code) usp.set('category_code', params.category_code);
  if (params.q) usp.set('q', params.q);
  const qs = usp.toString();
  return api(`/api/invoices/pending${qs ? `?${qs}` : ''}`);
}

export interface GenerateInvoiceReq {
  record_ids: number[];
  issue_date?: string; // YYYY-MM-DD
  invoice_type?: '二聯式' | '三聯式';
  prefix?: string;
}

export interface GenerateInvoiceResult {
  blob: Blob;
  filename: string;
  count: number;
  firstNo: string;
  lastNo: string;
}

export async function generateInvoices(
  req: GenerateInvoiceReq,
): Promise<GenerateInvoiceResult> {
  const token = useAuthStore.getState().token;
  const res = await fetch('/api/invoices/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(req),
    credentials: 'include',
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = `HTTP ${res.status}`;
    try {
      const data = JSON.parse(text);
      detail = data.detail || data.message || detail;
    } catch {
      if (text) detail = text;
    }
    throw new ApiError(res.status, detail);
  }

  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') || '';
  const m = cd.match(/filename="?([^"]+)"?/);
  const filename = m ? m[1] : `invoice_${new Date().toISOString().slice(0, 10)}.xlsx`;
  return {
    blob,
    filename,
    count: Number(res.headers.get('X-Invoice-Count') || 0),
    firstNo: res.headers.get('X-Invoice-First') || '',
    lastNo: res.headers.get('X-Invoice-Last') || '',
  };
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
