#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  TYPED_FALLBACK_LEVELS,
  TYPED_FALLBACK_ORTHOGONAL_FLAGS,
  computeDecisionTrace,
  loadPolicyRuntimeArtifact,
  minBarsForAccumulate,
  sha256Hex,
} from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const HORIZONS = [5, 20, 60];
const OUTCOME_SCORING_CONTRACT =
  "Outcome-over-index and mean_excess_vs_spy remain assessed-only in CP-0: only structurally mapped policy decisions are scored. Fallback levels are reported separately and are not silently promoted into assessed quality.";

function resolveWorkspaceRoot() {
  const configured = String(process.env.TFE_WORKSPACE_ROOT ?? "").trim();
  const candidates = [
    configured,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "../.."),
    ROOT_FALLBACK,
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

function parseJsonText(text, allowNonFinite = false) {
  const raw = String(text ?? "");
  try {
    return JSON.parse(raw);
  } catch (error) {
    if (!allowNonFinite) {
      throw error;
    }
    const normalized = raw
      .replace(/\bNaN\b/g, "null")
      .replace(/\b-Infinity\b/g, "null")
      .replace(/\bInfinity\b/g, "null");
    return JSON.parse(normalized);
  }
}

function readJson(filePath, allowNonFinite = false) {
  return parseJsonText(readFileSync(filePath, "utf-8"), allowNonFinite);
}

function writeJson(filePath, payload) {
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

function toFinite(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function percentRate(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number((count / total).toFixed(6));
}

function percentPct(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function average(values) {
  const usable = values.filter((value) => Number.isFinite(value));
  if (usable.length === 0) return null;
  return Number((usable.reduce((sum, value) => sum + value, 0) / usable.length).toFixed(6));
}

function levelTemplate() {
  const out = {};
  for (const level of TYPED_FALLBACK_LEVELS) {
    out[level.id] = {
      row_count: 0,
      rate: 0,
      pct: 0,
      decision_reason_codes: {},
      fallback_reason_codes: {},
      legacy_match_levels: {},
      matched_exact_true_count: 0,
      anomaly_flag_count: 0,
    };
  }
  return out;
}

function qualityLevelTemplate() {
  const out = {};
  for (const level of TYPED_FALLBACK_LEVELS) {
    out[level.id] = {
      level_order: level.order,
      snapshot_row_count: 0,
      snapshot_rate: 0,
      snapshot_pct: 0,
      scored_under_current_contract: level.quality_assessed_under_current_contract,
      assessed_row_count: 0,
      excluded_row_count: 0,
      avg_outcome_over_index_pct: null,
      avg_mean_excess_vs_spy: null,
      horizon_outcome_over_index_pct: {
        "5": null,
        "20": null,
        "60": null,
      },
      horizon_mean_excess_vs_spy: {
        "5": null,
        "20": null,
        "60": null,
      },
      notes: [],
    };
  }
  return out;
}

function parseSnapshotRows(snapshotPath) {
  const payload = readJson(snapshotPath, true);
  if (Array.isArray(payload)) return payload.filter((row) => row && typeof row === "object");
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) {
    return payload.rows.filter((row) => row && typeof row === "object");
  }
  return [];
}

function parseCsvRows(csvPath) {
  const raw = readFileSync(csvPath, "utf-8").trim();
  if (!raw) return [];
  const lines = raw.split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines
    .filter(Boolean)
    .map((line) => {
      const cols = line.split(",");
      const row = {};
      headers.forEach((header, index) => {
        row[header] = cols[index] ?? "";
      });
      return row;
    });
}

function upperBound(sortedValues, target) {
  let low = 0;
  let high = sortedValues.length;
  while (low < high) {
    const mid = low + Math.floor((high - low) / 2);
    if (sortedValues[mid] <= target) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

function parseIsoMs(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return null;
  return Math.trunc(parsed);
}

function spyForwardReturn(spyTs, spyClose, entryTs, horizon) {
  const idx = upperBound(spyTs, entryTs) - 1;
  if (idx < 0) return null;
  const j = idx + horizon;
  if (j >= spyClose.length) return null;
  const c0 = Number(spyClose[idx]);
  const c1 = Number(spyClose[j]);
  if (!Number.isFinite(c0) || !Number.isFinite(c1) || c0 <= 0) return null;
  return Number((c1 / c0 - 1).toFixed(12));
}

function decisionReturn(decision, forwardReturn) {
  if (decision === "Accumulate") return forwardReturn;
  if (decision === "Avoid") return -forwardReturn;
  return 0;
}

function loadPolicyRuntimeFromPath(policyPath) {
  const raw = readFileSync(policyPath, "utf-8");
  const payload = JSON.parse(raw);
  const cells = payload && typeof payload === "object" && payload.cells && typeof payload.cells === "object" ? payload.cells : {};
  return {
    source_path: policyPath,
    policy_artifact_id: path.basename(policyPath),
    policy_artifact_hash_sha256: sha256Hex(raw),
    policy_source_mode: "runtime_file",
    generated_at_utc: typeof payload?.generated_at_utc === "string" ? payload.generated_at_utc : null,
    cells,
  };
}

function withTemporaryEnv(key, value, fn) {
  const hadOriginal = Object.prototype.hasOwnProperty.call(process.env, key);
  const original = process.env[key];
  if (value === null || value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = String(value);
  }

  try {
    return fn();
  } finally {
    if (hadOriginal) {
      process.env[key] = original;
    } else {
      delete process.env[key];
    }
  }
}

function updateBucketCount(bucket, key) {
  const normalized = String(key ?? "").trim() || "null";
  bucket[normalized] = Number(bucket[normalized] ?? 0) + 1;
}

function buildRuntimeSemantics(snapshotRows, policyRuntime, minBars, anomalyFallbackEnabled, persistenceArtifact) {
  const levels = levelTemplate();
  let totalRows = 0;
  let classifiedRows = 0;

  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", anomalyFallbackEnabled ? "1" : "0", () => {
    for (const row of snapshotRows) {
      const trace = computeDecisionTrace(row, policyRuntime, minBars);
      totalRows += 1;
      const level = trace.fallbackLadderLevel;
      const bucket = levels[level];
      if (!bucket) continue;
      classifiedRows += 1;
      bucket.row_count += 1;
      updateBucketCount(bucket.decision_reason_codes, trace.decisionReasonCode);
      updateBucketCount(bucket.fallback_reason_codes, trace.fallbackReasonCode);
      updateBucketCount(bucket.legacy_match_levels, trace.matchLevel);
      if (trace.matchedExactBool) bucket.matched_exact_true_count += 1;
      if (trace.anomalyFlags?.anomaly_any === true) bucket.anomaly_flag_count += 1;
    }
  });

  for (const level of TYPED_FALLBACK_LEVELS) {
    const bucket = levels[level.id];
    bucket.rate = percentRate(bucket.row_count, totalRows);
    bucket.pct = percentPct(bucket.row_count, totalRows);
  }

  return {
    analysis_name: "A4_runtime_fallback_semantics",
    generated_at_utc: new Date().toISOString(),
    cp_profile: "CP-0",
    source_context: {
      snapshot_path: persistenceArtifact?.snapshot_artifact_path ?? null,
      policy_artifact_path: persistenceArtifact?.policy_artifact_path ?? policyRuntime.source_path,
      persisted_provenance_run_id: persistenceArtifact?.run_id ?? null,
      decision_provenance_min_bars: minBars,
      anomaly_fallback_enabled: anomalyFallbackEnabled,
      note:
        "This reflects the decision-provenance write path semantics. Serving freshness/stale conditions remain orthogonal and are not collapsed into ladder levels.",
    },
    classification_integrity: {
      total_rows: totalRows,
      classified_rows: classifiedRows,
      unclassified_rows: Math.max(0, totalRows - classifiedRows),
      every_row_maps_to_exactly_one_level: totalRows === classifiedRows,
    },
    level_breakdown: levels,
    orthogonal_flags: {
      registry: TYPED_FALLBACK_ORTHOGONAL_FLAGS,
      matched_exact_true_rate: percentRate(
        Object.values(levels).reduce((sum, bucket) => sum + bucket.matched_exact_true_count, 0),
        totalRows,
      ),
      anomaly_flag_rate: percentRate(
        Object.values(levels).reduce((sum, bucket) => sum + bucket.anomaly_flag_count, 0),
        totalRows,
      ),
    },
  };
}

function tracePseudoRowFromRowTrace(row, minBars) {
  return {
    ticker: String(row.symbol ?? "").trim().toUpperCase(),
    regime: String(row.regime ?? "UNKNOWN"),
    S_UF: toFinite(row.S_UF) ?? 0,
    R_UF: toFinite(row.R_UF) ?? 0,
    D_k: toFinite(row.D),
    M_k: toFinite(row.M),
    R_rev_k: toFinite(row.R_rev),
    U_star_k: toFinite(row.U_star),
    C_k: toFinite(row.C_k ?? row.C),
    P_k: toFinite(row.P),
    B_k: toFinite(row.B),
    bar_count: minBars,
    stability_score: 0,
  };
}

function emptyHorizonArrays() {
  const out = {};
  for (const horizon of HORIZONS) {
    out[String(horizon)] = {
      action_returns: [],
      benchmark_returns: [],
      excess_returns: [],
      evaluated_rows: 0,
      outcome_wins: 0,
    };
  }
  return out;
}

function buildAdminQualityBreakdown(snapshotRows, winnerPolicyRuntime, winnerMinBars, qualitySummary, rowTraceRows, spyPayload) {
  const levels = qualityLevelTemplate();
  let totalSnapshotRows = 0;
  let classifiedSnapshotRows = 0;

  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", "1", () => {
    for (const row of snapshotRows) {
      const trace = computeDecisionTrace(row, winnerPolicyRuntime, winnerMinBars);
      totalSnapshotRows += 1;
      const bucket = levels[trace.fallbackLadderLevel];
      if (!bucket) continue;
      classifiedSnapshotRows += 1;
      bucket.snapshot_row_count += 1;
    }
  });

  for (const level of TYPED_FALLBACK_LEVELS) {
    const bucket = levels[level.id];
    bucket.snapshot_rate = percentRate(bucket.snapshot_row_count, totalSnapshotRows);
    bucket.snapshot_pct = percentPct(bucket.snapshot_row_count, totalSnapshotRows);
  }

  const spyTs = Array.isArray(spyPayload?.spy?.ts_ms) ? spyPayload.spy.ts_ms.map((value) => Number(value)) : [];
  const spyClose = Array.isArray(spyPayload?.spy?.close) ? spyPayload.spy.close.map((value) => Number(value)) : [];
  const rowTraceScores = {};
  for (const level of TYPED_FALLBACK_LEVELS) {
    rowTraceScores[level.id] = emptyHorizonArrays();
  }

  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", "0", () => {
    for (const row of rowTraceRows) {
      const horizon = Math.trunc(Number(row.horizon));
      if (!HORIZONS.includes(horizon)) continue;

      const tsMs = parseIsoMs(row.decision_timestamp);
      const forwardReturn = toFinite(row.forward_return);
      if (!Number.isFinite(tsMs) || forwardReturn === null) continue;

      const benchRet = spyForwardReturn(spyTs, spyClose, tsMs, horizon);
      if (benchRet === null) continue;

      const trace = computeDecisionTrace(tracePseudoRowFromRowTrace(row, winnerMinBars), winnerPolicyRuntime, winnerMinBars);
      const levelBucket = levels[trace.fallbackLadderLevel];
      if (!levelBucket) continue;

      if (trace.decisionReasonCode !== "PSCF_POLICY_DECISION") {
        levelBucket.excluded_row_count += 1;
        continue;
      }

      const scoreBucket = rowTraceScores[trace.fallbackLadderLevel][String(horizon)];
      const actionRet = decisionReturn(trace.decision, forwardReturn);
      scoreBucket.action_returns.push(actionRet);
      scoreBucket.benchmark_returns.push(benchRet);
      scoreBucket.excess_returns.push(actionRet - benchRet);
      scoreBucket.evaluated_rows += 1;
      scoreBucket.outcome_wins += Number(actionRet > benchRet);
      levelBucket.assessed_row_count += 1;
    }
  });

  for (const level of TYPED_FALLBACK_LEVELS) {
    const bucket = levels[level.id];
    const horizonOutcomeValues = [];
    const horizonMeanExcessValues = [];

    for (const horizon of HORIZONS) {
      const scoreBucket = rowTraceScores[level.id][String(horizon)];
      if (scoreBucket.evaluated_rows > 0) {
        const outcomePct = Number(((100 * scoreBucket.outcome_wins) / scoreBucket.evaluated_rows).toFixed(6));
        const meanExcess = average(scoreBucket.excess_returns);
        bucket.horizon_outcome_over_index_pct[String(horizon)] = outcomePct;
        bucket.horizon_mean_excess_vs_spy[String(horizon)] = meanExcess;
        horizonOutcomeValues.push(outcomePct);
        if (meanExcess !== null) {
          horizonMeanExcessValues.push(meanExcess);
        }
      }
    }

    bucket.avg_outcome_over_index_pct = average(horizonOutcomeValues);
    bucket.avg_mean_excess_vs_spy = average(horizonMeanExcessValues);

    if (!bucket.scored_under_current_contract) {
      bucket.notes.push("Not scored under the current assessed-only quality contract.");
    } else if (bucket.assessed_row_count === 0) {
      bucket.notes.push("No assessed rows mapped into this level under the current winner context.");
    }
  }

  const exactStructural = levels.L0_EXACT_STRUCTURAL_MATCH.snapshot_rate;
  const relaxedStructural = levels.L1_RELAXED_STRUCTURAL_MATCH.snapshot_rate;
  const safeFallback = levels.L2_SAFE_POLICY_FALLBACK.snapshot_rate;
  const degradedUnmapped = levels.L3_DEGRADED_UNMAPPED.snapshot_rate;
  const unavailableBlocked = levels.L4_UNAVAILABLE_OR_BLOCKED.snapshot_rate;

  const winner = qualitySummary?.winner ?? {};
  const coverageRate = Number(winner.coverage_rate ?? 0);
  const fallbackRate = Number(winner.fallback_rate ?? 0);
  const structuralCoverageRate = Number((exactStructural + relaxedStructural).toFixed(6));
  const nonStructuralRate = Number((safeFallback + degradedUnmapped + unavailableBlocked).toFixed(6));
  const compatibilityChecks = {
    all_snapshot_rows_classified_exactly_once: totalSnapshotRows === classifiedSnapshotRows,
    structural_coverage_matches_quality_winner: Math.abs(structuralCoverageRate - coverageRate) < 0.000001,
    non_structural_share_matches_quality_winner: Math.abs(nonStructuralRate - fallbackRate) < 0.000001,
  };

  return {
    analysis_name: "A4_admin_quality_fallback_breakdown",
    generated_at_utc: new Date().toISOString(),
    cp_profile: "CP-0",
    quality_winner_context: {
      summary_path: path.join(resolveWorkspaceRoot(), "web", "data", "recommendation-quality-latest.json"),
      winner_variant_name: String(winner.variant_name ?? ""),
      winner_policy_path: String(winner.policy_path ?? winnerPolicyRuntime.source_path ?? ""),
      winner_min_bars: winnerMinBars,
      anomaly_fallback_enabled: true,
      quality_contract: OUTCOME_SCORING_CONTRACT,
    },
    compatibility_checks: compatibilityChecks,
    phase_3a_admin_internal_ready:
      compatibilityChecks.all_snapshot_rows_classified_exactly_once &&
      compatibilityChecks.structural_coverage_matches_quality_winner &&
      compatibilityChecks.non_structural_share_matches_quality_winner,
    phase_3a_admin_internal_recommendation:
      compatibilityChecks.all_snapshot_rows_classified_exactly_once &&
      compatibilityChecks.structural_coverage_matches_quality_winner &&
      compatibilityChecks.non_structural_share_matches_quality_winner
        ? "Ready for admin/internal-only exposure. Keep reader strict mode false and keep public recommendation ranking unchanged."
        : "Not ready. Verify ladder mapping against winner quality context before exposing admin/internal views.",
    coverage_summary: {
      total_snapshot_rows: totalSnapshotRows,
      exact_structural_coverage_rate: exactStructural,
      exact_structural_coverage_pct: percentPct(levels.L0_EXACT_STRUCTURAL_MATCH.snapshot_row_count, totalSnapshotRows),
      relaxed_structural_coverage_rate: relaxedStructural,
      relaxed_structural_coverage_pct: percentPct(levels.L1_RELAXED_STRUCTURAL_MATCH.snapshot_row_count, totalSnapshotRows),
      safe_policy_fallback_rate: safeFallback,
      safe_policy_fallback_pct: percentPct(levels.L2_SAFE_POLICY_FALLBACK.snapshot_row_count, totalSnapshotRows),
      degraded_unmapped_rate: degradedUnmapped,
      degraded_unmapped_pct: percentPct(levels.L3_DEGRADED_UNMAPPED.snapshot_row_count, totalSnapshotRows),
      unavailable_or_blocked_rate: unavailableBlocked,
      unavailable_or_blocked_pct: percentPct(levels.L4_UNAVAILABLE_OR_BLOCKED.snapshot_row_count, totalSnapshotRows),
      structural_coverage_rate: structuralCoverageRate,
      structural_coverage_pct: Number((structuralCoverageRate * 100).toFixed(6)),
      non_structural_rate: nonStructuralRate,
      non_structural_pct: Number((nonStructuralRate * 100).toFixed(6)),
      quality_winner_coverage_rate: coverageRate,
      quality_winner_fallback_rate: fallbackRate,
    },
    level_breakdown: levels,
  };
}

