#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

const ROOT = '/workspaces/Tao_Financial_Engine';
const NOW = new Date();
const GENERATED_AT = NOW.toISOString();

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

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(filePath, value) {
  fs.writeFileSync(filePath, value, 'utf8');
}

function hoursBetween(aIso, bIso) {
  const a = Date.parse(aIso);
  const b = Date.parse(bIso);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  return Number(((b - a) / 3600000).toFixed(3));
}

function toPct(part, total) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total === 0) return 0;
  return Number(((part / total) * 100).toFixed(6));
}

const snapshotContracts = readJson(path.join(ROOT, 'snapshot_event_contracts_latest.json'));
const quoteContracts = readJson(path.join(ROOT, 'quote_field_contracts_latest.json'));
const snapshot = readJson(path.join(ROOT, 'uf_snapshot.json'));
const quoteCache = readJson(path.join(ROOT, 'web/data/screener-quote-cache.json'));

const snapshotRows = Array.isArray(snapshot.rows) ? snapshot.rows : [];
const totalSnapshotRows = snapshotRows.length;
const snapshotGeneratedAt = snapshot.generated_at_utc || null;
const quoteGeneratedAt = quoteCache.generated_at_utc || null;
const quoteAgeHoursNow = quoteGeneratedAt ? hoursBetween(quoteGeneratedAt, GENERATED_AT) : null;
const quoteLagVsSnapshotHours = quoteGeneratedAt && snapshotGeneratedAt ? hoursBetween(quoteGeneratedAt, snapshotGeneratedAt) : null;
const quoteSymbolsCached = Number(quoteCache.symbols_cached || 0);
const quoteSymbolsTotal = Number(quoteCache.symbols_total || 0);
const quoteCoveragePct = toPct(quoteSymbolsCached, quoteSymbolsTotal || quoteSymbolsCached || 1);

const currentSnapshotKeySet = new Set();
let rowsWithRecencyNamespace = 0;
let rowsWithRecencySchemaVersion = 0;
let rowsWithEpochState = 0;
let rowsWithRegimeCode = 0;
let rowsWithGapState = 0;
let rowsWithEpochSchemaVersion = 0;
for (const row of snapshotRows) {
  for (const key of Object.keys(row || {})) currentSnapshotKeySet.add(key);
  const hasRecencyNamespace = Object.keys(row || {}).some((key) => key.startsWith('steps_since_') || key.includes('recency'));
  if (hasRecencyNamespace) rowsWithRecencyNamespace += 1;
  if (row && row.structural_recency_schema_version != null) rowsWithRecencySchemaVersion += 1;
  const hasEpoch = Boolean(
    (row && row.epoch && typeof row.epoch === 'object' && Object.keys(row.epoch).length > 0) ||
      (row && row.regime_code != null) ||
      (row && row.gap_state != null) ||
      (row && row.epoch_schema_version != null)
  );
  if (hasEpoch) rowsWithEpochState += 1;
  if (row && row.regime_code != null) rowsWithRegimeCode += 1;
  if (row && row.gap_state != null) rowsWithGapState += 1;
  if (row && row.epoch_schema_version != null) rowsWithEpochSchemaVersion += 1;
}

const currentSnapshotKeys = Array.from(currentSnapshotKeySet).sort();

const recencyFamily = snapshotContracts.families.find((item) => item.id === 'recency_sensitive_accumulation');
const epochFamily = snapshotContracts.families.find((item) => item.id === 'epoch_assisted_accumulation');
if (!recencyFamily || !epochFamily) {
  throw new Error('Missing recency or epoch family in snapshot_event_contracts_latest.json');
}

const DEFAULT_VALIDATION_MAX_AGE_HOURS = 30;
const DEFAULT_RUNTIME_CACHE_TTL_MS = 60000;
const DEFAULT_RUNTIME_CACHE_MAX_STALE_MS = 15 * 60 * 1000;

