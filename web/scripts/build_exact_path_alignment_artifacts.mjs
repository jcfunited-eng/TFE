#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  computeDecisionTrace,
  loadPolicyRuntimeArtifact,
  minBarsForAccumulate,
  sha256Hex,
} from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const CURRENT_EXACT_ANCHOR_MODE = "CURRENT_ST_ANCHORED_EXACT_FAMILY";
const PROPOSED_EXACT_ANCHOR_MODE = "NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT";
const STRATEGY_FAMILY_GATING_REGISTRY = {
  require_L0_exact: [
    "double-bottom / double-top",
    "pivot / squeeze / crossover triggers",
    "short-side / downside triggers",
    "high-conviction company-specific catalyst triggers",
  ],
  allow_L1_relaxed: [
    "long-side accumulation / hold discipline",
    "survivability / margin / valuation / capital-preservation",
    "insider / ownership overlays",
    "sector / macro / rates / build-cycle / commodity overlays",
    "non-sole-trigger news/catalyst overlays",
  ],
  safe_only_L2_L3_L4: [
    "abstention / suppression",
    "degraded or unmapped surfaces",
    "insufficient-bars / unavailable / blocked states",
  ],
};

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

function readOptionalJson(filePath, allowNonFinite = false) {
  if (!existsSync(filePath)) return null;
  return readJson(filePath, allowNonFinite);
}

function writeJson(filePath, payload) {
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

function normalizeBoolean(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (["1", "true", "yes", "on", "y"].includes(text)) return true;
    if (["0", "false", "no", "off", "n", ""].includes(text)) return false;
  }
  return fallback;
}

function toFinite(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function toInt(value) {
  const n = toFinite(value);
  if (n === null) return null;
  return Math.trunc(n);
}

function toBoolean(value) {
  return normalizeBoolean(value, false);
}

function toRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}

function dvValue(row, index) {
  const dv = row.decision_vector;
  if (!Array.isArray(dv)) return null;
  if (index < 0 || index >= dv.length) return null;
  return toFinite(dv[index]);
}

function rowNumberField(row, key) {
  return toFinite(row[key]);
}

function sign3(value) {
  if (value > 0) return 1;
  if (value < 0) return -1;
  return 0;
}

function resolveBasis(row) {
  const regime = String(row?.regime ?? "UNKNOWN");

  let dVal = dvValue(row, 0);
  if (dVal === null) dVal = rowNumberField(row, "D_k");

  let mVal = dvValue(row, 1);
  if (mVal === null) mVal = rowNumberField(row, "M_k");

  let rVal = dvValue(row, 2);
  if (rVal === null) rVal = rowNumberField(row, "R_rev_k");

  let uVal = dvValue(row, 3);
  if (uVal === null) uVal = rowNumberField(row, "U_star_k");

  const dv = row.decision_vector;
  const dvLen = Array.isArray(dv) ? dv.length : 0;

  let cVal = null;
  let pVal = null;
  let bVal = null;

  if (dvLen >= 7) {
    cVal = dvValue(row, 4);
    pVal = dvValue(row, 5);
    bVal = dvValue(row, 6);
  } else if (dvLen >= 6) {
    pVal = dvValue(row, 4);
    bVal = dvValue(row, 5);
  }

  if (cVal === null) cVal = rowNumberField(row, "C_k");
  if (pVal === null) pVal = rowNumberField(row, "P_k");
  if (bVal === null) bVal = rowNumberField(row, "B_k");

  const basis = {
    regime,
    D_k: dVal === null ? null : Math.round(dVal),
    M_k: mVal,
    M_sign: mVal === null ? null : sign3(mVal),
    R_rev_k: rVal === null ? null : (rVal > 0.5 ? 1 : 0),
    U_star_k: uVal,
    C_k: cVal === null ? null : Math.round(cVal),
    P_k: pVal === null ? null : Math.round(pVal),
    B_k: bVal === null ? null : sign3(bVal),
    missing_fields: [],
  };

  if (basis.D_k === null) basis.missing_fields.push("D_k");
  if (basis.M_k === null) basis.missing_fields.push("M_k");
  if (basis.R_rev_k === null) basis.missing_fields.push("R_rev_k");
  if (basis.U_star_k === null) basis.missing_fields.push("U_star_k");
  if (basis.C_k === null) basis.missing_fields.push("C_k");
  if (basis.P_k === null) basis.missing_fields.push("P_k");
  if (basis.B_k === null) basis.missing_fields.push("B_k");

  return basis;
}

function uBucket(value) {
  if (value < 0.33) return "U0";
  if (value < 0.66) return "U1";
  return "U2";
}

function pBucket(value) {
  if (value <= 0) return "P0";
  if (value === 1) return "P1";
  return "P2";
}

