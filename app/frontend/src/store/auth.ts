import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Role =
  | 'officer_a'
  | 'officer_b'
  | 'accountant'
  | 'issuer'
  | 'viewer'
  | 'admin';

export interface User {
  id: number;
  username: string;
  display_name: string | null;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clear: () => set({ token: null, user: null }),
    }),
    { name: 'tmca-auth' },
  ),
);

export const ROLE_LABEL: Record<Role, string> = {
  officer_a: '承辦 A（單場次表演）',
  officer_b: '承辦 B（其餘類別）',
  accountant: '會計',
  issuer: '核發',
  viewer: '檢視者',
  admin: '系統管理員',
};
