import { pbkdf2Sync, randomBytes, timingSafeEqual } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { Pool } from "pg";

import { resolveSharedStorageBackend } from "@/lib/user-storage-backend";

export type UserRole = "admin" | "member";

type UserRecord = {
  username: string;
  password_hash: string;
  role: UserRole;
  is_active: boolean;
  is_test_user: boolean;
  access_expires_at: string | null;
  created_at: string;
};

type UserStore = {
  version: number;
  created_at: string;
  users: UserRecord[];
};

export type UserSummary = {
  username: string;
  role: UserRole;
  is_active: boolean;
  is_test_user: boolean;
  access_expires_at: string | null;
  created_at: string;
};

type UserStoreBackend = "file" | "postgres";

type PostgresUserRow = {
  username: string;
  password_hash: string;
  role: UserRole;
  is_active: boolean;
  is_test_user: boolean;
  access_expires_at: string | null;
  created_at: string;
};

const USER_STORE_FILE = "tfe_users.json";
const USER_TABLE_NAME = "tfe_users";
const PBKDF2_ITERATIONS = 210_000;
const PRIVATE_FILE_MODE = 0o600;

let postgresPool: Pool | null = null;
let postgresInitPromise: Promise<void> | null = null;

function nowIso(): string {
  return new Date().toISOString();
}

