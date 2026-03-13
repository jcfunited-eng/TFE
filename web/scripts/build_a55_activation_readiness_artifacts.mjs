#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const ROOT = '/workspaces/Tao_Financial_Engine';
const GENERATED_AT = new Date().toISOString();

function parseJsonLike(text) {
  return JSON.parse(
    text
      .replace(/\bNaN\b/g, 'null')
      .replace(/\bInfinity\b/g, 'null')
      .replace(/-null/g, 'null')
  );
}

function readJson(filePath) {
  return parseJsonLike(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(filePath, value) {
  fs.writeFileSync(filePath, value, 'utf8');
}

function pct(part, total) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total === 0) return 0;
  return Number(((part / total) * 100).toFixed(6));
}

function extractDirectiveMetric(text, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp('- `' + escaped + '`: flip `([^`]+)`, delta outcome `([^`]+)`, delta excess `([^`]+)`');
  const match = text.match(pattern);
  if (!match) return null;
  return {
    flip_rate: Number(match[1]),
    delta_outcome_over_index_pct: Number(match[2]),
    delta_mean_excess_vs_spy: Number(match[3]),
  };
}

function readObservedRowTraceRegimeMap() {
  const candidates = [
    path.join(ROOT, 'backups/lab/recommendation_lab/current_inputs/real_world_cleaned_universe_l5_row_trace_full.csv'),
    path.join(ROOT, 'backups/lab/recommendation_lab/current_inputs/real_world_cleaned_universe_l5_row_trace_merged_historical.csv'),
    path.join(ROOT, 'backups/lab/recommendation_lab/current_inputs/fresh_temporal_rowtrace_latest.csv'),
  ];
  const existing = candidates.find((filePath) => fs.existsSync(filePath));
  if (!existing) {
    return {
      source_path: null,
      mapping: null,
      status: 'row_trace_not_found',
    };
  }

  const py = [
    'import csv, json, sys',
    'p = sys.argv[1]',
    'seen = {}',
    "with open(p, 'r', encoding='utf-8', newline='') as f:",
    '    reader = csv.DictReader(f)',
    '    for row in reader:',
    "        regime = str(row.get('regime', '') or '').strip()",
    '        if regime and regime not in seen:',
    '            seen[regime] = len(seen)',
    '            if len(seen) >= 12:',
    '                break',
    'print(json.dumps(seen, sort_keys=True))',
  ].join('\n');

  const raw = execFileSync('python3', ['-c', py, existing], { encoding: 'utf8' }).trim();
  return {
    source_path: existing,
    mapping: raw ? JSON.parse(raw) : {},
    status: 'ok',
  };
}

const snapshot = readJson(path.join(ROOT, 'uf_snapshot.json'));
const longSideReadiness = readJson(path.join(ROOT, 'long_side_activation_readiness_latest.json'));
const blockedFamilyReadiness = readJson(path.join(ROOT, 'blocked_family_readiness_latest.json'));
const structuralRecencyRuntimeReadiness = readJson(path.join(ROOT, 'structural_recency_runtime_readiness_latest.json'));
const epochStateRuntimeReadiness = readJson(path.join(ROOT, 'epoch_state_runtime_readiness_latest.json'));
const quoteSourceReadiness = readJson(path.join(ROOT, 'quote_source_readiness_gate_latest.json'));
const quoteFamilyBlockers = readJson(path.join(ROOT, 'quote_family_activation_blockers_latest.json'));
const directiveText = readText(path.join(ROOT, 'LOAD_DIRECTIVE_NEXT_CHAT.md'));

const snapshotRows = Array.isArray(snapshot.rows) ? snapshot.rows : [];
const totalSnapshotRows = snapshotRows.length;
const snapshotGeneratedAt = snapshot.generated_at_utc || null;
const observedSnapshotRegimes = Array.from(new Set(snapshotRows.map((row) => String(row?.regime ?? '').trim()).filter(Boolean))).sort();
const rowTraceRegimeMap = readObservedRowTraceRegimeMap();

const longSideContext = longSideReadiness.long_side_family_context || {};
const accumulationBaseCount = Number(longSideContext.accumulation_row_count || 0);
const blockedRecencyFamily = (blockedFamilyReadiness.families || []).find((item) => item.id === 'recency_sensitive_accumulation') || {};
const blockedEpochFamily = (blockedFamilyReadiness.families || []).find((item) => item.id === 'epoch_assisted_accumulation') || {};

const structuralRecencyRemoved = extractDirectiveMetric(directiveText, 'G_structural_recency_removed');
const regimeCodeRemoved = extractDirectiveMetric(directiveText, 'G_regime_code_removed');
const gapRemoved = extractDirectiveMetric(directiveText, 'G_gap_removed');

