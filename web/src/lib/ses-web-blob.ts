import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const ROOT_DIR = path.resolve(process.cwd(), "..");
const SCRIPT_PATH = path.join(ROOT_DIR, "web", "scripts", "ses_web_blob.py");
const PYTHON_BIN = process.env.TFE_PYTHON_BIN || "python";
const TMP_DIR = path.join(ROOT_DIR, "web_user_data", ".ses_tmp");
const PRIVATE_FILE_MODE = 0o600;
const PRIVATE_DIR_MODE = 0o700;
const MAX_BUFFER = 128 * 1024 * 1024;

function normalizeBridgeTimeoutMs(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 15000;
  const whole = Math.floor(parsed);
  if (whole < 1000) return 1000;
  if (whole > 30000) return 30000;
  return whole;
}

const BRIDGE_TIMEOUT_MS = normalizeBridgeTimeoutMs(process.env.TFE_SES_BRIDGE_TIMEOUT_MS);

type BridgeMode = "encrypt" | "decrypt";

type SesRuntimeOverride = {
  sesEnvironment?: string;
  sesRegion?: string;
};

type BridgeParams = {
  mode: BridgeMode;
  purposeSuffix: string;
  actorId: string;
  assetId: string;
  inputPath: string;
  outputPath: string;
} & SesRuntimeOverride;

type EncryptParams = {
  value: unknown;
  envelopePath: string;
  purposeSuffix: string;
  actorId: string;
  assetId: string;
} & SesRuntimeOverride;

type DecryptParams = {
  envelopePath: string;
  purposeSuffix: string;
  actorId: string;
  assetId: string;
} & SesRuntimeOverride;

type EncryptToObjectParams = {
  value: unknown;
  purposeSuffix: string;
  actorId: string;
  assetId: string;
} & SesRuntimeOverride;

type DecryptFromObjectParams = {
  envelope: Record<string, unknown>;
  purposeSuffix: string;
  actorId: string;
  assetId: string;
} & SesRuntimeOverride;

function normalizeToken(value: string): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._:-]/g, "_");
}

function normalizeSesArg(value: string | undefined): string | null {
  const normalized = String(value ?? "").trim();
  return normalized.length > 0 ? normalized : null;
}

function ensureAbsolutePath(filePath: string): string {
  const resolved = path.resolve(filePath);
  return resolved;
}

async function ensurePrivateTmpDir(): Promise<void> {
  await fs.mkdir(TMP_DIR, { recursive: true, mode: PRIVATE_DIR_MODE });
  try {
    await fs.chmod(TMP_DIR, PRIVATE_DIR_MODE);
  } catch {
    // Best effort on restricted filesystems.
  }
}

function tempJsonPath(prefix: string): string {
  const token = randomUUID();
  return path.join(TMP_DIR, `${prefix}-${token}.json`);
}

async function writePrivateJson(filePath: string, value: unknown): Promise<void> {
  await fs.writeFile(filePath, JSON.stringify(value), { mode: PRIVATE_FILE_MODE, encoding: "utf-8" });
  try {
    await fs.chmod(filePath, PRIVATE_FILE_MODE);
  } catch {
    // Best effort on restricted filesystems.
  }
}

async function runBridge(params: BridgeParams): Promise<void> {
  const purposeSuffix = normalizeToken(params.purposeSuffix);
  const actorId = normalizeToken(params.actorId);
  const assetId = normalizeToken(params.assetId);
  const sesEnvironment = normalizeSesArg(params.sesEnvironment);
  const sesRegion = normalizeSesArg(params.sesRegion);

  if (!purposeSuffix) {
    throw new Error("SES purpose suffix is required.");
  }

  if (!actorId) {
    throw new Error("SES actor id is required.");
  }

  if (!assetId) {
    throw new Error("SES asset id is required.");
  }

  const args = [
    SCRIPT_PATH,
    params.mode,
    "--purpose-suffix",
    purposeSuffix,
    "--actor-id",
    actorId,
    "--asset-id",
    assetId,
    "--input-path",
    ensureAbsolutePath(params.inputPath),
    "--output-path",
    ensureAbsolutePath(params.outputPath),
  ];

  if (sesEnvironment) {
    args.push("--environment", sesEnvironment);
  }

  if (sesRegion) {
    args.push("--region", sesRegion);
  }

  try {
    await execFileAsync(PYTHON_BIN, args, {
      cwd: ROOT_DIR,
      maxBuffer: MAX_BUFFER,
      timeout: BRIDGE_TIMEOUT_MS,
      env: process.env,
    });
  } catch (error) {
    const e = error as {
      message?: string;
      stdout?: string;
      stderr?: string;
    };

    const message = String(e?.message ?? "").trim();
    const stderr = String(e?.stderr ?? "").trim();
    const stdout = String(e?.stdout ?? "").trim();

    if (message.toLowerCase().includes("timed out")) {
      throw new Error(
        `SES bridge failed: timed out after ${BRIDGE_TIMEOUT_MS}ms (mode=${params.mode}, input=${params.inputPath}).`,
      );
    }

    const detail = stderr || stdout || message || "unknown SES bridge error";
    throw new Error(`SES bridge failed: ${detail}`);
  }
}

