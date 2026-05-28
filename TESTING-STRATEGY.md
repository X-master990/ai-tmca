# TMCA 系統 — 測試策略

> 對應 ADR-001 / ADR-002 / SYSTEM-DESIGN.md，涵蓋目前已實作功能。

## 一、現有功能盤點

### Backend（FastAPI）

| 模組 | 端點 / 函式 | 主要邏輯 |
|---|---|---|
| **Auth** | `POST /api/auth/login`、`GET /api/auth/me`、`POST /api/auth/logout` | bcrypt 驗證、JWT 簽發、cookie 下發 |
| **Categories** | `GET /api/categories` | 列出 12 個申請類型 |
| **Records** | `GET /api/records`、`GET /api/records/permissions`、`PATCH /api/records/{id}` | CRUD + 欄位白名單權限 |
| **Renewals** | `GET /api/renewals`、`POST /api/renewals/recompute` | 續約名單 + 觸發重算 |
| **Reports** | `GET /api/reports/summary` | 月/年彙總 |
| **Search** | `GET /api/search`、`GET /api/search/agents` | 全欄位搜尋 + 代辦人交叉 |
| **Services** | `services/renewals.compute()` | 一條 UPDATE 把 14k 筆續約狀態算完 |
| **Services** | `services/scheduler` | APScheduler 排程（每日 06:00 跑續約偵測） |
| **Utils** | `utils/roc_date.roc_to_ad()` `ad_to_roc()` | 民國年 ↔ 西元 |
| **Security** | `core/security` | bcrypt hash、JWT encode/decode |
| **Permissions** | `core/permissions` | 角色 → 可寫欄位白名單 |
| **Scripts** | `seed_users`、`seed_categories`、`import_excel` | 一次性 |

### Frontend（React + Vite）

| 頁面 / 元件 | 角色 |
|---|---|
| `pages/Login` | 登入頁 |
| `pages/Home` | 角色預設首頁 |
| `pages/Records` | 總表（Univer 試算表 + 12 個 tab） |
| `pages/Renewals` | 續約名單（卡片 + Excel 模式） |
| `pages/Search` | 全欄位搜尋、代辦人交叉 |
| `pages/Reports` | 報表 |
| `components/ProtectedRoute` | 角色路由保護 |
| `components/UniverSheet` | Excel-like 試算表封裝 |
| `components/RecordsTable` | 表格元件 |
| `components/StatusDot` | 紅綠燈點 |
| `store/auth` | Zustand auth state |
| `api/*` | fetch wrapper、records / renewals / reports / search / permissions |

---

## 二、測試金字塔（針對 TMCA 規模調整）

```
       ┌───────────────────┐
       │   E2E  (10-15)    │  ← Playwright；4 個角色關鍵旅程
       ├───────────────────┤
       │ Integration (40+) │  ← FastAPI TestClient + 真 PG（docker-compose）
       ├───────────────────┤
       │   Unit  (80+)     │  ← pytest（後端純函數）+ Vitest（前端純元件）
       └───────────────────┘
```

**為何不是 1:10:100 的經典金字塔？** TMCA 是內部系統，4 人團隊用，業務邏輯集中在後端、且很多邏輯就是「資料變換」。所以**整合測試比單元測試重要**，因為「PATCH /records/{id} 同時改 invoice_no → 自動翻 issuance_status」這種行為要在 DB 真環境才測得準。

---

## 三、Backend 測試清單

### 3.1 Unit Tests（pytest）

**`tests/unit/test_roc_date.py`** — 民國年轉換
```python
def test_roc_to_ad_basic():
    assert roc_to_ad("110.11.23") == date(2021, 11, 23)
    assert roc_to_ad("114/05/16") == date(2025, 5, 16)
    assert roc_to_ad("1140516") == date(2025, 5, 16)  # 7-digit

def test_roc_to_ad_invalid():
    assert roc_to_ad("") is None
    assert roc_to_ad(None) is None
    assert roc_to_ad("abc") is None
    assert roc_to_ad("110.13.45") is None  # 月日越界

def test_ad_to_roc_roundtrip():
    d = date(2021, 11, 23)
    assert roc_to_ad(ad_to_roc(d)) == d
```
**邊界：** 民國 0 年、跨千禧年、單位數月日、leading zero、UTF 全形數字（要不要支援？）。