function bucket3(value) {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function bucketCdOpt(value) {
  if (value < -0.6) return "B0";
  if (value < -0.4) return "B1";
  if (value < -0.3) return "B2";
  if (value < -0.2) return "B3";
  return "B4";
}

function bucketStability(value) {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function irfPhase(mSign, rUf) {
  if (rUf < 0.33 && mSign > 0) return "U2UP";
  if (rUf > 0.66 && mSign < 0) return "U2DN";
  return "UFLAT";
}

function anomalyFlagsFromRow(row) {
  const guard = toRecord(row.decision_guard);
  const guardGateUnlock = guard
    ? toBoolean(guard.gate_unlock_transient_neutralized)
    : toBoolean(row.gate_unlock_transient_neutralized);

  const hardening = toRecord(row.hardening);
  const hardeningFlags = hardening ? toRecord(hardening.flags) : null;
  const hardeningHysteresisOverload = hardeningFlags
    ? toBoolean(hardeningFlags.hysteresis_overload)
    : toBoolean(row.hysteresis_overload);

  return {
    guard_gate_unlock_transient_neutralized: guardGateUnlock,
    hardening_hysteresis_overload: hardeningHysteresisOverload,
    anomaly_any: guardGateUnlock || hardeningHysteresisOverload,
  };
}

function spiderEyesTag(flags) {
  if (flags.guard_gate_unlock_transient_neutralized && flags.hardening_hysteresis_overload) return "GU_HO";
  if (flags.guard_gate_unlock_transient_neutralized) return "GU";
  if (flags.hardening_hysteresis_overload) return "HO";
  return "NONE";
}

function decisionLabel(value) {
  if (value === "Accumulate" || value === "Hold" || value === "Avoid") return value;
  return "Hold";
}

function deriveTypedFallbackLadderLevel(decisionReasonCode, matchedIndex) {
  const reasonCode = String(decisionReasonCode ?? "").trim();
  const index = Number.isFinite(Number(matchedIndex)) ? Number(matchedIndex) : -1;

  if (reasonCode === "PSCF_POLICY_DECISION") {
    if (index === 0) return "L0_EXACT_STRUCTURAL_MATCH";
    if (index > 0) return "L1_RELAXED_STRUCTURAL_MATCH";
  }

  if (reasonCode === "PSCF_FALLBACK_ANOMALOUS") {
    return "L2_SAFE_POLICY_FALLBACK";
  }

  if (
    reasonCode === "PSCF_FALLBACK_POLICY_MISSING" ||
    reasonCode === "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE" ||
    reasonCode === "PSCF_FALLBACK_CELL_UNMAPPED"
  ) {
    return "L3_DEGRADED_UNMAPPED";
  }

  if (
    reasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS" ||
    reasonCode === "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
  ) {
    return "L4_UNAVAILABLE_OR_BLOCKED";
  }

  return "L3_DEGRADED_UNMAPPED";
}

function suffixVariantEntries(core, phaseTag, spiderTag) {
  const entries = [];
  if (phaseTag && spiderTag) entries.push({ key: `${core}${phaseTag}${spiderTag}`, suffix_variant: "PH_SE" });
  if (phaseTag) entries.push({ key: `${core}${phaseTag}`, suffix_variant: "PH_ONLY" });
  if (spiderTag) entries.push({ key: `${core}${spiderTag}`, suffix_variant: "SE_ONLY" });
  entries.push({ key: core, suffix_variant: "CORE_ONLY" });
  return entries;
}

function uniqueCandidateEntries(entries) {
  const out = [];
  const seen = new Set();
  for (const entry of entries) {
    const key = String(entry?.key ?? "");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(entry);
  }
  return out;
}

function buildCandidateEntries(row, basis, anomalyFlags, exactAnchorMode) {
  if (basis.missing_fields.length > 0) return [];

  const base =
    `reg=${basis.regime}|D=${basis.D_k}|M=${basis.M_sign}|Rrev=${basis.R_rev_k}|` +
    `${uBucket(basis.U_star_k)}|C=${basis.C_k}|${pBucket(basis.P_k)}|B=${basis.B_k}`;

  const sUf = toFinite(row.S_UF) ?? 0;
  const rUf = toFinite(row.R_UF) ?? 0;
  const cd = sUf - rUf;
  const st = bucketStability(toFinite(row.stability_score) ?? 0);
  const phaseTag = `|PH=${irfPhase(basis.M_sign ?? 0, rUf)}`;
  const spiderTag = `|SE=${spiderEyesTag(anomalyFlags)}`;

  const familyMap = {
    enriched_cd_st: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}|ST=${st}`,
    enriched_sr_st: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|ST=${st}`,
    enriched_cd: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}`,
    enriched_sr: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}`,
    base_spider: `${base}|SE=${spiderEyesTag(anomalyFlags)}`,
    base_only: base,
  };

  const familyOrder =
    exactAnchorMode === PROPOSED_EXACT_ANCHOR_MODE
      ? [
          "enriched_cd",
          "enriched_cd_st",
          "enriched_sr_st",
          "enriched_sr",
          "base_spider",
          "base_only",
        ]
      : [
          "enriched_cd_st",
          "enriched_sr_st",
          "enriched_cd",
          "enriched_sr",
          "base_spider",
          "base_only",
        ];

  const entries = [];
  for (const familyId of familyOrder) {
    if (familyId === "base_spider") {
      entries.push({
        key: familyMap.base_spider,
        family_id: familyId,
        suffix_variant: "SE_ONLY",
      });
      continue;
    }
    if (familyId === "base_only") {
      entries.push({
        key: familyMap.base_only,
        family_id: familyId,
        suffix_variant: "CORE_ONLY",
      });
      continue;
    }
    for (const item of suffixVariantEntries(familyMap[familyId], phaseTag, spiderTag)) {
      entries.push({
        key: item.key,
        family_id: familyId,
        suffix_variant: item.suffix_variant,
      });
    }
  }

  return uniqueCandidateEntries(entries);
}

