#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { Pool } from "pg";
import {
  buildIdentityWitness,
  buildPersistedProvenanceRecord,
  loadPolicyRuntimeArtifact,
  minBarsForAccumulate,
  stableStringify,
} from "./runtime_decision_provenance.mjs";

const DEFAULT_DB_PORT = 5432;
const DEFAULT_SAMPLE_LIMIT = 300;
const MAX_SAMPLE_LIMIT = 50_000;

const DECISION_MISMATCH_CLASSES = [
  "key chain mismatch",
  "matched key mismatch",
  "fallback level mismatch",
  "anomaly mismatch",
  "epoch mismatch",
  "timestamp/order mismatch",
];

function resolveWorkspaceRoot() {
  const configured = String(process.env.TFE_WORKSPACE_ROOT ?? "").trim();
  const candidates = [
    configured,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "../.."),
    "/workspaces/Tao_Financial_Engine",
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .map((value) => path.resolve(value));

  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "run_refresh_with_l5_learning.py"))) {
      return candidate;
    }
  }

  return path.resolve(process.cwd(), "..");
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
    application_name: "tfe-provenance-decision-parity",
  });
}

function parseArgs(argv) {
  const out = {
    runId: "",
    sampleLimit: DEFAULT_SAMPLE_LIMIT,
    jsonOut: "",
    mdOut: "",
  };

  for (let i = 0; i < argv.length; i += 1) {
    const key = String(argv[i] ?? "").trim();
    const next = String(argv[i + 1] ?? "").trim();

    if (key === "--run-id" && next) {
      out.runId = next;
      i += 1;
      continue;
    }
    if (key === "--sample-limit" && next) {
      const n = Number(next);
      if (Number.isFinite(n)) {
        out.sampleLimit = Math.min(MAX_SAMPLE_LIMIT, Math.max(10, Math.floor(n)));
      }
      i += 1;
      continue;
    }
    if (key === "--json-out" && next) {
      out.jsonOut = next;
      i += 1;
      continue;
    }
    if (key === "--md-out" && next) {
      out.mdOut = next;
      i += 1;
      continue;
    }
  }

  return out;
}

function initMismatchCounts() {
  const out = {};
  for (const name of DECISION_MISMATCH_CLASSES) {
    out[name] = 0;
  }
  return out;
}

function initExamplesByClass() {
  const out = {};
  for (const name of DECISION_MISMATCH_CLASSES) {
    out[name] = [];
  }
  return out;
}

function normalizeIso(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return new Date(parsed).toISOString();
}

function toRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value;
}

function toArray(value) {
  return Array.isArray(value) ? value : [];
}

function classifyDecisionMismatches({ persisted, recomputed, snapshotTimestampUtc }) {
  const classes = [];

  if (stableStringify(toArray(persisted.candidate_key_chain_json)) !== stableStringify(toArray(recomputed.candidate_key_chain_json))) {
    classes.push("key chain mismatch");
  }

  if (String(persisted.matched_key ?? "") !== String(recomputed.matched_key ?? "")) {
    classes.push("matched key mismatch");
  }

  if (String(persisted.match_level ?? "") !== String(recomputed.match_level ?? "")) {
    classes.push("fallback level mismatch");
  }

  const persistedAnomaly = toRecord(persisted.anomaly_flags_used_json);
  const recomputedAnomaly = toRecord(recomputed.anomaly_flags_used_json);
  if (stableStringify(persistedAnomaly) !== stableStringify(recomputedAnomaly)) {
    classes.push("anomaly mismatch");
  }

  const persistedEpoch = toRecord(toRecord(persisted.epoch_components_used_json).components);
  const recomputedEpoch = toRecord(toRecord(recomputed.epoch_components_used_json).components);
  if (stableStringify(persistedEpoch) !== stableStringify(recomputedEpoch)) {
    classes.push("epoch mismatch");
  }

  const decisionTs = Date.parse(String(persisted.decision_timestamp_utc ?? ""));
  const snapshotTs = Date.parse(String(snapshotTimestampUtc ?? ""));
  const timestampOrderValid = Number.isFinite(decisionTs) && Number.isFinite(snapshotTs) && decisionTs >= snapshotTs;
  if (!timestampOrderValid) {
    classes.push("timestamp/order mismatch");
  }

  return classes;
}

