import { api } from './client';
import { RecordRow } from './records';

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
