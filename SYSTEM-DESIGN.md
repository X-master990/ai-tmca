# TMCA 音樂版權授權系統 — 系統設計書

**承接：** ADR-001、ADR-002
**版本：** v1.0（2026-05-16）
**狀態：** 待 Phase 0 動工前最後確認

---

## 一、需求重述

### 功能性需求

| 編號 | 功能 | 角色 | 優先級 |
|---|---|---|---|
| F-01 | 4 角色登入（officer_a / officer_b / accountant / issuer） | 全 | P0 |
| F-02 | 41 欄總表的 CRUD（12 個申請類型） | 承辦 A/B 全寫；會計 / 核發 限定欄位 | P0 |
| F-03 | 從現有 `110-115年 總表.xlsx` 匯入既有資料 | （一次性） | P0 |
| F-04 | 類 Excel 介面：儲存格直編、排序、篩選、凍結欄、多分頁 | 全 | P0 |
| F-05 | 續約自動偵測（基於 holder + period_end） | 系統 | P1 |
| F-06 | 續約狀態燈（紅 ≤30 天 / 綠已續約 / 灰無關） | 系統顯示 | P1 |
| F-07 | 「續約資料」分類頁：12 個月分頁 × 未續約 / 已續約 兩張子清單 | 承辦 | P1 |
| F-08 | 核發狀態燈（紅未輸發票號碼 / 綠已輸入） | 系統顯示 | P1 |
| F-09 | 核發 Word 套印：證書 + 信封（27 種模板依 category 對應） | 核發 | P1 |
| F-10 | 承辦寄信檔：續約通知函 + 信封（同代辦人合併批次） | 承辦 | P2 |
| F-11 | 全欄位搜尋（跨 12 個 category） | 全 | P2 |
| F-12 | 代辦人交叉查詢：「搜姓名 → 列出代辦的所有公司」 | 承辦 | P2 |
| F-13 | 稽核軌跡（誰、何時、改了什麼欄位） | 系統 | P2 |
| F-14 | 每日自動 PG dump → 異地備份 | 系統 | P1 |
| F-15 | 簡易報表：月/年產證書數、收入、續約率 | 全（唯讀） | P3 |

### 非功能性需求

| 維度 | 目標 |
|---|---|
| 同時上線使用者 | ≤ 4（峰值 6，預留遠端） |
| 資料量 | ~50,000 列總表、6 年成長 → 預估 5 年內到 100K 列 |
| 介面延遲 | 9 成操作 < 500ms；Word 產生 < 5s（單張） |
| 可用性 | 99%（每月停機 ≤ 7 小時，含維護） |
| 備份 RPO | 24 小時（每日凌晨 dump） |
| 備份 RTO | 4 小時（從 dump 還原可運作） |
| 瀏覽器支援 | Chrome / Edge / Safari 最新 2 個版本 |
| 行動裝置 | 不支援（內部桌機優先） |
| 中文 | 繁體中文 UI，全欄位 UTF-8 |

### 限制條件

- 4 人團隊、無專職 IT。
- 雲端部署於 DigitalOcean。
- 預算 ≤ NT$1,500/月。
- 沿用既有 Word 模板，不重寫。

---

## 二、High-Level 架構

### 元件圖

```
┌──────────────────────────────────────────────────────────┐
│                       Browser (4 users)                  │
│  React 18 SPA  •  Univer Spreadsheet  •  TailwindCSS     │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / JSON / WebSocket(可選)
                         │
┌────────────────────────┴─────────────────────────────────┐
│                    Caddy (reverse proxy, TLS)            │
│              :443 → frontend / :443/api → backend        │
└────────────────────────┬─────────────────────────────────┘
                         │
       ┌─────────────────┴────────────────────┐
       │                                      │
┌──────┴────────┐                  ┌──────────┴──────────────┐
│  Frontend     │                  │  Backend  FastAPI       │
│  Nginx + SPA  │                  │  Uvicorn ASGI worker x2 │
│  (靜態檔)     │                  │  APScheduler (排程)     │
└───────────────┘                  └──────────┬──────────────┘
                                              │
                            ┌─────────────────┼─────────────────┐
                            │                 │                 │
                  ┌─────────┴──────┐   ┌──────┴──────┐   ┌──────┴──────────┐
                  │  PostgreSQL 15 │   │  Volume     │   │  External       │
                  │  Managed       │   │  /var/tmca/ │   │  • Wasabi (備份)│
                  │  (DigitalOcean)│   │   ├─tmpl/   │   │  • Cloudflare   │
                  └────────────────┘   │   ├─out/    │   │    DNS          │
                                       │   └─backup/ │   └─────────────────┘
                                       └─────────────┘
```

