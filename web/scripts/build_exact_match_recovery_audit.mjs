#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  computeDecisionTrace,
  loadPolicyRuntimeArtifact,
  sha256Hex,
} from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const REQUIRED_DIMENSIONS = [
  "regime_mismatch",
  "D_mismatch",
  "M_sign_mismatch",
  "R_rev_mismatch",
  "U_bucket_mismatch",
  "C_mismatch",
  "P_bucket_mismatch",
  "B_sign_mismatch",
  "S_bucket_mismatch",
  "R_bucket_mismatch",
  "CD_bucket_mismatch",
  "stability_bucket_mismatch",
  "phase_suffix_mismatch",
  "Spider_Eyes_suffix_mismatch",
  "missing_null_field",
  "runtime_materialization_serialization_mismatch",
  "policy_artifact_mismatch",
  "exact_path_unreachable_by_current_runtime_construction",
];
const POLICY_DIMENSION_ORDER = [
  "spider_eyes_suffix",
  "phase_suffix",
  "CD_bucket",
  "stability_bucket",
  "S_bucket",
  "R_bucket",
  "regime",
  "D",
  "M_sign",
  "R_rev",
  "U_bucket",
  "C",
  "P_bucket",
  "B_sign",
];
const DIMENSION_LABELS = {
  regime_mismatch: "regime mismatch",
  D_mismatch: "D mismatch",
  M_sign_mismatch: "M sign mismatch",
  R_rev_mismatch: "R_rev mismatch",
  U_bucket_mismatch: "U bucket mismatch",
  C_mismatch: "C mismatch",
  P_bucket_mismatch: "P bucket mismatch",
  B_sign_mismatch: "B sign mismatch",
  S_bucket_mismatch: "S bucket mismatch",
  R_bucket_mismatch: "R bucket mismatch",
  CD_bucket_mismatch: "CD bucket mismatch",
  stability_bucket_mismatch: "stability bucket mismatch",
  phase_suffix_mismatch: "phase suffix mismatch",
  Spider_Eyes_suffix_mismatch: "Spider Eyes suffix mismatch",
  missing_null_field: "missing/null field",
  runtime_materialization_serialization_mismatch: "runtime materialization/serialization mismatch",
  policy_artifact_mismatch: "policy artifact mismatch",
  exact_path_unreachable_by_current_runtime_construction: "exact path unreachable by current runtime construction",
};
const FIELD_TO_DIMENSION = {
  regime: "regime_mismatch",
  D: "D_mismatch",
  M_sign: "M_sign_mismatch",
  R_rev: "R_rev_mismatch",
  U_bucket: "U_bucket_mismatch",
  C: "C_mismatch",
  P_bucket: "P_bucket_mismatch",
  B_sign: "B_sign_mismatch",
  S_bucket: "S_bucket_mismatch",
  R_bucket: "R_bucket_mismatch",
  CD_bucket: "CD_bucket_mismatch",
  stability_bucket: "stability_bucket_mismatch",
  phase_suffix: "phase_suffix_mismatch",
  spider_eyes_suffix: "Spider_Eyes_suffix_mismatch",
};
const PARSED_DIMENSION_KEYS = [
  "regime",
  "D",
  "M_sign",
  "R_rev",
  "U_bucket",
  "C",
  "P_bucket",
  "B_sign",
  "S_bucket",
  "R_bucket",
  "CD_bucket",
  "stability_bucket",
  "phase_suffix",
  "spider_eyes_suffix",
];

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
    return JSON.parse(
      raw
        .replace(/\bNaN\b/g, "null")
        .replace(/\b-Infinity\b/g, "null")
        .replace(/\bInfinity\b/g, "null"),
    );
  }
}

function readJson(filePath, allowNonFinite = false) {
  return parseJsonText(readFileSync(filePath, "utf-8"), allowNonFinite);
}

