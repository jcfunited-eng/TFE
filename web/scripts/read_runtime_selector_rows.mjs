import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const RUNS_TABLE = "runtime_refresh_runs";
const DECISIONS_TABLE = "runtime_decisions_latest";
const DECISIONS_HISTORY_TABLE = "runtime_decisions_history";
const STEP1_ACTIVE_PUBLICATION_POINTER_TABLE = "active_publication_pointer";
const STEP1_PUBLICATION_BUNDLES_TABLE = "publication_bundles";
const STEP1_ACTIVE_POINTER_SOURCE_ENV = "TFE_STEP1_ACTIVE_POINTER_SOURCE";
const STEP1_FILE_PROOF_STORE_PATH_ENV = "TFE_STEP1_FILE_PROOF_STORE_PATH";
const STEP1_TARGET_ENVIRONMENT_ENV = "TFE_STEP1_TARGET_ENVIRONMENT";
const MODULE_FILE_PATH = fileURLToPath(import.meta.url);

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}`);
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

function toTextOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function toIsoOrNull(value) {
  if (value instanceof Date) return value.toISOString();
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function normalizeSqlIdentifier(value) {
  const text = String(value ?? "").trim();
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(text)) {
    throw new Error(`invalid_sql_identifier:${text || "empty"}`);
  }
  return text;
}

function normalizeColumnNames(columnNames) {
  const names = new Set();
  if (!columnNames || typeof columnNames[Symbol.iterator] !== "function") {
    return names;
  }
  for (const columnName of columnNames) {
    const normalized = String(columnName ?? "").trim();
    if (normalized) {
      names.add(normalized);
    }
  }
  return names;
}

export function buildSelectorQuery(tableName, columnNames) {
  const safeTableName = normalizeSqlIdentifier(tableName);
  const availableColumns = normalizeColumnNames(columnNames);
  const selectParts = [
    "snapshot_row_json",
    "ticker",
    availableColumns.has("bar_count") ? "bar_count" : "NULL::integer AS bar_count",
    availableColumns.has("regime") ? "regime" : "NULL::text AS regime",
  ];
  return `
    SELECT ${selectParts.join(", ")}
    FROM ${safeTableName}
    WHERE run_id = $1
    ORDER BY ticker ASC
  `;
}

async function tableExists(pool, tableName) {
  const result = await pool.query(
    `
      SELECT to_regclass($1) AS oid
    `,
    [tableName],
  );
  return String(result.rows[0]?.oid ?? "").trim().length > 0;
}

async function loadTableColumns(pool, tableName) {
  const result = await pool.query(
    `
      SELECT a.attname AS column_name
      FROM pg_attribute AS a
      WHERE a.attrelid = to_regclass($1)
        AND a.attnum > 0
        AND NOT a.attisdropped
      ORDER BY a.attnum ASC
    `,
    [tableName],
  );
  return normalizeColumnNames(result.rows.map((row) => row.column_name));
}

async function loadActivePublication(pool) {
  const result = await pool.query(
    `
      SELECT
        run_id,
        validation_status,
        snapshot_publication_id,
        quote_publication_id,
        quote_binding_status,
        COALESCE(bundle_generated_at_utc, completed_at, report_generated_at_utc) AS generated_at_utc
      FROM ${RUNS_TABLE}
      WHERE is_active_publication IS TRUE
      ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST
      LIMIT 1
    `,
  );
  return result.rows[0] ?? null;
}

function activePublicationIsValid(row) {
  if (!row) return false;
  if (String(row.validation_status ?? "").trim().toLowerCase() !== "pass") return false;
  if (!toTextOrNull(row.snapshot_publication_id)) return false;
  if (!toTextOrNull(row.quote_publication_id)) return false;
  if (String(row.quote_binding_status ?? "").trim().toLowerCase() !== "aligned") return false;
  return Boolean(toTextOrNull(row.run_id));
}

async function loadLatestRuntimeRunId(pool) {
  const result = await pool.query(
    `
      SELECT run_id, generated_at_utc
      FROM ${DECISIONS_TABLE}
      ORDER BY generated_at_utc DESC NULLS LAST, ticker ASC
      LIMIT 1
    `,
  );
  return {
    runId: toTextOrNull(result.rows[0]?.run_id),
    generatedAtUtc: toIsoOrNull(result.rows[0]?.generated_at_utc),
  };
}

function parseArgs(argv) {
  return {
    activePointerOnly: argv.some((arg) => String(arg ?? "").trim() === "--active-pointer-only"),
  };
}

function step1TargetEnvironment() {
  return String(process.env[STEP1_TARGET_ENVIRONMENT_ENV] ?? "production").trim() || "production";
}

function step1FileProofStorePath() {
  const value = String(process.env[STEP1_FILE_PROOF_STORE_PATH_ENV] ?? "").trim();
  return value || null;
}

function step1ActivePointerSourceEnabled() {
  return String(process.env[STEP1_ACTIVE_POINTER_SOURCE_ENV] ?? "").trim().toLowerCase() === "cutover";
}

function loadActivePublicationPointerFromProofStore(targetEnvironment) {
  const storePath = step1FileProofStorePath();
  if (!storePath) {
    throw new Error("active_publication_pointer_proof_store_missing");
  }

  const parsed = JSON.parse(readFileSync(storePath, "utf8"));
  const pointerRows = Array.isArray(parsed?.active_publication_pointer) ? parsed.active_publication_pointer : [];
  const bundleRows = Array.isArray(parsed?.publication_bundles) ? parsed.publication_bundles : [];
  const pointerRow = pointerRows.find(
    (row) => String(row?.target_environment ?? "").trim() === targetEnvironment,
  );
  if (!pointerRow) {
    throw new Error(`active_publication_pointer_missing:${targetEnvironment}`);
  }
  const publicationBundleId = toTextOrNull(pointerRow.publication_bundle_id);
  const runId = toTextOrNull(pointerRow.run_id);
  if (!publicationBundleId || !runId) {
    throw new Error(`active_publication_pointer_invalid:${targetEnvironment}`);
  }
  const bundleRow = bundleRows.find(
    (row) => String(row?.publication_bundle_id ?? "").trim() === publicationBundleId,
  );
  if (!bundleRow) {
    throw new Error(`publication_bundle_missing:${publicationBundleId}`);
  }
  return {
    publicationBundleId,
    runId,
    targetEnvironment,
    source: "active_publication_pointer",
  };
}

async function loadActivePublicationPointerFromPostgres(pool, targetEnvironment) {
  const [pointerTableExists, bundleTableExists] = await Promise.all([
    tableExists(pool, STEP1_ACTIVE_PUBLICATION_POINTER_TABLE),
    tableExists(pool, STEP1_PUBLICATION_BUNDLES_TABLE),
  ]);
  if (!pointerTableExists || !bundleTableExists) {
    throw new Error("step1_pointer_tables_missing");
  }

  const result = await pool.query(
    `
      SELECT
        p.publication_bundle_id,
        p.run_id,
        p.target_environment
      FROM ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE} AS p
      INNER JOIN ${STEP1_PUBLICATION_BUNDLES_TABLE} AS b
        ON b.publication_bundle_id = p.publication_bundle_id
      WHERE p.target_environment = $1
      LIMIT 1
    `,
    [targetEnvironment],
  );
  const row = result.rows[0] ?? null;
  if (!row) {
    throw new Error(`active_publication_pointer_missing:${targetEnvironment}`);
  }
  const publicationBundleId = toTextOrNull(row.publication_bundle_id);
  const runId = toTextOrNull(row.run_id);
  if (!publicationBundleId || !runId) {
    throw new Error(`active_publication_pointer_invalid:${targetEnvironment}`);
  }
  return {
    publicationBundleId,
    runId,
    targetEnvironment,
    source: "active_publication_pointer",
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const targetEnvironment = step1TargetEnvironment();

  if (args.activePointerOnly) {
    if (!step1ActivePointerSourceEnabled()) {
      throw new Error("step1_active_pointer_source_disabled");
    }

    if (step1FileProofStorePath()) {
      process.stdout.write(`${JSON.stringify({
        ok: true,
        ...loadActivePublicationPointerFromProofStore(targetEnvironment),
      })}\n`);
      return;
    }
  }

  const pool = new Pool({
    host: readRequiredEnv("PGHOST", "TFE_DB_HOST"),
    database: readRequiredEnv("PGDATABASE", "TFE_DB_NAME"),
    user: readRequiredEnv("PGUSER", "TFE_DB_USER"),
    password: readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD"),
    port: readPgPort(),
    max: 2,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized: resolvePgSslRejectUnauthorized() },
    application_name: "tfe-runtime-selector-rows",
  });

  try {
    if (args.activePointerOnly) {
      process.stdout.write(`${JSON.stringify({
        ok: true,
        ...(await loadActivePublicationPointerFromPostgres(pool, targetEnvironment)),
      })}\n`);
      return;
    }

    const runsTableExists = await tableExists(pool, RUNS_TABLE);
    if (!runsTableExists) {
      throw new Error(`table_missing:${RUNS_TABLE}`);
    }

    const activePublication = await loadActivePublication(pool);
    if (!activePublication) {
      throw new Error("active_publication_pointer_missing");
    }
    if (!activePublicationIsValid(activePublication)) {
      throw new Error("active_publication_pointer_invalid");
    }

    const selectedRunId = toTextOrNull(activePublication.run_id);
    if (!selectedRunId) {
      throw new Error("active_publication_run_id_missing");
    }

    const latestRuntime = await loadLatestRuntimeRunId(pool);
    const useHistoryTable = latestRuntime.runId !== null && latestRuntime.runId !== selectedRunId;
    const selectedTable = useHistoryTable ? DECISIONS_HISTORY_TABLE : DECISIONS_TABLE;

    if (useHistoryTable) {
      const historyExists = await tableExists(pool, selectedTable);
      if (!historyExists) {
        throw new Error(`history_table_missing:${selectedTable}`);
      }
    }

    const selectedTableColumns = await loadTableColumns(pool, selectedTable);
    if (selectedTableColumns.size === 0) {
      throw new Error(`table_columns_missing:${selectedTable}`);
    }

    const result = await pool.query(
      buildSelectorQuery(selectedTable, selectedTableColumns),
      [selectedRunId],
    );

    const rows = [];
    for (const record of result.rows) {
      const parsed = record.snapshot_row_json && typeof record.snapshot_row_json === "object"
        ? { ...record.snapshot_row_json }
        : {};
      const ticker = toTextOrNull(record.ticker);
      if (ticker && !parsed.ticker) parsed.ticker = ticker;
      if (record.regime && !parsed.regime) parsed.regime = record.regime;
      if (record.bar_count !== undefined && record.bar_count !== null && parsed.bar_count === undefined) {
        parsed.bar_count = record.bar_count;
      }
      if (Object.keys(parsed).length > 0) {
        rows.push(parsed);
      }
    }

    if (rows.length === 0) {
      throw new Error(`selector_rows_empty:${selectedTable}:${selectedRunId}`);
    }

    process.stdout.write(`${JSON.stringify({
      ok: true,
      run_id: selectedRunId,
      generated_at_utc: toIsoOrNull(activePublication.generated_at_utc) ?? latestRuntime.generatedAtUtc,
      source_table: selectedTable,
      row_count: rows.length,
      rows,
    })}\n`);
  } finally {
    await pool.end();
  }
}

function isDirectExecution() {
  const entryPath = String(process.argv[1] ?? "").trim();
  if (!entryPath) {
    return false;
  }
  return path.resolve(entryPath) === MODULE_FILE_PATH;
}

if (isDirectExecution()) {
  main().catch((error) => {
    const reason = error instanceof Error ? error.message : "runtime_selector_rows_failed";
    process.stderr.write(`${JSON.stringify({ ok: false, reason })}\n`);
    process.exit(1);
  });
}