const structuralRecencyContract = {
  analysis_name: 'A5_4S1_structural_recency_contract',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  contract_version: 'v1_namespace_transport',
  family_id: recencyFamily.id,
  purpose: recencyFamily.purpose,
  parent_family: recencyFamily.parent_family,
  required_ladder_level: recencyFamily.required_ladder_level,
  contract_boundary: 'snapshot row namespace + runtime transport + provenance extraction only; no production activation',
  contract_fields: [
    {
      field: 'steps_since_*',
      location: 'snapshot_row_top_level_namespace',
      type_requirement: 'non-negative integer namespace',
      required_for_family_admission: true,
      current_code_truth_status: 'namespace_consumer_exists_but_no_current_snapshot_members',
      member_registry_status: 'not_defined_in_current_code_truth',
      fallback_if_missing: recencyFamily.fallback_default_behavior_if_field_missing,
    },
    {
      field: 'structural_recency_schema_version',
      location: 'snapshot_row_top_level',
      type_requirement: 'string',
      required_for_family_admission: true,
      recommended_initial_value: 'v1',
      current_code_truth_status: 'not_present_in_current_snapshot_rows',
      fallback_if_missing: recencyFamily.fallback_default_behavior_if_field_missing,
    },
  ],
  nullability_and_completeness: {
    required_fields_nullable_in_source: false,
    namespace_or_version_missing_blocks_family: true,
    decision_governing_target_completeness: '100% of eligible rows',
  },
  freshness_requirement: 'Recency fields must be generated in the same snapshot publication as the structural basis. Runtime sync transports them; it does not derive them.',
  normalization_rules: [
    'Only top-level keys starting with steps_since_ are canonical for the structural recency namespace.',
    'Legacy top-level keys containing recency may be read during migration, but they are not the target schema.',
    'All values must be deterministic numeric counts already resolved before runtime sync.',
  ],
  hard_block_vs_soft_block_classification: recencyFamily.hard_block_vs_soft_block_classification,
  runtime_exposure_class_current: 'admin-only',
  runtime_exposure_class_target: 'decision-governing',
  current_observation: {
    total_snapshot_rows: totalSnapshotRows,
    rows_with_steps_since_namespace: rowsWithRecencyNamespace,
    rows_with_structural_recency_schema_version: rowsWithRecencySchemaVersion,
    blocked_base_population_row_count: recencyFamily.current_status.base_population_row_count,
    current_block_reason: recencyFamily.current_status.primary_block_reason,
    expected_eligible_row_lift_upper_bound: recencyFamily.expected_eligible_row_lift_if_contracts_completed_upper_bound.additional_rows_if_required_fields_are_materialized,
  },
  evidence_paths: [
    'uf_mdg_snapshot.py:202',
    'uf_mdg_snapshot.py:228',
    'rebuild_uf_snapshot.py:699',
    'web/scripts/runtime_decision_provenance.mjs:378',
    'web/scripts/runtime_decision_provenance.mjs:634',
    'web/scripts/sync_runtime_postgres.mjs:694',
    'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:98',
    'LOAD_DIRECTIVE_NEXT_CHAT.md:206',
  ],
};

const structuralRecencyRuntimeReadiness = {
  analysis_name: 'A5_4S1_structural_recency_runtime_readiness',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  current_snapshot_state: {
    generated_at_utc: snapshotGeneratedAt,
    total_rows: totalSnapshotRows,
    rows_with_steps_since_namespace: rowsWithRecencyNamespace,
    rows_with_structural_recency_schema_version: rowsWithRecencySchemaVersion,
    schema_present: rowsWithRecencyNamespace > 0 && rowsWithRecencySchemaVersion > 0,
  },
  runtime_transport_readiness: {
    snapshot_builder_schema_ready: false,
    runtime_sync_transport_ready: true,
    runtime_sync_transport_basis: 'runtime_decisions_latest persists snapshot_row_json as JSONB, so new top-level snapshot fields will flow through once the snapshot builder emits them.',
    provenance_consumer_ready: true,
    provenance_consumer_basis: 'extractStructuralRecencyComponents already reads top-level steps_since_* and recency keys.',
    admin_internal_family_consumer_ready: false,
  },
  activation_blocked: true,
  block_reasons: [
    'snapshot_schema_missing_steps_since_namespace',
    'snapshot_schema_missing_structural_recency_schema_version',
    'no_current_snapshot_rows_with_recency_contract_fields',
  ],
  recommended_next_implementation: 'Add steps_since_* namespace plus structural_recency_schema_version to the snapshot builder output. Do not change ranking, allocator semantics, or public recommendation behavior.',
};