const recencyMembers = [
  {
    id: 'steps_since_regime_change',
    derivation_basis: 'timeline.steps_since_regime_change[idx]',
    reset_condition: 'Reset to 0 when current regime differs from prior regime; otherwise increment prior value by 1.',
    initial_condition: 'First row for a symbol timeline is 0.',
    null_condition: 'No null in temporal dataset builder; missing from CP-0 snapshot rows today because the snapshot contract does not materialize it.',
    units: 'history steps',
    lower_bound: 0,
    upper_bound_rule: 'bounded by history_available_steps',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'decision-governing',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Direct member of the current temporal extra-column block and part of the structural-recency signal that materially moves outputs in the epoch decomposition microprobe.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:180',
      'tools/build_temporal_policy_dataset.py:265',
      'tools/eval_temporal_walkforward.py:650',
      'LOAD_DIRECTIVE_NEXT_CHAT.md:205',
    ],
  },
  {
    id: 'steps_since_pattern_change',
    derivation_basis: 'timeline.steps_since_pattern_change[idx]',
    reset_condition: 'Reset to 0 when current pattern_key differs from prior pattern_key; otherwise increment prior value by 1.',
    initial_condition: 'First row for a symbol timeline is 0.',
    null_condition: 'No null in temporal dataset builder; missing from CP-0 snapshot rows today because the snapshot contract does not materialize it.',
    units: 'history steps',
    lower_bound: 0,
    upper_bound_rule: 'bounded by history_available_steps',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'decision-governing',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Direct member of the current temporal extra-column block and needed for recency-sensitive accumulation timing without forcing exact-only coverage.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:181',
      'tools/build_temporal_policy_dataset.py:266',
      'tools/eval_temporal_walkforward.py:651',
      'LOAD_DIRECTIVE_NEXT_CHAT.md:205',
    ],
  },
  {
    id: 'steps_since_reversal_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["R_rev"][idx] when R_rev exists; else -1 sentinel.',
    reset_condition: 'Reset to 0 when R_rev sign flips; otherwise increment since last R_rev sign flip.',
    initial_condition: 'First row is -1 until the first reversal sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 is the sentinel before any reversal flip or when R_rev is absent from the configured state field set.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'decision-governing',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Explicit dedicated reversal-memory feature already admitted into the temporal extra-column block and the strongest direct bridge between recency and current decision flow.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:298',
      'tools/eval_temporal_walkforward.py:652',
      'LOAD_DIRECTIVE_NEXT_CHAT.md:205',
    ],
  },
  {
    id: 'D_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["D"][idx]',
    reset_condition: 'Reset to 0 when D sign flips; otherwise increment since last D sign flip.',
    initial_condition: 'First row is -1 until the first D sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'M_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["M"][idx]',
    reset_condition: 'Reset to 0 when M sign flips; otherwise increment since last M sign flip.',
    initial_condition: 'First row is -1 until the first M sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'R_rev_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["R_rev"][idx]',
    reset_condition: 'Reset to 0 when R_rev sign flips; otherwise increment since last R_rev sign flip.',
    initial_condition: 'First row is -1 until the first R_rev sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'proof-only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Duplicate proof surface for the dedicated canonical alias steps_since_reversal_sign_flip; useful for lineage checks, not needed as a separate CP-0 governance field.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/build_temporal_policy_dataset.py:300',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'U_star_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["U_star"][idx]',
    reset_condition: 'Reset to 0 when U_star sign flips; otherwise increment since last U_star sign flip.',
    initial_condition: 'First row is -1 until the first U_star sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'C_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["C"][idx]',
    reset_condition: 'Reset to 0 when C sign flips; otherwise increment since last C sign flip.',
    initial_condition: 'First row is -1 until the first C sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'P_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["P"][idx]',
    reset_condition: 'Reset to 0 when P sign flips; otherwise increment since last P sign flip.',
    initial_condition: 'First row is -1 until the first P sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'B_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["B"][idx]',
    reset_condition: 'Reset to 0 when B sign flips; otherwise increment since last B sign flip.',
    initial_condition: 'First row is -1 until the first B sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'S_UF_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["S_UF"][idx]',
    reset_condition: 'Reset to 0 when S_UF sign flips; otherwise increment since last S_UF sign flip.',
    initial_condition: 'First row is -1 until the first S_UF sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
  {
    id: 'R_UF_steps_since_sign_flip',
    derivation_basis: 'timeline.steps_since_sign_flip_by_field["R_UF"][idx]',
    reset_condition: 'Reset to 0 when R_UF sign flips; otherwise increment since last R_UF sign flip.',
    initial_condition: 'First row is -1 until the first R_UF sign flip occurs.',
    null_condition: 'No null in temporal dataset builder; -1 sentinel before the first sign flip.',
    units: 'history steps',
    lower_bound: -1,
    upper_bound_rule: 'bounded by history_available_steps after the first flip',
    version_introduced: 'structural_recency_schema_version v1',
    runtime_exposure_class: 'admin/internal only',
    ladder_level_requirement: 'allow_L1_relaxed',
    activation_rationale: 'Available in temporal tooling but not required for the initial CP-0 recency-assisted family admission path.',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:277',
      'tools/eval_temporal_walkforward.py:677',
    ],
  },
];

