#!/usr/bin/env node

import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const DEFAULT_MIN_NON_META_FIELDS = 20;
const DEFAULT_RECOVERY_CANDIDATE_LIMIT = 8;
const MISSING_TEXT_MARKERS = new Set([
  "",
  "NONE",
  "NULL",
  "N/A",
  "NA",
  "NAN",
  "UNKNOWN",
  "UNCLASSIFIED",
  "UNDEFINED",
  "-",
]);

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
    if (candidate && path.basename(candidate) === "Tao_Financial_Engine") {
      return candidate;
    }
  }

  return path.resolve(process.cwd(), "../..");
}

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function readPositiveIntEnv(name, defaultValue) {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) return defaultValue;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return defaultValue;
  const whole = Math.floor(parsed);
  if (whole <= 0) return defaultValue;
  return whole;
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
  return new Pool({
    host: readRequiredEnv("PGHOST", "TFE_DB_HOST"),
    database: readRequiredEnv("PGDATABASE", "TFE_DB_NAME"),
    user: readRequiredEnv("PGUSER", "TFE_DB_USER"),
    password: readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD"),
    port: readPgPort(),
    max: 2,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized: resolvePgSslRejectUnauthorized() },
    application_name: "tfe-quote-cache-runtime-seed",
  });
}

function parseArgs(argv) {
  const out = {
    output: "",
    minRows: 1,
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = String(argv[index] ?? "").trim();
    if (arg === "--output") {
      out.output = String(argv[index + 1] ?? "").trim();
      index += 1;
      continue;
    }
    if (arg === "--min-rows") {
      const parsed = Number(argv[index + 1] ?? "");
      out.minRows = Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 1;
      index += 1;
      continue;
    }
  }

  return out;
}

function toTextOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function toFiniteOrNull(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

function toPositiveOrNull(value) {
  const parsed = toFiniteOrNull(value);
  if (parsed === null) return null;
  if (parsed <= 0) return null;
  return parsed;
}

function parseIsoMs(value) {
  const parsed = Date.parse(String(value ?? "").trim());
  if (!Number.isFinite(parsed)) return 0;
  return parsed;
}

function isMissingValue(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") {
    const text = value.trim();
    if (!text) return true;
    return MISSING_TEXT_MARKERS.has(text.toUpperCase());
  }
  const numberValue = toFiniteOrNull(value);
  if (numberValue === null && typeof value === "number") return true;
  return false;
}

function nonMetaFieldCount(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return 0;
  let count = 0;
  for (const [key, value] of Object.entries(row)) {
    if (String(key).startsWith("__")) continue;
    if (isMissingValue(value)) continue;
    count += 1;
  }
  return count;
}

function looksLikeMissingProfile(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return true;

  const companyName = toTextOrNull(row.companyName);
  const sector = toTextOrNull(row.sector);
  const industry = toTextOrNull(row.industry);
  const country = toTextOrNull(row.country);
  const quoteType = String(row.quoteType ?? "").trim().toUpperCase();
  const assetType = String(row.assetType ?? "").trim().toUpperCase();

  if (!companyName) return true;

  if (["ETF", "MUTUALFUND", "MUTUAL FUND"].includes(quoteType) || ["ETF", "MUTUALFUND", "MUTUAL FUND"].includes(assetType)) {
    const category = toTextOrNull(row.category);
    const fundFamily = toTextOrNull(row.fundFamily);
    if (!sector && !category) return true;
    if (!industry) return true;
    if (!country && !fundFamily) return true;
    return false;
  }

  if (!sector) return true;
  if (!industry) return true;
  if (!country) return true;
  return false;
}

function looksLikeMissingCoreMetrics(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return true;
  if (isMissingValue(row.companyName)) return true;

  const assetType = String(row.assetType ?? "").trim().toUpperCase();
  const quoteType = String(row.quoteType ?? "").trim().toUpperCase();
  const profileKind = quoteType || assetType;
  if (!profileKind) return true;

  const baselineNumericFields = [
    "price",
    "changePct",
    "volume",
    "avgVolume",
    "high52",
    "low52",
    "sma20",
    "sma50",
    "atr14",
    "rsi14",
  ];
  for (const field of baselineNumericFields) {
    if (toFiniteOrNull(row[field]) === null) return true;
  }

  const isEtfLike = ["ETF", "MUTUALFUND", "MUTUAL FUND", "FUND"].includes(profileKind);
  const isEquityLike = ["EQUITY", "STOCK", "COMMONSTOCK", "COMMON STOCK"].includes(profileKind);
  const isIndexLike = ["INDEX", "CURRENCY", "CRYPTOCURRENCY", "FUTURE"].includes(profileKind);

  if (!isIndexLike && toFiniteOrNull(row.sma200) === null) return true;
  if (isEquityLike && toFiniteOrNull(row.marketCap) === null) return true;
  if (isEtfLike && toFiniteOrNull(row.marketCap) === null && toFiniteOrNull(row.totalAssets) === null) return true;

  return false;
}