function computeShadowDecisionTrace(row, policyRuntime, minBars, anomalyFallbackEnabled, exactAnchorMode) {
  const basis = resolveBasis(row);
  const anomalyFlags = anomalyFlagsFromRow(row);
  const candidateEntries = buildCandidateEntries(row, basis, anomalyFlags, exactAnchorMode);
  const barCount = Math.max(0, toInt(row.bar_count) ?? 0);
  const cells = policyRuntime?.cells && typeof policyRuntime.cells === "object" ? policyRuntime.cells : null;

  let decision = "Hold";
  let decisionReasonCode = "PSCF_FALLBACK_POLICY_MISSING";
  let fallbackReasonCode = "policy_missing";
  let matchedKey = null;
  let matchedIndex = -1;
  let matchedCandidateEntry = null;

  if (barCount < minBars) {
    decisionReasonCode = "PSCF_FALLBACK_INSUFFICIENT_BARS";
    fallbackReasonCode = "insufficient_bars";
  } else if (basis.missing_fields.length > 0) {
    decisionReasonCode = "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE";
    fallbackReasonCode = "structural_incomplete";
  } else if (!cells || Object.keys(cells).length === 0) {
    decisionReasonCode = "PSCF_FALLBACK_POLICY_MISSING";
    fallbackReasonCode = "policy_missing";
  } else if (candidateEntries.length === 0) {
    decisionReasonCode = "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE";
    fallbackReasonCode = "cell_key_unavailable";
  } else {
    for (let index = 0; index < candidateEntries.length; index += 1) {
      const candidateEntry = candidateEntries[index];
      const cell = cells[candidateEntry.key];
      if (!cell || typeof cell !== "object") continue;
      matchedKey = candidateEntry.key;
      matchedIndex = index;
      matchedCandidateEntry = candidateEntry;
      break;
    }

    if (!matchedKey) {
      decisionReasonCode = "PSCF_FALLBACK_CELL_UNMAPPED";
      fallbackReasonCode = "cell_unmapped";
    } else if (anomalyFallbackEnabled && anomalyFlags.anomaly_any) {
      decisionReasonCode = "PSCF_FALLBACK_ANOMALOUS";
      fallbackReasonCode = "anomalous_row";
    } else {
      const matchedCell = cells[matchedKey] ?? {};
      decision = decisionLabel(matchedCell.decision);
      decisionReasonCode = "PSCF_POLICY_DECISION";
      fallbackReasonCode = null;
    }
  }

  return {
    basis,
    anomalyFlags,
    candidateKeyChain: candidateEntries.map((entry) => entry.key),
    candidateEntries,
    matchedKey,
    matchedIndex,
    matchedCandidateFamily: matchedCandidateEntry?.family_id ?? null,
    matchedCandidateSuffixVariant: matchedCandidateEntry?.suffix_variant ?? null,
    matchedExactBool: decisionReasonCode === "PSCF_POLICY_DECISION" && matchedIndex === 0,
    decision,
    decisionReasonCode,
    fallbackReasonCode,
    fallbackLadderLevel: deriveTypedFallbackLadderLevel(decisionReasonCode, matchedIndex),
    fallbackUsed: decisionReasonCode !== "PSCF_POLICY_DECISION",
    exactAnchorMode,
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
    if (hadOriginal) process.env[key] = original;
    else delete process.env[key];
  }
}

