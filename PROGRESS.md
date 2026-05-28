# TMCA 音樂版權授權系統 — 製作進度

> 社團法人台灣音樂著作權集體管理協會 — 內部作業系統
> 對應文件：ADR-001 / ADR-002 / SYSTEM-DESIGN.md
> 更新日期：2026-05-23

---

## 一、總覽

| 項目 | 狀態 |
|---|---|
| 整體進度 | 8 個 Phase 中 **6 個完成**，2 個未開工（Phase 5 證書套印、Phase 6 寄信檔） |
| 後端核心 | ✅ 認證、權限、案件總表、續約偵測、發票配號、搜尋、報表皆可運作 |
| 資料庫 | ✅ 已匯入 110–115 年總表共 **14,610 筆**真實資料 |
| 自動化測試 | ✅ Tier 1 + Tier 2 共 **143 通過 / 1 xfail**（單元 + 整合）|
| 待補 | 證書 Word 套印、承辦寄信檔、前端 / E2E / 性能測試（Tier 3）|

---

## 二、技術堆疊

| 層級 | 技術 |
|---|---|
| 前端 | React 18 + Vite + TypeScript + TailwindCSS（已改用純 HTML table，棄用 Univer）|
| 後端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic |
| 資料庫 | PostgreSQL 15（含 `search_vec` 全文搜尋 generated column）|
| 排程 | APScheduler（每日續約狀態重算）|
| 反向代理 | Caddy 2（自動 HTTPS）|
| 部署 | Docker Compose（4 service）|
| 套印產出 | openpyxl（發票 xlsx）、python-docx / docxtpl（證書 Word，**尚未接線**）|

---

## 三、Phase 進度明細

### ✅ Phase 0 — 專案骨架
Docker Compose 四服務編排、Caddyfile、FastAPI 骨架、React + Vite 前端骨架、健康檢查 `/api/health`。

### ✅ Phase 1 — 認證 + 角色
- JWT 認證（Cookie + Bearer 雙模式）、bcrypt 密碼雜湊
- 登入頁、`ProtectedRoute` 路由守門
- **5 個角色**：承辦 A（單場次）、承辦 B（其他 11 類）、會計、核發、Admin
- 角色 × 12 category 的**編輯欄位白名單**（`app/core/permissions.py`）
- 後續強化：核發角色開放全欄位編輯（commit `0b15a88`）

### ✅ Phase 2 — Excel 匯入
- `scripts/import_excel.py` 把「110-115年 總表.xlsx」匯入 → **14,610 筆**
- `scripts/seed_categories.py` 種 12 個 category、`seed_users.py` 種 5 帳號
- 過程中針對真實資料修正 schema：
  - 放寬 `action_type` CHECK（真實資料 20+ 種值）
  - `serial_no` String(400) → Text（多機台條目超長）
  - 移除 `cert_no` UNIQUE（來源有 77 組重複、155 筆受影響）
  - 主動加寬電話 / 姓名 / 型態等字串欄位
- 對照文件：`IMPORT-MAPPING.md`

### ✅ Phase 3 — 主總表介面
- **Phase 3a**：原本用 Univer 試算表元件，因 sizing / 初始化問題改為**純 HTML table**
  - 12 個分類 tab × 41 欄、篩選、500 列上限（`ROW_CAP`）
- **Phase 3b**：
  - 可編輯儲存格（`EditableCell`）+ 角色欄位白名單 + `audit_log` 稽核
  - 還原功能 — Ctrl+Z / ⌘Z + ↶ 還原按鈕（commit `ab420e8`）
  - 新建案件 Modal、「持證者」欄位自動帶入
  - 排序修正：新建案件 `NULLS FIRST` 避免被前端列上限截掉

### ✅ Phase 4 — 續約偵測 + 狀態燈
- `app/services/renewals.py` 偵測即將到期案件
- 紅燈定義收斂為「**將要到期（today..+30 天）**」，不含已過期積壓
- APScheduler 每日自動重算（`app/services/scheduler.py`）
- `/renewals` 頁、依月份 / category 篩選、summary
- 權限：限承辦 / admin 才能看續約表（commit `44d3aa2`）
- ⚠️ 性能觀察：14,610 筆重算 **2.89s**，貼著 3s 目標上限

