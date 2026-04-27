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
const DEFAULT_RUNTIME_SYNC_BATCH_SIZE = 500;
const DEADLOCK_ERROR_CODE = "40P01";
const DEADLOCK_RETRY_ATTEMPTS = 5;
const DEADLOCK_RETRY_BASE_DELAY_MS = 500;
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

function readRuntimeSyncBatchSize() {
  const raw = String(process.env.TFE_RUNTIME_SYNC_BATCH_SIZE ?? `${DEFAULT_RUNTIME_SYNC_BATCH_SIZE}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_RUNTIME_SYNC_BATCH_SIZE;
  const whole = Math.floor(n);
  if (whole < 1) return DEFAULT_RUNTIME_SYNC_BATCH_SIZE;
  return whole;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isDeadlockError(error) {
  if (!error || typeof error !== "object") return false;
  return String(error.code ?? "").trim() === DEADLOCK_ERROR_CODE;
}

async function runTransactionWithDeadlockRetry(pool, work) {
  let lastError = null;

  for (let attempt = 1; attempt <= DEADLOCK_RETRY_ATTEMPTS; attempt += 1) {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const result = await work(client, attempt);
      await client.query("COMMIT");
      return result;
    } catch (error) {
      lastError = error;
      try {
        await client.query("ROLLBACK");
      } catch {
        // Ignore rollback errors.
      }

      if (isDeadlockError(error) && attempt < DEADLOCK_RETRY_ATTEMPTS) {
        const delayMs = DEADLOCK_RETRY_BASE_DELAY_MS * attempt;
        process.stderr.write(
          `runtime_sync_postgres deadlock detected; retrying attempt ${attempt + 1}/${DEADLOCK_RETRY_ATTEMPTS} after ${delayMs}ms\n`,
        );
        await sleep(delayMs);
        continue;
      }

      throw error;
    } finally {
      client.release();
    }
  }

  throw lastError ?? new Error("Runtime sync deadlock retries exhausted.");
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
  // Use L5 basin physics decision if available (written by L5 canonical filter).
  // Falls back to simple S_UF/R_UF threshold for pre-filter snapshots.
  const basinDecision = row?.l5_basin_decision;
  if (basinDecision === "Accumulate" || basinDecision === "Hold" || basinDecision === "Avoid") {
    return basinDecision;
  }

  // Fallback: simple threshold (used when l5_basin_decision not in snapshot)
  const sUf = toFiniteOrNull(row?.S_UF ?? row?.s_uf);
  const rUf = toFiniteOrNull(row?.R_UF ?? row?.r_uf);
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
  // Dropped: the old (run_id, ticker) unique index is replaced by ticker-only PK.
  // The migration in the sync transaction handles removing the old constraint.
  await client.query(`
    DROP INDEX IF EXISTS idx_runtime_decision_provenance_latest_run_ticker_unique
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

function chunkArray(values, chunkSize) {
  if (!Array.isArray(values) || values.length === 0) return [];

  const normalizedChunkSize = Math.max(1, Math.floor(Number(chunkSize) || DEFAULT_RUNTIME_SYNC_BATCH_SIZE));
  const chunks = [];
  for (let index = 0; index < values.length; index += normalizedChunkSize) {
    chunks.push(values.slice(index, index + normalizedChunkSize));
  }
  return chunks;
}

function buildPreparedRuntimeRecords({
  snapshotRows,
  quoteRows,
  runId,
  generatedAtUtc,
  completedAt,
  policyRuntime,
  provenanceMinBars,
}) {
  const records = [];
  const provenanceStats = initializeProvenanceStats();
  const barDate = generatedAtUtc.slice(0, 10);

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

    const closePrice = firstPositiveNumber(quote.price, row.price);
    const openPrice = firstPositiveNumber(quote.open, quote.prevClose, closePrice);
    const highPrice = firstPositiveNumber(quote.dayHigh, quote.high, closePrice);
    const lowPrice = firstPositiveNumber(quote.dayLow, quote.low, closePrice);

    records.push({
      ticker,
      runId,
      generatedAtUtc,
      barDate,
      snapshotRowJson: JSON.stringify(snapshotRow),
      decisionLabel: String(persistedProvenance.decision ?? "Avoid"),
      barCount: toIntOrNull(row.bar_count),
      minBarsForAccumulate: DEFAULT_MIN_BARS,
      regime: String(row.regime ?? "UNKNOWN"),
      stabilityScore: toFiniteOrNull(row.stability_score),
      maxDd: toFiniteOrNull(row.max_dd),
      assetType: String(row.asset_type ?? quote.assetType ?? ""),
      quoteType: String(quote.quoteType ?? ""),
      exchange: String(quote.exchange ?? ""),
      companyName: String(quote.companyName ?? ""),
      sector: String(quote.sector ?? ""),
      industry: String(quote.industry ?? ""),
      country: String(quote.country ?? ""),
      marketCap: toFiniteOrNull(quote.marketCap),
      sharesOutstanding: toFiniteOrNull(quote.sharesOutstanding),
      floatShares: firstPositiveNumber(quote.sharesFloat, quote.floatShares),
      profileJson: JSON.stringify(quote),
      atr14: firstPositiveNumber(quote.atr14, quote.atr),
      rsi14: toFiniteOrNull(quote.rsi14),
      sma20: toFiniteOrNull(quote.sma20),
      sma50: toFiniteOrNull(quote.sma50),
      sma200: toFiniteOrNull(quote.sma200),
      changePct: toFiniteOrNull(quote.changePct),
      changeAmount: toFiniteOrNull(quote.change),
      gapPct: toFiniteOrNull(quote.gap),
      relVolume: toFiniteOrNull(quote.relVolume),
      avgVolume: firstPositiveNumber(quote.avgVolume, quote.averageVolume),
      volume: toFiniteOrNull(quote.volume),
      perfWeek: toFiniteOrNull(quote.perfWeek),
      perfMonth: toFiniteOrNull(quote.perfMonth),
      perfQuarter: toFiniteOrNull(quote.perfQuarter),
      perfHalf: toFiniteOrNull(quote.perfHalf),
      perfYtd: toFiniteOrNull(quote.perfYtd),
      perfYear: toFiniteOrNull(quote.perfYear),
      metricsJson: JSON.stringify(quote),
      barOpen: openPrice,
      barHigh: highPrice,
      barLow: lowPrice,
      barClose: closePrice,
      barVolume: toFiniteOrNull(quote.volume),
      barSource: "bridge_snapshot_quote_cache",
      provenance: {
        generatedAtUtc,
        snapshotTimestampUtc: persistedProvenance.snapshot_timestamp_utc,
        runtimeSyncCompletedUtc: persistedProvenance.runtime_sync_completed_utc,
        decisionTimestampUtc: persistedProvenance.decision_timestamp_utc,
        snapshotRowDigestSha256: persistedProvenance.snapshot_row_digest_sha256,
        policyArtifactId: persistedProvenance.policy_artifact_id,
        policyArtifactHashSha256: persistedProvenance.policy_artifact_hash_sha256,
        policySourceMode: persistedProvenance.policy_source_mode,
        candidateKeyChainJson: JSON.stringify(persistedProvenance.candidate_key_chain_json),
        matchedKey: persistedProvenance.matched_key,
        matchLevel: persistedProvenance.match_level,
        fallbackLadderLevel: persistedProvenance.fallback_ladder_level,
        matchedExactBool: persistedProvenance.matched_exact_bool,
        fallbackUsed: persistedProvenance.fallback_used,
        fallbackReasonCode: persistedProvenance.fallback_reason_code,
        decision: persistedProvenance.decision,
        decisionReasonCode: persistedProvenance.decision_reason_code,
        anomalyFlagsUsedJson: JSON.stringify(persistedProvenance.anomaly_flags_used_json),
        structuralRecencyComponentsUsedJson: JSON.stringify(
          persistedProvenance.structural_recency_components_used_json,
        ),
        epochComponentsUsedJson: JSON.stringify(persistedProvenance.epoch_components_used_json),
        coverageClass: persistedProvenance.coverage_class,
        provenanceSchemaVersion: persistedProvenance.provenance_schema_version,
        writerComponent: persistedProvenance.writer_component,
        writerBuildHash: persistedProvenance.writer_build_hash,
        cpProfile: persistedProvenance.cp_profile,
        provenanceGeneratedUtc: persistedProvenance.provenance_generated_utc,
        provenanceValid: persistedProvenance.provenance_valid,
        provenanceJson: JSON.stringify(persistedProvenance.provenance_json),
      },
    });
  }

  return {
    records,
    provenanceStats,
  };
}

async function upsertRuntimeBatch(client, records) {
  if (!Array.isArray(records) || records.length === 0) {
    return {
      decisionsInserted: 0,
      decisionsHistoryInserted: 0,
      provenanceInserted: 0,
      symbolsInserted: 0,
      symbolsHistoryInserted: 0,
      metricsInserted: 0,
      barsInserted: 0,
    };
  }

  const tickers = records.map((record) => record.ticker);
  const runIds = records.map((record) => record.runId);
  const generatedAtUtcValues = records.map((record) => record.generatedAtUtc);
  const snapshotRowJsonTexts = records.map((record) => record.snapshotRowJson);
  const decisionLabels = records.map((record) => record.decisionLabel);
  const barCounts = records.map((record) => record.barCount);
  const minBarsValues = records.map((record) => record.minBarsForAccumulate);
  const regimes = records.map((record) => record.regime);
  const stabilityScores = records.map((record) => record.stabilityScore);
  const maxDds = records.map((record) => record.maxDd);
  // CP-2: wire decision_reason_code from provenance into runtime_decisions_latest.reason_code
  const decisionReasonCodes = records.map((record) => record.provenance.decisionReasonCode ?? null);

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
      SELECT
        batch.ticker,
        batch.run_id,
        batch.generated_at_utc,
        batch.snapshot_row_json_text::jsonb,
        batch.decision_label,
        batch.decision_reason_code,
        NULL,
        batch.bar_count,
        batch.min_bars_for_accumulate,
        batch.regime,
        batch.stability_score,
        batch.max_dd,
        NULL, NULL, NULL, NULL,
        NULL, NULL, NULL, NULL, NULL, '[]'::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::text[],
        $5::text[],
        $6::integer[],
        $7::integer[],
        $8::text[],
        $9::double precision[],
        $10::double precision[],
        $11::text[]
      ) AS batch(
        ticker, run_id, generated_at_utc, snapshot_row_json_text,
        decision_label, bar_count, min_bars_for_accumulate, regime, stability_score, max_dd,
        decision_reason_code
      )
      ON CONFLICT (ticker)
      DO UPDATE SET
        run_id = EXCLUDED.run_id,
        generated_at_utc = EXCLUDED.generated_at_utc,
        snapshot_row_json = EXCLUDED.snapshot_row_json,
        decision_label = EXCLUDED.decision_label,
        reason_code = EXCLUDED.reason_code,
        bar_count = EXCLUDED.bar_count,
        min_bars_for_accumulate = EXCLUDED.min_bars_for_accumulate,
        regime = EXCLUDED.regime,
        stability_score = EXCLUDED.stability_score,
        max_dd = EXCLUDED.max_dd,
        updated_at = NOW()
    `,
    [
      tickers,
      runIds,
      generatedAtUtcValues,
      snapshotRowJsonTexts,
      decisionLabels,
      barCounts,
      minBarsValues,
      regimes,
      stabilityScores,
      maxDds,
      decisionReasonCodes,
    ],
  );

  await client.query(
    `
      INSERT INTO runtime_decisions_history (
        run_id, ticker, generated_at_utc, snapshot_row_json, updated_at
      )
      SELECT
        batch.run_id,
        batch.ticker,
        batch.generated_at_utc,
        batch.snapshot_row_json_text::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::text[]
      ) AS batch(run_id, ticker, generated_at_utc, snapshot_row_json_text)
      ON CONFLICT (run_id, ticker)
      DO UPDATE SET
        generated_at_utc = EXCLUDED.generated_at_utc,
        snapshot_row_json = EXCLUDED.snapshot_row_json,
        updated_at = NOW()
    `,
    [
      runIds,
      tickers,
      generatedAtUtcValues,
      snapshotRowJsonTexts,
    ],
  );

  const provenanceGeneratedAtUtcValues = records.map((record) => record.provenance.generatedAtUtc);
  const provenanceSnapshotTimestampUtcValues = records.map((record) => record.provenance.snapshotTimestampUtc);
  const provenanceRuntimeSyncCompletedUtcValues = records.map((record) => record.provenance.runtimeSyncCompletedUtc);
  const provenanceDecisionTimestampUtcValues = records.map((record) => record.provenance.decisionTimestampUtc);
  const provenanceSnapshotRowDigestValues = records.map((record) => record.provenance.snapshotRowDigestSha256);
  const provenancePolicyArtifactIdValues = records.map((record) => record.provenance.policyArtifactId);
  const provenancePolicyArtifactHashValues = records.map((record) => record.provenance.policyArtifactHashSha256);
  const provenancePolicySourceModeValues = records.map((record) => record.provenance.policySourceMode);
  const provenanceCandidateKeyChainValues = records.map((record) => record.provenance.candidateKeyChainJson);
  const provenanceMatchedKeyValues = records.map((record) => record.provenance.matchedKey);
  const provenanceMatchLevelValues = records.map((record) => record.provenance.matchLevel);
  const provenanceFallbackLadderValues = records.map((record) => record.provenance.fallbackLadderLevel);
  const provenanceMatchedExactValues = records.map((record) => record.provenance.matchedExactBool);
  const provenanceFallbackUsedValues = records.map((record) => record.provenance.fallbackUsed);
  const provenanceFallbackReasonValues = records.map((record) => record.provenance.fallbackReasonCode);
  const provenanceDecisionValues = records.map((record) => record.provenance.decision);
  const provenanceDecisionReasonValues = records.map((record) => record.provenance.decisionReasonCode);
  const provenanceAnomalyFlagsValues = records.map((record) => record.provenance.anomalyFlagsUsedJson);
  const provenanceStructuralRecencyValues = records.map(
    (record) => record.provenance.structuralRecencyComponentsUsedJson,
  );
  const provenanceEpochComponentsValues = records.map((record) => record.provenance.epochComponentsUsedJson);
  const provenanceCoverageValues = records.map((record) => record.provenance.coverageClass);
  const provenanceSchemaVersionValues = records.map((record) => record.provenance.provenanceSchemaVersion);
  const provenanceWriterComponentValues = records.map((record) => record.provenance.writerComponent);
  const provenanceWriterBuildHashValues = records.map((record) => record.provenance.writerBuildHash);
  const provenanceCpProfileValues = records.map((record) => record.provenance.cpProfile);
  const provenanceGeneratedUtcValues = records.map((record) => record.provenance.provenanceGeneratedUtc);
  const provenanceValidValues = records.map((record) => record.provenance.provenanceValid);
  const provenanceJsonValues = records.map((record) => record.provenance.provenanceJson);

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
      SELECT
        batch.run_id,
        batch.ticker,
        batch.generated_at_utc,
        batch.snapshot_timestamp_utc,
        batch.runtime_sync_completed_utc,
        batch.decision_timestamp_utc,
        batch.snapshot_row_digest_sha256,
        batch.policy_artifact_id,
        batch.policy_artifact_hash_sha256,
        batch.policy_source_mode,
        batch.candidate_key_chain_json_text::jsonb,
        batch.matched_key,
        batch.match_level,
        batch.fallback_ladder_level,
        batch.matched_exact_bool,
        batch.fallback_used,
        batch.fallback_reason_code,
        batch.decision,
        batch.decision_reason_code,
        batch.anomaly_flags_used_json_text::jsonb,
        batch.structural_recency_components_used_json_text::jsonb,
        batch.epoch_components_used_json_text::jsonb,
        batch.coverage_class,
        batch.provenance_schema_version,
        batch.writer_component,
        batch.writer_build_hash,
        batch.cp_profile,
        batch.provenance_generated_utc,
        batch.provenance_valid,
        batch.provenance_json_text::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::timestamptz[],
        $5::timestamptz[],
        $6::timestamptz[],
        $7::text[],
        $8::text[],
        $9::text[],
        $10::text[],
        $11::text[],
        $12::text[],
        $13::text[],
        $14::text[],
        $15::boolean[],
        $16::boolean[],
        $17::text[],
        $18::text[],
        $19::text[],
        $20::text[],
        $21::text[],
        $22::text[],
        $23::text[],
        $24::text[],
        $25::text[],
        $26::text[],
        $27::text[],
        $28::timestamptz[],
        $29::boolean[],
        $30::text[]
      ) AS batch(
        run_id, ticker, generated_at_utc, snapshot_timestamp_utc, runtime_sync_completed_utc, decision_timestamp_utc, snapshot_row_digest_sha256,
        policy_artifact_id, policy_artifact_hash_sha256, policy_source_mode,
        candidate_key_chain_json_text, matched_key, match_level, fallback_ladder_level, matched_exact_bool,
        fallback_used, fallback_reason_code, decision, decision_reason_code,
        anomaly_flags_used_json_text, structural_recency_components_used_json_text, epoch_components_used_json_text,
        coverage_class,
        provenance_schema_version, writer_component, writer_build_hash, cp_profile, provenance_generated_utc,
        provenance_valid, provenance_json_text
      )
      ON CONFLICT (ticker)
      DO UPDATE SET
        run_id = EXCLUDED.run_id,
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
      runIds,
      tickers,
      provenanceGeneratedAtUtcValues,
      provenanceSnapshotTimestampUtcValues,
      provenanceRuntimeSyncCompletedUtcValues,
      provenanceDecisionTimestampUtcValues,
      provenanceSnapshotRowDigestValues,
      provenancePolicyArtifactIdValues,
      provenancePolicyArtifactHashValues,
      provenancePolicySourceModeValues,
      provenanceCandidateKeyChainValues,
      provenanceMatchedKeyValues,
      provenanceMatchLevelValues,
      provenanceFallbackLadderValues,
      provenanceMatchedExactValues,
      provenanceFallbackUsedValues,
      provenanceFallbackReasonValues,
      provenanceDecisionValues,
      provenanceDecisionReasonValues,
      provenanceAnomalyFlagsValues,
      provenanceStructuralRecencyValues,
      provenanceEpochComponentsValues,
      provenanceCoverageValues,
      provenanceSchemaVersionValues,
      provenanceWriterComponentValues,
      provenanceWriterBuildHashValues,
      provenanceCpProfileValues,
      provenanceGeneratedUtcValues,
      provenanceValidValues,
      provenanceJsonValues,
    ],
  );

  const assetTypes = records.map((record) => record.assetType);
  const quoteTypes = records.map((record) => record.quoteType);
  const exchanges = records.map((record) => record.exchange);
  const companyNames = records.map((record) => record.companyName);
  const sectors = records.map((record) => record.sector);
  const industries = records.map((record) => record.industry);
  const countries = records.map((record) => record.country);
  const marketCaps = records.map((record) => record.marketCap);
  const sharesOutstandingValues = records.map((record) => record.sharesOutstanding);
  const floatSharesValues = records.map((record) => record.floatShares);
  const profileJsonTexts = records.map((record) => record.profileJson);

  await client.query(
    `
      INSERT INTO runtime_symbols (
        ticker, run_id, generated_at_utc, asset_type, quote_type, exchange, company_name,
        sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json, updated_at
      )
      SELECT
        batch.ticker,
        batch.run_id,
        batch.generated_at_utc,
        batch.asset_type,
        batch.quote_type,
        batch.exchange,
        batch.company_name,
        batch.sector,
        batch.industry,
        batch.country,
        batch.market_cap,
        batch.shares_outstanding,
        batch.float_shares,
        batch.profile_json_text::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::text[],
        $5::text[],
        $6::text[],
        $7::text[],
        $8::text[],
        $9::text[],
        $10::text[],
        $11::double precision[],
        $12::double precision[],
        $13::double precision[],
        $14::text[]
      ) AS batch(
        ticker, run_id, generated_at_utc, asset_type, quote_type, exchange, company_name,
        sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json_text
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
      tickers,
      runIds,
      generatedAtUtcValues,
      assetTypes,
      quoteTypes,
      exchanges,
      companyNames,
      sectors,
      industries,
      countries,
      marketCaps,
      sharesOutstandingValues,
      floatSharesValues,
      profileJsonTexts,
    ],
  );

  await client.query(
    `
      INSERT INTO runtime_symbols_history (
        run_id, ticker, generated_at_utc, asset_type, quote_type, exchange, company_name,
        sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json, updated_at
      )
      SELECT
        batch.run_id,
        batch.ticker,
        batch.generated_at_utc,
        batch.asset_type,
        batch.quote_type,
        batch.exchange,
        batch.company_name,
        batch.sector,
        batch.industry,
        batch.country,
        batch.market_cap,
        batch.shares_outstanding,
        batch.float_shares,
        batch.profile_json_text::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::text[],
        $5::text[],
        $6::text[],
        $7::text[],
        $8::text[],
        $9::text[],
        $10::text[],
        $11::double precision[],
        $12::double precision[],
        $13::double precision[],
        $14::text[]
      ) AS batch(
        run_id, ticker, generated_at_utc, asset_type, quote_type, exchange, company_name,
        sector, industry, country, market_cap, shares_outstanding, float_shares, profile_json_text
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
      runIds,
      tickers,
      generatedAtUtcValues,
      assetTypes,
      quoteTypes,
      exchanges,
      companyNames,
      sectors,
      industries,
      countries,
      marketCaps,
      sharesOutstandingValues,
      floatSharesValues,
      profileJsonTexts,
    ],
  );

  const atr14Values = records.map((record) => record.atr14);
  const rsi14Values = records.map((record) => record.rsi14);
  const sma20Values = records.map((record) => record.sma20);
  const sma50Values = records.map((record) => record.sma50);
  const sma200Values = records.map((record) => record.sma200);
  const changePctValues = records.map((record) => record.changePct);
  const changeAmountValues = records.map((record) => record.changeAmount);
  const gapPctValues = records.map((record) => record.gapPct);
  const relVolumeValues = records.map((record) => record.relVolume);
  const avgVolumeValues = records.map((record) => record.avgVolume);
  const volumeValues = records.map((record) => record.volume);
  const perfWeekValues = records.map((record) => record.perfWeek);
  const perfMonthValues = records.map((record) => record.perfMonth);
  const perfQuarterValues = records.map((record) => record.perfQuarter);
  const perfHalfValues = records.map((record) => record.perfHalf);
  const perfYtdValues = records.map((record) => record.perfYtd);
  const perfYearValues = records.map((record) => record.perfYear);
  const metricsJsonTexts = records.map((record) => record.metricsJson);

  await client.query(
    `
      INSERT INTO runtime_metrics_latest (
        ticker, run_id, generated_at_utc, atr14, rsi14, sma20, sma50, sma200,
        change_pct, change_amount, gap_pct, rel_volume, avg_volume, volume,
        perf_week, perf_month, perf_quarter, perf_half, perf_ytd, perf_year, metrics_json, updated_at
      )
      SELECT
        batch.ticker,
        batch.run_id,
        batch.generated_at_utc,
        batch.atr14,
        batch.rsi14,
        batch.sma20,
        batch.sma50,
        batch.sma200,
        batch.change_pct,
        batch.change_amount,
        batch.gap_pct,
        batch.rel_volume,
        batch.avg_volume,
        batch.volume,
        batch.perf_week,
        batch.perf_month,
        batch.perf_quarter,
        batch.perf_half,
        batch.perf_ytd,
        batch.perf_year,
        batch.metrics_json_text::jsonb,
        NOW()
      FROM UNNEST(
        $1::text[],
        $2::text[],
        $3::timestamptz[],
        $4::double precision[],
        $5::double precision[],
        $6::double precision[],
        $7::double precision[],
        $8::double precision[],
        $9::double precision[],
        $10::double precision[],
        $11::double precision[],
        $12::double precision[],
        $13::double precision[],
        $14::double precision[],
        $15::double precision[],
        $16::double precision[],
        $17::double precision[],
        $18::double precision[],
        $19::double precision[],
        $20::double precision[],
        $21::text[]
      ) AS batch(
        ticker, run_id, generated_at_utc, atr14, rsi14, sma20, sma50, sma200,
        change_pct, change_amount, gap_pct, rel_volume, avg_volume, volume,
        perf_week, perf_month, perf_quarter, perf_half, perf_ytd, perf_year, metrics_json_text
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
      tickers,
      runIds,
      generatedAtUtcValues,
      atr14Values,
      rsi14Values,
      sma20Values,
      sma50Values,
      sma200Values,
      changePctValues,
      changeAmountValues,
      gapPctValues,
      relVolumeValues,
      avgVolumeValues,
      volumeValues,
      perfWeekValues,
      perfMonthValues,
      perfQuarterValues,
      perfHalfValues,
      perfYtdValues,
      perfYearValues,
      metricsJsonTexts,
    ],
  );

  const barDates = records.map((record) => record.barDate);
  const barOpenValues = records.map((record) => record.barOpen);
  const barHighValues = records.map((record) => record.barHigh);
  const barLowValues = records.map((record) => record.barLow);
  const barCloseValues = records.map((record) => record.barClose);
  const barVolumeValues = records.map((record) => record.barVolume);
  const barSourceValues = records.map((record) => record.barSource);

  await client.query(
    `
      INSERT INTO runtime_bars_daily (
        ticker, bar_date, run_id, generated_at_utc, open, high, low, close, volume, source
      )
      SELECT
        batch.ticker,
        batch.bar_date,
        batch.run_id,
        batch.generated_at_utc,
        batch.open,
        batch.high,
        batch.low,
        batch.close,
        batch.volume,
        batch.source
      FROM UNNEST(
        $1::text[],
        $2::date[],
        $3::text[],
        $4::timestamptz[],
        $5::double precision[],
        $6::double precision[],
        $7::double precision[],
        $8::double precision[],
        $9::double precision[],
        $10::text[]
      ) AS batch(
        ticker, bar_date, run_id, generated_at_utc, open, high, low, close, volume, source
      )
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
      tickers,
      barDates,
      runIds,
      generatedAtUtcValues,
      barOpenValues,
      barHighValues,
      barLowValues,
      barCloseValues,
      barVolumeValues,
      barSourceValues,
    ],
  );

  return {
    decisionsInserted: records.length,
    decisionsHistoryInserted: records.length,
    provenanceInserted: records.length,
    symbolsInserted: records.length,
    symbolsHistoryInserted: records.length,
    metricsInserted: records.length,
    barsInserted: records.length,
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
  const runtimeSyncBatchSize = readRuntimeSyncBatchSize();

  if (snapshotRows.length === 0) {
    throw new Error("Snapshot row set is empty after dedupe; refusing runtime sync.");
  }

  const policyRuntime = loadPolicyRuntimeArtifact(root);
  const provenanceMinBars = minBarsForAccumulate();
  const preparedRecords = buildPreparedRuntimeRecords({
    snapshotRows,
    quoteRows,
    runId,
    generatedAtUtc,
    completedAt,
    policyRuntime,
    provenanceMinBars,
  });
  const runtimeSyncBatches = chunkArray(preparedRecords.records, runtimeSyncBatchSize);

  const pool = resolvePool();
  try {
    const provenanceArtifactPath = path.join(root, "current_l5_provenance_persistence_latest.json");
    const transactionResult = await runTransactionWithDeadlockRetry(pool, async (client) => {
      await ensureRuntimeTables(client);

      // NO DELETE. Ever. The upsert (ON CONFLICT) handles updates.
      // New symbols are inserted. Existing symbols are updated in place.
      // Delisted symbols stay in the table — they are harmless and their
      // structural history has value. If cleanup is ever needed, it is a
      // separate administrative operation, not part of the refresh pipeline.
      //
      // Update run_id on all existing rows so they share the same run_id
      // as the new batch (required for serving consistency).
      const newRunId = preparedRecords.records[0]?.runId ?? runId;
      await client.query(
        "UPDATE runtime_decisions_latest SET run_id = $1, generated_at_utc = $2 WHERE run_id != $1",
        [newRunId, generatedAtUtc]
      );
      await client.query(
        "UPDATE runtime_symbols SET run_id = $1 WHERE run_id != $1",
        [newRunId]
      );
      // Fix: drop the composite PK and use ticker-only PK for _latest tables.
      // The (run_id, ticker) PK was wrong — a _latest table should have one row
      // per ticker, not one row per (run_id, ticker). The composite PK caused
      // duplicate key violations when updating run_id across batches.
      await client.query(`
        DO $$
        BEGIN
          -- Remove the old composite primary key if it exists
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'runtime_decision_provenance_latest_pkey'
              AND conrelid = 'runtime_decision_provenance_latest'::regclass
          ) THEN
            -- Deduplicate: keep only the latest row per ticker before dropping PK
            DELETE FROM runtime_decision_provenance_latest a
            USING runtime_decision_provenance_latest b
            WHERE a.ticker = b.ticker
              AND a.ctid < b.ctid;

            ALTER TABLE runtime_decision_provenance_latest
              DROP CONSTRAINT runtime_decision_provenance_latest_pkey;

            ALTER TABLE runtime_decision_provenance_latest
              ADD PRIMARY KEY (ticker);
          END IF;
        END
        $$
      `);
      await client.query(
        "UPDATE runtime_decision_provenance_latest SET run_id = $1 WHERE run_id != $1",
        [newRunId]
      );
      await client.query(
        "UPDATE runtime_metrics_latest SET run_id = $1 WHERE run_id != $1",
        [newRunId]
      );
      console.log(`[RUNTIME-SYNC] Upsert mode — ${preparedRecords.records.length} records to upsert, existing rows preserved`);

      let decisionsInserted = 0;
      let decisionsHistoryInserted = 0;
      let provenanceInserted = 0;
      let symbolsInserted = 0;
      let symbolsHistoryInserted = 0;
      let metricsInserted = 0;
      let barsInserted = 0;
      for (const batch of runtimeSyncBatches) {
        const batchResult = await upsertRuntimeBatch(client, batch);
        decisionsInserted += batchResult.decisionsInserted;
        decisionsHistoryInserted += batchResult.decisionsHistoryInserted;
        provenanceInserted += batchResult.provenanceInserted;
        symbolsInserted += batchResult.symbolsInserted;
        symbolsHistoryInserted += batchResult.symbolsHistoryInserted;
        metricsInserted += batchResult.metricsInserted;
        barsInserted += batchResult.barsInserted;
      }

      if (decisionsInserted === 0 || symbolsInserted === 0 || metricsInserted === 0) {
        throw new Error("Runtime sync produced empty critical table insert counts.");
      }

      if (decisionsInserted !== symbolsInserted || decisionsInserted !== metricsInserted) {
        // Upsert mode: slight count differences can occur when some rows
        // are inserts and others are updates. Log but do not abort.
        console.warn(
          `[RUNTIME-SYNC] Upsert count variance (non-fatal): decisions=${decisionsInserted}, symbols=${symbolsInserted}, metrics=${metricsInserted}`,
        );
      }
      if (decisionsHistoryInserted !== decisionsInserted || symbolsHistoryInserted !== symbolsInserted) {
        throw new Error(
          `Runtime history insert mismatch: decisions_history=${decisionsHistoryInserted}, decisions=${decisionsInserted}, symbols_history=${symbolsInserted}, symbols=${symbolsInserted}`,
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

      return {
        decisionsInserted,
        decisionsHistoryInserted,
        provenanceInserted,
        symbolsInserted,
        symbolsHistoryInserted,
        metricsInserted,
        barsInserted,
        provenanceStats: preparedRecords.provenanceStats,
      };
    });

    const provenanceSummary = await pool.query(
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
    const provenanceArtifact = buildProvenanceArtifact(transactionResult.provenanceStats, runId, {
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
        runtime_decisions_latest: transactionResult.decisionsInserted,
        runtime_decisions_history: transactionResult.decisionsHistoryInserted,
        runtime_decision_provenance_latest: transactionResult.provenanceInserted,
        runtime_symbols: transactionResult.symbolsInserted,
        runtime_symbols_history: transactionResult.symbolsHistoryInserted,
        runtime_metrics_latest: transactionResult.metricsInserted,
        runtime_bars_daily: transactionResult.barsInserted,
      },
      batch_size: runtimeSyncBatchSize,
      batch_count: runtimeSyncBatches.length,
      provenance_artifact_path: provenanceArtifactPath,
    };

    process.stdout.write(`${JSON.stringify(summary)}\n`);
  } finally {
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