const epochStateContract = {
  analysis_name: 'A5_4S2_epoch_state_contract',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  contract_version: 'v1_transport_and_projection',
  family_id: epochFamily.id,
  purpose: epochFamily.purpose,
  parent_family: epochFamily.parent_family,
  required_ladder_level: epochFamily.required_ladder_level,
  contract_boundary: 'snapshot regime/gap fields + epoch projection join contract + provenance extraction only; no production activation',
  contract_fields: [
    {
      field: 'regime_code',
      location: 'snapshot_row_top_level',
      type_requirement: 'string enum contract required',
      current_code_truth_status: 'field_absent_from_current_snapshot_rows',
      enum_registry_status: 'not_defined_in_current_code_truth',
      source_of_truth: 'snapshot materialization',
    },
    {
      field: 'gap_state',
      location: 'snapshot_row_top_level',
      type_requirement: 'structured categorical contract required',
      current_code_truth_status: 'field_absent_from_current_snapshot_rows',
      enum_registry_status: 'not_defined_in_current_code_truth',
      source_of_truth: 'snapshot materialization',
    },
    {
      field: 'epoch_schema_version',
      location: 'snapshot_row_top_level',
      type_requirement: 'string',
      current_code_truth_status: 'field_absent_from_current_snapshot_rows',
      recommended_initial_value: 'v1',
      source_of_truth: 'event/epoch registry sidecar',
    },
    {
      field: 'epoch.company_news_catalyst',
      location: 'snapshot_row_top_level_nested_object',
      type_requirement: 'normalized epoch projection',
      current_code_truth_status: 'projection_not_implemented',
      source_of_truth: 'event/epoch registry sidecar',
    },
    {
      field: 'epoch.macro_sector_sphere_of_impact',
      location: 'snapshot_row_top_level_nested_object',
      type_requirement: 'normalized epoch projection',
      current_code_truth_status: 'projection_not_implemented',
      source_of_truth: 'event/epoch registry sidecar',
    },
  ],
  nullability_and_completeness: {
    required_fields_nullable_in_source: false,
    missing_regime_gap_or_epoch_projection_blocks_family: true,
    decision_governing_target_completeness: '100% of eligible rows',
  },
  freshness_requirement: 'Epoch state must share the active epoch schema version and the published runtime artifact set. Runtime sync may project normalized epoch values into rows but must not invent them.',
  normalization_rules: [
    'regime_code and gap_state belong to the snapshot materialization path, not runtime inference.',
    'epoch.* values are normalized projections only; raw sidecar/event payloads remain outside the runtime row contract.',
    'epoch_schema_version must version the projection payload used for the runtime row.',
  ],
  hard_block_vs_soft_block_classification: epochFamily.hard_block_vs_soft_block_classification,
  runtime_exposure_class_current: 'admin-only',
  runtime_exposure_class_target: 'decision-governing',
  current_observation: {
    total_snapshot_rows: totalSnapshotRows,
    rows_with_any_epoch_state: rowsWithEpochState,
    rows_with_regime_code: rowsWithRegimeCode,
    rows_with_gap_state: rowsWithGapState,
    rows_with_epoch_schema_version: rowsWithEpochSchemaVersion,
    blocked_base_population_row_count: epochFamily.current_status.base_population_row_count,
    current_block_reason: epochFamily.current_status.primary_block_reason,
    expected_eligible_row_lift_upper_bound: epochFamily.expected_eligible_row_lift_if_contracts_completed_upper_bound.additional_rows_if_required_fields_are_materialized,
  },
  evidence_paths: [
    'web/scripts/runtime_decision_provenance.mjs:397',
    'web/scripts/runtime_decision_provenance.mjs:405',
    'web/scripts/sync_runtime_postgres.mjs:694',
    'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:98',
    'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:100',
    'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:101',
    'web_user_data/TFE_Specification_v2_4.tex:1629',
    'web_user_data/TFE_Specification_v2_4.tex:1661',
    'web_user_data/TFE_Specification_v2_4.tex:1733',
    'web_user_data/TFE_Specification_v2_4.tex:1747',
    'L5_CURRENT_SYSTEM_FULL_SPEC.md:60',
    'LOAD_DIRECTIVE_NEXT_CHAT.md:206',
  ],
};

