import { api } from './client';

export interface Category {
  code: string;
  name_zh: string;
  sheet_name: string | null;
  assigned_role: string;
  sort_order: number | null;
  record_count: number;
}

export interface RecordRow {
  id: number;
  category_code: string;
  cert_no: string | null;
  issued_date: string | null;
  note: string | null;
  invoice_date: string | null;
  invoice_type: string | null;
  invoice_title: string | null;
  tax_id: string | null;
  invoice_no: string | null;
  amount: number | null;
  source: string | null;
  officer: string | null;
  action_type: string | null;
  apply_date: string | null;
  applicant_name: string | null;
  applicant_id: string | null;
  applicant_mobile: string | null;
  applicant_phone: string | null;
  applicant_fax: string | null;
  holder_name: string | null;
  holder_type: string | null;
  use_zip: string | null;
  use_address: string | null;
  onsite_name: string | null;
  onsite_mobile: string | null;
  onsite_phone: string | null;
  onsite_ext: string | null;
  onsite_fax: string | null;
  qty: number | null;
  brand: string | null;
  serial_no: string | null;
  period_start: string | null;
  period_end: string | null;
  mail_type: string | null;
  mail_zip: string | null;
  mail_address: string | null;
  mail_recipient: string | null;
  mail_phone: string | null;
  paper_application: boolean;
  paper_remittance: boolean;
  paper_official_doc: boolean;
  issuance_status: string;
  renewal_status: string | null;
  extra: RecordExtra;
  created_at: string;
  updated_at: string;
}

export type RecordExtra = { [key: string]: string | number | boolean | null };

export interface Column {
  // 一般欄位用 RecordRow 的 key；類型專屬欄位用 "extra.<key>"
  key: string;
  label: string;
  width: number;
}

export const COLUMNS: Column[] = [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'cert_no', label: '證書編號', width: 120 },
  { key: 'issued_date', label: '發證日', width: 100 },
  { key: 'invoice_date', label: '發票日期', width: 100 },
  { key: 'invoice_type', label: '發票形式', width: 80 },
  { key: 'invoice_title', label: '發票抬頭', width: 200 },
  { key: 'tax_id', label: '統一編號', width: 100 },
  { key: 'invoice_no', label: '發票號碼', width: 120 },
  { key: 'amount', label: '金額', width: 90 },
  { key: 'source', label: '提報', width: 70 },
  { key: 'officer', label: '承辦人', width: 90 },
  { key: 'action_type', label: '辦理項目', width: 100 },
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'applicant_name', label: '申請人', width: 120 },
  { key: 'applicant_id', label: '身分證號', width: 110 },
  { key: 'applicant_mobile', label: '行動', width: 130 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'holder_type', label: '性質/類型', width: 120 },
  { key: 'use_zip', label: '郵遞區號', width: 80 },
  { key: 'use_address', label: '使用地址', width: 240 },
  { key: 'onsite_name', label: '現場聯絡人', width: 100 },
  { key: 'onsite_mobile', label: '現場手機', width: 130 },
  { key: 'onsite_phone', label: '現場電話', width: 130 },
  { key: 'onsite_ext', label: '分機', width: 60 },
  { key: 'onsite_fax', label: '現場傳真', width: 130 },
  { key: 'qty', label: '台數', width: 60 },
  { key: 'brand', label: '廠牌', width: 100 },
  { key: 'serial_no', label: '機號', width: 240 },
  { key: 'period_start', label: '授權起', width: 110 },
  { key: 'period_end', label: '授權迄', width: 110 },
  { key: 'mail_zip', label: '寄證郵區', width: 80 },
  { key: 'mail_address', label: '寄證地址', width: 240 },
  { key: 'mail_recipient', label: '收件人', width: 140 },
  { key: 'mail_phone', label: '收件人電話', width: 130 },
  { key: 'issuance_status', label: '核發狀態', width: 80 },
  { key: 'renewal_status', label: '續約狀態', width: 80 },
  { key: 'note', label: '註記', width: 200 },
];

