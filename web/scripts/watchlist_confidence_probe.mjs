#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const args = {
    baseUrl: process.env.TFE_BASE_URL || 'https://taofinancialengine.com',
    username: process.env.TFE_USERNAME || '',
    password: process.env.TFE_PASSWORD || '',
    outDir: '',
    timeoutMs: 45000,
    maxAgeMinutes: 1440,
    symbols: ['AAPL', 'MSFT', 'SPY'],
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);

    if (key === 'symbols' && next && !next.startsWith('--')) {
      args.symbols = next
        .split(',')
        .map((value) => String(value).trim().toUpperCase())
        .filter((value) => value.length > 0);
      i += 1;
      continue;
    }

    if (next && !next.startsWith('--')) {
      args[key] = next;
      i += 1;
      continue;
    }

    args[key] = 'true';
  }

  args.timeoutMs = Number(args.timeoutMs || 45000);
  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs < 1000) args.timeoutMs = 45000;

  args.maxAgeMinutes = Number(args.maxAgeMinutes || 1440);
  if (!Number.isFinite(args.maxAgeMinutes) || args.maxAgeMinutes < 1) args.maxAgeMinutes = 1440;

  return args;
}

function toIso() {
  return new Date().toISOString();
}

function trimText(text, max = 1200) {
  const raw = String(text ?? '');
  if (raw.length <= max) return raw;
  return `${raw.slice(0, max)}...[truncated]`;
}

function parseJsonSafely(text) {
  try {
    return JSON.parse(String(text ?? ''));
  } catch {
    return null;
  }
}