const epochStateRuntimeReadiness = {
  analysis_name: 'A5_4S2_epoch_state_runtime_readiness',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  current_snapshot_state: {
    generated_at_utc: snapshotGeneratedAt,
    total_rows: totalSnapshotRows,
    rows_with_any_epoch_state: rowsWithEpochState,
    rows_with_regime_code: rowsWithRegimeCode,
    rows_with_gap_state: rowsWithGapState,
    rows_with_epoch_schema_version: rowsWithEpochSchemaVersion,
    schema_present: rowsWithEpochState > 0 && rowsWithRegimeCode > 0 && rowsWithGapState > 0,
  },
  runtime_transport_readiness: {
    snapshot_builder_regime_gap_ready: false,
    runtime_sync_transport_ready_for_top_level_fields: true,
    runtime_sync_projection_join_ready: false,
    runtime_sync_projection_join_basis: 'Current runtime sync reads uf_snapshot.json and screener-quote-cache.json only; no epoch sidecar join exists in code truth.',
    provenance_consumer_ready: true,
    provenance_consumer_basis: 'extractEpochComponents already reads top-level regime_code, gap_state, and row.epoch when present.',
    admin_internal_family_consumer_ready: false,
  },
  activation_blocked: true,
  block_reasons: [
    'snapshot_schema_missing_regime_code',
    'snapshot_schema_missing_gap_state',
    'epoch_sidecar_projection_not_defined_in_runtime_sync',
    'epoch_schema_version_not_present',
  ],
  recommended_next_implementation: 'Define the epoch projection payload and runtime sync join contract, then add regime_code and gap_state to snapshot materialization. Keep behavior unchanged.',
};

const quoteFreshnessSlaLines = [
  '# Quote Freshness SLA (Latest)',
  '',
  '## Basis',
  '',
  '- Refresh wrapper order in current code truth: snapshot rebuild -> quote cache refresh -> profile override refresh -> runtime sync -> validation gate.',
  '- Validation freshness gate default: `TFE_VALIDATION_MAX_AGE_HOURS = 30`.',
  '- Runtime Postgres cache TTL default: `60000 ms`.',
  '- Runtime Postgres max stale fallback default: `900000 ms` (15 minutes).',
  '',
  '## SLA',
  '',
  '- Quote source readiness requires symbol coverage completeness and publication alignment with the active snapshot/runtime artifact set.',
  '- Quote artifact publication alignment means `quote_cache.generated_at_utc >= snapshot.generated_at_utc` for the published set used by runtime sync.',
  '- Quote freshness for activation readiness must stay within the current validation freshness window (`<= 30 hours`).',
  '- The 15-minute stale-cache fallback is a transient read-failure allowance only. It is not sufficient for quote-family activation readiness.',
  '',
  '## Current Observed State',
  '',
  `- Quote cache generated_at_utc: ${quoteGeneratedAt}`,
  `- Snapshot generated_at_utc: ${snapshotGeneratedAt}`,
  `- Quote lag behind snapshot: ${quoteLagVsSnapshotHours} hours`,
  `- Quote age versus now: ${quoteAgeHoursNow} hours`,
  `- Symbol coverage: ${quoteSymbolsCached}/${quoteSymbolsTotal} (${quoteCoveragePct}%)`,
  '',
  '## Interpretation',
  '',
  '- Quote-family activation remains blocked until freshness is restored and the family-specific extraction gates pass.',
];
const quoteFreshnessSla = `${quoteFreshnessSlaLines.join('\n')}\n`;

