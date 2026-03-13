#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { Pool } from "pg";
import { fileURLToPath } from "node:url";

const DEFAULT_DB_PORT = 5432;
const ROOT = String(process.env.A3_APP_ROOT ?? "/app").trim() || "/app";
const SELF_DIR = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT_ROOT = String(process.env.A3_SCRIPT_ROOT ?? SELF_DIR).trim() || SELF_DIR;
const SYNC_SCRIPT = path.join(SCRIPT_ROOT, "sync_runtime_postgres.mjs");
const PARITY_SCRIPT = path.join(SCRIPT_ROOT, "run_provenance_persistence_parity_audit.mjs");
const SNAPSHOT_PATH = path.join(ROOT, "uf_snapshot.json");
const PERSISTENCE_ARTIFACT_PATH = path.join(ROOT, "current_l5_provenance_persistence_latest.json");
const PARITY_JSON_PATH = path.join(ROOT, "provenance_persistence_parity_latest.json");
const PARITY_MD_PATH = path.join(ROOT, "provenance_persistence_parity_latest.md");

function sha256Text(text) {
  return createHash("sha256").update(String(text ?? "")).digest("hex");
}

function sha256File(filePath) {
  if (!existsSync(filePath)) return null;
  return sha256Text(readFileSync(filePath));
}

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
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

function resolvePool() {
  const host = readRequiredEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readPgPort();
  const rejectUnauthorized = resolvePgSslRejectUnauthorized();

  return new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 2,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-a3-surgical-sync-parity",
  });
}

function parseJsonLine(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return null;
  const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (!line.startsWith("{")) continue;
    try {
      const parsed = JSON.parse(line);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      // continue
    }
  }
  return null;
}

function runNodeScript(scriptPath, args, env) {
  const run = spawnSync("node", [scriptPath, ...args], {
    cwd: ROOT,
    env,
    encoding: "utf-8",
    maxBuffer: 10 * 1024 * 1024,
  });

  return {
    status: run.status ?? 1,
    stdout: String(run.stdout ?? ""),
    stderr: String(run.stderr ?? ""),
    parsed: parseJsonLine(run.stdout),
  };
}

async function resolveSchemaContext(pool) {
  const candidateSchemas = ["runtime_shadow", "staging_shadow", "tfe_shadow", "shadow"];
  const rows = await pool.query(
    `
      SELECT schema_name
      FROM information_schema.schemata
      WHERE schema_name = ANY($1::text[])
      ORDER BY array_position($1::text[], schema_name)
      LIMIT 1
    `,
    [candidateSchemas],
  );

  const chosen = String(rows.rows[0]?.schema_name ?? "").trim() || null;
  if (!chosen) {
    return {
      shadow_schema_used: false,
      search_path: "public",
      reason: "no_shadow_schema_available",
    };
  }

  return {
    shadow_schema_used: true,
    search_path: `${chosen},public`,
    reason: "shadow_schema_available",
  };
}

async function readPreExecution(pool, runId, context) {
  const runtimeCountRes = await pool.query("SELECT COUNT(*)::int AS n FROM runtime_decisions_latest");
  const runtimeRowCount = Number(runtimeCountRes.rows[0]?.n ?? 0);

  const latestRunRes = await pool.query(
    `
      SELECT run_id
      FROM runtime_refresh_runs
      ORDER BY completed_at DESC NULLS LAST, updated_at DESC NULLS LAST
      LIMIT 1
    `,
  );

  const latestRunId = String(latestRunRes.rows[0]?.run_id ?? "").trim() || null;

  const policyPath = path.join(ROOT, "pscf_policy_runtime.json");

  return {
    snapshot_artifact_path: SNAPSHOT_PATH,
    snapshot_artifact_hash_sha256: sha256File(SNAPSHOT_PATH),
    policy_artifact_path: policyPath,
    policy_artifact_hash_sha256: sha256File(policyPath),
    current_runtime_decision_row_count: runtimeRowCount,
    current_latest_runtime_run_id: latestRunId,
    run_id_for_sync_and_audit: runId,
    reader_flag_states: {
      TFE_ADVISOR_USE_PERSISTED_PROVENANCE: String(process.env.TFE_ADVISOR_USE_PERSISTED_PROVENANCE ?? "0"),
      TFE_ADVISOR_PERSISTED_PROVENANCE_STRICT: String(process.env.TFE_ADVISOR_PERSISTED_PROVENANCE_STRICT ?? "0"),
    },
    schema_context: context,
  };
}

async function main() {
  const runId =
    String(process.env.A3_RUN_ID ?? "").trim() ||
    `a3-provenance-${new Date().toISOString().replace(/[-:.]/g, "").replace("T", "-").replace("Z", "")}`;

  const baseEnv = {
    ...process.env,
    TFE_ADVISOR_USE_PERSISTED_PROVENANCE: "0",
    TFE_ADVISOR_PERSISTED_PROVENANCE_STRICT: "0",
    TFE_REFRESH_RUN_ID: runId,
    TFE_REFRESH_REQUESTED_MODE: "snapshot",
    TFE_REFRESH_TRIGGER_SOURCE: "program",
    TFE_REFRESH_REQUESTED_BY: "codex_a3_surgical",
    TFE_RUNTIME_DATA_SOURCE: "postgres",
  };

  const writerBuildHash = sha256File(SYNC_SCRIPT) ?? sha256Text("sync_runtime_postgres");
  baseEnv.TFE_PROVENANCE_WRITER_BUILD_HASH = writerBuildHash;

  const pool = resolvePool();
  let preExecution = null;

  try {
    const context = await resolveSchemaContext(pool);
    if (context.shadow_schema_used) {
      baseEnv.PGOPTIONS = `-c search_path=${context.search_path}`;
    }

    preExecution = await readPreExecution(pool, runId, context);

    const nowIso = new Date().toISOString();
    baseEnv.TFE_REFRESH_STARTED_AT = nowIso;
    baseEnv.TFE_REFRESH_COMPLETED_AT = nowIso;

    const syncRes = runNodeScript(SYNC_SCRIPT, [], baseEnv);
    if (syncRes.status !== 0) {
      throw new Error(`sync_runtime_postgres_failed:${syncRes.stderr || syncRes.stdout}`);
    }

    const parityRes = runNodeScript(PARITY_SCRIPT, ["--run-id", runId], baseEnv);
    if (parityRes.status !== 0) {
      throw new Error(`parity_audit_failed:${parityRes.stderr || parityRes.stdout}`);
    }

    const persistenceArtifact = JSON.parse(readFileSync(PERSISTENCE_ARTIFACT_PATH, "utf-8"));
    const parityArtifact = JSON.parse(readFileSync(PARITY_JSON_PATH, "utf-8"));
    const parityMarkdown = readFileSync(PARITY_MD_PATH, "utf-8");

    const out = {
      status: "pass",
      run_id: runId,
      pre_execution: preExecution,
      sync_summary: syncRes.parsed,
      parity_summary: parityRes.parsed,
      artifacts: {
        current_l5_provenance_persistence_latest_json: persistenceArtifact,
        provenance_persistence_parity_latest_json: parityArtifact,
        provenance_persistence_parity_latest_md: parityMarkdown,
      },
    };

    process.stdout.write(`${JSON.stringify(out)}\n`);
  } finally {
    await pool.end();
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : "unknown_a3_surgical_failure";
  process.stdout.write(`${JSON.stringify({ status: "fail", reason: message })}\n`);
  process.exit(1);
});