**`tests/unit/test_security.py`** — bcrypt + JWT
```python
def test_password_roundtrip():
    h = hash_password("Tmca0001!")
    assert verify_password("Tmca0001!", h) is True
    assert verify_password("wrong", h) is False

def test_jwt_encode_decode():
    token = create_access_token({"user_id": 1, "role": "officer_a"})
    decoded = decode_token(token)
    assert decoded["user_id"] == 1
    assert decoded["role"] == "officer_a"

def test_jwt_expired_returns_none(monkeypatch):
    token = create_access_token({"user_id": 1}, ttl_hours=-1)  # 立刻過期
    assert decode_token(token) is None

def test_jwt_tampered_returns_none():
    token = create_access_token({"user_id": 1}) + "tamper"
    assert decode_token(token) is None
```

**`tests/unit/test_permissions.py`** — 欄位白名單
```python
def test_accountant_can_write_invoice_fields():
    assert can_write("accountant", "invoice_no") is True
    assert can_write("accountant", "use_address") is False

def test_officer_a_can_write_all():
    for f in ALL_FIELDS:
        assert can_write("officer_a", f) is True

def test_viewer_writes_nothing():
    for f in ALL_FIELDS:
        assert can_write("viewer", f) is False
```

**`tests/unit/test_renewals_logic.py`** — 純函數版的續約規則
```python
def test_classify_status_already_renewed():
    # 同 holder 有 period_end > 此筆 → 綠
    rec = make_rec(period_end="2025-12-31")
    others = [make_rec(holder_name=rec.holder_name, period_end="2026-12-31")]
    assert classify(rec, others) == "綠"

def test_classify_status_imminent_red():
    # 30 天內到期、無續約 → 紅
    rec = make_rec(period_end=today + timedelta(days=20))
    assert classify(rec, []) == "紅"

def test_classify_status_far_future_gray():
    rec = make_rec(period_end=today + timedelta(days=200))
    assert classify(rec, []) == "灰"

def test_classify_handles_tax_id_null_match():
    # tax_id 任一為 NULL 視為相符
    rec = make_rec(tax_id=None, period_end="2025-12-31")
    others = [make_rec(holder_name=rec.holder_name, tax_id="12345678", period_end="2026-12-31")]
    assert classify(rec, others) == "綠"
```

### 3.2 Integration Tests（FastAPI TestClient + 真 PG）

用 `pytest-postgresql` 或在 docker-compose 多開一個 `db_test`（不同 port），每個 test class 用 transaction rollback。

**`tests/integration/test_auth_flow.py`**
```python
def test_login_returns_cookie(client, seeded_users):
    r = client.post("/api/auth/login",
                   json={"username": "officer_a", "password": "Tmca0001!"})
    assert r.status_code == 200
    assert "access_token" in r.cookies
    assert r.json()["user"]["role"] == "officer_a"

def test_login_wrong_password(client, seeded_users):
    r = client.post("/api/auth/login",
                   json={"username": "officer_a", "password": "wrong"})
    assert r.status_code == 401

def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401

def test_logout_clears_cookie(authed_client):
    r = authed_client.post("/api/auth/logout")
    assert r.status_code == 200
    r2 = authed_client.get("/api/auth/me")
    assert r2.status_code == 401
```

**`tests/integration/test_records_permissions.py`** ← 最重要
```python
def test_accountant_cannot_change_use_address(client_as_accountant, sample_record):
    r = client_as_accountant.patch(
        f"/api/records/{sample_record.id}",
        json={"use_address": "改的地址"}
    )
    assert r.status_code == 403
    assert "use_address" in r.json()["detail"]

def test_accountant_can_change_invoice_no(client_as_accountant, sample_record):
    r = client_as_accountant.patch(
        f"/api/records/{sample_record.id}",
        json={"invoice_no": "TC99999999"}
    )
    assert r.status_code == 200
    assert r.json()["invoice_no"] == "TC99999999"

def test_officer_a_can_change_use_address(client_as_officer_a, sample_record):
    r = client_as_officer_a.patch(
        f"/api/records/{sample_record.id}",
        json={"use_address": "改的地址"}
    )
    assert r.status_code == 200

def test_officer_a_cannot_edit_officer_b_category(client_as_officer_a, ktv_record):
    # SINGLE_EVENT 給 A，其他給 B；A 編 KTV 應該被擋
    r = client_as_officer_a.patch(f"/api/records/{ktv_record.id}", json={"note": "改"})
    assert r.status_code == 403
```

