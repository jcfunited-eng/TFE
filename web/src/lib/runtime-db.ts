import { Pool } from "pg";

export type AttemptFailure = {
  path: string;
  reason: string;
};

export const DEFAULT_DB_PORT = 5432;
export const RUNTIME_REFRESH_RUNS_TABLE = "runtime_refresh_runs";
export const RUNTIME_DECISIONS_TABLE = "runtime_decisions_latest";
export const RUNTIME_DECISIONS_HISTORY_TABLE = "runtime_decisions_history";
export const RUNTIME_SYMBOLS_TABLE = "runtime_symbols";
export const RUNTIME_SYMBOLS_HISTORY_TABLE = "runtime_symbols_history";
export const RUNTIME_DECISION_PROVENANCE_TABLE = "runtime_decision_provenance_latest";

let runtimePool: Pool | null = null;

export function resolveRuntimeSource(): string {
  return String(process.env.TFE_RUNTIME_DATA_SOURCE ?? process.env.TFE_RUNTIME_SOURCE ?? "postgres")
    .trim()
    .toLowerCase();
}

export function runtimeSourceIsPostgres(): boolean {
  return resolveRuntimeSource() === "postgres";
}

export function readOptionalEnv(...names: string[]): string | null {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  return null;
}

export function readRequiredEnv(...names: string[]): string {
  const value = readOptionalEnv(...names);
  if (value) return value;
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

export function isPostgresConfigured(): boolean {
  return Boolean(readOptionalEnv("PGHOST", "TFE_DB_HOST"))
    && Boolean(readOptionalEnv("PGDATABASE", "TFE_DB_NAME"))
    && Boolean(readOptionalEnv("PGUSER", "TFE_DB_USER"))
    && Boolean(readOptionalEnv("PGPASSWORD", "TFE_DB_PASSWORD"));
}

export function readPgPort(): number {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DB_PORT;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

export function resolvePgSslRejectUnauthorized(): boolean {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

export function postgresSourceBase(): string {
  const host = readOptionalEnv("PGHOST", "TFE_DB_HOST") ?? "<unset-host>";
  const port = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim() || `${DEFAULT_DB_PORT}`;
  const database = readOptionalEnv("PGDATABASE", "TFE_DB_NAME") ?? "<unset-db>";
  return `postgres://${host}:${port}/${database}`;
}

export function postgresSourcePath(tableName: string): string {
  return `${postgresSourceBase()}#${tableName}`;
}

export function resolveRuntimePostgresPool(): Pool {
  if (runtimePool) return runtimePool;

  const host = readRequiredEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readPgPort();
  const rejectUnauthorized = resolvePgSslRejectUnauthorized();

  runtimePool = new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 8,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 60_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-runtime-shared",
  });

  return runtimePool;
}

export function toTextOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

export function toLowerTextOrNull(value: unknown): string | null {
  const text = toTextOrNull(value);
  return text ? text.toLowerCase() : null;
}

export function toIsoOrNull(value: unknown): string | null {
  if (value instanceof Date) return value.toISOString();
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

export function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export async function tableExists(pool: Pool, tableName: string): Promise<boolean> {
  const result = await pool.query<{ oid: string | null }>(
    `
      SELECT to_regclass($1) AS oid
    `,
    [tableName],
  );
  return String(result.rows[0]?.oid ?? "").trim().length > 0;
}

export async function columnExists(pool: Pool, tableName: string, columnName: string): Promise<boolean> {
  const result = await pool.query<{ exists: boolean }>(
    `
      SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = $1
          AND column_name = $2
      ) AS exists
    `,
    [tableName, columnName],
  );
  return Boolean(result.rows[0]?.exists);
}
