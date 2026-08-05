#!/usr/bin/env node
import fs from 'node:fs/promises';

const API_TABS = ['overview', 'valuation', 'financial', 'ownership', 'performance', 'technical', 'etf'];
const DATA_TAB_API_MAP = [
  { dataTab: 'overview', apiTab: 'overview' },
  { dataTab: 'valuation', apiTab: 'valuation' },
  { dataTab: 'financial', apiTab: 'financial' },
  { dataTab: 'ownership', apiTab: 'ownership' },
  { dataTab: 'performance', apiTab: 'performance' },
  { dataTab: 'technical', apiTab: 'technical' },
  { dataTab: 'etf', apiTab: 'etf' },
  { dataTab: 'etfPerf', apiTab: 'etf' },
  { dataTab: 'basic', apiTab: 'overview' },
  { dataTab: 'ta', apiTab: 'technical' },
  { dataTab: 'newsTab', apiTab: 'performance' },
  { dataTab: 'maps', apiTab: 'overview' },
];

const ADVANCED_KEYS = [
  'exchange',
  'index',
  'sector',
  'industry',
  'country',
  'marketCap',
  'dividendYield',
  'shortFloat',
  'analystRecom',
  'optionShort',
  'earningsDate',
  'avgVolume',
  'relVolume',
  'currentVolume',
  'trades',
  'priceBand',
  'targetPrice',
  'ipoDate',
  'sharesOutstanding',
  'float',
  'theme',
  'subTheme',
];

function parseArgs(argv) {
  const out = {
    baseUrl: 'https://taofinancialengine.com',
    username: '',
    password: '',
    out: '',
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

function withTimeout(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return {
    signal: controller.signal,
    done: () => clearTimeout(timer),
  };
}

async function fetchJson(url, init, timeoutMs) {
  const t = withTimeout(timeoutMs);
  try {
    const res = await fetch(url, { ...init, signal: t.signal });
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    return { res, body };
  } finally {
    t.done();
  }
}

function parseSetCookieToHeader(setCookies) {
  if (!Array.isArray(setCookies) || setCookies.length === 0) return '';
  return setCookies
    .map((c) => String(c).split(';')[0].trim())
    .filter(Boolean)
    .join('; ');
}

function normalizeRows(value) {
  return Array.isArray(value) ? value : [];
}

function everyRow(rows, predicate) {
  for (const row of rows) {
    if (!predicate(row)) return false;
  }
  return true;
}

function firstEligibleOptionValue(block) {
  const optionPattern = /value:\s*"([^"]*)"/g;
  let match;
  while ((match = optionPattern.exec(block)) !== null) {
    const value = String(match[1] ?? '').trim();
    if (!value || value === 'custom_subscription') continue;
    return value;
  }
  return null;
}

