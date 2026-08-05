#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const out = {
    baseUrl: 'https://taofinancialengine.com',
    username: '',
    password: '',
    outDir: '',
    timeoutMs: 45000,
    baselineAttempts: 3,
  };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    if (!token.startsWith('--')) continue;
    if (next && !next.startsWith('--')) {
      out[token.slice(2)] = next;
      i += 1;
    } else {
      out[token.slice(2)] = 'true';
    }
  }
  out.timeoutMs = Number(out.timeoutMs || 45000);
  out.baselineAttempts = Number(out.baselineAttempts || 3);
  if (!Number.isFinite(out.baselineAttempts) || out.baselineAttempts < 1) {
    out.baselineAttempts = 3;
  }
  return out;
}

const tabChecks = [
  { label: 'Overview', expectedApiTab: 'overview' },
  { label: 'Valuation', expectedApiTab: 'valuation' },
  { label: 'Financial', expectedApiTab: 'financial' },
  { label: 'Ownership', expectedApiTab: 'ownership' },
  { label: 'Performance', expectedApiTab: 'performance' },
  { label: 'Technical', expectedApiTab: 'technical' },
  { label: 'ETF', expectedApiTab: 'etf' },
  { label: 'ETF Perf', expectedApiTab: 'etf' },
  { label: 'Basic', expectedApiTab: 'overview' },
  { label: 'TA', expectedApiTab: 'technical' },
  { label: 'News', expectedApiTab: 'performance' },
  { label: 'Maps', expectedApiTab: 'overview' },
];

const orderByChecks = [
  { sortKey: 'ticker', sortDir: 'asc' },
  { sortKey: 'ticker', sortDir: 'desc' },
  { sortKey: 'price', sortDir: 'desc' },
  { sortKey: 'change', sortDir: 'desc' },
  { sortKey: 'volume', sortDir: 'desc' },
];

