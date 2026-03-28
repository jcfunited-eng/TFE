#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const DEFAULT_MAX_AGE_HOURS = 30;
const DEFAULT_SCHEDULE_LOOKBACK_DAYS = 8;
const DEFAULT_API_CHECK_TIMEOUT_MS = 120000;
const VALIDATION_HISTORY_TABLE = "runtime_validation_reports";

function resolveWorkspaceRoot() {
  const configured = String(process.env.TFE_WORKSPACE_ROOT ?? "").trim();
  const candidates = [
    configured,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "../.."),
    "/workspaces/Tao_Financial_Engine",
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .map((value) => path.resolve(value));

  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "run_refresh_with_l5_learning.py"))) {
      return candidate;
    }
  }

  return path.resolve(process.cwd(), "..");
}

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function readPgPort() {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DB_PORT;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

function resolvePgSslRejectUnauthorized() {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

function resolvePool() {
  const host = readRequiredEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readPgPort();
  const rejectUnauthorized = resolvePgSslRejectUnauthorized();

  return new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 2,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-runtime-validation-gate",
  });
}

function toFiniteOrNull(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function readPositiveIntEnv(name, fallback) {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole <= 0) return fallback;
  return whole;
}

function isoNow() {
  return new Date().toISOString();
}

function readOptionalEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  return "";
}

function readBooleanEnv(name, fallback) {
  const raw = String(process.env[name] ?? "").trim().toLowerCase();
  if (!raw) return fallback;
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return fallback;
}

function readBoundedIntEnv(name, fallback, minimum, maximum) {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < minimum) return minimum;
  if (whole > maximum) return maximum;
  return whole;
}

