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

async function collectTopTickerValues(page, limit = 5) {
  const all = await page.locator('button.tfe-row-button').allTextContents();
  const symbols = all.map((item) => String(item || '').trim()).filter(looksLikeTicker);
  return symbols.slice(0, limit);
}

async function waitForRowsReady(page, timeoutMs) {
  await page
    .waitForFunction(
      () => {
        const rows = Array.from(document.querySelectorAll('table.tfe-table tbody tr'));
        if (rows.length === 0) return false;
        const first = String(rows[0]?.textContent || '').toLowerCase();
        if (first.includes('loading screener rows')) return false;
        return true;
      },
      undefined,
      { timeout: timeoutMs },
    )
    .catch(() => {});
}

async function waitForScreenerReady(page, timeoutMs) {
  try {
    await page.waitForSelector('section[aria-label="Screener data tabs"]', { timeout: 15000 });
    return { ok: true, marker: 'tabs_section' };
  } catch {
    // fall through
  }

  try {
    await page.waitForSelector('#screenerPageSize', { timeout: 15000 });
    return { ok: true, marker: 'rows_select' };
  } catch {
    // fall through
  }

  try {
    await page.waitForSelector('select.tfe-select', { timeout: timeoutMs });
    return { ok: true, marker: 'generic_select' };
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
      dropdown_has_save_action: false,
      dropdown_has_edit_action: false,
      dropdown_save_action_creates_preset: false,
      dropdown_edit_action_opens_editor: false,
      preset_editor_load_action_works: false,
      preset_editor_rename_action_works: false,
      preset_editor_delete_action_works: false,
      hide_show_button_present: false,
      hide_show_toggles: false,
      sort_buttons_present: false,
      ticker_click_toggles_direction: false,
      ticker_order_changes_between_directions: false,
      rows_select_present: false,
      rows_select_allows_100: false,
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
      },
      preset: {
        initial_options: [],
        options_after_save: [],
        options_after_rename: [],
        options_after_delete: [],
        renamed_name: '',
        load_notice: '',
      },
      hide_show: {
        initial_text: '',
        after_first_click_text: '',
        sector_count_after_hide: null,
        sector_count_after_show: null,
      },
      sort: {
        sort_button_count: 0,
        ticker_text_before_click: '',
        ticker_text_after_first: '',
        ticker_text_after_second: '',
        top_tickers_before: [],
        top_tickers_after_first: [],
        top_tickers_after_second: [],
      },
      rows_and_jump: {
        rows_options: [],
        numeric_pagination_button_count: 0,
        numeric_pagination_link_count: 0,
        jump_input_count: 0,
        jump_select_count: 0,
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

  const uniqueSuffix = Date.now();
  const presetName = `UI Parity Preset ${uniqueSuffix}`;

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
    summary.details.auth.session_sample = trimText(await sessionProbe.text());

    await page.goto(`${args.baseUrl}/screener`, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    summary.details.page.url_at_probe = page.url();

    summary.checks.sign_in_success = !new URL(page.url()).pathname.startsWith('/sign-in');
    if (!summary.checks.sign_in_success) {
      summary.failures.push({ type: 'sign_in_failed', page_url: page.url() });
    }

    const ready = await waitForScreenerReady(page, args.timeoutMs);
    summary.details.page.ready_marker = ready.marker;
    summary.details.page.ready_error = ready.ok ? '' : String(ready.error || 'screener_not_ready');

    await page.screenshot({ path: summary.screenshots.before, fullPage: true });

    if (!ready.ok) {
      const bodyText = await page.locator('body').innerText().catch(() => '');
      summary.details.page.content_sample = trimText(bodyText, 4000);
      summary.failures.push({ type: 'screener_ui_not_ready', marker: ready.marker, message: summary.details.page.ready_error });
      summary.status = 'fail';
      await fs.writeFile(path.join(outDir, 'check-summary.json'), JSON.stringify(summary, null, 2), 'utf8');
      process.stdout.write(`${path.join(outDir, 'check-summary.json')}\n`);
      return;
    }

    await waitForRowsReady(page, args.timeoutMs);

    const presetsSelect = page
      .locator('select.tfe-select')
      .filter({ has: page.locator('option', { hasText: 'My Presets' }) })
      .first();

    const presetOptions = await presetsSelect.locator('option').allTextContents();
    const normalizedPresetOptions = presetOptions.map((item) => String(item || '').trim()).filter(Boolean);
    summary.details.preset.initial_options = normalizedPresetOptions;

    summary.checks.dropdown_has_save_action = normalizedPresetOptions.includes('Save Screen...');
    summary.checks.dropdown_has_edit_action = normalizedPresetOptions.some((item) => item.includes('Edit Screens'));

    await page.evaluate((name) => {
      window.prompt = () => String(name);
    }, presetName);

    await presetsSelect.selectOption({ label: 'Save Screen...' });
    await page.waitForTimeout(600);

    const optionsAfterSave = (await presetsSelect.locator('option').allTextContents()).map((item) => String(item || '').trim());
    summary.details.preset.options_after_save = optionsAfterSave;
    summary.checks.dropdown_save_action_creates_preset = optionsAfterSave.includes(presetName);

    await presetsSelect.selectOption({ label: 'Edit Screens...' });
    await page.waitForTimeout(600);
    const editorRow = page.locator('tr', { hasText: presetName }).first();
    summary.checks.dropdown_edit_action_opens_editor = (await editorRow.count()) > 0;

    const renamedPresetName = `${presetName} Renamed`;
    summary.details.preset.renamed_name = renamedPresetName;

    if (summary.checks.dropdown_edit_action_opens_editor) {
      await page.evaluate((name) => {
        window.prompt = () => String(name);
        window.confirm = () => true;
      }, renamedPresetName);

      const renameButton = editorRow.getByRole('button', { name: 'Rename' }).first();
      if ((await renameButton.count()) > 0) {
        await renameButton.click();
        await page.waitForTimeout(500);
      }

      const optionsAfterRename = (await presetsSelect.locator('option').allTextContents()).map((item) => String(item || '').trim());
      summary.details.preset.options_after_rename = optionsAfterRename;

      const renamedEditorRow = page.locator('tr', { hasText: renamedPresetName }).first();
      summary.checks.preset_editor_rename_action_works =
        (await renamedEditorRow.count()) > 0 && optionsAfterRename.includes(renamedPresetName);

      const activePresetName = summary.checks.preset_editor_rename_action_works ? renamedPresetName : presetName;
      const activeRow = summary.checks.preset_editor_rename_action_works ? renamedEditorRow : editorRow;

      const loadButton = activeRow.getByRole('button', { name: 'Load' }).first();
      if ((await loadButton.count()) > 0) {
        await loadButton.click();
        await page.waitForTimeout(400);
      }
      const loadNoticeText = String((await page.locator('p.tfe-muted').filter({ hasText: /^Loaded preset:/ }).first().textContent().catch(() => '')) || '').trim();
      summary.details.preset.load_notice = loadNoticeText;
      summary.checks.preset_editor_load_action_works = loadNoticeText.includes(activePresetName);

      const deleteButton = activeRow.getByRole('button', { name: 'Delete' }).first();
      if ((await deleteButton.count()) > 0) {
        await deleteButton.click();
        await page.waitForTimeout(500);
      }
      const optionsAfterDelete = (await presetsSelect.locator('option').allTextContents()).map((item) => String(item || '').trim());
      summary.details.preset.options_after_delete = optionsAfterDelete;
      summary.checks.preset_editor_delete_action_works = !optionsAfterDelete.includes(activePresetName);
    }

    const hideShowButton = page.getByRole('button', { name: /Hide Filters|Show Filters/ }).first();
    summary.checks.hide_show_button_present = (await hideShowButton.count()) > 0;

    if (summary.checks.hide_show_button_present) {
      const initialText = String((await hideShowButton.textContent()) || '').trim();
      summary.details.hide_show.initial_text = initialText;

      await hideShowButton.click();
      await page.waitForTimeout(300);

      const afterFirstClickText = String((await hideShowButton.textContent()) || '').trim();
      const sectorCountAfterHide = await page.locator('#screener-filter-sector').count();

      await hideShowButton.click();
      await page.waitForTimeout(300);

      const sectorCountAfterShow = await page.locator('#screener-filter-sector').count();

      summary.details.hide_show.after_first_click_text = afterFirstClickText;
      summary.details.hide_show.sector_count_after_hide = sectorCountAfterHide;
      summary.details.hide_show.sector_count_after_show = sectorCountAfterShow;

      summary.checks.hide_show_toggles =
        initialText !== afterFirstClickText &&
        sectorCountAfterHide === 0 &&
        sectorCountAfterShow >= 1;
    }

    const sortButtons = page.locator('button.tfe-sort-btn');
    const sortButtonCount = await sortButtons.count();
    summary.details.sort.sort_button_count = sortButtonCount;
    summary.checks.sort_buttons_present = sortButtonCount > 0;

    const tickerSortButton = sortButtons.filter({ hasText: /^Ticker/ }).first();
    if ((await tickerSortButton.count()) > 0) {
      await waitForRowsReady(page, args.timeoutMs);
      summary.details.sort.top_tickers_before = await collectTopTickerValues(page);
      summary.details.sort.ticker_text_before_click = String((await tickerSortButton.textContent()) || '').trim();

      await tickerSortButton.click();
      await waitForRowsReady(page, args.timeoutMs);
      await page.waitForTimeout(350);

      summary.details.sort.ticker_text_after_first = String((await tickerSortButton.textContent()) || '').trim();
      summary.details.sort.top_tickers_after_first = await collectTopTickerValues(page);

      await tickerSortButton.click();
      await waitForRowsReady(page, args.timeoutMs);
      await page.waitForTimeout(350);

      summary.details.sort.ticker_text_after_second = String((await tickerSortButton.textContent()) || '').trim();
      summary.details.sort.top_tickers_after_second = await collectTopTickerValues(page);

      summary.checks.ticker_click_toggles_direction =
        summary.details.sort.ticker_text_before_click !== summary.details.sort.ticker_text_after_first &&
        summary.details.sort.ticker_text_after_first !== summary.details.sort.ticker_text_after_second;

      summary.checks.ticker_order_changes_between_directions =
        JSON.stringify(summary.details.sort.top_tickers_after_first) !== JSON.stringify(summary.details.sort.top_tickers_after_second);
    }

    const rowsSelect = page.locator('#screenerPageSize').first();
    summary.checks.rows_select_present = (await rowsSelect.count()) > 0;

    if (summary.checks.rows_select_present) {
      const rowOptions = (await rowsSelect.locator('option').allTextContents()).map((item) => String(item || '').trim());
      summary.details.rows_and_jump.rows_options = rowOptions;
      summary.checks.rows_select_allows_100 = rowOptions.includes('100');
      await rowsSelect.selectOption('100');
      await page.waitForTimeout(300);
    }

    const numericPaginationButtons = await page
      .locator('[aria-label="Pagination"] button')
      .evaluateAll((nodes) => nodes.filter((node) => /^\d+$/.test(String(node.textContent || '').trim())).length);
    const numericPaginationLinks = await page
      .locator('[aria-label="Pagination"] a')
      .evaluateAll((nodes) => nodes.filter((node) => /^\d+$/.test(String(node.textContent || '').trim())).length);
    const jumpInputCount = await page
      .locator('input[aria-label*="jump" i], input[placeholder*="jump" i], input[aria-label*="page" i], input[placeholder*="page" i]')
      .count();
    const jumpSelectCount = await page
      .locator('select[aria-label*="jump" i], select[aria-label*="page" i], select[id*="jump" i], select[id*="page" i]')
      .count();

    summary.details.rows_and_jump.numeric_pagination_button_count = numericPaginationButtons;
    summary.details.rows_and_jump.numeric_pagination_link_count = numericPaginationLinks;
    summary.details.rows_and_jump.jump_input_count = jumpInputCount;
    summary.details.rows_and_jump.jump_select_count = jumpSelectCount;

    summary.checks.jump_controls_present = numericPaginationButtons + numericPaginationLinks + jumpInputCount + jumpSelectCount > 0;

    await page.screenshot({ path: summary.screenshots.after, fullPage: true });

    if (!summary.checks.dropdown_has_save_action) summary.failures.push({ type: 'missing_dropdown_save_action' });
    if (!summary.checks.dropdown_has_edit_action) summary.failures.push({ type: 'missing_dropdown_edit_action' });
    if (!summary.checks.dropdown_save_action_creates_preset) summary.failures.push({ type: 'dropdown_save_action_failed' });
    if (!summary.checks.dropdown_edit_action_opens_editor) summary.failures.push({ type: 'dropdown_edit_action_failed' });
    if (!summary.checks.preset_editor_load_action_works) summary.failures.push({ type: 'preset_editor_load_action_failed' });
    if (!summary.checks.preset_editor_rename_action_works) summary.failures.push({ type: 'preset_editor_rename_action_failed' });
    if (!summary.checks.preset_editor_delete_action_works) summary.failures.push({ type: 'preset_editor_delete_action_failed' });
    if (!summary.checks.hide_show_button_present) summary.failures.push({ type: 'missing_hide_show_button' });
    if (!summary.checks.hide_show_toggles) summary.failures.push({ type: 'hide_show_toggle_failed' });
    if (!summary.checks.sort_buttons_present) summary.failures.push({ type: 'missing_sort_buttons' });
    if (!summary.checks.ticker_click_toggles_direction) summary.failures.push({ type: 'ticker_sort_toggle_failed' });
    if (!summary.checks.ticker_order_changes_between_directions) summary.failures.push({ type: 'ticker_sort_order_unchanged' });
    if (!summary.checks.rows_select_present) summary.failures.push({ type: 'missing_rows_select' });
    if (!summary.checks.rows_select_allows_100) summary.failures.push({ type: 'rows_select_missing_100_option' });
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