function trimBody(value, max = 800) {
  const text = String(value ?? '');
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...[truncated]`;
}

async function fetchScreenerJsonWithRetry(context, url, timeoutMs, attempts) {
  const errors = [];
  let lastStatus = null;

  for (let i = 1; i <= attempts; i += 1) {
    const startedAt = Date.now();
    try {
      const response = await context.request.get(url, { timeout: timeoutMs });
      const elapsedMs = Date.now() - startedAt;
      lastStatus = response.status();
      const bodyText = await response.text();

      let payload = null;
      try {
        payload = JSON.parse(bodyText);
      } catch {
        payload = null;
      }

      const total = Number(payload?.total);
      const totalValid = Number.isFinite(total) && total >= 0;

      if (response.ok() && payload && totalValid) {
        return {
          ok: true,
          status: response.status(),
          elapsedMs,
          total,
          payload,
          error: '',
          attempts: i,
        };
      }

      errors.push({
        attempt: i,
        status: response.status(),
        elapsedMs,
        reason: 'invalid_response_contract',
        body_sample: trimBody(bodyText),
      });
    } catch (error) {
      const elapsedMs = Date.now() - startedAt;
      const message = error instanceof Error ? error.message : String(error);
      errors.push({
        attempt: i,
        status: null,
        elapsedMs,
        reason: 'request_error',
        error: message,
      });
    }
  }

  return {
    ok: false,
    status: lastStatus,
    elapsedMs: null,
    total: null,
    payload: null,
    error: JSON.stringify(errors),
    attempts,
  };
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');

  await fs.mkdir(args.outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1536, height: 960 } });
  const page = await context.newPage();

  const summary = {
    generated_at_utc: new Date().toISOString(),
    base_url: args.baseUrl,
    status: 'running',
    checks: [],
    failures: [],
    screenshots: {},
  };

  try {
    await page.goto(`${args.baseUrl}/sign-in`, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    await page.fill('#signin-username', args.username);
    await page.fill('#signin-password', args.password);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: args.timeoutMs }),
      page.click('button[type="submit"]'),
    ]);

    await page.goto(`${args.baseUrl}/screener`, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    await page.waitForSelector('section[aria-label="Screener data tabs"]', { timeout: args.timeoutMs });

    summary.screenshots.overview_before = path.join(args.outDir, 'screener-overview-before.png');
    await page.screenshot({ path: summary.screenshots.overview_before, fullPage: true });

    const waitForScreenerResponse = (predicate) =>
      page.waitForResponse(
        async (response) => {
          const url = response.url();
          if (!url.includes('/api/screener?')) return false;
          if (response.request().method() !== 'GET') return false;
          try {
            const parsed = new URL(url);
            return predicate(parsed);
          } catch {
            return false;
          }
        },
        { timeout: args.timeoutMs },
      );

    const dataTabsGroup = page.getByLabel('Screener data tabs');

    for (const check of tabChecks) {
      await dataTabsGroup.getByRole('button', { name: check.label, exact: true }).click();

      await page.waitForTimeout(200);
      await page.selectOption('#screener-filter-sector', '').catch(() => {});
      await page.fill('input[placeholder="Min Price"]', '').catch(() => {});

      const baselineUrl = `${args.baseUrl}/api/screener?tab=${check.expectedApiTab}&page=1&pageSize=50&sortKey=ticker&sortDir=asc&filterGroup=descriptive`;
      const baselineResult = await fetchScreenerJsonWithRetry(context, baselineUrl, args.timeoutMs, args.baselineAttempts);
      const baselineTotal = baselineResult.ok ? Number(baselineResult.total ?? 0) : null;

      const orderByResults = [];
      for (const orderByCheck of orderByChecks) {
        const orderByUrl =
          `${args.baseUrl}/api/screener?tab=${check.expectedApiTab}` +
          `&page=1&pageSize=50&sortKey=${encodeURIComponent(orderByCheck.sortKey)}` +
          `&sortDir=${encodeURIComponent(orderByCheck.sortDir)}&filterGroup=descriptive`;
        const orderByResult = await fetchScreenerJsonWithRetry(context, orderByUrl, args.timeoutMs, args.baselineAttempts);
        orderByResults.push({
          sortKey: orderByCheck.sortKey,
          sortDir: orderByCheck.sortDir,
          ok: orderByResult.ok,
          status: orderByResult.status,
          elapsed_ms: orderByResult.elapsedMs,
          total: orderByResult.total,
          attempts: orderByResult.attempts,
          error: orderByResult.error,
          url: orderByUrl,
        });
      }
      const orderByPass = orderByResults.every((entry) => entry.ok);

      const sectorResponsePromise = waitForScreenerResponse((url) => {
        const tab = url.searchParams.get('tab');
        const sector = url.searchParams.get('sector');
        return tab === check.expectedApiTab && sector === 'technology';
      });
      const sectorStartedAt = Date.now();
      await page.selectOption('#screener-filter-sector', 'technology');
      const sectorResponse = await sectorResponsePromise;
      const sectorElapsedMs = Date.now() - sectorStartedAt;
      const sectorUrl = new URL(sectorResponse.url());
      const sectorJson = await sectorResponse.json().catch(() => ({}));
      const sectorTotal = Number(sectorJson?.total ?? 0);

      const minPriceResponsePromise = waitForScreenerResponse((url) => {
        const tab = url.searchParams.get('tab');
        const sector = url.searchParams.get('sector');
        const minPrice = url.searchParams.get('minPrice');
        return tab === check.expectedApiTab && sector === 'technology' && minPrice === '100';
      });
      const minPriceStartedAt = Date.now();
      await page.fill('input[placeholder="Min Price"]', '100');
      const minPriceResponse = await minPriceResponsePromise;
      const minPriceElapsedMs = Date.now() - minPriceStartedAt;
      const minPriceUrl = new URL(minPriceResponse.url());
      const minPriceJson = await minPriceResponse.json().catch(() => ({}));
      const minPriceTotal = Number(minPriceJson?.total ?? 0);

      const tableRows = await page.locator('table.tfe-table tbody tr').count();
      const taCards = await page.locator('.tfe-ta-card').count();
      const visibleRows = Math.max(tableRows, taCards);

      const baselineOk = baselineResult.ok && baselineTotal !== null;
      const tabPass =
        baselineOk &&
        orderByPass &&
        sectorResponse.ok() &&
        minPriceResponse.ok() &&
        sectorUrl.searchParams.get('tab') === check.expectedApiTab &&
        minPriceUrl.searchParams.get('tab') === check.expectedApiTab &&
        sectorTotal <= Number(baselineTotal) &&
        minPriceTotal <= sectorTotal;

      const item = {
        tab_label: check.label,
        expected_api_tab: check.expectedApiTab,
        baseline_total: baselineTotal,
        baseline_ok: baselineOk,
        baseline_status: baselineResult.status,
        baseline_elapsed_ms: baselineResult.elapsedMs,
        baseline_attempts: baselineResult.attempts,
        baseline_error: baselineResult.error,
        baseline_url: baselineUrl,
        order_by_pass: orderByPass,
        order_by_results: orderByResults,
        sector_total: sectorTotal,
        min_price_total: minPriceTotal,
        visible_table_rows: visibleRows,
        sector_request_url: sectorResponse.url(),
        sector_latency_ms: sectorElapsedMs,
        min_price_request_url: minPriceResponse.url(),
        min_price_latency_ms: minPriceElapsedMs,
        ok: tabPass,
      };
      summary.checks.push(item);
      if (!tabPass) summary.failures.push({ type: 'tab_filter_behavior', ...item });

      const clearMinPricePromise = waitForScreenerResponse((url) => {
        const tab = url.searchParams.get('tab');
        const minPrice = url.searchParams.get('minPrice');
        return tab === check.expectedApiTab && (minPrice === null || minPrice === '');
      });
      await page.fill('input[placeholder="Min Price"]', '');
      await clearMinPricePromise;

      const clearSectorPromise = waitForScreenerResponse((url) => {
        const tab = url.searchParams.get('tab');
        const sector = url.searchParams.get('sector');
        return tab === check.expectedApiTab && (sector === null || sector === '');
      });
      await page.selectOption('#screener-filter-sector', '');
      await clearSectorPromise;

      if (check.label === 'Maps') {
        summary.screenshots.maps_after = path.join(args.outDir, 'screener-maps-after.png');
        await page.screenshot({ path: summary.screenshots.maps_after, fullPage: true });
      }
    }

    summary.status = summary.failures.length === 0 ? 'pass' : 'fail';
  } finally {
    await browser.close();
  }

  const summaryPath = path.join(args.outDir, 'summary.json');
  await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2), 'utf8');
  process.stdout.write(`${summaryPath}\n`);
}

run().catch(async (error) => {
  const args = parseArgs(process.argv);
  const payload = {
    generated_at_utc: new Date().toISOString(),
    status: 'error',
    error: error instanceof Error ? { name: error.name, message: error.message, stack: error.stack } : String(error),
  };
  if (args.outDir) {
    await fs.mkdir(args.outDir, { recursive: true });
    await fs.writeFile(path.join(args.outDir, 'summary.json'), JSON.stringify(payload, null, 2), 'utf8');
  }
  process.stderr.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(1);
});