async function safeDelete(filePath: string): Promise<void> {
  try {
    await fs.unlink(filePath);
  } catch {
    // Ignore cleanup failures.
  }
}

// ── File-path-based encrypt/decrypt (file backend) ────────────────────────────

export async function encryptJsonToEnvelope(params: EncryptParams): Promise<void> {
  await ensurePrivateTmpDir();

  const tempInput = tempJsonPath("ses-enc-in");

  try {
    await writePrivateJson(tempInput, params.value);

    await runBridge({
      mode: "encrypt",
      purposeSuffix: params.purposeSuffix,
      actorId: params.actorId,
      assetId: params.assetId,
      inputPath: tempInput,
      outputPath: params.envelopePath,
      sesEnvironment: params.sesEnvironment,
      sesRegion: params.sesRegion,
    });
  } finally {
    await safeDelete(tempInput);
  }
}

export async function decryptEnvelopeToJson<T>(params: DecryptParams): Promise<T> {
  await ensurePrivateTmpDir();

  const tempOutput = tempJsonPath("ses-dec-out");

  try {
    await runBridge({
      mode: "decrypt",
      purposeSuffix: params.purposeSuffix,
      actorId: params.actorId,
      assetId: params.assetId,
      inputPath: params.envelopePath,
      outputPath: tempOutput,
      sesEnvironment: params.sesEnvironment,
      sesRegion: params.sesRegion,
    });

    const raw = await fs.readFile(tempOutput, "utf-8");
    return JSON.parse(raw) as T;
  } finally {
    await safeDelete(tempOutput);
  }
}

// ── Object-based encrypt/decrypt (Postgres backend) ───────────────────────────
//
// These functions encrypt to / decrypt from an in-memory SES envelope object
// rather than a persistent file path. They are used by the Postgres write/read
// paths in portfolio-store and watchlist-store so that user data is SES-encrypted
// before it reaches the database — the plaintext never touches the wire.
//
// Both functions still route through the Python SES bridge via temp files so that
// the cryptographic implementation (HKDF key hierarchy, SCE-SIV AEAD, chain of
// custody) remains identical to the file-backend path.

export async function encryptJsonToEnvelopeObject(params: EncryptToObjectParams): Promise<Record<string, unknown>> {
  await ensurePrivateTmpDir();

  const tempInput = tempJsonPath("ses-obj-enc-in");
  const tempOutput = tempJsonPath("ses-obj-enc-out");

  try {
    await writePrivateJson(tempInput, params.value);

    await runBridge({
      mode: "encrypt",
      purposeSuffix: params.purposeSuffix,
      actorId: params.actorId,
      assetId: params.assetId,
      inputPath: tempInput,
      outputPath: tempOutput,
      sesEnvironment: params.sesEnvironment,
      sesRegion: params.sesRegion,
    });

    const raw = await fs.readFile(tempOutput, "utf-8");
    const parsed = JSON.parse(raw) as unknown;

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("SES bridge returned non-object envelope.");
    }

    return parsed as Record<string, unknown>;
  } finally {
    await safeDelete(tempInput);
    await safeDelete(tempOutput);
  }
}

export async function decryptEnvelopeObjectToJson<T>(params: DecryptFromObjectParams): Promise<T> {
  await ensurePrivateTmpDir();

  const tempInput = tempJsonPath("ses-obj-dec-in");
  const tempOutput = tempJsonPath("ses-obj-dec-out");

  try {
    await writePrivateJson(tempInput, params.envelope);

    await runBridge({
      mode: "decrypt",
      purposeSuffix: params.purposeSuffix,
      actorId: params.actorId,
      assetId: params.assetId,
      inputPath: tempInput,
      outputPath: tempOutput,
      sesEnvironment: params.sesEnvironment,
      sesRegion: params.sesRegion,
    });

    const raw = await fs.readFile(tempOutput, "utf-8");
    return JSON.parse(raw) as T;
  } finally {
    await safeDelete(tempInput);
    await safeDelete(tempOutput);
  }
}

// ── Path / identity helpers ───────────────────────────────────────────────────

export function buildSesActorId(username: string): string {
  return `web-user:${normalizeToken(username)}`;
}

export function buildSesAssetId(kind: string, username: string): string {
  const safeKind = normalizeToken(kind);
  const safeUser = normalizeToken(username);
  return `${safeKind}:${safeUser}`;
}

export function resolveRootRelativePath(...parts: string[]): string {
  return path.join(ROOT_DIR, ...parts);
}

export function resolveTempDirectory(): string {
  return TMP_DIR;
}

export function resolvePythonBinary(): string {
  return PYTHON_BIN;
}

export function resolveScriptPath(): string {
  return SCRIPT_PATH;
}

export function resolveHomeDirectory(): string {
  return os.homedir();
}
