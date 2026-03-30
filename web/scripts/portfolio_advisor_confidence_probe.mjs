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
    symbols: ['AAPL', 'MSFT', 'SPY'],
    units: 1,
    unitCost: 100,
    epsilon: 0.01,
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

  args.units = Number(args.units || 1);
  if (!Number.isFinite(args.units) || args.units <= 0) args.units = 1;

  args.unitCost = Number(args.unitCost || 100);
  if (!Number.isFinite(args.unitCost) || args.unitCost <= 0) args.unitCost = 100;

  args.epsilon = Number(args.epsilon || 0.01);
  if (!Number.isFinite(args.epsilon) || args.epsilon <= 0) args.epsilon = 0.01;

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

function pushGap(gaps, id, detail) {
  gaps.push({ id, detail });
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');
  if (!Array.isArray(args.symbols) || args.symbols.length === 0) throw new Error('Missing probe symbols');

  const outDir = path.resolve(String(args.outDir));
  await fs.mkdir(outDir, { recursive: true });

  const requiredPositionFields = [
    'ticker',
    'units',
    'avgCost',
    'costBasis',
    'currentPrice',
    'marketValue',
    'unrealizedPnL',
    'unrealizedPnLPct',
    'decision',
    'decisionReason',
    'decisionReasonCode',
    'classification',
    'S_UF',
    'R_UF',
    'barCount',
    'minBarsForAccumulate',
  ];

  const summary = {
    generated_at_utc: toIso(),
    base_url: String(args.baseUrl),
    status: 'running',
    checks: {
      sign_in_success: false,
      portfolio_add_lots_success: false,
      portfolio_get_success: false,
      portfolio_page_http_200: false,
      portfolio_page_guidance_rails_present: false,
      portfolio_page_summary_cards_present: false,
      portfolio_page_section_headers_present: false,
      portfolio_page_table_headers_present: false,
      portfolio_page_table_rows_present: false,
      portfolio_page_research_links_present: false,
      portfolio_contains_saved_lots: false,
      portfolio_contains_saved_positions: false,
      advisor_decision_audit_fields_present: false,
      allocator_plan_present: false,
      allocator_rows_have_reason_and_action: false,
      summary_units_integrity: false,
      summary_cost_basis_integrity: false,
      portfolio_realized_pnl_contract_present: false,
      portfolio_benchmark_compare_contract_present: false,
      portfolio_store_source_postgres: false,
      snapshot_source_postgres: false,
    },
    failures: [],
    gaps: [],
    details: {
      symbols_under_test: args.symbols,
      sign_in: {},
      added_lots: [],
      portfolio_get: {},
      portfolio_page: {},
      integrity: {},
      cleanup: {
        removed_ids: [],
        remove_errors: [],
      },
    },
    screenshots: {
      portfolio_page: path.join(outDir, 'portfolio-page.png'),
    },
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.setDefaultTimeout(args.timeoutMs);

  const addedIds = [];

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

    let addFailures = 0;
    for (const symbol of args.symbols) {
      const addResp = await context.request.post(`${args.baseUrl}/api/portfolio`, {
        data: {
          ticker: symbol,
          units: args.units,
          unitCost: args.unitCost,
        },
        timeout: args.timeoutMs,
      });
      const addBodyText = await addResp.text();
      const addBody = parseJsonSafely(addBodyText);
      const addedId = String(addBody?.addedLot?.id ?? '').trim();
      if (addedId) addedIds.push(addedId);
      summary.details.added_lots.push({
        symbol,
        status: addResp.status(),
        added_id: addedId || null,
        body_sample: trimText(addBodyText, 1600),
      });
      if (!addResp.ok()) {
        addFailures += 1;
      }
    }

    if (addFailures === 0 && addedIds.length === args.symbols.length) {
      summary.checks.portfolio_add_lots_success = true;
    } else {
      summary.failures.push('portfolio_add_lots_failed');
    }

    const getResp = await context.request.get(`${args.baseUrl}/api/portfolio`, { timeout: args.timeoutMs });
    const getBodyText = await getResp.text();
    const getBody = parseJsonSafely(getBodyText);
    summary.details.portfolio_get = {
      status: getResp.status(),
      body_sample: trimText(getBodyText, 12000),
      parsed: getBody,
    };

    if (getResp.ok()) {
      summary.checks.portfolio_get_success = true;
    } else {
      summary.failures.push('portfolio_get_failed');
    }

    const pageResp = await page.goto(`${args.baseUrl}/portfolio`, {
      waitUntil: 'domcontentloaded',
      timeout: args.timeoutMs,
    });

    summary.details.portfolio_page = {
      status: pageResp ? pageResp.status() : null,
      url: page.url(),
    };

    if (pageResp && pageResp.status() === 200) {
      summary.checks.portfolio_page_http_200 = true;
    } else {
      summary.failures.push('portfolio_page_not_200');
    }

    await page.waitForTimeout(1500);
    await page.screenshot({ path: summary.screenshots.portfolio_page, fullPage: true });

    const pageText = await page.locator('body').innerText();

    const expectedGuidanceLabels = [
      'How This Page Works',
      'Decision Context',
    ];
    const missingGuidanceLabels = expectedGuidanceLabels.filter((label) => !String(pageText).includes(label));
    if (missingGuidanceLabels.length === 0) {
      summary.checks.portfolio_page_guidance_rails_present = true;
    } else {
      summary.failures.push('portfolio_page_guidance_rails_missing');
      summary.details.portfolio_page.missing_guidance_labels = missingGuidanceLabels;
    }

    const expectedSummaryCardLabels = [
      'Total Market Value',
      'Total Cost Basis',
      'Unrealized P/L',
      'Unrealized P/L %',
    ];
    const missingSummaryCardLabels = expectedSummaryCardLabels.filter((label) => !String(pageText).includes(label));
    if (missingSummaryCardLabels.length === 0) {
      summary.checks.portfolio_page_summary_cards_present = true;
    } else {
      summary.failures.push('portfolio_page_summary_cards_missing');
      summary.details.portfolio_page.missing_summary_card_labels = missingSummaryCardLabels;
    }

    const expectedSectionHeaders = [
      'Manual Portfolio',
      'Positions',
      'Lots',
    ];
    const missingSectionHeaders = expectedSectionHeaders.filter((label) => !String(pageText).includes(label));
    if (missingSectionHeaders.length === 0) {
      summary.checks.portfolio_page_section_headers_present = true;
    } else {
      summary.failures.push('portfolio_page_section_headers_missing');
      summary.details.portfolio_page.missing_section_headers = missingSectionHeaders;
    }

    const tableHeaderStats = await page.evaluate(() => {
      const headers = Array.from(document.querySelectorAll('table th'))
        .map((header) => String(header.textContent ?? '').replace(/\s+/g, ' ').trim())
        .filter((header) => header.length > 0);
      const researchLinkCount = Array.from(document.querySelectorAll('a, button'))
        .map((node) => String(node.textContent ?? '').replace(/\s+/g, ' ').trim())
        .filter((text) => text.startsWith('Research'))
        .length;
      return {
        headers,
        researchLinkCount,
      };
    });
    const normalizedTableHeaders = tableHeaderStats.headers.map((header) =>
      header
        .replace(/[▲▼]/g, '')
        .replace(/\s+/g, ' ')
        .trim(),
    );
    summary.details.portfolio_page.table_headers = tableHeaderStats.headers;
    summary.details.portfolio_page.table_headers_normalized = normalizedTableHeaders;
    summary.details.portfolio_page.research_link_count = tableHeaderStats.researchLinkCount;

    const expectedTableHeaderGroups = [
      ['Ticker'],
      ['Asset'],
      ['Units'],
      ['Avg Cost'],
      ['Price'],
      ['Market Value'],
      ['Net P/L %'],
      ['Decision'],
      ['S_UF'],
      ['R_UF'],
      ['Bars'],
      ['Research'],
      ['Unit Cost'],
      ['Added'],
      ['Updated'],
      ['Action'],
    ];
    const missingTableHeaders = expectedTableHeaderGroups
      .filter(
        (group) =>
          !group.some((label) =>
            normalizedTableHeaders.some((header) => header === label || header.includes(label)),
          ),
      )
      .map((group) => group.join(' | '));
    if (missingTableHeaders.length === 0) {
      summary.checks.portfolio_page_table_headers_present = true;
    } else {
      summary.failures.push('portfolio_page_table_headers_missing');
      summary.details.portfolio_page.missing_table_headers = missingTableHeaders;
    }

    const tableStats = await page.evaluate(() => {
      const tables = Array.from(document.querySelectorAll('table'));
      const rowCounts = tables.map((table) => table.querySelectorAll('tbody tr').length);
      return {
        tableCount: tables.length,
        rowCounts,
      };
    });
    summary.details.portfolio_page.table_stats = tableStats;

    const nonEmptyTableCount = Array.isArray(tableStats.rowCounts)
      ? tableStats.rowCounts.filter((value) => Number(value) > 0).length
      : 0;
    if (tableStats.tableCount >= 2 && nonEmptyTableCount >= 2) {
      summary.checks.portfolio_page_table_rows_present = true;
    } else {
      summary.failures.push('portfolio_page_table_rows_missing_or_empty');
    }

    const lots = Array.isArray(getBody?.lots) ? getBody.lots : [];
    const positions = Array.isArray(getBody?.positions) ? getBody.positions : [];
    const summaryObj = getBody?.summary && typeof getBody.summary === 'object' ? getBody.summary : {};
    const allocatorPlan = getBody?.allocatorPlan && typeof getBody.allocatorPlan === 'object' ? getBody.allocatorPlan : null;

    if (positions.length > 0 && tableHeaderStats.researchLinkCount >= positions.length) {
      summary.checks.portfolio_page_research_links_present = true;
    } else {
      summary.failures.push('portfolio_page_research_links_missing');
      summary.details.portfolio_page.expected_research_links_min = positions.length;
    }

    const expectedTickers = new Set(args.symbols);
    const lotTickers = new Set(
      lots
        .map((lot) => String(lot?.ticker ?? '').trim().toUpperCase())
        .filter((value) => value.length > 0),
    );
    const positionTickers = new Set(
      positions
        .map((row) => String(row?.ticker ?? '').trim().toUpperCase())
        .filter((value) => value.length > 0),
    );

    if ([...expectedTickers].every((ticker) => lotTickers.has(ticker))) {
      summary.checks.portfolio_contains_saved_lots = true;
    } else {
      summary.failures.push('portfolio_missing_saved_lots');
    }

    if ([...expectedTickers].every((ticker) => positionTickers.has(ticker))) {
      summary.checks.portfolio_contains_saved_positions = true;
    } else {
      summary.failures.push('portfolio_missing_saved_positions');
    }

    const auditFieldsMissing = [];
    for (const row of positions) {
      for (const field of requiredPositionFields) {
        if (!(field in row)) {
          auditFieldsMissing.push({ ticker: row?.ticker ?? null, field });
        }
      }
      const decision = String(row?.decision ?? '');
      const code = String(row?.decisionReasonCode ?? '');
      const reason = String(row?.decisionReason ?? '');
      if (!['Accumulate', 'Hold', 'Avoid'].includes(decision)) {
        auditFieldsMissing.push({ ticker: row?.ticker ?? null, field: 'decision_value_invalid' });
      }
      if (!code || !reason) {
        auditFieldsMissing.push({ ticker: row?.ticker ?? null, field: 'decision_reason_missing' });
      }
    }

    if (auditFieldsMissing.length === 0 && positions.length > 0) {
      summary.checks.advisor_decision_audit_fields_present = true;
    } else {
      summary.failures.push('advisor_decision_audit_fields_missing');
      summary.details.integrity.audit_fields_missing = auditFieldsMissing;
    }

    if (allocatorPlan && Array.isArray(allocatorPlan.rows)) {
      summary.checks.allocator_plan_present = true;

      let allocatorRowIssues = 0;
      for (const row of allocatorPlan.rows) {
        const action = String(row?.action ?? '').trim();
        const reason = String(row?.reason ?? '').trim();
        if (!action || !reason) allocatorRowIssues += 1;
      }
      if (allocatorRowIssues === 0) {
        summary.checks.allocator_rows_have_reason_and_action = true;
      } else {
        summary.failures.push('allocator_rows_missing_reason_or_action');
      }
    } else {
      summary.failures.push('allocator_plan_missing');
    }

    const unitsFromLots = lots.reduce((sum, lot) => sum + Number(lot?.units ?? 0), 0);
    const costBasisFromLots = lots.reduce((sum, lot) => sum + Number(lot?.units ?? 0) * Number(lot?.unitCost ?? 0), 0);

    summary.details.integrity.units_from_lots = unitsFromLots;
    summary.details.integrity.summary_total_units = Number(summaryObj?.totalUnits ?? NaN);
    summary.details.integrity.cost_basis_from_lots = costBasisFromLots;
    summary.details.integrity.summary_total_cost_basis = Number(summaryObj?.totalCostBasis ?? NaN);

    if (isFiniteNumber(summaryObj?.totalUnits) && approxEqual(summaryObj.totalUnits, unitsFromLots, args.epsilon)) {
      summary.checks.summary_units_integrity = true;
    } else {
      summary.failures.push('summary_units_integrity_failed');
    }

    if (isFiniteNumber(summaryObj?.totalCostBasis) && approxEqual(summaryObj.totalCostBasis, costBasisFromLots, args.epsilon)) {
      summary.checks.summary_cost_basis_integrity = true;
    } else {
      summary.failures.push('summary_cost_basis_integrity_failed');
    }

    const source = String(getBody?.source ?? '').trim();
    const snapshotSource = String(getBody?.snapshotSource ?? '').trim();

    summary.details.integrity.source = source;
    summary.details.integrity.snapshot_source = snapshotSource;

    if (source.startsWith('postgres://')) {
      summary.checks.portfolio_store_source_postgres = true;
    } else {
      summary.failures.push('portfolio_store_source_not_postgres');
      pushGap(summary.gaps, 'portfolio_store_backend_not_postgres', `source=${source || '<empty>'}`);
    }

    if (snapshotSource.startsWith('postgres://')) {
      summary.checks.snapshot_source_postgres = true;
    } else {
      summary.failures.push('portfolio_snapshot_source_not_postgres');
      pushGap(summary.gaps, 'portfolio_snapshot_backend_not_postgres', `snapshotSource=${snapshotSource || '<empty>'}`);
    }

    if (!('quoteSource' in (getBody || {}))) {
      pushGap(summary.gaps, 'portfolio_quote_source_not_exposed', 'GET /api/portfolio response does not expose quoteSource for traceability.');
    }
    if (!('run_id' in (getBody || {}))) {
      pushGap(summary.gaps, 'portfolio_runtime_run_id_not_exposed', 'GET /api/portfolio response does not expose run_id for runtime provenance.');
    }
    if (!('generated_at_utc' in (getBody || {}))) {
      pushGap(summary.gaps, 'portfolio_runtime_generated_at_not_exposed', 'GET /api/portfolio response does not expose generated_at_utc for freshness audit.');
    }

    const realizedContractFields = ['realizedPnL', 'realizedPnLPct', 'realizedPnLStatus', 'realizedPnLMethod'];
    const missingRealizedContractFields = realizedContractFields.filter((field) => !(field in summaryObj));
    const realizedStatus = String(summaryObj?.realizedPnLStatus ?? '').trim();
    const realizedMethod = String(summaryObj?.realizedPnLMethod ?? '').trim();
    const realizedStatusValid =
      realizedStatus === 'unavailable_no_trade_ledger' || realizedStatus === 'computed_from_trade_ledger';
    const realizedMethodValid = realizedMethod === 'trade_ledger_required' || realizedMethod === 'trade_ledger_v1';

    if (missingRealizedContractFields.length === 0 && realizedStatusValid && realizedMethodValid) {
      summary.checks.portfolio_realized_pnl_contract_present = true;
    } else {
      summary.failures.push('portfolio_realized_pnl_contract_missing_or_invalid');
      pushGap(
        summary.gaps,
        'portfolio_realized_pnl_contract_not_present',
        `missing_fields=${missingRealizedContractFields.join(',') || '<none>'}; status=${realizedStatus || '<empty>'}; method=${realizedMethod || '<empty>'}`,
      );
    }

    const benchmarkObj = getBody?.benchmark && typeof getBody.benchmark === 'object' ? getBody.benchmark : null;
    const benchmarkContractFields = [
      'symbol',
      'portfolioReturnPct',
      'benchmarkReturnPct',
      'relativeReturnPctPoints',
      'status',
      'method',
    ];
    const missingBenchmarkContractFields = benchmarkContractFields.filter((field) => !(field in (benchmarkObj || {})));
    const benchmarkSymbol = String(benchmarkObj?.symbol ?? '').trim();
    const benchmarkStatus = String(benchmarkObj?.status ?? '').trim();
    const benchmarkMethod = String(benchmarkObj?.method ?? '').trim();
    const benchmarkStatusValid =
      benchmarkStatus === 'unavailable_same_dates_same_dollars_ledger_required' ||
      benchmarkStatus === 'computed_same_dates_same_dollars_v1';
    const benchmarkMethodValid =
      benchmarkMethod === 'same_dates_same_dollars_ledger_required' ||
      benchmarkMethod === 'same_dates_same_dollars_v1';

    if (
      missingBenchmarkContractFields.length === 0 &&
      benchmarkSymbol === 'SPY' &&
      benchmarkStatusValid &&
      benchmarkMethodValid
    ) {
      summary.checks.portfolio_benchmark_compare_contract_present = true;
    } else {
      summary.failures.push('portfolio_benchmark_compare_contract_missing_or_invalid');
      pushGap(
        summary.gaps,
        'portfolio_benchmark_compare_contract_not_present',
        `missing_fields=${missingBenchmarkContractFields.join(',') || '<none>'}; symbol=${benchmarkSymbol || '<empty>'}; status=${benchmarkStatus || '<empty>'}; method=${benchmarkMethod || '<empty>'}`,
      );
    }
  } finally {
    for (const lotId of addedIds) {
      try {
        const deleteResp = await context.request.delete(`${args.baseUrl}/api/portfolio?id=${encodeURIComponent(lotId)}`, {
          timeout: args.timeoutMs,
        });
        const ok = deleteResp.ok();
        summary.details.cleanup.removed_ids.push({ id: lotId, status: deleteResp.status(), ok });
        if (!ok) {
          const body = await deleteResp.text();
          summary.details.cleanup.remove_errors.push({ id: lotId, status: deleteResp.status(), body_sample: trimText(body) });
        }
      } catch (error) {
        summary.details.cleanup.remove_errors.push({
          id: lotId,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    await browser.close();
  }

  if (summary.details.cleanup.remove_errors.length > 0) {
    summary.failures.push('portfolio_cleanup_failed');
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