### 資料流（請求生命週期）

```
1. user 在 Univer 編輯儲存格
2. onCellEdit → debounce 500ms → PATCH /api/records/{id}
3. FastAPI 驗 JWT → 驗 role 權限 → 驗欄位白名單
4. SQLAlchemy ORM UPDATE records SET col = :val WHERE id = :id
5. 同筆寫入 audit_log（before / after / user_id）
6. 觸發 hooks：
   - 若欄位 = invoice_no → 同筆 issuance_status = '綠'
   - 若欄位 = period_end → 排入「續約重新計算佇列」
7. 回 200 + 更新後 row
8. 前端 Univer 用 row 重繪該列
```

### API 對外介面（總覽）

| 模組 | 端點 | 方法 |
|---|---|---|
| Auth | `/api/auth/login` | POST |
| Auth | `/api/auth/me` | GET |
| Auth | `/api/auth/logout` | POST |
| Records | `/api/records` | GET（list, filter）/ POST（create） |
| Records | `/api/records/{id}` | GET / PATCH / DELETE |
| Records | `/api/records/bulk` | PATCH（批次更新） |
| Categories | `/api/categories` | GET（12 個分類定義） |
| Renewals | `/api/renewals` | GET（含 month、status 篩選） |
| Renewals | `/api/renewals/recompute` | POST（手動觸發重算） |
| Generate | `/api/generate/cert` | POST（依 record_id 產證書+信封） |
| Generate | `/api/generate/mail-batch` | POST（批次產通知函） |
| Search | `/api/search` | GET（全欄位、跨 category） |
| Templates | `/api/templates` | GET / POST（管理員上傳） |
| Audit | `/api/audit/{record_id}` | GET（單筆稽核） |
| Reports | `/api/reports/summary` | GET（月/年彙總） |

詳細請見 §四 API 設計。

---

## 三、資料模型詳細設計

### ER 概念

```
users ─┬─< audit_log >── records ──┬─< generated_files
       │                            │
       │                            ├─ category (查 categories)
       │                            └─ template (查 templates)
       │
       └─ login sessions（暫存於 JWT，不入庫）
```

### Full DDL

