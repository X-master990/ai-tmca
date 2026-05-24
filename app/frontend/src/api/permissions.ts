import { api } from './client';

export interface PermissionsOut {
  role: string;
  editable_fields_by_category: { [code: string]: string[] };
  deletable_categories: string[];
}

export const fetchPermissions = () =>
  api<PermissionsOut>('/api/records/permissions');

export const patchRecord = (id: number, patch: { [field: string]: unknown }) =>
  api<unknown>(`/api/records/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