// 各類型專屬欄位順序，逐一對齊「110-115年 總表.xlsx」每個 sheet（見 IMPORT-MAPPING.md）。
// extra.* 取 JSONB 子欄位；授權期間 6 欄（起年/月/日、迄年/月/日）以 DB 實際儲存的
// period_start/period_end 兩個日期欄呈現。共同的前 10 欄與尾端寄證/狀態欄抽成共用片段。
const HEAD: Column[] = [
  { key: 'id', label: 'NO.', width: 60 },
  { key: 'issued_date', label: '發證日', width: 100 },
  { key: 'note', label: '註記', width: 160 },
  { key: 'cert_no', label: '證書編號', width: 120 },
  { key: 'invoice_date', label: '發票日期', width: 100 },
  { key: 'invoice_type', label: '發票形式', width: 80 },
  { key: 'invoice_title', label: '發票抬頭', width: 180 },
  { key: 'tax_id', label: '統一編號', width: 100 },
  { key: 'invoice_no', label: '發票號碼', width: 120 },
  { key: 'amount', label: '金額(含稅)', width: 100 },
];
const PERIOD: Column[] = [
  { key: 'period_start', label: '授權起', width: 110 },
  { key: 'period_end', label: '授權迄', width: 110 },
];
const MAIL: Column[] = [
  { key: 'mail_zip', label: '郵區', width: 70 },
  { key: 'mail_address', label: '收件地址', width: 220 },
  { key: 'mail_recipient', label: '收件人', width: 120 },
  { key: 'mail_phone', label: '收件人電話', width: 120 },
];
const STATUS: Column[] = [
  { key: 'issuance_status', label: '核發狀態', width: 80 },
  { key: 'renewal_status', label: '續約狀態', width: 80 },
];

// 提報 / 承辦人 / 辦理項目 — 伴唱機家族、KTV、街頭藝人、交通有；其餘類型總表沒這 3 欄。
const REPORT: Column[] = [
  { key: 'source', label: '提報', width: 70 },
  { key: 'officer', label: '承辦人', width: 90 },
  { key: 'action_type', label: '辦理項目', width: 100 },
];

const SINGLE_EVENT_COLUMNS: Column[] = [
  ...HEAD,
  // 申請人 / 主辦單位 / 持證者
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'holder_name', label: '主辦單位(持證人)', width: 200 },
  { key: 'extra.holder_tax_id', label: '統一編號', width: 100 },
  { key: 'applicant_phone', label: '電話', width: 120 },
  { key: 'applicant_fax', label: '傳真', width: 120 },
  { key: 'use_address', label: '地址', width: 220 },
  // 節目 / 活動資料
  { key: 'extra.event_name', label: '節目名稱', width: 180 },
  { key: 'extra.songs', label: '演出曲目', width: 260 },
  { key: 'extra.song_count', label: '總曲數', width: 70 },
  { key: 'extra.venue', label: '活動地點', width: 160 },
  { key: 'extra.venue_address', label: '地址', width: 220 },
  { key: 'qty', label: '場次', width: 60 },
  { key: 'extra.audience_size', label: '人數', width: 70 },
  ...PERIOD,
  // 業務承辦人
  { key: 'extra.contact_org', label: '所屬單位', width: 160 },
  { key: 'onsite_name', label: '姓名', width: 100 },
  { key: 'extra.contact_title', label: '職稱', width: 90 },
  { key: 'onsite_mobile', label: '手機', width: 120 },
  { key: 'onsite_phone', label: '電話', width: 120 },
  { key: 'onsite_ext', label: '分機', width: 60 },
  { key: 'onsite_fax', label: '傳真', width: 120 },
  { key: 'extra.contact_email', label: '信箱', width: 180 },
  ...MAIL,
  ...STATUS,
];

const SELF_KTV_COLUMNS: Column[] = [
  ...HEAD,
  ...REPORT,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'applicant_name', label: '申請人', width: 120 },
  { key: 'applicant_id', label: '身分證號', width: 110 },
  { key: 'applicant_mobile', label: '手機', width: 130 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'onsite_name', label: '聯絡人', width: 100 },
  { key: 'onsite_mobile', label: '手機', width: 130 },
  { key: 'onsite_phone', label: '電話', width: 130 },
  { key: 'onsite_ext', label: '分機', width: 60 },
  { key: 'onsite_fax', label: '傳真', width: 130 },
  { key: 'use_zip', label: '郵遞區號', width: 80 },
  { key: 'use_address', label: '使用地址', width: 240 },
  { key: 'qty', label: '包廂數', width: 70 },
  ...PERIOD,
  ...MAIL,
  ...STATUS,
];

const STREET_ARTIST_COLUMNS: Column[] = [
  ...HEAD,
  ...REPORT,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'applicant_name', label: '申請人', width: 120 },
  { key: 'applicant_mobile', label: '手機', width: 130 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'extra.email', label: 'E-mail', width: 180 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'extra.cert_issuer', label: '發證單位', width: 140 },
  { key: 'extra.street_cert_no', label: '街頭藝人證號', width: 130 },
  { key: 'extra.street_cert_expiry', label: '證號到期日', width: 110 },
  { key: 'use_address', label: '表演場地', width: 240 },
  ...PERIOD,
  ...MAIL,
  ...STATUS,
];

