import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const RUNS_TABLE = "runtime_refresh_runs";
const DECISIONS_TABLE = "runtime_decisions_latest";
const DECISIONS_HISTORY_TABLE = "runtime_decisions_history";

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

async function tableExists(pool, tableName) {
  const result = await pool.query(
    `
      SELECT to_regclass($1) AS oid
    `,
    [tableName],
  );
  return String(result.rows[0]?.oid ?? "").trim().length > 0;
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

async function main() {
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

    const result = await pool.query(
      `
        SELECT snapshot_row_json, ticker, bar_count, regime
        FROM ${selectedTable}
        WHERE run_id = $1
        ORDER BY ticker ASC
      `,
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

main().catch((error) => {
  const reason = error instanceof Error ? error.message : "runtime_selector_rows_failed";
  process.stderr.write(`${JSON.stringify({ ok: false, reason })}\n`);
  process.exit(1);
});