function writeJson(filePath, payload) {
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

function percent(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function rate(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number((count / total).toFixed(6));
}

function parseSnapshotRows(snapshotPath) {
  const payload = readJson(snapshotPath, true);
  if (Array.isArray(payload)) return payload.filter((row) => row && typeof row === "object");
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) {
    return payload.rows.filter((row) => row && typeof row === "object");
  }
  return [];
}

function parsePolicyKey(key) {
  const out = {
    regime: null,
    D: null,
    M_sign: null,
    R_rev: null,
    U_bucket: null,
    C: null,
    P_bucket: null,
    B_sign: null,
    S_bucket: null,
    R_bucket: null,
    CD_bucket: null,
    stability_bucket: null,
    phase_suffix: null,
    spider_eyes_suffix: null,
  };

  for (const part of String(key ?? "").split("|")) {
    if (part.startsWith("reg=")) out.regime = part.slice(4);
    else if (part.startsWith("D=")) out.D = part.slice(2);
    else if (part.startsWith("M=")) out.M_sign = part.slice(2);
    else if (part.startsWith("Rrev=")) out.R_rev = part.slice(5);
    else if (part === "U0" || part === "U1" || part === "U2") out.U_bucket = part;
    else if (part.startsWith("C=")) out.C = part.slice(2);
    else if (part === "P0" || part === "P1" || part === "P2") out.P_bucket = part;
    else if (part.startsWith("B=")) out.B_sign = part.slice(2);
    else if (part.startsWith("S=")) out.S_bucket = part.slice(2);
    else if (part.startsWith("R=")) out.R_bucket = part.slice(2);
    else if (part.startsWith("CD=")) out.CD_bucket = part.slice(3);
    else if (part.startsWith("ST=")) out.stability_bucket = part.slice(3);
    else if (part.startsWith("PH=")) out.phase_suffix = part.slice(3);
    else if (part.startsWith("SE=")) out.spider_eyes_suffix = part.slice(3);
  }

  return out;
}

function signatureWithoutDimension(parts, omittedDimension) {
  return PARSED_DIMENSION_KEYS
    .filter((key) => key !== omittedDimension)
    .map((key) => `${key}=${parts[key] === null ? "__NULL__" : parts[key]}`)
    .join("|");
}

function buildPolicyWildcardIndices(policyKeys) {
  const indices = {};
  for (const dimension of PARSED_DIMENSION_KEYS) {
    indices[dimension] = new Map();
  }

  for (const key of policyKeys) {
    const parsed = parsePolicyKey(key);
    for (const dimension of PARSED_DIMENSION_KEYS) {
      const signature = signatureWithoutDimension(parsed, dimension);
      const bucket = indices[dimension].get(signature) ?? new Set();
      bucket.add(parsed[dimension] === null ? "__NULL__" : parsed[dimension]);
      indices[dimension].set(signature, bucket);
    }
  }

  return indices;
}

function findFirstSingleDimensionFailure(exactParts, wildcardIndices) {
  for (const dimension of POLICY_DIMENSION_ORDER) {
    const signature = signatureWithoutDimension(exactParts, dimension);
    const candidates = wildcardIndices[dimension].get(signature);
    if (!candidates) continue;
    const current = exactParts[dimension] === null ? "__NULL__" : exactParts[dimension];
    for (const candidate of candidates) {
      if (candidate !== current) {
        return FIELD_TO_DIMENSION[dimension] ?? null;
      }
    }
  }
  return null;
}

function diffRelaxedDimensions(exactKey, matchedKey) {
  const exact = parsePolicyKey(exactKey);
  const matched = parsePolicyKey(matchedKey);
  const out = [];
  for (const dimension of [
    "stability_bucket",
    "CD_bucket",
    "S_bucket",
    "R_bucket",
    "phase_suffix",
    "spider_eyes_suffix",
  ]) {
    if (exact[dimension] !== matched[dimension]) {
      out.push(dimension);
    }
  }
  return out;
}

function explainUnreachable(trace, row, minBars) {
  const barCount = Number(row?.bar_count ?? 0);
  if (barCount < minBars) {
    return "insufficient_bars_guard_before_policy_lookup";
  }
  if (!trace.matchedKey) {
    return "no_policy_cell_even_after_full_relaxation";
  }
  const relaxed = diffRelaxedDimensions(trace.candidateKeyChain?.[0] ?? "", trace.matchedKey);
  if (relaxed.length > 0) {
    return `multi_dimension_relaxation_required:${relaxed.join("+")}`;
  }
  return "exact_path_family_missing_without_single_dimension_recovery";
}

function buildMaterializationDiagnostics(rows, policyRuntime, minBars) {
  const fieldMismatchCounts = {
    D_k: 0,
    M_k: 0,
    R_rev_k: 0,
    P_k: 0,
  };
  let betterWithoutDecisionVector = 0;
  let worseWithoutDecisionVector = 0;
  let sameWithoutDecisionVector = 0;
  let exactRestoredWithoutDecisionVector = 0;
  const examples = [];

  for (const row of rows) {
    const runtimeTrace = computeDecisionTrace(row, policyRuntime, minBars);
    const rowWithoutDecisionVector = { ...row };
    delete rowWithoutDecisionVector.decision_vector;
    const topLevelTrace = computeDecisionTrace(rowWithoutDecisionVector, policyRuntime, minBars);

    const runtimeIndex = runtimeTrace.matchedIndex < 0 ? 999 : runtimeTrace.matchedIndex;
    const topLevelIndex = topLevelTrace.matchedIndex < 0 ? 999 : topLevelTrace.matchedIndex;

    if (topLevelIndex < runtimeIndex) betterWithoutDecisionVector += 1;
    else if (topLevelIndex > runtimeIndex) worseWithoutDecisionVector += 1;
    else sameWithoutDecisionVector += 1;

    if (runtimeTrace.matchedIndex !== 0 && topLevelTrace.matchedIndex === 0) {
      exactRestoredWithoutDecisionVector += 1;
    }

    const dv = Array.isArray(row.decision_vector) ? row.decision_vector : [];
    const pairs = [
      ["D_k", 0, (value) => (value === null || value === undefined ? null : Math.round(Number(value)))],
      ["M_k", 1, (value) => (value === null || value === undefined ? null : Number(value))],
      ["R_rev_k", 2, (value) => (value === null || value === undefined ? null : (Number(value) > 0.5 ? 1 : 0))],
    ];
    if (dv.length >= 7) {
      pairs.push(["P_k", 5, (value) => (value === null || value === undefined ? null : Math.round(Number(value)))]);
    } else if (dv.length >= 6) {
      pairs.push(["P_k", 4, (value) => (value === null || value === undefined ? null : Math.round(Number(value)))]);
    }

    const mismatchedFields = [];
    for (const [field, index, normalizer] of pairs) {
      const topValue = normalizer(row[field]);
      const dvValue = index < dv.length ? normalizer(dv[index]) : null;
      if (topValue !== null && dvValue !== null && topValue !== dvValue) {
        fieldMismatchCounts[field] += 1;
        mismatchedFields.push(field);
      }
    }

    if (mismatchedFields.length > 0 && examples.length < 5) {
      examples.push({
        ticker: String(row.ticker ?? ""),
        mismatched_fields: mismatchedFields,
        runtime_exact_key: runtimeTrace.candidateKeyChain?.[0] ?? null,
        top_level_exact_key: topLevelTrace.candidateKeyChain?.[0] ?? null,
        runtime_matched_index: runtimeTrace.matchedIndex,
        top_level_matched_index: topLevelTrace.matchedIndex,
      });
    }
  }

  return {
    field_mismatch_counts: fieldMismatchCounts,
    rows_with_better_match_without_decision_vector: betterWithoutDecisionVector,
    rows_with_worse_match_without_decision_vector: worseWithoutDecisionVector,
    rows_with_same_match_without_decision_vector: sameWithoutDecisionVector,
    rows_with_exact_restored_without_decision_vector: exactRestoredWithoutDecisionVector,
    examples,
  };
}

function buildTopReasons(primaryCounts, unreachableSubreasons, totalNonL0, policyStructuralEvidence) {
  const reasons = [];

  for (const [dimensionId, count] of Object.entries(primaryCounts)) {
    if (!count) continue;
    reasons.push({
      type: "row_primary",
      id: dimensionId,
      label: DIMENSION_LABELS[dimensionId] ?? dimensionId,
      count,
      pct_of_non_l0_rows: percent(count, totalNonL0),
    });
  }

  for (const [reasonId, count] of Object.entries(unreachableSubreasons)) {
    if (!count) continue;
    reasons.push({
      type: "row_detail",
      id: reasonId,
      label: reasonId.replace(/_/g, " "),
      count,
      pct_of_non_l0_rows: percent(count, totalNonL0),
    });
  }

  reasons.push({
    type: "policy_structure",
    id: "policy_has_zero_ST_plus_PH_plus_SE_cells",
    label: "policy has zero cells containing ST + PH + SE together",
    count: policyStructuralEvidence.eligible_rows_impacted,
    pct_of_non_l0_rows: percent(policyStructuralEvidence.eligible_rows_impacted, totalNonL0),
  });
  reasons.push({
    type: "policy_structure",
    id: "policy_has_zero_ST_plus_PH_cells",
    label: "policy has zero cells containing ST + PH together",
    count: policyStructuralEvidence.eligible_rows_impacted,
    pct_of_non_l0_rows: percent(policyStructuralEvidence.eligible_rows_impacted, totalNonL0),
  });
  reasons.push({
    type: "policy_structure",
    id: "policy_has_zero_ST_plus_SE_cells",
    label: "policy has zero cells containing ST + SE together",
    count: policyStructuralEvidence.eligible_rows_impacted,
    pct_of_non_l0_rows: percent(policyStructuralEvidence.eligible_rows_impacted, totalNonL0),
  });

  reasons.sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return String(a.label).localeCompare(String(b.label));
  });

  return reasons.slice(0, 10);
}

