import { promises as fs } from "node:fs";
import path from "node:path";
import { Pool } from "pg";

import {
  buildSesActorId,
  buildSesAssetId,
  decryptEnvelopeObjectToJson,
  decryptEnvelopeToJson,
  encryptJsonToEnvelope,
  encryptJsonToEnvelopeObject,
} from "@/lib/ses-web-blob";
import { resolveSharedStorageBackend } from "@/lib/user-storage-backend";

const WATCHLIST_FILE_LEGACY = "watchlist.csv";
const WATCHLIST_FILE_SES = "watchlist.ses.json";
const USER_DATA_ROOT_NAME = "web_user_data";
const PRIVATE_FILE_MODE = 0o600;
const WATCHLIST_TABLE_NAME = "tfe_watchlists";

type UserDataBackend = "file" | "postgres";

// ses_envelope holds the SES-encrypted ciphertext of the watchlist symbols.
// symbols is retained for schema compatibility and migration; it is cleared
// to ARRAY[]::TEXT[] on the first SES write and must not be read as
// authoritative once ses_envelope is present.
type PostgresWatchlistRow = {
  symbols: string[] | null;
  ses_envelope: unknown;
};

let postgresPool: Pool | null = null;
let postgresInitPromise: Promise<void> | null = null;

function sanitizeUsernameForPath(username: string): string {
  const value = String(username ?? "")
    .trim()
    .toLowerCase();

  const sanitized = value.replace(/[^a-z0-9._-]/g, "_");
  return sanitized || "unknown_user";
}

function normalizeUsername(username: string): string {
  return String(username ?? "").trim().toLowerCase();
}

function userRootCandidates(): string[] {
  const cwd = process.cwd();
  const primary = path.basename(cwd) === "web" ? path.resolve(cwd, "..", USER_DATA_ROOT_NAME) : path.resolve(cwd, USER_DATA_ROOT_NAME);
  return [
    primary,
    path.resolve(cwd, USER_DATA_ROOT_NAME),
    path.resolve(cwd, "..", USER_DATA_ROOT_NAME),
    path.resolve("/workspaces/Tao_Financial_Engine", USER_DATA_ROOT_NAME),
  ];
}

async function resolveUserRootPath(): Promise<string> {
  const candidates = userRootCandidates();

  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // keep checking
    }
  }

  return candidates[0];
}

async function resolveWatchlistPaths(username: string): Promise<{
  userDir: string;
  sesPath: string;
  legacyPath: string;
}> {
  const root = await resolveUserRootPath();
  const userDir = path.join(root, sanitizeUsernameForPath(username));
  await fs.mkdir(userDir, { recursive: true });

  return {
    userDir,
    sesPath: path.join(userDir, WATCHLIST_FILE_SES),
    legacyPath: path.join(userDir, WATCHLIST_FILE_LEGACY),
  };
}

async function writePrivateTextFile(filePath: string, text: string): Promise<void> {
  await fs.writeFile(filePath, text, { mode: PRIVATE_FILE_MODE });
  try {
    await fs.chmod(filePath, PRIVATE_FILE_MODE);
  } catch {
    // Best-effort on restricted filesystems.
  }
}

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
}

function watchlistPurposeSuffix(username: string): string {
  return `watchlist-${sanitizeUsernameForPath(username)}`;
}

function watchlistLegacyPurposeSuffix(): string {
  return "watchlist";
}

function uniqueSymbols(symbols: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];

  for (const raw of symbols) {
    const symbol = normalizeSymbol(raw);
    if (!symbol) continue;
    if (seen.has(symbol)) continue;
    seen.add(symbol);
    out.push(symbol);
  }

  return out;
}

function parseWatchlistCsv(text: string): string[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) return [];

  const header = lines[0].toLowerCase();
  const symbolIndex = header.split(",").findIndex((col) => {
    const c = col.trim();
    return c === "symbol" || c === "ticker";
  });

  if (symbolIndex < 0) return [];

  const symbols = lines.slice(1).map((line) => {
    const cols = line.split(",");
    return cols[symbolIndex] ?? "";
  });

  return uniqueSymbols(symbols);
}

function toWatchlistCsv(symbols: string[]): string {
  const rows = uniqueSymbols(symbols).map((symbol) => symbol);
  return ["symbol", ...rows].join("\n") + "\n";
}

function sanitizeEncryptedPayload(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];

  const obj = payload as { symbols?: unknown };
  if (!Array.isArray(obj.symbols)) return [];

  return uniqueSymbols(obj.symbols.map((value) => String(value ?? "")));
}

async function removeLegacyFile(filePath: string): Promise<void> {
  try {
    await fs.unlink(filePath);
  } catch {
    // Ignore cleanup failures.
  }
}

async function readLegacyWatchlist(filePath: string): Promise<string[] | null> {
  try {
    const text = await fs.readFile(filePath, "utf-8");
    try {
      await fs.chmod(filePath, PRIVATE_FILE_MODE);
    } catch {
      // Best-effort only.
    }

    return parseWatchlistCsv(text);
  } catch {
    return null;
  }
}