const sourceReadinessChecks = [
  {
    id: 'symbol_coverage_complete',
    pass: quoteSymbolsTotal > 0 && quoteSymbolsCached === quoteSymbolsTotal,
    details: {
      symbols_cached: quoteSymbolsCached,
      symbols_total: quoteSymbolsTotal,
      coverage_pct: quoteCoveragePct,
    },
  },
  {
    id: 'publication_alignment_with_snapshot',
    pass: quoteLagVsSnapshotHours !== null ? quoteLagVsSnapshotHours <= 0 : false,
    details: {
      quote_generated_at_utc: quoteGeneratedAt,
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_minus_snapshot_hours: quoteLagVsSnapshotHours,
    },
  },
  {
    id: 'quote_age_within_validation_window',
    pass: quoteAgeHoursNow !== null ? quoteAgeHoursNow <= DEFAULT_VALIDATION_MAX_AGE_HOURS : false,
    details: {
      quote_age_hours_now: quoteAgeHoursNow,
      max_age_hours_allowed: DEFAULT_VALIDATION_MAX_AGE_HOURS,
    },
  },
];

const quoteSourceReadinessGate = {
  analysis_name: 'A5_4QH_quote_source_readiness_gate',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  basis: {
    validation_max_age_hours_default: DEFAULT_VALIDATION_MAX_AGE_HOURS,
    runtime_cache_ttl_ms_default: DEFAULT_RUNTIME_CACHE_TTL_MS,
    runtime_cache_max_stale_ms_default: DEFAULT_RUNTIME_CACHE_MAX_STALE_MS,
    refresh_sequence: 'snapshot_rebuild -> quote_cache_refresh -> profile_override_refresh -> runtime_sync -> validation_gate',
  },
  quote_artifact_state: {
    quote_generated_at_utc: quoteGeneratedAt,
    snapshot_generated_at_utc: snapshotGeneratedAt,
    quote_age_hours_now: quoteAgeHoursNow,
    quote_lag_vs_snapshot_hours: quoteLagVsSnapshotHours,
    symbols_cached: quoteSymbolsCached,
    symbols_total: quoteSymbolsTotal,
    coverage_pct: quoteCoveragePct,
    source_snapshot: quoteCache.source_snapshot || null,
  },
  source_readiness_checks: sourceReadinessChecks,
  source_readiness_pass: sourceReadinessChecks.every((item) => item.pass),
  extraction_readiness_gate_definition: {
    description: 'Family extraction readiness requires source_readiness_pass plus complete required-field extraction for the target family contract.',
    depends_on_source_readiness: true,
    family_field_completeness_required: true,
  },
  source_block_reasons: sourceReadinessChecks.filter((item) => !item.pass).map((item) => item.id),
};

const quoteFamilies = quoteContracts.families || [];
const quoteFamilyActivationBlockers = {
  analysis_name: 'A5_4QH_quote_family_activation_blockers',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  global_source_readiness_pass: quoteSourceReadinessGate.source_readiness_pass,
  families: quoteFamilies.map((family) => ({
    id: family.id,
    activation_blocked: true,
    blocker_classes: [
      ...(quoteSourceReadinessGate.source_readiness_pass ? [] : ['quote_source_not_ready']),
      ...(family.readiness.extraction_ready ? [] : ['family_field_extraction_not_ready']),
      'no_production_activation_approved',
    ],
    source_readiness: family.readiness.source_ready,
    extraction_readiness: family.readiness.extraction_ready,
    current_eligible_row_count: family.current_status.eligible_row_count,
    base_population_row_count: family.current_status.base_population_row_count,
    primary_block_reason: family.current_status.primary_block_reason,
    required_fields: family.exact_required_fields,
    required_field_non_null_source_stats: (family.source_of_truth_by_field || []).map((item) => ({
      field: item.field,
      key_presence_symbols: item.current_source_statistics?.key_presence_symbols ?? null,
      non_null_symbols: item.current_source_statistics?.non_null_symbols ?? null,
    })),
    current_activation_blockers: [
      ...(quoteSourceReadinessGate.source_block_reasons || []),
      family.current_status.primary_block_reason?.key ?? 'unknown_family_blocker',
    ],
  })),
};