function buildSchemaArtifact() {
  const levels = TYPED_FALLBACK_LEVELS.map((level) => ({
    id: level.id,
    order: level.order,
    structural_coverage: level.structural_coverage,
    exact_structural: level.exact_structural,
    quality_assessed_under_current_contract: level.quality_assessed_under_current_contract,
    description: level.description,
  }));

  return {
    generated_at_utc: new Date().toISOString(),
    cp_profile: "CP-0",
    schema_name: "typed_fallback_ladder_v1",
    levels,
    orthogonal_flags: TYPED_FALLBACK_ORTHOGONAL_FLAGS,
    deterministic_mapping_rules: [
      {
        when: "decision_reason_code == PSCF_POLICY_DECISION and matched_candidate_index == 0",
        level: "L0_EXACT_STRUCTURAL_MATCH",
      },
      {
        when: "decision_reason_code == PSCF_POLICY_DECISION and matched_candidate_index > 0",
        level: "L1_RELAXED_STRUCTURAL_MATCH",
      },
      {
        when: "decision_reason_code == PSCF_FALLBACK_ANOMALOUS",
        level: "L2_SAFE_POLICY_FALLBACK",
      },
      {
        when:
          "decision_reason_code in {PSCF_FALLBACK_POLICY_MISSING, PSCF_FALLBACK_CELL_KEY_UNAVAILABLE, PSCF_FALLBACK_CELL_UNMAPPED}",
        level: "L3_DEGRADED_UNMAPPED",
      },
      {
        when:
          "decision_reason_code in {PSCF_FALLBACK_INSUFFICIENT_BARS, PSCF_FALLBACK_STRUCTURAL_INCOMPLETE}",
        level: "L4_UNAVAILABLE_OR_BLOCKED",
      },
    ],
    preserved_legacy_fields: [
      "match_level",
      "matched_exact_bool",
      "fallback_used",
      "fallback_reason_code",
      "decision_reason_code",
      "coverage_class",
    ],
    serving_layer_boundary: {
      freshness_or_stale_flag_remains_orthogonal: true,
      serving_unavailable_or_blocked_only_enters_ladder_when_reported_by_serving_layer: true,
    },
  };
}

