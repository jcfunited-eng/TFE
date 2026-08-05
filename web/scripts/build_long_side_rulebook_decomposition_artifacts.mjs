#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { computeDecisionTrace, loadPolicyRuntimeArtifact } from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const VALUATION_FIELDS = ["marketCap", "peRatio", "forwardPE", "priceToBook", "priceToSales", "evToEbitda", "evToSales", "pegRatio"];
const SURVIVABILITY_FIELDS = [
  "currentRatio",
  "quickRatio",
  "debtToEquity",
  "longTermDebtToEquity",
  "cashPerShare",
  "freeCashflow",
  "profitMargin",
  "operatingMargin",
  "grossMargin",
];
const MARGIN_QUALITY_FIELDS = ["grossMargin", "operatingMargin", "profitMargin", "roa", "roe", "roic"];

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
    if (!allowNonFinite) throw error;
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

function writeText(filePath, text) {
  writeFileSync(filePath, `${String(text ?? "").replace(/\s+$/u, "")}\n`, "utf-8");
}

function parseSnapshotRows(snapshotPath) {
  const payload = readJson(snapshotPath, true);
  if (Array.isArray(payload)) return payload.filter((row) => row && typeof row === "object");
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) {
    return payload.rows.filter((row) => row && typeof row === "object");
  }
  return [];
}

function parseQuoteRows(quotePath) {
  const payload = readJson(quotePath);
  return payload && typeof payload === "object" && payload.rows && typeof payload.rows === "object" ? payload.rows : {};
}

function pct(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function updateCount(bucket, key, amount = 1) {
  const normalized = String(key ?? "").trim() || "null";
  bucket[normalized] = Number(bucket[normalized] ?? 0) + amount;
}

function sortedCountArray(counts, total) {
  return Object.entries(counts)
    .map(([key, count]) => ({ key, count: Number(count), pct: pct(Number(count), total) }))
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return a.key.localeCompare(b.key);
    });
}

function fieldPresent(value) {
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "boolean") return true;
  return false;
}

function missingFields(quote, fields) {
  if (!quote || typeof quote !== "object") return [...fields];
  return fields.filter((field) => !fieldPresent(quote[field]));
}

function summarizeLadder(contexts) {
  const out = {
    L0_EXACT_STRUCTURAL_MATCH: { row_count: 0, pct: 0 },
    L1_RELAXED_STRUCTURAL_MATCH: { row_count: 0, pct: 0 },
    L2_SAFE_POLICY_FALLBACK: { row_count: 0, pct: 0 },
    L3_DEGRADED_UNMAPPED: { row_count: 0, pct: 0 },
    L4_UNAVAILABLE_OR_BLOCKED: { row_count: 0, pct: 0 },
  };
  for (const context of contexts) {
    out[context.trace.fallbackLadderLevel].row_count += 1;
  }
  for (const value of Object.values(out)) {
    value.pct = pct(value.row_count, contexts.length);
  }
  return out;
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

function buildLongSideContexts(snapshotRows, quoteRows, policyRuntime, minBars, anomalyFallbackEnabled) {
  const contexts = [];
  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", anomalyFallbackEnabled ? "1" : "0", () => {
    for (const row of snapshotRows) {
      const ticker = String(row.ticker ?? "").trim().toUpperCase();
      const quote = ticker ? quoteRows[ticker] ?? null : null;
      const trace = computeDecisionTrace(row, policyRuntime, minBars);
      const ladder = trace.fallbackLadderLevel;
      const eligibleForLongSide = Boolean(
        quote && (ladder === "L0_EXACT_STRUCTURAL_MATCH" || ladder === "L1_RELAXED_STRUCTURAL_MATCH"),
      );
      if (!eligibleForLongSide) continue;
      const valuationMissing = missingFields(quote, VALUATION_FIELDS);
      const survivabilityMissing = missingFields(quote, SURVIVABILITY_FIELDS);
      const marginMissing = missingFields(quote, MARGIN_QUALITY_FIELDS);
      const recencyKeys = Object.keys(row).filter((key) => key.startsWith("steps_since_") || key.includes("recency"));
      const epochKeys = Object.keys(row).filter(
        (key) => key.includes("epoch") || key === "regime_code" || key === "gap_state",
      );
      const hasEpochObject = Boolean(row.epoch && typeof row.epoch === "object" && !Array.isArray(row.epoch));
      contexts.push({
        ticker,
        row,
        quote,
        trace,
        decision: trace.decision,
        valuationMissing,
        survivabilityMissing,
        marginMissing,
        hasValuationStrict: valuationMissing.length === 0,
        hasSurvivabilityStrict: survivabilityMissing.length === 0,
        hasMarginStrict: marginMissing.length === 0,
        hasRecency: recencyKeys.length > 0,
        hasEpoch: epochKeys.length > 0 || hasEpochObject,
        recencyKeys,
        epochKeys,
      });
    }
  });
  return contexts;
}