**`tests/integration/test_records_side_effects.py`** — 副作用
```python
def test_setting_invoice_no_flips_issuance_status(client_as_issuer, red_record):
    """填入發票號碼 → issuance_status 應變綠"""
    assert red_record.issuance_status == "紅"
    r = client_as_issuer.patch(
        f"/api/records/{red_record.id}",
        json={"invoice_no": "AB12345678"}
    )
    assert r.status_code == 200
    assert r.json()["issuance_status"] == "綠"

def test_clearing_invoice_no_flips_back_to_red(client_as_issuer, green_record):
    r = client_as_issuer.patch(
        f"/api/records/{green_record.id}",
        json={"invoice_no": ""}
    )
    assert r.json()["issuance_status"] == "紅"

def test_patch_writes_audit_log(client_as_officer_a, sample_record, db):
    client_as_officer_a.patch(
        f"/api/records/{sample_record.id}",
        json={"note": "新註記"}
    )
    logs = db.query(AuditLog).filter_by(record_id=sample_record.id).all()
    assert any(l.field_name == "note" and l.new_value == "新註記" for l in logs)
```

**`tests/integration/test_renewals.py`**
```python
def test_renewals_pending_list_excludes_renewed(client, db):
    holder = "玉亭餐廳"
    # 舊合約：到期日 2026-05-14
    old = make_record(holder_name=holder, period_end="2026-05-14")
    # 新合約：到期日 2027-05-14（= 已續約）
    new = make_record(holder_name=holder, period_end="2027-05-14")
    db.add_all([old, new]); db.commit()

    # 跑偵測
    client.post("/api/renewals/recompute")

    r = client.get("/api/renewals?month=5&year=2026&status=pending")
    holders = [x["holder_name"] for x in r.json()["items"]]
    assert holder not in holders  # 已被續約 → 不在 pending

def test_renewals_visibility_only_officers(client_as_accountant):
    r = client_as_accountant.get("/api/renewals?month=5&year=2026")
    assert r.status_code == 403
```

**`tests/integration/test_search.py`**
```python
def test_search_holder_name_full_text(client, sample_records):
    r = client.get("/api/search?q=玉亭")
    assert r.status_code == 200
    titles = [x["holder_name"] for x in r.json()["items"]]
    assert any("玉亭" in t for t in titles)

def test_search_agent_lists_companies(client, multi_company_agent):
    """同一代辦人代辦多家公司"""
    r = client.get(f"/api/search/agents?name={multi_company_agent.name}")
    companies = r.json()
    assert len(companies) >= 2
```

### 3.3 服務層測試

**`tests/integration/test_renewal_service.py`**
```python
def test_compute_renewal_status_perf(db, bulk_14k_records):
    """14k 筆紀錄全部重算 < 3 秒"""
    t0 = time.perf_counter()
    compute_renewal_status_for_all(db)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0

def test_renewal_handles_null_period_end(db):
    rec = make_record(period_end=None)
    db.add(rec); db.commit()
    compute_renewal_status_for_all(db)
    db.refresh(rec)
    assert rec.renewal_status == "灰"
```

### 3.4 資料匯入測試

**`tests/integration/test_import_excel.py`**
```python
def test_import_real_total_xlsx(db):
    """跑 110-115年 總表.xlsx 真實檔案"""
    count = import_xlsx("fixtures/110-115年 總表.xlsx", db)
    assert count > 15000  # 預估 ~15728
    # 隨機抽 5 筆驗欄位
    sample = db.query(Record).limit(5).all()
    assert all(s.cert_no for s in sample)

def test_import_handles_roc_dates(db):
    """民國年欄位正確轉成西元 date"""
    import_xlsx("fixtures/sample.xlsx", db)
    rec = db.query(Record).first()
    assert isinstance(rec.apply_date, date)
    assert rec.apply_date.year >= 2021  # 民國 110 = 2021

def test_import_idempotent(db):
    """跑兩次匯入不應產生重複"""
    import_xlsx("fixtures/sample.xlsx", db)
    n1 = db.query(Record).count()
    import_xlsx("fixtures/sample.xlsx", db)
    n2 = db.query(Record).count()
    assert n1 == n2
```

---

## 四、Frontend 測試清單

### 4.1 Unit / Component（Vitest + React Testing Library）

**`src/components/__tests__/StatusDot.test.tsx`**
```tsx
test('renders green for 綠', () => {
  render(<StatusDot status="綠" />);
  expect(screen.getByRole('status')).toHaveClass('bg-ok');
});

test('renders red for 紅', () => {
  render(<StatusDot status="紅" />);
  expect(screen.getByRole('status')).toHaveClass('bg-warn');
});

test('renders gray for null/灰', () => {
  render(<StatusDot status={null} />);
  expect(screen.getByRole('status')).toHaveClass('bg-slate-300');
});
```