function renderSchemaMarkdown(schemaArtifact) {
  const levelLines = schemaArtifact.levels
    .map(
      (level) =>
        `- \`${level.id}\`: ${level.description} structural_coverage=${level.structural_coverage} exact_structural=${level.exact_structural} assessed=${level.quality_assessed_under_current_contract}`,
    )
    .join("\n");

  const ruleLines = schemaArtifact.deterministic_mapping_rules
    .map((rule) => `- \`${rule.level}\` when ${rule.when}`)
    .join("\n");

  const flagLines = schemaArtifact.orthogonal_flags.map((flag) => `- \`${flag}\``).join("\n");
  const legacyLines = schemaArtifact.preserved_legacy_fields.map((field) => `- \`${field}\``).join("\n");

  return [
    "# Typed Fallback Ladder Schema (Latest)",
    "",
    `Generated (UTC): ${schemaArtifact.generated_at_utc}`,
    "",
    "## Levels",
    "",
    levelLines,
    "",
    "## Deterministic Mapping Rules",
    "",
    ruleLines,
    "",
    "## Orthogonal Flags",
    "",
    flagLines,
    "",
    "## Preserved Legacy Fields",
    "",
    legacyLines,
    "",
    "## Serving Layer Boundary",
    "",
    "- Freshness/stale remains orthogonal and is not collapsed into decision provenance ladder levels.",
    "- Serving-layer unavailable/blocked states enter the ladder only when the serving layer is explicitly reporting them.",
    "",
  ].join("\n");
}

