/**
 * TMCA Happy-Path E2E —— 承辦 → 會計 → 核發 完整跑一筆
 *
 * 流程驗證（紅燈 → 綠燈）：
 *   1. officer_a 登入 → 在前端 NewRecordModal 新增一筆「單場次表演」案件
 *      （holder_name + 必要欄位）→ 預設 issuance_status = "紅"
 *   2. 登出 → accountant 登入 → 從瀏覽器發 PATCH 補 invoice_no
 *      （Univer 試算表是 canvas 不易由 Playwright 點擊，因此走 page.request
 *      使用同一 cookie session，等同於前端 fetch 的真實行為）
 *   3. issuance_status 應自動翻成「綠」= 核發完成
 *   4. 登出 → issuer 登入 → 再讀一次該筆，確認看得到「綠」
 *
 * 跑法（系統需先 `docker compose up -d`）：
 *   cd app/tests/e2e
 *   npx playwright test happy-path.spec.ts --headed
 *
 * 想看資料但不要瀏覽器：把 playwright.config.ts 的 headless 改 true。
 */
import { expect, test, type Page, type APIRequestContext } from '@playwright/test';

const PASSWORD = 'Tmca0001!';

// 用 timestamp 確保每次測試 holder 唯一，方便事後人工驗屍
const STAMP = Date.now();
const HOLDER_NAME = `E2E測試持證者-${STAMP}`;
const INVOICE_NO = `EE${String(STAMP).slice(-8)}`;

async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.locator('input:not([type="password"])').first().fill(username);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: /^登入/ }).click();
  await page.waitForURL('**/');
  // 等 /api/auth/me 回來、Home 已渲染
  await expect(page.getByText('進入總表')).toBeVisible({ timeout: 10_000 });
}

/**
 * NewRecordModal 的 <label> 沒掛 htmlFor，所以走「label 同層的 input/textarea」這條路。
 * 每個欄位是包在一個 div 裡：<div><label>標題</label><input/></div>
 */
function modalField(page: Page, labelText: string | RegExp) {
  const label =
    typeof labelText === 'string'
      ? page.locator(`label:has-text("${labelText}")`)
      : page.locator('label').filter({ hasText: labelText });
  // label 的相鄰 input 或 textarea（同一個 div 容器內）
  return label.locator('xpath=following-sibling::*[self::input or self::textarea][1]').first();
}

async function logout(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: '登出' }).click();
  await page.waitForURL('**/login');
}

/** 透過已登入瀏覽器的 cookie 直接打 API，模擬「前端 fetch」的真實行為。 */
async function apiGetRecordsByHolder(
  request: APIRequestContext,
  categoryCode: string,
  holderName: string,
) {
  const res = await request.get(
    `/api/records?category_code=${encodeURIComponent(categoryCode)}`,
  );
  expect(res.ok(), `GET /api/records failed: ${res.status()}`).toBeTruthy();
  const rows = (await res.json()) as Array<{
    id: number;
    holder_name: string | null;
    issuance_status: string;
    invoice_no: string | null;
  }>;
  return rows.filter((r) => r.holder_name === holderName);
}

test.describe.configure({ mode: 'serial' });