async function saveSesWatchlist(username: string, symbols: string[], sesPath: string, legacyPath: string): Promise<void> {
  const clean = uniqueSymbols(symbols);

  await encryptJsonToEnvelope({
    value: { symbols: clean },
    envelopePath: sesPath,
    purposeSuffix: watchlistPurposeSuffix(username),
    actorId: buildSesActorId(username),
    assetId: buildSesAssetId("watchlist", username),
  });

  try {
    await fs.chmod(sesPath, PRIVATE_FILE_MODE);
  } catch {
    // Best-effort only.
  }

  await removeLegacyFile(legacyPath);
}

function resolveUserDataBackend(): UserDataBackend {
  return resolveSharedStorageBackend();
}

function readRequiredEnv(name: string, fallbackName?: string): string {
  const direct = String(process.env[name] ?? "").trim();
  if (direct) return direct;

  if (fallbackName) {
    const fallback = String(process.env[fallbackName] ?? "").trim();
    if (fallback) return fallback;
  }

  throw new Error(`${name} is required when TFE_USER_DATA_BACKEND resolves to postgres.`);
}

function readPgPort(): number {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? "5432").trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    throw new Error("PGPORT must be a valid number.");
  }

  const whole = Math.floor(parsed);
  if (!(whole > 0 && whole <= 65535)) {
    throw new Error("PGPORT must be between 1 and 65535.");
  }

  return whole;
}

function resolvePgSslRejectUnauthorized(): boolean {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  throw new Error("TFE_DB_SSL_REJECT_UNAUTHORIZED must be true or false.");
}

function postgresSourcePath(): string {
  const host = String(process.env.PGHOST ?? process.env.TFE_DB_HOST ?? "").trim() || "<unset-host>";
  const port = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? "5432").trim() || "5432";
  const database = String(process.env.PGDATABASE ?? process.env.TFE_DB_NAME ?? "").trim() || "<unset-db>";
  return `postgres://${host}:${port}/${database}#${WATCHLIST_TABLE_NAME}`;
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
    max: 10,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-web-watchlist-store",
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
    // Create table with ses_envelope column for SES-encrypted data.
    // symbols column is kept for schema compatibility and migration; it is
    // cleared to ARRAY[]::TEXT[] on the first SES write.
    await pool.query(`
      CREATE TABLE IF NOT EXISTS ${WATCHLIST_TABLE_NAME} (
        username     VARCHAR(64)  PRIMARY KEY,
        symbols      TEXT[]       NOT NULL DEFAULT ARRAY[]::TEXT[],
        ses_envelope JSONB        NULL,
        updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
      )
    `);

    // Idempotent column addition for tables created before SES was introduced.
    await pool.query(`
      ALTER TABLE ${WATCHLIST_TABLE_NAME}
      ADD COLUMN IF NOT EXISTS ses_envelope JSONB NULL
    `);
  })();

  try {
    await postgresInitPromise;
  } catch (error) {
    postgresInitPromise = null;
    throw error;
  }
}

// ── Postgres read ─────────────────────────────────────────────────────────────
//
// Priority:
//   1. Decrypt ses_envelope if present  — authoritative, SES-protected
//   2. Migrate plaintext symbols to SES — one-time migration on first read
//   3. Return null (caller bootstraps)

async function readWatchlistPostgres(username: string): Promise<string[] | null> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();
  const normalizedUsername = normalizeUsername(username);

  const result = await pool.query<PostgresWatchlistRow>(
    `
      SELECT symbols, ses_envelope
      FROM ${WATCHLIST_TABLE_NAME}
      WHERE username = $1
      LIMIT 1
    `,
    [normalizedUsername],
  );

  if (result.rows.length === 0) return null;

  const row = result.rows[0];

  // Path 1: SES envelope present — decrypt it.
  if (row.ses_envelope !== null && row.ses_envelope !== undefined && typeof row.ses_envelope === "object") {
    const envelope = row.ses_envelope as Record<string, unknown>;
    const payload = await decryptEnvelopeObjectToJson<{ symbols?: unknown }>({
      envelope,
      purposeSuffix: watchlistPurposeSuffix(username),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("watchlist", username),
    });
    return sanitizeEncryptedPayload(payload);
  }

  // Path 2: No envelope yet — plaintext symbols exist from before SES was
  // introduced. Encrypt them now and clear the plaintext column.
  const plaintextSymbols = Array.isArray(row.symbols)
    ? uniqueSymbols(row.symbols.map((v) => String(v ?? "")))
    : [];
  await writeWatchlistPostgres(username, plaintextSymbols);
  return plaintextSymbols;
}

// ── Postgres write ────────────────────────────────────────────────────────────
//
// Always encrypts via SES before writing. The plaintext symbols column is
// explicitly cleared to ARRAY[]::TEXT[] so no unencrypted data persists.