function toBase64UrlWithPadding(data: Buffer): string {
  return data.toString("base64").replace(/\+/g, "-").replace(/\//g, "_");
}

function fromBase64UrlWithPadding(text: string): Buffer {
  const normalized = text.replace(/-/g, "+").replace(/_/g, "/");
  const padLength = normalized.length % 4;
  const padded = padLength === 0 ? normalized : normalized + "=".repeat(4 - padLength);
  return Buffer.from(padded, "base64");
}

function hashPassword(password: string): string {
  const salt = randomBytes(16);
  const digest = pbkdf2Sync(password, salt, PBKDF2_ITERATIONS, 32, "sha256");
  return `pbkdf2_sha256$${PBKDF2_ITERATIONS}$${toBase64UrlWithPadding(salt)}$${toBase64UrlWithPadding(digest)}`;
}

function validatePasswordPolicy(password: string): void {
  if (password.length < 10) {
    throw new Error("Password must be at least 10 characters.");
  }

  if (password.length > 256) {
    throw new Error("Password is too long.");
  }
}

function verifyPassword(password: string, storedHash: string): boolean {
  const parts = String(storedHash ?? "").split("$", 4);
  if (parts.length !== 4) return false;

  const [algorithm, iterationsText, saltText, digestText] = parts;
  if (algorithm !== "pbkdf2_sha256") return false;

  const iterations = Number(iterationsText);
  if (!Number.isFinite(iterations) || iterations <= 0) return false;

  let salt: Buffer;
  let expectedDigest: Buffer;

  try {
    salt = fromBase64UrlWithPadding(saltText);
    expectedDigest = fromBase64UrlWithPadding(digestText);
  } catch {
    return false;
  }

  if (expectedDigest.length <= 0) return false;

  const probeDigest = pbkdf2Sync(password, salt, iterations, expectedDigest.length, "sha256");

  if (probeDigest.length !== expectedDigest.length) return false;

  return timingSafeEqual(probeDigest, expectedDigest);
}

function normalizeUsername(value: unknown): string {
  return String(value ?? "").trim().toLowerCase();
}

function sanitizeRole(value: unknown): UserRole {
  return value === "admin" ? "admin" : "member";
}

function sanitizeIso(value: unknown, fallback: string): string {
  const raw = String(value ?? "").trim();
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return new Date(parsed).toISOString();
}

function sanitizeOptionalIso(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function sanitizeUserRecord(raw: unknown): UserRecord | null {
  if (!raw || typeof raw !== "object") return null;

  const record = raw as Record<string, unknown>;
  const username = normalizeUsername(record.username);
  const passwordHash = String(record.password_hash ?? "").trim();
  const createdAt = sanitizeIso(record.created_at, nowIso());

  if (!username) return null;
  if (!passwordHash) return null;

  return {
    username,
    password_hash: passwordHash,
    role: sanitizeRole(record.role),
    is_active: Boolean(record.is_active),
    is_test_user: Boolean(record.is_test_user),
    access_expires_at: sanitizeOptionalIso(record.access_expires_at),
    created_at: createdAt,
  };
}

function sanitizeStore(raw: unknown): UserStore {
  const defaultCreatedAt = nowIso();
  if (!raw || typeof raw !== "object") {
    return {
      version: 1,
      created_at: defaultCreatedAt,
      users: [],
    };
  }

  const source = raw as Record<string, unknown>;
  const usersRaw = Array.isArray(source.users) ? source.users : [];
  const normalizedUsers: UserRecord[] = [];
  const seen = new Set<string>();

  for (const candidate of usersRaw) {
    const user = sanitizeUserRecord(candidate);
    if (!user) continue;
    if (seen.has(user.username)) continue;
    seen.add(user.username);
    normalizedUsers.push(user);
  }

  normalizedUsers.sort((a, b) => a.username.localeCompare(b.username));

  return {
    version: Number.isFinite(Number(source.version)) ? Number(source.version) : 1,
    created_at: sanitizeIso(source.created_at, defaultCreatedAt),
    users: normalizedUsers,
  };
}

function defaultStore(): UserStore {
  // Bootstrap usernames: override via TFE_ADMIN_USERNAME / TFE_USER_USERNAME.
  // Defaults are non-obvious to reduce credential-stuffing exposure on fresh deploys.
  const adminUsername = normalizeUsername(process.env.TFE_ADMIN_USERNAME ?? "tao_admin") || "tao_admin";
  const memberUsername = normalizeUsername(process.env.TFE_USER_USERNAME ?? "tao_member") || "tao_member";

  // Bootstrap passwords: TFE_ADMIN_PASSWORD / TFE_USER_PASSWORD MUST be set via
  // the ECS task definition secrets. If absent the account is bootstrapped with an
  // empty-string password hash which cannot authenticate (authenticateUser rejects
  // empty passwords), effectively locking the account until the env var is provided.
  const adminPassword = String(process.env.TFE_ADMIN_PASSWORD ?? "");
  const memberPassword = String(process.env.TFE_USER_PASSWORD ?? "");

  if (!adminPassword) {
    console.error(
      "[TFE-SECURITY] TFE_ADMIN_PASSWORD is not set. The bootstrap admin account will be " +
      "inaccessible until this variable is configured in the ECS task definition.",
    );
  }

  return {
    version: 1,
    created_at: nowIso(),
    users: [
      {
        username: adminUsername,
        password_hash: hashPassword(adminPassword),
        role: "admin",
        is_active: true,
        is_test_user: false,
        access_expires_at: null,
        created_at: nowIso(),
      },
      {
        username: memberUsername,
        password_hash: hashPassword(memberPassword),
        role: "member",
        is_active: true,
        is_test_user: false,
        access_expires_at: null,
        created_at: nowIso(),
      },
    ],
  };
}

function toSummary(record: UserRecord): UserSummary {
  return {
    username: record.username,
    role: record.role,
    is_active: record.is_active,
    is_test_user: record.is_test_user,
    access_expires_at: record.access_expires_at,
    created_at: record.created_at,
  };
}

function sanitizeDays(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  const whole = Math.floor(n);
  if (!(whole > 0)) return null;
  return whole;
}

function buildExpiryIso(days: number | null): string | null {
  if (days === null) return null;
  const millis = days * 24 * 60 * 60 * 1000;
  return new Date(Date.now() + millis).toISOString();
}

function resolveUserStoreBackend(): UserStoreBackend {
  return resolveSharedStorageBackend();
}

function userStoreCandidates(): string[] {
  const cwd = process.cwd();
  return [
    path.resolve(cwd, USER_STORE_FILE),
    path.resolve(cwd, "..", USER_STORE_FILE),
    path.resolve(cwd, "..", "..", USER_STORE_FILE),
    path.resolve("/workspaces/Tao_Financial_Engine", USER_STORE_FILE),
  ];
}

async function resolveUserStoreFilePath(): Promise<string> {
  const candidates = userStoreCandidates();

  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // keep checking
    }
  }

  return candidates[1] ?? candidates[0];
}

async function writePrivateTextFile(filePath: string, text: string): Promise<void> {
  await fs.writeFile(filePath, text, { mode: PRIVATE_FILE_MODE });
  try {
    await fs.chmod(filePath, PRIVATE_FILE_MODE);
  } catch {
    // Best-effort for filesystems/platforms that restrict chmod.
  }
}

