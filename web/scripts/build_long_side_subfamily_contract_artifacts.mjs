#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { PROVENANCE_REQUIRED_NON_NULL_FIELDS } from "./runtime_decision_provenance.mjs";

const ROOT_FALLBACK = "/workspaces/Tao_Financial_Engine";
const READY_SUBFAMILIES = ["accumulation_core", "hold_discipline_core", "hold_only_no_add_discipline"];
const BLOCKED_SUBFAMILIES = [
  "valuation_protected_accumulation",
  "survivability_capital_preservation_protected_accumulation",
  "margin_quality_discipline",
  "recency_sensitive_accumulation",
  "epoch_assisted_accumulation",
];
const CONTRACT_PROOF_FIELDS = [
  "run_id",
  "ticker",
  "snapshot_row_digest_sha256",
  "decision_timestamp_utc",
  "policy_artifact_id",
  "policy_artifact_hash_sha256",
  "candidate_key_chain_json",
  "matched_key",
  "match_level",
  "fallback_ladder_level",
  "matched_exact_bool",
  "decision",
  "decision_reason_code",
  "fallback_reason_code",
  "anomaly_flags_used_json",
  "structural_recency_components_used_json",
  "epoch_components_used_json",
  "coverage_class",
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

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf-8"));
}

function writeJson(filePath, payload) {
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

function writeText(filePath, text) {
  writeFileSync(filePath, `${String(text ?? "").replace(/\s+$/u, "")}\n`, "utf-8");
}

function pct(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function stringOrNull(value) {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text : null;
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

function sortedEntries(values) {
  return [...values].sort((a, b) => String(a).localeCompare(String(b)));
}

function expectedSourceForBlockedSubfamily(id) {
  if (id === "valuation_protected_accumulation") {
    return {
      expected_source: "Quote-cache valuation fields in web/data/screener-quote-cache.json",
      source_system_owner: "quote_cache_pipeline",
      source_system_owner_paths: [
        "web/scripts/get_history_json.py:24",
        "web/scripts/get_history_json.py:903",
        "web/scripts/get_history_json.py:1037",
        "web/scripts/build_screener_quote_cache.py:20",
        "web/scripts/build_screener_quote_cache.py:528",
        "web/data/screener-quote-cache.json",
      ],
      block_types: ["source unavailable", "contract undefined"],
    };
  }

  if (id === "survivability_capital_preservation_protected_accumulation") {
    return {
      expected_source: "Quote-cache survivability and capital-preservation fields in web/data/screener-quote-cache.json",
      source_system_owner: "quote_cache_pipeline",
      source_system_owner_paths: [
        "web/scripts/get_history_json.py:24",
        "web/scripts/get_history_json.py:880",
        "web/scripts/get_history_json.py:916",
        "web/scripts/get_history_json.py:1047",
        "web/scripts/build_screener_quote_cache.py:20",
        "web/data/screener-quote-cache.json",
      ],
      block_types: ["source unavailable", "contract undefined"],
    };
  }

  if (id === "margin_quality_discipline") {
    return {
      expected_source: "Quote-cache margin and quality fields in web/data/screener-quote-cache.json",
      source_system_owner: "quote_cache_pipeline",
      source_system_owner_paths: [
        "web/scripts/get_history_json.py:24",
        "web/scripts/get_history_json.py:929",
        "web/scripts/get_history_json.py:1060",
        "web/scripts/build_screener_quote_cache.py:20",
        "web/data/screener-quote-cache.json",
      ],
      block_types: ["source unavailable", "contract undefined"],
    };
  }

  if (id === "recency_sensitive_accumulation") {
    return {
      expected_source: "Structural recency fields embedded in uf_snapshot row payloads",
      source_system_owner: "uf_snapshot_builder",
      source_system_owner_paths: [
        "uf_mdg_snapshot.py:202",
        "uf_mdg_snapshot.py:228",
        "rebuild_uf_snapshot.py:54",
        "rebuild_uf_snapshot.py:699",
        "runtime_decision_provenance.mjs:378",
        "uf_snapshot.json",
      ],
      block_types: ["schema missing", "contract undefined"],
    };
  }

  if (id === "epoch_assisted_accumulation") {
    return {
      expected_source: "Epoch fields embedded in uf_snapshot row payloads",
      source_system_owner: "uf_snapshot_builder",
      source_system_owner_paths: [
        "uf_mdg_snapshot.py:202",
        "uf_mdg_snapshot.py:228",
        "rebuild_uf_snapshot.py:54",
        "rebuild_uf_snapshot.py:699",
        "runtime_decision_provenance.mjs:397",
        "uf_snapshot.json",
      ],
      block_types: ["schema missing", "contract undefined"],
    };
  }

  throw new Error(`No expected source mapping for blocked subfamily: ${id}`);
}

function hierarchyArtifact({ decomp, readyLookup, strategyLookup, totalSnapshotRows }) {
  const holdOnly = readyLookup.hold_only_no_add_discipline;
  const holdDiscipline = readyLookup.hold_discipline_core;
  const accumulation = readyLookup.accumulation_core;
  const avoidInsideLongSide = holdDiscipline.eligible_row_count - holdOnly.eligible_row_count;

  return {
    analysis_name: "A5_3_long_side_subfamily_hierarchy",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    parent_family: "long_side_accumulation_hold_discipline",
    clarifications: {
      long_side_base_means_candidate_context_not_action: true,
      long_side_base_definition:
        "Long-side base means the current CP-0 candidate context for the long-side family under the admin winner contract: structurally covered rows (L0/L1) with runtime quote support. It is not an automatic long-side action.",
      why_avoid_can_appear_inside_long_side_base:
        "Avoid can appear inside the long-side base because current CP-0 has no active short-side family. In this lane, Avoid is a protective no-add / avoidance output emitted under structurally covered long-side context, not a short-entry instruction.",
      hold_only_is_subset_of_hold_discipline_core: true,
      hold_only_subset_explanation:
        "hold_only_no_add_discipline is the strict Hold-only subset of hold_discipline_core. hold_discipline_core includes both Hold and Avoid outcomes; hold_only excludes Avoid.",
    },
    counts: {
      total_snapshot_rows: totalSnapshotRows,
      long_side_base_row_count: decomp.context.long_side_family_eligible_row_count,
      long_side_base_pct_of_total_snapshot: decomp.context.long_side_family_eligible_pct_of_total_snapshot,
      accumulation_core_row_count: accumulation.eligible_row_count,
      hold_discipline_core_row_count: holdDiscipline.eligible_row_count,
      hold_only_no_add_discipline_row_count: holdOnly.eligible_row_count,
      protective_avoid_within_long_side_base_row_count: avoidInsideLongSide,
      accumulation_plus_hold_discipline_equals_base:
        accumulation.eligible_row_count + holdDiscipline.eligible_row_count === decomp.context.long_side_family_eligible_row_count,
    },
    nodes: [
      {
        id: "long_side_accumulation_hold_discipline",
        label: strategyLookup.long_side_accumulation_hold_discipline?.name ?? "Long-Side Accumulation / Hold Discipline",
        node_type: "parent_family",
      },
      {
        id: "long_side_base_candidate_context",
        label: "Long-Side Base Candidate Context",
        node_type: "candidate_context",
        row_count: decomp.context.long_side_family_eligible_row_count,
        pct_of_total_snapshot: decomp.context.long_side_family_eligible_pct_of_total_snapshot,
      },
      {
        id: "accumulation_core",
        label: accumulation.label,
        node_type: "ready_subfamily",
        row_count: accumulation.eligible_row_count,
      },
      {
        id: "hold_discipline_core",
        label: holdDiscipline.label,
        node_type: "ready_subfamily",
        row_count: holdDiscipline.eligible_row_count,
      },
      {
        id: "hold_only_no_add_discipline",
        label: holdOnly.label,
        node_type: "ready_subset_subfamily",
        row_count: holdOnly.eligible_row_count,
      },
      {
        id: "protective_avoid_inside_long_side_base",
        label: "Protective Avoid Inside Long-Side Base",
        node_type: "residual_state_not_contractized_in_a5_3",
        row_count: avoidInsideLongSide,
      },
    ],
    relationships: [
      {
        type: "family_to_context",
        parent: "long_side_accumulation_hold_discipline",
        child: "long_side_base_candidate_context",
      },
      {
        type: "context_partition",
        parent: "long_side_base_candidate_context",
        children: ["accumulation_core", "hold_discipline_core"],
      },
      {
        type: "subset",
        parent: "hold_discipline_core",
        child: "hold_only_no_add_discipline",
      },
      {
        type: "residual_within_parent",
        parent: "hold_discipline_core",
        residual_child: "protective_avoid_inside_long_side_base",
      },
    ],
  };
}

function contractArtifact({ readyLookup, hierarchy, strategyLookup }) {
  const parentFamily = strategyLookup.long_side_accumulation_hold_discipline;
  const readyContracts = READY_SUBFAMILIES.map((id) => {
    const subfamily = readyLookup[id];
    const isHoldOnly = id === "hold_only_no_add_discipline";
    const isHoldDiscipline = id === "hold_discipline_core";
    const isAccumulation = id === "accumulation_core";

    const purpose = isAccumulation
      ? "Define the governed accumulation branch inside the current long-side base without changing ranking or allocator semantics."
      : isHoldDiscipline
        ? "Define the governed no-add / protective discipline branch inside the current long-side base, including both Hold and Avoid outcomes."
        : "Define the strict Hold-only / no-add subset inside hold_discipline_core. It excludes Avoid outcomes.";

    const triggerConditions = isAccumulation
      ? [
          "long_side_base_candidate_context == true",
          "decision_reason_code == PSCF_POLICY_DECISION",
          "decision == Accumulate",
          "fallback_ladder_level in {L0_EXACT_STRUCTURAL_MATCH, L1_RELAXED_STRUCTURAL_MATCH}",
        ]
      : isHoldDiscipline
        ? [
            "long_side_base_candidate_context == true",
            "decision_reason_code == PSCF_POLICY_DECISION",
            "decision in {Hold, Avoid}",
            "fallback_ladder_level in {L0_EXACT_STRUCTURAL_MATCH, L1_RELAXED_STRUCTURAL_MATCH}",
          ]
        : [
            "hold_discipline_core == true",
            "decision == Hold",
            "fallback_ladder_level in {L0_EXACT_STRUCTURAL_MATCH, L1_RELAXED_STRUCTURAL_MATCH}",
          ];

    const outputSemantics = isAccumulation
      ? [
          "Classify the row as an accumulation-core candidate in admin/internal surfaces.",
          "Do not interpret this class as an automatic add, order, or allocator override.",
          "Current production output remains whatever the existing recommendations and portfolio routes already emit.",
        ]
      : isHoldDiscipline
        ? [
            "Classify the row as a long-side hold-discipline candidate in admin/internal surfaces.",
            "This branch explicitly includes both Hold and Avoid outcomes under structural coverage.",
            "Avoid here means protective no-add / avoidance inside the long-side family, not a short-entry family.",
          ]
        : [
            "Classify the row as a strict Hold-only / no-add candidate in admin/internal surfaces.",
            "This branch is narrower than hold_discipline_core because it excludes Avoid outcomes.",
            "No portfolio rebalance or ranking change is implied.",
          ];

    const overrideSuppressionConditions = [
      "fallback_ladder_level in {L2_SAFE_POLICY_FALLBACK, L3_DEGRADED_UNMAPPED, L4_UNAVAILABLE_OR_BLOCKED} => contract suppressed",
      "serving freshness stale or recommendation-quality degraded state remains orthogonal and can suppress downstream exposure without changing contract membership",
      "anomaly fallback rows are excluded because in the current admin winner context they migrate to L2 and therefore leave the long-side base",
    ];

    const hierarchyPosition = isAccumulation
      ? {
          parent_family: "long_side_accumulation_hold_discipline",
          subset_of: [],
          sibling_of: ["hold_discipline_core"],
        }
      : isHoldDiscipline
        ? {
            parent_family: "long_side_accumulation_hold_discipline",
            subset_of: [],
            sibling_of: ["accumulation_core"],
          }
        : {
            parent_family: "long_side_accumulation_hold_discipline",
            subset_of: ["hold_discipline_core"],
            sibling_of: [],
          };

    const explanationProofFields = CONTRACT_PROOF_FIELDS.filter(
      (field) => PROVENANCE_REQUIRED_NON_NULL_FIELDS.includes(field) || field === "matched_key" || field === "fallback_reason_code",
    );

    return {
      id,
      label: subfamily.label,
      parent_family: "long_side_accumulation_hold_discipline",
      hierarchy_position: hierarchyPosition,
      purpose,
      trigger_conditions: triggerConditions,
      required_fields: ["ticker", "asset_type", "bar_count", "regime", "decision", "decision_reason_code", "fallback_ladder_level"],
      required_ladder_levels: ["L0_EXACT_STRUCTURAL_MATCH", "L1_RELAXED_STRUCTURAL_MATCH"],
      exact_required_vs_relaxed_allowed: subfamily.exact_required_vs_relaxed_allowed,
      output_semantics: outputSemantics,
      override_suppression_conditions: overrideSuppressionConditions,
      explanation_proof_fields: explanationProofFields,
      governance_status: subfamily.governance_status,
      activation_readiness: subfamily.activation_readiness,
      current_observed_population: {
        eligible_row_count: subfamily.eligible_row_count,
        eligible_pct_of_long_side_base: subfamily.eligible_pct_of_base_population,
        eligible_pct_of_total_snapshot: subfamily.eligible_pct_of_total_snapshot,
        current_ladder_distribution: subfamily.current_ladder_distribution,
        blocked_reasons: subfamily.blocked_reasons,
      },
      evidence_paths: [
        "long_side_rulebook_decomposition_latest.json",
        "admin_rulebook_coverage_latest.json",
        "runtime_provenance_schema_latest.md",
        "web/scripts/runtime_decision_provenance.mjs",
        ...(Array.isArray(parentFamily?.source_refs) ? parentFamily.source_refs : []),
      ],
    };
  });

  return {
    analysis_name: "A5_3_long_side_subfamily_contracts",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    lineage_baseline: "Section 9 strict lineage baseline for L5 revisions remains in force.",
    source_truth: [
      "long_side_rulebook_decomposition_latest.json",
      "admin_rulebook_coverage_latest.json",
      "strategy_registry_v1.json",
      "runtime_provenance_schema_latest.md",
      "web/scripts/runtime_decision_provenance.mjs",
      "web/src/app/api/recommendations/list/route.ts",
    ],
    scope: "Governed contractization only. No strategy-family production activation, no ranking change, and no allocator change.",
    parent_family_context: {
      id: "long_side_accumulation_hold_discipline",
      label: parentFamily?.name ?? "Long-Side Accumulation / Hold Discipline",
      doctrine: parentFamily?.doctrine ?? [],
      long_side_base_candidate_context: hierarchy.clarifications.long_side_base_definition,
      why_avoid_can_appear_inside_long_side_base: hierarchy.clarifications.why_avoid_can_appear_inside_long_side_base,
    },
    contracts: readyContracts,
  };
}

function blockedMatrixArtifact({ blockedLookup }) {
  const matrix = BLOCKED_SUBFAMILIES.map((id) => {
    const blocked = blockedLookup[id];
    const source = expectedSourceForBlockedSubfamily(id);
    const missingFields = Array.isArray(blocked.missing_field_counts_when_relevant)
      ? blocked.missing_field_counts_when_relevant.map((field) => ({
          field: field.key,
          blocked_row_count: field.count,
          blocked_row_pct_of_base_population: field.pct,
          expected_source: source.expected_source,
          source_system_owner: source.source_system_owner,
          source_system_owner_paths: source.source_system_owner_paths,
          block_types: source.block_types.filter((type) => type !== "contract undefined"),
        }))
      : [];

    const sourceDependency = missingFields.length > 0
      ? missingFields
      : [
          {
            dependency: `${id}_source_fields`,
            missing_fields: blocked.data_contract?.required_fields ?? [],
            expected_source: source.expected_source,
            source_system_owner: source.source_system_owner,
            source_system_owner_paths: source.source_system_owner_paths,
            block_types: source.block_types.filter((type) => type !== "contract undefined"),
          },
        ];

    const contractGap = {
      dependency: `${id}_governed_contract_thresholds_or_activation_rules`,
      missing_fields: [],
      expected_source: `Future A5.4 contract artifact for ${id}`,
      source_system_owner: null,
      source_system_owner_paths: [],
      block_types: ["contract undefined"],
    };

    return {
      id,
      label: blocked.label,
      parent_family: "long_side_accumulation_hold_discipline",
      base_population_row_count: blocked.base_population_row_count,
      eligible_row_count: blocked.eligible_row_count,
      eligible_pct_of_base_population: blocked.eligible_pct_of_base_population,
      primary_block_reason: blocked.blocked_reasons[0] ?? null,
      dependencies: [...sourceDependency, contractGap],
      evidence_paths: [
        "long_side_rulebook_decomposition_latest.json",
        ...source.source_system_owner_paths,
      ],
    };
  });

  return {
    analysis_name: "A5_3_long_side_subfamily_blocked_dependency_matrix",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    matrix,
  };
}

function readinessArtifact({ hierarchy, contracts, blockedMatrix }) {
  const readyContracts = contracts.contracts.map((contract) => ({
    id: contract.id,
    label: contract.label,
    governance_status: contract.governance_status,
    activation_readiness: contract.activation_readiness,
    eligible_row_count: contract.current_observed_population.eligible_row_count,
    eligible_pct_of_long_side_base: contract.current_observed_population.eligible_pct_of_long_side_base,
    exact_required_vs_relaxed_allowed: contract.exact_required_vs_relaxed_allowed,
    top_blocked_reason: contract.current_observed_population.blocked_reasons[0] ?? null,
  }));

    const blockedFamilies = blockedMatrix.matrix.map((entry) => ({
      id: entry.id,
      label: entry.label,
      primary_block_reason: entry.primary_block_reason,
      block_type_summary: sortedEntries(new Set(entry.dependencies.flatMap((dep) => dep.block_types))),
      owner_path_summary: sortedEntries(new Set(entry.dependencies.flatMap((dep) => dep.source_system_owner_paths))),
    }));

  return {
    analysis_name: "A5_3_long_side_subfamily_activation_readiness",
    generated_at_utc: new Date().toISOString(),
    status: "admin_internal_visibility_only",
    cp_profile: "CP-0",
    hierarchy_checks: {
      hold_only_is_subset_of_hold_discipline_core: hierarchy.clarifications.hold_only_is_subset_of_hold_discipline_core,
      long_side_base_is_candidate_context_not_action: hierarchy.clarifications.long_side_base_means_candidate_context_not_action,
      avoid_inside_long_side_base_explained: true,
    },
    ready_contracts: readyContracts,
    blocked_families: blockedFamilies,
    safe_scope_checks: {
      production_behavior_activation: false,
      ranking_changes: false,
      allocator_changes: false,
      refresh_or_oracle_or_learning_run: false,
    },
    recommendation: {
      recommended_option: "A5.4 field/event contracts for blocked families",
      rationale:
        "A5.3 has now made the ready long-side subfamilies explicit and governed without changing behavior. The highest remaining ROI is to define field/event contracts for the blocked long-side protection families and the zero-coverage external families, because those are now the clearest gating constraints.",
      why_not_a6_first:
        "Promotion-gate upgrades should follow the missing field and event contracts; otherwise the gates would formalize gaps that are still undefined at the source-contract level.",
      why_not_a7_first:
        "Proof-plane upgrades are higher value after the blocked field/event contracts exist, so the proof surfaces can distinguish unavailable source channels from merely inactive contracts.",
    },
  };
}

function renderMarkdown({ hierarchy, contracts, blockedMatrix, readiness }) {
  const contractLines = contracts.contracts
    .map((contract) => {
      return [
        `### ${contract.label}`,
        `- Parent family: \`${contract.parent_family}\``,
        `- Purpose: ${contract.purpose}`,
        `- Trigger conditions: ${contract.trigger_conditions.join("; ")}`,
        `- Required fields: ${contract.required_fields.map((field) => `\`${field}\``).join(", ")}`,
        `- Required ladder levels: ${contract.required_ladder_levels.map((level) => `\`${level}\``).join(", ")}`,
        `- Exact required vs relaxed allowed: exact_required=${contract.exact_required_vs_relaxed_allowed.exact_required} relaxed_allowed=${contract.exact_required_vs_relaxed_allowed.relaxed_allowed}`,
        `- Output semantics: ${contract.output_semantics.join(" ")}`,
        `- Override/suppression: ${contract.override_suppression_conditions.join(" ")}`,
        `- Governance status: ${contract.governance_status}`,
        `- Activation readiness: ${contract.activation_readiness}`,
        `- Current observed population: ${contract.current_observed_population.eligible_row_count} rows (${contract.current_observed_population.eligible_pct_of_long_side_base.toFixed(6)}% of long-side base)`,
      ].join("\n");
    })
    .join("\n\n");

  const blockedLines = blockedMatrix.matrix
    .map((entry) => {
      const topDep = entry.dependencies[0];
      return `- \`${entry.id}\`: primary_block=${entry.primary_block_reason?.key ?? "none"}; first dependency source=${topDep?.expected_source ?? "n/a"}; block_types=${topDep?.block_types?.join(", ") ?? "n/a"}`;
    })
    .join("\n");

  return [
    "# Long-Side Subfamily Contracts (Latest)",
    "",
    `Generated (UTC): ${contracts.generated_at_utc}`,
    `Status: ${contracts.status}`,
    `CP Profile: ${contracts.cp_profile}`,
    "",
    "## Hierarchy Clarifications",
    "",
    `- Long-side base is candidate context, not action: ${hierarchy.clarifications.long_side_base_definition}`,
    `- Hold-only subset of hold-discipline core: ${hierarchy.clarifications.hold_only_subset_explanation}`,
    `- Why Avoid can appear inside long-side base: ${hierarchy.clarifications.why_avoid_can_appear_inside_long_side_base}`,
    "",
    "## Ready Subfamily Contracts",
    "",
    contractLines,
    "",
    "## Blocked Dependency Summary",
    "",
    blockedLines,
    "",
    "## Recommendation",
    "",
    `- Recommended next step: ${readiness.recommendation.recommended_option}`,
    `- Rationale: ${readiness.recommendation.rationale}`,
    "",
  ].join("\n");
}

function main() {
  const root = resolveWorkspaceRoot();
  const decompPath = path.join(root, "long_side_rulebook_decomposition_latest.json");
  const adminCoveragePath = path.join(root, "admin_rulebook_coverage_latest.json");
  const strategyPath = path.join(root, "strategy_registry_v1.json");

  const contractsJsonPath = path.join(root, "long_side_subfamily_contracts_latest.json");
  const contractsMdPath = path.join(root, "long_side_subfamily_contracts_latest.md");
  const hierarchyJsonPath = path.join(root, "long_side_subfamily_hierarchy_latest.json");
  const blockedMatrixJsonPath = path.join(root, "long_side_subfamily_blocked_dependency_matrix_latest.json");
  const readinessJsonPath = path.join(root, "long_side_subfamily_activation_readiness_latest.json");

  const decomp = readJson(decompPath);
  const adminCoverage = readJson(adminCoveragePath);
  const strategyRegistry = readJson(strategyPath);

  const subfamilyLookup = arrayToLookup(decomp.subfamilies);
  const readyLookup = {};
  for (const id of READY_SUBFAMILIES) readyLookup[id] = subfamilyLookup[id];
  const blockedLookup = {};
  for (const id of BLOCKED_SUBFAMILIES) blockedLookup[id] = subfamilyLookup[id];

  const strategyCoverageLookup = arrayToLookup(adminCoverage.strategy_family_coverage);

  const accumulation = readyLookup.accumulation_core;
  const holdDiscipline = readyLookup.hold_discipline_core;
  const holdOnly = readyLookup.hold_only_no_add_discipline;
  if (holdOnly.eligible_row_count > holdDiscipline.eligible_row_count) {
    throw new Error("hold_only_no_add_discipline cannot exceed hold_discipline_core");
  }
  if (accumulation.eligible_row_count + holdDiscipline.eligible_row_count !== decomp.context.long_side_family_eligible_row_count) {
    throw new Error("accumulation_core plus hold_discipline_core must partition the long-side base");
  }

  const hierarchy = hierarchyArtifact({
    decomp,
    readyLookup,
    strategyLookup: strategyCoverageLookup,
    totalSnapshotRows: adminCoverage.runtime_contexts.eligibility_view_context.total_snapshot_rows,
  });
  const contracts = contractArtifact({
    readyLookup,
    hierarchy,
    strategyLookup: strategyCoverageLookup,
  });
  const blockedMatrix = blockedMatrixArtifact({
    blockedLookup,
  });
  const readiness = readinessArtifact({
    hierarchy,
    contracts,
    blockedMatrix,
  });

  writeJson(contractsJsonPath, contracts);
  writeText(contractsMdPath, renderMarkdown({ hierarchy, contracts, blockedMatrix, readiness }));
  writeJson(hierarchyJsonPath, hierarchy);
  writeJson(blockedMatrixJsonPath, blockedMatrix);
  writeJson(readinessJsonPath, readiness);

  process.stdout.write(
    `${JSON.stringify({
      status: "ok",
      contracts_json: contractsJsonPath,
      contracts_md: contractsMdPath,
      hierarchy_json: hierarchyJsonPath,
      blocked_matrix_json: blockedMatrixJsonPath,
      readiness_json: readinessJsonPath,
    })}\n`,
  );
}

main();