const structuralRecencyRegistry = {
  analysis_name: 'A5_5R_structural_recency_member_registry',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_readiness_only',
  cp_profile: 'CP-0',
  registry_version: 'structural_recency_schema_version_v1',
  family_id: 'recency_sensitive_accumulation',
  required_ladder_level: 'allow_L1_relaxed',
  current_snapshot_state: {
    generated_at_utc: snapshotGeneratedAt,
    total_snapshot_rows: totalSnapshotRows,
    rows_with_steps_since_namespace: structuralRecencyRuntimeReadiness.current_snapshot_state?.rows_with_steps_since_namespace ?? 0,
    rows_with_structural_recency_schema_version: structuralRecencyRuntimeReadiness.current_snapshot_state?.rows_with_structural_recency_schema_version ?? 0,
    current_eligible_row_count: blockedRecencyFamily.current_status?.eligible_row_count ?? 0,
    blocked_base_population_row_count: blockedRecencyFamily.current_status?.base_population_row_count ?? accumulationBaseCount,
  },
  code_truth_basis: {
    default_state_fields: ['D', 'M', 'R_rev', 'U_star', 'C', 'P', 'B', 'S_UF', 'R_UF'],
    adjacent_non_member_controls: ['history_available_steps', 'ts_gap_days_from_prev'],
    microprobe_context: {
      structural_recency_removed: structuralRecencyRemoved,
      regime_code_removed: regimeCodeRemoved,
      gap_removed: gapRemoved,
    },
  },
  members: recencyMembers,
  classification_summary: {
    decision_governing_count: recencyMembers.filter((item) => item.runtime_exposure_class === 'decision-governing').length,
    proof_only_count: recencyMembers.filter((item) => item.runtime_exposure_class === 'proof-only').length,
    admin_internal_only_count: recencyMembers.filter((item) => item.runtime_exposure_class === 'admin/internal only').length,
  },
  evidence_paths: [
    'tools/build_temporal_policy_dataset.py:30',
    'tools/build_temporal_policy_dataset.py:180',
    'tools/build_temporal_policy_dataset.py:265',
    'tools/build_temporal_policy_dataset.py:277',
    'tools/build_temporal_policy_dataset.py:300',
    'tools/eval_temporal_walkforward.py:649',
    'tools/eval_temporal_walkforward.py:677',
    'web/scripts/runtime_decision_provenance.mjs:378',
    'LOAD_DIRECTIVE_NEXT_CHAT.md:205',
  ],
};

const structuralRecencySnapshotContractMd = `# Structural Recency Snapshot Materialization Contract (Latest)\n\n## Scope\n\n- Track: A5.5R\n- Family: \`recency_sensitive_accumulation\`\n- Status: admin/internal readiness only\n- Production activation: not approved\n\n## Canonical Members\n\nThe snapshot row contract must materialize these top-level members:\n\n- \`steps_since_regime_change\`\n- \`steps_since_pattern_change\`\n- \`steps_since_reversal_sign_flip\`\n- \`D_steps_since_sign_flip\`\n- \`M_steps_since_sign_flip\`\n- \`R_rev_steps_since_sign_flip\`\n- \`U_star_steps_since_sign_flip\`\n- \`C_steps_since_sign_flip\`\n- \`P_steps_since_sign_flip\`\n- \`B_steps_since_sign_flip\`\n- \`S_UF_steps_since_sign_flip\`\n- \`R_UF_steps_since_sign_flip\`\n- \`structural_recency_schema_version\`\n\nAdjacent controls that remain outside the member registry but should stay available for proof/admin use:\n\n- \`history_available_steps\`\n- \`ts_gap_days_from_prev\`\n\n## Source Owner\n\n- Materialization owner: snapshot builder path\n- Current code-truth basis: \`tools/build_temporal_policy_dataset.py\` defines exact reset and sentinel semantics for all members.\n- CP-0 snapshot rows do not currently carry any of these fields.\n\n## Member Semantics\n\n- Units: discrete history steps, not wall-clock time.\n- \`steps_since_regime_change\` and \`steps_since_pattern_change\` start at \`0\` and reset to \`0\` on change.\n- All \`*_steps_since_sign_flip\` members use \`-1\` as the pre-first-flip sentinel, then reset to \`0\` on sign flip.\n- \`steps_since_reversal_sign_flip\` is the canonical CP-0 decision-governing alias for reversal recency.\n- Upper bound is effectively \`history_available_steps\` for the row.\n\n## Completeness Rules\n\n- \`structural_recency_schema_version\` must be present on every row that materializes any structural-recency member.\n- For decision-governing family admission, required member completeness target is \`100%\` across candidate rows.\n- If the namespace or schema version is missing, the recency-assisted family remains blocked and the row falls back to the parent long-side family with no recency subclass.\n\n## Versioning Rules\n\nIncrement \`structural_recency_schema_version\` when any of the following changes:\n\n- member set\n- reset or sentinel semantics\n- units or bounds semantics\n- canonical member naming\n\n## Current Readiness\n\n- Snapshot rows with \`steps_since_*\` namespace: ${structuralRecencyRuntimeReadiness.current_snapshot_state?.rows_with_steps_since_namespace ?? 0}/${totalSnapshotRows}\n- Snapshot rows with \`structural_recency_schema_version\`: ${structuralRecencyRuntimeReadiness.current_snapshot_state?.rows_with_structural_recency_schema_version ?? 0}/${totalSnapshotRows}\n- Current family block reason: \`${blockedRecencyFamily.current_status?.primary_block_reason?.key ?? 'unknown'}\`\n\n## Evidence Paths\n\n- \`tools/build_temporal_policy_dataset.py:180\`\n- \`tools/build_temporal_policy_dataset.py:265\`\n- \`tools/build_temporal_policy_dataset.py:277\`\n- \`tools/build_temporal_policy_dataset.py:300\`\n- \`tools/eval_temporal_walkforward.py:649\`\n- \`web/scripts/runtime_decision_provenance.mjs:378\`\n`;