function validIso(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function includesAllSymbols(actualList, expectedList) {
  const actual = new Set((actualList || []).map((item) => String(item ?? '').trim().toUpperCase()));
  return expectedList.every((symbol) => actual.has(symbol));
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');
  if (!Array.isArray(args.symbols) || args.symbols.length === 0) throw new Error('Missing probe symbols');

  const outDir = path.resolve(String(args.outDir));
  await fs.mkdir(outDir, { recursive: true });

  const summary = {
    generated_at_utc: toIso(),
    base_url: String(args.baseUrl),
    status: 'running',
    checks: {
      sign_in_success: false,
      watchlist_save_success: false,
      watchlist_get_success: false,
      watchlist_page_http_200: false,
      watchlist_response_data_source_postgres: false,
      watchlist_response_has_run_id: false,
      watchlist_response_has_generated_at_utc: false,
      watchlist_freshness_within_budget: false,
      watchlist_response_has_snapshot_source: false,
      watchlist_response_has_quote_source: false,
      watchlist_contains_saved_symbols: false,
      watchlist_metrics_nonempty: false,
      watchlist_missing_symbols_empty: false,
    },
    failures: [],
    details: {
      symbols_under_test: args.symbols,
      sign_in: {},
      watchlist_save: {},
      watchlist_get: {},
      watchlist_page: {},
      freshness: {
        max_age_minutes: args.maxAgeMinutes,
      },
      cleanup: {},
    },
    screenshots: {
      watchlist_page: path.join(outDir, 'watchlist-page.png'),
    },
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.setDefaultTimeout(args.timeoutMs);

  try {
    const signInResp = await context.request.post(`${args.baseUrl}/api/auth/sign-in`, {
      data: {
        username: args.username,
        password: args.password,
      },
      timeout: args.timeoutMs,
    });
    const signInBody = await signInResp.text();
    summary.details.sign_in = {
      status: signInResp.status(),
      body_sample: trimText(signInBody),
    };

    if (signInResp.ok()) {
      summary.checks.sign_in_success = true;
    } else {
      summary.failures.push('sign_in_failed');
    }

    const saveResp = await context.request.post(`${args.baseUrl}/api/watchlist`, {
      data: { symbols: args.symbols },
      timeout: args.timeoutMs,
    });
    const saveBodyText = await saveResp.text();
    const saveBody = parseJsonSafely(saveBodyText);
    summary.details.watchlist_save = {
      status: saveResp.status(),
      body_sample: trimText(saveBodyText),
      parsed: saveBody,
    };

    if (saveResp.ok()) {
      summary.checks.watchlist_save_success = true;
    } else {
      summary.failures.push('watchlist_save_failed');
    }

    const getResp = await context.request.get(`${args.baseUrl}/api/watchlist`, { timeout: args.timeoutMs });
    const getBodyText = await getResp.text();
    const getBody = parseJsonSafely(getBodyText);
    summary.details.watchlist_get = {
      status: getResp.status(),
      body_sample: trimText(getBodyText, 8000),
      parsed: getBody,
    };

    if (getResp.ok()) {
      summary.checks.watchlist_get_success = true;
    } else {
      summary.failures.push('watchlist_get_failed');
    }

    const pageResp = await page.goto(`${args.baseUrl}/watchlist`, {
      waitUntil: 'domcontentloaded',
      timeout: args.timeoutMs,
    });
    summary.details.watchlist_page = {
      status: pageResp ? pageResp.status() : null,
      url: page.url(),
    };

    if (pageResp && pageResp.status() === 200) {
      summary.checks.watchlist_page_http_200 = true;
    } else {
      summary.failures.push('watchlist_page_not_200');
    }

    await page.waitForTimeout(1500);
    await page.screenshot({ path: summary.screenshots.watchlist_page, fullPage: true });

    const dataSource = String(getBody?.data_source ?? '').trim().toLowerCase();
    const runId = String(getBody?.run_id ?? '').trim();
    const generatedAtText = validIso(getBody?.generated_at_utc);
    const snapshotSource = String(getBody?.snapshotSource ?? '').trim();
    const quoteSource = String(getBody?.quoteSource ?? '').trim();
    const symbols = Array.isArray(getBody?.symbols) ? getBody.symbols : [];
    const metrics = Array.isArray(getBody?.metrics) ? getBody.metrics : [];
    const missingSymbols = Array.isArray(getBody?.missingSymbols) ? getBody.missingSymbols : [];

    summary.details.freshness.generated_at_utc = generatedAtText;
    if (generatedAtText) {
      const ageMs = Date.now() - Date.parse(generatedAtText);
      const ageMinutes = ageMs / 60000;
      summary.details.freshness.age_minutes = Number(ageMinutes.toFixed(2));
      summary.checks.watchlist_response_has_generated_at_utc = true;
      if (ageMinutes <= args.maxAgeMinutes) {
        summary.checks.watchlist_freshness_within_budget = true;
      } else {
        summary.failures.push('watchlist_generated_at_too_old');
      }
    } else {
      summary.failures.push('watchlist_missing_generated_at_utc');
    }

    if (dataSource === 'postgres') {
      summary.checks.watchlist_response_data_source_postgres = true;
    } else {
      summary.failures.push('watchlist_data_source_not_postgres');
    }

    if (runId) {
      summary.checks.watchlist_response_has_run_id = true;
    } else {
      summary.failures.push('watchlist_missing_run_id');
    }

    if (snapshotSource) {
      summary.checks.watchlist_response_has_snapshot_source = true;
    } else {
      summary.failures.push('watchlist_missing_snapshot_source');
    }

    if (quoteSource) {
      summary.checks.watchlist_response_has_quote_source = true;
    } else {
      summary.failures.push('watchlist_missing_quote_source');
    }

    if (includesAllSymbols(symbols, args.symbols)) {
      summary.checks.watchlist_contains_saved_symbols = true;
    } else {
      summary.failures.push('watchlist_symbols_mismatch');
    }

    if (metrics.length > 0) {
      summary.checks.watchlist_metrics_nonempty = true;
    } else {
      summary.failures.push('watchlist_metrics_empty');
    }

    if (missingSymbols.length === 0) {
      summary.checks.watchlist_missing_symbols_empty = true;
    } else {
      summary.failures.push('watchlist_missing_symbols_present');
    }
  } finally {
    try {
      const cleanupResp = await context.request.post(`${args.baseUrl}/api/watchlist`, {
        data: { symbols: [] },
        timeout: args.timeoutMs,
      });
      summary.details.cleanup = {
        status: cleanupResp.status(),
        ok: cleanupResp.ok(),
      };
      if (!cleanupResp.ok()) {
        summary.failures.push('watchlist_cleanup_failed');
      }
    } catch (error) {
      summary.details.cleanup = {
        status: null,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
      summary.failures.push('watchlist_cleanup_failed');
    }

    await browser.close();
  }

  summary.status = summary.failures.length === 0 ? 'pass' : 'fail';

  const summaryPath = path.join(outDir, 'summary.json');
  await fs.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');

  process.stdout.write(`${JSON.stringify({ status: summary.status, summary_path: summaryPath, out_dir: outDir })}\n`);
  process.exitCode = summary.status === 'pass' ? 0 : 1;
}

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