const structuralRecencyContractMd = [
  '# Structural Recency Contract (Latest)',
  '',
  `- Family: ${structuralRecencyContract.family_id}`,
  `- Parent family: ${structuralRecencyContract.parent_family}`,
  `- Required ladder level: ${structuralRecencyContract.required_ladder_level}`,
  '',
  '## Contract',
  '',
  '- Add `steps_since_*` as a top-level snapshot namespace.',
  '- Add `structural_recency_schema_version` as a top-level snapshot field.',
  '- Keep this contract admin/internal only. No production activation is approved in this step.',
  '',
  '## Current Code Truth',
  '',
  `- Snapshot rows with recency namespace: ${rowsWithRecencyNamespace}/${totalSnapshotRows}`,
  `- Snapshot rows with structural_recency_schema_version: ${rowsWithRecencySchemaVersion}/${totalSnapshotRows}`,
  '- Runtime sync transport is already viable because `runtime_decisions_latest` stores `snapshot_row_json` as JSONB.',
  '- Provenance extraction is already viable because `extractStructuralRecencyComponents` reads top-level `steps_since_*` keys.',
  '',
  '## Recommendation',
  '',
  '- Add the namespace and schema version in the snapshot builder first. Do not change ranking or allocator behavior.',
].join('\n') + '\n';

const structuralRecencySchemaDelta = [
  '# Structural Recency Schema Delta (Latest)',
  '',
  '## Current Snapshot Row Contract',
  '',
  `- Current top-level keys observed: ${currentSnapshotKeys.join(', ')}`,
  '- No current row contains `steps_since_*` or `structural_recency_schema_version`.',
  '',
  '## Required Delta',
  '',
  '- Add `steps_since_*` top-level fields to `uf_mdg_snapshot.py` output rows.',
  '- Add `structural_recency_schema_version` top-level field to `uf_mdg_snapshot.py` output rows.',
  '- No `runtime_decisions_latest` table DDL change is required for transport because the row is already stored inside `snapshot_row_json`.',
  '- No `runtime_decision_provenance` extractor change is required for the namespace itself because the top-level consumer already exists.',
  '',
  '## Not In Scope',
  '',
  '- No production activation',
  '- No ranking changes',
  '- No allocator changes',
].join('\n') + '\n';

const epochStateContractMd = [
  '# Epoch State Contract (Latest)',
  '',
  `- Family: ${epochStateContract.family_id}`,
  `- Parent family: ${epochStateContract.parent_family}`,
  `- Required ladder level: ${epochStateContract.required_ladder_level}`,
  '',
  '## Contract',
  '',
  '- Add top-level `regime_code`.',
  '- Add top-level `gap_state`.',
  '- Add top-level `epoch_schema_version`.',
  '- Add normalized `epoch` projection support for `epoch.company_news_catalyst` and `epoch.macro_sector_sphere_of_impact`.',
  '- Keep this contract admin/internal only. No production activation is approved in this step.',
  '',
  '## Current Code Truth',
  '',
  `- Snapshot rows with any epoch state: ${rowsWithEpochState}/${totalSnapshotRows}`,
  `- Snapshot rows with regime_code: ${rowsWithRegimeCode}/${totalSnapshotRows}`,
  `- Snapshot rows with gap_state: ${rowsWithGapState}/${totalSnapshotRows}`,
  `- Snapshot rows with epoch_schema_version: ${rowsWithEpochSchemaVersion}/${totalSnapshotRows}`,
  '- Provenance extraction is already viable because `extractEpochComponents` reads top-level `regime_code`, `gap_state`, and `row.epoch` when present.',
  '- Runtime sync does not currently join any epoch sidecar.',
  '',
  '## Recommendation',
  '',
  '- Add `regime_code` and `gap_state` through snapshot materialization, then define the epoch sidecar projection join before any family activation readiness work.',
].join('\n') + '\n';