**`src/components/__tests__/ProtectedRoute.test.tsx`**
```tsx
test('redirects to /login when not authed', () => {
  const { container } = renderWithRouter(
    <ProtectedRoute><div>Secret</div></ProtectedRoute>,
    { initialUser: null }
  );
  expect(container).not.toHaveTextContent('Secret');
});

test('renders children when authed', () => {
  const { getByText } = renderWithRouter(
    <ProtectedRoute><div>Secret</div></ProtectedRoute>,
    { initialUser: { role: 'officer_a' } }
  );
  expect(getByText('Secret')).toBeInTheDocument();
});

test('redirects when role not allowed', () => {
  const { container } = renderWithRouter(
    <ProtectedRoute allowedRoles={['admin']}>
      <div>AdminOnly</div>
    </ProtectedRoute>,
    { initialUser: { role: 'officer_a' } }
  );
  expect(container).not.toHaveTextContent('AdminOnly');
});
```

**`src/api/__tests__/records.test.ts`** — fetch wrapper（用 MSW mock 後端）
```ts
test('listRecords passes filter params correctly', async () => {
  server.use(
    rest.get('/api/records', (req, res, ctx) => {
      expect(req.url.searchParams.get('category')).toBe('COMPUTER_KARAOKE');
      expect(req.url.searchParams.get('page')).toBe('2');
      return res(ctx.json({ items: [], total: 0 }));
    })
  );
  await listRecords({ category: 'COMPUTER_KARAOKE', page: 2 });
});
```

### 4.2 Page-level interaction tests

**`src/pages/__tests__/Login.test.tsx`**
```tsx
test('login form submits and stores user', async () => {
  server.use(rest.post('/api/auth/login', (_, res, ctx) =>
    res(ctx.json({ user: { id: 1, username: 'officer_a', role: 'officer_a' } }))
  ));

  render(<App />);
  userEvent.type(screen.getByLabelText('帳號'), 'officer_a');
  userEvent.type(screen.getByLabelText('密碼'), 'Tmca0001!');
  userEvent.click(screen.getByRole('button', { name: '登入' }));

  await waitFor(() => {
    expect(useAuthStore.getState().user?.role).toBe('officer_a');
  });
});

test('login error shows message', async () => {
  server.use(rest.post('/api/auth/login', (_, res, ctx) =>
    res(ctx.status(401), ctx.json({ detail: '帳號或密碼錯誤' }))
  ));
  render(<App />);
  userEvent.type(screen.getByLabelText('帳號'), 'x');
  userEvent.type(screen.getByLabelText('密碼'), 'y');
  userEvent.click(screen.getByRole('button', { name: '登入' }));
  expect(await screen.findByText(/帳號或密碼錯誤/)).toBeInTheDocument();
});
```

---

## 五、E2E 測試（Playwright）

**最關鍵 6 條使用者旅程：**

1. `tests/e2e/officer_a_full_flow.spec.ts` — 承辦 A 認領→填表→送出→總表出現
2. `tests/e2e/officer_b_renewal_flow.spec.ts` — 承辦 B 進續約頁→看名單→產寄信檔
3. `tests/e2e/accountant_invoice_flow.spec.ts` — 會計開發票→列印明細表→檢查總表發票欄位
4. `tests/e2e/issuer_cert_flow.spec.ts` — 核發補登發票號→狀態燈轉綠→產證書 Word
5. `tests/e2e/permission_boundaries.spec.ts` — 4 角色嘗試 access 各自不能做的事
6. `tests/e2e/cross_role_data_flow.spec.ts` — 承辦填→會計看→核發看→證書產出（一筆資料貫穿）

範例：
```ts
test('完整單場次案件：承辦 A → 會計 → 核發', async ({ browser }) => {
  // 承辦 A 開新案
  const a = await loginAs(browser, 'officer_a');
  await a.goto('/');
  await a.click('text=快速填寫');
  await a.fill('[name=holder_name]', 'E2E測試樂團');
  await a.fill('[name=tax_id]', '99887766');
  await a.fill('[name=amount]', '1350');
  await a.click('text=送出 → 進入總表');

  // 會計開發票
  const b = await loginAs(browser, 'accountant');
  await b.goto('/');  // → /invoice
  await b.fill('[data-record-id=新案件] [name=invoice_no]', 'TC99999999');
  await expect(b.locator('text=已開立')).toBeVisible();

  // 核發產證書
  const c = await loginAs(browser, 'issuer');
  await c.goto('/');
  await c.click('text=⚡ 產生 Word');
  await expect(c.locator('text=證書檔(Word)')).toBeVisible();
});
```

---

## 六、Coverage 目標

