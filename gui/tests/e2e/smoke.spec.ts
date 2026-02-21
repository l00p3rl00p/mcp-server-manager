import { test, expect } from '@playwright/test';

test('Nexus Commander smoke: inventory drawers + audit panel', async ({ page }) => {
  // Guardrail: no browser dialogs/popups. UX must use drawers/side-panels only.
  page.on('dialog', async (d) => {
    await d.dismiss().catch(() => {});
    throw new Error(`Unexpected browser dialog: ${d.type()} ${d.message()}`);
  });

  // Stub the API so the UI can render deterministically without requiring a live bridge process.
  // Backend contracts are covered by Python call-chain tests; this is UI wiring smoke.
  const api = 'http://127.0.0.1:5001';
  const servers = [
    {
      id: 'notebooklm',
      name: 'notebooklm',
      status: 'stopped',
      type: 'generic',
      metrics: { cpu: 0, ram: 0, pid: null },
      raw: { id: 'notebooklm', name: 'notebooklm', run: { start_cmd: 'python3 mcp_server.py' } },
    },
  ];

  await page.route(`${api}/status`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        pulse: 'green',
        posture: 'Optimal',
        metrics: { cpu: 0, ram_total: 1, ram_used: 0, disk_total: 1, disk_used: 0 },
        history: [],
        servers,
        core_components: { activator: 'online', librarian: 'online', librarian_bin: 'online', observer: 'online', surgeon: 'online' },
        active_project: { id: 'nexus-default', path: '/tmp' },
        version: '3.3.1',
      }),
    });
  });

  const empty = (body: any) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  await page.route(`${api}/logs`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/librarian/links`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/nexus/projects`, (route) => route.fulfill(empty([{ id: 'nexus-default', name: 'Nexus Commander (Default)', path: '/tmp' }])));
  await page.route(`${api}/librarian/roots`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/librarian/watcher`, (route) => route.fulfill(empty({ status: 'offline' })));
  await page.route(`${api}/validate`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/project/history`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/nexus/catalog`, (route) => route.fulfill(empty([])));
  await page.route(`${api}/forge/last`, (route) => route.fulfill(empty({})));
  await page.route(`${api}/system/python_info`, (route) => route.fulfill(empty({ success: true, packages: {} })));

  await page.route(new RegExp(`${api.replace(/\./g, '\\.')}/server/logs/.*`), (route) =>
    route.fulfill(empty({ log_path: '/tmp/x.log', mtime: 0, lines: ['--- SERVER: notebooklm ---', '--- ACTION: start ---'] })),
  );
  await page.route(new RegExp(`${api.replace(/\./g, '\\.')}/export/report\\.json.*`), (route) =>
    route.fulfill(empty({ generated_at: 'now', server_id: 'notebooklm', target: servers[0], servers, recent_activity: [] })),
  );

  await page.goto('/');

  // Dashboard inventory should render.
  await expect(page.getByText('Active Inventory')).toBeVisible();

  // Open a server lifecycle log drawer (Terminal icon).
  const terminalBtn = page.locator('button[title="View lifecycle log"]').first();
  await terminalBtn.click();
  await expect(page.getByText('Lifecycle Log')).toBeVisible();

  // Open audit report drawer (FileText icon).
  const reportBtn = page.locator('button[title="Open audit report"]').first();
  await reportBtn.click();
  await expect(page.getByText('Audit Report')).toBeVisible();

  // Switch to list view (icon toggle) and ensure table row exists.
  await page.locator('button[title="List View"]').click();
  await expect(page.locator('b', { hasText: 'notebooklm' })).toBeVisible();

  // Open Command Hub and open in-app Audit (Log Browser panel).
  await page.getByText('Command Log').click();
  await page.getByRole('button', { name: 'Audit' }).click();
  await expect(page.getByText('Log Browser')).toBeVisible();
  // The selector is an <option>, which is not necessarily "visible" in all browsers.
  await expect(page.locator('select').first()).toHaveValue('audit');
});