```sql
-- ============================================================
-- Migration 001: 初始 schema
-- ============================================================

-- 1. 使用者與權限
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(40) UNIQUE NOT NULL,
    password_hash   VARCHAR(120) NOT NULL,
    display_name    VARCHAR(40),
    role            VARCHAR(20) NOT NULL CHECK (role IN
                    ('officer_a','officer_b','accountant','issuer','viewer','admin')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_login_at   TIMESTAMP
);

-- 2. 分類定義
CREATE TABLE categories (
    code            VARCHAR(40) PRIMARY KEY,    -- 例：'COMPUTER_KARAOKE'
    name_zh         VARCHAR(40) NOT NULL,       -- '電腦伴唱機'
    sheet_name      VARCHAR(40),                -- 原 xlsx sheet 名（匯入用）
    assigned_role   VARCHAR(20) NOT NULL,       -- 'officer_a' or 'officer_b'
    sort_order      INTEGER
);

INSERT INTO categories VALUES
  ('COMPUTER_KARAOKE','電腦伴唱機','電腦伴唱機','officer_b',1),
  ('COMMUNITY_BOARD','社區管委會','社區管委會','officer_b',2),
  ('PUBLIC_KARAOKE','公益伴唱機','公益伴唱機','officer_b',3),
  ('SELF_SERVICE_KTV','自助KTV','自助KTV','officer_b',4),
  ('STREET_ARTIST','街頭藝人','街頭藝人','officer_b',5),
  ('TRANSPORT','交通運輸工具','交通運輸工具','officer_b',6),
  ('SINGLE_EVENT','單場次表演','單場次表演','officer_a',7),  -- 男生負責
  ('PUBLIC_TRANSMIT','公開傳輸','公開傳輸','officer_b',8),
  ('FUNERAL','告別式','告別式','officer_b',9),
  ('AREA_DISPLAY','坪數-顯示器','坪數-顯示器','officer_b',10),
  ('HALL_ROOM','大廳-宴會廳-客房','大廳-宴會廳-客房','officer_b',11),
  ('ELECTION','競選活動','競選活動','officer_b',12);

-- 3. 主表
CREATE TABLE records (
    id                  SERIAL PRIMARY KEY,
    category_code       VARCHAR(40) REFERENCES categories(code) NOT NULL,
    cert_no             VARCHAR(40) UNIQUE,
    issued_date         DATE,
    note                TEXT,

    invoice_date        DATE,
    invoice_type        VARCHAR(20),
    invoice_title       VARCHAR(200),
    tax_id              VARCHAR(20),
    invoice_no          VARCHAR(40),
    amount              INTEGER,

    source              VARCHAR(20),
    officer             VARCHAR(40),
    action_type         VARCHAR(20) CHECK (action_type IN
                        ('新申辦','續約','授權延長','補發','其他') OR action_type IS NULL),
    apply_date          DATE,

    applicant_name      VARCHAR(80),
    applicant_id        VARCHAR(20),
    applicant_mobile    VARCHAR(30),
    applicant_phone     VARCHAR(30),
    applicant_fax       VARCHAR(30),

    holder_name         VARCHAR(120),
    holder_type         VARCHAR(40),

    use_zip             VARCHAR(10),
    use_address         TEXT,

    onsite_name         VARCHAR(40),
    onsite_mobile       VARCHAR(30),
    onsite_phone        VARCHAR(30),
    onsite_ext          VARCHAR(20),
    onsite_fax          VARCHAR(30),

    qty                 INTEGER,
    brand               VARCHAR(80),
    serial_no           VARCHAR(400),     -- 多機號可能很長

    period_start        DATE,
    period_end          DATE,

    mail_type           VARCHAR(10) CHECK (mail_type IN ('掛號','平信') OR mail_type IS NULL),
    mail_zip            VARCHAR(10),
    mail_address        TEXT,
    mail_recipient      VARCHAR(80),
    mail_phone          VARCHAR(30),

    issuance_status     VARCHAR(10) DEFAULT '紅' CHECK (issuance_status IN ('紅','綠')),
    renewal_status      VARCHAR(10) CHECK (renewal_status IN ('紅','綠','灰') OR renewal_status IS NULL),

    -- 額外類型專用欄位（JSON 容納各類型 1-3 個特有欄位）
    extra               JSONB DEFAULT '{}'::jsonb,

    created_by          INTEGER REFERENCES users(id),
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_by          INTEGER REFERENCES users(id),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_records_category       ON records(category_code);
CREATE INDEX idx_records_holder         ON records(holder_name);
CREATE INDEX idx_records_tax_id         ON records(tax_id);
CREATE INDEX idx_records_period_end     ON records(period_end);
CREATE INDEX idx_records_invoice_no     ON records(invoice_no);
CREATE INDEX idx_records_applicant      ON records(applicant_name);
CREATE INDEX idx_records_issued_date    ON records(issued_date);

-- 全文搜尋：把多個欄位拼成 tsvector
ALTER TABLE records ADD COLUMN search_vec tsvector
    GENERATED ALWAYS AS (
        to_tsvector('simple',
            coalesce(cert_no,'') || ' ' ||
            coalesce(holder_name,'') || ' ' ||
            coalesce(applicant_name,'') || ' ' ||
            coalesce(tax_id,'') || ' ' ||
            coalesce(invoice_no,'') || ' ' ||
            coalesce(use_address,'') || ' ' ||
            coalesce(mail_address,''))
    ) STORED;
CREATE INDEX idx_records_search_vec ON records USING gin(search_vec);

-- 4. Word 模板
CREATE TABLE templates (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,         -- 例「A2電腦伴唱機證書-正面」
    type            VARCHAR(20) NOT NULL CHECK (type IN
                    ('cert_front','cert_back','envelope','notice')),
    category_code   VARCHAR(40) REFERENCES categories(code),
    file_path       VARCHAR(400) NOT NULL,         -- 相對 /var/tmca/templates/
    field_mapping   JSONB NOT NULL,                -- {jinja_var: db_column}
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 5. 已產出檔案紀錄
CREATE TABLE generated_files (
    id              SERIAL PRIMARY KEY,
    record_id       INTEGER REFERENCES records(id),
    template_id     INTEGER REFERENCES templates(id),
    file_path       VARCHAR(400) NOT NULL,         -- 相對 /var/tmca/output/
    generated_by    INTEGER REFERENCES users(id),
    generated_at    TIMESTAMP DEFAULT NOW(),
    download_count  INTEGER DEFAULT 0
);
CREATE INDEX idx_genfiles_record ON generated_files(record_id);

-- 6. 稽核
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    record_id       INTEGER REFERENCES records(id),
    user_id         INTEGER REFERENCES users(id),
    field_name      VARCHAR(40) NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_audit_record ON audit_log(record_id, changed_at DESC);
```

