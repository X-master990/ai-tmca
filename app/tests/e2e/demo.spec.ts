/**
 * TMCA Demo —— 給螢幕錄影用
 *
 * 跑法：
 *   cd app/tests/e2e
 *   npx playwright test demo.spec.ts --headed
 *
 * 流程：
 *   1. 登入頁巡禮（officer_a）
 *   2. 總表 → 選類型 → 點 cell（officer_a 是單場次負責人）
 *   3. 登出 → 會計（accountant）→ 看欄位被鎖
 *   4. 登出 → 管理員（admin）→ 搜尋 / 代辦人 / 續約 / 報表
 */
import { expect, test, type Page } from '@playwright/test';

const PASSWORD = 'Tmca0001!';

// Narration helper —— 把標題印到 stdout，方便對照錄影時間軸
function narrate(title: string) {
  console.log(`\n▶ ${title}\n`);
}

async function login(page: Page, username: string) {
  narrate(`登入：${username}`);
  await page.goto('/login');
  await page.waitForTimeout(800);
  // Login.tsx 的 input 沒有 htmlFor，只能用 type/位置定位
  await page.locator('input:not([type="password"])').first().fill(username);
  await page.waitForTimeout(300);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: /^登入/ }).click();
  await page.waitForURL('**/');
  await page.waitForTimeout(1200);
}

async function logout(page: Page) {
  narrate('登出');
  // 先回 Home（登出按鈕只在那裡）
  await page.goto('/');
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: '登出' }).click();
  await page.waitForURL('**/login');
  await page.waitForTimeout(1000);
}

test.describe.configure({ mode: 'serial' });

test('TMCA 完整 demo', async ({ page }) => {
  test.setTimeout(15 * 60 * 1000); // 15 分鐘

  // ────────────────── 1. 登入頁 ──────────────────
  narrate('登入頁面');
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'TMCA' })).toBeVisible();
  await page.waitForTimeout(2500);

  // ────────────────── 2. officer_a → 總表 ──────────────────
  await login(page, 'officer_a');
  await expect(page.getByText('進入總表')).toBeVisible();
  await page.waitForTimeout(1500);

  narrate('進入總表');
  await page.getByRole('button', { name: /進入總表/ }).click();
  await page.waitForURL('**/records');
  await page.waitForTimeout(2500);

  narrate('切換類型 tab：單場次表演（officer_a 是負責人）');
  // tab 元件可能用 button 標籤或文字；先試文字
  const singleEventTab = page.getByText('單場次表演').first();
  if (await singleEventTab.isVisible().catch(() => false)) {
    await singleEventTab.click();
    await page.waitForTimeout(2500);
  }

  narrate('切到別的類型（officer_a 應該無權編輯）');
  const ktvTab = page.getByText('自助KTV').first();
  if (await ktvTab.isVisible().catch(() => false)) {
    await ktvTab.click();
    await page.waitForTimeout(2500);
  }

  // ────────────────── 3. 切到搜尋頁 ──────────────────
  narrate('側欄/Home → 搜尋');
  await page.goto('/search');
  await page.waitForTimeout(1500);

  narrate('全域搜尋：「玉亭」');
  const searchInput = page.getByPlaceholder(/證書編號/);
  await searchInput.fill('玉亭');
  await page.waitForTimeout(400);
  await page.getByRole('button', { name: '搜尋', exact: true }).click();
  await page.waitForTimeout(2500);

  narrate('搜尋：發票號碼');
  await searchInput.fill('');
  await searchInput.type('114', { delay: 80 });
  await page.getByRole('button', { name: '搜尋', exact: true }).click();
  await page.waitForTimeout(2500);

  narrate('切到「代辦人查詢」');
  await page.getByRole('button', { name: '代辦人查詢' }).click();
  await page.waitForTimeout(1200);
  const agentInput = page.getByPlaceholder(/代辦人姓名/);
  await agentInput.fill('陳');
  await page.getByRole('button', { name: '搜尋', exact: true }).click();
  await page.waitForTimeout(3500);

  // ────────────────── 4. 登出 → accountant ──────────────────
  await logout(page);
  await login(page, 'accountant');

  narrate('會計角色 — 進總表');
  await page.getByRole('button', { name: /進入總表/ }).click();
  await page.waitForURL('**/records');
  await page.waitForTimeout(3000);

  narrate('會計只能改發票相關欄位，其他唯讀（觀察灰底 cells）');
  await page.waitForTimeout(2500);

  // ────────────────── 5. 登出 → admin ──────────────────
  await logout(page);
  await login(page, 'admin');

  narrate('管理員 → 續約管理');
  await page.getByRole('button', { name: /續約管理/ }).click();
  await page.waitForURL('**/renewals');
  await page.waitForTimeout(3500);

  narrate('續約管理：捲動看清單');
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(1500);
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(1500);

  narrate('回首頁 → 報表');
  await page.goto('/reports');
  await page.waitForTimeout(3500);

  narrate('Demo 結束');
  await page.goto('/');
  await page.waitForTimeout(2500);
});