const epochProjectionJoinContract = [
  '# Epoch Projection Join Contract (Latest)',
  '',
  '## Current State',
  '',
  '- `sync_runtime_postgres.mjs` currently reads `uf_snapshot.json` and `web/data/screener-quote-cache.json` only.',
  '- No epoch sidecar source exists in current code truth.',
  '- `runtime_decision_provenance.mjs` can already consume `regime_code`, `gap_state`, and `row.epoch` if they are present.',
  '',
  '## Required Join Contract',
  '',
  '- A future epoch registry sidecar must emit normalized epoch projections, not raw event payloads.',
  '- Required projected fields for CP-0 family gating are `epoch.company_news_catalyst`, `epoch.macro_sector_sphere_of_impact`, and `epoch_schema_version`.',
  '- Snapshot materialization remains the owner of `regime_code` and `gap_state`.',
  '- Runtime sync is the recommended projection point for sidecar-derived `epoch.*` values because it already assembles the published runtime row set.',
  '- Runtime sync must not infer epoch values. It may only project approved sidecar values into the runtime row payload.',
  '',
  '## Readiness',
  '',
  '- Snapshot transport for top-level fields: ready once fields exist.',
  '- Sidecar join: not implemented.',
  '- Public/runtime activation: blocked.',
].join('\n') + '\n';

writeJson(path.join(ROOT, 'structural_recency_contract_latest.json'), structuralRecencyContract);
writeText(path.join(ROOT, 'structural_recency_contract_latest.md'), structuralRecencyContractMd);
writeText(path.join(ROOT, 'structural_recency_schema_delta_latest.md'), structuralRecencySchemaDelta);
writeJson(path.join(ROOT, 'structural_recency_runtime_readiness_latest.json'), structuralRecencyRuntimeReadiness);
writeJson(path.join(ROOT, 'epoch_state_contract_latest.json'), epochStateContract);
writeText(path.join(ROOT, 'epoch_state_contract_latest.md'), epochStateContractMd);
writeText(path.join(ROOT, 'epoch_projection_join_contract_latest.md'), epochProjectionJoinContract);
writeJson(path.join(ROOT, 'epoch_state_runtime_readiness_latest.json'), epochStateRuntimeReadiness);
writeText(path.join(ROOT, 'quote_freshness_sla_latest.md'), quoteFreshnessSla);
writeJson(path.join(ROOT, 'quote_source_readiness_gate_latest.json'), quoteSourceReadinessGate);
writeJson(path.join(ROOT, 'quote_family_activation_blockers_latest.json'), quoteFamilyActivationBlockers);

console.log(JSON.stringify({
  status: 'ok',
  structural_recency_contract_latest_json: path.join(ROOT, 'structural_recency_contract_latest.json'),
  structural_recency_contract_latest_md: path.join(ROOT, 'structural_recency_contract_latest.md'),
  structural_recency_schema_delta_latest_md: path.join(ROOT, 'structural_recency_schema_delta_latest.md'),
  structural_recency_runtime_readiness_latest_json: path.join(ROOT, 'structural_recency_runtime_readiness_latest.json'),
  epoch_state_contract_latest_json: path.join(ROOT, 'epoch_state_contract_latest.json'),
  epoch_state_contract_latest_md: path.join(ROOT, 'epoch_state_contract_latest.md'),
  epoch_projection_join_contract_latest_md: path.join(ROOT, 'epoch_projection_join_contract_latest.md'),
  epoch_state_runtime_readiness_latest_json: path.join(ROOT, 'epoch_state_runtime_readiness_latest.json'),
  quote_freshness_sla_latest_md: path.join(ROOT, 'quote_freshness_sla_latest.md'),
  quote_source_readiness_gate_latest_json: path.join(ROOT, 'quote_source_readiness_gate_latest.json'),
  quote_family_activation_blockers_latest_json: path.join(ROOT, 'quote_family_activation_blockers_latest.json'),
}, null, 2));