function renderMarkdown(report) {
  const mismatchRows = DECISION_MISMATCH_CLASSES
    .map((name) => `| ${name} | ${report.decision_provenance_parity.mismatch_classes[name] ?? 0} |`)
    .join("\n");

  const examples = report.decision_provenance_parity.examples || [];
  const exampleRows = examples
    .slice(0, 20)
    .map((item) => {
      const classes = Array.isArray(item.mismatch_classes) ? item.mismatch_classes.join(", ") : "";
      return `| ${item.ticker || ""} | ${item.run_id || ""} | ${classes} | ${item.persisted_match_level || ""} | ${item.recomputed_match_level || ""} |`;
    })
    .join("\n");

  const byClassSections = DECISION_MISMATCH_CLASSES.map((cls) => {
    const samples = ((report.decision_provenance_parity.examples_by_class || {})[cls] || []).slice(0, 5);
    const lines =
      samples.length > 0
        ? samples.map((s) => `- ${s.ticker} | ${s.run_id} | persisted=${s.persisted_match_level || ""} | recomputed=${s.recomputed_match_level || ""}`).join("\n")
        : "- none";
    return `### ${cls}\n${lines}`;
  }).join("\n\n");

  return [
    "# Provenance Persistence Parity (Latest)",
    "",
    `- **Generated (UTC)**: \`${report.generated_at_utc}\``,
    `- **Run ID**: \`${report.run_id ?? ""}\``,
    `- **Status**: \`${report.status}\``,
    `- **Context Frozen**: ${report.context_frozen.pass ? "true" : "false"}`,
    "",
    "## Decision Provenance Parity",
    "",
    `- **Rows Sampled**: ${report.decision_provenance_parity.rows_sampled}`,
    `- **Runtime Decision Row Count**: ${report.decision_provenance_parity.runtime_decision_row_count}`,
    `- **Provenance Row Count**: ${report.decision_provenance_parity.provenance_row_count}`,
    `- **Completeness Rate**: ${report.decision_provenance_parity.completeness_rate}`,
    `- **Rows With Persisted Provenance**: ${report.decision_provenance_parity.rows_with_persisted}`,
    `- **Matched Rows**: ${report.decision_provenance_parity.matched_rows}`,
    `- **Rows With Any Mismatch**: ${report.decision_provenance_parity.rows_with_any_mismatch}`,
    `- **Mismatch Rate**: ${report.decision_provenance_parity.mismatch_rate}`,
    `- **Identity Witness Mismatches**: ${report.decision_provenance_parity.identity_witness_mismatch_count}`,
    "",
    "| Mismatch Class | Count |",
    "|---|---|",
    mismatchRows,
    "",
    "## Rollout Gate",
    "",
    `- **Pass**: ${report.rollout_gate.pass ? "true" : "false"}`,
    `- **Blocking Classes**: ${(report.rollout_gate.blocking_classes || []).join(", ") || "none"}`,
    `- **Phase 3 Blocked**: ${report.conclusion.phase_3_blocked ? "true" : "false"}`,
    `- **Block Reasons**: ${(report.conclusion.block_reasons || []).join(", ") || "none"}`,
    "",
    "## Serving Provenance Parity",
    "",
    `- **Status**: \`${report.serving_provenance_parity.status}\``,
    `- **Reason**: ${report.serving_provenance_parity.reason}`,
    "",
    "## Example Rows",
    "",
    "| Ticker | Run ID | Mismatch Classes | Persisted Match Level | Recomputed Match Level |",
    "|---|---|---|---|---|",
    exampleRows || "|  |  |  |  |  |",
    "",
    "## Examples By Mismatch Class",
    "",
    byClassSections,
    "",
  ].join("\n");
}

async function resolveRunId(client, requestedRunId) {
  if (requestedRunId) return requestedRunId;

  const res = await client.query(
    `
      SELECT run_id
      FROM runtime_refresh_runs
      ORDER BY completed_at DESC NULLS LAST, updated_at DESC NULLS LAST
      LIMIT 1
    `,
  );
  return String(res.rows[0]?.run_id ?? "").trim() || null;
}

