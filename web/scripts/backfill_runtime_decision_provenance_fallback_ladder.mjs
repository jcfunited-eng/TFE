#!/usr/bin/env node

import { Pool } from "pg";
import { deriveTypedFallbackLadderLevel } from "./runtime_decision_provenance.mjs";

const DEFAULT_DB_PORT = 5432;

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
    application_name: "tfe-a4-fallback-ladder-backfill",
  });
}

function parseArgs(argv) {
  const out = { runId: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const key = String(argv[i] ?? "").trim();
    const next = String(argv[i + 1] ?? "").trim();
    if (key === "--run-id" && next) {
      out.runId = next;
      i += 1;
    }
  }
  return out;
}

function parseStringArray(payload) {
  if (!Array.isArray(payload)) return [];
  const out = [];
  for (const item of payload) {
    const text = String(item ?? "").trim();
    if (!text) continue;
    out.push(text);
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const runId = String(args.runId ?? "").trim();
  if (!runId) {
    throw new Error("run_id_required");
  }

  const pool = resolvePool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");
    await client.query(`
      ALTER TABLE runtime_decision_provenance_latest
      ADD COLUMN IF NOT EXISTS fallback_ladder_level TEXT
    `);

    const result = await client.query(
      `
        SELECT run_id, ticker, candidate_key_chain_json, matched_key, decision_reason_code
        FROM runtime_decision_provenance_latest
        WHERE run_id = $1
        ORDER BY ticker ASC
      `,
      [runId],
    );

    const levelCounts = {};
    for (const row of result.rows) {
      const candidateKeyChain = parseStringArray(row.candidate_key_chain_json);
      const matchedKey = String(row.matched_key ?? "").trim();
      const matchedIndex = matchedKey ? candidateKeyChain.indexOf(matchedKey) : -1;
      const fallbackLadderLevel = deriveTypedFallbackLadderLevel({
        decisionReasonCode: row.decision_reason_code,
        matchedIndex,
      });
      levelCounts[fallbackLadderLevel] = Number(levelCounts[fallbackLadderLevel] ?? 0) + 1;

      await client.query(
        `
          UPDATE runtime_decision_provenance_latest
          SET
            fallback_ladder_level = $3,
            provenance_json = jsonb_set(
              COALESCE(provenance_json, '{}'::jsonb),
              '{fallback_ladder_level}',
              to_jsonb($3::text),
              true
            ),
            updated_at = NOW()
          WHERE run_id = $1
            AND ticker = $2
        `,
        [runId, row.ticker, fallbackLadderLevel],
      );
    }

    await client.query("COMMIT");

    process.stdout.write(
      `${JSON.stringify({
        status: "ok",
        run_id: runId,
        rows_total: result.rows.length,
        updated_rows: result.rows.length,
        level_counts: levelCounts,
      })}\n`,
    );
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch {
      // ignore rollback errors
    }
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : "unknown_backfill_failure";
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
