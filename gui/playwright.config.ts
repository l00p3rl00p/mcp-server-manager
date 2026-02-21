import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  projects: [
    // Use the locally installed Chrome (best match for Codex/Atlas workflows on macOS),
    // avoiding Playwright-bundled Chromium which can be blocked by sandbox permissions.
    { name: 'chrome', use: { browserName: 'chromium', channel: 'chrome' } },
  ],
  use: {
    // In this repo, the GUI is served by the bridge on :5001.
    // We do not start a webServer here because sandboxed environments may forbid binding ports.
    baseURL: 'http://127.0.0.1:5001',
    trace: 'retain-on-failure',
  },
});