function ladderRequirementObject(requirement) {
  return {
    declared_requirement: requirement,
    exact_required: requirement === "require_L0_exact",
    relaxed_allowed: requirement === "allow_L1_relaxed",
    safe_only: requirement === "safe_only_L2_L3_L4",
  };
}

function buildSubfamilyView({
  id,
  label,
  axis,
  baseContexts,
  eligibleSelector,
  blockedReasonForContext,
  ladderRequirement,
  governanceStatus,
  activationReadiness,
  competitivenessRoiEstimate,
  notes,
  dataContract,
}) {
  const eligibleContexts = [];
  const blockedReasonCounts = {};
  const missingFieldCounts = {};

  for (const context of baseContexts) {
    if (eligibleSelector(context)) {
      eligibleContexts.push(context);
      continue;
    }
    const reason = blockedReasonForContext(context);
    updateCount(blockedReasonCounts, reason);
    if (reason.startsWith("strict_field_set_incomplete:")) {
      const missing =
        reason.includes("valuation")
          ? context.valuationMissing
          : reason.includes("survivability")
            ? context.survivabilityMissing
            : reason.includes("margin_quality")
              ? context.marginMissing
              : [];
      for (const field of missing) {
        updateCount(missingFieldCounts, field);
      }
    }
  }

  return {
    id,
    label,
    axis,
    base_population_row_count: baseContexts.length,
    eligible_row_count: eligibleContexts.length,
    eligible_pct_of_base_population: pct(eligibleContexts.length, baseContexts.length),
    current_ladder_distribution: summarizeLadder(eligibleContexts),
    blocked_reasons: sortedCountArray(blockedReasonCounts, baseContexts.length),
    missing_field_counts_when_relevant: sortedCountArray(missingFieldCounts, baseContexts.length),
    exact_required_vs_relaxed_allowed: ladderRequirementObject(ladderRequirement),
    governance_status: governanceStatus,
    activation_readiness: activationReadiness,
    competitiveness_roi_estimate: competitivenessRoiEstimate,
    data_contract: dataContract ?? null,
    notes,
  };
}

function renderMarkdown(payload) {
  const subfamilyLines = payload.subfamilies
    .map((item) => {
      const topBlocked = item.blocked_reasons[0]
        ? `${item.blocked_reasons[0].key} (${item.blocked_reasons[0].count})`
        : "none";
      return `- \`${item.id}\`: eligible=${item.eligible_row_count}/${item.base_population_row_count} (${item.eligible_pct_of_base_population.toFixed(3)}% of base, ${item.eligible_pct_of_total_snapshot.toFixed(3)}% of total), readiness=${item.activation_readiness}, ROI=${item.competitiveness_roi_estimate.summary}. Top blocker: ${topBlocked}`;
    })
    .join("\n");

  const missingFamilyLines = payload.next_missing_competitive_family_readiness
    .map(
      (item) =>
        `- \`${item.id}\`: coverage=${item.current_coverage_pct.toFixed(6)}%, readiness=${item.readiness_status}, next_contract=${item.next_required_contract}`,
    )
    .join("\n");

  return [
    "# Long-Side Rulebook Decomposition (Latest)",
    "",
    `Generated (UTC): ${payload.generated_at_utc}`,
    `Status: ${payload.status}`,
    `CP Profile: ${payload.cp_profile}`,
    "",
    "## Context",
    "",
    `- Long-side eligible rows: ${payload.context.long_side_family_eligible_row_count}`,
    `- Total snapshot rows: ${payload.context.total_snapshot_rows}`,
    `- Admin winner policy: ${payload.context.policy_path}`,
    `- Admin winner min bars: ${payload.context.min_bars}`,
    `- Admin winner anomaly fallback enabled: ${payload.context.anomaly_fallback_enabled}`,
    "",
    "## Subfamilies",
    "",
    subfamilyLines,
    "",
    "## Next Missing Competitive Families",
    "",
    missingFamilyLines,
    "",
    `Recommended next step: ${payload.recommendation.recommended_option}`,
    `Rationale: ${payload.recommendation.rationale}`,
    "",
  ].join("\n");
}