function extractSampleValues(fileText) {
  const samples = {};
  for (const key of ADVANCED_KEYS) {
    const blockMatch = new RegExp(`${key}:\\s*\\[(.*?)\\n\\s*\\],`, 's').exec(fileText);
    if (!blockMatch) {
      samples[key] = null;
      continue;
    }
    samples[key] = firstEligibleOptionValue(blockMatch[1]);
  }
  return samples;
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.out) throw new Error('Missing --out');

  const result = {
    generated_at_utc: new Date().toISOString(),
    base_url: args.baseUrl,
    status: 'running',
    auth: { signed_in: false, user: null, error: null },
    samples: {},
    checks: {
      baseline_totals_by_api_tab: {},
      top_controls_by_api_tab: [],
      numeric_filters_by_api_tab: [],
      advanced_filters_by_data_tab: [],
    },
    failures: [],
    warnings: [],
  };

  const filterOptionsText = await fs.readFile('/workspaces/Tao_Financial_Engine/web/src/lib/screener-filter-v111.ts', 'utf8');
  const samples = extractSampleValues(filterOptionsText);
  result.samples = samples;

  const signIn = await fetchJson(
    `${args.baseUrl}/api/auth/sign-in`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username: args.username, password: args.password, next: '/' }),
      redirect: 'manual',
    },
    args.timeoutMs,
  );

  const setCookies = typeof signIn.res.headers.getSetCookie === 'function' ? signIn.res.headers.getSetCookie() : [];
  const cookieHeader = parseSetCookieToHeader(setCookies);
  if (!signIn.res.ok || !signIn.body || signIn.body.signedIn !== true || !cookieHeader) {
    result.auth.error = {
      status: signIn.res.status,
      body: signIn.body,
      has_cookie: Boolean(cookieHeader),
    };
    result.status = 'failed';
    await fs.writeFile(args.out, JSON.stringify(result, null, 2), 'utf8');
    return;
  }

  result.auth.signed_in = true;
  result.auth.user = signIn.body.user || null;

  async function callScreener(params) {
    const url = `${args.baseUrl}/api/screener?${params.toString()}`;
    const { res, body } = await fetchJson(url, { method: 'GET', headers: { cookie: cookieHeader } }, args.timeoutMs);
    return { status: res.status, ok: res.ok, body, url };
  }

  const optionsByApiTab = {};

  for (const tab of API_TABS) {
    const base = new URLSearchParams({ tab, page: '1', pageSize: '50', sortKey: 'ticker', sortDir: 'asc' });
    const response = await callScreener(base);
    const rows = normalizeRows(response.body?.rows);
    const total = Number(response.body?.total ?? rows.length);

    result.checks.baseline_totals_by_api_tab[tab] = {
      status: response.status,
      total,
      row_count: rows.length,
    };

    if (!response.ok || !Array.isArray(response.body?.rows)) {
      result.failures.push({ type: 'baseline_tab_request', tab, status: response.status, error: response.body?.error || null });
      continue;
    }

    optionsByApiTab[tab] = {
      decisions: Array.isArray(response.body?.options?.decisions) ? response.body.options.decisions : [],
      assetTypes: Array.isArray(response.body?.options?.assetTypes) ? response.body.options.assetTypes : [],
    };

    const decisionSample = optionsByApiTab[tab].decisions.find((value) => value === 'Accumulate') || optionsByApiTab[tab].decisions[0] || null;
    if (decisionSample) {
      const p = new URLSearchParams(base);
      p.set('decision', decisionSample);
      const r = await callScreener(p);
      const decisionRows = normalizeRows(r.body?.rows);
      const decisionOk = r.ok && everyRow(decisionRows, (row) => String(row.decision || '') === String(decisionSample));
      result.checks.top_controls_by_api_tab.push({ tab, control: 'decision', value: decisionSample, status: r.status, ok: decisionOk, total: r.body?.total ?? null, row_count: decisionRows.length });
      if (!decisionOk) {
        result.failures.push({ type: 'decision_filter_behavior', tab, value: decisionSample, status: r.status, row_count: decisionRows.length });
      }
    }

    const assetSample = tab === 'etf' ? 'etf' : 'equities';
    const pAsset = new URLSearchParams(base);
    pAsset.set('assetType', assetSample);
    const rAsset = await callScreener(pAsset);
    const assetRows = normalizeRows(rAsset.body?.rows);
    const assetOk = rAsset.ok && everyRow(assetRows, (row) => String(row.assetType || '') === String(assetSample));
    result.checks.top_controls_by_api_tab.push({ tab, control: 'assetType', value: assetSample, status: rAsset.status, ok: assetOk, total: rAsset.body?.total ?? null, row_count: assetRows.length });
    if (!assetOk) {
      result.failures.push({ type: 'asset_filter_behavior', tab, value: assetSample, status: rAsset.status, row_count: assetRows.length });
    }

    const numericCases = [
      { key: 'minPrice', value: '100' },
      { key: 'maxPrice', value: '10' },
      { key: 'minBars', value: '250' },
      { key: 'maxBars', value: '30' },
    ];
    for (const numeric of numericCases) {
      const pNum = new URLSearchParams(base);
      pNum.set(numeric.key, numeric.value);
      const rNum = await callScreener(pNum);
      const numRows = normalizeRows(rNum.body?.rows);
      let rowsRespect = false;
      if (numeric.key === 'minPrice') rowsRespect = everyRow(numRows, (row) => row.price != null && Number(row.price) >= Number(numeric.value));
      if (numeric.key === 'maxPrice') rowsRespect = everyRow(numRows, (row) => row.price != null && Number(row.price) <= Number(numeric.value));
      if (numeric.key === 'minBars') rowsRespect = everyRow(numRows, (row) => Number(row.barCount || 0) >= Number(numeric.value));
      if (numeric.key === 'maxBars') rowsRespect = everyRow(numRows, (row) => Number(row.barCount || 0) <= Number(numeric.value));
      const ok = rNum.ok && rowsRespect;
      result.checks.numeric_filters_by_api_tab.push({ tab, key: numeric.key, value: numeric.value, status: rNum.status, ok, total: rNum.body?.total ?? null, row_count: numRows.length });
      if (!ok) {
        result.failures.push({ type: 'numeric_filter_behavior', tab, key: numeric.key, value: numeric.value, status: rNum.status, row_count: numRows.length });
      }
    }
  }

  for (const key of ADVANCED_KEYS) {
    const sample = samples[key];
    if (!sample) {
      result.warnings.push({
        type: 'advanced_filter_sample_missing',
        key,
        note: 'No non-empty/non-custom option available to validate this control in non-elite mode.',
      });
      continue;
    }

    let changedAnyTab = false;

    for (const mapping of DATA_TAB_API_MAP) {
      const baseline = result.checks.baseline_totals_by_api_tab[mapping.apiTab] || { total: null };
      const baselineTotal = Number(baseline.total ?? 0);
      const p = new URLSearchParams({
        tab: mapping.apiTab,
        page: '1',
        pageSize: '50',
        sortKey: 'ticker',
        sortDir: 'asc',
      });
      p.set(key, sample);

      const r = await callScreener(p);
      const total = Number(r.body?.total ?? 0);
      const echoOk = r.body?.filters?.[key] === sample;
      const statusOk = r.ok && Array.isArray(r.body?.rows);
      const monotonicOk = total <= baselineTotal;
      const changed = total !== baselineTotal;
      if (changed) changedAnyTab = true;

      const ok = statusOk && echoOk && monotonicOk;
      result.checks.advanced_filters_by_data_tab.push({
        dataTab: mapping.dataTab,
        apiTab: mapping.apiTab,
        key,
        value: sample,
        status: r.status,
        ok,
        changed_total: changed,
        baseline_total: baselineTotal,
        filtered_total: total,
        row_count: Array.isArray(r.body?.rows) ? r.body.rows.length : null,
      });

      if (!ok) {
        result.failures.push({
          type: 'advanced_filter_behavior',
          dataTab: mapping.dataTab,
          apiTab: mapping.apiTab,
          key,
          value: sample,
          status: r.status,
          echo_ok: echoOk,
          monotonic_ok: monotonicOk,
          baseline_total: baselineTotal,
          filtered_total: total,
          error: r.body?.error || null,
        });
      }
    }

    if (!changedAnyTab) {
      result.warnings.push({
        type: 'advanced_filter_no_total_change_any_tab',
        key,
        value: sample,
        note: 'Control executed successfully but did not change total rows; this may indicate permissive bucket semantics or pipeline coverage limits.',
      });
    }
  }

  result.status = result.failures.length === 0 ? 'pass' : 'fail';
  await fs.writeFile(args.out, JSON.stringify(result, null, 2), 'utf8');
}

run().catch(async (error) => {
  const args = parseArgs(process.argv);
  const payload = {
    generated_at_utc: new Date().toISOString(),
    status: 'error',
    error: error instanceof Error ? { name: error.name, message: error.message, stack: error.stack } : String(error),
  };
  if (args.out) {
    try {
      await fs.writeFile(args.out, JSON.stringify(payload, null, 2), 'utf8');
    } catch {
      // ignore
    }
  }
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
});