| 區塊 | line coverage | 為什麼 |
|---|---|---|
| `app/core/*`（security、permissions） | **≥ 95%** | 安全關鍵 |
| `app/services/renewals.py` | **≥ 90%** | 業務核心邏輯 + 性能敏感 |
| `app/api/*` | **≥ 80%** | HTTP 層、權限驗證 |
| `app/utils/*` | **≥ 90%** | 純函數好測 |
| `app/models/*` | 不強制 | 主要靠 integration test 覆蓋 |
| 前端 `components/` | **≥ 70%** | 重要元件 |
| 前端 `pages/` | **≥ 50%** | 頁面整合行為走 E2E |

---

## 七、跑測試的方式

### 後端

```bash
# 進 backend container 跑
docker compose exec backend pytest                    # 全跑
docker compose exec backend pytest tests/unit/        # 只跑 unit
docker compose exec backend pytest -k renewal         # 名字含 renewal
docker compose exec backend pytest --cov=app          # 含 coverage
docker compose exec backend pytest --cov=app --cov-report=html
```

需要新增的開發依賴（加進 `requirements-dev.txt`）：
```
pytest==8.3.3
pytest-cov==5.0.0
pytest-asyncio==0.24.0
pytest-postgresql==6.1.1
httpx==0.27.2
```

### 前端

```bash
docker compose exec frontend npm test           # 跑 Vitest
docker compose exec frontend npm run test:cov   # 含 coverage
```

需加進 `frontend/package.json` devDependencies：
```json
{
  "vitest": "^2.1.4",
  "@testing-library/react": "^16.0.1",
  "@testing-library/user-event": "^14.5.2",
  "@testing-library/jest-dom": "^6.6.3",
  "msw": "^2.6.0",
  "jsdom": "^25.0.1"
}
```

### E2E（Playwright）

```bash
# 在 host machine（不在 container 內）
cd app/tests/e2e
npx playwright install        # 第一次
npx playwright test           # 跑全部
npx playwright test --ui      # 互動模式
```

---

## 八、CI（GitHub Actions 範本）

當你建好 GitHub repo 後，丟到 `.github/workflows/test.yml`：

```yaml
name: test
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: tmca
          POSTGRES_PASSWORD: test
          POSTGRES_DB: tmca_test
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r app/backend/requirements.txt -r app/backend/requirements-dev.txt
      - run: cd app/backend && alembic upgrade head
        env: { DATABASE_URL: 'postgresql+psycopg://tmca:test@localhost:5432/tmca_test' }
      - run: cd app/backend && pytest --cov=app --cov-fail-under=80

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd app/frontend && npm ci
      - run: cd app/frontend && npm test
      - run: cd app/frontend && npm run build  # 確認 TS 編譯通過

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - run: cd app && docker compose up -d
      - run: cd app && docker compose exec -T backend alembic upgrade head
      - run: cd app && docker compose exec -T backend python scripts/seed_users.py
      - run: cd app/tests/e2e && npx playwright install --with-deps && npx playwright test
```

---

## 九、優先順序建議（時間有限就先做這些）

### Tier 1（一定要寫，2-3 天）
1. `test_security.py` — bcrypt + JWT（auth 是安全底線）
2. `test_records_permissions.py` — 角色欄位白名單（會計動到總表就完蛋）
3. `test_records_side_effects.py` — 發票號 → 狀態燈翻轉（業務關鍵）
4. `test_renewals_logic.py` — 續約規則（高敏感、會誤判客戶）
5. `test_roc_date.py` — 民國年（轉錯整批資料毀掉）

### Tier 2（穩定後加，2-3 天）
6. `test_auth_flow.py` integration
7. `test_renewals.py` integration（含真 DB）
8. `test_search.py` integration
9. Frontend `ProtectedRoute.test.tsx`、`Login.test.tsx`

### Tier 3（上線前一週做）
10. 6 條 Playwright E2E 旅程
11. 性能測試：renewal recompute 對 100k 筆 < 5 秒
12. Visual regression（Percy / Chromatic）

---

## 十、不測什麼

- SQLAlchemy ORM 行為（信任 ORM）
- Vite/React 框架行為
- Caddy reverse proxy
- 第三方套件（docxtpl、openpyxl）— 假設它們已測過
- 一次性 scripts（`seed_users.py`、`import_excel.py` 只人工測過 1-2 次就好；當然 import_excel 的轉換邏輯可以另外抽出來測）

---

## 十一、目前覆蓋的 gap

對照功能盤點 §一，**還沒做的測試**：

- ❌ 所有 backend（目前 `tests/` 是空的）
- ❌ 所有 frontend（沒有 Vitest 設定）
- ❌ E2E（沒有 Playwright 設定）

建議：**從 Tier 1 開始**，2-3 天可以把最關鍵 5 個檔案寫完。要不要我直接寫 Tier 1 的測試檔案？
