# TMCA 系統 — 測試執行報告

> 日期：2026-05-18
> 對應：[TESTING-STRATEGY.md](./TESTING-STRATEGY.md) Tier 1 + Tier 2

---

## 一、總覽

| 區塊 | 測試數 | 通過 | 失敗 | xfail | 時間 |
|---|---:|---:|---:|---:|---:|
| Tier 1 — Unit Tests | 81 | 81 | 0 | 0 | 2.6s |
| Tier 2 — Integration Tests | 63 | 62 | 0 | 1 | 15.6s |
| **總計** | **144** | **143** | **0** | **1** | **18.5s** |

**指令**：`docker compose exec backend pytest`

---

## 二、Tier 1 — Unit Tests

| 檔案 | 測試數 | 範圍 |
|---|---:|---|
| `tests/unit/test_roc_date.py` | 21 | 民國年 ↔ 西元年（含 7-digit、單位數月日、UTF 邊界、roundtrip） |
| `tests/unit/test_security.py` | 10 | bcrypt salt、JWT encode/decode、過期、竄改、payload 隔離 |
| `tests/unit/test_permissions.py` | 22 | 5 角色 × 12 category 編輯欄位白名單 + invariants |
| `tests/unit/test_renewals_logic.py` | 28 | 續約規則（純 Python 版本，鏡像 SQL 邏輯）+ 30 天邊界 parametrize |
| **小計** | **81** | |

**程式碼變更**：`app/services/renewals.py` 加了 `RenewalCandidate` dataclass + `classify_renewal_status()` 純函數版（SQL 版仍為 production path）。

---

## 三、Tier 2 — Integration Tests

### 基礎設施

- 獨立 test DB：`tmca_test`（同一 PG 容器、不同 database）
- 每測試外層 transaction + nested savepoint → app 內 `commit()` 只 commit 內層，測試結束 rollback 外層，互不污染
- FastAPI `TestClient` 不用 `with` block → 避免 lifespan 觸發 APScheduler
- session-scope autouse `_seed`：bcrypt 5 帳號 + 12 categories 只跑一次

### 結果

| 檔案 | 測試數 | 涵蓋 |
|---|---:|---|
| `tests/integration/test_auth_flow.py` | 10 | login / me / logout / Cookie / Bearer / 過期 token |
| `tests/integration/test_records_permissions.py` | 17 | 5 角色 PATCH × SINGLE_EVENT / KTV × 多欄位 + `/permissions` endpoint |
| `tests/integration/test_records_side_effects.py` | 11 | invoice_no ↔ issuance_status、audit_log、no-op、型態轉換 |
| `tests/integration/test_renewals.py` | 11 | recompute（admin 限定）、月份列表、category filter、summary |
| `tests/integration/test_search.py` | 14 | 全欄位搜尋、代辦人交叉、auth 守門 |
| **小計** | **63** | |

---

## 四、發現的問題

### 4.1 行為缺口 — `invoice_no` 清空不會翻紅燈

- **位置**：`app/api/records.py:129-134`
- **現況**：只實作「填入發票號 → `issuance_status` 翻 綠」單向
- **strategy 期望**：清空發票號 → `issuance_status` 翻回 紅（見 `test_clearing_invoice_no_flips_back_to_red`）
- **目前處理**：該測試標 `@pytest.mark.xfail(strict=True)`。Strategy 與 code 都是合理選項：
  - **修 code**（雙向同步）：使用者改錯後可以還原燈號狀態，邏輯對稱
  - **修 strategy**（單向）：發票一旦開立就有正式憑證，事後清空通常是誤操作，不應自動降級
- **待決議**

### 4.2 環境問題（已解決，記錄供後續參考）

| 事件 | 處置 |
|---|---|
| Docker daemon 卡住 | killall + 重啟 |
| 磁碟滿（`/` 100% capacity） | 使用者清空 + `docker system prune` |
| Containerd content store I/O error | 重啟 Docker Desktop 修復 |
| `pg_data` volume 在 prune 時被砍掉 | 重跑 `alembic upgrade head` + seed + `import_excel.py` 14,610 筆 |

---

## 五、性能觀察

| 項目 | 觀察值 | strategy 目標 | 結果 |
|---|---:|---:|---|
| 14,610 筆續約重算 | 2.89s | < 3s | ✅ 貼著邊過 |
| 全套測試執行 | 18.5s | — | ✅ |

⚠️ 續約重算 2.89s 已逼近 3s 目標上限。若資料量再成長 30% 以上，預估會破線；屆時需要考慮 partial recompute、indexing 強化、或分批處理。

---

## 六、目前覆蓋的缺口（Tier 3、未完成）

照 strategy §九 順序：

- ❌ Frontend 測試（Vitest 未設定）
  - `StatusDot.test.tsx`、`ProtectedRoute.test.tsx`、`Login.test.tsx`、`api/records.test.ts`（MSW mock）
- ❌ E2E 測試（Playwright 已裝、有 demo.spec.ts 雛形但未完整跑通）
  - 4 角色關鍵旅程、cross-role data flow
- ❌ 性能壓力測試（100k 筆 < 5s）
- ❌ Visual regression
- ❌ `test_import_excel.py`（資料匯入冪等性 / 民國年正確性）
- ❌ Coverage 報告（`pytest --cov` 未開）

---

## 七、跑測試的指令

```bash
# 全套
docker compose exec backend pytest

# 只 unit（不需 DB）
docker compose exec backend pytest tests/unit/

# 只 integration（需要 db container 起來）
docker compose exec backend pytest tests/integration/

# 過濾
docker compose exec backend pytest -k renewal
docker compose exec backend pytest tests/integration/test_auth_flow.py::TestLogin -v

# 加 coverage（要先 pip install pytest-cov）
docker compose exec backend pytest --cov=app --cov-report=term
```

**注意**：backend Dockerfile 用 `COPY . .`，修改 `tests/` 後要 `docker compose build backend` 或 `docker cp` 進去才會生效。建議加 `./backend:/app` 進 compose dev override。

---

## 八、結論

✅ **Tier 1 + Tier 2 已可上線標準**

- 後端核心邏輯（auth、permissions、renewals、records、search）有 143 個自動化測試覆蓋
- 一個已記錄的設計決定待議（4.1）
- 剩餘工作集中在前端 + E2E + 性能，屬於 Tier 3 上線前一週的清單