const structuralRecencyRuntimeTransportContractMd = `# Structural Recency Runtime Transport Contract (Latest)\n\n## Scope\n\n- Track: A5.5R\n- Status: admin/internal readiness only\n- Production activation: not approved\n\n## Runtime Path\n\n1. Snapshot materialization emits top-level structural-recency fields plus \`structural_recency_schema_version\`.\n2. \`uf_snapshot.json\` carries those fields without collapsing them into a compressed surrogate.\n3. \`web/scripts/sync_runtime_postgres.mjs\` stores the full snapshot row in \`runtime_decisions_latest.snapshot_row_json\`.\n4. \`web/scripts/runtime_decision_provenance.mjs\` extracts top-level \`steps_since_*\` members into \`structural_recency_components_used_json\`.\n\n## Transport Rules\n\n- Runtime sync transports structural-recency fields verbatim; it does not derive them.\n- \`structural_recency_schema_version\` must survive transport unchanged.\n- Missing structural-recency fields do not fail runtime sync, but they keep \`recency_sensitive_accumulation\` blocked.\n- The required family ladder level remains \`allow_L1_relaxed\`; exact-only coverage is not required for this family.\n\n## Consumer Classification\n\n- Decision-governing on approval: \`steps_since_regime_change\`, \`steps_since_pattern_change\`, \`steps_since_reversal_sign_flip\`\n- Proof-only: \`R_rev_steps_since_sign_flip\`\n- Admin/internal only: all remaining field-specific sign-flip recency members unless separately approved\n\n## Current Readiness\n\n- Runtime sync transport ready: ${String(structuralRecencyRuntimeReadiness.runtime_transport_readiness?.runtime_sync_transport_ready ?? false)}\n- Provenance consumer ready: ${String(structuralRecencyRuntimeReadiness.runtime_transport_readiness?.provenance_consumer_ready ?? false)}\n- Admin/internal family consumer ready: ${String(structuralRecencyRuntimeReadiness.runtime_transport_readiness?.admin_internal_family_consumer_ready ?? false)}\n\n## Activation Blockers\n\n- \`snapshot_schema_missing_steps_since_namespace\`\n- \`snapshot_schema_missing_structural_recency_schema_version\`\n- \`no_current_snapshot_rows_with_recency_contract_fields\`\n\n## Evidence Paths\n\n- \`web/scripts/runtime_decision_provenance.mjs:378\`\n- \`web/scripts/runtime_decision_provenance.mjs:634\`\n- \`web/scripts/sync_runtime_postgres.mjs:694\`\n- \`structural_recency_runtime_readiness_latest.json\`\n`;

const structuralRecencyActivationReadiness = {
  analysis_name: 'A5_5R_structural_recency_activation_readiness',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_readiness_only',
  cp_profile: 'CP-0',
  family_id: 'recency_sensitive_accumulation',
  required_ladder_level: 'allow_L1_relaxed',
  current_state: {
    snapshot_generated_at_utc: snapshotGeneratedAt,
    total_snapshot_rows: totalSnapshotRows,
    accumulation_base_population_row_count: accumulationBaseCount,
    currently_eligible_rows: blockedRecencyFamily.current_status?.eligible_row_count ?? 0,
    current_primary_block_reason: blockedRecencyFamily.current_status?.primary_block_reason ?? null,
    current_expected_eligible_row_lift_upper_bound: blockedRecencyFamily.expected_eligible_row_lift_if_contracts_completed_upper_bound ?? null,
  },
  contract_completion: {
    member_registry_defined: true,
    snapshot_materialization_contract_defined: true,
    runtime_transport_contract_defined: true,
  },
  readiness: {
    schema_ready: false,
    source_ready: false,
    runtime_sync_transport_ready: Boolean(structuralRecencyRuntimeReadiness.runtime_transport_readiness?.runtime_sync_transport_ready),
    provenance_consumer_ready: Boolean(structuralRecencyRuntimeReadiness.runtime_transport_readiness?.provenance_consumer_ready),
    admin_internal_activation_ready: false,
    decision_governing_activation_ready: false,
  },
  blockers: [
    'snapshot_schema_missing_steps_since_namespace',
    'snapshot_schema_missing_structural_recency_schema_version',
    'no_current_snapshot_rows_with_recency_contract_fields',
    'no_production_activation_approved',
  ],
  competitiveness_context: {
    structural_recency_removed: structuralRecencyRemoved,
    rationale: 'Structural recency is the dominant active component inside the current epoch feature block, so this remains the highest-ROI local activation path once snapshot materialization exists.',
  },
  quote_track_status: {
    quote_family_activation_blocked: Boolean(quoteFamilyBlockers.global_source_readiness_pass === false),
    quote_source_readiness_pass: Boolean(quoteSourceReadiness.source_readiness_pass),
    reason: quoteSourceReadiness.source_block_reasons || [],
  },
  recommended_next_step_after_a55: {
    recommended_option: 'admin/internal activation readiness for recency-assisted family',
    rationale: 'Structural recency has a complete member registry, a defined snapshot/runtime contract, and ready transport/provenance consumers. Epoch still lacks a stable gap_state enum and a real sidecar join implementation.',
  },
};

