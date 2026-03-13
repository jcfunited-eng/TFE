import { Pool } from "pg";

const ADMIN_REFRESH_PERSIST_TABLE = "tfe_admin_refresh_persist";
const DEFAULT_DB_PORT = 5432;
const MAX_KEY_LENGTH = 96;
export const ADMIN_REFRESH_TEXT_SNAPSHOT_MAX_CHARS = 2_000_000;

export const ADMIN_REFRESH_PERSIST_KEYS = {
  statusRecord: "status_record_v1",
  logSnapshot: "log_snapshot_v1",
  historySnapshot: "history_snapshot_v1",
} as const;

let postgresPool: Pool | null = null;
let postgresInitPromise: Promise<void> | null = null;

type PersistRow = {
  payload: unknown;
};

function readRequiredEnv(...names: string[]): string {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function isPostgresConfigured(): boolean {
  const host = String(process.env.PGHOST ?? process.env.TFE_DB_HOST ?? "").trim();
  const database = String(process.env.PGDATABASE ?? process.env.TFE_DB_NAME ?? "").trim();
  const user = String(process.env.PGUSER ?? process.env.TFE_DB_USER ?? "").trim();
  const password = String(process.env.PGPASSWORD ?? process.env.TFE_DB_PASSWORD ?? "").trim();
  return Boolean(host && database && user && password);
}

function readPgPort(): number {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DB_PORT;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

function resolvePgSslRejectUnauthorized(): boolean {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

function resolvePostgresPool(): Pool {
  if (postgresPool) return postgresPool;

  const host = readRequiredEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readPgPort();
  const rejectUnauthorized = resolvePgSslRejectUnauthorized();

  postgresPool = new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 4,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-web-admin-refresh-persist",
  });

  return postgresPool;
}

async function ensurePostgresInitialized(): Promise<void> {
  if (postgresInitPromise) {
    await postgresInitPromise;
    return;
  }

  const pool = resolvePostgresPool();
  postgresInitPromise = (async () => {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS ${ADMIN_REFRESH_PERSIST_TABLE} (
        key VARCHAR(96) PRIMARY KEY,
        payload JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
  })();

  try {
    await postgresInitPromise;
  } catch (error) {
    postgresInitPromise = null;
    throw error;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeKey(raw: string): string | null {
  const key = String(raw ?? "").trim();
  if (!key) return null;
  if (key.length > MAX_KEY_LENGTH) return null;
  return key;
}

export function clampRefreshTextSnapshot(text: string): string {
  if (text.length <= ADMIN_REFRESH_TEXT_SNAPSHOT_MAX_CHARS) return text;
  return text.slice(text.length - ADMIN_REFRESH_TEXT_SNAPSHOT_MAX_CHARS);
}

export async function writeAdminRefreshPersist(keyInput: string, payload: Record<string, unknown>): Promise<void> {
  const key = normalizeKey(keyInput);
  if (!key) return;
  if (!isPostgresConfigured()) return;

  try {
    await ensurePostgresInitialized();
    const pool = resolvePostgresPool();
    await pool.query(
      `
        INSERT INTO ${ADMIN_REFRESH_PERSIST_TABLE} (key, payload, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (key)
        DO UPDATE SET
          payload = EXCLUDED.payload,
          updated_at = NOW()
      `,
      [key, JSON.stringify(payload)],
    );
  } catch {
    // Persistence must never block refresh operations.
  }
}

export async function readAdminRefreshPersist(keyInput: string): Promise<Record<string, unknown> | null> {
  const key = normalizeKey(keyInput);
  if (!key) return null;
  if (!isPostgresConfigured()) return null;

  try {
    await ensurePostgresInitialized();
    const pool = resolvePostgresPool();
    const result = await pool.query<PersistRow>(
      `
        SELECT payload
        FROM ${ADMIN_REFRESH_PERSIST_TABLE}
        WHERE key = $1
        LIMIT 1
      `,
      [key],
    );
    if (result.rows.length === 0) return null;
    return asRecord(result.rows[0]?.payload);
  } catch {
    return null;
  }
}

export async function appendAdminRefreshHistorySnapshotLine(entry: Record<string, unknown>, pathHint: string): Promise<void> {
  const existing = await readAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.historySnapshot);
  const existingRaw = typeof existing?.raw_text === "string" ? existing.raw_text : "";
  const nextRaw = clampRefreshTextSnapshot(`${existingRaw}${JSON.stringify(entry)}\n`);
  const nextPath = typeof existing?.path === "string" && existing.path.trim() ? existing.path : pathHint;
  await writeAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.historySnapshot, {
    path: nextPath,
    raw_text: nextRaw,
    updated_at_utc: nowIso(),
  });
}