function looksLikeIncompleteCachedQuote(row, minNonMetaFields) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return true;
  if (nonMetaFieldCount(row) < minNonMetaFields) return true;
  if (looksLikeMissingProfile(row)) return true;
  if (looksLikeMissingCoreMetrics(row)) return true;
  return false;
}

function normalizeProfileRow(row, runId, seededAtUtc, sourceTable) {
  let profile = {};
  const raw = row?.profile_json;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    profile = { ...raw };
  } else if (typeof raw === "string" && raw.trim()) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        profile = { ...parsed };
      }
    } catch {
      profile = {};
    }
  }

  if (!toTextOrNull(profile.assetType) && toTextOrNull(row.asset_type)) profile.assetType = row.asset_type;
  if (!toTextOrNull(profile.quoteType) && toTextOrNull(row.quote_type)) profile.quoteType = row.quote_type;
  if (!toTextOrNull(profile.exchange) && toTextOrNull(row.exchange)) profile.exchange = row.exchange;
  if (!toTextOrNull(profile.companyName) && toTextOrNull(row.company_name)) profile.companyName = row.company_name;
  if (!toTextOrNull(profile.sector) && toTextOrNull(row.sector)) profile.sector = row.sector;
  if (!toTextOrNull(profile.industry) && toTextOrNull(row.industry)) profile.industry = row.industry;
  if (!toTextOrNull(profile.country) && toTextOrNull(row.country)) profile.country = row.country;
  if (toFiniteOrNull(profile.marketCap) === null && toFiniteOrNull(row.market_cap) !== null) profile.marketCap = Number(row.market_cap);
  if (toFiniteOrNull(profile.sharesOutstanding) === null && toFiniteOrNull(row.shares_outstanding) !== null) {
    profile.sharesOutstanding = Number(row.shares_outstanding);
  }
  if (toFiniteOrNull(profile.sharesFloat) === null && toFiniteOrNull(row.float_shares) !== null) {
    profile.sharesFloat = Number(row.float_shares);
  }
  if (!toTextOrNull(profile.__seedSource)) profile.__seedSource = sourceTable;
  profile.__seedRunId = runId;
  if (!toTextOrNull(profile.__updatedAtUtc)) profile.__updatedAtUtc = seededAtUtc;
  return profile;
}

async function readValidatedSeedRun(client) {
  const result = await client.query(
    `
      SELECT
        run_id,
        completed_at,
        report_generated_at_utc,
        validation_status,
        report_status,
        snapshot_publication_id,
        quote_publication_id,
        quote_binding_status,
        COALESCE(is_active_publication, FALSE) AS is_active_publication
      FROM runtime_refresh_runs
      WHERE LOWER(COALESCE(validation_status, '')) = 'pass'
        AND NULLIF(TRIM(COALESCE(snapshot_publication_id, '')), '') IS NOT NULL
        AND NULLIF(TRIM(COALESCE(quote_publication_id, '')), '') IS NOT NULL
        AND LOWER(COALESCE(quote_binding_status, '')) = 'aligned'
      ORDER BY COALESCE(is_active_publication, FALSE) DESC,
               completed_at DESC NULLS LAST,
               updated_at DESC NULLS LAST
      LIMIT 1
    `,
  );
  return result.rows[0] ?? null;
}

