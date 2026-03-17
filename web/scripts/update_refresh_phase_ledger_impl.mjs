#!/usr/bin/env node

import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const RUNS_TABLE = "runtime_refresh_runs";
const PHASES_TABLE = "runtime_refresh_run_phases";

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
    application_name: "tfe-refresh-phase-ledger",
  });
}

function toTextOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function toIsoOrNull(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

async function readPayload() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  const raw = Buffer.concat(chunks).toString("utf-8").trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

async function ensureSchema(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS ${RUNS_TABLE} (
      run_id TEXT PRIMARY KEY,
      mode TEXT,
      trigger_source TEXT,
      requested_by TEXT,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      report_generated_at_utc TIMESTAMPTZ,
      rows_written INTEGER,
      report_status TEXT,
      optimizer_short_cycle TEXT,
      optimizer_cycle_requested_runs INTEGER,
      optimizer_cycle_completed_runs INTEGER,
      optimizer_session_id TEXT,
      optimizer_target_return_lift_pct DOUBLE PRECISION,
      optimizer_best_score DOUBLE PRECISION,
      optimizer_target_met BOOLEAN,
      epoch_library_confidence_schema TEXT,
      epoch_library_status TEXT,
      validation_status TEXT,
      validation_report_path TEXT,
      bundle_generated_at_utc TIMESTAMPTZ,
      snapshot_publication_id TEXT,
      quote_publication_id TEXT,
      quote_binding_status TEXT,
      activation_state TEXT,
      serving_state TEXT,
      blocking_reason_code TEXT,
      blocking_reason_detail TEXT,
      failure_code TEXT,
      failure_detail TEXT,
      current_phase TEXT,
      current_phase_process_status TEXT,
      current_phase_started_at TIMESTAMPTZ,
      current_phase_completed_at TIMESTAMPTZ,
      current_phase_last_heartbeat_at TIMESTAMPTZ,
      current_phase_failure_code TEXT,
      current_phase_failure_detail TEXT,
      is_active_publication BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await client.query(`
    ALTER TABLE ${RUNS_TABLE}
    ADD COLUMN IF NOT EXISTS bundle_generated_at_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS snapshot_publication_id TEXT,
    ADD COLUMN IF NOT EXISTS quote_publication_id TEXT,
    ADD COLUMN IF NOT EXISTS quote_binding_status TEXT,
    ADD COLUMN IF NOT EXISTS activation_state TEXT,
    ADD COLUMN IF NOT EXISTS serving_state TEXT,
    ADD COLUMN IF NOT EXISTS blocking_reason_code TEXT,
    ADD COLUMN IF NOT EXISTS blocking_reason_detail TEXT,
    ADD COLUMN IF NOT EXISTS failure_code TEXT,
    ADD COLUMN IF NOT EXISTS failure_detail TEXT,
    ADD COLUMN IF NOT EXISTS current_phase TEXT,
    ADD COLUMN IF NOT EXISTS current_phase_process_status TEXT,
    ADD COLUMN IF NOT EXISTS current_phase_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS current_phase_completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS current_phase_last_heartbeat_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS current_phase_failure_code TEXT,
    ADD COLUMN IF NOT EXISTS current_phase_failure_detail TEXT,
    ADD COLUMN IF NOT EXISTS is_active_publication BOOLEAN NOT NULL DEFAULT FALSE
  `);

  await client.query(`
    CREATE TABLE IF NOT EXISTS ${PHASES_TABLE} (
      run_id TEXT NOT NULL,
      phase_name TEXT NOT NULL,
      input_contract JSONB,
      process_status TEXT NOT NULL,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      output_contract JSONB,
      failure_code TEXT,
      failure_detail TEXT,
      last_heartbeat_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (run_id, phase_name),
      CONSTRAINT runtime_refresh_run_phases_run_id_fkey
        FOREIGN KEY (run_id) REFERENCES ${RUNS_TABLE}(run_id)
        ON DELETE CASCADE
    )
  `);

  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_run_id
    ON ${PHASES_TABLE} (run_id)
  `);

  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_running
    ON ${PHASES_TABLE} (run_id, process_status, last_heartbeat_at DESC)
  `);
}

async function upsertPhaseState(client, payload) {
  const runId = toTextOrNull(payload.run_id ?? process.env.TFE_REFRESH_RUN_ID);
  const phaseName = toTextOrNull(payload.phase_name);
  const processStatus = toTextOrNull(payload.process_status);

  if (!runId) throw new Error("Missing run_id for refresh phase ledger update.");
  if (!phaseName) throw new Error("Missing phase_name for refresh phase ledger update.");
  if (!processStatus) throw new Error("Missing process_status for refresh phase ledger update.");

  const startedAtIso = toIsoOrNull(payload.started_at);
  const completedAtIso = toIsoOrNull(payload.completed_at);
  const lastHeartbeatAtIso = toIsoOrNull(payload.last_heartbeat_at ?? payload.started_at);
  const failureCode = toTextOrNull(payload.failure_code);
  const failureDetail = toTextOrNull(payload.failure_detail);
  const inputContract = payload.input_contract ?? null;
  const outputContract = payload.output_contract ?? null;

  await client.query(
    `
      INSERT INTO ${RUNS_TABLE} (
        run_id,
        started_at,
        report_status,
        current_phase,
        current_phase_process_status,
        current_phase_started_at,
        current_phase_completed_at,
        current_phase_last_heartbeat_at,
        current_phase_failure_code,
        current_phase_failure_detail,
        created_at,
        updated_at
      )
      VALUES (
        $1,
        $2::timestamptz,
        'running',
        $3,
        $4,
        $2::timestamptz,
        $5::timestamptz,
        COALESCE($6::timestamptz, $2::timestamptz),
        $7,
        $8,
        NOW(),
        NOW()
      )
      ON CONFLICT (run_id)
      DO NOTHING
    `,
    [
      runId,
      startedAtIso,
      phaseName,
      processStatus,
      completedAtIso,
      lastHeartbeatAtIso,
      failureCode,
      failureDetail,
    ],
  );

  await client.query(
    `
      INSERT INTO ${PHASES_TABLE} (
        run_id,
        phase_name,
        input_contract,
        process_status,
        started_at,
        completed_at,
        output_contract,
        failure_code,
        failure_detail,
        last_heartbeat_at,
        updated_at
      )
      VALUES (
        $1,
        $2,
        $3::jsonb,
        $4,
        $5::timestamptz,
        $6::timestamptz,
        $7::jsonb,
        $8,
        $9,
        $10::timestamptz,
        NOW()
      )
      ON CONFLICT (run_id, phase_name)
      DO UPDATE SET
        input_contract = COALESCE(EXCLUDED.input_contract, ${PHASES_TABLE}.input_contract),
        process_status = EXCLUDED.process_status,
        started_at = COALESCE(EXCLUDED.started_at, ${PHASES_TABLE}.started_at),
        completed_at = EXCLUDED.completed_at,
        output_contract = COALESCE(EXCLUDED.output_contract, ${PHASES_TABLE}.output_contract),
        failure_code = EXCLUDED.failure_code,
        failure_detail = EXCLUDED.failure_detail,
        last_heartbeat_at = COALESCE(EXCLUDED.last_heartbeat_at, ${PHASES_TABLE}.last_heartbeat_at),
        updated_at = NOW()
    `,
    [
      runId,
      phaseName,
      inputContract === null ? null : JSON.stringify(inputContract),
      processStatus,
      startedAtIso,
      completedAtIso,
      outputContract === null ? null : JSON.stringify(outputContract),
      failureCode,
      failureDetail,
      lastHeartbeatAtIso,
    ],
  );

  await client.query(
    `
      UPDATE ${RUNS_TABLE}
      SET current_phase = $2,
          current_phase_process_status = $3,
          current_phase_started_at = COALESCE($4::timestamptz, current_phase_started_at),
          current_phase_completed_at = $5::timestamptz,
          current_phase_last_heartbeat_at = COALESCE($6::timestamptz, current_phase_last_heartbeat_at),
          current_phase_failure_code = $7,
          current_phase_failure_detail = $8,
          failure_code = CASE
            WHEN $3 IN ('failed', 'blocked') THEN COALESCE($7, failure_code)
            ELSE failure_code
          END,
          failure_detail = CASE
            WHEN $3 IN ('failed', 'blocked') THEN COALESCE($8, failure_detail)
            ELSE failure_detail
          END,
          updated_at = NOW()
      WHERE run_id = $1
    `,
    [
      runId,
      phaseName,
      processStatus,
      startedAtIso,
      completedAtIso,
      lastHeartbeatAtIso,
      failureCode,
      failureDetail,
    ],
  );

  return {
    ok: true,
    run_id: runId,
    phase_name: phaseName,
    process_status: processStatus,
  };
}

async function main() {
  const payload = await readPayload();
  const pool = resolvePool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");
    await ensureSchema(client);
    const result = await upsertPhaseState(client, payload);
    await client.query("COMMIT");
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch {
      // Rollback failure should not hide the original ledger error.
    }
    const message = error instanceof Error ? error.message : "Unknown refresh phase ledger failure.";
    process.stderr.write(`refresh_phase_ledger_update_failed: ${message}\n`);
    process.exitCode = 1;
  } finally {
    client.release();
    await pool.end();
  }
}

await main();
