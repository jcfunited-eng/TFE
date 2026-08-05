#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  computeDecisionTrace,
  loadPolicyRuntimeArtifact,
  TYPED_FALLBACK_LEVELS,
} from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const CURRENT_HORIZONS = [5, 20, 60];
const INSIDER_FIELDS = ["insiderOwn", "insiderTrans", "instOwn", "instTrans"];
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

const STRATEGY_RUNTIME_RULES = {
  long_side_accumulation_hold_discipline: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "runtime_quote_cache"],
    missing_dependencies: ["strategy_family_activation_logic", "class_precedence_registry", "horizon_specific_hold_discipline_rules"],
    risk_class: "medium",
    governance_status: "registry_declared_not_active",
    purpose:
      "Long-side accumulation and hold discipline layer that operates inside current structural governance without changing CP-0 ranking or allocator semantics.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      if (!rowContext.hasQuote) return { eligible: false, blockedReason: "runtime_quote_row_missing" };
      return { eligible: true, blockedReason: null };
    },
  },
  short_side_downside_families: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "runtime_quote_cache", "shortability_borrow_profile"],
    missing_dependencies: [
      "cp0_scope_excludes_short_side_activation",
      "short_side_action_semantics_not_wired",
      "borrow_shortability_governance_policy",
      "strategy_family_activation_logic",
    ],
    risk_class: "high",
    governance_status: "registry_declared_not_active_out_of_scope_for_cp0",
    purpose:
      "Controlled short-side and downside-protection family for future CP-1/CP-2 activation; it is not in current CP-0 production scope.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      return { eligible: false, blockedReason: "short_side_activation_not_permitted_in_cp0" };
    },
  },
  pattern_setup_tactical_overlays: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "setup_signal_extraction"],
    missing_dependencies: ["setup_signal_extraction", "setup_activation_registry_wiring", "family_precedence_registry"],
    risk_class: "high",
    governance_status: "registry_declared_not_active",
    purpose:
      "Deterministic setup overlays for exact structural matches only. Current CP-0 runtime does not materialize setup-state signals needed for activation.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      return { eligible: false, blockedReason: "setup_signal_extraction_missing" };
    },
  },
  insider_ownership_rules: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "runtime_quote_cache", "insider_ownership_profile"],
    missing_dependencies: [
      "timestamped_insider_event_provenance",
      "deterministic_insider_threshold_transforms",
      "strategy_family_activation_logic",
    ],
    risk_class: "medium",
    governance_status: "registry_declared_not_active",
    purpose:
      "Insider and ownership overlays that require provenance, timestamps, and source confidence before they are allowed to govern decisions.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      if (!rowContext.hasQuote) return { eligible: false, blockedReason: "runtime_quote_row_missing" };
      if (!rowContext.hasInsiderProfile) return { eligible: false, blockedReason: "insider_ownership_profile_missing" };
      return { eligible: true, blockedReason: null };
    },
  },
  company_news_catalyst_rules: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "company_news_event_source", "sphere_of_impact_mapping"],
    missing_dependencies: [
      "company_news_event_source",
      "catalyst_quantification_transform",
      "sphere_of_impact_mapping",
      "strategy_family_activation_logic",
    ],
    risk_class: "high",
    governance_status: "registry_declared_not_active",
    purpose:
      "Company-specific news and catalyst layer that should govern recommendations only when event provenance, quantification, and sphere mapping are explicit.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      return { eligible: false, blockedReason: "company_news_event_source_missing" };
    },
  },
  sector_macro_epoch_intelligence: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "runtime_quote_cache", "sector_taxonomy", "macro_epoch_event_source", "sphere_of_impact_mapping"],
    missing_dependencies: [
      "macro_epoch_event_source",
      "sector_sphere_mapping_runtime_wiring",
      "epoch_quantification_transform",
      "strategy_family_activation_logic",
    ],
    risk_class: "high",
    governance_status: "registry_declared_not_active",
    purpose:
      "Sector, macro, rates, war, build-cycle, and commodity intelligence layer that should act through explicit epoch and sphere mappings, not implicit drift.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      if (!rowContext.hasQuote) return { eligible: false, blockedReason: "runtime_quote_row_missing" };
      if (!rowContext.hasSectorTaxonomy) return { eligible: false, blockedReason: "sector_taxonomy_missing" };
      return { eligible: false, blockedReason: "macro_epoch_event_source_missing" };
    },
  },
  valuation_margin_survivability_capital_preservation: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "runtime_quote_cache", "valuation_profile", "survivability_profile"],
    missing_dependencies: [
      "deterministic_valuation_threshold_registry",
      "deterministic_survivability_threshold_registry",
      "strategy_family_activation_logic",
    ],
    risk_class: "medium",
    governance_status: "registry_declared_not_active",
    purpose:
      "Capital-preservation overlays for valuation tension, survivability, and margin discipline that should constrain structurally attractive rows before activation.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      if (!rowContext.hasQuote) return { eligible: false, blockedReason: "runtime_quote_row_missing" };
      if (!rowContext.hasValuationProfile) return { eligible: false, blockedReason: "valuation_profile_missing" };
      if (!rowContext.hasSurvivabilityProfile) return { eligible: false, blockedReason: "survivability_profile_missing" };
      return { eligible: true, blockedReason: null };
    },
  },
  abstention_suppression_degraded_mode: {
    dependent_channels: ["typed_fallback_ladder", "runtime_snapshot", "degraded_mode_reporting"],
    missing_dependencies: ["explicit_strategy_registry_wiring_for_suppression"],
    risk_class: "low",
    governance_status: "registry_declared_not_active_but_runtime_fallback_semantics_exist",
    purpose:
      "Explicit abstention, suppression, and degraded-mode hygiene family that should govern non-structural states without changing ranking semantics.",
    rowGate(rowContext) {
      if (!rowContext.appliesToCp0) return { eligible: false, blockedReason: "family_not_applicable_to_cp0" };
      if (!rowContext.ladderEligible) return { eligible: false, blockedReason: `minimum_ladder_not_met:${rowContext.trace.fallbackLadderLevel}` };
      return { eligible: true, blockedReason: null };
    },
  },
};