### 民國年處理

匯入時把「110.11.23」格式轉成 `DATE`：

```python
def roc_to_ad(roc_str: str) -> date | None:
    """民國年字串 → 西元 date。容錯：空字串、None、奇怪格式 → None"""
    if not roc_str or not isinstance(roc_str, str):
        return None
    parts = roc_str.replace('/', '.').split('.')
    if len(parts) != 3:
        return None
    try:
        roc_y, m, d = (int(x) for x in parts)
        return date(roc_y + 1911, m, d)
    except (ValueError, TypeError):
        return None
```

UI 顯示時保持民國年（前端 helper 函式）；DB 一律西元。

---

## 四、API 設計詳細

### 認證

#### `POST /api/auth/login`
```json
// Request
{ "username": "officer_a", "password": "..." }

// Response 200
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 28800,   // 8 小時
  "user": {
    "id": 1,
    "username": "officer_a",
    "display_name": "王小明",
    "role": "officer_a"
  }
}

// Response 401
{ "detail": "帳號或密碼錯誤" }
```

JWT 同時也透過 HttpOnly Cookie 下發，前端有 fetch wrapper 自動帶 Authorization header。

#### `GET /api/auth/me`
回目前登入 user info。401 = 未登入。

---

### Records CRUD

#### `GET /api/records`
查詢，支援多 filter：

```
GET /api/records?category=COMPUTER_KARAOKE&page=1&page_size=100&sort=apply_date.desc
GET /api/records?status=invoice_no_null     # 自訂 filter
GET /api/records?holder_name=玉亭餐廳
GET /api/records?period_end_lte=2026-06-15  # 範圍
```

```json
// Response
{
  "items": [ { /* record 完整欄位 */ }, ... ],
  "total": 9629,
  "page": 1,
  "page_size": 100,
  "has_more": true
}
```

#### `PATCH /api/records/{id}`
單欄或多欄更新。

```json
// Request
{
  "invoice_no": "TC20290007",
  "amount": 3675
}

// Response 200
{
  "id": 42,
  // ... 完整 row 更新後
  "issuance_status": "綠",   // 系統自動翻
  "updated_at": "2026-05-16T08:14:00Z"
}

// Response 403
{ "detail": "您的角色（accountant）無權編輯欄位 'use_address'" }
```

權限規則寫在 `permissions.py`：

```python
WRITABLE_FIELDS_BY_ROLE = {
    'officer_a':  ALL_FIELDS,
    'officer_b':  ALL_FIELDS,
    'accountant': {'invoice_date','invoice_type','invoice_title','tax_id',
                   'invoice_no','amount','note'},
    'issuer':     {'invoice_no','issued_date','note'},
    'viewer':     set(),
}
```

外加 `category` 拘束：`officer_a` 只能改 `category='SINGLE_EVENT'` 的列，`officer_b` 不能改 `SINGLE_EVENT`。

#### `POST /api/records`
新增一筆。Request body 同 PATCH 但需含 `category_code`。

#### `PATCH /api/records/bulk`
批次更新（用於 Univer「貼上整欄」）：

```json
{
  "updates": [
    { "id": 42, "fields": { "mail_type": "掛號" } },
    { "id": 43, "fields": { "mail_type": "平信" } }
  ]
}
```

並行寫入 audit_log，整批要嘛全成功要嘛全 rollback。

---

### 續約

#### `GET /api/renewals?month=5&year=2026&status=pending`

`status` 接受：
- `pending` → 未續約名單
- `done` → 已續約名單

```json
{
  "year": 2026,
  "month": 5,
  "status": "pending",
  "items": [
    {
      "id": 1234,
      "holder_name": "玉亭餐廳",
      "tax_id": "79841273",
      "period_end": "2026-05-14",
      "days_to_expire": -2,
      "applicant_name": "陳玉貞",
      "category_code": "COMPUTER_KARAOKE",
      "mail_recipient": "...",
      "mail_address": "...",
      "mail_type": "平信"
    }
  ],
  "total": 17
}
```

#### `POST /api/renewals/recompute`
立即重算所有列的 `renewal_status`。只有 admin / officer 可呼叫。回 202 + job_id。

---

### Word 套印

