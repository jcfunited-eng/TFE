import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { Pool } from "pg";
import {
  readOptionalEnv,
  readPgPort,
  readRequiredEnv,
  resolvePgSslRejectUnauthorized,
} from "@/lib/runtime-db";

const PROCESS_HEARTBEAT_PATH = "/tmp/tfe_process_health.json";
const MAX_HEARTBEAT_AGE_MS = 45_000;
const REQUIRED_ARTIFACTS = ["snapshot", "envelope", "report"] as const;

// The nightly rebuild (rebuild_uf_snapshot.py) rewrites, hides and republishes
// the bound artifacts in place before the next manifest exists. While it holds
// them it records a generation hold beside the manifest; the receipts check
// honors that hold only while the recorded process is alive and the hold is
// younger than the bound below. The bound derives from the longest rebuild
// phase observed in production (2,926 s, the Sunday full-universe run) with
// room for retries; a rebuild older than this is treated as hung and the
// receipts fail closed again.
const GENERATION_HOLD_FILENAME = "uf_snapshot_generation.hold.json";
const GENERATION_HOLD_SCHEMA = "tfe.snapshot-generation-hold.v1";
const MAX_GENERATION_HOLD_MS = 3 * 60 * 60 * 1000;

type ProcessReceipt = { pid?: unknown; alive?: unknown };
type ArtifactReceipt = {
  filename?: unknown;
  sha256?: unknown;
  bytes?: unknown;
};

type ProcessHeartbeat = {
  schema?: unknown;
  generated_at_utc?: unknown;
  processes?: Record<string, ProcessReceipt>;
};

type SnapshotManifest = {
  schema?: unknown;
  generation_id?: unknown;
  publication_id?: unknown;
  artifacts?: Record<string, ArtifactReceipt>;
};

type GenerationHold = {
  schema?: unknown;
  pid?: unknown;
  started_at_utc?: unknown;
};

export type SnapshotReceiptsResult = {
  ok: boolean;
  generationId: string | null;
  generationHold: boolean;
};

export type RuntimeHealthResult = {
  healthy: boolean;
  checkedAtUtc: string;
  generationId: string | null;
  generationHold: boolean;
  checks: {
    processHeartbeat: boolean;
    database: boolean;
    snapshotReceipts: boolean;
  };
};

let healthPool: Pool | null = null;

function appRoot(): string {
  return String(process.env.TFE_APP_ROOT ?? "/app").trim() || "/app";
}

