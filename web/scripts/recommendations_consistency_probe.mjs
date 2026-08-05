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
    epsilon: 1e-6,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);

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

  args.epsilon = Number(args.epsilon || 1e-6);
  if (!Number.isFinite(args.epsilon) || args.epsilon <= 0) args.epsilon = 1e-6;

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

function isFiniteNumber(value) {
  return Number.isFinite(Number(value));
}

function approxEqual(a, b, epsilon) {
  return Math.abs(Number(a) - Number(b)) <= epsilon;
}

function validIso(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function decisionToClassification(decision) {
  if (decision === 'Accumulate') return 'BUY';
  if (decision === 'Avoid') return 'SELL';
  return 'HOLD';
}

const ALLOWED_REASON_CODES = new Set([
  'ROW_NOT_FOUND',
  'PSCF_POLICY_DECISION',
  'PSCF_FALLBACK_INSUFFICIENT_BARS',
  'PSCF_FALLBACK_STRUCTURAL_INCOMPLETE',
  'PSCF_FALLBACK_POLICY_MISSING',
  'PSCF_FALLBACK_CELL_KEY_UNAVAILABLE',
  'PSCF_FALLBACK_CELL_UNMAPPED',
  'PSCF_FALLBACK_ANOMALOUS',
]);

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');

  const outDir = path.resolve(String(args.outDir));
  await fs.mkdir(outDir, { recursive: true });

  const summary = {
    generated_at_utc: toIso(),
    base_url: String(args.baseUrl),
    status: 'running',
    checks: {
      sign_in_success: false,
      recommendations_api_success: false,
      recommendations_page_http_200: false,
      response_has_buckets: false,
      response_has_total_accumulate: false,
      total_accumulate_matches_bucket_sum: false,
      titans_market_cap_threshold: false,
      heavyweights_market_cap_threshold: false,
      mid_tier_market_cap_threshold: false,
      hunters_market_cap_threshold: false,
      all_rows_decision_accumulate: false,
      all_rows_have_required_numeric_fields: false,
      all_rows_ticker_nonempty: false,
      all_rows_sector_nonempty: false,
      no_ticker_duplicates_across_buckets: false,
      is_new_listing_boolean: false,
    },
    failures: [],
    details: {
      sign_in: {},
      recommendations_api: {},
      recommendations_page: {},
      computed: {
        bucket_counts: {
          titans: 0,
          heavyweights: 0,
          mid_tier: 0,
          hunters: 0,
          total: 0,
        },
        bad_decision_rows: 0,
        bad_numeric_rows: 0,
        bad_ticker_rows: 0,
        bad_sector_rows: 0,
        duplicate_tickers: [],
        bad_new_listing_rows: 0,
        bad_threshold_rows: {
          titans: 0,
          heavyweights: 0,
          mid_tier: 0,
          hunters: 0,
        },
      },
    },
    screenshots: {
      recommendations_page: path.join(outDir, 'recommendations-page.png'),
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
    const signInBodyText = await signInResp.text();
    summary.details.sign_in = {
      status: signInResp.status(),
      body_sample: trimText(signInBodyText),
    };

    if (signInResp.ok()) {
      summary.checks.sign_in_success = true;
    } else {
      summary.failures.push('sign_in_failed');
    }

    const recResp = await context.request.get(`${args.baseUrl}/api/recommendations/list`, { timeout: args.timeoutMs });
    const recBodyText = await recResp.text();
    const recBody = parseJsonSafely(recBodyText);
    summary.details.recommendations_api = {
      status: recResp.status(),
      body_sample: trimText(recBodyText, 12000),
      parsed: recBody,
    };

    if (recResp.ok()) {
      summary.checks.recommendations_api_success = true;
    } else {
      summary.failures.push('recommendations_api_failed');
    }

    const pageResp = await page.goto(`${args.baseUrl}/recommendations`, {
      waitUntil: 'domcontentloaded',
      timeout: args.timeoutMs,
    });
    summary.details.recommendations_page = {
      status: pageResp ? pageResp.status() : null,
      url: page.url(),
    };

    if (pageResp && pageResp.status() === 200) {
      summary.checks.recommendations_page_http_200 = true;
    } else {
      summary.failures.push('recommendations_page_not_200');
    }

    await page.waitForTimeout(1500);
    await page.screenshot({ path: summary.screenshots.recommendations_page, fullPage: true });

    const payload = recBody && typeof recBody === 'object' ? recBody : {};

    // ── Check 4: response has buckets structure ────────────────────────────────
    const buckets = payload.buckets && typeof payload.buckets === 'object' ? payload.buckets : null;
    const titans = Array.isArray(buckets?.titans) ? buckets.titans : [];
    const heavyweights = Array.isArray(buckets?.heavyweights) ? buckets.heavyweights : [];
    const midTier = Array.isArray(buckets?.midTier) ? buckets.midTier : [];
    const hunters = Array.isArray(buckets?.hunters) ? buckets.hunters : [];

    if (buckets !== null) {
      summary.checks.response_has_buckets = true;
    } else {
      summary.failures.push('recommendations_missing_buckets');
    }

    // ── Check 5: totalAccumulate is a non-negative integer ────────────────────
    const totalAccumulate = Number(payload.totalAccumulate ?? NaN);
    if (Number.isFinite(totalAccumulate) && totalAccumulate >= 0 && Number.isInteger(totalAccumulate)) {
      summary.checks.response_has_total_accumulate = true;
    } else {
      summary.failures.push('recommendations_missing_total_accumulate');
    }

    // ── Check 6: totalAccumulate === sum of bucket lengths ────────────────────
    const bucketSum = titans.length + heavyweights.length + midTier.length + hunters.length;
    summary.details.computed.bucket_counts = {
      titans: titans.length,
      heavyweights: heavyweights.length,
      mid_tier: midTier.length,
      hunters: hunters.length,
      total: bucketSum,
    };
    if (Number.isFinite(totalAccumulate) && totalAccumulate === bucketSum) {
      summary.checks.total_accumulate_matches_bucket_sum = true;
    } else {
      summary.failures.push('recommendations_total_accumulate_bucket_sum_mismatch');
    }

    // ── Checks 7–10: market cap thresholds per bucket ─────────────────────────
    // Only check rows where marketCap > 0 (0 means data unavailable, falls through to hunters)
    const TITAN_MIN = 200_000_000_000;
    const HW_MIN = 50_000_000_000;
    const MT_MIN = 10_000_000_000;

    let badTitans = 0;
    for (const row of titans) {
      const mc = Number(row?.marketCap ?? 0);
      if (mc > 0 && mc < TITAN_MIN) badTitans += 1;
    }
    let badHeavyweights = 0;
    for (const row of heavyweights) {
      const mc = Number(row?.marketCap ?? 0);
      if (mc > 0 && (mc < HW_MIN || mc >= TITAN_MIN)) badHeavyweights += 1;
    }
    let badMidTier = 0;
    for (const row of midTier) {
      const mc = Number(row?.marketCap ?? 0);
      if (mc > 0 && (mc < MT_MIN || mc >= HW_MIN)) badMidTier += 1;
    }
    let badHunters = 0;
    for (const row of hunters) {
      const mc = Number(row?.marketCap ?? 0);
      if (mc > 0 && mc >= MT_MIN) badHunters += 1;
    }

    summary.details.computed.bad_threshold_rows = { titans: badTitans, heavyweights: badHeavyweights, mid_tier: badMidTier, hunters: badHunters };

    if (badTitans === 0) {
      summary.checks.titans_market_cap_threshold = true;
    } else {
      summary.failures.push('recommendations_titans_market_cap_invalid');
    }
    if (badHeavyweights === 0) {
      summary.checks.heavyweights_market_cap_threshold = true;
    } else {
      summary.failures.push('recommendations_heavyweights_market_cap_invalid');
    }
    if (badMidTier === 0) {
      summary.checks.mid_tier_market_cap_threshold = true;
    } else {
      summary.failures.push('recommendations_mid_tier_market_cap_invalid');
    }
    if (badHunters === 0) {
      summary.checks.hunters_market_cap_threshold = true;
    } else {
      summary.failures.push('recommendations_hunters_market_cap_invalid');
    }

    // ── Checks 11–16: per-row integrity across all buckets ────────────────────
    const allRows = [...titans, ...heavyweights, ...midTier, ...hunters];
    let badDecision = 0;
    let badNumeric = 0;
    let badTicker = 0;
    let badSector = 0;
    let badNewListing = 0;
    const seenTickers = new Map();
    const duplicateTickers = [];

    for (const row of allRows) {
      if (String(row?.decision ?? '') !== 'Accumulate') badDecision += 1;

      const mc = Number(row?.marketCap ?? NaN);
      const cr = Number(row?.currentRatio ?? NaN);
      const fcf = Number(row?.freeCashFlow ?? NaN);
      const gm = Number(row?.grossMargin ?? NaN);
      if (!Number.isFinite(mc) || !Number.isFinite(cr) || !Number.isFinite(fcf) || !Number.isFinite(gm)) {
        badNumeric += 1;
      }

      const ticker = String(row?.ticker ?? '').trim();
      if (!ticker) {
        badTicker += 1;
      } else {
        if (seenTickers.has(ticker)) {
          duplicateTickers.push(ticker);
        } else {
          seenTickers.set(ticker, true);
        }
      }

      const sector = String(row?.sector ?? '').trim();
      if (!sector) badSector += 1;

      if ('isNewListing' in Object(row) && typeof row.isNewListing !== 'boolean') {
        badNewListing += 1;
      }
    }

    summary.details.computed.bad_decision_rows = badDecision;
    summary.details.computed.bad_numeric_rows = badNumeric;
    summary.details.computed.bad_ticker_rows = badTicker;
    summary.details.computed.bad_sector_rows = badSector;
    summary.details.computed.duplicate_tickers = duplicateTickers;
    summary.details.computed.bad_new_listing_rows = badNewListing;

    if (badDecision === 0) {
      summary.checks.all_rows_decision_accumulate = true;
    } else {
      summary.failures.push('recommendations_non_accumulate_rows_in_buckets');
    }

    if (badNumeric === 0) {
      summary.checks.all_rows_have_required_numeric_fields = true;
    } else {
      summary.failures.push('recommendations_rows_missing_numeric_fields');
    }

    if (badTicker === 0) {
      summary.checks.all_rows_ticker_nonempty = true;
    } else {
      summary.failures.push('recommendations_rows_empty_ticker');
    }

    if (badSector === 0) {
      summary.checks.all_rows_sector_nonempty = true;
    } else {
      summary.failures.push('recommendations_rows_empty_sector');
    }

    if (duplicateTickers.length === 0) {
      summary.checks.no_ticker_duplicates_across_buckets = true;
    } else {
      summary.failures.push('recommendations_duplicate_tickers_across_buckets');
    }

    if (badNewListing === 0) {
      summary.checks.is_new_listing_boolean = true;
    } else {
      summary.failures.push('recommendations_is_new_listing_not_boolean');
    }

    summary.details.recommendations_api.meta = {
      totalAccumulate: payload.totalAccumulate ?? null,
      bucket_counts: summary.details.computed.bucket_counts,
    };
  } finally {
    await context.close();
    await browser.close();
  }

  if (summary.failures.length === 0) {
    summary.status = 'pass';
  } else {
    summary.status = 'fail';
  }

  await fs.writeFile(path.join(outDir, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify({ status: summary.status, outDir, failures: summary.failures.length })}\n`);

  if (summary.status !== 'pass') {
    process.exitCode = 1;
  }
}

run().catch(async (error) => {
  const outDirArgIndex = process.argv.indexOf('--outDir');
  const outDir = outDirArgIndex >= 0 ? process.argv[outDirArgIndex + 1] : '';
  if (outDir) {
    try {
      await fs.mkdir(path.resolve(outDir), { recursive: true });
      await fs.writeFile(
        path.join(path.resolve(outDir), 'fatal.json'),
        `${JSON.stringify({ status: 'error', message: String(error?.message ?? error) }, null, 2)}\n`,
        'utf8',
      );
    } catch {
      // ignore secondary failure
    }
  }
  console.error(error);
  process.exit(1);
});