const SETUP_GROUPS = [
  {
    id: "double_bottom_top",
    name: "Double Bottom / Top",
    members: ["double_bottom", "double_top"],
    dependency_gaps: ["setup_signal_extraction", "setup_activation_wiring", "family_precedence_registry"],
  },
  {
    id: "pivot",
    name: "Pivot",
    members: ["pivot_recovery", "failed_pivot_breakdown"],
    dependency_gaps: ["setup_signal_extraction", "setup_activation_wiring", "family_precedence_registry"],
  },
  {
    id: "squeeze_breakout",
    name: "Squeeze / Breakout",
    members: ["bollinger_squeeze_release", "volatility_expansion_contraction", "breakout_with_structural_confirmation"],
    dependency_gaps: ["setup_signal_extraction", "breakout_confirmation_wiring", "family_precedence_registry"],
  },
  {
    id: "crossover_trend",
    name: "Crossover / Trend",
    members: ["moving_average_crossover", "moving_average_trend_continuation", "rsi_momentum_exhaustion_reversal"],
    dependency_gaps: ["setup_signal_extraction", "trend_state_wiring", "family_precedence_registry"],
  },
  {
    id: "short_side_triggers",
    name: "Short-Side Triggers",
    members: ["double_top", "failed_pivot_breakdown", "moving_average_crossover", "bollinger_squeeze_release", "breakout_with_structural_confirmation"],
    dependency_gaps: ["cp0_scope_excludes_short_side_activation", "short_side_setup_registry", "family_precedence_registry"],
  },
  {
    id: "catalyst_triggers",
    name: "Catalyst Triggers",
    members: [],
    dependency_gaps: ["missing_in_setup_registry", "company_news_event_source", "catalyst_quantification_transform"],
  },
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
  const rows = payload && typeof payload === "object" && payload.rows && typeof payload.rows === "object" ? payload.rows : {};
  return rows;
}

