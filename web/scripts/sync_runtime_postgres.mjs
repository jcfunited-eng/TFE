#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Pool } from "pg";
import {
  PROVENANCE_REQUIRED_NON_NULL_FIELDS,
  buildPersistedProvenanceRecord,
  loadPolicyRuntimeArtifact,
  minBarsForAccumulate,
} from "./runtime_decision_provenance.mjs";

const DEFAULT_DB_PORT = 5432;
const DEFAULT_MIN_BARS = 514;
const MODULE_FILE_PATH = fileURLToPath(import.meta.url);

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

function readBooleanEnv(name, defaultValue = false) {
  const raw = String(process.env[name] ?? "").trim().toLowerCase();
  if (!raw) return defaultValue;
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return defaultValue;
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
    application_name: "tfe-runtime-bridge-sync",
  });
}

function normalizeTicker(value) {
  return String(value ?? "").trim().toUpperCase();
}

function toFiniteOrNull(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function toIntOrNull(value) {
  const n = toFiniteOrNull(value);
  if (n === null) return null;
  return Math.trunc(n);
}

function toBooleanOrNull(value) {
  if (typeof value === "boolean") return value;
  if (value === 1 || value === "1" || value === "true") return true;
  if (value === 0 || value === "0" || value === "false") return false;
  return null;
}

function canonicalRefreshMode(value) {
  const raw = String(value ?? "").trim().toLowerCase();
  if (!raw) return "snapshot";
  if (raw === "snapshot" || raw === "targeted_pfsc" || raw === "targeted") return "snapshot";
  if (raw === "universe_snapshot" || raw === "full_universe" || raw === "full") return "universe_snapshot";
  return raw;
}

function firstPositiveNumber(...values) {
  for (const value of values) {
    const n = Number(value);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

function percentFromAnchor(price, anchor) {
  const p = toFiniteOrNull(price);
  const a = toFiniteOrNull(anchor);
  if (p === null || a === null || a <= 0) return null;
  return ((p - a) / a) * 100;
}

function normalizePositiveAnchor(value) {
  const n = toFiniteOrNull(value);
  if (n === null || n <= 0) return null;
  return n;
}

export function buildRuntimeQuote(quote, row) {
  const runtimeQuote = quote && typeof quote === "object" ? { ...quote } : {};
  if (!Object.prototype.hasOwnProperty.call(runtimeQuote, "price")) {
    runtimeQuote.price = toFiniteOrNull(row?.price);
  }
  if (!Object.prototype.hasOwnProperty.call(runtimeQuote, "marketCap")) {
    runtimeQuote.marketCap = toFiniteOrNull(row?.marketCap ?? row?.market_cap);
  }
  if (!Object.prototype.hasOwnProperty.call(runtimeQuote, "changePct")) {
    runtimeQuote.changePct = toFiniteOrNull(row?.changePct ?? row?.change_pct);
  }
  const livePrice = firstPositiveNumber(runtimeQuote.price, row?.price, runtimeQuote.prevClose, runtimeQuote.open);

  const sma20Price = normalizePositiveAnchor(runtimeQuote.sma20);
  const sma50Price = normalizePositiveAnchor(runtimeQuote.sma50);
  const sma200Price = normalizePositiveAnchor(runtimeQuote.sma200);

  runtimeQuote.sma20Price = sma20Price;
  runtimeQuote.sma50Price = sma50Price;
  runtimeQuote.sma200Price = sma200Price;

  runtimeQuote.sma20 = percentFromAnchor(livePrice, sma20Price);
  runtimeQuote.sma50 = percentFromAnchor(livePrice, sma50Price);
  runtimeQuote.sma200 = percentFromAnchor(livePrice, sma200Price);

  if (toFiniteOrNull(runtimeQuote.perfHalf) === null) {
    const perfHalfY = toFiniteOrNull(runtimeQuote.perfHalfY);
    if (perfHalfY !== null) runtimeQuote.perfHalf = perfHalfY;
  }
  if (toFiniteOrNull(runtimeQuote.perfYtd) === null) {
    const perfYtd = toFiniteOrNull(runtimeQuote.perfYTD);
    if (perfYtd !== null) runtimeQuote.perfYtd = perfYtd;
  }

  return runtimeQuote;
}

function normalizeSnapshotRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) return payload.rows;
  return [];
}

function normalizeQuoteRows(payload) {
  if (!payload || typeof payload !== "object") return {};

  if (Array.isArray(payload)) {
    const out = {};
    for (const row of payload) {
      if (!row || typeof row !== "object") continue;
      const ticker = normalizeTicker(row.ticker);
      const quote = row.quote;
      if (!ticker || !quote || typeof quote !== "object" || Array.isArray(quote)) continue;
      out[ticker] = quote;
    }
    return out;
  }

  const bag = payload;
  if (bag.rows && typeof bag.rows === "object") {
    return normalizeQuoteRows(bag.rows);
  }

  const out = {};
  for (const [key, value] of Object.entries(bag)) {
    const ticker = normalizeTicker(key);
    if (!ticker) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    out[ticker] = value;
  }
  return out;
}

function normalizeIsoOrNull(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function toTextOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function resolveSnapshotGeneratedAt(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  return normalizeIsoOrNull(payload.generated_at_utc);
}

export function resolvePublicationBundleMeta(snapshotPayload, quotePayload) {
  const snapshotPublicationId = toTextOrNull(snapshotPayload?.publication_id);
  const quotePublicationId = toTextOrNull(quotePayload?.publication_id);
  const quoteSourceSnapshotPublicationId = toTextOrNull(quotePayload?.source_snapshot_publication_id);
  const explicitBindingStatus = toTextOrNull(quotePayload?.publication_binding_status ?? quotePayload?.quote_binding_status);

  let quoteBindingStatus = explicitBindingStatus ? explicitBindingStatus.toLowerCase() : null;
  if (!quoteBindingStatus) {
    if (
      snapshotPublicationId &&
      quotePublicationId &&
      quoteSourceSnapshotPublicationId &&
      snapshotPublicationId === quotePublicationId &&
      snapshotPublicationId === quoteSourceSnapshotPublicationId
    ) {
      quoteBindingStatus = "aligned";
    } else if (quotePublicationId || quoteSourceSnapshotPublicationId || snapshotPublicationId) {
      quoteBindingStatus = "unbound";
    }
  }

  return {
    snapshotPublicationId,
    quotePublicationId,
    quoteBindingStatus,
  };
}

export function buildDeferredQuoteFallbackPayload(snapshotPayload) {
  const snapshotPublicationId = toTextOrNull(snapshotPayload?.publication_id);
  const snapshotGeneratedAtUtc = resolveSnapshotGeneratedAt(snapshotPayload);
  return {
    publication_id: snapshotPublicationId,
    source_snapshot_publication_id: snapshotPublicationId,
    publication_binding_status: snapshotPublicationId ? "aligned" : null,
    quote_binding_status: snapshotPublicationId ? "aligned" : null,
    generated_at_utc: snapshotGeneratedAtUtc,
    rows: {},
    quote_input_mode: "snapshot_deferred_fallback",
  };
}

export function resolveQuotePayloadInput({
  snapshotPayload,
  quotePayloadRaw,
  quotePath,
  allowDeferredQuoteFallback,
}) {
  if (quotePayloadRaw && typeof quotePayloadRaw === "object" && !Array.isArray(quotePayloadRaw)) {
    return {
      quotePayload: quotePayloadRaw,
      quoteInputMode: "quote_cache_file",
    };
  }
  if (allowDeferredQuoteFallback) {
    return {
      quotePayload: buildDeferredQuoteFallbackPayload(snapshotPayload),
      quoteInputMode: "snapshot_deferred_fallback",
    };
  }
  throw new Error(`Quote cache file not found: ${quotePath}`);
}

function resolveGeneratedAt(report, snapshotPayload, fallbackIso) {
  const snapshotGeneratedAtUtc = resolveSnapshotGeneratedAt(snapshotPayload);
  const reportGeneratedAtUtc = normalizeIsoOrNull(report?.generated_at_utc);
  const fallbackGeneratedAtUtc = normalizeIsoOrNull(fallbackIso) ?? new Date().toISOString();

  const snapshotGeneratedAtMs = snapshotGeneratedAtUtc ? Date.parse(snapshotGeneratedAtUtc) : Number.NaN;
  const reportGeneratedAtMs = reportGeneratedAtUtc ? Date.parse(reportGeneratedAtUtc) : Number.NaN;
  const timestampMismatch = Boolean(
    snapshotGeneratedAtUtc
      && reportGeneratedAtUtc
      && snapshotGeneratedAtUtc !== reportGeneratedAtUtc,
  );

  if (snapshotGeneratedAtUtc && reportGeneratedAtUtc) {
    if (Number.isFinite(reportGeneratedAtMs) && Number.isFinite(snapshotGeneratedAtMs) && reportGeneratedAtMs >= snapshotGeneratedAtMs) {
      return {
        generatedAtUtc: reportGeneratedAtUtc,
        generatedAtSource: "rebuild_report_newer_than_snapshot_payload",
        snapshotGeneratedAtUtc,
        reportGeneratedAtUtc,
        timestampMismatch,
      };
    }
    return {
      generatedAtUtc: snapshotGeneratedAtUtc,
      generatedAtSource: "snapshot_payload",
      snapshotGeneratedAtUtc,
      reportGeneratedAtUtc,
      timestampMismatch,
    };
  }

  if (snapshotGeneratedAtUtc) {
    return {
      generatedAtUtc: snapshotGeneratedAtUtc,
      generatedAtSource: "snapshot_payload",
      snapshotGeneratedAtUtc,
      reportGeneratedAtUtc,
      timestampMismatch,
    };
  }

  if (reportGeneratedAtUtc) {
    return {
      generatedAtUtc: reportGeneratedAtUtc,
      generatedAtSource: "rebuild_report",
      snapshotGeneratedAtUtc: null,
      reportGeneratedAtUtc,
      timestampMismatch: false,
    };
  }

  return {
    generatedAtUtc: fallbackGeneratedAtUtc,
    generatedAtSource: "fallback_now",
    snapshotGeneratedAtUtc: null,
    reportGeneratedAtUtc: null,
    timestampMismatch: false,
  };
}

function inferDecisionLabel(row) {
  const sUf = toFiniteOrNull(row?.S_UF);
  const rUf = toFiniteOrNull(row?.R_UF);
  if (sUf !== null && rUf !== null) {
    if (sUf >= 0.5 && rUf >= 0.5) return "Accumulate";
    if (sUf <= -0.5 && rUf <= -0.5) return "Avoid";
  }
  return "Hold";
}

function scoreSnapshotRowForDedupe(row, quote) {
  const barCount = toIntOrNull(row?.bar_count) ?? 0;
  const price = firstPositiveNumber(quote?.price, row?.price, quote?.prevClose, quote?.open) ?? 0;
  const stability = toFiniteOrNull(row?.stability_score) ?? -9_999;

  return {
    barCount,
    price,
    stability,
  };
}

function shouldReplaceSnapshotRow(current, candidate, quoteRows) {
  const currentQuote = quoteRows[normalizeTicker(current?.ticker)] ?? {};
  const candidateQuote = quoteRows[normalizeTicker(candidate?.ticker)] ?? {};
  const left = scoreSnapshotRowForDedupe(current, currentQuote);
  const right = scoreSnapshotRowForDedupe(candidate, candidateQuote);

  if (right.barCount !== left.barCount) return right.barCount > left.barCount;
  if (right.price !== left.price) return right.price > left.price;
  if (right.stability !== left.stability) return right.stability > left.stability;
  return false;
}

function dedupeSnapshotRows(rows, quoteRows) {
  const byTicker = new Map();
  let duplicateRowsDropped = 0;

  for (const raw of rows) {
    if (!raw || typeof raw !== "object") continue;
    const ticker = normalizeTicker(raw.ticker);
    if (!ticker) continue;

    const candidate = { ...raw, ticker };
    const current = byTicker.get(ticker);
    if (!current) {
      byTicker.set(ticker, candidate);
      continue;
    }

    duplicateRowsDropped += 1;
    if (shouldReplaceSnapshotRow(current, candidate, quoteRows)) {
      byTicker.set(ticker, candidate);
    }
  }

  return {
    rows: Array.from(byTicker.values()),
    duplicateTickers: rows.length - byTicker.size > 0 ? rows.length - byTicker.size : 0,
    duplicateRowsDropped,
  };
}

async function ensureRuntimeTables(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_symbols (
      ticker TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      asset_type TEXT,
      quote_type TEXT,
      exchange TEXT,
      company_name TEXT,
      sector TEXT,
      industry TEXT,
      country TEXT,
      market_cap DOUBLE PRECISION,
      shares_outstanding DOUBLE PRECISION,
      float_shares DOUBLE PRECISION,
      profile_json JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_decisions_latest (
      ticker TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      snapshot_row_json JSONB NOT NULL,
      decision_label TEXT,
      reason_code TEXT,
      reason_text TEXT,
      bar_count INTEGER,
      min_bars_for_accumulate INTEGER,
      regime TEXT,
      stability_score DOUBLE PRECISION,
      max_dd DOUBLE PRECISION,
      policy_source_path TEXT,
      policy_generated_at_utc TEXT,
      policy_cell_key_requested TEXT,
      policy_cell_key_matched TEXT,
      policy_scoring_mode TEXT,
      fallback_used BOOLEAN,
      fallback_reason TEXT,
      anomaly_flagged BOOLEAN,
      structural_complete BOOLEAN,
      structural_missing_fields_json JSONB NOT NULL DEFAULT '[]'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_decisions_history (
      run_id TEXT NOT NULL,
      ticker TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      snapshot_row_json JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (run_id, ticker)
    )
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decisions_history_generated_at
    ON runtime_decisions_history (generated_at_utc DESC)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decisions_history_run_id
    ON runtime_decisions_history (run_id)
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_decision_provenance_latest (
      run_id TEXT NOT NULL,
      ticker TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      snapshot_timestamp_utc TIMESTAMPTZ,
      runtime_sync_completed_utc TIMESTAMPTZ,
      decision_timestamp_utc TIMESTAMPTZ NOT NULL,
      snapshot_row_digest_sha256 TEXT NOT NULL,
      policy_artifact_id TEXT NOT NULL,
      policy_artifact_hash_sha256 TEXT NOT NULL,
      policy_source_mode TEXT NOT NULL,
      candidate_key_chain_json JSONB NOT NULL DEFAULT '[]'::jsonb,
      matched_key TEXT,
      match_level TEXT NOT NULL,
      fallback_ladder_level TEXT NOT NULL,
      matched_exact_bool BOOLEAN NOT NULL DEFAULT FALSE,
      fallback_used BOOLEAN NOT NULL DEFAULT TRUE,
      fallback_reason_code TEXT,
      decision TEXT NOT NULL,
      decision_reason_code TEXT NOT NULL,
      anomaly_flags_used_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      structural_recency_components_used_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      epoch_components_used_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      coverage_class TEXT NOT NULL,
      provenance_schema_version TEXT NOT NULL,
      writer_component TEXT NOT NULL,
      writer_build_hash TEXT NOT NULL,
      cp_profile TEXT NOT NULL,
      provenance_generated_utc TIMESTAMPTZ NOT NULL,
      provenance_valid BOOLEAN NOT NULL DEFAULT TRUE,
      provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (run_id, ticker)
    )
  `);
  await client.query(`
    ALTER TABLE runtime_decision_provenance_latest
      ADD COLUMN IF NOT EXISTS snapshot_timestamp_utc TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS runtime_sync_completed_utc TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS provenance_schema_version TEXT,
      ADD COLUMN IF NOT EXISTS writer_component TEXT,
      ADD COLUMN IF NOT EXISTS writer_build_hash TEXT,
      ADD COLUMN IF NOT EXISTS cp_profile TEXT,
      ADD COLUMN IF NOT EXISTS provenance_generated_utc TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS fallback_ladder_level TEXT
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_ticker
    ON runtime_decision_provenance_latest (ticker)
  `);
  await client.query(`
    CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_run_ticker_unique
    ON runtime_decision_provenance_latest (run_id, ticker)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_run_id
    ON runtime_decision_provenance_latest (run_id)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_policy_hash
    ON runtime_decision_provenance_latest (policy_artifact_hash_sha256)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_match_level
    ON runtime_decision_provenance_latest (match_level)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_exact_fallback
    ON runtime_decision_provenance_latest (matched_exact_bool, fallback_used)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_decision_provenance_latest_generated_at
    ON runtime_decision_provenance_latest (generated_at_utc DESC)
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_metrics_latest (
      ticker TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      atr14 DOUBLE PRECISION,
      rsi14 DOUBLE PRECISION,
      sma20 DOUBLE PRECISION,
      sma50 DOUBLE PRECISION,
      sma200 DOUBLE PRECISION,
      change_pct DOUBLE PRECISION,
      change_amount DOUBLE PRECISION,
      gap_pct DOUBLE PRECISION,
      rel_volume DOUBLE PRECISION,
      avg_volume DOUBLE PRECISION,
      volume DOUBLE PRECISION,
      perf_week DOUBLE PRECISION,
      perf_month DOUBLE PRECISION,
      perf_quarter DOUBLE PRECISION,
      perf_half DOUBLE PRECISION,
      perf_ytd DOUBLE PRECISION,
      perf_year DOUBLE PRECISION,
      metrics_json JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_symbols_history (
      run_id TEXT NOT NULL,
      ticker TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      asset_type TEXT,
      quote_type TEXT,
      exchange TEXT,
      company_name TEXT,
      sector TEXT,
      industry TEXT,
      country TEXT,
      market_cap DOUBLE PRECISION,
      shares_outstanding DOUBLE PRECISION,
      float_shares DOUBLE PRECISION,
      profile_json JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (run_id, ticker)
    )
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_symbols_history_generated_at
    ON runtime_symbols_history (generated_at_utc DESC)
  `);
  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_symbols_history_run_id
    ON runtime_symbols_history (run_id)
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS runtime_bars_daily (
      ticker TEXT NOT NULL,
      bar_date DATE NOT NULL,
      run_id TEXT NOT NULL,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      open DOUBLE PRECISION,
      high DOUBLE PRECISION,
      low DOUBLE PRECISION,
      close DOUBLE PRECISION,
      volume DOUBLE PRECISION,
      source TEXT NOT NULL,
      PRIMARY KEY (ticker, bar_date)
    )
  `);

  await client.query(`
      CREATE TABLE IF NOT EXISTS runtime_refresh_runs (
        run_id TEXT PRIMARY KEY,
        mode TEXT,
        trigger_source TEXT,
        requested_by TEXT,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      report_generated_at_utc TIMESTAMPTZ,
      rows_written INTEGER,
      report_status TEXT,
      optimizer_short_cycle TEXT,
      optimizer_cycle_requested_runs INTEGER,
      optimizer_cycle_completed_runs INTEGER,
      optimizer_session_id TEXT,
      optimizer_target_return_lift_pct DOUBLE PRECISION,
      optimizer_best_score DOUBLE PRECISION,
      optimizer_target_met BOOLEAN,
      epoch_library_confidence_schema TEXT,
        epoch_library_status TEXT,
        validation_status TEXT,
        validation_report_path TEXT,
        is_active_publication BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    await client.query(`
      ALTER TABLE runtime_refresh_runs
      ADD COLUMN IF NOT EXISTS bundle_generated_at_utc TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS snapshot_publication_id TEXT,
      ADD COLUMN IF NOT EXISTS quote_publication_id TEXT,
      ADD COLUMN IF NOT EXISTS quote_binding_status TEXT,
      ADD COLUMN IF NOT EXISTS activation_state TEXT,
      ADD COLUMN IF NOT EXISTS serving_state TEXT,
      ADD COLUMN IF NOT EXISTS blocking_reason_code TEXT,
      ADD COLUMN IF NOT EXISTS blocking_reason_detail TEXT,
      ADD COLUMN IF NOT EXISTS failure_code TEXT,
      ADD COLUMN IF NOT EXISTS failure_detail TEXT,
      ADD COLUMN IF NOT EXISTS current_phase TEXT,
      ADD COLUMN IF NOT EXISTS current_phase_process_status TEXT,
      ADD COLUMN IF NOT EXISTS current_phase_started_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS current_phase_completed_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS current_phase_last_heartbeat_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS current_phase_failure_code TEXT,
      ADD COLUMN IF NOT EXISTS current_phase_failure_detail TEXT,
      ADD COLUMN IF NOT EXISTS is_active_publication BOOLEAN NOT NULL DEFAULT FALSE
    `);
    await client.query(`
      CREATE TABLE IF NOT EXISTS runtime_refresh_run_phases (
        run_id TEXT NOT NULL REFERENCES runtime_refresh_runs(run_id) ON DELETE CASCADE,
        phase_name TEXT NOT NULL,
        input_contract JSONB,
        process_status TEXT NOT NULL,
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        output_contract JSONB,
        failure_code TEXT,
        failure_detail TEXT,
        last_heartbeat_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (run_id, phase_name)
      )
    `);
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_run_id
      ON runtime_refresh_run_phases (run_id)
    `);
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_running
      ON runtime_refresh_run_phases (run_id, process_status, last_heartbeat_at DESC)
    `);
    await client.query(`
      CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_refresh_runs_single_active_publication
      ON runtime_refresh_runs ((1))
      WHERE is_active_publication IS TRUE
    `);

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

function initializeProvenanceStats() {
  const nullCounts = {};
  for (const field of PROVENANCE_REQUIRED_NON_NULL_FIELDS) {
    nullCounts[field] = 0;
  }
  return {
    rows_attempted: 0,
    rows_written: 0,
    invalid_rows: 0,
    null_counts: nullCounts,
  };
}

function updateProvenanceStats(stats, record) {
  stats.rows_attempted += 1;
  stats.rows_written += 1;
  if (!record.provenance_valid) {
    stats.invalid_rows += 1;
  }

  for (const field of PROVENANCE_REQUIRED_NON_NULL_FIELDS) {
    const value = record[field];
    const isNullish =
      value === null ||
      value === undefined ||
      (typeof value === "string" && !value.trim()) ||
      (Array.isArray(value) && value.length === 0 && field === "candidate_key_chain_json");
    if (isNullish) {
      stats.null_counts[field] += 1;
    }
  }
}

function buildProvenanceArtifact(stats, runId, extras = {}) {
  const rows = Math.max(0, stats.rows_written);
  const fieldCount = PROVENANCE_REQUIRED_NON_NULL_FIELDS.length;

  let totalNulls = 0;
  const nullRateByField = {};
  for (const field of PROVENANCE_REQUIRED_NON_NULL_FIELDS) {
    const nullCount = Number(stats.null_counts[field] ?? 0);
    totalNulls += nullCount;
    nullRateByField[field] = rows > 0 ? Number((nullCount / rows).toFixed(6)) : null;
  }

  const denominator = rows * fieldCount;
  const completenessRate = denominator > 0 ? Number(((denominator - totalNulls) / denominator).toFixed(6)) : 0;

  return {
    analysis_name: "A3_phase1_provenance_persistence_write_only",
    generated_at_utc: new Date().toISOString(),
    run_id: runId,
    status: "ok",
    rows_attempted: stats.rows_attempted,
    rows_written: stats.rows_written,
    invalid_rows: stats.invalid_rows,
    required_non_null_fields: PROVENANCE_REQUIRED_NON_NULL_FIELDS,
    null_counts: stats.null_counts,
    null_rate_by_field: nullRateByField,
    completeness_rate: completenessRate,
    runtime_decision_row_count: toIntOrNull(extras.runtime_decision_row_count) ?? rows,
    provenance_row_count: toIntOrNull(extras.provenance_row_count) ?? rows,
    latest_provenance_generated_utc: extras.latest_provenance_generated_utc ?? null,
    writer_build_hash: extras.writer_build_hash ?? null,
    cp_profile: extras.cp_profile ?? null,
  };
}

async function main() {
  const root = resolveWorkspaceRoot();
  const nowIso = new Date().toISOString();
  const runId = String(process.env.TFE_REFRESH_RUN_ID ?? `manual-${nowIso}`).trim();
  const mode = canonicalRefreshMode(process.env.TFE_REFRESH_REQUESTED_MODE ?? "snapshot");
  const allowDeferredQuoteFallback = readBooleanEnv("TFE_ALLOW_DEFERRED_QUOTE_CACHE_FALLBACK", false);
  const triggerSource = String(process.env.TFE_REFRESH_TRIGGER_SOURCE ?? "program").trim() || "program";
  const requestedBy = String(process.env.TFE_REFRESH_REQUESTED_BY ?? "system").trim() || "system";
  const startedAt = String(process.env.TFE_REFRESH_STARTED_AT ?? nowIso).trim() || nowIso;
  const completedAt = String(process.env.TFE_REFRESH_COMPLETED_AT ?? nowIso).trim() || nowIso;

  const reportPath = path.join(root, "uf_snapshot_rebuild_report.json");
  const snapshotPath = path.join(root, "uf_snapshot.json");
  const quotePath = path.join(root, "web", "data", "screener-quote-cache.json");

  if (!existsSync(snapshotPath)) {
    throw new Error(`Snapshot file not found: ${snapshotPath}`);
  }

  const snapshotText = readFileSync(snapshotPath, "utf-8")
    .replace(/\bNaN\b/g, "null")
    .replace(/\b-Infinity\b/g, "null")
    .replace(/\bInfinity\b/g, "null");
  const snapshotRowsRaw = JSON.parse(snapshotText);
  const report = existsSync(reportPath) ? JSON.parse(readFileSync(reportPath, "utf-8")) : {};
  const timestampResolution = resolveGeneratedAt(report, snapshotRowsRaw, nowIso);
  const generatedAtUtc = timestampResolution.generatedAtUtc;
  const barDate = generatedAtUtc.slice(0, 10);
  const snapshotRowsInput = normalizeSnapshotRows(snapshotRowsRaw);
  const quoteFileExists = existsSync(quotePath);
  const quotePayloadRaw = quoteFileExists ? JSON.parse(readFileSync(quotePath, "utf-8")) : null;
  const quoteInput = resolveQuotePayloadInput({
    snapshotPayload: snapshotRowsRaw,
    quotePayloadRaw,
    quotePath,
    allowDeferredQuoteFallback,
  });
  const quoteRowsRaw = quoteInput.quotePayload;
  const quoteRows = normalizeQuoteRows(quoteRowsRaw);
  const publicationBundleMeta = resolvePublicationBundleMeta(snapshotRowsRaw, quoteRowsRaw);

  if (snapshotRowsInput.length === 0) {
    throw new Error("Snapshot row set is empty; refusing runtime sync.");
  }

  const dedupe = dedupeSnapshotRows(snapshotRowsInput, quoteRows);
  const snapshotRows = dedupe.rows;

  if (snapshotRows.length === 0) {
    throw new Error("Snapshot row set is empty after dedupe; refusing runtime sync.");
  }

  const policyRuntime = loadPolicyRuntimeArtifact(root);
  const provenanceMinBars = minBarsForAccumulate();

  const pool = resolvePool();
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await ensureRuntimeTables(client);

    await client.query("DELETE FROM runtime_decisions_latest");
    await client.query("DELETE FROM runtime_symbols");
    await client.query("DELETE FROM runtime_metrics_latest");
    await client.query("DELETE FROM runtime_bars_daily");

    let decisionsInserted = 0;
    let decisionsHistoryInserted = 0;
    let provenanceInserted = 0;
    let symbolsInserted = 0;
    let symbolsHistoryInserted = 0;
    let metricsInserted = 0;
    let barsInserted = 0;
    const provenanceStats = initializeProvenanceStats();
    const provenanceArtifactPath = path.join(root, "current_l5_provenance_persistence_latest.json");

    for (const row of snapshotRows) {
      const ticker = normalizeTicker(row.ticker);
      if (!ticker) continue;

      const snapshotRow = { ...row, ticker };
      const quoteBase = quoteRows[ticker] && typeof quoteRows[ticker] === "object" ? quoteRows[ticker] : {};
      const quote = buildRuntimeQuote(quoteBase, row);
      const persistedProvenance = buildPersistedProvenanceRecord({
        row: snapshotRow,
        ticker,
        runId,
        generatedAtUtc,
        snapshotTimestampUtc: generatedAtUtc,
        runtimeSyncCompletedUtc: completedAt,
        policyRuntime,
        minBars: provenanceMinBars,
        writerBuildHash: process.env.TFE_PROVENANCE_WRITER_BUILD_HASH ?? null,
      });
      updateProvenanceStats(provenanceStats, persistedProvenance);

      await client.query(
        `
          INSERT INTO runtime_decisions_latest (
            ticker, run_id, generated_at_utc, snapshot_row_json,
            decision_label, reason_code, reason_text,
            bar_count, min_bars_for_accumulate, regime, stability_score, max_dd,
            policy_source_path, policy_generated_at_utc, policy_cell_key_requested, policy_cell_key_matched,
            policy_scoring_mode, fallback_used, fallback_reason, anomaly_flagged, structural_complete, structural_missing_fields_json,
            updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4::jsonb,
            $5, NULL, NULL,
            $6, $7, $8, $9, $10,
            NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, '[]'::jsonb,
            NOW()
          )
          ON CONFLICT (ticker)
          DO UPDATE SET
            run_id = EXCLUDED.run_id,
            generated_at_utc = EXCLUDED.generated_at_utc,
            snapshot_row_json = EXCLUDED.snapshot_row_json,
            decision_label = EXCLUDED.decision_label,
            bar_count = EXCLUDED.bar_count,
            min_bars_for_accumulate = EXCLUDED.min_bars_for_accumulate,
            regime = EXCLUDED.regime,
            stability_score = EXCLUDED.stability_score,
            max_dd = EXCLUDED.max_dd,
            updated_at = NOW()
        `,
        [
          ticker,
          runId,
          generatedAtUtc,
          JSON.stringify(snapshotRow),
          inferDecisionLabel(row),
          toIntOrNull(row.bar_count),
          DEFAULT_MIN_BARS,
          String(row.regime ?? "UNKNOWN"),
          toFiniteOrNull(row.stability_score),
          toFiniteOrNull(row.max_dd),
        ],
      );
      decisionsInserted += 1;

      await client.query(
        `
          INSERT INTO runtime_decisions_history (
            run_id, ticker, generated_at_utc, snapshot_row_json, updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4::jsonb, NOW()
          )
          ON CONFLICT (run_id, ticker)
          DO UPDATE SET
            generated_at_utc = EXCLUDED.generated_at_utc,
            snapshot_row_json = EXCLUDED.snapshot_row_json,
            updated_at = NOW()
        `,
        [
          runId,
          ticker,
          generatedAtUtc,
          JSON.stringify(snapshotRow),
        ],
      );
      decisionsHistoryInserted += 1;

      await client.query(
        `
          INSERT INTO runtime_decision_provenance_latest (
            run_id, ticker, generated_at_utc, snapshot_timestamp_utc, runtime_sync_completed_utc, decision_timestamp_utc, snapshot_row_digest_sha256,
            policy_artifact_id, policy_artifact_hash_sha256, policy_source_mode,
            candidate_key_chain_json, matched_key, match_level, fallback_ladder_level, matched_exact_bool,
            fallback_used, fallback_reason_code, decision, decision_reason_code,
            anomaly_flags_used_json, structural_recency_components_used_json, epoch_components_used_json,
            coverage_class,
            provenance_schema_version, writer_component, writer_build_hash, cp_profile, provenance_generated_utc,
            provenance_valid, provenance_json, updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4::timestamptz, $5::timestamptz, $6::timestamptz, $7,
            $8, $9, $10,
            $11::jsonb, $12, $13, $14, $15,
            $16, $17, $18, $19,
            $20::jsonb, $21::jsonb, $22::jsonb,
            $23,
            $24, $25, $26, $27, $28::timestamptz,
            $29, $30::jsonb, NOW()
          )
          ON CONFLICT (run_id, ticker)
          DO UPDATE SET
            generated_at_utc = EXCLUDED.generated_at_utc,
            snapshot_timestamp_utc = EXCLUDED.snapshot_timestamp_utc,
            runtime_sync_completed_utc = EXCLUDED.runtime_sync_completed_utc,
            decision_timestamp_utc = EXCLUDED.decision_timestamp_utc,
            snapshot_row_digest_sha256 = EXCLUDED.snapshot_row_digest_sha256,
            policy_artifact_id = EXCLUDED.policy_artifact_id,
            policy_artifact_hash_sha256 = EXCLUDED.policy_artifact_hash_sha256,
            policy_source_mode = EXCLUDED.policy_source_mode,
            candidate_key_chain_json = EXCLUDED.candidate_key_chain_json,
            matched_key = EXCLUDED.matched_key,
            match_level = EXCLUDED.match_level,
            fallback_ladder_level = EXCLUDED.fallback_ladder_level,
            matched_exact_bool = EXCLUDED.matched_exact_bool,
            fallback_used = EXCLUDED.fallback_used,
            fallback_reason_code = EXCLUDED.fallback_reason_code,
            decision = EXCLUDED.decision,
            decision_reason_code = EXCLUDED.decision_reason_code,
            anomaly_flags_used_json = EXCLUDED.anomaly_flags_used_json,
            structural_recency_components_used_json = EXCLUDED.structural_recency_components_used_json,
            epoch_components_used_json = EXCLUDED.epoch_components_used_json,
            coverage_class = EXCLUDED.coverage_class,
            provenance_schema_version = EXCLUDED.provenance_schema_version,
            writer_component = EXCLUDED.writer_component,
            writer_build_hash = EXCLUDED.writer_build_hash,
            cp_profile = EXCLUDED.cp_profile,
            provenance_generated_utc = EXCLUDED.provenance_generated_utc,
            provenance_valid = EXCLUDED.provenance_valid,
            provenance_json = EXCLUDED.provenance_json,
            updated_at = NOW()
        `,
        [
          runId,
          ticker,
          generatedAtUtc,
          persistedProvenance.snapshot_timestamp_utc,
          persistedProvenance.runtime_sync_completed_utc,
          persistedProvenance.decision_timestamp_utc,
          persistedProvenance.snapshot_row_digest_sha256,
          persistedProvenance.policy_artifact_id,
          persistedProvenance.policy_artifact_hash_sha256,
          persistedProvenance.policy_source_mode,
          JSON.stringify(persistedProvenance.candidate_key_chain_json),
          persistedProvenance.matched_key,
          persistedProvenance.match_level,
          persistedProvenance.fallback_ladder_level,
          persistedProvenance.matched_exact_bool,
          persistedProvenance.fallback_used,
          persistedProvenance.fallback_reason_code,
          persistedProvenance.decision,
          persistedProvenance.decision_reason_code,
          JSON.stringify(persistedProvenance.anomaly_flags_used_json),
          JSON.stringify(persistedProvenance.structural_recency_components_used_json),
          JSON.stringify(persistedProvenance.epoch_components_used_json),
          persistedProvenance.coverage_class,
          persistedProvenance.provenance_schema_version,
          persistedProvenance.writer_component,
          persistedProvenance.writer_build_hash,
          persistedProvenance.cp_profile,
          persistedProvenance.provenance_generated_utc,
          persistedProvenance.provenance_valid,
          JSON.stringify(persistedProvenance.provenance_json),
        ],
      );
      provenanceInserted += 1;

      await client.query(
        `
          INSERT INTO runtime_symbols (
            ticker, run_id, generated_at_utc, asset_type, quote_type, exchange, company_name,
            sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json, updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4, $5, $6, $7,
            $8, $9, $10, $11, $12, $13, $14::jsonb, NOW()
          )
          ON CONFLICT (ticker)
          DO UPDATE SET
            run_id = EXCLUDED.run_id,
            generated_at_utc = EXCLUDED.generated_at_utc,
            asset_type = EXCLUDED.asset_type,
            quote_type = EXCLUDED.quote_type,
            exchange = EXCLUDED.exchange,
            company_name = EXCLUDED.company_name,
            sector = EXCLUDED.sector,
            industry = EXCLUDED.industry,
            country = EXCLUDED.country,
            market_cap = EXCLUDED.market_cap,
            shares_outstanding = EXCLUDED.shares_outstanding,
            float_shares = EXCLUDED.float_shares,
            profile_json = EXCLUDED.profile_json,
            updated_at = NOW()
        `,
        [
          ticker,
          runId,
          generatedAtUtc,
          String(row.asset_type ?? quote.assetType ?? ""),
          String(quote.quoteType ?? ""),
          String(quote.exchange ?? ""),
          String(quote.companyName ?? ""),
          String(quote.sector ?? ""),
          String(quote.industry ?? ""),
          String(quote.country ?? ""),
          toFiniteOrNull(quote.marketCap),
          toFiniteOrNull(quote.sharesOutstanding),
          firstPositiveNumber(quote.sharesFloat, quote.floatShares),
          JSON.stringify(quote),
        ],
      );
      symbolsInserted += 1;

      await client.query(
        `
          INSERT INTO runtime_symbols_history (
            run_id, ticker, generated_at_utc, asset_type, quote_type, exchange, company_name,
            sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json, updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4, $5, $6, $7,
            $8, $9, $10, $11, $12, $13, $14::jsonb, NOW()
          )
          ON CONFLICT (run_id, ticker)
          DO UPDATE SET
            generated_at_utc = EXCLUDED.generated_at_utc,
            asset_type = EXCLUDED.asset_type,
            quote_type = EXCLUDED.quote_type,
            exchange = EXCLUDED.exchange,
            company_name = EXCLUDED.company_name,
            sector = EXCLUDED.sector,
            industry = EXCLUDED.industry,
            country = EXCLUDED.country,
            market_cap = EXCLUDED.market_cap,
            shares_outstanding = EXCLUDED.shares_outstanding,
            float_shares = EXCLUDED.float_shares,
            profile_json = EXCLUDED.profile_json,
            updated_at = NOW()
        `,
        [
          runId,
          ticker,
          generatedAtUtc,
          String(row.asset_type ?? quote.assetType ?? ""),
          String(quote.quoteType ?? ""),
          String(quote.exchange ?? ""),
          String(quote.companyName ?? ""),
          String(quote.sector ?? ""),
          String(quote.industry ?? ""),
          String(quote.country ?? ""),
          toFiniteOrNull(quote.marketCap),
          toFiniteOrNull(quote.sharesOutstanding),
          firstPositiveNumber(quote.sharesFloat, quote.floatShares),
          JSON.stringify(quote),
        ],
      );
      symbolsHistoryInserted += 1;

      await client.query(
        `
          INSERT INTO runtime_metrics_latest (
            ticker, run_id, generated_at_utc, atr14, rsi14, sma20, sma50, sma200,
            change_pct, change_amount, gap_pct, rel_volume, avg_volume, volume,
            perf_week, perf_month, perf_quarter, perf_half, perf_ytd, perf_year, metrics_json, updated_at
          )
          VALUES (
            $1, $2, $3::timestamptz, $4, $5, $6, $7, $8,
            $9, $10, $11, $12, $13, $14,
            $15, $16, $17, $18, $19, $20, $21::jsonb, NOW()
          )
          ON CONFLICT (ticker)
          DO UPDATE SET
            run_id = EXCLUDED.run_id,
            generated_at_utc = EXCLUDED.generated_at_utc,
            atr14 = EXCLUDED.atr14,
            rsi14 = EXCLUDED.rsi14,
            sma20 = EXCLUDED.sma20,
            sma50 = EXCLUDED.sma50,
            sma200 = EXCLUDED.sma200,
            change_pct = EXCLUDED.change_pct,
            change_amount = EXCLUDED.change_amount,
            gap_pct = EXCLUDED.gap_pct,
            rel_volume = EXCLUDED.rel_volume,
            avg_volume = EXCLUDED.avg_volume,
            volume = EXCLUDED.volume,
            perf_week = EXCLUDED.perf_week,
            perf_month = EXCLUDED.perf_month,
            perf_quarter = EXCLUDED.perf_quarter,
            perf_half = EXCLUDED.perf_half,
            perf_ytd = EXCLUDED.perf_ytd,
            perf_year = EXCLUDED.perf_year,
            metrics_json = EXCLUDED.metrics_json,
            updated_at = NOW()
        `,
        [
          ticker,
          runId,
          generatedAtUtc,
          firstPositiveNumber(quote.atr14, quote.atr),
          toFiniteOrNull(quote.rsi14),
          toFiniteOrNull(quote.sma20),
          toFiniteOrNull(quote.sma50),
          toFiniteOrNull(quote.sma200),
          toFiniteOrNull(quote.changePct),
          toFiniteOrNull(quote.change),
          toFiniteOrNull(quote.gap),
          toFiniteOrNull(quote.relVolume),
          firstPositiveNumber(quote.avgVolume, quote.averageVolume),
          toFiniteOrNull(quote.volume),
          toFiniteOrNull(quote.perfWeek),
          toFiniteOrNull(quote.perfMonth),
          toFiniteOrNull(quote.perfQuarter),
          toFiniteOrNull(quote.perfHalf),
          toFiniteOrNull(quote.perfYtd),
          toFiniteOrNull(quote.perfYear),
          JSON.stringify(quote),
        ],
      );
      metricsInserted += 1;

      const closePrice = firstPositiveNumber(quote.price, row.price);
      const openPrice = firstPositiveNumber(quote.open, quote.prevClose, closePrice);
      const highPrice = firstPositiveNumber(quote.dayHigh, quote.high, closePrice);
      const lowPrice = firstPositiveNumber(quote.dayLow, quote.low, closePrice);

      await client.query(
        `
          INSERT INTO runtime_bars_daily (
            ticker, bar_date, run_id, generated_at_utc, open, high, low, close, volume, source
          )
          VALUES ($1, $2::date, $3, $4::timestamptz, $5, $6, $7, $8, $9, $10)
          ON CONFLICT (ticker, bar_date)
          DO UPDATE SET
            run_id = EXCLUDED.run_id,
            generated_at_utc = EXCLUDED.generated_at_utc,
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            source = EXCLUDED.source
        `,
        [
          ticker,
          barDate,
          runId,
          generatedAtUtc,
          openPrice,
          highPrice,
          lowPrice,
          closePrice,
          toFiniteOrNull(quote.volume),
          "bridge_snapshot_quote_cache",
        ],
      );
      barsInserted += 1;
    }

    if (decisionsInserted === 0 || symbolsInserted === 0 || metricsInserted === 0) {
      throw new Error("Runtime sync produced empty critical table insert counts.");
    }

    if (decisionsInserted !== symbolsInserted || decisionsInserted !== metricsInserted) {
      throw new Error(
        `Runtime table insert mismatch: decisions=${decisionsInserted}, symbols=${symbolsInserted}, metrics=${metricsInserted}`,
      );
    }
    if (decisionsHistoryInserted !== decisionsInserted || symbolsHistoryInserted !== symbolsInserted) {
      throw new Error(
        `Runtime history insert mismatch: decisions_history=${decisionsHistoryInserted}, decisions=${decisionsInserted}, symbols_history=${symbolsHistoryInserted}, symbols=${symbolsInserted}`,
      );
    }

    await client.query(
      `
        INSERT INTO runtime_refresh_runs (
          run_id, mode, trigger_source, requested_by, started_at, completed_at, report_generated_at_utc,
          bundle_generated_at_utc, snapshot_publication_id, quote_publication_id, quote_binding_status,
          rows_written, report_status, optimizer_short_cycle, optimizer_cycle_requested_runs, optimizer_cycle_completed_runs,
          optimizer_session_id, optimizer_target_return_lift_pct, optimizer_best_score, optimizer_target_met,
          epoch_library_confidence_schema, epoch_library_status, updated_at
        )
        VALUES (
          $1, $2, $3, $4, $5::timestamptz, $6::timestamptz, $7::timestamptz,
          $8::timestamptz, $9, $10, $11,
          $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, NOW()
        )
        ON CONFLICT (run_id)
        DO UPDATE SET
          mode = EXCLUDED.mode,
          trigger_source = EXCLUDED.trigger_source,
          requested_by = EXCLUDED.requested_by,
          started_at = EXCLUDED.started_at,
          report_generated_at_utc = EXCLUDED.report_generated_at_utc,
          bundle_generated_at_utc = EXCLUDED.bundle_generated_at_utc,
          snapshot_publication_id = EXCLUDED.snapshot_publication_id,
          quote_publication_id = EXCLUDED.quote_publication_id,
          quote_binding_status = EXCLUDED.quote_binding_status,
          rows_written = EXCLUDED.rows_written,
          report_status = EXCLUDED.report_status,
          optimizer_short_cycle = COALESCE(EXCLUDED.optimizer_short_cycle, runtime_refresh_runs.optimizer_short_cycle),
          optimizer_cycle_requested_runs = COALESCE(EXCLUDED.optimizer_cycle_requested_runs, runtime_refresh_runs.optimizer_cycle_requested_runs),
          optimizer_cycle_completed_runs = COALESCE(EXCLUDED.optimizer_cycle_completed_runs, runtime_refresh_runs.optimizer_cycle_completed_runs),
          optimizer_session_id = COALESCE(EXCLUDED.optimizer_session_id, runtime_refresh_runs.optimizer_session_id),
          optimizer_target_return_lift_pct = COALESCE(EXCLUDED.optimizer_target_return_lift_pct, runtime_refresh_runs.optimizer_target_return_lift_pct),
          optimizer_best_score = COALESCE(EXCLUDED.optimizer_best_score, runtime_refresh_runs.optimizer_best_score),
          optimizer_target_met = COALESCE(EXCLUDED.optimizer_target_met, runtime_refresh_runs.optimizer_target_met),
          epoch_library_confidence_schema = COALESCE(EXCLUDED.epoch_library_confidence_schema, runtime_refresh_runs.epoch_library_confidence_schema),
          epoch_library_status = COALESCE(EXCLUDED.epoch_library_status, runtime_refresh_runs.epoch_library_status),
          updated_at = NOW()
      `,
      [
        runId,
        mode,
        triggerSource,
        requestedBy,
        startedAt,
        completedAt,
        generatedAtUtc,
        generatedAtUtc,
        publicationBundleMeta.snapshotPublicationId,
        publicationBundleMeta.quotePublicationId,
        publicationBundleMeta.quoteBindingStatus,
        toIntOrNull(report?.rows_written),
        String(report?.status ?? "unknown"),
        process.env.TFE_OPTIMIZER_SHORT_CYCLE ?? null,
        toIntOrNull(process.env.TFE_OPTIMIZER_CYCLE_REQUESTED_RUNS),
        toIntOrNull(process.env.TFE_OPTIMIZER_CYCLE_COMPLETED_RUNS),
        process.env.TFE_OPTIMIZER_SESSION_ID ?? null,
        toFiniteOrNull(process.env.TFE_OPTIMIZER_TARGET_RETURN_LIFT_PCT),
        toFiniteOrNull(process.env.TFE_OPTIMIZER_BEST_SCORE),
        toBooleanOrNull(process.env.TFE_OPTIMIZER_TARGET_MET),
        process.env.TFE_EPOCH_LIBRARY_CONFIDENCE_SCHEMA ?? null,
        process.env.TFE_EPOCH_LIBRARY_STATUS ?? null,
      ],
    );

    await client.query("COMMIT");

    const provenanceSummary = await client.query(
      `
        SELECT
          (SELECT COUNT(*)::int FROM runtime_decisions_latest WHERE run_id = $1) AS runtime_decision_row_count,
          (SELECT COUNT(*)::int FROM runtime_decision_provenance_latest WHERE run_id = $1) AS provenance_row_count,
          (SELECT MAX(provenance_generated_utc) FROM runtime_decision_provenance_latest WHERE run_id = $1) AS latest_provenance_generated_utc,
          (SELECT writer_build_hash FROM runtime_decision_provenance_latest WHERE run_id = $1 ORDER BY provenance_generated_utc DESC NULLS LAST LIMIT 1) AS writer_build_hash,
          (SELECT cp_profile FROM runtime_decision_provenance_latest WHERE run_id = $1 ORDER BY provenance_generated_utc DESC NULLS LAST LIMIT 1) AS cp_profile
      `,
      [runId],
    );
    const summaryRow = provenanceSummary.rows[0] ?? {};
    const provenanceArtifact = buildProvenanceArtifact(provenanceStats, runId, {
      runtime_decision_row_count: summaryRow.runtime_decision_row_count,
      provenance_row_count: summaryRow.provenance_row_count,
      latest_provenance_generated_utc:
        summaryRow.latest_provenance_generated_utc instanceof Date
          ? summaryRow.latest_provenance_generated_utc.toISOString()
          : String(summaryRow.latest_provenance_generated_utc ?? "").trim() || null,
      writer_build_hash: String(summaryRow.writer_build_hash ?? "").trim() || null,
      cp_profile: String(summaryRow.cp_profile ?? "").trim() || null,
    });
    writeFileSync(provenanceArtifactPath, `${JSON.stringify(provenanceArtifact, null, 2)}\n`, "utf-8");

    const summary = {
      status: "ok",
      run_id: runId,
      mode,
      generated_at_utc: generatedAtUtc,
      generated_at_source: timestampResolution.generatedAtSource,
      snapshot_generated_at_utc: timestampResolution.snapshotGeneratedAtUtc,
      report_generated_at_utc: timestampResolution.reportGeneratedAtUtc,
      timestamp_mismatch_detected: timestampResolution.timestampMismatch,
      rows_snapshot_input: snapshotRowsInput.length,
      rows_snapshot_deduped: snapshotRows.length,
      duplicate_rows_dropped: dedupe.duplicateRowsDropped,
      quote_input_mode: quoteInput.quoteInputMode,
      quote_file_exists: quoteFileExists,
      rows_quote_cache: Object.keys(quoteRows).length,
      snapshot_publication_id: publicationBundleMeta.snapshotPublicationId,
      quote_publication_id: publicationBundleMeta.quotePublicationId,
      quote_binding_status: publicationBundleMeta.quoteBindingStatus,
      inserted: {
        runtime_decisions_latest: decisionsInserted,
        runtime_decisions_history: decisionsHistoryInserted,
        runtime_decision_provenance_latest: provenanceInserted,
        runtime_symbols: symbolsInserted,
        runtime_symbols_history: symbolsHistoryInserted,
        runtime_metrics_latest: metricsInserted,
        runtime_bars_daily: barsInserted,
      },
      provenance_artifact_path: provenanceArtifactPath,
    };

    process.stdout.write(`${JSON.stringify(summary)}\n`);
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch {
      // Ignore rollback errors.
    }
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

function isDirectExecution() {
  const entryPath = String(process.argv[1] ?? "").trim();
  if (!entryPath) return false;
  return path.resolve(entryPath) === MODULE_FILE_PATH;
}

if (isDirectExecution()) {
  main().catch((error) => {
    const message = error instanceof Error ? error.message : "Unknown runtime sync failure.";
    process.stderr.write(`${message}\n`);
    process.exit(1);
  });
}
