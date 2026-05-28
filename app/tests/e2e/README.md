# TMCA E2E 測試

放從瀏覽器（或純 HTTP）跑的端對端測試。對應策略文件：
[`../../TESTING-STRATEGY.md`](../../TESTING-STRATEGY.md)

---

## 檔案

| 檔案 | 角色 | 跑多久 |
|---|---|---:|
| `happy-path.spec.ts` | 真瀏覽器：officer_a 點 UI 新增 → accountant 補發票 → issuer 看綠燈 | ~30s |
| `happy-path-api.spec.ts` | 純 HTTP smoke test，不開瀏覽器 | ~3s |
| `demo.spec.ts` | 給螢幕錄影用的 narrate 版（既有） | ~3 min |

---

## 前置

1. 系統要在跑：
   ```bash
   cd app
   docker compose up -d
   docker compose exec backend python scripts/seed_users.py     # 第一次跑用
   docker compose exec backend python scripts/seed_categories.py
   ```

2. 確認 http://localhost 開得起來、五個帳號可登入：
   `officer_a` `officer_b` `accountant` `issuer` `admin`（密碼一律 `Tmca0001!`）

---

## 跑 happy-path

```bash
cd app/tests/e2e
npx playwright test happy-path.spec.ts --headed
```

`--headed` 會開瀏覽器讓你看著跑。確認沒問題後可拿掉，純 headless。

跑完應該看到：

```
[E2E] 新增 record id=15234, holder=E2E測試持證者-1747...
[E2E] accountant 補 invoice_no=EE47123456 → issuance_status=綠 ✓
[E2E] issuer 確認 record 15234 = 綠燈 → 可進入核發/寄送階段 ✓
[E2E] 全流程通過 ✓ record id=15234
```

---

## 跑純 API 版本（30 秒驗收）

```bash
cd app/tests/e2e
npx playwright test happy-path-api.spec.ts
```

連 Chromium 都不開，純 fetch，適合 CI 或剛部署完做煙霧測試。

---

## 為什麼會計那段不是用滑鼠點 cell？

`UniverSheet` 試算表是 canvas-based，Playwright 沒辦法穩定地點到「第 N 列 invoice_no 欄」。
所以會計補發票走 `page.request.patch()` —— 這個 request 帶著瀏覽器登入後的 cookie，
等同於前端 fetch 真的執行。驗的是同一條 code path：
**權限白名單 + `invoice_no` 副作用自動翻綠燈**。

---

## 跑完留下什麼

每次測試用 timestamp 隨機 holder name（例：`E2E測試持證者-1747xxxx`），
不會跟正式資料碰撞，但會在 DB 留一筆。如果累積太多想清，去 DB：

```sql
DELETE FROM audit_log
 WHERE record_id IN (
   SELECT id FROM records WHERE holder_name LIKE 'E2E測試持證者-%' OR holder_name LIKE 'API測試持證者-%'
 );
DELETE FROM records WHERE holder_name LIKE 'E2E測試持證者-%' OR holder_name LIKE 'API測試持證者-%';
```
