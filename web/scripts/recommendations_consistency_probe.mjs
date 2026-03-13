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
      response_data_source_postgres: false,
      response_has_run_id: false,
      response_has_generated_at_utc: false,
      freshness_not_stale: false,
      freshness_within_budget: false,
      response_nonempty_all_market: false,
      decision_summary_matches_all_market: false,
      classification_decision_consistency: false,
      confidence_range_consistency: false,
      reason_code_allowed: false,
      fallback_flag_consistency: false,
      health_counts_consistency: false,
      top_lists_consistency: false,
    },
    failures: [],
    details: {
      sign_in: {},
      recommendations_api: {},
      recommendations_page: {},
      computed: {
        decision_counts: {
          accumulate: 0,
          hold: 0,
          avoid: 0,
        },
        policy_mapped_rows: 0,
        fallback_rows: 0,
        bad_classification_rows: 0,
        bad_confidence_rows: 0,
        bad_reason_code_rows: 0,
        bad_fallback_flag_rows: 0,
        top_under50_invalid_rows: 0,
        top_asset_invalid_rows: 0,
      },
      freshness: {
        max_age_minutes: args.maxAgeMinutes,
        age_minutes: null,
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
    const allMarket = Array.isArray(payload.allMarket) ? payload.allMarket : [];
    const topUnder50 = Array.isArray(payload.topUnder50) ? payload.topUnder50 : [];
    const topByAssetType = payload.topByAssetType && typeof payload.topByAssetType === 'object' ? payload.topByAssetType : {};
    const decisionSummary = payload.decisionSummary && typeof payload.decisionSummary === 'object' ? payload.decisionSummary : {};
    const recommendationHealth = payload.recommendationHealth && typeof payload.recommendationHealth === 'object' ? payload.recommendationHealth : {};
    const freshness = payload.freshness && typeof payload.freshness === 'object' ? payload.freshness : {};

    const dataSource = String(payload.data_source ?? '').trim().toLowerCase();
    if (dataSource === 'postgres') {
      summary.checks.response_data_source_postgres = true;
    } else {
      summary.failures.push('recommendations_data_source_not_postgres');
    }

    const runId = String(payload.run_id ?? '').trim();
    if (runId) {
      summary.checks.response_has_run_id = true;
    } else {
      summary.failures.push('recommendations_missing_run_id');
    }

    const generatedAtIso = validIso(payload.generated_at_utc);
    if (generatedAtIso) {
      summary.checks.response_has_generated_at_utc = true;
      const ageMinutes = (Date.now() - Date.parse(generatedAtIso)) / 60000;
      summary.details.freshness.age_minutes = Number(ageMinutes.toFixed(3));
      if (ageMinutes <= args.maxAgeMinutes) {
        summary.checks.freshness_within_budget = true;
      } else {
        summary.failures.push('recommendations_snapshot_too_old');
      }
    } else {
      summary.failures.push('recommendations_generated_at_invalid');
    }

    if (freshness.stale === false) {
      summary.checks.freshness_not_stale = true;
    } else {
      summary.failures.push('recommendations_freshness_marked_stale');
    }

    if (allMarket.length > 0) {
      summary.checks.response_nonempty_all_market = true;
    } else {
      summary.failures.push('recommendations_all_market_empty');
    }

    let accumulate = 0;
    let hold = 0;
    let avoid = 0;
    let policyMappedRows = 0;
    let fallbackRows = 0;
    let badClassificationRows = 0;
    let badConfidenceRows = 0;
    let badReasonCodeRows = 0;
    let badFallbackFlagRows = 0;

    for (const row of allMarket) {
      const decision = String(row?.decision ?? '');
      const classification = String(row?.classification ?? '');
      const reasonCode = String(row?.decisionReasonCode ?? '');
      const fallbackUsed = Boolean(row?.fallbackUsed);

      if (decision === 'Accumulate') accumulate += 1;
      else if (decision === 'Avoid') avoid += 1;
      else hold += 1;

      if (reasonCode === 'PSCF_POLICY_DECISION') {
        policyMappedRows += 1;
      }
      if (fallbackUsed) {
        fallbackRows += 1;
      }

      if (classification !== decisionToClassification(decision)) {
        badClassificationRows += 1;
      }

      const sUf = Number(row?.S_UF);
      const rUf = Number(row?.R_UF);
      const confidence = Number(row?.confidence);
      const expectedConfidence = (sUf + rUf) / 2;
      const numericOk = isFiniteNumber(sUf) && isFiniteNumber(rUf) && isFiniteNumber(confidence);
      const rangeOk = confidence >= 0 && confidence <= 1 && sUf >= 0 && sUf <= 1 && rUf >= 0 && rUf <= 1;
      const confidenceOk = numericOk && rangeOk && approxEqual(confidence, expectedConfidence, args.epsilon);
      if (!confidenceOk) {
        badConfidenceRows += 1;
      }

      if (!ALLOWED_REASON_CODES.has(reasonCode)) {
        badReasonCodeRows += 1;
      }

      if (reasonCode === 'PSCF_POLICY_DECISION' && fallbackUsed) {
        badFallbackFlagRows += 1;
      }
      if (reasonCode !== 'PSCF_POLICY_DECISION' && !fallbackUsed) {
        badFallbackFlagRows += 1;
      }
    }

    summary.details.computed.decision_counts = { accumulate, hold, avoid };
    summary.details.computed.policy_mapped_rows = policyMappedRows;
    summary.details.computed.fallback_rows = fallbackRows;
    summary.details.computed.bad_classification_rows = badClassificationRows;
    summary.details.computed.bad_confidence_rows = badConfidenceRows;
    summary.details.computed.bad_reason_code_rows = badReasonCodeRows;
    summary.details.computed.bad_fallback_flag_rows = badFallbackFlagRows;

    const summaryMatch =
      Number(decisionSummary.accumulate ?? -1) === accumulate &&
      Number(decisionSummary.hold ?? -1) === hold &&
      Number(decisionSummary.avoid ?? -1) === avoid;
    if (summaryMatch) {
      summary.checks.decision_summary_matches_all_market = true;
    } else {
      summary.failures.push('recommendations_decision_summary_mismatch');
    }

    if (badClassificationRows === 0) {
      summary.checks.classification_decision_consistency = true;
    } else {
      summary.failures.push('recommendations_classification_mismatch');
    }

    if (badConfidenceRows === 0) {
      summary.checks.confidence_range_consistency = true;
    } else {
      summary.failures.push('recommendations_confidence_inconsistent');
    }

    if (badReasonCodeRows === 0) {
      summary.checks.reason_code_allowed = true;
    } else {
      summary.failures.push('recommendations_reason_code_invalid');
    }

    if (badFallbackFlagRows === 0) {
      summary.checks.fallback_flag_consistency = true;
    } else {
      summary.failures.push('recommendations_fallback_flag_inconsistent');
    }

    const total = allMarket.length;
    const coverageRate = total > 0 ? policyMappedRows / total : 0;
    const fallbackRate = total > 0 ? fallbackRows / total : 0;

    const healthCountsOk =
      Number(recommendationHealth.policyMappedRows ?? -1) === policyMappedRows &&
      Number(recommendationHealth.fallbackRows ?? -1) === fallbackRows &&
      approxEqual(Number(recommendationHealth.coverageRate ?? NaN), coverageRate, args.epsilon) &&
      approxEqual(Number(recommendationHealth.fallbackRate ?? NaN), fallbackRate, args.epsilon);

    if (healthCountsOk) {
      summary.checks.health_counts_consistency = true;
    } else {
      summary.failures.push('recommendations_health_counts_mismatch');
    }

    let badTopUnder50 = 0;
    for (const row of topUnder50) {
      const ok =
        String(row?.classification ?? '') === 'BUY' &&
        String(row?.assetType ?? '') === 'equities' &&
        isFiniteNumber(row?.price) &&
        Number(row?.price) < 50;
      if (!ok) badTopUnder50 += 1;
    }

    let badTopAsset = 0;
    for (const [assetType, rows] of Object.entries(topByAssetType)) {
      if (!Array.isArray(rows)) continue;
      for (const row of rows) {
        const ok =
          String(row?.classification ?? '') === 'BUY' &&
          String(row?.assetType ?? '') === String(assetType);
        if (!ok) badTopAsset += 1;
      }
    }

    summary.details.computed.top_under50_invalid_rows = badTopUnder50;
    summary.details.computed.top_asset_invalid_rows = badTopAsset;

    if (badTopUnder50 === 0 && badTopAsset === 0) {
      summary.checks.top_lists_consistency = true;
    } else {
      summary.failures.push('recommendations_top_lists_inconsistent');
    }

    summary.details.recommendations_api.meta = {
      run_id: payload.run_id ?? null,
      generated_at_utc: payload.generated_at_utc ?? null,
      snapshotSource: payload.snapshotSource ?? null,
      data_source: payload.data_source ?? null,
      freshness,
      universeStats: payload.universeStats ?? null,
      decisionSummary: payload.decisionSummary ?? null,
      recommendationHealth: payload.recommendationHealth ?? null,
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