async function runAudit(config) {
  const root = resolveWorkspaceRoot();
  const jsonOut = config.jsonOut
    ? path.resolve(config.jsonOut)
    : path.join(root, "provenance_persistence_parity_latest.json");
  const mdOut = config.mdOut
    ? path.resolve(config.mdOut)
    : path.join(root, "provenance_persistence_parity_latest.md");

  const report = {
    analysis_name: "A3_phase2_provenance_parity_decision_only",
    generated_at_utc: new Date().toISOString(),
    run_id: null,
    status: "error",
    context_frozen: {
      pass: false,
      as_of_utc: new Date().toISOString(),
      policy_artifact_hash_sha256: null,
      feature_flags: {
        min_bars_for_accumulate: minBarsForAccumulate(),
        anomaly_fallback_enabled: String(process.env.TFE_RECOMMENDATIONS_ANOMALY_FALLBACK ?? "false"),
      },
      failures: [],
    },
    decision_provenance_parity: {
      rows_sampled: 0,
      rows_with_persisted: 0,
      matched_rows: 0,
      rows_with_any_mismatch: 0,
      mismatch_count: 0,
      mismatch_rate: 0,
      runtime_decision_row_count: 0,
      provenance_row_count: 0,
      completeness_rate: null,
      mismatch_classes: initMismatchCounts(),
      identity_witness_mismatch_count: 0,
      examples: [],
      examples_by_class: initExamplesByClass(),
    },
    serving_provenance_parity: {
      status: "deferred",
      reason:
        "Serving provenance parity is intentionally deferred. It must run under fixed as_of_utc and route-level freshness/degraded context.",
    },
    rollout_gate: {
      pass: false,
      blocking_classes: ["key chain mismatch", "matched key mismatch", "fallback level mismatch"],
    },
    conclusion: {
      phase_3_blocked: true,
      block_reasons: ["audit_not_run"],
    },
    error: null,
  };

  let pool = null;

  try {
    pool = resolvePool();
    const client = await pool.connect();

    try {
      const runId = await resolveRunId(client, config.runId);
      if (!runId) {
        throw new Error("No runtime run_id found for provenance parity audit.");
      }

      report.run_id = runId;
      const persistenceArtifactPath = path.join(root, "current_l5_provenance_persistence_latest.json");
      let completenessRate = null;
      let persistenceArtifactRunId = null;
      if (existsSync(persistenceArtifactPath)) {
        try {
          const artifact = JSON.parse(readFileSync(persistenceArtifactPath, "utf-8"));
          completenessRate = Number.isFinite(Number(artifact?.completeness_rate))
            ? Number(artifact.completeness_rate)
            : null;
          persistenceArtifactRunId = String(artifact?.run_id ?? "").trim() || null;
        } catch {
          completenessRate = null;
          persistenceArtifactRunId = null;
        }
      }

      const countsRes = await client.query(
        `
          SELECT
            (SELECT COUNT(*)::int FROM runtime_decisions_latest WHERE run_id = $1) AS runtime_decision_row_count,
            (SELECT COUNT(*)::int FROM runtime_decision_provenance_latest WHERE run_id = $1) AS provenance_row_count
        `,
        [runId],
      );
      const countsRow = countsRes.rows[0] ?? {};
      const runtimeDecisionRowCount = Number(countsRow.runtime_decision_row_count ?? 0);
      const provenanceRowCount = Number(countsRow.provenance_row_count ?? 0);

      const policyRuntime = loadPolicyRuntimeArtifact(root);

      const rowsRes = await client.query(
        `
          SELECT
            d.ticker,
            d.run_id,
            d.generated_at_utc,
            d.snapshot_row_json,
            p.snapshot_timestamp_utc,
            p.decision_timestamp_utc,
            p.snapshot_row_digest_sha256,
            p.policy_artifact_hash_sha256,
            p.candidate_key_chain_json,
            p.matched_key,
            p.match_level,
            p.anomaly_flags_used_json,
            p.epoch_components_used_json,
            p.provenance_valid
          FROM runtime_decisions_latest d
          LEFT JOIN runtime_decision_provenance_latest p
            ON p.run_id = d.run_id
           AND p.ticker = d.ticker
          WHERE d.run_id = $1
          ORDER BY d.ticker ASC
          LIMIT $2
        `,
        [runId, config.sampleLimit],
      );

      const persistedPolicyHashes = new Set();
      for (const row of rowsRes.rows) {
        const hash = String(row.policy_artifact_hash_sha256 ?? "").trim();
        if (hash) persistedPolicyHashes.add(hash);
      }

      if (persistedPolicyHashes.size !== 1) {
        report.context_frozen.failures.push(
          `policy_artifact_hash_set_size_invalid:${persistedPolicyHashes.size}:expected=1`,
        );
      }

      const expectedPolicyHash = persistedPolicyHashes.size === 1 ? Array.from(persistedPolicyHashes)[0] : null;
      report.context_frozen.policy_artifact_hash_sha256 = expectedPolicyHash;

      if (!expectedPolicyHash) {
        report.context_frozen.failures.push("policy_artifact_hash_missing");
      } else if (expectedPolicyHash !== String(policyRuntime.policy_artifact_hash_sha256 ?? "")) {
        report.context_frozen.failures.push(
          `policy_hash_context_mismatch:persisted=${expectedPolicyHash}:current=${String(policyRuntime.policy_artifact_hash_sha256 ?? "")}`,
        );
      }

      report.context_frozen.pass = report.context_frozen.failures.length === 0;

      const mismatches = initMismatchCounts();
      const examplesByClass = initExamplesByClass();
      const examples = [];
      let rowsWithPersisted = 0;
      let matchedRows = 0;
      let rowsWithAnyMismatch = 0;
      let identityWitnessMismatchCount = 0;

      for (const dbRow of rowsRes.rows) {
        const ticker = String(dbRow.ticker ?? "").trim().toUpperCase();
        const snapshotRow = toRecord(dbRow.snapshot_row_json);
        const generatedAtUtc = normalizeIso(dbRow.generated_at_utc) ?? new Date().toISOString();
        const snapshotTimestampUtc = normalizeIso(dbRow.snapshot_timestamp_utc) ?? generatedAtUtc;

        const recomputed = buildPersistedProvenanceRecord({
          row: { ...snapshotRow, ticker },
          ticker,
          runId,
          generatedAtUtc,
          snapshotTimestampUtc,
          runtimeSyncCompletedUtc: generatedAtUtc,
          policyRuntime,
          minBars: minBarsForAccumulate(),
          writerBuildHash: null,
        });

        const persisted = {
          run_id: String(dbRow.run_id ?? runId),
          ticker,
          snapshot_row_digest_sha256: String(dbRow.snapshot_row_digest_sha256 ?? ""),
          policy_artifact_hash_sha256: String(dbRow.policy_artifact_hash_sha256 ?? ""),
          candidate_key_chain_json: toArray(dbRow.candidate_key_chain_json),
          matched_key: dbRow.matched_key,
          match_level: dbRow.match_level,
          anomaly_flags_used_json: toRecord(dbRow.anomaly_flags_used_json),
          epoch_components_used_json: toRecord(dbRow.epoch_components_used_json),
          decision_timestamp_utc: normalizeIso(dbRow.decision_timestamp_utc),
          provenance_valid: dbRow.provenance_valid === true,
        };

        if (persisted.provenance_valid) {
          rowsWithPersisted += 1;
        }

        const persistedWitness = buildIdentityWitness(persisted);
        const recomputedWitness = buildIdentityWitness(recomputed);
        if (stableStringify(persistedWitness) !== stableStringify(recomputedWitness)) {
          identityWitnessMismatchCount += 1;
        }

        const mismatchClasses = classifyDecisionMismatches({
          persisted,
          recomputed,
          snapshotTimestampUtc,
        });

        if (mismatchClasses.length > 0) {
          rowsWithAnyMismatch += 1;
          for (const cls of mismatchClasses) {
            mismatches[cls] = Number(mismatches[cls] ?? 0) + 1;
            const bucket = examplesByClass[cls] || [];
            if (bucket.length < 8) {
              bucket.push({
                ticker,
                run_id: runId,
                persisted_match_level: String(persisted.match_level ?? ""),
                recomputed_match_level: String(recomputed.match_level ?? ""),
                persisted_matched_key: String(persisted.matched_key ?? ""),
                recomputed_matched_key: String(recomputed.matched_key ?? ""),
              });
            }
            examplesByClass[cls] = bucket;
          }

          if (examples.length < 40) {
            examples.push({
              ticker,
              run_id: runId,
              mismatch_classes: mismatchClasses,
              persisted_match_level: String(persisted.match_level ?? ""),
              recomputed_match_level: String(recomputed.match_level ?? ""),
              persisted_matched_key: String(persisted.matched_key ?? ""),
              recomputed_matched_key: String(recomputed.matched_key ?? ""),
            });
          }
        } else {
          matchedRows += 1;
        }
      }

      const rowsSampled = rowsRes.rows.length;
      const mismatchCount = Object.values(mismatches).reduce((sum, value) => sum + Number(value ?? 0), 0);

      report.decision_provenance_parity.rows_sampled = rowsSampled;
      report.decision_provenance_parity.runtime_decision_row_count = runtimeDecisionRowCount;
      report.decision_provenance_parity.provenance_row_count = provenanceRowCount;
      report.decision_provenance_parity.completeness_rate = completenessRate;
      report.decision_provenance_parity.rows_with_persisted = rowsWithPersisted;
      report.decision_provenance_parity.matched_rows = matchedRows;
      report.decision_provenance_parity.rows_with_any_mismatch = rowsWithAnyMismatch;
      report.decision_provenance_parity.mismatch_count = mismatchCount;
      report.decision_provenance_parity.mismatch_rate = rowsSampled > 0 ? Number((rowsWithAnyMismatch / rowsSampled).toFixed(6)) : 0;
      report.decision_provenance_parity.mismatch_classes = mismatches;
      report.decision_provenance_parity.identity_witness_mismatch_count = identityWitnessMismatchCount;
      report.decision_provenance_parity.examples = examples;
      report.decision_provenance_parity.examples_by_class = examplesByClass;

      const blockingClasses = [
        "key chain mismatch",
        "matched key mismatch",
        "fallback level mismatch",
      ].filter((name) => Number(mismatches[name] ?? 0) > 0);

      report.rollout_gate = {
        pass: report.context_frozen.pass && blockingClasses.length === 0,
        blocking_classes: blockingClasses,
      };
      report.conclusion = {
        phase_3_blocked: !(
          report.context_frozen.pass &&
          blockingClasses.length === 0 &&
          runtimeDecisionRowCount === provenanceRowCount &&
          completenessRate === 1
        ),
        block_reasons:
          report.context_frozen.pass &&
          blockingClasses.length === 0 &&
          runtimeDecisionRowCount === provenanceRowCount &&
          completenessRate === 1
            ? []
            : [
                ...report.context_frozen.failures.map((item) => `frozen_context:${item}`),
                ...(runtimeDecisionRowCount !== provenanceRowCount
                  ? [`row_count_mismatch:runtime_decision=${runtimeDecisionRowCount}:provenance=${provenanceRowCount}`]
                  : []),
                ...(completenessRate !== 1
                  ? [`completeness_not_100:${completenessRate === null ? "null" : completenessRate}`]
                  : []),
                ...(persistenceArtifactRunId && persistenceArtifactRunId !== runId
                  ? [`persistence_artifact_run_id_mismatch:${persistenceArtifactRunId}!=${runId}`]
                  : []),
                ...blockingClasses.map((item) => `mismatch_class:${item}`),
              ],
      };

      report.status = report.context_frozen.pass ? "ok" : "blocked_context_not_frozen";
    } finally {
      client.release();
    }
  } catch (error) {
    report.status = "error";
    report.error = error instanceof Error ? error.message : "Unknown provenance parity audit failure.";
  } finally {
    if (pool) {
      await pool.end();
    }
  }

  writeFileSync(jsonOut, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
  writeFileSync(mdOut, renderMarkdown(report), "utf-8");

  process.stdout.write(`${JSON.stringify({ status: report.status, json_out: jsonOut, md_out: mdOut })}\n`);

  if (report.status === "error") {
    process.exit(1);
  }
}

const args = parseArgs(process.argv.slice(2));
runAudit(args).catch((error) => {
  const message = error instanceof Error ? error.message : "Unknown provenance parity audit failure.";
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
