#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { request } from 'playwright';

const PHASE_TIMING_KEYS = [
  'snapshot_load_ms',
  'quote_load_ms',
  'map_filter_ms',
  'advanced_external_ms',
  'sort_page_ms',
  'map_build_ms',
  'total_ms',
];

function parseArgs(argv) {
  const out = {
    baseUrl: 'https://taofinancialengine.com',
    username: '',
    password: '',
    outDir: '',
    timeoutMs: 45000,
    attempts: 5,
    delayMs: 200,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    if (next && !next.startsWith('--')) {
      out[key] = next;
      i += 1;
    } else {
      out[key] = 'true';
    }
  }

  out.timeoutMs = Number(out.timeoutMs || 45000);
  out.attempts = Number(out.attempts || 5);
  out.delayMs = Number(out.delayMs || 200);
  if (!Number.isFinite(out.timeoutMs) || out.timeoutMs < 1000) out.timeoutMs = 45000;
  if (!Number.isFinite(out.attempts) || out.attempts < 1) out.attempts = 5;
  if (!Number.isFinite(out.delayMs) || out.delayMs < 0) out.delayMs = 200;
  return out;
}

function trimText(text, max = 1000) {
  const raw = String(text ?? '');
  if (raw.length <= max) return raw;
  return `${raw.slice(0, max)}...[truncated]`;
}

