import { api } from './client';

export interface ReportSummary {
  year: number;
  totals: {
    issued_this_year: number;
    amount_this_year: number;
    total_records: number;
  };
  monthly: { month: number; issued_count: number; amount_sum: number }[];
  by_category: {
    code: string;
    name_zh: string;
    issued_count: number;
    amount_sum: number;
  }[];
  renewal: {
    renewed: number;
    unrenewed: number;
    other: number;
    rate_percent: number | null;
  };
  issuance: {
    issued: number;
    pending: number;
  };
}

export const fetchReportSummary = (year?: number) => {
  const p = new URLSearchParams();
  if (year !== undefined) p.set('year', String(year));
  const qs = p.toString();
  return api<ReportSummary>(`/api/reports/summary${qs ? '?' + qs : ''}`);
};