async function runApiFilterValidation(root) {
  const strictRequired = readBooleanEnv("TFE_VALIDATION_REQUIRE_API_FILTER_CHECK", false);
  const baseUrl = readOptionalEnv("TFE_VALIDATION_BASE_URL", "TFE_BASE_URL", "TFE_WEB_BASE_URL");
  const username = readOptionalEnv("TFE_VALIDATION_USERNAME", "TFE_VALIDATION_USER", "TFE_LOGIN_USERNAME", "TFE_USERNAME");
  const password = readOptionalEnv("TFE_VALIDATION_PASSWORD", "TFE_LOGIN_PASSWORD", "TFE_PASSWORD");

  if (!baseUrl || !username || !password) {
    return {
      configured: false,
      strict_required: strictRequired,
      passed: !strictRequired,
      details: {
        base_url_present: Boolean(baseUrl),
        username_present: Boolean(username),
        password_present: Boolean(password),
        reason: "Missing API filter validation credentials/base URL.",
      },
    };
  }

  const outDir = path.join(root, "backups", "runtime");
  mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `validation-api-filter-${Date.now()}.json`);
  const timeoutMs = readBoundedIntEnv("TFE_VALIDATION_API_CHECK_TIMEOUT_MS", DEFAULT_API_CHECK_TIMEOUT_MS, 15000, 900000);

  const tabs = ["overview", "valuation", "financial", "ownership", "performance", "technical", "etf"];
  const summary = {
    generated_at_utc: isoNow(),
    base_url: baseUrl,
    status: "running",
    checks: [],
    failures: [],
  };

  async function fetchJson(url, init = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, { ...init, signal: controller.signal });
      let body = null;
      try {
        body = await res.json();
      } catch {
        body = null;
      }
      return { res, body };
    } finally {
      clearTimeout(timer);
    }
  }

  const signInPayload = { username, password, next: "/" };
  const signIn = await fetchJson(`${baseUrl}/api/auth/sign-in`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(signInPayload),
  });

  const setCookies = typeof signIn.res.headers.getSetCookie === "function" ? signIn.res.headers.getSetCookie() : [];
  const cookieHeader = setCookies
    .map((cookie) => String(cookie ?? "").split(";")[0].trim())
    .filter(Boolean)
    .join("; ");

  if (!signIn.res.ok || !signIn.body?.signedIn || !cookieHeader) {
    summary.status = "fail";
    summary.failures.push({
      type: "sign_in_failed",
      status: signIn.res.status,
      signed_in: Boolean(signIn.body?.signedIn),
      has_cookie: Boolean(cookieHeader),
    });
    writeFileSync(outPath, `${JSON.stringify(summary, null, 2)}\n`, "utf-8");
    return {
      configured: true,
      strict_required: strictRequired,
      passed: false,
      details: {
        out_path: outPath,
        summary,
      },
    };
  }

  for (const tab of tabs) {
    const baseParams = new URLSearchParams({
      tab,
      page: "1",
      pageSize: "50",
      sortKey: "ticker",
      sortDir: "asc",
    });
    const base = await fetchJson(`${baseUrl}/api/screener?${baseParams.toString()}`, {
      method: "GET",
      headers: { cookie: cookieHeader },
    });
    const baseRows = Array.isArray(base.body?.rows) ? base.body.rows : [];
    const baseTotal = Number(base.body?.total ?? baseRows.length ?? 0);
    const basePass = base.res.ok && Array.isArray(base.body?.rows);
    summary.checks.push({
      tab,
      type: "baseline",
      ok: basePass,
      status: base.res.status,
      total: baseTotal,
      row_count: baseRows.length,
    });
    if (!basePass) {
      summary.failures.push({ type: "baseline_failed", tab, status: base.res.status });
      continue;
    }

    const sectorParams = new URLSearchParams(baseParams);
    sectorParams.set("sector", "technology");
    const sector = await fetchJson(`${baseUrl}/api/screener?${sectorParams.toString()}`, {
      method: "GET",
      headers: { cookie: cookieHeader },
    });
    const sectorRows = Array.isArray(sector.body?.rows) ? sector.body.rows : [];
    const sectorTotal = Number(sector.body?.total ?? sectorRows.length ?? 0);
    const sectorPass = sector.res.ok && sectorTotal <= baseTotal;
    summary.checks.push({
      tab,
      type: "sector_filter",
      ok: sectorPass,
      status: sector.res.status,
      total: sectorTotal,
      row_count: sectorRows.length,
    });
    if (!sectorPass) {
      summary.failures.push({ type: "sector_filter_failed", tab, status: sector.res.status, sector_total: sectorTotal, base_total: baseTotal });
    }

    const minPriceParams = new URLSearchParams(sectorParams);
    minPriceParams.set("minPrice", "100");
    const minPrice = await fetchJson(`${baseUrl}/api/screener?${minPriceParams.toString()}`, {
      method: "GET",
      headers: { cookie: cookieHeader },
    });
    const minPriceRows = Array.isArray(minPrice.body?.rows) ? minPrice.body.rows : [];
    const minPriceTotal = Number(minPrice.body?.total ?? minPriceRows.length ?? 0);
    const minPriceRowsRespect = minPriceRows.every((row) => {
      const p = Number(row?.price);
      return Number.isFinite(p) && p >= 100;
    });
    const minPricePass = minPrice.res.ok && minPriceTotal <= sectorTotal && minPriceRowsRespect;
    summary.checks.push({
      tab,
      type: "min_price_filter",
      ok: minPricePass,
      status: minPrice.res.status,
      total: minPriceTotal,
      row_count: minPriceRows.length,
    });
    if (!minPricePass) {
      summary.failures.push({
        type: "min_price_filter_failed",
        tab,
        status: minPrice.res.status,
        min_price_total: minPriceTotal,
        sector_total: sectorTotal,
        rows_respect_threshold: minPriceRowsRespect,
      });
    }
  }

  summary.status = summary.failures.length === 0 ? "pass" : "fail";
  writeFileSync(outPath, `${JSON.stringify(summary, null, 2)}\n`, "utf-8");
  const payload = summary;
  const passed = payload.status === "pass";
  return {
    configured: true,
    strict_required: strictRequired,
    passed,
    details: {
      out_path: outPath,
      summary_status: payload.status,
      summary_failures: Array.isArray(payload.failures) ? payload.failures.length : null,
      summary: payload,
    },
  };
}

async function tableExists(client, tableName) {
  const result = await client.query(
    `
      SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = $1
      ) AS table_exists
    `,
    [tableName],
  );
  return Boolean(result.rows[0]?.table_exists);
}

function buildCheck(name, pass, details) {
  return { name, status: pass ? "pass" : "fail", details };
}

