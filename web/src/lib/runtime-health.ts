import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
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

export type RuntimeHealthResult = {
  healthy: boolean;
  checkedAtUtc: string;
  generationId: string | null;
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

export async function checkSnapshotReceipts(): Promise<{ ok: boolean; generationId: string | null }> {
  try {
    const root = appRoot();
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
      return { ok: false, generationId: generationId || null };
    }

    for (const name of REQUIRED_ARTIFACTS) {
      const receipt = objectValue(artifacts[name]) as ArtifactReceipt | null;
      const filename = String(receipt?.filename ?? "").trim();
      const expectedDigest = String(receipt?.sha256 ?? "").trim();
      const expectedBytes = Number(receipt?.bytes);
      if (!filename || path.basename(filename) !== filename || !expectedDigest || !Number.isInteger(expectedBytes)) {
        return { ok: false, generationId };
      }
      const artifact = await readFile(path.join(root, filename));
      if (artifact.byteLength !== expectedBytes || sha256(artifact) !== expectedDigest) {
        return { ok: false, generationId };
      }
    }
    return { ok: true, generationId };
  } catch {
    return { ok: false, generationId: null };
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
    checks,
  };
}