async function readRecoverySeedRuns(client, limit) {
  const safeLimit = Math.max(1, Math.floor(limit));
  const result = await client.query(
    `
      SELECT
        run_id,
        completed_at,
        report_generated_at_utc,
        validation_status,
        report_status,
        snapshot_publication_id,
        quote_publication_id,
        quote_binding_status,
        COALESCE(is_active_publication, FALSE) AS is_active_publication
      FROM runtime_refresh_runs
      WHERE NULLIF(TRIM(COALESCE(snapshot_publication_id, '')), '') IS NOT NULL
        AND NULLIF(TRIM(COALESCE(quote_publication_id, '')), '') IS NOT NULL
        AND LOWER(COALESCE(quote_binding_status, '')) = 'aligned'
        AND LOWER(COALESCE(validation_status, '')) <> 'pass'
      ORDER BY completed_at DESC NULLS LAST,
               updated_at DESC NULLS LAST
      LIMIT $1
    `,
    [safeLimit],
  );
  return result.rows;
}

async function readSeedRows(client, runId) {
  const historyResult = await client.query(
    `
      SELECT
        ticker,
        asset_type,
        quote_type,
        exchange,
        company_name,
        sector,
        industry,
        country,
        market_cap,
        shares_outstanding,
        float_shares,
        profile_json
      FROM runtime_symbols_history
      WHERE run_id = $1
    `,
    [runId],
  );
  if (historyResult.rows.length > 0) {
    return {
      sourceTable: "runtime_symbols_history",
      rows: historyResult.rows,
    };
  }

  const latestResult = await client.query(
    `
      SELECT
        ticker,
        asset_type,
        quote_type,
        exchange,
        company_name,
        sector,
        industry,
        country,
        market_cap,
        shares_outstanding,
        float_shares,
        profile_json
      FROM runtime_symbols
      WHERE run_id = $1
    `,
    [runId],
  );
  return {
    sourceTable: "runtime_symbols",
    rows: latestResult.rows,
  };
}

function evaluateSeedCandidate(candidate, sourceTable, rowsRaw, minNonMetaFields, seededAtUtc) {
  const rows = {};
  let totalRows = 0;
  let completeRows = 0;
  let marketCapRows = 0;
  let priceRows = 0;

  for (const row of Array.isArray(rowsRaw) ? rowsRaw : []) {
    const ticker = String(row?.ticker ?? "").trim().toUpperCase();
    if (!ticker) continue;
    const profile = normalizeProfileRow(row, String(candidate.run_id), seededAtUtc, sourceTable);
    rows[ticker] = profile;
    totalRows += 1;
    if (toPositiveOrNull(profile.marketCap) !== null) marketCapRows += 1;
    if (toFiniteOrNull(profile.price) !== null) priceRows += 1;
    if (!looksLikeIncompleteCachedQuote(profile, minNonMetaFields)) completeRows += 1;
  }

  return {
    ...candidate,
    sourceTable,
    rows,
    totalRows,
    completeRows,
    incompleteRows: Math.max(0, totalRows - completeRows),
    marketCapRows,
    priceRows,
    completeRatio: totalRows > 0 ? completeRows / totalRows : 0,
  };
}

function compareSeedCandidates(left, right) {
  if (left.completeRows !== right.completeRows) return right.completeRows - left.completeRows;
  if (left.totalRows !== right.totalRows) return right.totalRows - left.totalRows;
  if (left.marketCapRows !== right.marketCapRows) return right.marketCapRows - left.marketCapRows;
  if (left.priceRows !== right.priceRows) return right.priceRows - left.priceRows;
  const completedGap = parseIsoMs(right.completed_at) - parseIsoMs(left.completed_at);
  if (completedGap !== 0) return completedGap;
  return parseIsoMs(right.report_generated_at_utc) - parseIsoMs(left.report_generated_at_utc);
}

async function chooseSeedCandidate(client, minNonMetaFields, seededAtUtc) {
  const validated = await readValidatedSeedRun(client);
  if (validated?.run_id) {
    const seeded = await readSeedRows(client, String(validated.run_id));
    const evaluated = evaluateSeedCandidate(validated, seeded.sourceTable, seeded.rows, minNonMetaFields, seededAtUtc);
    return {
      selected: evaluated,
      candidates: [evaluated],
      selectionMode: "validated_aligned_publication",
    };
  }

  const recoveryLimit = readPositiveIntEnv("TFE_QUOTE_CACHE_SEED_RECOVERY_CANDIDATE_LIMIT", DEFAULT_RECOVERY_CANDIDATE_LIMIT);
  const recoveryCandidates = await readRecoverySeedRuns(client, recoveryLimit);
  const evaluated = [];
  for (const candidate of recoveryCandidates) {
    const seeded = await readSeedRows(client, String(candidate.run_id));
    evaluated.push(evaluateSeedCandidate(candidate, seeded.sourceTable, seeded.rows, minNonMetaFields, seededAtUtc));
  }

  evaluated.sort(compareSeedCandidates);
  const selected = evaluated[0] ?? null;
  return {
    selected,
    candidates: evaluated,
    selectionMode: "aligned_historical_recovery",
  };
}

