#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import pkg from "pg";

const { Pool } = pkg;

const SHADOW_OUTPUT_PATH = path.resolve(
  process.cwd(),
  "../../backups/runtime/l5_policy_learning/shadow_candidate_results.json"
);

async function runShadowSync() {
  console.log(`[SHADOW SYNC] Starting shadow sync against candidate_l5_results...`);
  
  const pool = new Pool({
    host: process.env.PGHOST || "localhost",
    database: process.env.PGDATABASE || "postgres",
    user: process.env.PGUSER || "postgres",
    password: process.env.PGPASSWORD || "postgres",
    port: parseInt(process.env.PGPORT || "5432", 10),
  });

  try {
    const fileData = await fs.readFile(SHADOW_OUTPUT_PATH, "utf-8");
    const payload = JSON.parse(fileData);
    const evaluations = payload.evaluations || [];

    if (evaluations.length === 0) {
      console.log("[SHADOW SYNC] No evaluations found in shadow candidate file.");
      return;
    }

    await pool.query(`
      CREATE TABLE IF NOT EXISTS candidate_l5_results (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        evaluation_date TEXT,
        shadow_decision VARCHAR(50),
        s_uf NUMERIC,
        r_uf NUMERIC,
        c_k NUMERIC,
        prev_c_k NUMERIC,
        sync_timestamp TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    // Clear out old shadow runs to keep the DB clean during iterations
    await pool.query(`TRUNCATE TABLE candidate_l5_results;`);

    console.log(`[SHADOW SYNC] Inserting ${evaluations.length} records into candidate_l5_results...`);
    
    for (const record of evaluations) {
      await pool.query(
        `INSERT INTO candidate_l5_results (symbol, evaluation_date, shadow_decision, s_uf, r_uf, c_k, prev_c_k)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          record.symbol,
          record.end_date,
          record.shadow_decision,
          record.composite_metrics?.S_UF || 0,
          record.composite_metrics?.R_UF || 0,
          record.state_metrics?.C_k || 0,
          record.state_metrics?.prev_C_k || 0
        ]
      );
    }

    console.log(`[SHADOW SYNC] Successfully loaded isolated shadow results. 'active_publication_pointer' remains unaffected.`);
  } catch (err) {
    console.error(`[SHADOW SYNC] Fatal Error:`, err);
  } finally {
    await pool.end();
  }
}

runShadowSync();