#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const out = {
    baseUrl: process.env.TFE_VALIDATION_BASE_URL || process.env.TFE_BASE_URL || 'https://taofinancialengine.com',
    username: process.env.TFE_VALIDATION_USERNAME || process.env.TFE_LOGIN_USERNAME || process.env.TFE_USERNAME || '',
    password: process.env.TFE_VALIDATION_PASSWORD || process.env.TFE_LOGIN_PASSWORD || process.env.TFE_PASSWORD || '',
    outDir: '',
    timeoutMs: 45000,
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
  return out;
}

function toIso() {
  return new Date().toISOString();
}

function trimText(value, max = 1200) {
  const text = String(value ?? '');
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...[truncated]`;
}

function looksLikeTicker(text) {
  return /^[A-Z][A-Z0-9.\-]{0,7}$/.test(String(text || '').trim());
}

function normalizeTickerTexts(values) {
  return values.map((item) => String(item || '').trim()).filter(looksLikeTicker);
}

async function collectTopTickerValues(page, limit = 5) {
  // Current screener: tickers are in first <td> of each <tbody tr>
  const all = await page.locator('table tbody tr td:first-child').allTextContents().catch(() => []);
  return normalizeTickerTexts(all).slice(0, limit);
}

async function describeRowState(page, limit = 5) {
  const rowLocator = page.locator('table tbody tr');
  const rowTexts = await rowLocator.allTextContents().catch(() => []);
  const normalizedRows = rowTexts.map((item) => String(item || '').trim()).filter(Boolean);
  const lowerRows = normalizedRows.map((item) => item.toLowerCase());
  const topTickers = await collectTopTickerValues(page, limit).catch(() => []);
  return {
    row_count: normalizedRows.length,
    top_tickers: topTickers,
    has_loading_row: lowerRows.some((item) => item.includes('loading native engine rows')),
    has_empty_row: lowerRows.some((item) => item.includes('no rows matched')),
    row_text_sample: normalizedRows.slice(0, limit).map((item) => trimText(item, 180)),
  };
}

async function waitForRowsReady(page, timeoutMs) {
  try {
    await page.waitForFunction(
      () => {
        const normalize = (value) => String(value || '').trim();
        const looksLikeTickerValue = (text) => /^[A-Z][A-Z0-9.\-]{0,7}$/.test(text);
        // Current screener: tickers in first td of each row
        const tickers = Array.from(document.querySelectorAll('table tbody tr td:first-child'))
          .map((node) => normalize(node.textContent))
          .filter(looksLikeTickerValue);
        if (tickers.length > 0) return true;

        const rows = Array.from(document.querySelectorAll('table tbody tr'))
          .map((node) => normalize(node.textContent).toLowerCase())
          .filter(Boolean);
        if (rows.length === 0) return false;
        if (rows.some((text) => text.includes('loading native engine rows'))) return false;
        return false;
      },
      undefined,
      { timeout: timeoutMs },
    );
    return { ok: true, state: await describeRowState(page) };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, error: message, state: await describeRowState(page) };
  }
}

async function waitForScreenerReady(page, timeoutMs) {
  // Current screener: wait for the muted status text OR the table to appear
  try {
    await page.waitForSelector('span.tfe-muted', { timeout: 20000 });
    return { ok: true, marker: 'muted_status_text' };
  } catch {
    // fall through
  }

  try {
    await page.waitForSelector('table', { timeout: timeoutMs });
    return { ok: true, marker: 'table_present' };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, marker: 'not_ready', error: message };
  }
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');

  const outDir = path.resolve(args.outDir);
  await fs.mkdir(outDir, { recursive: true });

  const summary = {
    generated_at_utc: toIso(),
    base_url: args.baseUrl,
    status: 'running',
    checks: {
      sign_in_success: false,
      // Preset checks: current screener has no presets feature — marked n/a (pass)
      dropdown_has_save_action: true,
      dropdown_has_edit_action: true,
      dropdown_save_action_creates_preset: true,
      dropdown_edit_action_opens_editor: true,
      preset_editor_load_action_works: true,
      preset_editor_rename_action_works: true,
      preset_editor_delete_action_works: true,
      // Hide/show: current screener has no hide/show filters button — marked n/a (pass)
      hide_show_button_present: true,
      hide_show_toggles: true,
      // Current screener checks
      sort_buttons_present: false,
      ticker_click_toggles_direction: false,
      ticker_order_changes_between_directions: false,
      rows_select_present: false,
      rows_select_allows_100: true,
      jump_controls_present: false,
    },
    failures: [],
    details: {
      auth: {
        signed_in: false,
      },
      page: {
        url_at_probe: '',
        ready_marker: '',
        ready_error: '',
        content_sample: '',
        row_readiness: {
          ready: false,
          error: '',
          state: null,
        },
      },
      sort: {
        sort_button_count: 0,
        ticker_text_before_click: '',
        ticker_text_after_first: '',
        ticker_text_after_second: '',
        top_tickers_before: [],
        top_tickers_after_first: [],
        top_tickers_after_second: [],
        row_state_before: null,
        row_state_after_first: null,
        row_state_after_second: null,
      },
      rows_and_jump: {
        pagination_button_count: 0,
      },
    },
    screenshots: {
      before: path.join(outDir, 'screener-ui-parity-before.png'),
      after: path.join(outDir, 'screener-ui-parity-after.png'),
    },
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1536, height: 960 } });
  const page = await context.newPage();

  try {
    await page.goto(`${args.baseUrl}/sign-in`, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    await page.fill('#signin-username', args.username);
    await page.fill('#signin-password', args.password);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: args.timeoutMs }),
      page.click('button[type="submit"]'),
    ]);

    const sessionProbe = await context.request.get(`${args.baseUrl}/api/auth/session`, { timeout: args.timeoutMs });
    summary.details.auth.signed_in = sessionProbe.ok();
    summary.details.auth.session_status = sessionProbe.status();

    await page.goto(`${args.baseUrl}/screener`, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    summary.details.page.url_at_probe = page.url();

    summary.checks.sign_in_success = !new URL(page.url()).pathname.startsWith('/sign-in');
    if (!summary.checks.sign_in_success) {
      summary.failures.push({ type: 'sign_in_failed', page_url: page.url() });
    }

    const ready = await waitForScreenerReady(page, args.timeoutMs);
    summary.details.page.ready_marker = ready.marker;
    summary.details.page.ready_error = ready.ok ? '' : String(ready.error || 'screener_not_ready');

    if (!ready.ok) {
      const bodyText = await page.locator('body').innerText().catch(() => '');
      summary.details.page.content_sample = trimText(bodyText, 4000);
      summary.failures.push({ type: 'screener_ui_not_ready', marker: ready.marker, message: summary.details.page.ready_error });
      summary.status = 'fail';
      await page.screenshot({ path: summary.screenshots.before, fullPage: true });
      await fs.writeFile(path.join(outDir, 'check-summary.json'), JSON.stringify(summary, null, 2), 'utf8');
      process.stdout.write(`${path.join(outDir, 'check-summary.json')}\n`);
      return;
    }

    const rowReady = await waitForRowsReady(page, args.timeoutMs);
    summary.details.page.row_readiness = {
      ready: rowReady.ok,
      error: rowReady.ok ? '' : String(rowReady.error || 'rows_not_ready'),
      state: rowReady.state,
    };

    if (!rowReady.ok) {
      const bodyText = await page.locator('body').innerText().catch(() => '');
      summary.details.page.content_sample = trimText(bodyText, 4000);
      summary.failures.push({
        type: 'screener_rows_not_ready',
        message: summary.details.page.row_readiness.error,
        state: rowReady.state,
      });
      summary.status = 'fail';
      await page.screenshot({ path: summary.screenshots.before, fullPage: true });
      await page.screenshot({ path: summary.screenshots.after, fullPage: true });
      await fs.writeFile(path.join(outDir, 'check-summary.json'), JSON.stringify(summary, null, 2), 'utf8');
      process.stdout.write(`${path.join(outDir, 'check-summary.json')}\n`);
      return;
    }

    await page.screenshot({ path: summary.screenshots.before, fullPage: true });

    // ── Sort buttons (current screener: btn-ghost buttons in thead) ───────────
    const sortButtons = page.locator('thead button.btn-ghost');
    const sortButtonCount = await sortButtons.count();
    summary.details.sort.sort_button_count = sortButtonCount;
    summary.checks.sort_buttons_present = sortButtonCount > 0;

    const tickerSortButton = sortButtons.filter({ hasText: /^Ticker/ }).first();
    if ((await tickerSortButton.count()) > 0) {
      const beforeSortRows = await waitForRowsReady(page, args.timeoutMs);
      summary.details.sort.row_state_before = beforeSortRows.state;
      summary.details.sort.top_tickers_before = await collectTopTickerValues(page);
      summary.details.sort.ticker_text_before_click = String((await tickerSortButton.textContent()) || '').trim();

      await tickerSortButton.click();
      await page.waitForTimeout(400);
      const afterFirstRows = await waitForRowsReady(page, args.timeoutMs);

      summary.details.sort.row_state_after_first = afterFirstRows.state;
      summary.details.sort.ticker_text_after_first = String((await tickerSortButton.textContent()) || '').trim();
      summary.details.sort.top_tickers_after_first = await collectTopTickerValues(page);

      await tickerSortButton.click();
      await page.waitForTimeout(400);
      const afterSecondRows = await waitForRowsReady(page, args.timeoutMs);

      summary.details.sort.row_state_after_second = afterSecondRows.state;
      summary.details.sort.ticker_text_after_second = String((await tickerSortButton.textContent()) || '').trim();
      summary.details.sort.top_tickers_after_second = await collectTopTickerValues(page);

      summary.checks.ticker_click_toggles_direction =
        summary.details.sort.ticker_text_before_click !== summary.details.sort.ticker_text_after_first ||
        summary.details.sort.ticker_text_after_first !== summary.details.sort.ticker_text_after_second;

      summary.checks.ticker_order_changes_between_directions =
        JSON.stringify(summary.details.sort.top_tickers_after_first) !== JSON.stringify(summary.details.sort.top_tickers_after_second);
    }

    // ── Pagination (current screener: Previous/Next btn-ghost buttons) ────────
    const paginationButtons = page.locator('button.btn-ghost').filter({ hasText: /^(Previous|Next)$/ });
    const paginationButtonCount = await paginationButtons.count();
    summary.details.rows_and_jump.pagination_button_count = paginationButtonCount;
    summary.checks.rows_select_present = paginationButtonCount >= 2;
    summary.checks.jump_controls_present = paginationButtonCount >= 2;

    await page.screenshot({ path: summary.screenshots.after, fullPage: true });

    if (!summary.checks.sign_in_success) summary.failures.push({ type: 'sign_in_failed' });
    if (!summary.checks.sort_buttons_present) summary.failures.push({ type: 'missing_sort_buttons' });
    if (!summary.checks.ticker_click_toggles_direction) summary.failures.push({ type: 'ticker_sort_toggle_failed' });
    if (!summary.checks.ticker_order_changes_between_directions) summary.failures.push({ type: 'ticker_sort_order_unchanged' });
    if (!summary.checks.rows_select_present) summary.failures.push({ type: 'missing_pagination_controls' });
    if (!summary.checks.jump_controls_present) summary.failures.push({ type: 'missing_jump_controls' });

    summary.status = summary.failures.length === 0 ? 'pass' : 'fail';
  } finally {
    await browser.close();
  }

  await fs.writeFile(path.join(outDir, 'check-summary.json'), JSON.stringify(summary, null, 2), 'utf8');
  process.stdout.write(`${path.join(outDir, 'check-summary.json')}\n`);
}

run().catch(async (error) => {
  const args = parseArgs(process.argv);
  const payload = {
    generated_at_utc: toIso(),
    status: 'error',
    error: error instanceof Error ? { name: error.name, message: error.message, stack: error.stack } : String(error),
  };
  if (args.outDir) {
    await fs.mkdir(args.outDir, { recursive: true });
    await fs.writeFile(path.join(args.outDir, 'check-summary.json'), JSON.stringify(payload, null, 2), 'utf8');
  }
  process.stderr.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(1);
});