function main() {
  const root = resolveWorkspaceRoot();
  const snapshotPath = path.join(root, "uf_snapshot.json");
  const quotePath = path.join(root, "web", "data", "screener-quote-cache.json");
  const adminCoveragePath = path.join(root, "admin_rulebook_coverage_latest.json");
  const outJsonPath = path.join(root, "long_side_rulebook_decomposition_latest.json");
  const outMdPath = path.join(root, "long_side_rulebook_decomposition_latest.md");
  const readinessPath = path.join(root, "long_side_activation_readiness_latest.json");

  const snapshotRows = parseSnapshotRows(snapshotPath);
  const quoteRows = parseQuoteRows(quotePath);
  const adminCoverage = readJson(adminCoveragePath);
  const policyRuntime = loadPolicyRuntimeArtifact(root);

  const context = adminCoverage?.runtime_contexts?.eligibility_view_context ?? {};
  const longSideFamily = Array.isArray(adminCoverage?.runtime_eligibility_blockage_view)
    ? adminCoverage.runtime_eligibility_blockage_view.find(
        (item) => item.strategy_family_id === "long_side_accumulation_hold_discipline",
      )
    : null;

  if (!longSideFamily) {
    throw new Error("Long-side family coverage not found in admin_rulebook_coverage_latest.json");
  }

  const minBars = Math.trunc(Number(context.min_bars ?? 252));
  const anomalyFallbackEnabled = context.anomaly_fallback_enabled === true;
  const longSideContexts = buildLongSideContexts(snapshotRows, quoteRows, policyRuntime, minBars, anomalyFallbackEnabled);

  if (longSideContexts.length !== Number(longSideFamily.eligible_row_count ?? -1)) {
    throw new Error(
      `Long-side eligible row count mismatch: computed=${longSideContexts.length} expected=${longSideFamily.eligible_row_count}`,
    );
  }

  const accumulationContexts = longSideContexts.filter((contextRow) => contextRow.decision === "Accumulate");
  const holdDisciplineContexts = longSideContexts.filter(
    (contextRow) => contextRow.decision === "Hold" || contextRow.decision === "Avoid",
  );
  const holdOnlyContexts = longSideContexts.filter((contextRow) => contextRow.decision === "Hold");

  const subfamilies = [
    buildSubfamilyView({
      id: "accumulation_core",
      label: "Accumulation Core",
      axis: "accumulation_vs_hold_discipline",
      baseContexts: longSideContexts,
      eligibleSelector: (contextRow) => contextRow.decision === "Accumulate",
      blockedReasonForContext: (contextRow) => `current_decision_not_accumulate:${contextRow.decision}`,
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_not_yet_split_into_activation_registry",
      activationReadiness: "ready_for_admin_contract_only",
      competitivenessRoiEstimate: {
        summary: "high",
        rationale:
          "Current CP-0 already resolves 2997 long-side rows to Accumulate under the active admin winner context, so governed decomposition can proceed without adding a new external channel.",
      },
      notes: [
        "This is a decomposition of the existing long-side family only. No activation or ranking change is implied.",
      ],
      dataContract: {
        type: "current_decision_split",
        required_fields: ["decision"],
        strict_complete_field_set: true,
      },
    }),
    buildSubfamilyView({
      id: "hold_discipline_core",
      label: "Hold-Discipline Core",
      axis: "accumulation_vs_hold_discipline",
      baseContexts: longSideContexts,
      eligibleSelector: (contextRow) => contextRow.decision === "Hold" || contextRow.decision === "Avoid",
      blockedReasonForContext: () => "current_decision_accumulate",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_not_yet_split_into_activation_registry",
      activationReadiness: "ready_for_admin_contract_only",
      competitivenessRoiEstimate: {
        summary: "high",
        rationale:
          "Current CP-0 routes 5449 long-side rows into Hold/Avoid, so no-add discipline is the dominant governance path inside the existing family.",
      },
      notes: [
        "Hold-discipline is reported as the existing no-add path inside the long-side family. It remains separate from degraded-mode abstention semantics.",
      ],
      dataContract: {
        type: "current_decision_split",
        required_fields: ["decision"],
        strict_complete_field_set: true,
      },
    }),
    buildSubfamilyView({
      id: "valuation_protected_accumulation",
      label: "Valuation-Protected Accumulation",
      axis: "valuation_protected_accumulation",
      baseContexts: accumulationContexts,
      eligibleSelector: (contextRow) => contextRow.hasValuationStrict,
      blockedReasonForContext: () => "strict_field_set_incomplete:valuation",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_pending_valuation_contract",
      activationReadiness: "blocked_sparse_data_contract_and_threshold_registry_missing",
      competitivenessRoiEstimate: {
        summary: "low_current_reach",
        rationale:
          `Only 9 of ${accumulationContexts.length} accumulation rows have the full strict valuation field set currently materialized.`,
      },
      notes: [
        "Strict valuation readiness currently requires every listed valuation field to be present; this is a conservative admin-only readiness contract, not an activation heuristic.",
      ],
      dataContract: {
        type: "strict_complete_field_set",
        required_fields: VALUATION_FIELDS,
        strict_complete_field_set: true,
      },
    }),
    buildSubfamilyView({
      id: "survivability_capital_preservation_protected_accumulation",
      label: "Survivability / Capital-Preservation Protected Accumulation",
      axis: "survivability_capital_preservation_protected_accumulation",
      baseContexts: accumulationContexts,
      eligibleSelector: (contextRow) => contextRow.hasSurvivabilityStrict,
      blockedReasonForContext: () => "strict_field_set_incomplete:survivability",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_pending_survivability_contract",
      activationReadiness: "blocked_sparse_data_contract_and_threshold_registry_missing",
      competitivenessRoiEstimate: {
        summary: "low_current_reach",
        rationale:
          `Only 57 of ${accumulationContexts.length} accumulation rows have the full strict survivability field set currently materialized.`,
      },
      notes: [
        "Strict survivability readiness currently requires the full liquidity, leverage, cashflow, and margin basket to be present.",
      ],
      dataContract: {
        type: "strict_complete_field_set",
        required_fields: SURVIVABILITY_FIELDS,
        strict_complete_field_set: true,
      },
    }),
    buildSubfamilyView({
      id: "margin_quality_discipline",
      label: "Margin / Quality Discipline",
      axis: "margin_quality_discipline",
      baseContexts: accumulationContexts,
      eligibleSelector: (contextRow) => contextRow.hasMarginStrict,
      blockedReasonForContext: () => "strict_field_set_incomplete:margin_quality",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_pending_margin_quality_contract",
      activationReadiness: "blocked_sparse_data_contract_and_threshold_registry_missing",
      competitivenessRoiEstimate: {
        summary: "low_current_reach",
        rationale:
          `Only 51 of ${accumulationContexts.length} accumulation rows have the full strict margin/quality field set currently materialized.`,
      },
      notes: [
        "Margin/quality readiness currently requires the full current profitability and return-on-capital basket to be present.",
      ],
      dataContract: {
        type: "strict_complete_field_set",
        required_fields: MARGIN_QUALITY_FIELDS,
        strict_complete_field_set: true,
      },
    }),
    buildSubfamilyView({
      id: "recency_sensitive_accumulation",
      label: "Recency-Sensitive Accumulation",
      axis: "recency_sensitive_accumulation",
      baseContexts: accumulationContexts,
      eligibleSelector: (contextRow) => contextRow.hasRecency,
      blockedReasonForContext: () => "no_structural_recency_fields_present",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_pending_structural_recency_materialization",
      activationReadiness: "blocked_missing_structural_recency_materialization",
      competitivenessRoiEstimate: {
        summary: "blocked",
        rationale: `None of the ${accumulationContexts.length} accumulation rows expose structural recency fields in the current runtime snapshot.`,
      },
      notes: [
        "A2 epoch decomposition / structural recency hardening is a dependency for this subfamily.",
      ],
      dataContract: {
        type: "runtime_structural_recency_fields",
        required_fields: ["steps_since_* or recency*"],
        strict_complete_field_set: false,
      },
    }),
    buildSubfamilyView({
      id: "epoch_assisted_accumulation",
      label: "Epoch-Assisted Accumulation",
      axis: "epoch_assisted_accumulation",
      baseContexts: accumulationContexts,
      eligibleSelector: (contextRow) => contextRow.hasEpoch,
      blockedReasonForContext: () => "no_epoch_fields_present",
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_pending_epoch_materialization",
      activationReadiness: "blocked_missing_epoch_materialization",
      competitivenessRoiEstimate: {
        summary: "blocked",
        rationale: `None of the ${accumulationContexts.length} accumulation rows expose epoch fields in the current runtime snapshot.`,
      },
      notes: [
        "This subfamily depends on explicit epoch inputs rather than compressed regime-only state.",
      ],
      dataContract: {
        type: "runtime_epoch_fields",
        required_fields: ["epoch.* or regime_code or gap_state"],
        strict_complete_field_set: false,
      },
    }),
    buildSubfamilyView({
      id: "hold_only_no_add_discipline",
      label: "Hold-Only / No-Add Discipline",
      axis: "hold_only_no_add_discipline",
      baseContexts: longSideContexts,
      eligibleSelector: (contextRow) => contextRow.decision === "Hold",
      blockedReasonForContext: (contextRow) => `current_decision_not_hold:${contextRow.decision}`,
      ladderRequirement: "allow_L1_relaxed",
      governanceStatus: "admin_taxonomy_only_not_yet_split_into_activation_registry",
      activationReadiness: "ready_for_admin_contract_only",
      competitivenessRoiEstimate: {
        summary: "high_governance_leverage",
        rationale:
          "Current CP-0 already resolves 4467 long-side rows to Hold, making hold-only/no-add discipline the single largest explicit no-add state inside the family.",
      },
      notes: [
        "Hold-only/no-add is narrower than hold-discipline core because it excludes current Avoid decisions.",
      ],
      dataContract: {
        type: "current_decision_split",
        required_fields: ["decision"],
        strict_complete_field_set: true,
      },
    }),
  ].map((entry) => ({
    ...entry,
    eligible_pct_of_total_snapshot: pct(entry.eligible_row_count, snapshotRows.length),
  }));

  const nextMissingCompetitiveFamilyReadiness = [
    {
      id: "pattern_setup_extraction",
      label: "Pattern Setup Extraction",
      current_coverage_pct: 0,
      readiness_status: "blocked_missing_runtime_setup_signal_extraction",
      blocking_dependencies: [
        "setup_signal_extraction_contract",
        "setup_state_materialization_in_runtime_snapshot",
        "pattern_family_precedence_registry",
      ],
      next_required_contract: "A5.4_pattern_setup_signal_contract_v1",
      rationale:
        "A5.1 showed zero eligible rows for pattern/setup overlays because the current runtime snapshot does not materialize setup-state signals.",
    },
    {
      id: "company_news_catalyst_event_source",
      label: "Company News / Catalyst Event Source",
      current_coverage_pct: 0,
      readiness_status: "blocked_missing_event_source_and_quantification_contract",
      blocking_dependencies: [
        "company_news_event_source_contract",
        "catalyst_quantification_contract",
        "timestamped_event_provenance_contract",
      ],
      next_required_contract: "A5.4_company_news_catalyst_event_contract_v1",
      rationale:
        "A5.1 showed zero eligible rows because no company-news or catalyst event source is materialized in current runtime artifacts.",
    },
    {
      id: "sector_macro_epoch_event_source",
      label: "Sector / Macro / Epoch Event Source",
      current_coverage_pct: 0,
      readiness_status: "blocked_missing_driver_source_and_sphere_mapping_contract",
      blocking_dependencies: [
        "macro_epoch_driver_contract",
        "sector_sphere_mapping_contract",
        "epoch_quantification_contract",
      ],
      next_required_contract: "A5.4_sector_macro_epoch_event_contract_v1",
      rationale:
        "A5.1 showed zero eligible rows because current runtime artifacts expose sector taxonomy but not the macro/epoch drivers or sphere mapping needed for decision governance.",
    },
    {
      id: "short_side_downside_family",
      label: "Short-Side / Downside Family",
      current_coverage_pct: 0,
      readiness_status: "blocked_out_of_cp0_scope_and_missing_short_side_semantics",
      blocking_dependencies: [
        "cp0_scope_approval_for_short_side",
        "short_side_action_semantics_contract",
        "borrow_shortability_governance_contract",
      ],
      next_required_contract: "A5.4_short_side_downside_contract_v1",
      rationale:
        "A5.1 showed zero eligible rows because the family is not applicable to current CP-0 and short-side semantics are not wired.",
    },
  ];

  const readinessPayload = {
    analysis_name: "A5_2_long_side_activation_readiness",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    long_side_family_context: {
      total_snapshot_rows: snapshotRows.length,
      long_side_family_eligible_row_count: longSideContexts.length,
      accumulation_row_count: accumulationContexts.length,
      hold_discipline_row_count: holdDisciplineContexts.length,
      hold_only_row_count: holdOnlyContexts.length,
      current_long_side_blocked_reasons: longSideFamily.blocked_reasons,
    },
    subfamily_activation_readiness: subfamilies.map((entry) => ({
      id: entry.id,
      label: entry.label,
      activation_readiness: entry.activation_readiness,
      governance_status: entry.governance_status,
      eligible_row_count: entry.eligible_row_count,
      eligible_pct_of_base_population: entry.eligible_pct_of_base_population,
      eligible_pct_of_total_snapshot: entry.eligible_pct_of_total_snapshot,
      top_blocked_reason: entry.blocked_reasons[0] ?? null,
      data_contract: entry.data_contract,
    })),
    next_missing_competitive_family_readiness: nextMissingCompetitiveFamilyReadiness,
    recommendation: {
      recommended_option: "A5.3 long-side subfamily activation readiness",
      rationale:
        "The dominant family is now decomposed, and three subfamilies already have admin-contract readiness without requiring a new external event source. Zero-coverage families remain blocked on new source contracts, so A5.3 is the highest-ROI next step before A5.4.",
      alternatives_considered: [
        {
          option: "A5.4 event-source contracts for zero-coverage families",
          why_not_recommended_first:
            "Necessary, but it does not improve control over the dominant 78.066365% long-side family before new external channels are introduced.",
        },
        {
          option: "A6 promotion-gate upgrade",
          why_not_recommended_first:
            "Promotion semantics should follow the governed long-side subfamily split, not precede it.",
        },
        {
          option: "A7 proof-plane upgrade",
          why_not_recommended_first:
            "Proof-plane reporting is higher value after the dominant family has governed activation-readiness classes.",
        },
      ],
    },
  };

  const payload = {
    analysis_name: "A5_2_long_side_rulebook_decomposition",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    lineage_baseline: "Section 9 strict lineage baseline for L5 revisions remains in force.",
    source_truth: [
      "admin_rulebook_coverage_latest.json",
      "uf_snapshot.json",
      "web/data/screener-quote-cache.json",
      "pscf_policy_runtime.json",
      "runtime_decision_provenance.mjs",
    ],
    scope: "Admin/internal decomposition only. No production strategy activation, no ranking change, and no allocator change.",
    context: {
      total_snapshot_rows: snapshotRows.length,
      long_side_family_eligible_row_count: longSideContexts.length,
      long_side_family_eligible_pct_of_total_snapshot: pct(longSideContexts.length, snapshotRows.length),
      policy_path: String(context.policy_path ?? ""),
      min_bars: minBars,
      anomaly_fallback_enabled: anomalyFallbackEnabled,
      long_side_family_ladder_distribution: summarizeLadder(longSideContexts),
      long_side_decision_distribution: sortedCountArray(
        longSideContexts.reduce((bucket, contextRow) => {
          updateCount(bucket, contextRow.decision);
          return bucket;
        }, {}),
        longSideContexts.length,
      ),
      long_side_family_blocked_reasons: longSideFamily.blocked_reasons,
      methodology:
        "Subfamily eligibility is reported as an admin-only readiness view. For protective subfamilies, eligibility means the row is already in the current long-side accumulation base and the full strict current data contract for that protection family is present. This does not imply activation.",
    },
    decomposition_axes: [
      "accumulation vs hold-discipline",
      "valuation-protected accumulation",
      "survivability / capital-preservation protected accumulation",
      "margin/quality discipline",
      "recency-sensitive accumulation",
      "epoch-assisted accumulation",
      "hold-only / no-add discipline",
      "ladder-level requirements by subfamily",
    ],
    subfamilies,
    next_missing_competitive_family_readiness: nextMissingCompetitiveFamilyReadiness,
    recommendation: readinessPayload.recommendation,
  };

  writeJson(outJsonPath, payload);
  writeText(outMdPath, renderMarkdown(payload));
  writeJson(readinessPath, readinessPayload);

  process.stdout.write(
    `${JSON.stringify({ status: "ok", output_json: outJsonPath, output_md: outMdPath, readiness_json: readinessPath, long_side_rows: longSideContexts.length })}\n`,
  );
}

main();