#### `POST /api/generate/cert`
```json
// Request
{ "record_id": 42 }

// Response 200
{
  "files": [
    {
      "type": "cert_front",
      "filename": "T1101100002_電腦伴唱機證書_正面.docx",
      "url": "/api/files/abc123/download",
      "size_bytes": 28160
    },
    {
      "type": "envelope",
      "filename": "T1101100002_信封.docx",
      "url": "/api/files/def456/download",
      "size_bytes": 15400
    }
  ],
  "generated_at": "2026-05-16T08:15:00Z"
}
```

實作：
1. 用 `record.category_code` 找對應的 `templates` 表中 `type='cert_front'` 的記錄
2. 讀 `field_mapping`，把 record 欄位填到 jinja 變數
3. `docxtpl.DocxTemplate(template_path).render(context).save(output_path)`
4. 寫 `generated_files` 表，回 download URL

#### `POST /api/generate/mail-batch`

```json
// Request
{
  "record_ids": [1234, 1235, 1240],
  "notice_type": "renewal_pending"  // or "renewal_done"
}

// Response 200
{
  "notice_file": { "filename": "115-05_續約通知函_合併.docx", "url": "/api/files/xyz/download" },
  "envelope_file": { "filename": "115-05_信封_合併.docx", "url": "/api/files/uvw/download" },
  "groups": [
    { "applicant_name": "張三", "companies": ["A公司","B公司"], "count": 2 },
    { "applicant_name": "李四", "companies": ["C公司"], "count": 1 }
  ]
}
```

同 `applicant_name` 自動合併為一份信件（信件正文列出他所有代辦公司）。

---

### 搜尋

#### `GET /api/search?q=玉亭&fields=holder_name,applicant_name`

利用 PG 的 `tsvector` 全文索引：

```sql
SELECT id, category_code, holder_name, applicant_name, tax_id
FROM records
WHERE search_vec @@ plainto_tsquery('simple', :q)
ORDER BY ts_rank(search_vec, plainto_tsquery('simple', :q)) DESC
LIMIT 100;
```

回 max 100 筆，按相關性排序。

#### `GET /api/search/applicant-companies?name=張三`

「代辦人交叉查詢」：

```sql
SELECT applicant_name, holder_name, category_code, COUNT(*) cnt
FROM records
WHERE applicant_name = :name
GROUP BY applicant_name, holder_name, category_code
ORDER BY cnt DESC;
```

---

## 五、前端架構

### 路由

```
/login                            登入頁
/                                 → redirect 到 /records 或角色預設頁
/records                          總表（Univer Sheet，12 個 tab）
/records/:category                預選某 category
/renewals                         續約資料分類頁
/renewals/:year/:month            單月名單
/mailing                          寄信檔產生頁
/search                           搜尋
/reports                          報表
/admin/users                      （admin）使用者管理
/admin/templates                  （admin）模板管理
```

### Component 樹

```
<App>
  <AuthProvider>
    <Router>
      <Layout>                                  /* nav + 角色 badge + 登出 */
        <Sidebar />                              /* 切換功能模組 */
        <main>
          <Outlet />                             /* 各頁進這 */
        </main>
      </Layout>
    </Router>
  </AuthProvider>

<RecordsPage>
  <CategoryTabs />                               /* 12 個 tab */
  <UniverSheet
    data={rows}
    columnsDef={fieldDef}
    readonly={!canEdit}
    cellStyle={(row) => statusColor(row)}        /* 紅綠燈染色 */
    onCellEdit={debouncedPatch}
  />
</RecordsPage>
```

### 狀態管理

- **TanStack Query**（react-query）做 server cache：每頁載入時 `useQuery(['records', category], fetch)`，PATCH 用 `useMutation` 並 optimistic update。
- **Zustand** 做輕量全域 state（目前角色、UI 偏好）。
- 不引入 Redux（過度設計）。

### Univer 整合要點

```tsx
import { Univer } from '@univerjs/core';
import { defaultTheme } from '@univerjs/design';
import { UniverFormulaEnginePlugin } from '@univerjs/engine-formula';
import { UniverSheetsPlugin } from '@univerjs/sheets';
import { UniverSheetsUIPlugin } from '@univerjs/sheets-ui';

const univer = new Univer({ theme: defaultTheme });
univer.registerPlugin(UniverFormulaEnginePlugin);
univer.registerPlugin(UniverSheetsPlugin);
univer.registerPlugin(UniverSheetsUIPlugin);
// 把 rows 灌進去、註冊 onChange handler
```