const regimeLabelEnum = [
  {
    label: 'DEGENERATE',
    status: 'supported_in_code_truth',
    source_paths: ['uf_core/layer2.py:155', 'uf_snapshot.json'],
  },
  {
    label: 'STABLE',
    status: 'supported_in_code_truth',
    source_paths: ['uf_core/layer2.py:157', 'uf_snapshot.json'],
  },
  {
    label: 'VOLATILE',
    status: 'supported_in_code_truth',
    source_paths: ['uf_core/layer2.py:159', 'uf_snapshot.json'],
  },
  {
    label: 'TRANSITIONAL',
    status: 'supported_in_code_truth',
    source_paths: ['uf_core/layer2.py:161', 'uf_snapshot.json'],
  },
  {
    label: 'INSUFFICIENT_DATA',
    status: 'supported_in_code_truth',
    source_paths: ['uf_core/uf_structural_engine.py:254', 'uf_snapshot.json'],
  },
  {
    label: 'NO_DATA',
    status: 'supported_in_code_truth',
    source_paths: ['uf_mdg_snapshot.py:261', 'uf_snapshot.json'],
  },
];

const epochStateEnumRegistry = {
  analysis_name: 'A5_5E_epoch_state_enum_registry',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_readiness_only',
  cp_profile: 'CP-0',
  registry_version: 'epoch_schema_pre_activation_v1',
  regime_code: {
    contract_status: 'partially_defined',
    canonical_field_name: 'regime_code',
    canonical_meaning: 'Stable enum encoding of the top-level regime label for runtime rows.',
    label_enum_ready: true,
    numeric_enum_ready: false,
    supported_labels: regimeLabelEnum,
    current_snapshot_observed_labels: observedSnapshotRegimes,
    current_temporal_dataset_behavior: 'Dynamic first-encounter integer assignment in tools/build_temporal_policy_dataset.py.',
    current_observed_row_trace_first_encounter_map: rowTraceRegimeMap,
    blocking_reason_for_numeric_contract: 'Current numeric mapping is dataset-order-dependent and therefore not a stable activation contract.',
    epoch_element_classification: 'gating',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:252',
      'tools/build_temporal_policy_dataset.py:500',
      'uf_core/layer2.py:149',
      'uf_core/uf_structural_engine.py:254',
      'uf_mdg_snapshot.py:261',
    ],
  },
  gap_state: {
    contract_status: 'blocked_missing_authoritative_enum',
    canonical_field_name: 'gap_state',
    enum_values: [],
    activation_ready: false,
    current_code_truth_proxy_fields: ['ts_gap_days_from_prev'],
    current_code_truth_proxy_policies: ['missing_day_policy=weekend_and_market_holiday_gaps_allowed'],
    blocking_reason: 'Current code truth provides a numeric gap-days measure and a missing-day policy note, but no categorical gap_state enum.',
    epoch_element_classification: 'suppression_modifier',
    evidence_paths: [
      'tools/build_temporal_policy_dataset.py:263',
      'tools/eval_temporal_walkforward.py:654',
      'tools/regenerate_fresh_temporal_rowtrace_from_raw.py:262',
    ],
  },
  epoch_schema_version: {
    contract_status: 'recommended_not_implemented',
    canonical_field_name: 'epoch_schema_version',
    meaning: 'Version of the normalized epoch projection payload joined into the runtime row.',
    increment_when: [
      'regime label or code contract changes',
      'gap_state enum changes',
      'epoch projection field set changes',
      'join precedence or missing-data semantics change',
    ],
    epoch_element_classification: 'gating',
    activation_ready: false,
  },
  projected_epoch_elements: [
    {
      field: 'epoch.company_news_catalyst',
      classification: 'confidence_modifier',
      contract_status: 'recommended_not_implemented',
      evidence_paths: ['web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:100', 'web_user_data/TFE_Specification_v2_4.tex:1543'],
    },
    {
      field: 'epoch.macro_sector_sphere_of_impact',
      classification: 'suppression_modifier',
      contract_status: 'recommended_not_implemented',
      evidence_paths: ['web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:101', 'web_user_data/TFE_Specification_v2_4.tex:1579'],
    },
  ],
  evidence_paths: [
    'tools/build_temporal_policy_dataset.py:252',
    'tools/build_temporal_policy_dataset.py:500',
    'uf_core/layer2.py:149',
    'uf_core/uf_structural_engine.py:254',
    'uf_mdg_snapshot.py:255',
    'tools/regenerate_fresh_temporal_rowtrace_from_raw.py:262',
  ],
};