function sha256(data: Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

function objectValue(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function parseJsonObject(data: Buffer): Record<string, unknown> | null {
  try {
    return objectValue(JSON.parse(data.toString("utf8")));
  } catch {
    return null;
  }
}

export async function checkProcessHeartbeat(nowMs = Date.now()): Promise<boolean> {
  try {
    const raw = await readFile(PROCESS_HEARTBEAT_PATH);
    const heartbeat = parseJsonObject(raw) as ProcessHeartbeat | null;
    if (!heartbeat || heartbeat.schema !== "tfe.process-health.v1") return false;
    const generatedAtMs = Date.parse(String(heartbeat.generated_at_utc ?? ""));
    if (!Number.isFinite(generatedAtMs)) return false;
    const age = nowMs - generatedAtMs;
    if (age < 0 || age > MAX_HEARTBEAT_AGE_MS) return false;
    const processes = objectValue(heartbeat.processes) as Record<string, ProcessReceipt> | null;
    if (!processes) return false;
    return ["next", "sentinel", "fundamentals_backfill"].every((name) => {
      const receipt = objectValue(processes[name]) as ProcessReceipt | null;
      return receipt?.alive === true && Number.isInteger(receipt.pid) && Number(receipt.pid) > 0;
    });
  } catch {
    return false;
  }
}

function resolveHealthPool(): Pool {
  if (healthPool) return healthPool;
  healthPool = new Pool({
    host: readRequiredEnv("PGHOST", "TFE_DB_HOST"),
    database: readRequiredEnv("PGDATABASE", "TFE_DB_NAME"),
    user: readRequiredEnv("PGUSER", "TFE_DB_USER"),
    password: readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD"),
    port: readPgPort(),
    max: 1,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
    statement_timeout: 5_000,
    ssl: { rejectUnauthorized: resolvePgSslRejectUnauthorized() },
    application_name: "tfe-runtime-health",
  });
  return healthPool;
}

export async function checkDatabase(): Promise<boolean> {
  if (!readOptionalEnv("PGHOST", "TFE_DB_HOST")) return false;
  try {
    const result = await resolveHealthPool().query("SELECT 1 AS reachable");
    return result.rows[0]?.reachable === 1;
  } catch {
    return false;
  }
}

async function processAlive(pid: number): Promise<boolean> {
  try {
    await access(`/proc/${pid}`);
    return true;
  } catch {
    return false;
  }
}

/**
 * True only while a live rebuild process holds the bound artifacts: the hold
 * file carries this schema, names a running process, and is younger than the
 * bound. Anything else (no file, unparseable, dead process, too old) is false.
 */
export async function checkGenerationHold(root = appRoot(), nowMs = Date.now()): Promise<boolean> {
  try {
    const raw = await readFile(path.join(root, GENERATION_HOLD_FILENAME));
    const hold = parseJsonObject(raw) as GenerationHold | null;
    if (!hold || hold.schema !== GENERATION_HOLD_SCHEMA) return false;
    const pid = Number(hold.pid);
    if (!Number.isInteger(pid) || pid <= 0) return false;
    const startedAtMs = Date.parse(String(hold.started_at_utc ?? ""));
    if (!Number.isFinite(startedAtMs)) return false;
    const age = nowMs - startedAtMs;
    if (age < 0 || age > MAX_GENERATION_HOLD_MS) return false;
    return processAlive(pid);
  } catch {
    return false;
  }
}

async function artifactsMatchManifest(root: string, artifacts: Record<string, ArtifactReceipt>): Promise<boolean> {
  for (const name of REQUIRED_ARTIFACTS) {
    const receipt = objectValue(artifacts[name]) as ArtifactReceipt | null;
    const filename = String(receipt?.filename ?? "").trim();
    const expectedDigest = String(receipt?.sha256 ?? "").trim();
    const expectedBytes = Number(receipt?.bytes);
    if (!filename || path.basename(filename) !== filename || !expectedDigest || !Number.isInteger(expectedBytes)) {
      return false;
    }
    let artifact: Buffer;
    try {
      artifact = await readFile(path.join(root, filename));
    } catch {
      return false;
    }
    if (artifact.byteLength !== expectedBytes || sha256(artifact) !== expectedDigest) {
      return false;
    }
  }
  return true;
}

export async function checkSnapshotReceipts(root = appRoot(), nowMs = Date.now()): Promise<SnapshotReceiptsResult> {
  try {
    const manifestRaw = await readFile(path.join(root, "uf_snapshot_generation_manifest.json"));
    const manifest = parseJsonObject(manifestRaw) as SnapshotManifest | null;
    const generationId = String(manifest?.generation_id ?? "").trim();
    const publicationId = String(manifest?.publication_id ?? "").trim();
    const artifacts = objectValue(manifest?.artifacts) as Record<string, ArtifactReceipt> | null;
    if (
      !manifest
      || manifest.schema !== "tfe.snapshot-generation.v1"
      || !generationId
      || generationId !== publicationId
      || !artifacts
      || Object.keys(artifacts).sort().join(",") !== [...REQUIRED_ARTIFACTS].sort().join(",")
    ) {
      return { ok: false, generationId: generationId || null, generationHold: false };
    }

    if (await artifactsMatchManifest(root, artifacts)) {
      return { ok: true, generationId, generationHold: false };
    }
    // The manifest is intact but the artifacts on disk are not the ones it
    // binds. That is the verified state only while a live rebuild holds them.
    const generationHold = await checkGenerationHold(root, nowMs);
    return { ok: generationHold, generationId, generationHold };
  } catch {
    return { ok: false, generationId: null, generationHold: false };
  }
}

export async function evaluateRuntimeHealth(): Promise<RuntimeHealthResult> {
  const checkedAtUtc = new Date().toISOString();
  const [processHeartbeat, database, snapshot] = await Promise.all([
    checkProcessHeartbeat(),
    checkDatabase(),
    checkSnapshotReceipts(),
  ]);
  const checks = {
    processHeartbeat,
    database,
    snapshotReceipts: snapshot.ok,
  };
  return {
    healthy: Object.values(checks).every(Boolean),
    checkedAtUtc,
    generationId: snapshot.generationId,
    generationHold: snapshot.generationHold,
    checks,
  };
}