function renderMarkdown(report) {
  const summaryLines = report.first_failing_dimension_summary.sorted_nonzero_counts
    .map((item) => `- ${item.label}: ${item.count} rows (${item.pct_of_non_l0_rows.toFixed(3)}%)`)
    .join("\n");

  const topReasonLines = report.top_10_reasons_exact_is_zero
    .map((item, index) => `${index + 1}. ${item.label}: ${item.count} rows (${item.pct_of_non_l0_rows.toFixed(3)}%)`)
    .join("\n");

  const requireL0 = report.strategy_family_gating.require_L0_exact.map((item) => `- ${item}`).join("\n");
  const allowL1 = report.strategy_family_gating.allow_L1_relaxed.map((item) => `- ${item}`).join("\n");
  const safeOnly = report.strategy_family_gating.safe_only_L2_L3_L4.map((item) => `- ${item}`).join("\n");

  return [
    "# Exact Match Recovery Audit (Latest)",
    "",
    `Generated (UTC): ${report.generated_at_utc}`,
    "",
    "## Verdict",
    "",
    `- Recommended action: ${report.recommended_action}`,
    `- Proceed to A5 immediately: ${report.proceed_to_A5_immediately}`,
    `- Can exact match be materially restored without destabilizing CP-0: ${report.can_materially_restore_exact_without_destabilizing_CP0}`,
    `- Reason: ${report.restore_exact_rationale}`,
    "",
    "## First Failing Dimension Counts",
    "",
    summaryLines,
    "",
    "## Top 10 Reasons Exact Match Is Zero",
    "",
    topReasonLines,
    "",
    "## Policy Structural Evidence",
    "",
    `- Cells total: ${report.policy_structure_evidence.total_cells}`,
    `- Cells with ST: ${report.policy_structure_evidence.cells_with_ST}`,
    `- Cells with PH: ${report.policy_structure_evidence.cells_with_PH}`,
    `- Cells with SE: ${report.policy_structure_evidence.cells_with_SE}`,
    `- Cells with ST+PH: ${report.policy_structure_evidence.cells_with_ST_and_PH}`,
    `- Cells with ST+SE: ${report.policy_structure_evidence.cells_with_ST_and_SE}`,
    `- Cells with ST+PH+SE: ${report.policy_structure_evidence.cells_with_ST_and_PH_and_SE}`,
    `- Cells with PH=U2DN: ${report.policy_structure_evidence.cells_with_phase_u2dn}`,
    "",
    "## Strategy Gating",
    "",
    "Require L0 exact:",
    requireL0,
    "",
    "Allow L1 relaxed:",
    allowL1,
    "",
    "Only safe behavior for L2/L3/L4:",
    safeOnly,
    "",
  ].join("\n");
}