const epochStateEnumRegistryMd = `# Epoch State Enum Registry (Latest)\n\n## Scope\n\n- Track: A5.5E\n- Status: admin/internal readiness only\n- Production activation: not approved\n\n## Regime Code\n\nCurrent code truth supports stable regime labels but not a stable numeric \`regime_code\` contract yet.\n\nSupported labels observed in current code truth:\n\n- \`DEGENERATE\`\n- \`STABLE\`\n- \`VOLATILE\`\n- \`TRANSITIONAL\`\n- \`INSUFFICIENT_DATA\`\n- \`NO_DATA\`\n\nCurrent temporal tooling behavior:\n\n- \`tools/build_temporal_policy_dataset.py\` assigns integer regime codes by first encounter order.\n- Current observed first-encounter map from row-trace evidence: ${rowTraceRegimeMap.mapping ? `\`${JSON.stringify(rowTraceRegimeMap.mapping)}\`` : '`unavailable`'}\n- This is not activation-ready because the numeric mapping is dataset-order-dependent.\n\n## Gap State\n\n\`gap_state\` is not truthfully definable as an enum today. Current code truth only provides:\n\n- numeric \`ts_gap_days_from_prev\`\n- policy note \`missing_day_policy=weekend_and_market_holiday_gaps_allowed\`\n\nResult:\n\n- \`gap_state\` enum status: blocked\n- activation readiness: false\n\n## Epoch Schema Version\n\n\`epoch_schema_version\` is defined here as a required control field, but it is not implemented yet. It must change when:\n\n- regime label/code semantics change\n- gap-state semantics change\n- projected epoch fields change\n- runtime join semantics change\n\n## Epoch Element Classification\n\n- \`regime_code\`: gating\n- \`gap_state\`: suppression modifier target, but blocked until an enum exists\n- \`epoch.company_news_catalyst\`: confidence modifier target\n- \`epoch.macro_sector_sphere_of_impact\`: suppression modifier target\n- \`epoch_schema_version\`: gating\n\n## Evidence Paths\n\n- \`tools/build_temporal_policy_dataset.py:252\`\n- \`tools/build_temporal_policy_dataset.py:500\`\n- \`uf_core/layer2.py:149\`\n- \`uf_core/uf_structural_engine.py:254\`\n- \`uf_mdg_snapshot.py:255\`\n- \`tools/regenerate_fresh_temporal_rowtrace_from_raw.py:262\`\n`;

const epochSidecarProjectionContractMd = `# Epoch Sidecar Projection Contract (Latest)\n\n## Scope\n\n- Track: A5.5E\n- Status: recommended contract only\n- Implementation status: not implemented\n- Production activation: not approved\n\n## Current Code Truth\n\n- Runtime sync currently reads \`uf_snapshot.json\` and the quote cache only.\n- No epoch sidecar join exists in current code truth.\n- Provenance extraction can already read top-level \`regime_code\`, \`gap_state\`, and nested \`epoch.*\` values when they exist.\n\n## Recommended Minimal Projection Payload\n\nThe sidecar should project normalized values only, not raw event payloads. Recommended minimum fields:\n\n- \`ticker\`\n- \`effective_from_utc\`\n- \`effective_to_utc\`\n- \`epoch_schema_version\`\n- \`epoch.company_news_catalyst\`\n- \`epoch.macro_sector_sphere_of_impact\`\n- \`projection_generated_utc\`\n\n## Recommended Join Identity\n\nBecause current runtime rows are organized per ticker and snapshot publication, the minimum recommended join identity is:\n\n- normalized \`ticker\`\n- snapshot publication time inside \`[effective_from_utc, effective_to_utc)\`\n- matching \`epoch_schema_version\`\n\nThis is a recommended contract for readiness planning only. It is not current code truth.\n\n## Ownership\n\n- Snapshot materialization remains owner of top-level \`regime_code\` and \`gap_state\`.\n- Epoch sidecar owns normalized \`epoch.*\` projections plus \`epoch_schema_version\`.\n- Runtime sync is the projection point; it must transport approved sidecar values and must not infer epoch state.\n\n## Readiness\n\n- Sidecar payload exists in code truth: false\n- Join contract exists in code truth: false\n- Readiness for activation work: blocked\n\n## Evidence Paths\n\n- \`web/scripts/runtime_decision_provenance.mjs:397\`\n- \`web/scripts/runtime_decision_provenance.mjs:405\`\n- \`web/scripts/sync_runtime_postgres.mjs:694\`\n- \`epoch_state_runtime_readiness_latest.json\`\n- \`web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:100\`\n- \`web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:101\`\n`;

