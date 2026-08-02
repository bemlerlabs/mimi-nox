import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 15000,
  retries: 0,
  use: {
    headless: true,
    baseURL: 'http://127.0.0.1:9199',
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
  },
  webServer: {
    command: 'python3 -m http.server 9199 --directory dist',
    port: 9199,
    cwd: '../../',
  },
});