function renderPromotionGateMarkdown(adminBreakdown) {
  const coverage = adminBreakdown.coverage_summary;
  return [
    "# Promotion Gate Fallback Integration (Latest)",
    "",
    `Generated (UTC): ${adminBreakdown.generated_at_utc}`,
    "",
    "## Purpose",
    "",
    "- Add typed fallback semantics to promotion governance without enforcing them yet.",
    "- Keep CP-0 ranking and allocator behavior unchanged until admin/internal verification is complete.",
    "",
    "## Current Observed Baseline",
    "",
    `- Exact structural coverage: ${coverage.exact_structural_coverage_pct.toFixed(3)}%`,
    `- Relaxed structural coverage: ${coverage.relaxed_structural_coverage_pct.toFixed(3)}%`,
    `- Safe policy fallback: ${coverage.safe_policy_fallback_pct.toFixed(3)}%`,
    `- Degraded/unmapped: ${coverage.degraded_unmapped_pct.toFixed(3)}%`,
    `- Unavailable/blocked: ${coverage.unavailable_or_blocked_pct.toFixed(3)}%`,
    "",
    "## Proposed Gate Metrics",
    "",
    "- Exact-match coverage floor: track `L0_EXACT_STRUCTURAL_MATCH` separately and require non-regression before promotion.",
    "- Relaxed-match signal: track `L1_RELAXED_STRUCTURAL_MATCH` separately; do not let higher relaxed share mask lower exact share.",
    "- Safe-fallback ceiling: cap `L2_SAFE_POLICY_FALLBACK` and treat increases as a negative unless exact-match quality improves independently.",
    "- Degraded/unmapped ceiling: cap `L3_DEGRADED_UNMAPPED` and block promotion if it rises materially.",
    "- Exact-match quality gate: require non-regression on L0 assessed outcome-over-index and mean_excess_vs_spy.",
    "- Fallback-adjusted quality gate: evaluate assessed quality together with the combined non-structural share `(L2+L3+L4)`.",
    "- No-improvement-via-more-fallback rule: reject any candidate whose headline quality improves only because exact coverage shrank while non-structural share grew.",
    "",
    "## Recommended Observation-Only Rollout",
    "",
    "- Phase 1: admin/internal dashboard only, with typed fallback rows and level-specific assessed metrics.",
    "- Phase 2: collect at least one verified admin review cycle against the existing winner summary.",
    "- Phase 3: only then convert the metrics above into enforced promotion thresholds.",
    "",
    "## Enforcement Status",
    "",
    "- Not enforced yet.",
    "- Recommended option: verify the admin/internal fallback breakdown first, then implement A6 using these metrics as explicit promotion gates.",
    "",
  ].join("\n");
}

