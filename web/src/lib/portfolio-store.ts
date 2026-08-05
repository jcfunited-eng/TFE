import { randomUUID } from "node:crypto";
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

export type PortfolioLot = {
  id: string;
  ticker: string;
  units: number;
  unitCost: number;
  addedAt: string;
  updatedAt: string;
};

const PORTFOLIO_FILE_LEGACY = "portfolio_manual.json";
const PORTFOLIO_FILE_SES = "portfolio_manual.ses.json";
const USER_DATA_ROOT_NAME = "web_user_data";
const PRIVATE_FILE_MODE = 0o600;
const PORTFOLIO_TABLE_NAME = "tfe_portfolio_manual";

type UserDataBackend = "file" | "postgres";

// ses_envelope holds the SES-encrypted ciphertext of the portfolio lots.
// lots is retained for schema compatibility only; it is cleared to '[]' on
// the first SES write and must never be read as authoritative once ses_envelope
// is present.
type PostgresPortfolioRow = {
  lots: unknown;
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

async function resolvePortfolioPaths(username: string): Promise<{
  sesPath: string;
  legacyPath: string;
}> {
  const root = await resolveUserRootPath();
  const userDir = path.join(root, sanitizeUsernameForPath(username));
  await fs.mkdir(userDir, { recursive: true });

  return {
    sesPath: path.join(userDir, PORTFOLIO_FILE_SES),
    legacyPath: path.join(userDir, PORTFOLIO_FILE_LEGACY),
  };
}

async function writePrivateTextFile(filePath: string, text: string): Promise<void> {
  await fs.writeFile(filePath, text, { mode: PRIVATE_FILE_MODE });
  try {
    await fs.chmod(filePath, PRIVATE_FILE_MODE);
  } catch {
    // Best-effort only on restricted filesystems.
  }
}

function toFinite(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function sanitizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function sanitizeIso(value: unknown, fallbackIso: string): string {
  const text = String(value ?? "").trim();
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return fallbackIso;
  return new Date(parsed).toISOString();
}

function portfolioPurposeSuffix(username: string): string {
  return `portfolio-manual-${sanitizeUsernameForPath(username)}`;
}

function portfolioLegacyPurposeSuffix(): string {
  return "portfolio-manual";
}

function sanitizeLot(raw: unknown): PortfolioLot | null {
  if (!raw || typeof raw !== "object") return null;

  const obj = raw as Record<string, unknown>;
  const ticker = sanitizeTicker(obj.ticker);
  const units = toFinite(obj.units, 0);
  const unitCost = toFinite(obj.unitCost, 0);
  const nowIso = new Date().toISOString();

  if (!ticker) return null;
  if (!(units > 0)) return null;
  if (!(unitCost >= 0)) return null;

  const idRaw = String(obj.id ?? "").trim();
  const id = idRaw || randomUUID();

  return {
    id,
    ticker,
    units,
    unitCost,
    addedAt: sanitizeIso(obj.addedAt, nowIso),
    updatedAt: sanitizeIso(obj.updatedAt, nowIso),
  };
}

function normalizeLots(rawLots: unknown): PortfolioLot[] {
  if (!Array.isArray(rawLots)) return [];

  const seen = new Set<string>();
  const lots: PortfolioLot[] = [];

  for (const raw of rawLots) {
    const lot = sanitizeLot(raw);
    if (!lot) continue;
    if (seen.has(lot.id)) continue;
    seen.add(lot.id);
    lots.push(lot);
  }

  lots.sort((a, b) => {
    if (a.addedAt !== b.addedAt) return a.addedAt.localeCompare(b.addedAt);
    return a.id.localeCompare(b.id);
  });

  return lots;
}

function parseLegacyPortfolioJson(raw: unknown): PortfolioLot[] {
  if (Array.isArray(raw)) {
    return normalizeLots(raw);
  }

  if (raw && typeof raw === "object") {
    const obj = raw as { lots?: unknown };
    if (Array.isArray(obj.lots)) {
      return normalizeLots(obj.lots);
    }
  }

  return [];
}

function parseEncryptedPayload(raw: unknown): PortfolioLot[] {
  if (!raw || typeof raw !== "object") return [];

  const obj = raw as { lots?: unknown };
  if (!Array.isArray(obj.lots)) return [];

  return normalizeLots(obj.lots);
}

async function removeLegacyFile(filePath: string): Promise<void> {
  try {
    await fs.unlink(filePath);
  } catch {
    // Ignore cleanup failures.
  }
}

async function readLegacyLots(filePath: string): Promise<PortfolioLot[] | null> {
  try {
    const text = await fs.readFile(filePath, "utf-8");
    try {
      await fs.chmod(filePath, PRIVATE_FILE_MODE);
    } catch {
      // Best-effort only.
    }

    const parsed = JSON.parse(text) as unknown;
    return parseLegacyPortfolioJson(parsed);
  } catch {
    return null;
  }
}

async function writeSesLots(username: string, lots: PortfolioLot[], sesPath: string, legacyPath: string): Promise<void> {
  const normalized = normalizeLots(lots);

  await encryptJsonToEnvelope({
    value: {
      lots: normalized,
      updatedAt: new Date().toISOString(),
    },
    envelopePath: sesPath,
    purposeSuffix: portfolioPurposeSuffix(username),
    actorId: buildSesActorId(username),
    assetId: buildSesAssetId("portfolio", username),
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
  return `postgres://${host}:${port}/${database}#${PORTFOLIO_TABLE_NAME}`;
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
    application_name: "tfe-web-portfolio-store",
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
    // lots column is kept for schema compatibility and migration; it is
    // cleared to '[]' on the first SES write and treated as stale thereafter.
    await pool.query(`
      CREATE TABLE IF NOT EXISTS ${PORTFOLIO_TABLE_NAME} (
        username     VARCHAR(64)  PRIMARY KEY,
        lots         JSONB        NOT NULL DEFAULT '[]'::jsonb,
        ses_envelope JSONB        NULL,
        updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
      )
    `);

    // Idempotent column addition for tables created before SES was introduced.
    await pool.query(`
      ALTER TABLE ${PORTFOLIO_TABLE_NAME}
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
//   2. Migrate plaintext lots to SES    — one-time migration on first read
//   3. Return empty and write encrypted — bootstraps a new user

async function readLotsPostgres(username: string): Promise<PortfolioLot[] | null> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();
  const normalizedUsername = normalizeUsername(username);

  const result = await pool.query<PostgresPortfolioRow>(
    `
      SELECT lots, ses_envelope
      FROM ${PORTFOLIO_TABLE_NAME}
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
    const payload = await decryptEnvelopeObjectToJson<{ lots?: unknown }>({
      envelope,
      purposeSuffix: portfolioPurposeSuffix(username),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("portfolio", username),
    });
    return normalizeLots(parseEncryptedPayload(payload));
  }

  // Path 2: No envelope yet — plaintext lots exist from before SES was
  // introduced. Encrypt them now and clear the plaintext column.
  const plaintextLots = normalizeLots(parseLegacyPortfolioJson(row.lots));
  await writeLotsPostgres(username, plaintextLots);
  return plaintextLots;
}

// ── Postgres write ────────────────────────────────────────────────────────────
//
// Always encrypts via SES before writing. The plaintext lots column is
// explicitly set to '[]' so no unencrypted data persists in the database.

async function writeLotsPostgres(username: string, lots: PortfolioLot[]): Promise<PortfolioLot[]> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();
  const normalizedUsername = normalizeUsername(username);
  const normalized = normalizeLots(lots);

  const envelope = await encryptJsonToEnvelopeObject({
    value: {
      lots: normalized,
      updatedAt: new Date().toISOString(),
    },
    purposeSuffix: portfolioPurposeSuffix(username),
    actorId: buildSesActorId(username),
    assetId: buildSesAssetId("portfolio", username),
  });

  await pool.query(
    `
      INSERT INTO ${PORTFOLIO_TABLE_NAME} (username, lots, ses_envelope, updated_at)
      VALUES ($1, '[]'::jsonb, $2::jsonb, NOW())
      ON CONFLICT (username)
      DO UPDATE SET
        lots         = '[]'::jsonb,
        ses_envelope = EXCLUDED.ses_envelope,
        updated_at   = NOW()
    `,
    [normalizedUsername, JSON.stringify(envelope)],
  );

  return normalized;
}

// ── File backend read/write ───────────────────────────────────────────────────

async function readLotsFromFileBackend(
  username: string,
  options?: { bootstrapIfMissing?: boolean },
): Promise<{ lots: PortfolioLot[]; filePath: string; legacyPath: string } | null> {
  const bootstrapIfMissing = options?.bootstrapIfMissing ?? true;
  const paths = await resolvePortfolioPaths(username);

  try {
    const payload = await decryptEnvelopeToJson<{ lots?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: portfolioPurposeSuffix(username),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("portfolio", username),
    });

    return {
      lots: parseEncryptedPayload(payload),
      filePath: paths.sesPath,
      legacyPath: paths.legacyPath,
    };
  } catch {
    // Fall through to legacy-purpose and plaintext migration paths.
  }

  try {
    const payload = await decryptEnvelopeToJson<{ lots?: unknown }>({
      envelopePath: paths.sesPath,
      purposeSuffix: portfolioLegacyPurposeSuffix(),
      actorId: buildSesActorId(username),
      assetId: buildSesAssetId("portfolio", username),
    });

    const migratedLots = parseEncryptedPayload(payload);
    await writeSesLots(username, migratedLots, paths.sesPath, paths.legacyPath);

    return {
      lots: migratedLots,
      filePath: paths.sesPath,
      legacyPath: paths.legacyPath,
    };
  } catch {
    // Fall through to plaintext migration path.
  }

  const legacyLots = await readLegacyLots(paths.legacyPath);
  if (legacyLots) {
    await writeSesLots(username, legacyLots, paths.sesPath, paths.legacyPath);
    return {
      lots: legacyLots,
      filePath: paths.sesPath,
      legacyPath: paths.legacyPath,
    };
  }

  if (!bootstrapIfMissing) {
    return null;
  }

  await writeSesLots(username, [], paths.sesPath, paths.legacyPath);
  return {
    lots: [],
    filePath: paths.sesPath,
    legacyPath: paths.legacyPath,
  };
}

async function writeLotsToFileBackend(
  username: string,
  lots: PortfolioLot[],
): Promise<{ filePath: string; legacyPath: string; lots: PortfolioLot[] }> {
  const paths = await resolvePortfolioPaths(username);
  const normalized = normalizeLots(lots);
  await writeSesLots(username, normalized, paths.sesPath, paths.legacyPath);
  return {
    filePath: paths.sesPath,
    legacyPath: paths.legacyPath,
    lots: normalized,
  };
}

// ── Backend router ────────────────────────────────────────────────────────────

async function readLots(username: string): Promise<{ lots: PortfolioLot[]; filePath: string; legacyPath: string }> {
  const backend = resolveUserDataBackend();

  if (backend === "postgres") {
    const fromDb = await readLotsPostgres(username);
    if (fromDb !== null) {
      return {
        lots: fromDb,
        filePath: postgresSourcePath(),
        legacyPath: "",
      };
    }

    // No row for this user yet — try to migrate from files, then bootstrap.
    const migratedFromFiles = await readLotsFromFileBackend(username, { bootstrapIfMissing: false });
    const initialLots = normalizeLots(migratedFromFiles?.lots ?? []);
    const written = await writeLotsPostgres(username, initialLots);

    return {
      lots: written,
      filePath: postgresSourcePath(),
      legacyPath: "",
    };
  }

  const fromFiles = await readLotsFromFileBackend(username, { bootstrapIfMissing: true });
  if (!fromFiles) {
    throw new Error("Failed to load portfolio from file backend.");
  }
  return fromFiles;
}

async function writeLots(
  username: string,
  lots: PortfolioLot[],
): Promise<{ filePath: string; legacyPath: string; lots: PortfolioLot[] }> {
  const backend = resolveUserDataBackend();

  if (backend === "postgres") {
    const written = await writeLotsPostgres(username, lots);
    return {
      filePath: postgresSourcePath(),
      legacyPath: "",
      lots: written,
    };
  }

  return writeLotsToFileBackend(username, lots);
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function loadPortfolioLots(username: string): Promise<{ lots: PortfolioLot[]; filePath: string }> {
  const result = await readLots(username);

  if (result.lots.length === 0) {
    const saved = await writeLots(username, []);
    return { lots: [], filePath: saved.filePath };
  }

  return { lots: result.lots, filePath: result.filePath };
}

export async function addPortfolioLot(
  username: string,
  input: {
    ticker: string;
    units: number;
    unitCost: number;
    addedAt?: string;
  },
): Promise<{ lots: PortfolioLot[]; filePath: string; addedLot: PortfolioLot }> {
  const current = await readLots(username);

  const nowIso = new Date().toISOString();
  const candidate: PortfolioLot = {
    id: randomUUID(),
    ticker: sanitizeTicker(input.ticker),
    units: toFinite(input.units, 0),
    unitCost: toFinite(input.unitCost, 0),
    addedAt: sanitizeIso(input.addedAt, nowIso),
    updatedAt: nowIso,
  };

  const validated = sanitizeLot(candidate);
  if (!validated) {
    throw new Error("Invalid portfolio lot input.");
  }

  const nextLots = normalizeLots([...current.lots, validated]);
  const saved = await writeLots(username, nextLots);

  return { lots: saved.lots, filePath: saved.filePath, addedLot: validated };
}

export async function updatePortfolioLot(
  username: string,
  lotId: string,
  patch: { units?: number; unitCost?: number },
): Promise<{ lots: PortfolioLot[]; filePath: string; updatedLot: PortfolioLot }> {
  const id = String(lotId ?? "").trim();
  if (!id) throw new Error("Lot id is required.");

  const current = await readLots(username);

  const index = current.lots.findIndex((lot) => lot.id === id);
  if (index < 0) {
    throw new Error("Portfolio lot not found.");
  }

  const existing = current.lots[index];
  const nowIso = new Date().toISOString();
  const nextCandidate: PortfolioLot = {
    ...existing,
    units: patch.units === undefined ? existing.units : toFinite(patch.units, existing.units),
    unitCost: patch.unitCost === undefined ? existing.unitCost : toFinite(patch.unitCost, existing.unitCost),
    updatedAt: nowIso,
  };

  const validated = sanitizeLot(nextCandidate);
  if (!validated) {
    throw new Error("Invalid updated portfolio lot values.");
  }

  const nextLots = [...current.lots];
  nextLots[index] = validated;

  const saved = await writeLots(username, nextLots);

  return { lots: saved.lots, filePath: saved.filePath, updatedLot: validated };
}

export async function removePortfolioLot(
  username: string,
  lotId: string,
): Promise<{ lots: PortfolioLot[]; filePath: string; removed: boolean }> {
  const id = String(lotId ?? "").trim();
  if (!id) throw new Error("Lot id is required.");

  const current = await readLots(username);

  const nextLots = current.lots.filter((lot) => lot.id !== id);
  const removed = nextLots.length !== current.lots.length;

  const saved = await writeLots(username, nextLots);

  return { lots: saved.lots, filePath: saved.filePath, removed };
}

export async function exportPortfolioLegacyJson(username: string): Promise<{ filePath: string }> {
  const result = await loadPortfolioLots(username);
  const paths = await resolvePortfolioPaths(username);
  const payload = {
    lots: result.lots,
    updatedAt: new Date().toISOString(),
  };
  await writePrivateTextFile(paths.legacyPath, `${JSON.stringify(payload, null, 2)}\n`);
  return { filePath: paths.legacyPath };
}