test('happy path — 承辦新增 → 會計補發票 → 核發轉綠', async ({ page }) => {
  test.setTimeout(3 * 60 * 1000);

  // ───────────── 1. officer_a 在前端 NewRecordModal 新增案件 ─────────────
  await login(page, 'officer_a');

  await page.getByRole('button', { name: /進入總表/ }).click();
  await page.waitForURL('**/records');

  await expect(page.getByRole('button', { name: /新增案件/ })).toBeVisible();
  await page.getByRole('button', { name: /新增案件/ }).click();

  // Modal 開啟
  await expect(page.getByRole('heading', { name: /新增案件/ })).toBeVisible();

  // 類型：officer_a 唯一能寫的是 SINGLE_EVENT（單場次表演）— 應該已是 default
  const categorySelect = page.locator('select').first();
  await categorySelect.selectOption({ label: /單場次表演/ });

  // 持證者 / 主辦單位（required）
  await page.getByPlaceholder(/玉亭演唱會/).fill(HOLDER_NAME);

  // 一些好填的欄位（讓資料看起來真實）
  await modalField(page, '統一編號').fill('12345678');
  await modalField(page, '發票抬頭').fill(`${HOLDER_NAME} 股份有限公司`);
  await modalField(page, '合約金額').fill('15000');
  await modalField(page, '申辦日期').fill('2026-05-20');
  await modalField(page, '授權起始').fill('2026-06-01');
  await modalField(page, '授權結束').fill('2026-06-01');
  await modalField(page, '辦理項目').fill('新件');
  await modalField(page, /營業地址/).fill('台北市中正區重慶南路一段 122 號');
  await modalField(page, '收件人').fill(HOLDER_NAME);
  await modalField(page, /申請人/).fill('E2E代辦人');

  // 攔截 POST 拿 record id，比 grep 試算表還可靠
  const createResponsePromise = page.waitForResponse(
    (r) => r.url().includes('/api/records') && r.request().method() === 'POST',
  );

  await page.getByRole('button', { name: /送出/ }).click();

  const createResp = await createResponsePromise;
  expect(createResp.status(), '建立應 201').toBe(201);
  const created = await createResp.json();
  expect(created.holder_name).toBe(HOLDER_NAME);
  expect(created.category_code).toBe('SINGLE_EVENT');
  expect(created.issuance_status).toBe('紅'); // 還沒補發票，預設紅燈
  const recordId: number = created.id;
  console.log(`[E2E] 新增 record id=${recordId}, holder=${HOLDER_NAME}`);

  // Modal 應該關閉、回到總表
  await expect(page.getByRole('heading', { name: /新增案件/ })).toBeHidden();

  // ───────────── 2. 登出 → accountant 補發票號碼 ─────────────
  await logout(page);
  await login(page, 'accountant');

  // accountant 的 PATCH 走 page.request — 同 origin + 同 cookie，相當於前端 fetch
  const patchResp = await page.request.patch(`/api/records/${recordId}`, {
    data: {
      invoice_no: INVOICE_NO,
      invoice_date: '2026-05-21',
      invoice_type: '二聯式',
    },
  });
  expect(patchResp.ok(), `accountant PATCH failed: ${patchResp.status()}`).toBeTruthy();
  const afterPatch = await patchResp.json();
  expect(afterPatch.invoice_no).toBe(INVOICE_NO);
  expect(afterPatch.issuance_status).toBe('綠'); // 副作用：補上發票號 → 自動綠燈
  console.log(`[E2E] accountant 補 invoice_no=${INVOICE_NO} → issuance_status=綠 ✓`);

  // 進總表用 UI 再 sanity check — accountant 應看到剛被翻綠的那筆
  await page.getByRole('button', { name: /進入總表/ }).click();
  await page.waitForURL('**/records');
  await page.locator('select').first().selectOption('2026'); // 預設應已選但保險
  // accountant 的權限矩陣是只能編發票欄位 → 其他應 readonly（這層在 unit/integration 已測過）

  // ───────────── 3. 登出 → issuer 確認看得到綠燈 ─────────────
  await logout(page);
  await login(page, 'issuer');

  const issuerView = await apiGetRecordsByHolder(
    page.request,
    'SINGLE_EVENT',
    HOLDER_NAME,
  );
  expect(issuerView.length, 'issuer 應看到剛剛建立的測試 record').toBe(1);
  expect(issuerView[0].id).toBe(recordId);
  expect(issuerView[0].invoice_no).toBe(INVOICE_NO);
  expect(issuerView[0].issuance_status).toBe('綠');
  console.log(`[E2E] issuer 確認 record ${recordId} = 綠燈 → 可進入核發/寄送階段 ✓`);

  // ───────────── 4. （選擇性）admin 看 audit_log ─────────────
  //   — audit_log endpoint 目前還沒有，所以這裡只用 admin 再 GET 確認最新狀態
  await logout(page);
  await login(page, 'admin');
  const adminView = await apiGetRecordsByHolder(
    page.request,
    'SINGLE_EVENT',
    HOLDER_NAME,
  );
  expect(adminView[0].issuance_status).toBe('綠');
  console.log(`[E2E] 全流程通過 ✓ record id=${recordId}`);
});