const epochRuntimeJoinSemanticsMd = `# Epoch Runtime Join Semantics (Latest)\n\n## Scope\n\n- Track: A5.5E\n- Status: recommended semantics only\n- Implementation status: not implemented\n- Production activation: not approved\n\n## Join Precedence\n\n1. Snapshot top-level \`regime\` label remains the canonical current-regime surface for CP-0 rows.\n2. If snapshot materialization emits approved top-level \`regime_code\` and \`gap_state\`, runtime sync transports those values unchanged.\n3. If exactly one sidecar projection row matches the normalized ticker and the snapshot publication time falls inside the projection effective interval, runtime sync may project \`epoch.*\` and \`epoch_schema_version\` into the runtime row.\n4. If no sidecar row matches, runtime sync leaves \`epoch.*\` absent and the epoch-assisted family remains blocked.\n5. If multiple sidecar rows match, classify the row as a join conflict, do not project epoch values, and surface the conflict to admin/internal diagnostics.\n6. If \`epoch_schema_version\` is missing or mismatched, block epoch-family activation and leave parent long-side semantics unchanged.\n\n## Missing-Data Behavior\n\n- Missing \`regime_code\`: epoch-assisted family blocked\n- Missing \`gap_state\`: epoch-assisted family blocked\n- Missing sidecar projection: epoch-assisted family blocked\n- Join conflict: epoch-assisted family blocked\n- Parent long-side family behavior remains unchanged in all blocked cases\n\n## Classification Targets\n\n- \`regime_code\`: gating\n- \`gap_state\`: suppression modifier target\n- \`epoch.company_news_catalyst\`: confidence modifier target\n- \`epoch.macro_sector_sphere_of_impact\`: suppression modifier target\n\n## Current Readiness\n\n- Top-level transport ready once fields exist: ${String(epochStateRuntimeReadiness.runtime_transport_readiness?.runtime_sync_transport_ready_for_top_level_fields ?? false)}\n- Sidecar projection join ready: ${String(epochStateRuntimeReadiness.runtime_transport_readiness?.runtime_sync_projection_join_ready ?? false)}\n- Provenance consumer ready: ${String(epochStateRuntimeReadiness.runtime_transport_readiness?.provenance_consumer_ready ?? false)}\n\n## Evidence Paths\n\n- \`epoch_state_runtime_readiness_latest.json\`\n- \`web/scripts/runtime_decision_provenance.mjs:397\`\n- \`web/scripts/runtime_decision_provenance.mjs:405\`\n- \`web/scripts/sync_runtime_postgres.mjs:694\`\n`;

const epochActivationReadiness = {
  analysis_name: 'A5_5E_epoch_activation_readiness',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_readiness_only',
  cp_profile: 'CP-0',
  family_id: 'epoch_assisted_accumulation',
  required_ladder_level: 'allow_L1_relaxed',
  current_state: {
    snapshot_generated_at_utc: snapshotGeneratedAt,
    total_snapshot_rows: totalSnapshotRows,
    accumulation_base_population_row_count: accumulationBaseCount,
    currently_eligible_rows: blockedEpochFamily.current_status?.eligible_row_count ?? 0,
    current_primary_block_reason: blockedEpochFamily.current_status?.primary_block_reason ?? null,
    current_expected_eligible_row_lift_upper_bound: blockedEpochFamily.expected_eligible_row_lift_if_contracts_completed_upper_bound ?? null,
    snapshot_rows_with_regime_code: epochStateRuntimeReadiness.current_snapshot_state?.rows_with_regime_code ?? 0,
    snapshot_rows_with_gap_state: epochStateRuntimeReadiness.current_snapshot_state?.rows_with_gap_state ?? 0,
    snapshot_rows_with_epoch_schema_version: epochStateRuntimeReadiness.current_snapshot_state?.rows_with_epoch_schema_version ?? 0,
  },
  contract_completion: {
    regime_label_enum_defined: true,
    regime_numeric_code_stable: false,
    gap_state_enum_defined: false,
    epoch_schema_version_semantics_defined: true,
    sidecar_projection_contract_defined: true,
    runtime_join_semantics_defined: true,
  },
  readiness: {
    top_level_regime_label_ready: true,
    top_level_regime_numeric_ready: false,
    gap_state_ready: false,
    runtime_sync_transport_ready_for_top_level_fields: Boolean(epochStateRuntimeReadiness.runtime_transport_readiness?.runtime_sync_transport_ready_for_top_level_fields),
    runtime_sync_projection_join_ready: Boolean(epochStateRuntimeReadiness.runtime_transport_readiness?.runtime_sync_projection_join_ready),
    provenance_consumer_ready: Boolean(epochStateRuntimeReadiness.runtime_transport_readiness?.provenance_consumer_ready),
    admin_internal_activation_ready: false,
    decision_governing_activation_ready: false,
  },
  blockers: [
    'snapshot_schema_missing_regime_code',
    'snapshot_schema_missing_gap_state',
    'gap_state_enum_not_defined_in_code_truth',
    'regime_code_numeric_mapping_not_stable',
    'epoch_sidecar_projection_not_implemented',
    'epoch_runtime_join_not_implemented',
    'epoch_schema_version_not_present',
    'no_production_activation_approved',
  ],
  element_classification: {
    regime_code: 'gating',
    gap_state: 'suppression_modifier',
    epoch_company_news_catalyst: 'confidence_modifier',
    epoch_macro_sector_sphere_of_impact: 'suppression_modifier',
    epoch_schema_version: 'gating',
  },
  quote_track_status: {
    quote_family_activation_blocked: Boolean(quoteFamilyBlockers.global_source_readiness_pass === false),
    quote_source_readiness_pass: Boolean(quoteSourceReadiness.source_readiness_pass),
    reason: quoteSourceReadiness.source_block_reasons || [],
  },
  recommended_next_step_after_a55: {
    recommended_option: 'admin/internal activation readiness for recency-assisted family',
    rationale: 'Epoch remains blocked on both an undefined gap-state enum and an unimplemented sidecar projection join. Structural recency is the lower-friction next move.',
  },
};