3 個關鍵客製：
1. **儲存格染色 hook**：監聽 `onCellChange` 觸發後端 PATCH，並依 `issuance_status` / `renewal_status` 自動染儲存格背景。
2. **欄位 type 約束**：日期欄位用 Univer 內建 date picker；下拉式（如 invoice_type、mail_type）用 data validation。
3. **讀寫權限**：依角色決定哪些欄位 `cellRange.locked = true`。

---

## 六、認證與授權

### 登入流程（sequence）

```
Browser              Frontend            Backend            DB
   │  /login           │                    │                 │
   │ ─────────────────▶│                    │                 │
   │                   │ POST /auth/login   │                 │
   │                   │ ──────────────────▶│ SELECT user     │
   │                   │                    │ ───────────────▶│
   │                   │                    │ ◀───────────────│
   │                   │                    │ bcrypt verify   │
   │                   │                    │ JWT sign        │
   │                   │ ◀── 200 + cookie ──│                 │
   │ ◀── redirect ─────│                    │                 │
   │  /records         │                    │                 │
   │ ─────────────────▶│ GET /records       │                 │
   │                   │ ──── + cookie ────▶│ verify JWT      │
   │                   │                    │ ───────────────▶│ SELECT
   │                   │                    │ ◀───────────────│
   │                   │ ◀── 200 + rows ────│                 │
```

### Token 策略

- JWT in HttpOnly + SameSite=Strict + Secure cookie。
- payload: `{ user_id, role, exp }`，8 小時 TTL。
- 不做 refresh token（4 人團隊不需要）；過期就重登。
- CSRF：因有 SameSite=Strict cookie + custom header `X-Requested-With: tmca-web` 雙重防護。

### 密碼

- bcrypt cost=12。
- 強制 8 字以上、含英數。
- 不做 2FA（內部小團隊 + JWT 短期）。
- 換密碼：在 `/admin/users/me/password` 頁面。

---

## 七、續約偵測演算法

### 詳細邏輯

```python
def compute_renewal_status_for_record(rec: Record, db: Session) -> str:
    """
    根據 'holder_name OR tax_id' 同單位，找有沒有 period_end > rec.period_end
    """
    if rec.period_end is None:
        return None  # 不適用

    same_unit = (
        db.query(Record.period_end)
        .filter(
            (Record.holder_name == rec.holder_name) |
            (Record.tax_id == rec.tax_id),
        )
        .filter(Record.id != rec.id)
        .filter(Record.period_end > rec.period_end)
        .first()
    )

    if same_unit:
        return '綠'  # 已續約

    today = date.today()
    if rec.period_end <= today + timedelta(days=30):
        return '紅'  # 即將/已到期、未續約

    return '綠'  # 還沒到期
```

### 排程

每日 06:00 跑 `compute_renewal_status_for_all()`：

```python
# backend/app/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(compute_renewal_status_for_all, 'cron', hour=6, minute=0)
scheduler.start()
```

### 邊界情況

| 情境 | 處理 |
|---|---|
| `period_end is NULL` | `renewal_status = NULL` |
| `holder_name` 是空字串、`tax_id` 是空字串 | fallback 用 `applicant_id`；都空 → 不比對 |
| 同一筆 record 自己跟自己比 | 排除 `id != rec.id` |
| 跨類型續約（例如 KTV 改成電腦伴唱機） | 仍視為同單位（用 holder+tax） |

---

## 八、Word 套印實作

### 範例 — 證書套印

模板 `證書/D2單場次表演證書-正面.docx` 內以 jinja 標記：

```
中華民國{{roc_period_start_y}}年{{period_start_m}}月{{period_start_d}}日至
中華民國{{roc_period_end_y}}年{{period_end_m}}月{{period_end_d}}日

持證者：{{ holder_name }}
證書編號：{{ cert_no }}
```

對應 `templates` 表的 `field_mapping`：

```json
{
  "cert_no": "cert_no",
  "holder_name": "holder_name",
  "period_start_y": "period_start.year",
  "period_start_m": "period_start.month",
  "period_start_d": "period_start.day",
  "roc_period_start_y": "period_start.year - 1911",
  "period_end_y": "period_end.year",
  "period_end_m": "period_end.month",
  "period_end_d": "period_end.day",
  "roc_period_end_y": "period_end.year - 1911"
}
```

### Pipeline