function buildTaAnchorValidExpression(columnName, anchorName) {
  return `${columnName} IS NULL OR (
    jsonb_typeof(metrics_json->'${anchorName}') = 'number'
    AND (metrics_json->>'${anchorName}')::double precision > 0
  )`;
}

function buildRsiValidExpression() {
  return "rsi14 IS NULL OR (rsi14 >= 0 AND rsi14 <= 100)";
}

function buildValidationGateRunId() {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "");
  const randomSuffix = Math.random().toString(16).slice(2, 10);
  return `validation-gate-${stamp}-${randomSuffix}`;
}

async function ensureValidationHistoryTable(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_validation_reports (
      validation_gate_run_id TEXT PRIMARY KEY,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      status TEXT NOT NULL,
      run_id TEXT,
      blocking_reason TEXT,
      checks_json JSONB NOT NULL,
      report_json JSONB NOT NULL,
      report_path TEXT NOT NULL,
      source TEXT NOT NULL DEFAULT 'run_validation_gate_v1',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_validation_reports_generated_at
    ON runtime_validation_reports (generated_at_utc DESC)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_validation_reports_run_id
    ON runtime_validation_reports (run_id)
  `);
}

async function insertValidationHistoryRow(client, payload) {
  const reportGeneratedAt = String(payload?.report?.generated_at_utc ?? "").trim() || isoNow();
  const checks = Array.isArray(payload?.report?.checks) ? payload.report.checks : [];
  await client.query(
    `
      INSERT INTO runtime_validation_reports (
        validation_gate_run_id,
        generated_at_utc,
        status,
        run_id,
        blocking_reason,
        checks_json,
        report_json,
        report_path,
        source
      )
      VALUES (
        $1,
        $2::timestamptz,
        $3,
        $4,
        $5,
        $6::jsonb,
        $7::jsonb,
        $8,
        'run_validation_gate_v1'
      )
    `,
    [
      payload.validation_gate_run_id,
      reportGeneratedAt,
      String(payload?.report?.status ?? "fail"),
      payload?.run_id ?? null,
      payload?.report?.blocking_reason ?? null,
      JSON.stringify(checks),
      JSON.stringify(payload?.report ?? {}),
      String(payload?.report_path ?? ""),
    ],
  );
}

async function updateValidationHistoryRow(client, payload) {
  const reportGeneratedAt = String(payload?.report?.generated_at_utc ?? "").trim() || isoNow();
  const checks = Array.isArray(payload?.report?.checks) ? payload.report.checks : [];
  await client.query(
    `
      UPDATE runtime_validation_reports
      SET generated_at_utc = $2::timestamptz,
          status = $3,
          run_id = $4,
          blocking_reason = $5,
          checks_json = $6::jsonb,
          report_json = $7::jsonb,
          report_path = $8
      WHERE validation_gate_run_id = $1
    `,
    [
      payload.validation_gate_run_id,
      reportGeneratedAt,
      String(payload?.report?.status ?? "fail"),
      payload?.run_id ?? null,
      payload?.report?.blocking_reason ?? null,
      JSON.stringify(checks),
      JSON.stringify(payload?.report ?? {}),
      String(payload?.report_path ?? ""),
    ],
  );
}

async function main() {
  const root = resolveWorkspaceRoot();
  const reportPath = path.join(root, "validation-report-v1.json");
  const requestedRunId = String(process.env.TFE_REFRESH_RUN_ID ?? "").trim() || null;

  const checks = [];
  let blockingReason = null;
  let latestRunId = null;
  let latestGeneratedAtUtc = null;
  const validationGateRunId = buildValidationGateRunId();

  const pool = resolvePool();
  const client = await pool.connect();

  try {
    await ensureValidationHistoryTable(client);

    const requiredTables = [
      "runtime_symbols",
      "runtime_decisions_latest",
      "runtime_metrics_latest",
      "runtime_bars_daily",
      "runtime_refresh_runs",
      VALIDATION_HISTORY_TABLE,
    ];

    let allTablesPresent = true;
    for (const tableName of requiredTables) {
      const exists = await tableExists(client, tableName);
      checks.push(buildCheck(`table_exists:${tableName}`, exists, { table: tableName }));
      if (!exists) allTablesPresent = false;
    }

    if (!allTablesPresent) {
      blockingReason = "required_runtime_tables_missing";
    }

    if (allTablesPresent) {
      const counts = await client.query(`
        SELECT
          (SELECT COUNT(*)::int FROM runtime_symbols) AS symbols_count,
          (SELECT COUNT(*)::int FROM runtime_decisions_latest) AS decisions_count,
          (SELECT COUNT(*)::int FROM runtime_metrics_latest) AS metrics_count,
          (SELECT COUNT(*)::int FROM runtime_bars_daily) AS bars_count
      `);
      const countRow = counts.rows[0] ?? {};
      const symbolsCount = Number(countRow.symbols_count ?? 0);
      const decisionsCount = Number(countRow.decisions_count ?? 0);
      const metricsCount = Number(countRow.metrics_count ?? 0);
      const barsCount = Number(countRow.bars_count ?? 0);

      const criticalNonEmpty = symbolsCount > 0 && decisionsCount > 0 && metricsCount > 0;
      checks.push(
        buildCheck("runtime_tables_non_empty", criticalNonEmpty, {
          symbols_count: symbolsCount,
          decisions_count: decisionsCount,
          metrics_count: metricsCount,
          bars_count: barsCount,
        }),
      );
      if (!criticalNonEmpty) {
        blockingReason = blockingReason ?? "runtime_tables_empty";
      }

      const joinMismatch = await client.query(`
        SELECT COUNT(*)::int AS missing_join_rows
        FROM runtime_decisions_latest d
        LEFT JOIN runtime_symbols s ON s.ticker = d.ticker
        LEFT JOIN runtime_metrics_latest m ON m.ticker = d.ticker
        WHERE s.ticker IS NULL OR m.ticker IS NULL
      `);
      const missingJoinRows = Number(joinMismatch.rows[0]?.missing_join_rows ?? 0);
      const joinPass = missingJoinRows === 0;
      checks.push(buildCheck("runtime_join_integrity", joinPass, { missing_join_rows: missingJoinRows }));
      if (!joinPass) {
        blockingReason = blockingReason ?? "runtime_join_integrity_failed";
      }

      const latestData = await client.query(`
        SELECT
          MAX(generated_at_utc) AS max_generated_at_utc,
          MIN(generated_at_utc) AS min_generated_at_utc
        FROM runtime_decisions_latest
      `);
      const maxGeneratedAtRaw = latestData.rows[0]?.max_generated_at_utc;
      latestGeneratedAtUtc = maxGeneratedAtRaw ? new Date(maxGeneratedAtRaw).toISOString() : null;
      const maxGeneratedTs = latestGeneratedAtUtc ? Date.parse(latestGeneratedAtUtc) : Number.NaN;
      const maxAgeHours = readPositiveIntEnv("TFE_VALIDATION_MAX_AGE_HOURS", DEFAULT_MAX_AGE_HOURS);
      const ageHours = Number.isFinite(maxGeneratedTs) ? (Date.now() - maxGeneratedTs) / 3_600_000 : Number.POSITIVE_INFINITY;
      const freshnessPass = Number.isFinite(ageHours) && ageHours <= maxAgeHours;
      checks.push(
        buildCheck("runtime_data_freshness", freshnessPass, {
          max_generated_at_utc: latestGeneratedAtUtc,
          age_hours: Number.isFinite(ageHours) ? Number(ageHours.toFixed(3)) : null,
          max_age_hours_allowed: maxAgeHours,
        }),
      );
      if (!freshnessPass) {
        blockingReason = blockingReason ?? "runtime_data_stale";
      }

      const decisionIntegrity = await client.query(`
        SELECT
          COUNT(*)::int AS total_rows,
          COUNT(*) FILTER (WHERE decision_label IN ('Accumulate', 'Hold', 'Avoid'))::int AS valid_decision_rows,
          COUNT(*) FILTER (
            WHERE snapshot_row_json ? 'ticker'
              AND snapshot_row_json ? 'bar_count'
              AND snapshot_row_json ? 'regime'
          )::int AS rows_with_required_snapshot_fields
        FROM runtime_decisions_latest
      `);
      const dRow = decisionIntegrity.rows[0] ?? {};
      const totalRows = Number(dRow.total_rows ?? 0);
      const validDecisionRows = Number(dRow.valid_decision_rows ?? 0);
      const rowsWithRequiredSnapshotFields = Number(dRow.rows_with_required_snapshot_fields ?? 0);
      const decisionPass = totalRows > 0 && validDecisionRows === totalRows && rowsWithRequiredSnapshotFields === totalRows;
      checks.push(
        buildCheck("decision_integrity", decisionPass, {
          total_rows: totalRows,
          valid_decision_rows: validDecisionRows,
          rows_with_required_snapshot_fields: rowsWithRequiredSnapshotFields,
        }),
      );
      if (!decisionPass) {
        blockingReason = blockingReason ?? "decision_integrity_failed";
      }

      const apiPayloadIntegrity = await client.query(`
        SELECT
          COUNT(*)::int AS total_rows,
          COUNT(*) FILTER (WHERE profile_json ? 'price')::int AS rows_with_price,
          COUNT(*) FILTER (WHERE profile_json ? 'marketCap')::int AS rows_with_market_cap,
          COUNT(*) FILTER (WHERE profile_json ? 'changePct')::int AS rows_with_change_pct
        FROM runtime_symbols
      `);
      const pRow = apiPayloadIntegrity.rows[0] ?? {};
      const payloadTotal = Number(pRow.total_rows ?? 0);
      const rowsWithPrice = Number(pRow.rows_with_price ?? 0);
      const rowsWithMarketCap = Number(pRow.rows_with_market_cap ?? 0);
      const rowsWithChangePct = Number(pRow.rows_with_change_pct ?? 0);
      const maxMissingPayloadFields = readBoundedIntEnv(
        "TFE_VALIDATION_MAX_MISSING_RUNTIME_PAYLOAD_FIELDS",
        6,
        0,
        100000,
      );
      const missingPrice = Math.max(0, payloadTotal - rowsWithPrice);
      const missingMarketCap = Math.max(0, payloadTotal - rowsWithMarketCap);
      const missingChangePct = Math.max(0, payloadTotal - rowsWithChangePct);
      const payloadPass =
        payloadTotal > 0 &&
        missingPrice <= maxMissingPayloadFields &&
        missingMarketCap <= maxMissingPayloadFields &&
        missingChangePct <= maxMissingPayloadFields;
      checks.push(
        buildCheck("api_integrity_runtime_payload", payloadPass, {
          total_rows: payloadTotal,
          rows_with_price: rowsWithPrice,
          rows_with_market_cap: rowsWithMarketCap,
          rows_with_change_pct: rowsWithChangePct,
          missing_price: missingPrice,
          missing_market_cap: missingMarketCap,
          missing_change_pct: missingChangePct,
          max_missing_runtime_payload_fields: maxMissingPayloadFields,
        }),
      );
      if (!payloadPass) {
        blockingReason = blockingReason ?? "api_integrity_runtime_payload_failed";
      }

      const sma20ValidExpr = buildTaAnchorValidExpression("sma20", "sma20Price");
      const sma50ValidExpr = buildTaAnchorValidExpression("sma50", "sma50Price");
      const sma200ValidExpr = buildTaAnchorValidExpression("sma200", "sma200Price");
      const rsiValidExpr = buildRsiValidExpression();
      const taSemantics = await client.query(`
        SELECT
          COUNT(*)::int AS total_rows,
          COUNT(*) FILTER (WHERE ${sma20ValidExpr})::int AS sma20_with_valid_anchor,
          COUNT(*) FILTER (WHERE ${sma50ValidExpr})::int AS sma50_with_valid_anchor,
          COUNT(*) FILTER (WHERE ${sma200ValidExpr})::int AS sma200_with_valid_anchor,
          COUNT(*) FILTER (WHERE ${rsiValidExpr})::int AS rsi14_within_range,
          COUNT(*) FILTER (
            WHERE NOT (${sma20ValidExpr})
               OR NOT (${sma50ValidExpr})
               OR NOT (${sma200ValidExpr})
               OR NOT (${rsiValidExpr})
          )::int AS flagged_rows
        FROM runtime_metrics_latest
      `);
      const taFlaggedSamples = await client.query(`
        SELECT
          ticker,
          NOT (${sma20ValidExpr}) AS invalid_sma20_anchor,
          NOT (${sma50ValidExpr}) AS invalid_sma50_anchor,
          NOT (${sma200ValidExpr}) AS invalid_sma200_anchor,
          NOT (${rsiValidExpr}) AS invalid_rsi14,
          sma20,
          sma50,
          sma200,
          rsi14,
          metrics_json->>'sma20Price' AS sma20_price_anchor,
          metrics_json->>'sma50Price' AS sma50_price_anchor,
          metrics_json->>'sma200Price' AS sma200_price_anchor
        FROM runtime_metrics_latest
        WHERE NOT (${sma20ValidExpr})
           OR NOT (${sma50ValidExpr})
           OR NOT (${sma200ValidExpr})
           OR NOT (${rsiValidExpr})
        ORDER BY ticker ASC
        LIMIT 25
      `);
      const tRow = taSemantics.rows[0] ?? {};
      const taTotal = Number(tRow.total_rows ?? 0);
      const sma20WithValidAnchor = Number(tRow.sma20_with_valid_anchor ?? 0);
      const sma50WithValidAnchor = Number(tRow.sma50_with_valid_anchor ?? 0);
      const sma200WithValidAnchor = Number(tRow.sma200_with_valid_anchor ?? 0);
      const rsi14WithinRange = Number(tRow.rsi14_within_range ?? 0);
      const flaggedTaRows = Number(tRow.flagged_rows ?? 0);
      const taSemanticsObservedPass =
        taTotal > 0 &&
        sma20WithValidAnchor === taTotal &&
        sma50WithValidAnchor === taTotal &&
        sma200WithValidAnchor === taTotal &&
        rsi14WithinRange === taTotal;
      const taSemanticsPass = taTotal > 0;
      checks.push(
        buildCheck("ta_semantics_integrity", taSemanticsPass, {
          total_rows: taTotal,
          sma20_with_valid_anchor: sma20WithValidAnchor,
          sma50_with_valid_anchor: sma50WithValidAnchor,
          sma200_with_valid_anchor: sma200WithValidAnchor,
          rsi14_within_range: rsi14WithinRange,
          flagged_rows: flaggedTaRows,
          flagged_rows_sample: taFlaggedSamples.rows,
          observed_status: taSemanticsObservedPass ? "pass" : "flagged",
          enforcement: "flag_only_non_blocking",
          ta_semantics_basis: "runtime_metrics_latest stores SMA drift percentages backed by positive raw SMA anchors in metrics_json",
        }),
      );

      const latestRun = await client.query(`
        SELECT
          run_id,
          mode,
          trigger_source,
          completed_at,
          report_status,
          optimizer_short_cycle,
          optimizer_target_met,
          epoch_library_status,
          epoch_library_confidence_schema
        FROM runtime_refresh_runs
        ORDER BY completed_at DESC NULLS LAST, updated_at DESC NULLS LAST
        LIMIT 1
      `);
      const latestRunRow = latestRun.rows[0] ?? null;
      let requestedRunRow = null;
      let requestedRunPass = false;

      if (requestedRunId) {
        const requestedRun = await client.query(
          `
            SELECT
              run_id,
              mode,
              trigger_source,
              completed_at,
              report_status,
              optimizer_short_cycle,
              optimizer_target_met,
              epoch_library_status,
              epoch_library_confidence_schema
            FROM runtime_refresh_runs
            WHERE run_id = $1
            LIMIT 1
          `,
          [requestedRunId],
        );
        requestedRunRow = requestedRun.rows[0] ?? null;
        requestedRunPass = requestedRun.rows.length > 0;
      }

      const runRow = requestedRunRow ?? latestRunRow;
      latestRunId = runRow?.run_id ? String(runRow.run_id) : latestRunId;
      const mode = String(runRow?.mode ?? "").trim().toLowerCase();
      const reportStatus = String(runRow?.report_status ?? "").trim().toLowerCase();
      const triggerSource = String(runRow?.trigger_source ?? "").trim().toLowerCase();
      const optimizerShortCycle = String(runRow?.optimizer_short_cycle ?? "").trim().toLowerCase();
      const isNoRowsTerminalPath =
        reportStatus === "no_rows_written" &&
        (
          optimizerShortCycle === "" ||
          optimizerShortCycle === "not_run" ||
          optimizerShortCycle === "skipped_targeted_no_rows" ||
          (
            optimizerShortCycle === "skipped_by_trigger_policy" &&
            (triggerSource === "manual" || triggerSource === "program" || triggerSource === "scheduled")
          )
        );
      const isTriggerPolicySkipPath =
        reportStatus === "ok" &&
        optimizerShortCycle === "skipped_by_trigger_policy" &&
        (triggerSource === "manual" || triggerSource === "program");
      const isL5SkipPath =
        reportStatus === "ok" &&
        (
          optimizerShortCycle === "skipped_by_skip_l5_learning" ||
          optimizerShortCycle === "skipped_targeted_no_l5"
        ) &&
        (triggerSource === "manual" || triggerSource === "program");
      const isScheduledSnapshotPath =
        reportStatus === "ok" &&
        triggerSource === "scheduled" &&
        (mode === "snapshot" || mode === "universe_snapshot" || mode === "targeted_pfsc") &&
        (
          optimizerShortCycle === "" ||
          optimizerShortCycle === "not_run" ||
          optimizerShortCycle === "skipped_by_trigger_policy"
        );
      const lifecycleOraclePass =
        Boolean(runRow) &&
        (
          (
            reportStatus === "ok" &&
            runRow.optimizer_target_met === true &&
            runRow.epoch_library_status === "ok" &&
            String(runRow.epoch_library_confidence_schema ?? "") === "v1"
          ) ||
          isNoRowsTerminalPath ||
          isTriggerPolicySkipPath ||
          isL5SkipPath ||
          isScheduledSnapshotPath
        );
      checks.push(
        buildCheck("pipeline_terminal_integrity", lifecycleOraclePass, {
          run_id: runRow?.run_id ?? null,
          trigger_source: runRow?.trigger_source ?? null,
          report_status: runRow?.report_status ?? null,
          optimizer_short_cycle: runRow?.optimizer_short_cycle ?? null,
          optimizer_target_met: runRow?.optimizer_target_met ?? null,
          epoch_library_status: runRow?.epoch_library_status ?? null,
          epoch_library_confidence_schema: runRow?.epoch_library_confidence_schema ?? null,
          no_rows_terminal_path: isNoRowsTerminalPath,
          trigger_policy_skip_path: isTriggerPolicySkipPath,
          l5_skip_path: isL5SkipPath,
          scheduled_snapshot_path: isScheduledSnapshotPath,
        }),
      );
      if (!lifecycleOraclePass) {
        blockingReason = blockingReason ?? "pipeline_terminal_integrity_failed";
      }

      const refreshLifecyclePass =
        Boolean(runRow) &&
        (runRow.completed_at !== null || reportStatus === "ok") &&
        ["ok", "error", "failed", "timeout", "no_rows_written"].includes(reportStatus);
      checks.push(
        buildCheck("refresh_lifecycle_integrity", refreshLifecyclePass, {
          run_id: runRow?.run_id ?? null,
          completed_at: runRow?.completed_at ?? null,
          report_status: runRow?.report_status ?? null,
        }),
      );
      if (!refreshLifecyclePass) {
        blockingReason = blockingReason ?? "refresh_lifecycle_integrity_failed";
      }

      if (requestedRunId) {
        checks.push(
          buildCheck("requested_run_present", requestedRunPass, {
            requested_run_id: requestedRunId,
            present: requestedRunPass,
          }),
        );
        if (!requestedRunPass) {
          blockingReason = blockingReason ?? "requested_run_missing_from_runtime_refresh_runs";
        }
      }

      const lookbackDays = readPositiveIntEnv("TFE_VALIDATION_SCHEDULE_LOOKBACK_DAYS", DEFAULT_SCHEDULE_LOOKBACK_DAYS);
      const scheduleRows = await client.query(
        `
          SELECT mode, completed_at
          FROM runtime_refresh_runs
          WHERE completed_at >= (NOW() - ($1::text || ' days')::interval)
          ORDER BY completed_at DESC
        `,
        [String(lookbackDays)],
      );

      let snapshotRuns = 0;
      let universeRuns = 0;
      for (const row of scheduleRows.rows) {
        const mode = String(row.mode ?? "").trim();
        if (mode === "snapshot") snapshotRuns += 1;
        if (mode === "universe_snapshot") universeRuns += 1;
      }

      const scheduleStrictRequired = readBooleanEnv("TFE_VALIDATION_REQUIRE_SCHEDULE_EVIDENCE", false);
      const scheduleObservedPass = snapshotRuns > 0 && universeRuns > 0;
      const schedulePass = scheduleStrictRequired ? scheduleObservedPass : true;
      checks.push(
        buildCheck("schedule_evidence", schedulePass, {
          strict_required: scheduleStrictRequired,
          observed_pass: scheduleObservedPass,
          lookback_days: lookbackDays,
          snapshot_runs: snapshotRuns,
          universe_snapshot_runs: universeRuns,
        }),
      );
      if (!schedulePass) {
        blockingReason = blockingReason ?? "schedule_evidence_missing";
      }

      const apiFilterValidation = await runApiFilterValidation(root);
      checks.push(buildCheck("ui_filter_behavior_integrity", apiFilterValidation.passed, apiFilterValidation.details));
      if (!apiFilterValidation.passed) {
        blockingReason = blockingReason ?? "ui_filter_behavior_integrity_failed";
      }
    }

    let passed = checks.every((check) => check.status === "pass");
    if (!passed && !blockingReason) {
      blockingReason = "at_least_one_check_failed";
    }

    const reportGeneratedAt = isoNow();
    const preHistoryReport = {
      status: passed ? "pass" : "fail",
      generated_at_utc: reportGeneratedAt,
      run_id: latestRunId,
      checks,
      blocking_reason: passed ? null : blockingReason,
      validation_history: {
        table: VALIDATION_HISTORY_TABLE,
        validation_gate_run_id: validationGateRunId,
        persisted: false,
        persisted_at_utc: null,
      },
    };

    let historyPersisted = false;
    let historyPersistError = null;
    try {
      await insertValidationHistoryRow(client, {
        validation_gate_run_id: validationGateRunId,
        report: preHistoryReport,
        run_id: latestRunId,
        report_path: reportPath,
      });
      historyPersisted = true;
    } catch (error) {
      historyPersistError = error instanceof Error ? error.message : "validation_history_insert_failed";
    }

    checks.push(
      buildCheck("validation_report_history_persisted", historyPersisted, {
        table: VALIDATION_HISTORY_TABLE,
        validation_gate_run_id: validationGateRunId,
        error: historyPersistError,
      }),
    );

    if (!historyPersisted) {
      blockingReason = blockingReason ?? "validation_report_history_persist_failed";
    }

    passed = checks.every((check) => check.status === "pass");
    if (!passed && !blockingReason) {
      blockingReason = "at_least_one_check_failed";
    }

    const report = {
      status: passed ? "pass" : "fail",
      generated_at_utc: isoNow(),
      run_id: latestRunId,
      checks,
      blocking_reason: passed ? null : blockingReason,
      validation_history: {
        table: VALIDATION_HISTORY_TABLE,
        validation_gate_run_id: validationGateRunId,
        persisted: historyPersisted,
        persisted_at_utc: historyPersisted ? isoNow() : null,
      },
    };

    writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf-8");

    if (historyPersisted) {
      await updateValidationHistoryRow(client, {
        validation_gate_run_id: validationGateRunId,
        report,
        run_id: latestRunId,
        report_path: reportPath,
      });
    }

    if (latestRunId) {
      await client.query(
        `
          UPDATE runtime_refresh_runs
          SET validation_status = $2,
              validation_report_path = $3,
              updated_at = NOW()
          WHERE run_id = $1
        `,
        [latestRunId, report.status, reportPath],
      );
    }

    process.stdout.write(`${JSON.stringify(report)}\n`);

    if (!passed) {
      process.exit(1);
    }
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  const root = resolveWorkspaceRoot();
  const reportPath = path.join(root, "validation-report-v1.json");
  const report = {
    status: "fail",
    generated_at_utc: isoNow(),
    run_id: null,
    checks: [],
    blocking_reason: error instanceof Error ? error.message : "validation_gate_unhandled_error",
    validation_history: {
      table: VALIDATION_HISTORY_TABLE,
      validation_gate_run_id: null,
      persisted: false,
      persisted_at_utc: null,
    },
  };
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
  process.stderr.write(`${report.blocking_reason}\n`);
  process.exit(1);
});
