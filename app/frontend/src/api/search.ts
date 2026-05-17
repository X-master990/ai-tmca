import { api } from './client';
import { RecordRow } from './records';

export interface SearchResponse {
  q: string;
  total: number;
  by_category: { [code: string]: number };
  results: RecordRow[];
}

export interface AgentGroup {
  applicant_name: string;
  holder_name: string;
  count: number;
  categories: string[];
  records: RecordRow[];
}

export interface AgentsResponse {
  query_name: string;
  total_records: number;
  distinct_holders: number;
  groups: AgentGroup[];
}

export const search = (q: string, categoryCode?: string) => {
  const p = new URLSearchParams({ q });
  if (categoryCode) p.set('category_code', categoryCode);
  return api<SearchResponse>(`/api/search?${p.toString()}`);
};

export const searchAgents = (name: string) =>
  api<AgentsResponse>(`/api/search/agents?name=${encodeURIComponent(name)}`);