```python
def generate_cert(record_id: int, user_id: int, db: Session) -> List[GeneratedFile]:
    rec = db.query(Record).get(record_id)
    if not rec:
        raise HTTPException(404)

    # 找適用的模板（cert_front + envelope 同 category）
    tmpls = (
        db.query(Template)
        .filter(Template.category_code == rec.category_code)
        .filter(Template.type.in_(['cert_front','cert_back','envelope']))
        .filter(Template.is_active)
        .all()
    )

    results = []
    for t in tmpls:
        ctx = build_context(rec, t.field_mapping)   # dict
        doc = DocxTemplate(f'/var/tmca/templates/{t.file_path}')
        doc.render(ctx)
        out_path = f'/var/tmca/output/{rec.cert_no}_{t.name}.docx'
        doc.save(out_path)

        gf = GeneratedFile(
            record_id=rec.id, template_id=t.id,
            file_path=out_path, generated_by=user_id,
        )
        db.add(gf); db.flush()
        results.append(gf)

    db.commit()
    return results
```

### 27 種模板對應表（暫定）

| category_code | 模板名稱（檔案） |
|---|---|
| COMPUTER_KARAOKE | A2電腦伴唱機證書-正面.docx + A2電腦伴唱機證書-背面.docx + 信封 |
| SELF_SERVICE_KTV | B1自助式KTV證書-正面.docx + B2自助式KTV證書-背面.docx |
| SINGLE_EVENT | D2單場次表演證書-正面.docx + D2單場次表演證書-後面.docx |
| STREET_ARTIST | E1街頭藝人授權證書-正面.docx + E2街頭藝人授權證書-背面.docx |
| ELECTION | F4競選活動證書-正面.docx + F4競選活動證書-背面.docx |
| TRANSPORT | H1交通運輸工具證書-正面.docx + H1交通運輸工具證書-背面.docx |
| PUBLIC_TRANSMIT | 公開傳輸證書-正面.docx + 公開傳輸證書-背面.docx |
| AREA_DISPLAY | 音樂著作公開播送授權證書-坪數及顯示器.docx |
| HALL_ROOM | 音樂著作公開播送授權證書 -大廳、客房、宴會廳-正面.docx + -背面.docx |
| FUNERAL | （需用戶補） |
| COMMUNITY_BOARD | （需用戶補） |
| PUBLIC_KARAOKE | （需用戶補） |

Phase 5 啟動前要請 user 補齊。

---

## 九、Background Jobs

| Job | 頻率 | 內容 |
|---|---|---|
| `renewal_recompute` | 每日 06:00 | 重算所有 record 的 `renewal_status` |
| `pg_dump` | 每日 02:30 | `pg_dump` → gzip → 上傳 Wasabi |
| `cleanup_generated_files` | 每週日 03:00 | 刪除 90 天以前的 generated_files（DB 紀錄保留） |
| `health_check` | 每 5 分鐘 | 自我健康檢查、寫入 metric |

用 APScheduler 在後端 main process 跑（4 個 user 規模不需要 Celery）。

---

## 十、Deployment 拓樸

### docker-compose.yml（精簡）

```yaml
services:
  caddy:
    image: caddy:2
    ports: ["80:80","443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on: [frontend, backend]

  frontend:
    build: ./frontend
    expose: ["80"]

  backend:
    build: ./backend
    expose: ["8000"]
    env_file: .env
    volumes:
      - tmca_files:/var/tmca
    depends_on: [db]

  db:
    image: postgres:15-alpine
    env_file: .env
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"]
      interval: 10s

volumes:
  caddy_data:
  tmca_files:
  pg_data:
```

### Caddyfile