function numberOrNull(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function pct(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function rate(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number((count / total).toFixed(6));
}

function stringOrNull(value) {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text : null;
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

function arrayToLookup(items, keyField = "id") {
  const out = {};
  for (const item of items) {
    const key = stringOrNull(item?.[keyField]);
    if (!key) continue;
    out[key] = item;
  }
  return out;
}

function fieldPresent(value) {
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "boolean") return true;
  return false;
}

function hasAnyField(quote, fields) {
  if (!quote || typeof quote !== "object") return false;
  return fields.some((field) => fieldPresent(quote[field]));
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

function ladderRequirementSatisfied(requirement, ladderLevel) {
  if (requirement === "require_L0_exact") return ladderLevel === "L0_EXACT_STRUCTURAL_MATCH";
  if (requirement === "allow_L1_relaxed") {
    return ladderLevel === "L0_EXACT_STRUCTURAL_MATCH" || ladderLevel === "L1_RELAXED_STRUCTURAL_MATCH";
  }
  if (requirement === "safe_only_L2_L3_L4") {
    return (
      ladderLevel === "L2_SAFE_POLICY_FALLBACK" ||
      ladderLevel === "L3_DEGRADED_UNMAPPED" ||
      ladderLevel === "L4_UNAVAILABLE_OR_BLOCKED"
    );
  }
  return false;
}

function sortObjectKeys(obj) {
  return Object.fromEntries(
    Object.entries(obj).sort(([a], [b]) => a.localeCompare(b)),
  );
}

function uniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function buildRowContexts(snapshotRows, quoteRows, policyRuntime, minBars, anomalyFallbackEnabled) {
  const contexts = [];
  withTemporaryEnv("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", anomalyFallbackEnabled ? "1" : "0", () => {
    for (const row of snapshotRows) {
      const ticker = String(row.ticker ?? "").trim().toUpperCase();
      const quote = ticker ? quoteRows[ticker] ?? null : null;
      const trace = computeDecisionTrace(row, policyRuntime, minBars);
      contexts.push({
        ticker,
        row,
        trace,
        quote,
        sector: stringOrNull(quote?.sector),
        industry: stringOrNull(quote?.industry),
        hasQuote: Boolean(quote),
        hasSectorTaxonomy: Boolean(stringOrNull(quote?.sector) && stringOrNull(quote?.industry)),
        hasInsiderProfile: hasAnyField(quote, INSIDER_FIELDS),
        hasValuationProfile: hasAnyField(quote, VALUATION_FIELDS),
        hasSurvivabilityProfile: hasAnyField(quote, SURVIVABILITY_FIELDS),
      });
    }
  });
  return contexts;
}

function summarizeLadder(contexts) {
  const out = {};
  for (const level of TYPED_FALLBACK_LEVELS) {
    out[level.id] = { row_count: 0, pct: 0 };
  }
  for (const context of contexts) {
    out[context.trace.fallbackLadderLevel].row_count += 1;
  }
  for (const level of TYPED_FALLBACK_LEVELS) {
    out[level.id].pct = pct(out[level.id].row_count, contexts.length);
  }
  return out;
}

function sectorDistribution(contexts) {
  const counts = {};
  for (const context of contexts) {
    updateCount(counts, context.sector ?? "Unclassified");
  }
  return sortedCountArray(counts, contexts.length);
}

function buildStrategyFamilyCoverage(strategyFamilies, contexts, gapItems) {
  const familyCoverage = [];
  const runtimeView = [];

  for (const family of strategyFamilies) {
    const familyId = String(family.id ?? "").trim();
    const config = STRATEGY_RUNTIME_RULES[familyId];
    if (!config) {
      throw new Error(`Missing strategy runtime rule config for family: ${familyId}`);
    }

    const minimumMatchRequirement = String(family.minimum_match_requirement ?? "").trim();
    const appliesTo = Array.isArray(family.applies_to) ? family.applies_to.map((value) => String(value)) : [];
    const doctrine = Array.isArray(family.doctrine) ? family.doctrine.map((value) => String(value)) : [];
    const relatedGapIds = gapItems
      .filter((item) => /financial strategy rulebook coverage|epoch handling and structural recency handling|portfolio allocator and action semantics/i.test(String(item.area ?? "")))
      .filter((item) => {
        const haystack = JSON.stringify(item).toLowerCase();
        if (familyId.includes("short_side")) return haystack.includes("short-side") || haystack.includes("downside");
        if (familyId.includes("pattern_setup")) return haystack.includes("setup") || haystack.includes("pattern");
        if (familyId.includes("insider")) return haystack.includes("insider") || haystack.includes("ownership");
        if (familyId.includes("company_news")) return haystack.includes("news") || haystack.includes("catalyst");
        if (familyId.includes("sector_macro")) return haystack.includes("sector") || haystack.includes("epoch") || haystack.includes("macro");
        if (familyId.includes("valuation_margin")) return haystack.includes("valuation") || haystack.includes("survivability") || haystack.includes("capital");
        if (familyId.includes("abstention")) return haystack.includes("suppression") || haystack.includes("abstention") || haystack.includes("degraded");
        return haystack.includes("strategy-family governance") || haystack.includes("class-based governance");
      })
      .map((item) => item.id);

    const blockedReasonCounts = {};
    const gateBlockedReasonCounts = {};
    const eligibleContexts = [];
    const gateEligibleContexts = [];
    for (const context of contexts) {
      const rowContext = {
        ...context,
        appliesToCp0: appliesTo.includes("CP-0"),
        ladderEligible: ladderRequirementSatisfied(minimumMatchRequirement, context.trace.fallbackLadderLevel),
      };
      if (rowContext.ladderEligible) {
        gateEligibleContexts.push(context);
      } else {
        updateCount(gateBlockedReasonCounts, `minimum_ladder_not_met:${context.trace.fallbackLadderLevel}`);
      }
      const decision = config.rowGate(rowContext);
      if (decision.eligible) {
        eligibleContexts.push(context);
      } else {
        updateCount(blockedReasonCounts, decision.blockedReason);
      }
    }

    const eligibleCount = eligibleContexts.length;
    const blockedCount = contexts.length - eligibleCount;
    const gateEligibleCount = gateEligibleContexts.length;
    const gateBlockedCount = contexts.length - gateEligibleCount;
    const eligibleLadderDistribution = summarizeLadder(eligibleContexts);
    const eligibleSectorDistribution = sectorDistribution(eligibleContexts);

    familyCoverage.push({
      id: familyId,
      name: String(family.label ?? familyId),
      purpose: config.purpose,
      scaffold_only: true,
      implemented: false,
      active: false,
      required_ladder_level: minimumMatchRequirement,
      dependent_channels: config.dependent_channels,
      missing_dependencies: config.missing_dependencies,
      governance_status: config.governance_status,
      risk_class: config.risk_class,
      applies_to: appliesTo,
      doctrine: doctrine,
      related_gap_ids: uniqueStrings(relatedGapIds),
      source_refs: Array.isArray(family.source_refs) ? family.source_refs : [],
    });

    runtimeView.push({
      strategy_family_id: familyId,
      strategy_family_name: String(family.label ?? familyId),
      eligibility_definition:
        "Eligible means the row satisfies the family's declared typed-fallback gate in the current admin quality winner context and all currently materialized runtime data channels required for later activation are present. This is not strategy activation.",
      gate_eligible_row_count: gateEligibleCount,
      gate_eligible_pct: pct(gateEligibleCount, contexts.length),
      eligible_row_count: eligibleCount,
      eligible_pct: pct(eligibleCount, contexts.length),
      blocked_row_count: blockedCount,
      blocked_pct: pct(blockedCount, contexts.length),
      gate_blocked_row_count: gateBlockedCount,
      gate_blocked_pct: pct(gateBlockedCount, contexts.length),
      blocked_reasons: sortedCountArray(blockedReasonCounts, contexts.length),
      gate_blocked_reasons: sortedCountArray(gateBlockedReasonCounts, contexts.length),
      ladder_level_distribution: eligibleLadderDistribution,
      sector_distribution: eligibleSectorDistribution,
      horizon_applicability: {
        supported_horizons: CURRENT_HORIZONS,
        family_specific_specialization_status: "not_declared_in_registry_currently",
      },
    });
  }

  return { familyCoverage, runtimeView };
}

function buildSetupCoverage(setupFamilies, strategyFamilyCoverage) {
  const lookup = arrayToLookup(setupFamilies);
  const out = [];
  for (const group of SETUP_GROUPS) {
    const memberRecords = group.members.map((id) => lookup[id]).filter(Boolean);
    const registryStatus =
      group.members.length === 0
        ? "missing_in_setup_registry"
        : memberRecords.length === group.members.length
          ? "declared_in_registry"
          : memberRecords.length > 0
            ? "partially_declared_in_registry"
            : "missing_in_setup_registry";
    const implementationStatus = memberRecords.length > 0 ? "registry_only_not_implemented" : "missing_in_registry_and_not_implemented";
    const activationStatus = "inactive";
    const relatedStrategy = strategyFamilyCoverage.find((item) => item.id === "pattern_setup_tactical_overlays");
    out.push({
      id: group.id,
      name: group.name,
      registry_status: registryStatus,
      implementation_status: implementationStatus,
      activation_status: activationStatus,
      members: memberRecords.map((record) => ({
        id: record.id,
        label: record.label,
        directional_mode: record.directional_mode,
        minimum_match_requirement: record.minimum_match_requirement,
        source_refs: Array.isArray(record.source_refs) ? record.source_refs : [],
      })),
      dependency_gaps: uniqueStrings([
        ...group.dependency_gaps,
        ...(relatedStrategy ? relatedStrategy.missing_dependencies : []),
      ]),
    });
  }
  return out;
}

function buildInformationEventCoverage(infoRegistry, couplingRegistry, rowContexts) {
  const infoLookup = arrayToLookup(infoRegistry);
  const sectorCoverageCount = rowContexts.filter((row) => row.hasSectorTaxonomy).length;
  const insiderCoverageCount = rowContexts.filter((row) => row.hasInsiderProfile).length;

  return [
    {
      id: "insider_activity",
      label: "Insider Activity",
      registry_members: ["insider_transaction", "insider_conviction_cluster", "ownership_change"].map((id) => infoLookup[id]).filter(Boolean),
      source_maturity: {
        status: insiderCoverageCount > 0 ? "runtime_quote_profile_available" : "no_runtime_source_visible",
        covered_row_count: insiderCoverageCount,
        covered_row_pct: pct(insiderCoverageCount, rowContexts.length),
        evidence: ["web/data/screener-quote-cache.json:rows.*.{insiderOwn,insiderTrans,instOwn,instTrans}"],
      },
      quantification_maturity: "not_decision_governing_in_cp0",
      sphere_mapping_maturity: "not_mapped_in_current_runtime_artifacts",
      advisory_only_vs_decision_governing: "advisory_fields_present_only_not_decision_governing",
    },
    {
      id: "company_specific_news",
      label: "Company-Specific News",
      registry_members: ["company_news_catalyst", "company_news_contagion_or_sympathy", "filing_event"].map((id) => infoLookup[id]).filter(Boolean),
      source_maturity: {
        status: "no_runtime_source_visible",
        covered_row_count: 0,
        covered_row_pct: 0,
        evidence: ["information_event_registry_v1.json", "uf_snapshot.json:rows[*] (no company-news fields)", "current_l5_code_truth_to_spec_gap_latest.json:G043"],
      },
      quantification_maturity: "missing_in_cp0",
      sphere_mapping_maturity: "missing_in_cp0",
      advisory_only_vs_decision_governing: "not_available_in_current_runtime_artifacts",
    },
    {
      id: "macro_events",
      label: "Macro Events",
      registry_members: couplingRegistry,
      source_maturity: {
        status: "regime_only_no_explicit_macro_event_materialization",
        covered_row_count: 0,
        covered_row_pct: 0,
        evidence: ["uf_snapshot.json:rows[*].regime", "current_l5_code_truth_to_spec_gap_latest.json:G029"],
      },
      quantification_maturity: "missing_in_cp0_serving_logic",
      sphere_mapping_maturity: "registry_declared_only",
      advisory_only_vs_decision_governing: "declared_in_registry_not_decision_governing",
    },
    {
      id: "rates_war_commodity_build_cycle_sector_pressure",
      label: "Rates / War / Commodity / Build-Cycle / Sector Pressure",
      registry_members: couplingRegistry,
      source_maturity: {
        status: sectorCoverageCount > 0 ? "sector_taxonomy_available_but_driver_source_missing" : "no_runtime_source_visible",
        covered_row_count: sectorCoverageCount,
        covered_row_pct: pct(sectorCoverageCount, rowContexts.length),
        evidence: ["web/data/screener-quote-cache.json:rows.*.{sector,industry}", "sector_sphere_coupling_registry_v1.json", "current_l5_code_truth_to_spec_gap_latest.json:G029"],
      },
      quantification_maturity: "missing_driver_quantification",
      sphere_mapping_maturity: "registry_declared_only_not_runtime_wired",
      advisory_only_vs_decision_governing: "sector_taxonomy_available_but_not_decision_governing",
    },
  ].map((entry) => ({
    ...entry,
    registry_member_count: entry.registry_members.length,
  }));
}

function buildHeuristicsGovernanceCoverage(heuristicsRegistry) {
  const approved = Array.isArray(heuristicsRegistry.approved_heuristics) ? heuristicsRegistry.approved_heuristics : [];
  const activeMap = {
    stale_snapshot_rejection: {
      active: true,
      justification_present: true,
      audit_trail_present: true,
      applicable_ladder_levels: TYPED_FALLBACK_LEVELS.map((level) => level.id),
      dependency_on_exact_vs_relaxed_matching: "orthogonal_serving_layer",
      evidence_paths: ["web/src/app/api/recommendations/list/route.ts:430", "web/src/app/api/recommendations/list/route.ts:497"],
    },
    explicit_data_integrity_rejection: {
      active: false,
      justification_present: true,
      audit_trail_present: false,
      applicable_ladder_levels: null,
      dependency_on_exact_vs_relaxed_matching: "not_verified_in_current_cp0_decision_surface",
      evidence_paths: ["heuristics_registry_v1.json:approved_heuristics[1]"],
    },
    forced_abstention_on_collapse_or_safemode: {
      active: false,
      justification_present: true,
      audit_trail_present: false,
      applicable_ladder_levels: null,
      dependency_on_exact_vs_relaxed_matching: "not_verified_in_current_cp0_decision_surface",
      evidence_paths: ["heuristics_registry_v1.json:approved_heuristics[2]"],
    },
    approved_sector_epoch_hard_blocks: {
      active: false,
      justification_present: true,
      audit_trail_present: false,
      applicable_ladder_levels: null,
      dependency_on_exact_vs_relaxed_matching: "intended_orthogonal_but_not_wired",
      evidence_paths: ["heuristics_registry_v1.json:approved_heuristics[3]", "current_l5_code_truth_to_spec_gap_latest.json:G029"],
    },
    deterministic_cooldowns_after_explicit_structural_reversals: {
      active: false,
      justification_present: true,
      audit_trail_present: false,
      applicable_ladder_levels: null,
      dependency_on_exact_vs_relaxed_matching: "not_verified_in_current_cp0_decision_surface",
      evidence_paths: ["heuristics_registry_v1.json:approved_heuristics[4]"],
    },
  };

  return approved.map((heuristic) => {
    const id = String(heuristic.id ?? "").trim();
    const active = activeMap[id] ?? {
      active: false,
      justification_present: false,
      audit_trail_present: false,
      applicable_ladder_levels: null,
      dependency_on_exact_vs_relaxed_matching: "not_mapped",
      evidence_paths: [],
    };
    return {
      id,
      label: String(heuristic.label ?? id),
      approved: true,
      active: active.active,
      justification_present: active.justification_present,
      audit_trail_present: active.audit_trail_present,
      applicable_ladder_levels: active.applicable_ladder_levels,
      dependency_on_exact_vs_relaxed_matching: active.dependency_on_exact_vs_relaxed_matching,
      registry_status: heuristic.status ?? null,
      source_refs: Array.isArray(heuristic.source_refs) ? heuristic.source_refs : [],
      evidence_paths: active.evidence_paths,
    };
  });
}

function buildPrioritizationSummary(strategyFamilyCoverage, runtimeEligibilityView) {
  const familyById = arrayToLookup(strategyFamilyCoverage);
  const prioritized = runtimeEligibilityView
    .map((row) => {
      const family = familyById[row.strategy_family_id];
      return {
        id: row.strategy_family_id,
        name: row.strategy_family_name,
        eligible_row_count: row.eligible_row_count,
        eligible_pct: row.eligible_pct,
        required_ladder_level: family.required_ladder_level,
        missing_dependency_count: Array.isArray(family.missing_dependencies) ? family.missing_dependencies.length : 0,
        risk_class: family.risk_class,
        governance_status: family.governance_status,
        applies_to_cp0: Array.isArray(family.applies_to) && family.applies_to.includes("CP-0"),
      };
    })
    .sort((a, b) => {
      if (Number(b.applies_to_cp0) !== Number(a.applies_to_cp0)) return Number(b.applies_to_cp0) - Number(a.applies_to_cp0);
      if (b.eligible_row_count !== a.eligible_row_count) return b.eligible_row_count - a.eligible_row_count;
      if (a.missing_dependency_count !== b.missing_dependency_count) return a.missing_dependency_count - b.missing_dependency_count;
      const riskOrder = { low: 0, medium: 1, high: 2 };
      if (riskOrder[a.risk_class] !== riskOrder[b.risk_class]) return riskOrder[a.risk_class] - riskOrder[b.risk_class];
      return a.name.localeCompare(b.name);
    });

  const blockers = [
    {
      id: "G042",
      blocker: "No active strategy-family governance layer in CP-0 APIs.",
      source: "current_l5_code_truth_to_spec_gap_latest.json:G042",
      competitiveness_impact: "high",
    },
    {
      id: "G043",
      blocker: "Setup, insider, ownership, and company-news families are still outside CP-0 decisioning.",
      source: "current_l5_code_truth_to_spec_gap_latest.json:G043",
      competitiveness_impact: "high",
    },
    {
      id: "G044",
      blocker: "Survivability, valuation, and sector-condition tensors are absent from serving logic.",
      source: "current_l5_code_truth_to_spec_gap_latest.json:G044",
      competitiveness_impact: "high",
    },
    {
      id: "G029",
      blocker: "G32 epoch mosaic and sector coupling rule families are not wired into CP-0 serving logic.",
      source: "current_l5_code_truth_to_spec_gap_latest.json:G029",
      competitiveness_impact: "high",
    },
    {
      id: "RB001",
      blocker: "Setup signal extraction is absent from the current runtime snapshot, so pattern/setup families cannot be activated safely.",
      source: "uf_snapshot.json:rows[*] keys; setup_registry_v1.json",
      competitiveness_impact: "high",
    },
    {
      id: "RB002",
      blocker: "Company-news and catalyst event sources are not present in the current runtime artifacts.",
      source: "information_event_registry_v1.json; uf_snapshot.json:rows[*]",
      competitiveness_impact: "high",
    },
    {
      id: "RB003",
      blocker: "Macro/epoch driver sources are not materialized beyond regime labels in the current runtime artifacts.",
      source: "uf_snapshot.json:rows[*].regime; current_l5_code_truth_to_spec_gap_latest.json:G029",
      competitiveness_impact: "high",
    },
    {
      id: "RB004",
      blocker: "Sphere-of-impact mapping is declared in registries but not wired into runtime decision surfaces.",
      source: "sector_sphere_coupling_registry_v1.json; current_l5_code_truth_to_spec_gap_latest.json:G029",
      competitiveness_impact: "high",
    },
    {
      id: "RB005",
      blocker: "Short-side families are out of scope for current CP-0 activation.",
      source: "strategy_registry_v1.json:short_side_downside_families.applies_to",
      competitiveness_impact: "medium",
    },
    {
      id: "RB006",
      blocker: "Class precedence and family activation wiring are missing across all declared A5 registries.",
      source: "strategy_registry_v1.json; current_l5_code_truth_to_spec_gap_latest.json:G042",
      competitiveness_impact: "high",
    },
  ];

  const implementationOrder = [
    "long_side_accumulation_hold_discipline",
    "valuation_margin_survivability_capital_preservation",
    "insider_ownership_rules",
    "abstention_suppression_degraded_mode",
    "pattern_setup_tactical_overlays",
    "company_news_catalyst_rules",
    "sector_macro_epoch_intelligence",
    "short_side_downside_families",
  ].map((id, index) => {
    const family = familyById[id];
    const runtime = runtimeEligibilityView.find((item) => item.strategy_family_id === id);
    return {
      order: index + 1,
      id,
      name: family?.name ?? id,
      rationale:
        id === "long_side_accumulation_hold_discipline"
          ? "Largest CP-0-relevant eligible population with no missing external event channel and no ranking/allocator change required for initial admin-only wiring."
          : id === "valuation_margin_survivability_capital_preservation"
            ? "Large CP-0-relevant eligible population and required quote profile data is already present in current artifacts."
            : id === "insider_ownership_rules"
              ? "Current quote cache already carries insider/ownership fields, making this the next governed overlay after valuation/survivability."
              : id === "abstention_suppression_degraded_mode"
                ? "Runtime fallback semantics already exist, so explicit registry wiring can tighten semantics without broad behavioral change."
                : id === "pattern_setup_tactical_overlays"
                  ? "Exact coverage is now materially restored, but setup extraction is still missing and must be added before activation."
                  : id === "company_news_catalyst_rules"
                    ? "Requires a new event source and quantification path before safe activation."
                    : id === "sector_macro_epoch_intelligence"
                      ? "Requires macro/epoch source materialization and sphere mapping before safe activation."
                      : "Short-side families remain outside current CP-0 scope and should stay last for this lane.",
      eligible_row_count: runtime?.eligible_row_count ?? 0,
      eligible_pct: runtime?.eligible_pct ?? 0,
    };
  });

  return {
    prioritization_method:
      "Ordered by current CP-0 applicability first, then current eligible row count under the admin quality winner context, then missing dependency count, then risk class. This is a reporting order only, not a production scoring heuristic.",
    top_10_highest_roi_strategy_families_to_populate_next: prioritized.slice(0, 10),
    top_10_blockers_to_competitive_rulebook_depth: blockers,
    recommended_a5_2_implementation_activation_order: implementationOrder,
    explicit_recommendation:
      "Recommended next implementation item after this coverage surface: A5.2 long-side accumulation / hold discipline admin-only wiring, followed by valuation/survivability overlays. Do not activate pattern, company-news, macro, or short-side families before their missing channels are present.",
  };
}

function renderMarkdown(payload) {
  const strategyLines = payload.strategy_family_coverage
    .map((family) => {
      const deps = family.missing_dependencies.map((value) => `\`${value}\``).join(", ");
      return `- \`${family.id}\`: required=${family.required_ladder_level}, scaffold_only=${family.scaffold_only}, implemented=${family.implemented}, active=${family.active}, governance=${family.governance_status}, risk=${family.risk_class}. Missing dependencies: ${deps}`;
    })
    .join("\n");

  const setupLines = payload.setup_family_coverage
    .map((group) => `- \`${group.id}\`: registry=${group.registry_status}, implementation=${group.implementation_status}, activation=${group.activation_status}`)
    .join("\n");

  const eventLines = payload.information_event_epoch_coverage
    .map(
      (entry) =>
        `- \`${entry.id}\`: source=${entry.source_maturity.status}, quantification=${entry.quantification_maturity}, sphere_mapping=${entry.sphere_mapping_maturity}, mode=${entry.advisory_only_vs_decision_governing}`,
    )
    .join("\n");

  const heuristicLines = payload.heuristics_governance_coverage
    .map(
      (entry) =>
        `- \`${entry.id}\`: approved=${entry.approved}, active=${entry.active}, audit_trail_present=${entry.audit_trail_present}, matching_dependency=${entry.dependency_on_exact_vs_relaxed_matching}`,
    )
    .join("\n");

  const runtimeLines = payload.runtime_eligibility_blockage_view
    .map(
      (entry) =>
        `- \`${entry.strategy_family_id}\`: eligible=${entry.eligible_row_count}/${payload.runtime_contexts.eligibility_view_context.total_snapshot_rows} (${entry.eligible_pct.toFixed(3)}%), blocked=${entry.blocked_row_count}, top_blocker=${entry.blocked_reasons[0] ? `${entry.blocked_reasons[0].key} (${entry.blocked_reasons[0].count})` : "none"}`,
    )
    .join("\n");

  const topFamilies = payload.competitive_prioritization_summary.top_10_highest_roi_strategy_families_to_populate_next
    .map((entry, index) => `- ${index + 1}. \`${entry.id}\` eligible=${entry.eligible_row_count} (${Number(entry.eligible_pct).toFixed(3)}%) risk=${entry.risk_class}`)
    .join("\n");

  const blockers = payload.competitive_prioritization_summary.top_10_blockers_to_competitive_rulebook_depth
    .map((entry, index) => `- ${index + 1}. \`${entry.id}\`: ${entry.blocker}`)
    .join("\n");

  const orderLines = payload.competitive_prioritization_summary.recommended_a5_2_implementation_activation_order
    .map((entry) => `- ${entry.order}. \`${entry.id}\`: ${entry.rationale}`)
    .join("\n");

  return [
    "# Admin Rulebook Coverage (Latest)",
    "",
    `Generated (UTC): ${payload.generated_at_utc}`,
    `Status: ${payload.status}`,
    `CP Profile: ${payload.cp_profile}`,
    "",
    "## Runtime Contexts",
    "",
    `- Eligibility view uses admin quality winner context: policy=${payload.runtime_contexts.eligibility_view_context.policy_path}, min_bars=${payload.runtime_contexts.eligibility_view_context.min_bars}, anomaly_fallback_enabled=${payload.runtime_contexts.eligibility_view_context.anomaly_fallback_enabled}`,
    `- Decision provenance context reference: min_bars=${payload.runtime_contexts.decision_provenance_context.decision_provenance_min_bars}, anomaly_fallback_enabled=${payload.runtime_contexts.decision_provenance_context.anomaly_fallback_enabled}`,
    "",
    "## 1. Strategy Family Coverage",
    "",
    strategyLines,
    "",
    "## 2. Setup Family Coverage",
    "",
    setupLines,
    "",
    "## 3. Information-Event / Epoch Coverage",
    "",
    eventLines,
    "",
    "## 4. Heuristics Governance Coverage",
    "",
    heuristicLines,
    "",
    "## 5. Runtime Eligibility / Blockage View",
    "",
    runtimeLines,
    "",
    "## 6. Competitive Prioritization Summary",
    "",
    "### Highest-ROI Families",
    "",
    topFamilies,
    "",
    "### Top Blockers",
    "",
    blockers,
    "",
    "### Recommended A5.2 Order",
    "",
    orderLines,
    "",
    `Recommended next implementation item: ${payload.competitive_prioritization_summary.explicit_recommendation}`,
    "",
  ].join("\n");
}

function main() {
  const root = resolveWorkspaceRoot();
  const snapshotPath = path.join(root, "uf_snapshot.json");
  const quotePath = path.join(root, "web", "data", "screener-quote-cache.json");
  const qualityPath = path.join(root, "web", "data", "recommendation-quality-latest.json");
  const strategyPath = path.join(root, "strategy_registry_v1.json");
  const setupPath = path.join(root, "setup_registry_v1.json");
  const infoPath = path.join(root, "information_event_registry_v1.json");
  const sectorPath = path.join(root, "sector_sphere_coupling_registry_v1.json");
  const heuristicsPath = path.join(root, "heuristics_registry_v1.json");
  const runtimeFallbackPath = path.join(root, "runtime_fallback_semantics_latest.json");
  const adminFallbackPath = path.join(root, "admin_quality_fallback_breakdown_latest.json");
  const provenancePath = path.join(root, "current_l5_provenance_persistence_latest.json");
  const gapPath = path.join(root, "current_l5_code_truth_to_spec_gap_latest.json");
  const outJsonPath = path.join(root, "admin_rulebook_coverage_latest.json");
  const outMdPath = path.join(root, "admin_rulebook_coverage_latest.md");

  const snapshotRows = parseSnapshotRows(snapshotPath);
  const quoteRows = parseQuoteRows(quotePath);
  const qualitySummary = readJson(qualityPath);
  const strategyRegistry = readJson(strategyPath);
  const setupRegistry = readJson(setupPath);
  const infoRegistry = readJson(infoPath);
  const sectorRegistry = readJson(sectorPath);
  const heuristicsRegistry = readJson(heuristicsPath);
  const runtimeFallback = readJson(runtimeFallbackPath);
  const adminFallback = readJson(adminFallbackPath);
  const provenance = readJson(provenancePath);
  const gapPayload = readJson(gapPath);
  const policyRuntime = loadPolicyRuntimeArtifact(root);

  const winner = qualitySummary?.winner ?? {};
  const qualityContext = adminFallback?.quality_winner_context ?? {};
  const minBars = Number.isFinite(Number(qualityContext.winner_min_bars))
    ? Math.trunc(Number(qualityContext.winner_min_bars))
    : Math.trunc(Number(winner.min_bars ?? 252));
  const anomalyFallbackEnabled = qualityContext.anomaly_fallback_enabled === true;

  const rowContexts = buildRowContexts(snapshotRows, quoteRows, policyRuntime, minBars, anomalyFallbackEnabled);
  const ladderSummary = summarizeLadder(rowContexts);
  const adminCoverageSummary = adminFallback?.coverage_summary ?? {};
  const expectedExact = Number(adminCoverageSummary.exact_structural_coverage_pct ?? 0);
  const expectedRelaxed = Number(adminCoverageSummary.relaxed_structural_coverage_pct ?? 0);
  const expectedSafe = Number(adminCoverageSummary.safe_policy_fallback_pct ?? 0);
  const expectedDegraded = Number(adminCoverageSummary.degraded_unmapped_pct ?? 0);
  const expectedUnavailable = Number(adminCoverageSummary.unavailable_or_blocked_pct ?? 0);
  const parity = {
    exact_pct_match: Math.abs(ladderSummary.L0_EXACT_STRUCTURAL_MATCH.pct - expectedExact) < 0.000001,
    relaxed_pct_match: Math.abs(ladderSummary.L1_RELAXED_STRUCTURAL_MATCH.pct - expectedRelaxed) < 0.000001,
    safe_pct_match: Math.abs(ladderSummary.L2_SAFE_POLICY_FALLBACK.pct - expectedSafe) < 0.000001,
    degraded_pct_match: Math.abs(ladderSummary.L3_DEGRADED_UNMAPPED.pct - expectedDegraded) < 0.000001,
    unavailable_pct_match: Math.abs(ladderSummary.L4_UNAVAILABLE_OR_BLOCKED.pct - expectedUnavailable) < 0.000001,
  };
  if (!Object.values(parity).every(Boolean)) {
    throw new Error(`Admin fallback coverage parity mismatch: ${JSON.stringify(parity)}`);
  }

  const gapItems = [];
  (function collectGapItems(value) {
    if (Array.isArray(value)) {
      for (const item of value) collectGapItems(item);
      return;
    }
    if (!value || typeof value !== "object") return;
    if (typeof value.id === "string" && typeof value.area === "string") {
      gapItems.push(value);
    }
    for (const nested of Object.values(value)) collectGapItems(nested);
  })(gapPayload);

  const strategyFamilies = Array.isArray(strategyRegistry.strategy_families) ? strategyRegistry.strategy_families : [];
  const setupFamilies = Array.isArray(setupRegistry.setup_families) ? setupRegistry.setup_families : [];
  const infoFamilies = Array.isArray(infoRegistry.informational_events) ? infoRegistry.informational_events : [];
  const sectorCouplings = Array.isArray(sectorRegistry.couplings) ? sectorRegistry.couplings : [];

  const { familyCoverage, runtimeView } = buildStrategyFamilyCoverage(strategyFamilies, rowContexts, gapItems);
  const setupCoverage = buildSetupCoverage(setupFamilies, familyCoverage);
  const infoCoverage = buildInformationEventCoverage(infoFamilies, sectorCouplings, rowContexts);
  const heuristicsCoverage = buildHeuristicsGovernanceCoverage(heuristicsRegistry);
  const prioritization = buildPrioritizationSummary(familyCoverage, runtimeView);

  const payload = {
    analysis_name: "A5_admin_rulebook_coverage",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    lineage_baseline: "Section 9 strict lineage baseline for L5 revisions remains in force.",
    source_truth: [
      "strategy_registry_v1.json",
      "setup_registry_v1.json",
      "information_event_registry_v1.json",
      "sector_sphere_coupling_registry_v1.json",
      "heuristics_registry_v1.json",
      "uf_snapshot.json",
      "web/data/screener-quote-cache.json",
      "web/data/recommendation-quality-latest.json",
      "runtime_fallback_semantics_latest.json",
      "admin_quality_fallback_breakdown_latest.json",
      "current_l5_provenance_persistence_latest.json",
      "current_l5_code_truth_to_spec_gap_latest.json",
    ],
    scope: "Admin/internal visibility only. No strategy-family behavior activation, no ranking change, and no allocator change.",
    runtime_contexts: {
      eligibility_view_context: {
        context_name: "admin_quality_winner_context",
        policy_path: String(qualityContext.winner_policy_path ?? winner.policy_path ?? policyRuntime.source_path ?? ""),
        policy_variant_name: String(qualityContext.winner_variant_name ?? winner.variant_name ?? ""),
        min_bars: minBars,
        anomaly_fallback_enabled: anomalyFallbackEnabled,
        total_snapshot_rows: rowContexts.length,
        quality_contract: String(qualityContext.quality_contract ?? ""),
      },
      decision_provenance_context: runtimeFallback.source_context ?? null,
      provenance_summary: {
        run_id: provenance.run_id ?? null,
        runtime_decision_row_count: provenance.runtime_decision_row_count ?? null,
        provenance_row_count: provenance.provenance_row_count ?? null,
        completeness_rate: provenance.completeness_rate ?? null,
      },
      parity_to_current_admin_fallback_artifact: parity,
      note:
        "Eligibility counts are computed in the current admin quality winner context because this is an admin/internal surface. Decision-provenance context is included separately for auditability.",
    },
    methodology: {
      eligibility_definition:
        "Eligible means the row satisfies the family's declared typed-fallback gate under the current admin quality winner context and all currently materialized runtime data channels required for later activation are present. This is not strategy activation.",
      non_goals: [
        "No strategy-family behavior activation.",
        "No recommendation ranking change.",
        "No allocator semantics change.",
        "No refresh, oracle, or L5 learning cycle.",
      ],
      missing_dependency_policy:
        "If a required family-specific channel is absent from current runtime artifacts, the row remains blocked even if its ladder level would otherwise qualify.",
    },
    strategy_family_coverage: familyCoverage,
    setup_family_coverage: setupCoverage,
    information_event_epoch_coverage: infoCoverage,
    heuristics_governance_coverage: heuristicsCoverage,
    runtime_eligibility_blockage_view: runtimeView,
    competitive_prioritization_summary: prioritization,
  };

  writeJson(outJsonPath, payload);
  writeText(outMdPath, renderMarkdown(payload));

  process.stdout.write(
    `${JSON.stringify({ status: "ok", output_json: outJsonPath, output_md: outMdPath, rows_evaluated: rowContexts.length })}\n`,
  );
}

main();
