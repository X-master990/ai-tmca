import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-TW',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    headless: false,
    launchOptions: {
      slowMo: 500,
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