function main() {
  const root = resolveWorkspaceRoot();
  const snapshotPath = path.join(root, "uf_snapshot.json");
  const rowTracePath = path.join(root, "real_world_cleaned_universe_l5_row_trace_full.csv");
  const qualityPath = path.join(root, "web", "data", "recommendation-quality-latest.json");
  const spyPath = path.join(root, "backups", "strict-ab-frozen-dataset-20260218T133559Z.json");
  const persistencePath = path.join(root, "current_l5_provenance_persistence_latest.json");

  const schemaJsonPath = path.join(root, "typed_fallback_ladder_schema_latest.json");
  const schemaMdPath = path.join(root, "typed_fallback_ladder_schema_latest.md");
  const runtimeSemanticsPath = path.join(root, "runtime_fallback_semantics_latest.json");
  const adminBreakdownPath = path.join(root, "admin_quality_fallback_breakdown_latest.json");
  const promotionGateMdPath = path.join(root, "promotion_gate_fallback_integration_latest.md");

  const snapshotRows = parseSnapshotRows(snapshotPath);
  const runtimePolicy = loadPolicyRuntimeArtifact(root);
  const qualitySummary = readJson(qualityPath);
  const winnerPolicyPathRaw = String(qualitySummary?.winner?.policy_path ?? runtimePolicy.source_path ?? "").trim();
  const winnerPolicyPath = winnerPolicyPathRaw ? path.resolve(winnerPolicyPathRaw) : path.resolve(root, "pscf_policy_runtime.json");
  const winnerPolicyRuntime = loadPolicyRuntimeFromPath(winnerPolicyPath);
  const winnerMinBars = Math.trunc(Number(qualitySummary?.winner?.min_bars ?? 0)) || 252;
  const rowTraceRows = parseCsvRows(rowTracePath);
  const spyPayload = readJson(spyPath);
  const persistenceArtifact = existsSync(persistencePath) ? readJson(persistencePath) : null;

  const schemaArtifact = buildSchemaArtifact();
  const runtimeSemantics = buildRuntimeSemantics(
    snapshotRows,
    runtimePolicy,
    minBarsForAccumulate(),
    false,
    persistenceArtifact,
  );
  const adminBreakdown = buildAdminQualityBreakdown(
    snapshotRows,
    winnerPolicyRuntime,
    winnerMinBars,
    qualitySummary,
    rowTraceRows,
    spyPayload,
  );

  writeJson(schemaJsonPath, schemaArtifact);
  writeFileSync(schemaMdPath, `${renderSchemaMarkdown(schemaArtifact)}\n`, "utf-8");
  writeJson(runtimeSemanticsPath, runtimeSemantics);
  writeJson(adminBreakdownPath, adminBreakdown);
  writeFileSync(promotionGateMdPath, `${renderPromotionGateMarkdown(adminBreakdown)}\n`, "utf-8");

  process.stdout.write(
    `${JSON.stringify({
      status: "ok",
      schema_json: schemaJsonPath,
      schema_md: schemaMdPath,
      runtime_semantics_json: runtimeSemanticsPath,
      admin_quality_breakdown_json: adminBreakdownPath,
      promotion_gate_md: promotionGateMdPath,
      admin_phase_3a_ready: adminBreakdown.phase_3a_admin_internal_ready,
    })}\n`,
  );
}

main();