const TRANSPORT_COLUMNS: Column[] = [
  ...HEAD,
  ...REPORT,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'applicant_name', label: '申請人', width: 120 },
  { key: 'applicant_mobile', label: '手機', width: 130 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'use_zip', label: '郵區', width: 80 },
  { key: 'use_address', label: '營業地址', width: 240 },
  { key: 'onsite_name', label: '聯絡人', width: 100 },
  { key: 'onsite_mobile', label: '手機', width: 130 },
  { key: 'onsite_phone', label: '電話', width: 130 },
  { key: 'onsite_ext', label: '分機', width: 60 },
  { key: 'onsite_fax', label: '傳真', width: 130 },
  { key: 'qty', label: '車輛數', width: 70 },
  { key: 'serial_no', label: '車輛號碼', width: 200 },
  ...PERIOD,
  ...MAIL,
  ...STATUS,
];

const PUBLIC_TRANSMIT_COLUMNS: Column[] = [
  ...HEAD,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'holder_name', label: '持證人', width: 200 },
  { key: 'applicant_name', label: '代表人', width: 120 },
  { key: 'onsite_name', label: '聯絡人', width: 120 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'extra.email', label: 'E-mail', width: 180 },
  { key: 'use_zip', label: '郵區', width: 80 },
  { key: 'use_address', label: '地址', width: 240 },
  { key: 'holder_type', label: '使用類型', width: 120 },
  { key: 'extra.has_revenue', label: '營收/來源', width: 90 },
  { key: 'extra.platform_name', label: '平台名稱', width: 200 },
  { key: 'extra.platform_url', label: '網址', width: 220 },
  { key: 'extra.songs', label: '公開傳輸曲目', width: 260 },
  ...PERIOD,
  ...MAIL,
  ...STATUS,
];

const FUNERAL_COLUMNS: Column[] = [
  ...HEAD,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'applicant_name', label: '申請人', width: 120 },
  { key: 'applicant_mobile', label: '手機', width: 130 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'extra.ceremony_name', label: '儀式名稱', width: 180 },
  { key: 'extra.songs', label: '演出曲目', width: 260 },
  { key: 'extra.language', label: '語言別', width: 80 },
  { key: 'extra.song_count', label: '總曲數', width: 70 },
  { key: 'extra.venue', label: '儀式地點', width: 160 },
  { key: 'use_address', label: '地址', width: 220 },
  { key: 'qty', label: '場次', width: 60 },
  ...PERIOD,
  // 禮儀公司
  { key: 'extra.funeral_company', label: '公司名', width: 160 },
  { key: 'onsite_name', label: '姓名', width: 100 },
  { key: 'onsite_mobile', label: '手機', width: 130 },
  { key: 'onsite_phone', label: '電話', width: 130 },
  { key: 'onsite_fax', label: '傳真', width: 130 },
  { key: 'extra.contact_email', label: '信箱', width: 180 },
  ...MAIL,
  ...STATUS,
];

const AREA_DISPLAY_COLUMNS: Column[] = [
  ...HEAD,
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'holder_name', label: '單位名稱/持證者', width: 200 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'extra.applicant_ext', label: '分機', width: 60 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'applicant_name', label: '聯絡人', width: 120 },
  { key: 'extra.email', label: 'Email', width: 180 },
  { key: 'extra.event_name', label: '活動名稱', width: 180 },
  { key: 'use_address', label: '使用地址', width: 240 },
  { key: 'extra.floor_area', label: '坪數', width: 70 },
  { key: 'qty', label: '顯示器', width: 70 },
  ...PERIOD,
  { key: 'extra.songs', label: '使用歌曲', width: 200 },
  { key: 'extra.language', label: '語言', width: 80 },
  ...MAIL,
  ...STATUS,
];

const HALL_ROOM_COLUMNS: Column[] = [
  ...HEAD,
  { key: 'action_type', label: '辦理項目', width: 100 },
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'holder_name', label: '持證者', width: 200 },
  { key: 'applicant_name', label: '負責人', width: 120 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'extra.applicant_ext', label: '分機', width: 60 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'onsite_name', label: '聯絡人', width: 120 },
  { key: 'onsite_mobile', label: '手機', width: 130 },
  { key: 'extra.email', label: 'Email', width: 180 },
  { key: 'use_address', label: '使用地址', width: 240 },
  { key: 'holder_type', label: '授權內容', width: 110 },
  { key: 'extra.floor_area', label: '坪數', width: 70 },
  { key: 'qty', label: '客房數', width: 70 },
  ...PERIOD,
  ...MAIL,
  ...STATUS,
];

