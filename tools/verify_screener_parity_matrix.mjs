#!/usr/bin/env node
import fs from 'node:fs/promises';

function parseArgs(argv) {
  const out = {
    baseUrl: 'https://taofinancialengine.com',
    username: '',
    password: '',
    out: '',
    concurrency: 10,
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
  out.concurrency = Number(out.concurrency || 10);
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

function normalizeTabs(raw) {
  return Array.isArray(raw) ? raw.map((x) => String(x || '').trim()).filter(Boolean) : [];
}

function everyRow(rows, predicate) {
  for (const row of rows || []) {
    if (!predicate(row)) return false;
  }
  return true;
}

function sortCheck(rows, key, dir) {
  if (!Array.isArray(rows) || rows.length < 2) return true;
  const asc = dir === 'asc';
  const toVal = (row) => {
    if (key === 'ticker') return String(row.ticker || '');
    if (key === 'assetType') return String(row.assetType || '');
    if (key === 'decision') return String(row.decision || '');
    if (key === 'price') return row.price == null ? Number.NEGATIVE_INFINITY : Number(row.price);
    if (key === 'barCount') return Number(row.barCount || 0);
    if (key === 'stabilityScore') return row.stabilityScore == null ? Number.NEGATIVE_INFINITY : Number(row.stabilityScore);
    if (key === 'maxDrawdown') return row.maxDrawdown == null ? Number.NEGATIVE_INFINITY : Number(row.maxDrawdown);
    if (key === 'regime') return String(row.regime || '');
    return '';
  };
  for (let i = 1; i < rows.length; i += 1) {
    const a = toVal(rows[i - 1]);
    const b = toVal(rows[i]);
    if (typeof a === 'string' || typeof b === 'string') {
      const cmp = String(a).localeCompare(String(b));
      if (asc ? cmp > 0 : cmp < 0) return false;
    } else {
      if (asc ? a > b : a < b) return false;
    }
  }
  return true;
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) {
    throw new Error('Missing --username or --password');
  }
  if (!args.out) {
    throw new Error('Missing --out output json path');
  }

  const now = new Date().toISOString();
  const result = {
    generated_at_utc: now,
    base_url: args.baseUrl,
    status: 'running',
    auth: { signed_in: false, user: null, error: null },
    checks: {
      tab_options: null,
      top_controls: null,
      numeric_filters: [],
      signal_filters: [],
      asset_filters: [],
      sort_checks: [],
      advanced_filter_options: null,
      advanced_filter_requests: null,
      tab_requests: [],
      maps_payload: null,
    },
    failures: [],
  };

  const signInUrl = `${args.baseUrl}/api/auth/sign-in`;
  const signIn = await fetchJson(
    signInUrl,
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

  const api = async (params) => {
    const url = `${args.baseUrl}/api/screener?${params.toString()}`;
    const { res, body } = await fetchJson(
      url,
      {
        method: 'GET',
        headers: { cookie: cookieHeader },
      },
      args.timeoutMs,
    );
    return { url, status: res.status, ok: res.ok, body };
  };

  const baseParams = new URLSearchParams({ tab: 'overview', page: '1', pageSize: '25', sortKey: 'ticker', sortDir: 'asc' });
  const baseline = await api(baseParams);
  if (!baseline.ok || !baseline.body) {
    result.failures.push({ type: 'baseline_api', detail: baseline });
    result.status = 'failed';
    await fs.writeFile(args.out, JSON.stringify(result, null, 2), 'utf8');
    return;
  }

  const options = baseline.body.options || {};
  const advancedFilterOptions = baseline.body.advancedFilterOptions || {};

  const expectedApiTabs = ['overview', 'valuation', 'financial', 'ownership', 'performance', 'technical', 'etf'];
  const apiTabs = normalizeTabs(options.tabs);
  const missingApiTabs = expectedApiTabs.filter((t) => !apiTabs.includes(t));
  result.checks.tab_options = {
    api_tabs: apiTabs,
    missing_expected_api_tabs: missingApiTabs,
  };
  if (missingApiTabs.length) {
    result.failures.push({ type: 'tab_options', missing: missingApiTabs });
  }

  const expectedControlKeys = ['assetTypes', 'decisions', 'sortKeys'];
  const missingControlKeys = expectedControlKeys.filter((k) => !Array.isArray(options[k]));
  result.checks.top_controls = {
    has_asset_types: Array.isArray(options.assetTypes),
    has_decisions: Array.isArray(options.decisions),
    has_sort_keys: Array.isArray(options.sortKeys),
    missing_control_keys: missingControlKeys,
  };
  if (missingControlKeys.length) {
    result.failures.push({ type: 'top_controls', missing: missingControlKeys });
  }

  for (const tab of expectedApiTabs) {
    const p = new URLSearchParams({ tab, page: '1', pageSize: '15', sortKey: 'ticker', sortDir: 'asc' });
    const r = await api(p);
    const ok = r.ok && Array.isArray(r.body?.rows);
    result.checks.tab_requests.push({ tab, status: r.status, ok, row_count: Array.isArray(r.body?.rows) ? r.body.rows.length : null, error: r.body?.error || null });
    if (!ok) result.failures.push({ type: 'tab_request', tab, status: r.status, error: r.body?.error || null });
  }

  const numericCases = [
    { key: 'minPrice', value: '100' },
    { key: 'maxPrice', value: '10' },
    { key: 'minBars', value: '250' },
    { key: 'maxBars', value: '30' },
  ];

  for (const c of numericCases) {
    const p = new URLSearchParams(baseParams);
    p.set(c.key, c.value);
    const r = await api(p);
    const rows = Array.isArray(r.body?.rows) ? r.body.rows : [];
    let rowsRespect = false;
    if (c.key === 'minPrice') rowsRespect = everyRow(rows, (row) => row.price != null && Number(row.price) >= Number(c.value));
    if (c.key === 'maxPrice') rowsRespect = everyRow(rows, (row) => row.price != null && Number(row.price) <= Number(c.value));
    if (c.key === 'minBars') rowsRespect = everyRow(rows, (row) => Number(row.barCount || 0) >= Number(c.value));
    if (c.key === 'maxBars') rowsRespect = everyRow(rows, (row) => Number(row.barCount || 0) <= Number(c.value));
    const ok = r.ok && rowsRespect;
    result.checks.numeric_filters.push({ key: c.key, value: c.value, status: r.status, ok, row_count: rows.length });
    if (!ok) result.failures.push({ type: 'numeric_filter', key: c.key, value: c.value, status: r.status, row_count: rows.length });
  }

  const decisions = Array.isArray(options.decisions) ? options.decisions : [];
  for (const decision of decisions) {
    const p = new URLSearchParams(baseParams);
    p.set('decision', decision);
    const r = await api(p);
    const rows = Array.isArray(r.body?.rows) ? r.body.rows : [];
    const ok = r.ok && everyRow(rows, (row) => String(row.decision || '') === String(decision));
    result.checks.signal_filters.push({ decision, status: r.status, ok, row_count: rows.length });
    if (!ok) result.failures.push({ type: 'decision_filter', decision, status: r.status, row_count: rows.length });
  }

  const assetTypes = Array.isArray(options.assetTypes) ? options.assetTypes : [];
  for (const assetType of assetTypes) {
    const p = new URLSearchParams(baseParams);
    p.set('assetType', assetType);
    const r = await api(p);
    const rows = Array.isArray(r.body?.rows) ? r.body.rows : [];
    const ok = r.ok && everyRow(rows, (row) => String(row.assetType || '') === String(assetType));
    result.checks.asset_filters.push({ tab: 'overview', assetType, status: r.status, ok, row_count: rows.length });
    if (!ok) result.failures.push({ type: 'asset_filter_overview', assetType, status: r.status, row_count: rows.length });
  }

  const etfNoAssetParams = new URLSearchParams({ tab: 'etf', page: '1', pageSize: '25', sortKey: 'ticker', sortDir: 'asc' });
  const etfNoAsset = await api(etfNoAssetParams);
  const etfRows = Array.isArray(etfNoAsset.body?.rows) ? etfNoAsset.body.rows : [];
  const etfOk = etfNoAsset.ok && everyRow(etfRows, (row) => String(row.assetType || '') === 'etf');
  result.checks.asset_filters.push({ tab: 'etf', assetType: '(implicit etf)', status: etfNoAsset.status, ok: etfOk, row_count: etfRows.length });
  if (!etfOk) result.failures.push({ type: 'asset_filter_etf_implicit', status: etfNoAsset.status, row_count: etfRows.length });

  const sortKeys = Array.isArray(options.sortKeys) ? options.sortKeys : [];
  for (const sortKey of sortKeys) {
    for (const sortDir of ['asc', 'desc']) {
      const p = new URLSearchParams(baseParams);
      p.set('sortKey', sortKey);
      p.set('sortDir', sortDir);
      const r = await api(p);
      const rows = Array.isArray(r.body?.rows) ? r.body.rows : [];
      const ok = r.ok && sortCheck(rows, sortKey, sortDir);
      result.checks.sort_checks.push({ sortKey, sortDir, status: r.status, ok, row_count: rows.length });
      if (!ok) result.failures.push({ type: 'sort_check', sortKey, sortDir, status: r.status, row_count: rows.length });
    }
  }

  const requiredAdvancedKeys = [
    'exchange', 'index', 'sector', 'industry', 'country',
    'marketCap', 'dividendYield', 'shortFloat', 'analystRecom', 'optionShort',
    'earningsDate', 'avgVolume', 'relVolume', 'currentVolume', 'trades',
    'priceBand', 'targetPrice', 'ipoDate', 'sharesOutstanding', 'float',
    'theme', 'subTheme',
  ];

  const missingAdvancedKeys = requiredAdvancedKeys.filter((k) => !Array.isArray(advancedFilterOptions[k]));
  result.checks.advanced_filter_options = {
    key_count: Object.keys(advancedFilterOptions).length,
    missing_required_keys: missingAdvancedKeys,
  };
  if (missingAdvancedKeys.length) result.failures.push({ type: 'advanced_keys_missing', missing: missingAdvancedKeys });

  const advancedRequests = [];
  const queue = [];
  for (const key of requiredAdvancedKeys) {
    const opts = Array.isArray(advancedFilterOptions[key]) ? advancedFilterOptions[key] : [];
    for (const opt of opts) {
      const value = String(opt?.value ?? '').trim();
      if (!value) continue;
      queue.push({ key, value });
    }
  }

  let idx = 0;
  let failures = 0;
  async function worker() {
    while (idx < queue.length) {
      const current = queue[idx];
      idx += 1;
      const p = new URLSearchParams(baseParams);
      p.set(current.key, current.value);
      const r = await api(p);
      const ok = r.ok && Array.isArray(r.body?.rows) && r.body?.filters?.[current.key] === current.value;
      advancedRequests.push({ key: current.key, value: current.value, status: r.status, ok, row_count: Array.isArray(r.body?.rows) ? r.body.rows.length : null, error: r.body?.error || null });
      if (!ok) {
        failures += 1;
        result.failures.push({ type: 'advanced_filter_request', key: current.key, value: current.value, status: r.status, error: r.body?.error || null });
      }
    }
  }

  const workers = [];
  for (let i = 0; i < Math.max(1, args.concurrency); i += 1) workers.push(worker());
  await Promise.all(workers);

  result.checks.advanced_filter_requests = {
    total_requests: advancedRequests.length,
    failed_requests: failures,
  };

  const mapParams = new URLSearchParams(baseParams);
  mapParams.set('includeMap', '1');
  const mapResponse = await api(mapParams);
  const mapTickers = Array.isArray(mapResponse.body?.mapTickers) ? mapResponse.body.mapTickers : [];
  result.checks.maps_payload = {
    status: mapResponse.status,
    ok: mapResponse.ok,
    map_ticker_count: mapTickers.length,
    has_map_tickers: mapTickers.length > 0,
  };
  if (!(mapResponse.ok && mapTickers.length > 0)) {
    result.failures.push({ type: 'maps_payload', status: mapResponse.status, map_ticker_count: mapTickers.length });
  }

  result.status = result.failures.length === 0 ? 'pass' : 'fail';
  await fs.writeFile(args.out, JSON.stringify(result, null, 2), 'utf8');
}

run().catch(async (err) => {
  const fallback = {
    generated_at_utc: new Date().toISOString(),
    status: 'error',
    error: err instanceof Error ? { name: err.name, message: err.message, stack: err.stack } : String(err),
  };
  const args = parseArgs(process.argv);
  if (args.out) {
    try {
      await fs.writeFile(args.out, JSON.stringify(fallback, null, 2), 'utf8');
    } catch {
      // ignore
    }
  }
  console.error(JSON.stringify(fallback, null, 2));
  process.exit(1);
});
