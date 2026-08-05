import { Pool } from "pg";

function req(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`missing db env: ${names.join("/")}`);
}

function readPort() {
  const n = Number(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? 5432);
  if (!Number.isFinite(n)) return 5432;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return 5432;
  return whole;
}

function readSslRejectUnauthorized() {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true")
    .trim()
    .toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

async function main() {
  const runId = String(process.argv[2] ?? process.env.TFE_CLEAR_STUCK_RUN_ID ?? "").trim();
  if (!runId) {
    throw new Error("TFE_CLEAR_STUCK_RUN_ID is required");
  }

  const nowIso = new Date().toISOString();
  const pool = new Pool({
    host: req("PGHOST", "TFE_DB_HOST"),
    database: req("PGDATABASE", "TFE_DB_NAME"),
    user: req("PGUSER", "TFE_DB_USER"),
    password: req("PGPASSWORD", "TFE_DB_PASSWORD"),
    port: readPort(),
    ssl: { rejectUnauthorized: readSslRejectUnauthorized() },
    max: 2,
    connectionTimeoutMillis: 8000,
    application_name: "tfe-clear-stuck-run",
  });

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    const runRes = await client.query(
      `
        UPDATE runtime_refresh_runs
        SET completed_at = COALESCE(completed_at, NOW()),
            report_status = CASE
              WHEN report_status IS NULL OR report_status = '' OR report_status = 'running' THEN 'error'
              ELSE report_status
            END,
            updated_at = NOW()
        WHERE run_id = $1
        RETURNING run_id, report_status, started_at, completed_at
      `,
      [runId],
    );

    const statusRes = await client.query(
      "SELECT payload FROM tfe_admin_refresh_persist WHERE key = $1 FOR UPDATE",
      ["status_record_v1"],
    );

    let statusRecordUpdated = false;
    const currentPayload = statusRes.rows[0]?.payload;
    if (
      currentPayload &&
      currentPayload.status &&
      String(currentPayload.status.run_id ?? "").trim() === runId &&
      Boolean(currentPayload.status.running)
    ) {
      const nextPayload = {
        ...currentPayload,
        status: {
          ...currentPayload.status,
          running: false,
          completed_at: nowIso,
          last_error:
            "Cleared stuck scheduled run after bounded monitor max_polls_exhausted; investigate refresh child hang path.",
          completion_logged_for_run_id: runId,
        },
        updated_at_utc: nowIso,
      };

      await client.query(
        "UPDATE tfe_admin_refresh_persist SET payload = $2::jsonb, updated_at = NOW() WHERE key = $1",
        ["status_record_v1", JSON.stringify(nextPayload)],
      );
      statusRecordUpdated = true;
    }

    await client.query("COMMIT");
    process.stdout.write(
      `${JSON.stringify({
        status: "pass",
        generated_at_utc: nowIso,
        run_id: runId,
        runtime_refresh_runs_updated: runRes.rowCount,
        status_record_updated: statusRecordUpdated,
        run_row: runRes.rows[0] ?? null,
      })}\n`,
    );
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch {
      // ignore rollback failure
    }
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  process.stdout.write(
    `${JSON.stringify({
      status: "fail",
      blocking_reason: error instanceof Error ? error.message : String(error),
    })}\n`,
  );
  process.exit(1);
});