const structuralRecencyRegistryMd = `# Structural Recency Member Registry (Latest)\n\n## Summary\n\n- Family: \`recency_sensitive_accumulation\`\n- Required ladder level: \`allow_L1_relaxed\`\n- Current snapshot rows with recency members: ${structuralRecencyRuntimeReadiness.current_snapshot_state?.rows_with_steps_since_namespace ?? 0}/${totalSnapshotRows}\n- Current eligible rows: ${blockedRecencyFamily.current_status?.eligible_row_count ?? 0}/${accumulationBaseCount}\n\n## Decision-Governing Members\n\n- \`steps_since_regime_change\`\n- \`steps_since_pattern_change\`\n- \`steps_since_reversal_sign_flip\`\n\nThese are the members that should govern the initial recency-assisted CP-0 family once snapshot materialization exists.\n\n## Proof/Admin Members\n\n- Proof-only: \`R_rev_steps_since_sign_flip\`\n- Admin/internal only: the remaining field-specific \`*_steps_since_sign_flip\` members\n\n## Reset and Sentinel Rules\n\n- Regime/pattern members start at \`0\` and reset to \`0\` on change.\n- Sign-flip members use \`-1\` before the first observed flip, then reset to \`0\` on flip.\n- All members use history steps as units.\n\n## Why This Matters\n\nThe current epoch-decomposition microprobe shows structural recency is the dominant active component inside the current epoch block. That makes this the highest-ROI local activation path once the snapshot contract exists.\n\n- \`G_structural_recency_removed\`: ${structuralRecencyRemoved ? `flip=${structuralRecencyRemoved.flip_rate}, delta_outcome=${structuralRecencyRemoved.delta_outcome_over_index_pct}, delta_excess=${structuralRecencyRemoved.delta_mean_excess_vs_spy}` : 'unavailable'}\n- \`G_regime_code_removed\`: ${regimeCodeRemoved ? `flip=${regimeCodeRemoved.flip_rate}, delta_outcome=${regimeCodeRemoved.delta_outcome_over_index_pct}, delta_excess=${regimeCodeRemoved.delta_mean_excess_vs_spy}` : 'unavailable'}\n- \`G_gap_removed\`: ${gapRemoved ? `flip=${gapRemoved.flip_rate}, delta_outcome=${gapRemoved.delta_outcome_over_index_pct}, delta_excess=${gapRemoved.delta_mean_excess_vs_spy}` : 'unavailable'}\n\n## Evidence Paths\n\n- \`tools/build_temporal_policy_dataset.py:180\`\n- \`tools/build_temporal_policy_dataset.py:265\`\n- \`tools/build_temporal_policy_dataset.py:277\`\n- \`tools/build_temporal_policy_dataset.py:300\`\n- \`tools/eval_temporal_walkforward.py:649\`\n- \`tools/eval_temporal_walkforward.py:677\`\n- \`LOAD_DIRECTIVE_NEXT_CHAT.md:205\`\n`;

writeJson(path.join(ROOT, 'structural_recency_member_registry_latest.json'), structuralRecencyRegistry);
writeText(path.join(ROOT, 'structural_recency_member_registry_latest.md'), structuralRecencyRegistryMd);
writeText(path.join(ROOT, 'structural_recency_snapshot_materialization_contract_latest.md'), structuralRecencySnapshotContractMd);
writeText(path.join(ROOT, 'structural_recency_runtime_transport_contract_latest.md'), structuralRecencyRuntimeTransportContractMd);
writeJson(path.join(ROOT, 'structural_recency_activation_readiness_latest.json'), structuralRecencyActivationReadiness);

writeJson(path.join(ROOT, 'epoch_state_enum_registry_latest.json'), epochStateEnumRegistry);
writeText(path.join(ROOT, 'epoch_state_enum_registry_latest.md'), epochStateEnumRegistryMd);
writeText(path.join(ROOT, 'epoch_sidecar_projection_contract_latest.md'), epochSidecarProjectionContractMd);
writeText(path.join(ROOT, 'epoch_runtime_join_semantics_latest.md'), epochRuntimeJoinSemanticsMd);
writeJson(path.join(ROOT, 'epoch_activation_readiness_latest.json'), epochActivationReadiness);