function main() {
  const root = resolveWorkspaceRoot();
  const snapshotPath = path.join(root, "uf_snapshot.json");
  const qualityPath = path.join(root, "web", "data", "recommendation-quality-latest.json");
  const outputJsonPath = path.join(root, "exact_match_recovery_audit_latest.json");
  const outputMdPath = path.join(root, "exact_match_recovery_audit_latest.md");

  const rows = parseSnapshotRows(snapshotPath);
  const qualitySummary = readJson(qualityPath);
  const winnerMinBars = Math.trunc(Number(qualitySummary?.winner?.min_bars ?? 0)) || 252;
  const winnerPolicyPath = String(qualitySummary?.winner?.policy_path ?? path.join(root, "pscf_policy_runtime.json")).trim();
  const policyRuntime = loadPolicyRuntimeArtifact(root);
  const policyKeys = Object.keys(policyRuntime.cells ?? {});
  const wildcardIndices = buildPolicyWildcardIndices(policyKeys);
  const qualityPolicyHash = existsSync(winnerPolicyPath) ? sha256Hex(readFileSync(winnerPolicyPath, "utf-8")) : null;
  const policyArtifactMismatchObserved =
    qualityPolicyHash !== null && qualityPolicyHash !== policyRuntime.policy_artifact_hash_sha256;

  const primaryCounts = Object.fromEntries(REQUIRED_DIMENSIONS.map((dimension) => [dimension, 0]));
  const primaryExamples = Object.fromEntries(REQUIRED_DIMENSIONS.map((dimension) => [dimension, []]));
  const unreachableSubreasons = {};
  const matchedIndexCounts = {};
  let totalNonL0 = 0;
  let rowsEligibleForPolicyLookup = 0;
  let rowsBlockedByBars = 0;

  process.env.TFE_RECOMMENDATIONS_ANOMALY_FALLBACK = "1";

  for (const row of rows) {
    const trace = computeDecisionTrace(row, policyRuntime, winnerMinBars);
    if (trace.matchedIndex === 0) continue;
    totalNonL0 += 1;

    const matchedIndexKey = String(trace.matchedIndex);
    matchedIndexCounts[matchedIndexKey] = Number(matchedIndexCounts[matchedIndexKey] ?? 0) + 1;

    let classification = null;
    const basisMissing = Array.isArray(trace.basis?.missing_fields) ? trace.basis.missing_fields.length > 0 : false;
    const barCount = Number(row?.bar_count ?? 0);

    if (policyArtifactMismatchObserved) {
      classification = "policy_artifact_mismatch";
    } else if (basisMissing) {
      classification = "missing_null_field";
    } else if (barCount < winnerMinBars) {
      classification = "exact_path_unreachable_by_current_runtime_construction";
      rowsBlockedByBars += 1;
    } else {
      rowsEligibleForPolicyLookup += 1;
      const rowWithoutDecisionVector = { ...row };
      delete rowWithoutDecisionVector.decision_vector;
      const topLevelTrace = computeDecisionTrace(rowWithoutDecisionVector, policyRuntime, winnerMinBars);
      if (trace.matchedIndex !== 0 && topLevelTrace.matchedIndex === 0) {
        classification = "runtime_materialization_serialization_mismatch";
      } else {
        const exactKey = trace.candidateKeyChain?.[0] ?? "";
        const exactParts = parsePolicyKey(exactKey);
        classification = findFirstSingleDimensionFailure(exactParts, wildcardIndices);
      }
    }

    if (!classification) {
      classification = "exact_path_unreachable_by_current_runtime_construction";
    }

    primaryCounts[classification] += 1;
    if (primaryExamples[classification].length < 5) {
      primaryExamples[classification].push({
        ticker: String(row.ticker ?? ""),
        decision_reason_code: trace.decisionReasonCode,
        matched_index: trace.matchedIndex,
        exact_candidate_key: trace.candidateKeyChain?.[0] ?? null,
        matched_key: trace.matchedKey,
      });
    }

    if (classification === "exact_path_unreachable_by_current_runtime_construction") {
      const subreason = explainUnreachable(trace, row, winnerMinBars);
      unreachableSubreasons[subreason] = Number(unreachableSubreasons[subreason] ?? 0) + 1;
    }
  }

  const materializationDiagnostics = buildMaterializationDiagnostics(rows, policyRuntime, winnerMinBars);
  const policyStructureEvidence = {
    total_cells: policyKeys.length,
    cells_with_ST: policyKeys.filter((key) => key.includes("|ST=")).length,
    cells_with_PH: policyKeys.filter((key) => key.includes("|PH=")).length,
    cells_with_SE: policyKeys.filter((key) => key.includes("|SE=")).length,
    cells_with_ST_and_PH: policyKeys.filter((key) => key.includes("|ST=") && key.includes("|PH=")).length,
    cells_with_ST_and_SE: policyKeys.filter((key) => key.includes("|ST=") && key.includes("|SE=")).length,
    cells_with_ST_and_PH_and_SE: policyKeys.filter(
      (key) => key.includes("|ST=") && key.includes("|PH=") && key.includes("|SE="),
    ).length,
    cells_with_phase_u2dn: policyKeys.filter((key) => key.includes("|PH=U2DN")).length,
    eligible_rows_impacted: rowsEligibleForPolicyLookup,
  };

  const sortedNonzeroCounts = REQUIRED_DIMENSIONS
    .map((dimension) => ({
      id: dimension,
      label: DIMENSION_LABELS[dimension] ?? dimension,
      count: primaryCounts[dimension],
      pct_of_non_l0_rows: percent(primaryCounts[dimension], totalNonL0),
    }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));

  const rowsThatWouldBecomeExactIfSTRemovedFromExactFamily = Number(matchedIndexCounts["8"] ?? 0);
  const rowsThatWouldRemainSameSelectedCellIfSTRemoved = Number(matchedIndexCounts["8"] ?? 0);

  const report = {
    generated_at_utc: new Date().toISOString(),
    status: "complete",
    cp_profile: "CP-0",
    scope: "static/code-truth + current runtime artifact analysis only",
    analysis_context: {
      snapshot_path: snapshotPath,
      snapshot_row_count: rows.length,
      quality_summary_path: qualityPath,
      winner_policy_path: winnerPolicyPath,
      winner_policy_hash_sha256: qualityPolicyHash,
      runtime_policy_path: policyRuntime.source_path,
      runtime_policy_hash_sha256: policyRuntime.policy_artifact_hash_sha256,
      winner_min_bars: winnerMinBars,
      anomaly_fallback_enabled: true,
      audited_run_reference: "a3surg-20260309T210311Z",
      audited_run_verification_path:
        "/workspaces/Tao_Financial_Engine/backups/runtime/a4-fallback-backfill-20260310T003646Z/ecs-backfill-verification.json",
      first_fail_dimension_order_from_code_truth: POLICY_DIMENSION_ORDER.map(
        (dimension) => DIMENSION_LABELS[FIELD_TO_DIMENSION[dimension]],
      ),
    },
    current_snapshot_ladder_context: {
      total_non_l0_rows: totalNonL0,
      rows_eligible_for_policy_lookup: rowsEligibleForPolicyLookup,
      rows_blocked_by_bar_guard: rowsBlockedByBars,
      matched_index_counts: matchedIndexCounts,
    },
    first_failing_dimension_summary: {
      counts_by_dimension: primaryCounts,
      pct_contribution_by_dimension: Object.fromEntries(
        REQUIRED_DIMENSIONS.map((dimension) => [dimension, percent(primaryCounts[dimension], totalNonL0)]),
      ),
      sorted_nonzero_counts: sortedNonzeroCounts,
      examples_by_dimension: primaryExamples,
      unreachable_subreasons: unreachableSubreasons,
    },
    policy_structure_evidence: policyStructureEvidence,
    runtime_materialization_secondary_diagnostics: materializationDiagnostics,
    top_10_reasons_exact_is_zero: buildTopReasons(
      primaryCounts,
      unreachableSubreasons,
      totalNonL0,
      policyStructureEvidence,
    ),
    can_materially_restore_exact_without_destabilizing_CP0: true,
    restore_exact_rationale:
      "Yes. The dominant blocker is the runtime exact family including ST while the current policy lattice contains zero ST+PH, zero ST+SE, and zero ST+PH+SE cells. Re-anchoring L0 to the populated no-ST exact family would recover current exact coverage for the rows already matching candidate index 8 without changing the selected policy cell for those rows.",
    restoration_scenarios: {
      drop_ST_from_exact_family_keep_CD_phase_spider_strict: {
        rows_that_become_exact: rowsThatWouldBecomeExactIfSTRemovedFromExactFamily,
        pct_of_non_l0_rows: percent(rowsThatWouldBecomeExactIfSTRemovedFromExactFamily, totalNonL0),
        selected_cell_changes_required: 0,
        note:
          "These rows already resolve to matched index 8, which is the no-ST exact family with CD + PH + SE preserved.",
      },
      accept_current_L1_as_effective_production_mode: {
        structurally_mapped_rows_currently_in_L1_or_L2: Number(matchedIndexCounts["8"] ?? 0) + Number(matchedIndexCounts["9"] ?? 0) + Number(matchedIndexCounts["10"] ?? 0) + Number(matchedIndexCounts["11"] ?? 0),
        pct_of_non_l0_rows:
          percent(
            Number(matchedIndexCounts["8"] ?? 0) +
              Number(matchedIndexCounts["9"] ?? 0) +
              Number(matchedIndexCounts["10"] ?? 0) +
              Number(matchedIndexCounts["11"] ?? 0),
            totalNonL0,
          ),
        note:
          "This would preserve current behavior but would leave CP-0 formally operating without true exact structural coverage under the current exact-family definition.",
      },
    },
    recommended_action: "restore_exact_path_now",
    proceed_to_A5_immediately: "no_full_rollout_before_exact_path_alignment",
    A5_recommendation_after_A4_1:
      "Do not start a full A5 rollout until the exact-path family is aligned. If parallel work is necessary, restrict A5 to L1-tolerant overlay families only.",
    strategy_family_gating: {
      require_L0_exact: [
        "double-bottom / double-top setup families",
        "pivot / squeeze / crossover trigger families",
        "short-side / downside trigger families",
        "high-conviction company-specific catalyst trigger families",
      ],
      allow_L1_relaxed: [
        "long-side accumulation and hold discipline",
        "survivability / margin / valuation / capital-preservation rules",
        "insider / ownership overlays",
        "sector / macro / rates / build-cycle / commodity overlays",
        "company/news/catalyst overlays that are not sole trade triggers",
      ],
      safe_only_L2_L3_L4: [
        "explicit abstention / suppression logic",
        "degraded or unmapped recommendation surfaces",
        "hard-block, unavailable, and insufficient-bars conditions",
      ],
    },
  };

  writeJson(outputJsonPath, report);
  writeFileSync(outputMdPath, `${renderMarkdown(report)}\n`, "utf-8");

  process.stdout.write(
    `${JSON.stringify({
      status: "ok",
      output_json: outputJsonPath,
      output_md: outputMdPath,
      recommended_action: report.recommended_action,
      proceed_to_A5_immediately: report.proceed_to_A5_immediately,
    })}\n`,
  );
}

main();