async function loadFileStoreAndPath(): Promise<{ store: UserStore; filePath: string }> {
  const filePath = await resolveUserStoreFilePath();

  try {
    const raw = await fs.readFile(filePath, "utf-8");
    try {
      await fs.chmod(filePath, PRIVATE_FILE_MODE);
    } catch {
      // Best-effort only.
    }
    const parsed = JSON.parse(raw) as unknown;
    const store = sanitizeStore(parsed);
    return { store, filePath };
  } catch {
    const store = defaultStore();
    await writePrivateTextFile(filePath, `${JSON.stringify(store, null, 2)}\n`);
    return { store, filePath };
  }
}

async function saveFileStore(filePath: string, store: UserStore): Promise<void> {
  const sanitized = sanitizeStore(store);
  await writePrivateTextFile(filePath, `${JSON.stringify(sanitized, null, 2)}\n`);
}

function readRequiredEnv(name: string): string {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) {
    throw new Error(`${name} is required when TFE_USER_STORE_BACKEND=postgres.`);
  }
  return raw;
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
  return `postgres://${host}:${port}/${database}#${USER_TABLE_NAME}`;
}

function resolvePostgresPool(): Pool {
  if (postgresPool) return postgresPool;

  const host = readRequiredEnv("PGHOST");
  const database = readRequiredEnv("PGDATABASE");
  const user = readRequiredEnv("PGUSER");
  const password = readRequiredEnv("PGPASSWORD");
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
    application_name: "tfe-web-user-store",
  });

  return postgresPool;
}