function percent(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function rate(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number((count / total).toFixed(6));
}

function normalizeNullableString(value) {
  const text = String(value ?? "");
  return text || null;
}

function parseSnapshotRows(snapshotPath) {
  const payload = readJson(snapshotPath, true);
  if (Array.isArray(payload)) return payload.filter((row) => row && typeof row === "object");
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) {
    return payload.rows.filter((row) => row && typeof row === "object");
  }
  return [];
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

function buildCountsTemplate(keys) {
  return Object.fromEntries(keys.map((key) => [key, 0]));
}

function sortedCountArray(counts, total) {
  return Object.entries(counts)
    .map(([id, count]) => ({
      id,
      row_count: count,
      row_rate: rate(count, total),
      row_pct: percent(count, total),
    }))
    .filter((item) => item.row_count > 0)
    .sort((a, b) => b.row_count - a.row_count || a.id.localeCompare(b.id));
}

function increment(bucket, key) {
  const normalized = String(key ?? "null");
  bucket[normalized] = Number(bucket[normalized] ?? 0) + 1;
}

function buildExample(row, beforeTrace, afterTrace) {
  return {
    ticker: String(row?.ticker ?? ""),
    current_matched_key: beforeTrace.matchedKey,
    proposed_matched_key: afterTrace.matchedKey,
    current_matched_index: beforeTrace.matchedIndex,
    proposed_matched_index: afterTrace.matchedIndex,
    current_decision: beforeTrace.decision,
    proposed_decision: afterTrace.decision,
    current_decision_reason_code: beforeTrace.decisionReasonCode,
    proposed_decision_reason_code: afterTrace.decisionReasonCode,
    current_fallback_reason_code: beforeTrace.fallbackReasonCode,
    proposed_fallback_reason_code: afterTrace.fallbackReasonCode,
    ladder_level_before: beforeTrace.fallbackLadderLevel,
    ladder_level_after: afterTrace.fallbackLadderLevel,
  };
}

function renderShadowMarkdown(report) {
  const migrationLines = report.summary_metrics.ladder_level_migration_counts_sorted
    .map((item) => `- ${item.from} -> ${item.to}: ${item.row_count} rows (${item.row_pct.toFixed(3)}%)`)
    .join("\n");

  const parityLines = report.current_resolver_parity.sorted_nonzero_mismatches
    .map((item) => `- ${item.id}: ${item.row_count} rows`)
    .join("\n");

  const exactExamples = report.examples.exact_restored_examples
    .map(
      (item) =>
        `- ${item.ticker}: ${item.current_matched_key} -> ${item.proposed_matched_key} | ${item.ladder_level_before} -> ${item.ladder_level_after}`,
    )
    .join("\n");

  const selectedCellExamples = report.examples.selected_cell_change_examples.length
    ? report.examples.selected_cell_change_examples
        .map(
          (item) =>
            `- ${item.ticker}: ${item.current_matched_key} -> ${item.proposed_matched_key} | ${item.current_decision} -> ${item.proposed_decision}`,
        )
        .join("\n")
    : "- none";

  return [
    "# Exact Path Alignment Shadow (Latest)",
    "",
    `Generated (UTC): ${report.generated_at_utc}`,
    "",
    "## Summary",
    "",
    `- Rows evaluated: ${report.summary_metrics.rows_evaluated}`,
    `- Exact restored count: ${report.summary_metrics.exact_restored_count}`,
    `- Exact restored pct: ${report.summary_metrics.exact_restored_pct.toFixed(3)}%`,
    `- Selected cell change count: ${report.summary_metrics.selected_cell_change_count}`,
    `- Decision change count: ${report.summary_metrics.decision_change_count}`,
    `- Fallback reason change count: ${report.summary_metrics.fallback_reason_change_count}`,
    `- Phase 1 pass: ${report.acceptance_gate.pass}`,
    "",
    "## Ladder Level Migrations",
    "",
    migrationLines || "- none",
    "",
    "## Current Resolver Parity Against Live ComputeDecisionTrace",
    "",
    parityLines || "- no mismatches",
    "",
    "## Exact Restored Examples",
    "",
    exactExamples || "- none",
    "",
    "## Selected Cell Change Examples",
    "",
    selectedCellExamples,
    "",
  ].join("\n");
}

function renderContractMarkdown(contract) {
  const currentOrder = contract.current_exact_path_resolver.family_order.map((item) => `- ${item}`).join("\n");
  const proposedOrder = contract.proposed_exact_path_resolver.family_order.map((item) => `- ${item}`).join("\n");
  const requireL0 = contract.strategy_family_gating_registry.require_L0_exact.map((item) => `- ${item}`).join("\n");
  const allowL1 = contract.strategy_family_gating_registry.allow_L1_relaxed.map((item) => `- ${item}`).join("\n");
  const safeOnly = contract.strategy_family_gating_registry.safe_only_L2_L3_L4.map((item) => `- ${item}`).join("\n");

  return [
    "# Exact Path Alignment Contract (Latest)",
    "",
    `Generated (UTC): ${contract.generated_at_utc}`,
    "",
    "## Objective",
    "",
    "- Restore CP-0 exact-path construction by moving the exact anchor to the populated no-ST exact family.",
    "- Keep ranking, allocator semantics, refresh/oracle/L5 learning, and public reader behavior unchanged in A4.2 shadow/admin phases.",
    "",
    "## Current Exact Path Resolver",
    "",
    `- Mode: ${contract.current_exact_path_resolver.mode}`,
    currentOrder,
    "",
    "## Proposed Exact Path Resolver",
    "",
    `- Mode: ${contract.proposed_exact_path_resolver.mode}`,
    `- Scope: ${contract.proposed_exact_path_resolver.scope}`,
    proposedOrder,
    "",
    "## Phase Contract",
    "",
    "- Phase 1: shadow only. Compute current and proposed traces for every runtime row and write the shadow/readiness artifacts.",
    "- Phase 2: admin/internal only. Expose the shadow metrics through `/api/admin/exact-path-alignment`.",
    "- Phase 3: controlled adoption only after explicit approval. Switch the CP-0 exact anchor to the proposed mode only if the shadow gate remains clean.",
    "",
    "## Shadow Acceptance Gate",
    "",
    "- selected_cell_change_count must be zero unless explicitly explained and approved.",
    "- decision_change_count must be zero unless explicitly explained and approved.",
    "- exact_restored_count must be materially positive.",
    "- no new mismatch or failure classes may be introduced.",
    "",
    "## Strategy Family Gating Registry",
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
  const runtimeSemanticsPath = path.join(root, "runtime_fallback_semantics_latest.json");
  const persistencePath = path.join(root, "current_l5_provenance_persistence_latest.json");
  const shadowJsonPath = path.join(root, "exact_path_alignment_shadow_latest.json");
  const shadowMdPath = path.join(root, "exact_path_alignment_shadow_latest.md");
  const contractMdPath = path.join(root, "exact_path_alignment_contract_latest.md");
  const readinessJsonPath = path.join(root, "exact_path_alignment_readiness_latest.json");

  const snapshotRows = parseSnapshotRows(snapshotPath);
  const runtimeSemantics = readOptionalJson(runtimeSemanticsPath);
  const persistenceArtifact = readOptionalJson(persistencePath);
  const runtimeSourceContext = runtimeSemantics?.source_context && typeof runtimeSemantics.source_context === "object"
    ? runtimeSemantics.source_context
    : {};
  const configuredPolicyPath = String(runtimeSourceContext.policy_artifact_path ?? "").trim();
  const policyRuntime = configuredPolicyPath && existsSync(configuredPolicyPath)
    ? loadPolicyRuntimeFromPath(configuredPolicyPath)
    : loadPolicyRuntimeArtifact(root);
  const minBars = Math.trunc(Number(runtimeSourceContext.decision_provenance_min_bars ?? minBarsForAccumulate())) || minBarsForAccumulate();
  const anomalyFallbackEnabled = normalizeBoolean(runtimeSourceContext.anomaly_fallback_enabled, false);

  const currentDecisionReasonCodes = new Set();
  const proposedDecisionReasonCodes = new Set();
  const currentFallbackReasonCodes = new Set();
  const proposedFallbackReasonCodes = new Set();
  const currentLevelCounts = {};
  const proposedLevelCounts = {};
  const currentMatchedIndexCounts = {};
  const proposedMatchedIndexCounts = {};
  const ladderLevelMigrationCounts = {};
  const resolverParityMismatches = buildCountsTemplate([
    "matched_key_mismatch",
    "matched_index_mismatch",
    "decision_mismatch",
    "decision_reason_mismatch",
    "fallback_reason_mismatch",
    "ladder_level_mismatch",
  ]);
  const resolverParityExamples = [];
  const selectedCellChangeExamples = [];
  const decisionChangeExamples = [];
  const fallbackReasonChangeExamples = [];
  const exactRestoredExamples = [];

  let rowsEvaluated = 0;
  let exactRestoredCount = 0;
  let selectedCellChangeCount = 0;
  let decisionChangeCount = 0;
  let fallbackReasonChangeCount = 0;

  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", anomalyFallbackEnabled ? "1" : "0", () => {
    for (const row of snapshotRows) {
      const liveCurrentTrace = computeDecisionTrace(row, policyRuntime, minBars);
      const shadowCurrentTrace = computeShadowDecisionTrace(
        row,
        policyRuntime,
        minBars,
        anomalyFallbackEnabled,
        CURRENT_EXACT_ANCHOR_MODE,
      );
      const proposedTrace = computeShadowDecisionTrace(
        row,
        policyRuntime,
        minBars,
        anomalyFallbackEnabled,
        PROPOSED_EXACT_ANCHOR_MODE,
      );

      rowsEvaluated += 1;
      increment(currentLevelCounts, liveCurrentTrace.fallbackLadderLevel);
      increment(proposedLevelCounts, proposedTrace.fallbackLadderLevel);
      increment(currentMatchedIndexCounts, liveCurrentTrace.matchedIndex);
      increment(proposedMatchedIndexCounts, proposedTrace.matchedIndex);
      increment(ladderLevelMigrationCounts, `${liveCurrentTrace.fallbackLadderLevel}=>${proposedTrace.fallbackLadderLevel}`);

      currentDecisionReasonCodes.add(String(liveCurrentTrace.decisionReasonCode ?? ""));
      proposedDecisionReasonCodes.add(String(proposedTrace.decisionReasonCode ?? ""));
      if (liveCurrentTrace.fallbackReasonCode !== null) currentFallbackReasonCodes.add(String(liveCurrentTrace.fallbackReasonCode));
      if (proposedTrace.fallbackReasonCode !== null) proposedFallbackReasonCodes.add(String(proposedTrace.fallbackReasonCode));

      if (normalizeNullableString(liveCurrentTrace.matchedKey) !== normalizeNullableString(shadowCurrentTrace.matchedKey)) {
        resolverParityMismatches.matched_key_mismatch += 1;
      }
      if (Number(liveCurrentTrace.matchedIndex) !== Number(shadowCurrentTrace.matchedIndex)) {
        resolverParityMismatches.matched_index_mismatch += 1;
      }
      if (String(liveCurrentTrace.decision ?? "") !== String(shadowCurrentTrace.decision ?? "")) {
        resolverParityMismatches.decision_mismatch += 1;
      }
      if (String(liveCurrentTrace.decisionReasonCode ?? "") !== String(shadowCurrentTrace.decisionReasonCode ?? "")) {
        resolverParityMismatches.decision_reason_mismatch += 1;
      }
      if (normalizeNullableString(liveCurrentTrace.fallbackReasonCode) !== normalizeNullableString(shadowCurrentTrace.fallbackReasonCode)) {
        resolverParityMismatches.fallback_reason_mismatch += 1;
      }
      if (String(liveCurrentTrace.fallbackLadderLevel ?? "") !== String(shadowCurrentTrace.fallbackLadderLevel ?? "")) {
        resolverParityMismatches.ladder_level_mismatch += 1;
      }

      if (resolverParityExamples.length < 5) {
        const mismatchKeys = Object.entries({
          matched_key_mismatch:
            normalizeNullableString(liveCurrentTrace.matchedKey) !== normalizeNullableString(shadowCurrentTrace.matchedKey),
          matched_index_mismatch: Number(liveCurrentTrace.matchedIndex) !== Number(shadowCurrentTrace.matchedIndex),
          decision_mismatch: String(liveCurrentTrace.decision ?? "") !== String(shadowCurrentTrace.decision ?? ""),
          decision_reason_mismatch:
            String(liveCurrentTrace.decisionReasonCode ?? "") !== String(shadowCurrentTrace.decisionReasonCode ?? ""),
          fallback_reason_mismatch:
            normalizeNullableString(liveCurrentTrace.fallbackReasonCode) !== normalizeNullableString(shadowCurrentTrace.fallbackReasonCode),
          ladder_level_mismatch:
            String(liveCurrentTrace.fallbackLadderLevel ?? "") !== String(shadowCurrentTrace.fallbackLadderLevel ?? ""),
        })
          .filter(([, changed]) => changed)
          .map(([key]) => key);
        if (mismatchKeys.length > 0) {
          resolverParityExamples.push({
            ticker: String(row?.ticker ?? ""),
            mismatch_classes: mismatchKeys,
            live: buildExample(row, liveCurrentTrace, liveCurrentTrace),
            shadow_current: buildExample(row, shadowCurrentTrace, shadowCurrentTrace),
          });
        }
      }

      const selectedCellChanged = normalizeNullableString(liveCurrentTrace.matchedKey) !== normalizeNullableString(proposedTrace.matchedKey);
      const decisionChanged = String(liveCurrentTrace.decision ?? "") !== String(proposedTrace.decision ?? "");
      const fallbackReasonChanged =
        normalizeNullableString(liveCurrentTrace.fallbackReasonCode) !== normalizeNullableString(proposedTrace.fallbackReasonCode);
      const exactRestored = liveCurrentTrace.matchedExactBool !== true && proposedTrace.matchedExactBool === true;

      if (selectedCellChanged) {
        selectedCellChangeCount += 1;
        if (selectedCellChangeExamples.length < 10) {
          selectedCellChangeExamples.push(buildExample(row, liveCurrentTrace, proposedTrace));
        }
      }

      if (decisionChanged) {
        decisionChangeCount += 1;
        if (decisionChangeExamples.length < 10) {
          decisionChangeExamples.push(buildExample(row, liveCurrentTrace, proposedTrace));
        }
      }

      if (fallbackReasonChanged) {
        fallbackReasonChangeCount += 1;
        if (fallbackReasonChangeExamples.length < 10) {
          fallbackReasonChangeExamples.push(buildExample(row, liveCurrentTrace, proposedTrace));
        }
      }

      if (exactRestored) {
        exactRestoredCount += 1;
        if (exactRestoredExamples.length < 10) {
          exactRestoredExamples.push(buildExample(row, liveCurrentTrace, proposedTrace));
        }
      }
    }
  });

  const newFailureDecisionReasonCodes = Array.from(proposedDecisionReasonCodes)
    .filter((code) => code && code !== "PSCF_POLICY_DECISION" && !currentDecisionReasonCodes.has(code))
    .sort();
  const newFailureFallbackReasonCodes = Array.from(proposedFallbackReasonCodes)
    .filter((code) => code && !currentFallbackReasonCodes.has(code))
    .sort();
  const resolverParityMismatchCount = Object.values(resolverParityMismatches).reduce((sum, value) => sum + Number(value ?? 0), 0);

  const acceptanceBlockedReasons = [];
  if (resolverParityMismatchCount > 0) {
    acceptanceBlockedReasons.push("shadow_current_resolver_does_not_match_live_computeDecisionTrace");
  }
  if (selectedCellChangeCount > 0) {
    acceptanceBlockedReasons.push("selected_cell_change_count_nonzero");
  }
  if (decisionChangeCount > 0) {
    acceptanceBlockedReasons.push("decision_change_count_nonzero");
  }
  if (exactRestoredCount <= 0) {
    acceptanceBlockedReasons.push("exact_restored_count_not_materially_positive");
  }
  if (newFailureDecisionReasonCodes.length > 0 || newFailureFallbackReasonCodes.length > 0) {
    acceptanceBlockedReasons.push("new_failure_classes_introduced");
  }

  const shadowReport = {
    generated_at_utc: new Date().toISOString(),
    status: "complete",
    cp_profile: "CP-0",
    analysis_context: {
      snapshot_path: snapshotPath,
      snapshot_row_count: snapshotRows.length,
      runtime_policy_path: policyRuntime.source_path,
      runtime_policy_hash_sha256: policyRuntime.policy_artifact_hash_sha256,
      persisted_provenance_run_id: String(persistenceArtifact?.run_id ?? runtimeSourceContext.persisted_provenance_run_id ?? "").trim() || null,
      decision_provenance_min_bars: minBars,
      anomaly_fallback_enabled: anomalyFallbackEnabled,
      current_exact_anchor_mode: CURRENT_EXACT_ANCHOR_MODE,
      proposed_exact_anchor_mode: PROPOSED_EXACT_ANCHOR_MODE,
    },
    current_resolver_parity: {
      total_rows_checked: rowsEvaluated,
      mismatch_count: resolverParityMismatchCount,
      mismatch_rate: rate(resolverParityMismatchCount, rowsEvaluated),
      counts_by_class: resolverParityMismatches,
      sorted_nonzero_mismatches: sortedCountArray(resolverParityMismatches, rowsEvaluated),
      examples: resolverParityExamples,
    },
    summary_metrics: {
      rows_evaluated: rowsEvaluated,
      exact_restored_count: exactRestoredCount,
      exact_restored_pct: percent(exactRestoredCount, rowsEvaluated),
      selected_cell_change_count: selectedCellChangeCount,
      decision_change_count: decisionChangeCount,
      fallback_reason_change_count: fallbackReasonChangeCount,
      ladder_level_migration_counts: ladderLevelMigrationCounts,
      ladder_level_migration_counts_sorted: sortedCountArray(ladderLevelMigrationCounts, rowsEvaluated).map((item) => {
        const [from, to] = item.id.split("=>");
        return {
          from,
          to,
          row_count: item.row_count,
          row_rate: item.row_rate,
          row_pct: item.row_pct,
        };
      }),
    },
    current_path_summary: {
      level_counts: currentLevelCounts,
      level_counts_sorted: sortedCountArray(currentLevelCounts, rowsEvaluated),
      matched_index_counts: currentMatchedIndexCounts,
      matched_index_counts_sorted: sortedCountArray(currentMatchedIndexCounts, rowsEvaluated),
    },
    proposed_path_summary: {
      level_counts: proposedLevelCounts,
      level_counts_sorted: sortedCountArray(proposedLevelCounts, rowsEvaluated),
      matched_index_counts: proposedMatchedIndexCounts,
      matched_index_counts_sorted: sortedCountArray(proposedMatchedIndexCounts, rowsEvaluated),
    },
    new_failure_classes_introduced: {
      decision_reason_codes: newFailureDecisionReasonCodes,
      fallback_reason_codes: newFailureFallbackReasonCodes,
      none_introduced: newFailureDecisionReasonCodes.length === 0 && newFailureFallbackReasonCodes.length === 0,
    },
    acceptance_gate: {
      selected_cell_change_count_pass: selectedCellChangeCount === 0,
      decision_change_count_pass: decisionChangeCount === 0,
      exact_restored_materially_positive: exactRestoredCount > 0,
      no_new_failure_classes_introduced:
        newFailureDecisionReasonCodes.length === 0 && newFailureFallbackReasonCodes.length === 0,
      pass: acceptanceBlockedReasons.length === 0,
      blocked_reasons: acceptanceBlockedReasons,
    },
    examples: {
      exact_restored_examples: exactRestoredExamples,
      selected_cell_change_examples: selectedCellChangeExamples,
      decision_change_examples: decisionChangeExamples,
      fallback_reason_change_examples: fallbackReasonChangeExamples,
    },
  };

  const readiness = {
    generated_at_utc: shadowReport.generated_at_utc,
    status: "complete",
    cp_profile: "CP-0",
    current_exact_anchor_mode: CURRENT_EXACT_ANCHOR_MODE,
    proposed_exact_anchor_mode: PROPOSED_EXACT_ANCHOR_MODE,
    phase_1_shadow: {
      pass: shadowReport.acceptance_gate.pass,
      rows_evaluated: rowsEvaluated,
      exact_restored_count: exactRestoredCount,
      exact_restored_pct: shadowReport.summary_metrics.exact_restored_pct,
      selected_cell_change_count: selectedCellChangeCount,
      decision_change_count: decisionChangeCount,
      fallback_reason_change_count: fallbackReasonChangeCount,
      blocked_reasons: acceptanceBlockedReasons,
    },
    phase_2_admin_internal_exposure: {
      ready: shadowReport.acceptance_gate.pass,
      scope: "admin/internal only",
      route_path: "/api/admin/exact-path-alignment",
      note: shadowReport.acceptance_gate.pass
        ? "Shadow metrics are ready for admin/internal exposure only. No public ranking or allocator behavior changes are included."
        : "Do not expose adoption guidance yet. Shadow gate is not clean.",
    },
    phase_3_controlled_adoption: {
      ready: shadowReport.acceptance_gate.pass,
      executed: false,
      blocked_reasons: shadowReport.acceptance_gate.pass ? [] : acceptanceBlockedReasons,
      note: shadowReport.acceptance_gate.pass
        ? "Readiness gate passed. Controlled adoption still requires explicit approval before switching the exact anchor."
        : "Controlled adoption remains blocked until the shadow gate is clean.",
    },
    strategy_family_gating_registry: STRATEGY_FAMILY_GATING_REGISTRY,
    recommendation: shadowReport.acceptance_gate.pass
      ? "Phase 3 can be prepared, but do not switch the exact anchor until explicitly approved. Do not start full A5 before this adoption decision is assessed."
      : "Keep A4.2 in shadow mode. Do not proceed to Phase 3 or full A5.",
    paths: {
      shadow_json: shadowJsonPath,
      shadow_md: shadowMdPath,
      contract_md: contractMdPath,
    },
  };

  const contract = {
    generated_at_utc: shadowReport.generated_at_utc,
    current_exact_path_resolver: {
      mode: CURRENT_EXACT_ANCHOR_MODE,
      family_order: [
        "enriched_cd_st exact family (CD + ST + PH + SE strict first)",
        "enriched_sr_st fallback family",
        "enriched_cd fallback family",
        "enriched_sr fallback family",
        "base spider fallback",
        "base-only fallback",
      ],
    },
    proposed_exact_path_resolver: {
      mode: PROPOSED_EXACT_ANCHOR_MODE,
      scope: "drop ST from the exact anchor while keeping CD + PH + SE strictness",
      family_order: [
        "enriched_cd exact family (CD + PH + SE strict first)",
        "enriched_cd_st fallback family",
        "enriched_sr_st fallback family",
        "enriched_sr fallback family",
        "base spider fallback",
        "base-only fallback",
      ],
    },
    strategy_family_gating_registry: STRATEGY_FAMILY_GATING_REGISTRY,
  };

  writeJson(shadowJsonPath, shadowReport);
  writeFileSync(shadowMdPath, `${renderShadowMarkdown(shadowReport)}\n`, "utf-8");
  writeJson(readinessJsonPath, readiness);
  writeFileSync(contractMdPath, `${renderContractMarkdown(contract)}\n`, "utf-8");

  process.stdout.write(
    `${JSON.stringify({
      status: "ok",
      shadow_json: shadowJsonPath,
      shadow_md: shadowMdPath,
      contract_md: contractMdPath,
      readiness_json: readinessJsonPath,
      phase_1_pass: readiness.phase_1_shadow.pass,
      phase_2_ready: readiness.phase_2_admin_internal_exposure.ready,
      phase_3_ready: readiness.phase_3_controlled_adoption.ready,
    })}\n`,
  );
}

main();