```
tmca.example.tw {
    encode gzip
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

### 環境變數（`.env.example`）

```
POSTGRES_DB=tmca
POSTGRES_USER=tmca
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql+asyncpg://tmca:changeme@db:5432/tmca
JWT_SECRET=replace-me-with-random-bytes
JWT_TTL_HOURS=8
WASABI_ACCESS_KEY=
WASABI_SECRET_KEY=
WASABI_BUCKET=tmca-backup
TIMEZONE=Asia/Taipei
```

### 部署 SOP（簡）

1. `ssh root@droplet-ip`
2. `git clone <repo>` → `cd tmca`
3. `cp .env.example .env` → 填密碼
4. `docker compose up -d`
5. `docker compose exec backend alembic upgrade head`
6. `docker compose exec backend python scripts/seed_users.py`
7. DNS A record 指過去 → Caddy 自動申請 HTTPS

---

## 十一、Performance 估算

### 載荷

- 4 user × 平均 10 操作/分 = 40 req/min = 0.7 req/s 平均
- 峰值（核發批次產 50 張證書）：~10 req/s 短脈衝

### DB 負載

- `records` 預估 100K 列、平均列大小 1.5 KB → 約 150 MB（含索引）。
- 全文搜尋 tsvector + GIN 索引 → 100ms 內回應。
- 續約偵測一次跑 100K 列：~3-5 秒（每日 06:00 跑、不阻塞使用者）。

### 系統資源

- DigitalOcean Droplet 2 GB RAM 估足：
  - frontend (nginx): ~50 MB
  - backend (uvicorn × 2 worker): ~300 MB
  - caddy: ~30 MB
  - 其餘 1.6 GB 給 OS / cache。
- Managed PG 1 GB plan 起步。

### 將來擴張

當總列數 > 500K 或 user > 20：
- Droplet 升級到 4 GB
- backend worker 加到 4 個
- 加 Redis 做 cache（目前不需要）

---

## 十二、Security 清單

| 類別 | 措施 |
|---|---|
| 密碼 | bcrypt cost 12 |
| Token | JWT in HttpOnly+SameSite=Strict+Secure cookie；TTL 8h |
| CSRF | SameSite=Strict + 自訂 header 雙保險 |
| XSS | React 預設 escape + DOMPurify 用於富文字（不太用到） |
| SQL Injection | SQLAlchemy ORM + parameterised queries（嚴禁 string interp） |
| 上傳檔案 | 模板上傳限 admin、限 .docx、檔名清洗、存非 web-served 目錄 |
| Rate limit | Caddy `rate_limit` 模組：登入 5 次/15min、API 100 次/min/user |
| HTTPS | Caddy 自動 Let's Encrypt |
| 機敏資料 | 身分證、電話：DB 加欄位 encrypt（pgcrypto）— Phase 2 之後再加 |
| 操作日誌 | `audit_log` 全 PATCH 都記錄 before/after |
| 備份加密 | Wasabi server-side encryption（內建） |

---

## 十三、Monitoring & 健康指標

最小可行（Phase 8）：

- 後端 `/api/health` 端點 → 檢查 DB 通、磁碟 > 1GB、JWT secret 已設
- Caddy access log → `/var/log/caddy/`
- Postgres slow query log（> 1s 紀錄）
- 每日健康檢查 cronjob → 失敗發 LINE 通知（透過 LINE Notify API）

進階（可選）：UptimeRobot 從外部 ping。

---

## 十四、Trade-off 記錄

| 決策 | 取 | 捨 |
|---|---|---|
| FastAPI 不選 Django | 輕量、async、自動 OpenAPI | 沒 admin 介面；自己寫 |
| Univer 不選 Handsontable | 開源免費、最像 Excel | 文件偏中文、英文社群小 |
| PostgreSQL 不選 SQLite | 多人並寫、全文索引 | 多一個服務要維運 |
| 41 欄共用 schema 不 JSON | 索引、查詢效率高 | 12 種類型獨特欄位用 `extra JSONB` 收 |
| 不引入 Celery | 4 user 不需要 | 將來重 IO 任務要換 |
| 沒有真正的 RBAC 框架 | 4 角色寫死最快 | 將來想新增角色要改 code |
| JWT 不做 refresh | 簡單 | 過期需重登 |

---

## 十五、未來會重新檢視

- **3 個月後**：續約偵測規則是否需要再客製（user 看實跑結果有沒有誤判）
- **6 個月後**：是否該加入「申請人線上申辦」對外功能（會大幅改變 schema）
- **1 年後**：總列數成長到 ~200K 時，重看 PG 索引、考慮分表
- **2 年後**：是否從自架轉到 Power Platform（看 user 維運成本實際感受）

---

## 十六、Open Questions（給 user）

1. 4 位使用者中，是否有人需要 admin 權限（管理使用者帳號、上傳模板）？目前假設「秘書長 / 理事長 = admin」。
2. 27+ 個證書模板，「告別式 / 社區管委會 / 公益伴唱機」對應檔案是哪幾個？（資料夾沒看到對應名稱的）
3. 一個 record 是否可能有「正面+背面」兩張證書？目前 schema 假設「一張 record → 一個 cert_no → 可產正面+背面+信封」三個檔案。
4. 既有 6 年資料（110-115）是否全匯入？或截取近 2 年？
5. 公司 IP 是否需要白名單限制（只准內網存取）？

回答後即可動 Phase 0。