async function loadSeedUsersForPostgres(): Promise<UserRecord[]> {
  const filePath = await resolveUserStoreFilePath();

  try {
    const raw = await fs.readFile(filePath, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    const store = sanitizeStore(parsed);
    if (store.users.length > 0) {
      return store.users;
    }
  } catch {
    // Fall through to defaults.
  }

  return defaultStore().users;
}

function rowToUserRecord(row: PostgresUserRow): UserRecord {
  const candidate = sanitizeUserRecord({
    username: row.username,
    password_hash: row.password_hash,
    role: row.role,
    is_active: row.is_active,
    is_test_user: row.is_test_user,
    access_expires_at: row.access_expires_at,
    created_at: row.created_at,
  });

  if (!candidate) {
    throw new Error("Invalid user record returned from PostgreSQL.");
  }

  return candidate;
}

async function ensurePostgresInitialized(): Promise<void> {
  if (postgresInitPromise) {
    await postgresInitPromise;
    return;
  }

  const pool = resolvePostgresPool();

  postgresInitPromise = (async () => {
    const client = await pool.connect();

    try {
      await client.query("BEGIN");

      await client.query(`
        CREATE TABLE IF NOT EXISTS ${USER_TABLE_NAME} (
          username VARCHAR(64) PRIMARY KEY,
          password_hash TEXT NOT NULL,
          role VARCHAR(16) NOT NULL CHECK (role IN ('admin', 'member')),
          is_active BOOLEAN NOT NULL,
          is_test_user BOOLEAN NOT NULL,
          access_expires_at TIMESTAMPTZ NULL,
          created_at TIMESTAMPTZ NOT NULL
        )
      `);

      await client.query(`LOCK TABLE ${USER_TABLE_NAME} IN EXCLUSIVE MODE`);

      const countResult = await client.query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM ${USER_TABLE_NAME}`);
      const count = Number(countResult.rows[0]?.count ?? "0");

      if (!Number.isFinite(count)) {
        throw new Error("Invalid PostgreSQL user count response.");
      }

      if (count === 0) {
        const seedUsers = await loadSeedUsersForPostgres();
        for (const user of seedUsers) {
          await client.query(
            `
              INSERT INTO ${USER_TABLE_NAME} (
                username,
                password_hash,
                role,
                is_active,
                is_test_user,
                access_expires_at,
                created_at
              )
              VALUES ($1, $2, $3, $4, $5, $6, $7)
              ON CONFLICT (username) DO NOTHING
            `,
            [
              user.username,
              user.password_hash,
              user.role,
              user.is_active,
              user.is_test_user,
              user.access_expires_at,
              user.created_at,
            ],
          );
        }
      }

      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK").catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  })();

  try {
    await postgresInitPromise;
  } catch (error) {
    postgresInitPromise = null;
    throw error;
  }
}

async function listPostgresUsers(): Promise<UserRecord[]> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();

  const result = await pool.query<PostgresUserRow>(
    `
      SELECT
        username,
        password_hash,
        role,
        is_active,
        is_test_user,
        access_expires_at::text,
        created_at::text
      FROM ${USER_TABLE_NAME}
      ORDER BY username ASC
    `,
  );

  return result.rows.map(rowToUserRecord);
}

async function getPostgresUser(username: string): Promise<UserRecord | null> {
  await ensurePostgresInitialized();
  const pool = resolvePostgresPool();

  const result = await pool.query<PostgresUserRow>(
    `
      SELECT
        username,
        password_hash,
        role,
        is_active,
        is_test_user,
        access_expires_at::text,
        created_at::text
      FROM ${USER_TABLE_NAME}
      WHERE username = $1
      LIMIT 1
    `,
    [username],
  );

  if (result.rows.length === 0) return null;
  return rowToUserRecord(result.rows[0]);
}

function isUniqueViolation(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const maybeCode = (error as { code?: unknown }).code;
  return maybeCode === "23505";
}

export function isUserAccessExpired(accessExpiresAt: string | null): boolean {
  if (!accessExpiresAt) return false;
  const parsed = Date.parse(accessExpiresAt);
  if (!Number.isFinite(parsed)) return true;
  return parsed <= Date.now();
}

export async function listUsers(): Promise<{ users: UserSummary[]; filePath: string }> {
  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    const users = await listPostgresUsers();
    return {
      users: users.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();
  return {
    users: store.users.map(toSummary),
    filePath,
  };
}

export async function getUserByUsername(username: unknown): Promise<UserSummary | null> {
  const lookup = normalizeUsername(username);
  if (!lookup) return null;

  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    const found = await getPostgresUser(lookup);
    return found ? toSummary(found) : null;
  }

  const { store } = await loadFileStoreAndPath();
  const found = store.users.find((user) => user.username === lookup);
  return found ? toSummary(found) : null;
}

export async function authenticateUser(input: { username: unknown; password: unknown }): Promise<UserSummary | null> {
  const username = normalizeUsername(input.username);
  const password = String(input.password ?? "");

  if (!username) return null;
  if (!password) return null;

  const backend = resolveUserStoreBackend();

  let found: UserRecord | null;

  if (backend === "postgres") {
    found = await getPostgresUser(username);
  } else {
    const { store } = await loadFileStoreAndPath();
    found = store.users.find((user) => user.username === username) ?? null;
  }

  if (!found) return null;
  if (!found.is_active) return null;
  if (isUserAccessExpired(found.access_expires_at)) return null;

  const ok = verifyPassword(password, found.password_hash);
  if (!ok) return null;

  return toSummary(found);
}

export async function createTestUser(input: {
  username: unknown;
  password: unknown;
  role?: unknown;
  expiresInDays?: unknown;
}): Promise<{ created: UserSummary; users: UserSummary[]; filePath: string }> {
  const username = normalizeUsername(input.username);
  const password = String(input.password ?? "");
  const role = sanitizeRole(input.role);
  const expiresInDays = sanitizeDays(input.expiresInDays);

  if (!username) {
    throw new Error("Username is required.");
  }

  if (!/^[a-z0-9._-]{3,64}$/.test(username)) {
    throw new Error("Username must be 3-64 chars using a-z, 0-9, dot, underscore, or dash.");
  }

  validatePasswordPolicy(password);

  const created: UserRecord = {
    username,
    password_hash: hashPassword(password),
    role,
    is_active: true,
    is_test_user: true,
    access_expires_at: buildExpiryIso(expiresInDays),
    created_at: nowIso(),
  };

  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    await ensurePostgresInitialized();
    const pool = resolvePostgresPool();

    try {
      await pool.query(
        `
          INSERT INTO ${USER_TABLE_NAME} (
            username,
            password_hash,
            role,
            is_active,
            is_test_user,
            access_expires_at,
            created_at
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `,
        [
          created.username,
          created.password_hash,
          created.role,
          created.is_active,
          created.is_test_user,
          created.access_expires_at,
          created.created_at,
        ],
      );
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new Error("User already exists.");
      }
      throw error;
    }

    const users = await listPostgresUsers();

    return {
      created: toSummary(created),
      users: users.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();

  const exists = store.users.some((user) => user.username === username);
  if (exists) {
    throw new Error("User already exists.");
  }

  const nextStore: UserStore = {
    ...store,
    users: [...store.users, created],
  };

  await saveFileStore(filePath, nextStore);

  const savedStore = sanitizeStore(nextStore);

  return {
    created: toSummary(created),
    users: savedStore.users.map(toSummary),
    filePath,
  };
}

export async function resetUserPassword(input: {
  username: unknown;
  password: unknown;
}): Promise<{ updated: UserSummary; users: UserSummary[]; filePath: string }> {
  const username = normalizeUsername(input.username);
  const password = String(input.password ?? "");

  if (!username) {
    throw new Error("Username is required.");
  }

  if (!/^[a-z0-9._-]{3,64}$/.test(username)) {
    throw new Error("Username must be 3-64 chars using a-z, 0-9, dot, underscore, or dash.");
  }

  validatePasswordPolicy(password);

  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    await ensurePostgresInitialized();
    const pool = resolvePostgresPool();
    const passwordHash = hashPassword(password);

    const updateResult = await pool.query<PostgresUserRow>(
      `
        UPDATE ${USER_TABLE_NAME}
        SET password_hash = $2
        WHERE username = $1
        RETURNING
          username,
          password_hash,
          role,
          is_active,
          is_test_user,
          access_expires_at::text,
          created_at::text
      `,
      [username, passwordHash],
    );

    if (updateResult.rows.length === 0) {
      throw new Error("User not found.");
    }

    const updated = rowToUserRecord(updateResult.rows[0]);
    const users = await listPostgresUsers();

    return {
      updated: toSummary(updated),
      users: users.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();
  const index = store.users.findIndex((user) => user.username === username);
  if (index < 0) {
    throw new Error("User not found.");
  }

  const existing = store.users[index];
  const updated: UserRecord = {
    ...existing,
    password_hash: hashPassword(password),
  };

  const nextStore: UserStore = {
    ...store,
    users: [...store.users],
  };
  nextStore.users[index] = updated;

  await saveFileStore(filePath, nextStore);
  const savedStore = sanitizeStore(nextStore);

  return {
    updated: toSummary(updated),
    users: savedStore.users.map(toSummary),
    filePath,
  };
}

function hasOtherActiveAdmin(users: UserRecord[], excludedUsername: string): boolean {
  return users.some(
    (user) =>
      user.username !== excludedUsername &&
      user.role === "admin" &&
      user.is_active &&
      !isUserAccessExpired(user.access_expires_at),
  );
}

export async function setUserActive(input: {
  username: unknown;
  isActive: unknown;
}): Promise<{ updated: UserSummary; users: UserSummary[]; filePath: string }> {
  const username = normalizeUsername(input.username);
  const isActive = Boolean(input.isActive);

  if (!username) {
    throw new Error("Username is required.");
  }

  if (!/^[a-z0-9._-]{3,64}$/.test(username)) {
    throw new Error("Username must be 3-64 chars using a-z, 0-9, dot, underscore, or dash.");
  }

  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    await ensurePostgresInitialized();
    const users = await listPostgresUsers();
    const existing = users.find((user) => user.username === username);
    if (!existing) {
      throw new Error("User not found.");
    }

    if (existing.role === "admin" && existing.is_active && !isActive) {
      if (!hasOtherActiveAdmin(users, existing.username)) {
        throw new Error("Cannot disable the last active admin account.");
      }
    }

    const pool = resolvePostgresPool();
    const updateResult = await pool.query<PostgresUserRow>(
      `
        UPDATE ${USER_TABLE_NAME}
        SET is_active = $2
        WHERE username = $1
        RETURNING
          username,
          password_hash,
          role,
          is_active,
          is_test_user,
          access_expires_at::text,
          created_at::text
      `,
      [username, isActive],
    );

    if (updateResult.rows.length === 0) {
      throw new Error("User not found.");
    }

    const updated = rowToUserRecord(updateResult.rows[0]);
    const nextUsers = await listPostgresUsers();

    return {
      updated: toSummary(updated),
      users: nextUsers.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();
  const index = store.users.findIndex((user) => user.username === username);
  if (index < 0) {
    throw new Error("User not found.");
  }

  const existing = store.users[index];
  if (existing.role === "admin" && existing.is_active && !isActive) {
    if (!hasOtherActiveAdmin(store.users, existing.username)) {
      throw new Error("Cannot disable the last active admin account.");
    }
  }

  const updated: UserRecord = {
    ...existing,
    is_active: isActive,
  };

  const nextStore: UserStore = {
    ...store,
    users: [...store.users],
  };
  nextStore.users[index] = updated;

  await saveFileStore(filePath, nextStore);
  const savedStore = sanitizeStore(nextStore);

  return {
    updated: toSummary(updated),
    users: savedStore.users.map(toSummary),
    filePath,
  };
}

export async function removeUser(input: {
  username: unknown;
  requestingUsername?: unknown;
}): Promise<{ removed: UserSummary; users: UserSummary[]; filePath: string }> {
  const username = normalizeUsername(input.username);
  const requestingUsername = normalizeUsername(input.requestingUsername);

  if (!username) {
    throw new Error("Username is required.");
  }

  if (!/^[a-z0-9._-]{3,64}$/.test(username)) {
    throw new Error("Username must be 3-64 chars using a-z, 0-9, dot, underscore, or dash.");
  }

  if (requestingUsername && requestingUsername === username) {
    throw new Error("Cannot remove the currently signed-in account.");
  }

  const backend = resolveUserStoreBackend();

  if (backend === "postgres") {
    await ensurePostgresInitialized();
    const users = await listPostgresUsers();
    const existing = users.find((user) => user.username === username);
    if (!existing) {
      throw new Error("User not found.");
    }

    if (existing.role === "admin" && existing.is_active) {
      if (!hasOtherActiveAdmin(users, existing.username)) {
        throw new Error("Cannot remove the last active admin account.");
      }
    }

    const pool = resolvePostgresPool();
    const deleteResult = await pool.query<PostgresUserRow>(
      `
        DELETE FROM ${USER_TABLE_NAME}
        WHERE username = $1
        RETURNING
          username,
          password_hash,
          role,
          is_active,
          is_test_user,
          access_expires_at::text,
          created_at::text
      `,
      [username],
    );

    if (deleteResult.rows.length === 0) {
      throw new Error("User not found.");
    }

    const removed = rowToUserRecord(deleteResult.rows[0]);
    const nextUsers = await listPostgresUsers();

    return {
      removed: toSummary(removed),
      users: nextUsers.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();
  const index = store.users.findIndex((user) => user.username === username);
  if (index < 0) {
    throw new Error("User not found.");
  }

  const existing = store.users[index];
  if (existing.role === "admin" && existing.is_active) {
    if (!hasOtherActiveAdmin(store.users, existing.username)) {
      throw new Error("Cannot remove the last active admin account.");
    }
  }

  const nextUsers = [...store.users];
  const [removed] = nextUsers.splice(index, 1);

  const nextStore: UserStore = {
    ...store,
    users: nextUsers,
  };

  await saveFileStore(filePath, nextStore);
  const savedStore = sanitizeStore(nextStore);

  return {
    removed: toSummary(removed),
    users: savedStore.users.map(toSummary),
    filePath,
  };
}

export async function cleanupUnusedTestUsers(input?: {
  requestingUsername?: unknown;
}): Promise<{ removedUsernames: string[]; users: UserSummary[]; filePath: string }> {
  const requestingUsername = normalizeUsername(input?.requestingUsername);
  const backend = resolveUserStoreBackend();

  const shouldRemove = (user: UserRecord): boolean => {
    if (!user.is_test_user) return false;
    if (requestingUsername && user.username === requestingUsername) return false;
    if (user.role === "admin" && user.is_active) return false;
    if (!user.is_active) return true;
    return isUserAccessExpired(user.access_expires_at);
  };

  if (backend === "postgres") {
    await ensurePostgresInitialized();
    const users = await listPostgresUsers();
    const removable = users.filter(shouldRemove);
    const removedUsernames = removable.map((user) => user.username);

    if (removedUsernames.length > 0) {
      const pool = resolvePostgresPool();
      await pool.query(
        `
          DELETE FROM ${USER_TABLE_NAME}
          WHERE username = ANY($1::text[])
        `,
        [removedUsernames],
      );
    }

    const nextUsers = await listPostgresUsers();
    return {
      removedUsernames,
      users: nextUsers.map(toSummary),
      filePath: postgresSourcePath(),
    };
  }

  const { store, filePath } = await loadFileStoreAndPath();
  const removable = store.users.filter(shouldRemove);
  const removedUsernames = removable.map((user) => user.username);

  if (removedUsernames.length === 0) {
    return {
      removedUsernames,
      users: store.users.map(toSummary),
      filePath,
    };
  }

  const nextStore: UserStore = {
    ...store,
    users: store.users.filter((user) => !removedUsernames.includes(user.username)),
  };

  await saveFileStore(filePath, nextStore);
  const savedStore = sanitizeStore(nextStore);

  return {
    removedUsernames,
    users: savedStore.users.map(toSummary),
    filePath,
  };
}
