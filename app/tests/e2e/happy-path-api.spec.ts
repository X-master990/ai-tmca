/**
 * TMCA Happy-Path 純 API 版 —— 不用瀏覽器
 *
 * 對應 happy-path.spec.ts，但完全走 HTTP，跑得比 UI 版快 10x。
 * 用途：
 *   - 後端剛重新部署後，先跑這支 30 秒驗收一下三角色 cookie + 權限 + 副作用
 *   - CI 環境沒裝瀏覽器時的 smoke test
 *
 * 跑法：
 *   cd app/tests/e2e
 *   npx playwright test happy-path-api.spec.ts
 */
import { expect, test, request as pwRequest } from '@playwright/test';

const PASSWORD = 'Tmca0001!';
const STAMP = Date.now();
const HOLDER_NAME = `API測試持證者-${STAMP}`;
const INVOICE_NO = `AP${String(STAMP).slice(-8)}`;

async function loginAs(username: string) {
  // 每個角色開一個獨立 storageState（cookie jar），避免互相污染
  const ctx = await pwRequest.newContext({ baseURL: 'http://localhost' });
  const res = await ctx.post('/api/auth/login', {
    data: { username, password: PASSWORD },
  });
  expect(res.ok(), `login ${username} failed: ${res.status()}`).toBeTruthy();
  return ctx;
}

test('happy path (API only) — 承辦建檔 → 會計補發票 → 燈號轉綠', async () => {
  // 1. officer_a 建檔
  const officer = await loginAs('officer_a');
  const created = await officer
    .post('/api/records', {
      data: {
        category_code: 'SINGLE_EVENT',
        holder_name: HOLDER_NAME,
        tax_id: '12345678',
        invoice_title: `${HOLDER_NAME} 股份有限公司`,
        amount: 15000,
        apply_date: '2026-05-20',
        period_start: '2026-06-01',
        period_end: '2026-06-01',
        action_type: '新件',
        use_address: '台北市中正區重慶南路一段 122 號',
        mail_recipient: HOLDER_NAME,
        applicant_name: 'API代辦人',
      },
    })
    .then((r) => {
      expect(r.status(), 'POST /api/records').toBe(201);
      return r.json();
    });
  expect(created.issuance_status).toBe('紅');
  const recordId = created.id;
  console.log(`[API] 建立 record id=${recordId}`);

  // 2. accountant 補發票號 → 副作用該翻綠
  const acct = await loginAs('accountant');
  const afterPatch = await acct
    .patch(`/api/records/${recordId}`, {
      data: {
        invoice_no: INVOICE_NO,
        invoice_date: '2026-05-21',
        invoice_type: '二聯式',
      },
    })
    .then((r) => {
      expect(r.ok(), 'PATCH by accountant').toBeTruthy();
      return r.json();
    });
  expect(afterPatch.issuance_status).toBe('綠');
  console.log(`[API] accountant 補 invoice_no=${INVOICE_NO} → 綠燈 ✓`);

  // 3. accountant 越界寫非發票欄位 → 該被擋
  const forbidden = await acct.patch(`/api/records/${recordId}`, {
    data: { holder_name: '不該被改' },
  });
  expect(forbidden.status(), 'accountant 不能改 holder_name').toBe(403);
  console.log(`[API] accountant 越界寫 holder_name → 403 ✓`);

  // 4. issuer 看綠燈
  const issuer = await loginAs('issuer');
  const issuerRows = await issuer
    .get('/api/records?category_code=SINGLE_EVENT')
    .then((r) => r.json());
  const found = issuerRows.find((r: { id: number }) => r.id === recordId);
  expect(found).toBeTruthy();
  expect(found.issuance_status).toBe('綠');
  expect(found.invoice_no).toBe(INVOICE_NO);
  console.log(`[API] issuer 看到綠燈 record ${recordId} ✓ 全流程通過`);
});