const ELECTION_COLUMNS: Column[] = [
  ...HEAD,
  // 申請人 / 主辦單位 / 持證者
  { key: 'apply_date', label: '申請日期', width: 100 },
  { key: 'holder_name', label: '主辦單位', width: 200 },
  { key: 'extra.holder_tax_id', label: '統一編號', width: 100 },
  { key: 'applicant_phone', label: '電話', width: 130 },
  { key: 'applicant_fax', label: '傳真', width: 130 },
  { key: 'use_address', label: '地址', width: 220 },
  // 競選 / 活動資料
  { key: 'extra.event_name', label: '活動名稱', width: 180 },
  { key: 'extra.venue', label: '活動地點', width: 160 },
  { key: 'extra.venue_address', label: '活動地址', width: 220 },
  { key: 'holder_type', label: '授權內容', width: 110 },
  { key: 'qty', label: '宣傳車輛數', width: 90 },
  { key: 'extra.songs', label: '演出曲目', width: 260 },
  { key: 'extra.language', label: '語言別', width: 80 },
  { key: 'extra.song_count', label: '總曲數', width: 70 },
  ...PERIOD,
  // 業務承辦人
  { key: 'extra.contact_org', label: '所屬單位', width: 160 },
  { key: 'onsite_name', label: '姓名', width: 100 },
  { key: 'extra.contact_title', label: '職稱', width: 90 },
  { key: 'onsite_mobile', label: '手機', width: 130 },
  { key: 'onsite_phone', label: '電話', width: 130 },
  { key: 'onsite_ext', label: '分機', width: 60 },
  { key: 'onsite_fax', label: '傳真', width: 130 },
  { key: 'extra.contact_email', label: 'E-mail', width: 180 },
  ...MAIL,
  ...STATUS,
];

// 類型 → 專屬欄位定義；未列者（電腦伴唱機 / 社區管委會 / 公益伴唱機）用通用 COLUMNS。
export const COLUMNS_BY_CATEGORY: Record<string, Column[]> = {
  SINGLE_EVENT: SINGLE_EVENT_COLUMNS,
  SELF_SERVICE_KTV: SELF_KTV_COLUMNS,
  STREET_ARTIST: STREET_ARTIST_COLUMNS,
  TRANSPORT: TRANSPORT_COLUMNS,
  PUBLIC_TRANSMIT: PUBLIC_TRANSMIT_COLUMNS,
  FUNERAL: FUNERAL_COLUMNS,
  AREA_DISPLAY: AREA_DISPLAY_COLUMNS,
  HALL_ROOM: HALL_ROOM_COLUMNS,
  ELECTION: ELECTION_COLUMNS,
};

export const columnsFor = (code: string): Column[] =>
  COLUMNS_BY_CATEGORY[code] ?? COLUMNS;

// 依欄位代號（含 "extra.<key>"）讀出 row 的值。
export function getCellValue(row: RecordRow, field: string): unknown {
  if (field.startsWith('extra.')) {
    const e = row.extra as Record<string, unknown> | null;
    return e ? e[field.slice('extra.'.length)] : undefined;
  }
  return (row as unknown as { [k: string]: unknown })[field];
}

export const fetchCategories = () => api<Category[]>('/api/categories');
export const fetchRecords = (code: string) =>
  api<RecordRow[]>(`/api/records?category_code=${encodeURIComponent(code)}`);

export const createRecord = (payload: Record<string, unknown>) =>
  api<RecordRow>('/api/records', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export interface HolderLookup {
  id: number;
  category_code: string;
  last_apply_date: string | null;
  period_end: string | null;
  holder_name: string | null;
  holder_type: string | null;
  tax_id: string | null;
  invoice_title: string | null;
  invoice_type: string | null;
  use_zip: string | null;
  use_address: string | null;
  mail_zip: string | null;
  mail_address: string | null;
  mail_recipient: string | null;
  mail_phone: string | null;
  applicant_name: string | null;
  applicant_id: string | null;
  applicant_mobile: string | null;
  applicant_phone: string | null;
  applicant_fax: string | null;
  onsite_name: string | null;
  onsite_mobile: string | null;
  onsite_phone: string | null;
  onsite_ext: string | null;
  onsite_fax: string | null;
}

export const lookupHolder = (q: string, limit = 5) =>
  api<HolderLookup[]>(
    `/api/records/lookup?q=${encodeURIComponent(q)}&limit=${limit}`,
  );

export interface UndoResult {
  record_id: number;
  field: string;
  previous_value: string | null;
  restored_value: string | null;
  also_reverted: string[];
  record: RecordRow;
}

export const undoLastEdit = () =>
  api<UndoResult>('/api/records/undo', { method: 'POST' });

export const deleteRecord = (id: number) =>
  api<{ id: number; deleted: boolean }>(`/api/records/${id}`, { method: 'DELETE' });

export const restoreRecord = (id: number) =>
  api<RecordRow>(`/api/records/${id}/restore`, { method: 'POST' });

export const fetchDeleted = (code: string) =>
  api<RecordRow[]>(`/api/records/deleted?category_code=${encodeURIComponent(code)}`);