function percentile(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

function buildLatencySummary(values) {
  if (!values.length) {
    return {
      min_ms: null,
      max_ms: null,
      p50_ms: null,
      p95_ms: null,
      mean_ms: null,
    };
  }
  const sum = values.reduce((acc, value) => acc + value, 0);
  return {
    min_ms: Math.min(...values),
    max_ms: Math.max(...values),
    p50_ms: percentile(values, 50),
    p95_ms: percentile(values, 95),
    mean_ms: Number((sum / values.length).toFixed(2)),
  };
}

function buildPhaseLatencySummary(runs) {
  const out = {};
  for (const key of PHASE_TIMING_KEYS) {
    const values = runs
      .map((row) => Number(row?.phase_timings?.[key]))
      .filter((value) => Number.isFinite(value));
    out[key] = buildLatencySummary(values);
  }
  return out;
}

function analyzeScenarioRuns(runs) {
  const latencyValues = runs.filter((row) => row.ok && row.contract_ok).map((row) => row.elapsed_ms);
  const quoteCacheErrors = runs.filter((row) => row.quote_cache_error).length;
  const snapshotErrors = runs.filter((row) => row.snapshot_error).length;
  const httpFailures = runs.filter((row) => !row.ok).length;
  const contractFailures = runs.filter((row) => row.ok && !row.contract_ok).length;
  const diagnosticsFailures = runs.filter((row) => row.diagnostics_requested && !row.diagnostics_ok).length;
  const successCount = runs.filter((row) => row.ok && row.contract_ok).length;
  const successfulRuns = runs.filter((row) => row.ok && row.contract_ok);

  return {
    attempts: runs.length,
    success_count: successCount,
    http_failure_count: httpFailures,
    contract_failure_count: contractFailures,
    diagnostics_failure_count: diagnosticsFailures,
    quote_cache_error_count: quoteCacheErrors,
    snapshot_error_count: snapshotErrors,
    latency: buildLatencySummary(latencyValues),
    phase_latency: buildPhaseLatencySummary(successfulRuns),
    success_rate: runs.length > 0 ? Number((successCount / runs.length).toFixed(4)) : 0,
  };
}

function scenarioStatus(analysis) {
  if (analysis.quote_cache_error_count > 0) return 'fail';
  if (analysis.snapshot_error_count > 0) return 'fail';
  if (analysis.http_failure_count > 0) return 'fail';
  if (analysis.contract_failure_count > 0) return 'fail';
  if (analysis.diagnostics_failure_count > 0) return 'fail';
  if (analysis.success_count < analysis.attempts) return 'warn';
  return 'pass';
}

async function fetchScreener(context, url, timeoutMs) {
  const startedAt = Date.now();
  const diagnosticsRequested = url.includes('diagnostics=1');
  try {
    const response = await context.get(url, { timeout: timeoutMs });
    const elapsedMs = Date.now() - startedAt;
    const bodyText = await response.text();
    let payload = null;
    try {
      payload = JSON.parse(bodyText);
    } catch {
      payload = null;
    }

    const errorText = String(payload?.error ?? '');
    const totalRaw = payload?.total;
    const total = Number(totalRaw);
    const diagnosticsPayload = payload && typeof payload === 'object' ? payload.diagnostics : null;
    const diagnosticsTimings = diagnosticsPayload && typeof diagnosticsPayload === 'object' ? diagnosticsPayload.timings : null;
    const diagnosticsPhase =
      diagnosticsPayload && typeof diagnosticsPayload === 'object' && typeof diagnosticsPayload.phase === 'string'
        ? diagnosticsPayload.phase
        : null;
    const phaseTimings = {};
    for (const key of PHASE_TIMING_KEYS) {
      const value = Number(diagnosticsTimings?.[key]);
      phaseTimings[key] = Number.isFinite(value) && value >= 0 ? value : null;
    }
    const diagnosticsOk = !diagnosticsRequested || phaseTimings.total_ms !== null;
    const contractOk = Number.isFinite(total) && total >= 0 && diagnosticsOk;

    return {
      ok: response.ok(),
      status: response.status(),
      elapsed_ms: elapsedMs,
      contract_ok: contractOk,
      diagnostics_requested: diagnosticsRequested,
      diagnostics_ok: diagnosticsOk,
      diagnostics_phase: diagnosticsPhase,
      phase_timings: phaseTimings,
      total: contractOk ? total : null,
      error: errorText || null,
      quote_cache_error: errorText.toLowerCase().includes('quote cache is unavailable or empty'),
      snapshot_error: errorText.toLowerCase().includes('snapshot is unavailable or empty'),
      body_sample: trimText(bodyText),
    };
  } catch (error) {
    const elapsedMs = Date.now() - startedAt;
    return {
      ok: false,
      status: null,
      elapsed_ms: elapsedMs,
      contract_ok: false,
      diagnostics_requested: diagnosticsRequested,
      diagnostics_ok: false,
      diagnostics_phase: null,
      phase_timings: {},
      total: null,
      error: error instanceof Error ? error.message : String(error),
      quote_cache_error: false,
      snapshot_error: false,
      body_sample: null,
    };
  }
}

function nowIso() {
  return new Date().toISOString();
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.username || !args.password) throw new Error('Missing --username or --password');
  if (!args.outDir) throw new Error('Missing --outDir');

  await fs.mkdir(args.outDir, { recursive: true });

  const scenarios = [
    {
      id: 'technical_baseline',
      url: `${args.baseUrl}/api/screener?tab=technical&page=1&pageSize=50&sortKey=ticker&sortDir=asc&filterGroup=descriptive&diagnostics=1`,
      focus: 'TA',
    },
    {
      id: 'technical_filtered',
      url: `${args.baseUrl}/api/screener?tab=technical&page=1&pageSize=25&sortKey=ticker&sortDir=asc&filterGroup=descriptive&sector=technology&minPrice=100&diagnostics=1`,
      focus: 'TA',
    },
    {
      id: 'performance_baseline',
      url: `${args.baseUrl}/api/screener?tab=performance&page=1&pageSize=50&sortKey=ticker&sortDir=asc&filterGroup=descriptive&diagnostics=1`,
      focus: 'News',
    },
    {
      id: 'performance_filtered',
      url: `${args.baseUrl}/api/screener?tab=performance&page=1&pageSize=25&sortKey=ticker&sortDir=asc&filterGroup=descriptive&sector=technology&minPrice=100&diagnostics=1`,
      focus: 'News',
    },
    {
      id: 'overview_control',
      url: `${args.baseUrl}/api/screener?tab=overview&page=1&pageSize=50&sortKey=ticker&sortDir=asc&filterGroup=descriptive&diagnostics=1`,
      focus: 'Control',
    },
  ];

  const context = await request.newContext();

  const summary = {
    generated_at_utc: nowIso(),
    status: 'running',
    base_url: args.baseUrl,
    attempts_per_scenario: args.attempts,
    timeout_ms: args.timeoutMs,
    delay_ms: args.delayMs,
    scenarios: [],
    failures: [],
  };

  try {
    const signIn = await context.post(`${args.baseUrl}/api/auth/sign-in`, {
      data: {
        username: args.username,
        password: args.password,
        next: '/',
      },
      timeout: args.timeoutMs,
    });

    if (!signIn.ok()) {
      const body = await signIn.text();
      throw new Error(`Sign-in failed status=${signIn.status()} body=${trimText(body)}`);
    }

    const detailed = {
      generated_at_utc: nowIso(),
      status: 'running',
      scenario_runs: {},
    };

    for (const scenario of scenarios) {
      const runs = [];
      for (let i = 1; i <= args.attempts; i += 1) {
        const result = await fetchScreener(context, scenario.url, args.timeoutMs);
        runs.push({
          attempt: i,
          checked_at_utc: nowIso(),
          ...result,
        });
        if (i < args.attempts && args.delayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, args.delayMs));
        }
      }

      detailed.scenario_runs[scenario.id] = {
        focus: scenario.focus,
        url: scenario.url,
        runs,
      };

      const analysis = analyzeScenarioRuns(runs);
      const status = scenarioStatus(analysis);
      const scenarioSummary = {
        id: scenario.id,
        focus: scenario.focus,
        url: scenario.url,
        status,
        ...analysis,
      };
      summary.scenarios.push(scenarioSummary);

      if (status !== 'pass') {
        summary.failures.push({
          id: scenario.id,
          focus: scenario.focus,
          status,
          analysis,
        });
      }
    }

    const anyFail = summary.scenarios.some((scenario) => scenario.status === 'fail');
    summary.status = anyFail ? 'fail' : 'pass';

    detailed.status = summary.status;
    detailed.summary = summary;

    const detailsPath = path.join(args.outDir, 'details.json');
    const summaryPath = path.join(args.outDir, 'summary.json');
    await fs.writeFile(detailsPath, `${JSON.stringify(detailed, null, 2)}\n`, 'utf8');
    await fs.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');

    process.stdout.write(`${JSON.stringify({ status: summary.status, summary_path: summaryPath, details_path: detailsPath })}\n`);
    process.exitCode = summary.status === 'pass' ? 0 : 1;
  } finally {
    await context.dispose();
  }
}

run().catch(async (error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