### ⬜ Phase 5 — 核發 Word 套印（**尚未實作**）
- `templates/證書/` 已備妥 **27 個證書模板**（正背面 docx + 套印 xlsx）
- 後端尚無證書產生程式碼（`python-docx` / `docxtpl` 已在 requirements，但未接線）
- 需求：核發角色選案件 → 套印對應證書 Word

### ⬜ Phase 6 — 承辦寄信檔（**尚未實作**）
- 需求：產生寄信用 Word + 信封套印
- 尚未開工

### ✅ Phase 7 — 搜尋 + 報表
- 全欄位搜尋（PostgreSQL `search_vec` generated column）
- 代辦人交叉查詢、auth 守門
- 報表 dashboard（`/reports`），限會計 / admin（commit `3ef23e6`）
- 修正：`ORDER BY DESC NULLS LAST` 語法錯誤

### 🟡 Phase 8 — 部署 SOP + Caddy HTTPS（部分完成）
- `docker-compose.yml`、`Caddyfile`、frontend `nginx.conf` 已就緒
- 完整部署 SOP 文件與正式上線流程待整理

---

## 四、額外完成：發票功能（介於 Phase 4–7）

> 不在原 8 Phase 清單，依實際作業流程補做。

- 會計專用 `/invoices` 頁 + `GET /api/invoices/pending`（commit `57d3865`）
- `app/services/invoices.py`：讀 `invoice_template.xlsx` 模板 → 填明細 → **以 `SELECT FOR UPDATE` 鎖序號配發票號**
- 12 category → 品名對應（公開傳輸 / 播送 / 演出授權費）
- 含稅金額自動換算未稅單價（÷1.05）、防重複開立
- 開立改為**純配號 + audit_log**，不再寫回 record（commit `10c34be`）
- 新增 `invoice_sequence` 資料表 + migration `006_invoice_sequence.py`

### 待決議：`invoice_no` 清空是否翻回紅燈
- 位置：`app/api/records.py`
- 現況：填入發票號 → 燈號翻綠（單向）；清空不會翻回紅
- 該測試標 `@pytest.mark.xfail`，等業務決定要單向或雙向同步

---

## 五、測試現況

| 區塊 | 測試數 | 通過 | xfail | 時間 |
|---|---:|---:|---:|---:|
| Tier 1 — 單元測試 | 81 | 81 | 0 | 2.6s |
| Tier 2 — 整合測試 | 63 | 62 | 1 | 15.6s |
| **總計** | **144** | **143** | **1** | 18.5s |

- 涵蓋：民國年換算、bcrypt / JWT、5 角色權限白名單、續約規則、auth flow、records 副作用、搜尋
- 指令：`docker compose exec backend pytest`
- 詳見 `TEST-REPORT.md` / `TESTING-STRATEGY.md`

### 未完成（Tier 3，上線前清單）
- ❌ 前端測試（Vitest 未設定）
- ❌ E2E（Playwright 已裝、有雛形未跑通）
- ❌ 性能壓測（100k 筆 < 5s）
- ❌ Excel 匯入冪等性測試、Coverage 報告

---

## 六、下一步建議優先序

1. **Phase 5 證書 Word 套印** — 27 模板已備妥，是核發角色的核心缺口
2. **Phase 6 寄信檔** — 承辦作業最後一段
3. 決議 `invoice_no` 清空燈號行為（4.1）
4. Phase 8 完整部署 SOP + 上線前改預設密碼
5. Tier 3 測試補完（前端 / E2E / 性能）

---

## 七、預設帳號

| 角色 | username | 密碼 |
|---|---|---|
| 承辦 A（單場次） | `officer_a` | `Tmca0001!` |
| 承辦 B（其他 11 類） | `officer_b` | `Tmca0001!` |
| 會計 | `accountant` | `Tmca0001!` |
| 核發 | `issuer` | `Tmca0001!` |
| Admin | `admin` | `Tmca0001!` |

> ⚠️ 上線前務必更改全部預設密碼。