async function writeWatchlistPostgres(username: string, symbols: string[]): Promise<string[]> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();
  const normalizedUsername = normalizeUsername(username);
  const clean = uniqueSymbols(symbols);

  const envelope = await encryptJsonToEnvelopeObject({
    value: { symbols: clean },
    purposeSuffix: watchlistPurposeSuffix(username),
    actorId: buildSesActorId(username),
    assetId: buildSesAssetId("watchlist", username),
  });

  await pool.query(
    `
      INSERT INTO ${WATCHLIST_TABLE_NAME} (username, symbols, ses_envelope, updated_at)
      VALUES ($1, ARRAY[]::TEXT[], $2::jsonb, NOW())
      ON CONFLICT (username)
      DO UPDATE SET
        symbols      = ARRAY[]::TEXT[],
        ses_envelope = EXCLUDED.ses_envelope,
        updated_at   = NOW()
    `,
    [normalizedUsername, JSON.stringify(envelope)],
  );

  return clean;
}

// ── File backend read/write ───────────────────────────────────────────────────

async function tryLoadWatchlistFromFiles(username: string): Promise<string[] | null> {
  const paths = await resolveWatchlistPaths(username);

  try {
    const payload = await decryptEnvelopeToJson<{ symbols?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: watchlistPurposeSuffix(username),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("watchlist", username),
    });

    return sanitizeEncryptedPayload(payload);
  } catch {
    // fall through
  }

  try {
    const payload = await decryptEnvelopeToJson<{ symbols?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: watchlistLegacyPurposeSuffix(),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("watchlist", username),
    });

    return sanitizeEncryptedPayload(payload);
  } catch {
    // fall through
  }

  const legacySymbols = await readLegacyWatchlist(paths.legacyPath);
  if (legacySymbols) {
    return legacySymbols;
  }

  return null;
}

async function loadWatchlistSymbolsFromFileBackend(username: string): Promise<{ symbols: string[]; filePath: string }> {
  const paths = await resolveWatchlistPaths(username);

  try {
    const payload = await decryptEnvelopeToJson<{ symbols?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: watchlistPurposeSuffix(username),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("watchlist", username),
    });

    const symbols = sanitizeEncryptedPayload(payload);
    return { symbols, filePath: paths.sesPath };
  } catch {
    // Fall through to legacy envelope and plaintext migration paths.
  }

  try {
    const payload = await decryptEnvelopeToJson<{ symbols?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: watchlistLegacyPurposeSuffix(),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("watchlist", username),
    });

    const symbols = sanitizeEncryptedPayload(payload);
    await saveSesWatchlist(username, symbols, paths.sesPath, paths.legacyPath);
    return { symbols, filePath: paths.sesPath };
  } catch {
    // Fall through to plaintext migration path.
  }

  const legacySymbols = await readLegacyWatchlist(paths.legacyPath);
  if (legacySymbols) {
    await saveSesWatchlist(username, legacySymbols, paths.sesPath, paths.legacyPath);
    return { symbols: legacySymbols, filePath: paths.sesPath };
  }

  await saveSesWatchlist(username, [], paths.sesPath, paths.legacyPath);
  return { symbols: [], filePath: paths.sesPath };
}

async function saveWatchlistSymbolsToFileBackend(username: string, symbols: string[]): Promise<{ symbols: string[]; filePath: string }> {
  const paths = await resolveWatchlistPaths(username);
  const clean = uniqueSymbols(symbols);

  await saveSesWatchlist(username, clean, paths.sesPath, paths.legacyPath);

  return { symbols: clean, filePath: paths.sesPath };
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function loadWatchlistSymbols(username: string): Promise<{ symbols: string[]; filePath: string }> {
  const backend = resolveUserDataBackend();

  if (backend === "postgres") {
    const fromDb = await readWatchlistPostgres(username);
    if (fromDb !== null) {
      return { symbols: fromDb, filePath: postgresSourcePath() };
    }

    // No row yet — migrate from files if available, then bootstrap encrypted.
    const migrated = await tryLoadWatchlistFromFiles(username);
    const initial = uniqueSymbols(migrated ?? []);
    await writeWatchlistPostgres(username, initial);
    return { symbols: initial, filePath: postgresSourcePath() };
  }

  return loadWatchlistSymbolsFromFileBackend(username);
}

export async function saveWatchlistSymbols(username: string, symbols: string[]): Promise<{ symbols: string[]; filePath: string }> {
  const backend = resolveUserDataBackend();

  if (backend === "postgres") {
    const clean = await writeWatchlistPostgres(username, symbols);
    return { symbols: clean, filePath: postgresSourcePath() };
  }

  return saveWatchlistSymbolsToFileBackend(username, symbols);
}

export async function exportWatchlistCsv(username: string): Promise<{ csv: string; filePath: string }> {
  const result = await loadWatchlistSymbols(username);
  const csv = toWatchlistCsv(result.symbols);

  const paths = await resolveWatchlistPaths(username);
  await writePrivateTextFile(paths.legacyPath, csv);

  return { csv, filePath: paths.legacyPath };
}