function summarizeCandidate(candidate) {
  if (!candidate) return null;
  return {
    run_id: String(candidate.run_id ?? ""),
    validation_status: toTextOrNull(candidate.validation_status),
    report_status: toTextOrNull(candidate.report_status),
    source_table: toTextOrNull(candidate.sourceTable),
    total_rows: Number(candidate.totalRows ?? 0),
    complete_rows: Number(candidate.completeRows ?? 0),
    incomplete_rows: Number(candidate.incompleteRows ?? 0),
    market_cap_rows: Number(candidate.marketCapRows ?? 0),
    price_rows: Number(candidate.priceRows ?? 0),
    complete_ratio: Number(candidate.completeRatio ?? 0),
    completed_at: candidate.completed_at ? new Date(candidate.completed_at).toISOString() : null,
    report_generated_at_utc: candidate.report_generated_at_utc
      ? new Date(candidate.report_generated_at_utc).toISOString()
      : null,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const root = resolveWorkspaceRoot();
  const outputPath = path.resolve(args.output || path.join(root, "web", "data", "screener-quote-cache.json"));
  const seededAtUtc = new Date().toISOString();
  const minNonMetaFields = readPositiveIntEnv("TFE_QUOTE_CACHE_MIN_NON_META_FIELDS", DEFAULT_MIN_NON_META_FIELDS);

  const pool = resolvePool();
  const client = await pool.connect();
  try {
    const selection = await chooseSeedCandidate(client, minNonMetaFields, seededAtUtc);
    const selected = selection.selected;
    console.log(
      JSON.stringify(
        {
          status: "seed_candidate_scan",
          selection_mode: selection.selectionMode,
          min_non_meta_fields: minNonMetaFields,
          candidates: selection.candidates.map(summarizeCandidate),
          selected: summarizeCandidate(selected),
        },
        null,
        2,
      ),
    );

    if (!selected?.run_id) {
      throw new Error("No aligned runtime publication or aligned historical recovery candidate exists for quote-cache seed.");
    }
    if (selected.totalRows < args.minRows) {
      throw new Error(
        `Runtime quote-cache seed row count is below minimum. rows=${selected.totalRows}; min_rows=${args.minRows}; run_id=${selected.run_id}`,
      );
    }
    if (selected.completeRows < args.minRows) {
      throw new Error(
        `Runtime quote-cache seed complete row count is below minimum. complete_rows=${selected.completeRows}; min_rows=${args.minRows}; run_id=${selected.run_id}`,
      );
    }

    const payload = {
      generated_at_utc: seededAtUtc,
      source_snapshot: path.join(root, "uf_snapshot.json"),
      symbols_total: Object.keys(selected.rows).length,
      symbols_cached: Object.keys(selected.rows).length,
      worker_count: 0,
      seed_source: selection.selectionMode,
      seed_run_id: String(selected.run_id),
      seed_validation_status: toTextOrNull(selected.validation_status),
      seed_report_status: toTextOrNull(selected.report_status),
      seed_source_table: selected.sourceTable,
      seed_complete_rows: selected.completeRows,
      seed_total_rows: selected.totalRows,
      seed_min_non_meta_fields: minNonMetaFields,
      seed_report_generated_at_utc: selected.report_generated_at_utc
        ? new Date(selected.report_generated_at_utc).toISOString()
        : null,
      rows: selected.rows,
    };

    mkdirSync(path.dirname(outputPath), { recursive: true });
    writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");

    console.log(
      JSON.stringify(
        {
          status: "ok",
          output: outputPath,
          seed_source: payload.seed_source,
          seed_run_id: payload.seed_run_id,
          symbols_cached: payload.symbols_cached,
          seed_complete_rows: payload.seed_complete_rows,
          seed_total_rows: payload.seed_total_rows,
          seed_source_table: payload.seed_source_table,
        },
        null,
        2,
      ),
    );
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(
    JSON.stringify(
      {
        status: "fail",
        error: message,
      },
      null,
      2,
    ),
  );
  process.exit(1);
});
