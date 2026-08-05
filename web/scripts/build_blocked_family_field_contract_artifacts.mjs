#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

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

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(filePath, value) {
  fs.writeFileSync(filePath, value, 'utf8');
}

function toPct(part, total) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total === 0) return 0;
  return Number(((part / total) * 100).toFixed(6));
}

function hoursBetween(olderIso, newerIso) {
  const older = Date.parse(olderIso);
  const newer = Date.parse(newerIso);
  if (!Number.isFinite(older) || !Number.isFinite(newer)) return null;
  return Number(((newer - older) / (1000 * 60 * 60)).toFixed(3));
}

const decomposition = readJson(path.join(ROOT, 'long_side_rulebook_decomposition_latest.json'));
const blockedMatrix = readJson(path.join(ROOT, 'long_side_subfamily_blocked_dependency_matrix_latest.json'));
const quoteCache = readJson(path.join(ROOT, 'web/data/screener-quote-cache.json'));
const snapshot = readJson(path.join(ROOT, 'uf_snapshot.json'));

const subfamilyById = new Map((decomposition.subfamilies || []).map((item) => [item.id, item]));
const blockedById = new Map((blockedMatrix.matrix || []).map((item) => [item.id, item]));

const quoteRows = quoteCache.rows || {};
const quoteSymbolsCached = Number(quoteCache.symbols_cached || Object.keys(quoteRows).length || 0);
const snapshotRows = Array.isArray(snapshot.rows) ? snapshot.rows : [];
const totalSnapshotRows = snapshotRows.length;
const quoteGeneratedAt = quoteCache.generated_at_utc || null;
const snapshotGeneratedAt = snapshot.generated_at_utc || null;
const quoteSnapshotLagHours = quoteGeneratedAt && snapshotGeneratedAt ? hoursBetween(quoteGeneratedAt, snapshotGeneratedAt) : null;

const quoteFamiliesConfig = [
  {
    id: 'valuation_protected_accumulation',
    purpose: 'Gate accumulation candidates through valuation discipline before any future governed activation.',
    parent_family: 'long_side_accumulation_hold_discipline',
    required_ladder_level: 'allow_L1_relaxed',
    exact_required_fields: ['marketCap', 'peRatio', 'forwardPE', 'priceToBook', 'priceToSales', 'evToEbitda', 'evToSales', 'pegRatio'],
    minimal_field_set_needed_to_unlock: ['marketCap', 'peRatio', 'forwardPE', 'priceToBook', 'priceToSales', 'evToEbitda', 'evToSales', 'pegRatio'],
    source_system_owner: 'quote_cache_pipeline',
    source_system_owner_paths: [
      'web/scripts/get_history_json.py:880',
      'web/scripts/get_history_json.py:903',
      'web/scripts/get_history_json.py:1037',
      'web/scripts/build_screener_quote_cache.py:20',
      'web/scripts/build_screener_quote_cache.py:528',
      'web/data/screener-quote-cache.json'
    ],
    freshness_requirement: 'Quote-cache artifact must be from the same published runtime artifact set as uf_snapshot.json; stale quote-cache relative to snapshot blocks decision-governing readiness.',
    normalization_extraction_rules: [
      'Use normalized float values emitted by get_history_json.py; no downstream string parsing is allowed.',
      'marketCap may fall back across summaryDetail, price, totalAssets, and keyStatistics in the current pipeline.',
      'pegRatio may come from keyStatistics or Yahoo timeseries trailingPegRatio if the direct field is missing.',
      'All valuation fields remain nullable in the source cache, but family admission requires non-null values for the full field set under the current strict contract.'
    ],
    runtime_exposure_class: 'admin-only',
    target_runtime_exposure_class: 'decision-governing',
    hard_soft_block_classification: 'hard-block for family admission; soft-block back to parent long-side contract when fields are missing'
  },
  {
    id: 'survivability_capital_preservation_protected_accumulation',
    purpose: 'Protect accumulation candidates with capital-preservation and survivability constraints before any governed activation.',
    parent_family: 'long_side_accumulation_hold_discipline',
    required_ladder_level: 'allow_L1_relaxed',
    exact_required_fields: ['freeCashflow', 'longTermDebtToEquity', 'currentRatio', 'quickRatio', 'cashPerShare', 'debtToEquity', 'grossMargin', 'operatingMargin', 'profitMargin'],
    minimal_field_set_needed_to_unlock: ['freeCashflow', 'longTermDebtToEquity', 'currentRatio', 'quickRatio', 'cashPerShare', 'debtToEquity', 'grossMargin', 'operatingMargin', 'profitMargin'],
    source_system_owner: 'quote_cache_pipeline',
    source_system_owner_paths: [
      'web/scripts/get_history_json.py:880',
      'web/scripts/get_history_json.py:916',
      'web/scripts/get_history_json.py:1047',
      'web/scripts/build_screener_quote_cache.py:20',
      'web/data/screener-quote-cache.json'
    ],
    freshness_requirement: 'Quote-cache artifact must be published in lockstep with the active snapshot/runtime sync run; stale quote-cache blocks activation readiness.',
    normalization_extraction_rules: [
      'Use normalized float values from the current quote-cache payload.',
      'longTermDebtToEquity may be derived from Yahoo timeseries annualLongTermDebtAndCapitalLeaseObligation and quarterlyStockholdersEquity when the direct field is missing.',
      'debtToEquity may be derived from annualTotalDebt and quarterlyStockholdersEquity when the direct field is missing.',
      'The current strict family contract requires every listed field to be non-null; partial survivability vectors do not admit the family.'
    ],
    runtime_exposure_class: 'admin-only',
    target_runtime_exposure_class: 'decision-governing',
    hard_soft_block_classification: 'hard-block for family admission; soft-block back to parent long-side contract when fields are missing'
  },
  {
    id: 'margin_quality_discipline',
    purpose: 'Constrain accumulation candidates with explicit profitability and quality discipline before any governed activation.',
    parent_family: 'long_side_accumulation_hold_discipline',
    required_ladder_level: 'allow_L1_relaxed',
    exact_required_fields: ['roe', 'roic', 'roa', 'grossMargin', 'operatingMargin', 'profitMargin'],
    minimal_field_set_needed_to_unlock: ['roe', 'roic', 'roa', 'grossMargin', 'operatingMargin', 'profitMargin'],
    source_system_owner: 'quote_cache_pipeline',
    source_system_owner_paths: [
      'web/scripts/get_history_json.py:929',
      'web/scripts/get_history_json.py:1060',
      'web/scripts/build_screener_quote_cache.py:20',
      'web/data/screener-quote-cache.json'
    ],
    freshness_requirement: 'Quote-cache artifact must remain publication-aligned with the active snapshot; stale fundamentals block decision-governing readiness.',
    normalization_extraction_rules: [
      'Use normalized float values from the quote-cache payload only.',
      'roic may be computed by the current pipeline from annual operating income, tax rate, and invested capital when direct profile fields are absent.',
      'Margins and returns remain nullable in the source cache; family admission requires the complete field set under the current strict contract.'
    ],
    runtime_exposure_class: 'admin-only',
    target_runtime_exposure_class: 'decision-governing',
    hard_soft_block_classification: 'hard-block for family admission; soft-block back to parent long-side contract when fields are missing'
  }
];

const snapshotFamiliesConfig = [
  {
    id: 'recency_sensitive_accumulation',
    purpose: 'Modulate accumulation timing using structural recency rather than compressed surrogate state.',
    parent_family: 'long_side_accumulation_hold_discipline',
    required_ladder_level: 'allow_L1_relaxed',
    exact_required_fields: ['steps_since_* top-level snapshot fields', 'structural_recency_schema_version'],
    minimal_field_set_needed_to_unlock: ['steps_since_* top-level snapshot fields'],
    source_of_truth_design: [
      {
        field: 'steps_since_* top-level snapshot fields',
        canonical_source: 'snapshot materialization',
        owner: 'uf_snapshot_builder',
        owner_paths: [
          'uf_mdg_snapshot.py:202',
          'uf_mdg_snapshot.py:228',
          'rebuild_uf_snapshot.py:54',
          'rebuild_uf_snapshot.py:699',
          'web/scripts/runtime_decision_provenance.mjs:378',
          'uf_snapshot.json'
        ]
      },
      {
        field: 'structural_recency_schema_version',
        canonical_source: 'snapshot materialization',
        owner: 'uf_snapshot_builder',
        owner_paths: [
          'uf_mdg_snapshot.py:202',
          'rebuild_uf_snapshot.py:699',
          'uf_snapshot.json'
        ]
      }
    ],
    freshness_requirement: 'Structural recency fields must be generated in the same snapshot row publication as the structural basis and provenance digest; runtime sync should transport but not derive them.',
    normalization_extraction_rules: [
      'Current decision-provenance extraction already accepts any top-level key that starts with steps_since_ or contains recency.',
      'The contract should formalize steps_since_* as the authoritative namespace and keep recency* only as legacy compatibility during migration.',
      'All recency fields must be deterministic numeric counts derived before runtime sync.'
    ],
    fallback_if_missing: 'Family remains ineligible; row falls back to the parent long-side contract with no recency-sensitive subclass.',
    hard_soft_block_classification: 'hard-block for family admission; soft-block to parent long-side contract for current CP-0 behavior',
    runtime_exposure_class: 'admin-only',
    target_runtime_exposure_class: 'decision-governing',
    exact_snapshot_schema_additions_needed: ['steps_since_* top-level fields', 'structural_recency_schema_version'],
    recommended_field_origin: 'snapshot materialization'
  },
  {
    id: 'epoch_assisted_accumulation',
    purpose: 'Allow accumulation governance to react to explicit epoch and sphere-of-impact state rather than implicit drift.',
    parent_family: 'long_side_accumulation_hold_discipline',
    required_ladder_level: 'allow_L1_relaxed',
    exact_required_fields: ['regime_code', 'gap_state', 'epoch.company_news_catalyst', 'epoch.macro_sector_sphere_of_impact', 'epoch_schema_version'],
    minimal_field_set_needed_to_unlock: ['regime_code', 'gap_state', 'epoch.company_news_catalyst', 'epoch.macro_sector_sphere_of_impact'],
    source_of_truth_design: [
      {
        field: 'regime_code',
        canonical_source: 'snapshot materialization',
        owner: 'uf_snapshot_builder',
        owner_paths: [
          'uf_mdg_snapshot.py:202',
          'rebuild_uf_snapshot.py:699',
          'web/scripts/runtime_decision_provenance.mjs:405',
          'LOAD_DIRECTIVE_NEXT_CHAT.md:206'
        ]
      },
      {
        field: 'gap_state',
        canonical_source: 'snapshot materialization',
        owner: 'uf_snapshot_builder',
        owner_paths: [
          'uf_mdg_snapshot.py:202',
          'rebuild_uf_snapshot.py:699',
          'web/scripts/runtime_decision_provenance.mjs:405',
          'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:98'
        ]
      },
      {
        field: 'epoch.company_news_catalyst',
        canonical_source: 'event/epoch registry sidecar',
        owner: 'epoch_registry_sidecar',
        owner_paths: [
          'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:100',
          'web_user_data/TFE_Specification_v2_4.tex:1733',
          'web_user_data/TFE_Specification_v2_4.tex:1747',
          'web/scripts/runtime_decision_provenance.mjs:397'
        ]
      },
      {
        field: 'epoch.macro_sector_sphere_of_impact',
        canonical_source: 'event/epoch registry sidecar',
        owner: 'epoch_registry_sidecar',
        owner_paths: [
          'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:101',
          'web_user_data/TFE_Specification_v2_4.tex:1629',
          'web_user_data/TFE_Specification_v2_4.tex:1661',
          'web/scripts/runtime_decision_provenance.mjs:397'
        ]
      },
      {
        field: 'epoch_schema_version',
        canonical_source: 'event/epoch registry sidecar',
        owner: 'epoch_registry_sidecar',
        owner_paths: [
          'L5_CURRENT_SYSTEM_FULL_SPEC.md:60',
          'L5_CURRENT_SYSTEM_FULL_SPEC.md:191'
        ]
      }
    ],
    freshness_requirement: 'Epoch fields must share the active epoch schema version and published runtime artifact set; runtime sync may join normalized epoch values, but it must not invent them.',
    normalization_extraction_rules: [
      'Current decision-provenance extraction reads top-level regime_code, gap_state, and epoch.* values from the row payload.',
      'The canonical external source for company/news/catalyst and macro/sector sphere-of-impact state should be the approved epoch registry sidecar, versioned by epoch_schema_version.',
      'Runtime sync may project normalized epoch values into runtime rows for CP-0 consumption, but raw sidecar payloads should remain external to the snapshot artifact.'
    ],
    fallback_if_missing: 'Family remains ineligible; row falls back to the parent long-side contract with no epoch-assisted subclass.',
    hard_soft_block_classification: 'hard-block for family admission; soft-block to parent long-side contract for current CP-0 behavior',
    runtime_exposure_class: 'admin-only',
    target_runtime_exposure_class: 'decision-governing',
    exact_snapshot_schema_additions_needed: ['regime_code', 'gap_state', 'epoch projection or runtime row join contract', 'epoch_schema_version'],
    recommended_field_origin: 'mixed: snapshot materialization for regime_code/gap_state, event/epoch registry sidecar for epoch.* with runtime-sync projection'
  }
];

function fieldStats(fieldName) {
  let keyPresence = 0;
  let nonNullPresence = 0;
  for (const row of Object.values(quoteRows)) {
    if (row && Object.prototype.hasOwnProperty.call(row, fieldName)) {
      keyPresence += 1;
      if (row[fieldName] !== null && row[fieldName] !== undefined) nonNullPresence += 1;
    }
  }
  return {
    field: fieldName,
    key_presence_symbols: keyPresence,
    key_presence_pct_of_cached_symbols: toPct(keyPresence, quoteSymbolsCached),
    non_null_symbols: nonNullPresence,
    non_null_pct_of_cached_symbols: toPct(nonNullPresence, quoteSymbolsCached)
  };
}

const quoteFamilyContracts = quoteFamiliesConfig.map((config) => {
  const subfamily = subfamilyById.get(config.id);
  const blocked = blockedById.get(config.id);
  if (!subfamily || !blocked) {
    throw new Error(`Missing source artifact entry for ${config.id}`);
  }

  const exactFieldStats = config.exact_required_fields.map(fieldStats);
  const availableButNotContractized = exactFieldStats.filter((item) => item.non_null_symbols > 0).map((item) => item.field);
  const trulyAbsentFromQuoteSchema = exactFieldStats.filter((item) => item.non_null_symbols === 0).map((item) => item.field);
  const keyMissingFields = exactFieldStats.filter((item) => item.key_presence_symbols < quoteSymbolsCached).map((item) => ({
    field: item.field,
    missing_key_rows: quoteSymbolsCached - item.key_presence_symbols
  }));

  const freshnessReady = quoteSnapshotLagHours !== null ? quoteSnapshotLagHours <= 0 : false;
  const sourceReady = freshnessReady && subfamily.eligible_row_count > 0;
  const extractionReady = exactFieldStats.every((item) => item.key_presence_symbols === quoteSymbolsCached && item.non_null_symbols > 0) && freshnessReady;

  return {
    id: config.id,
    track: 'A5.4Q',
    purpose: config.purpose,
    parent_family: config.parent_family,
    required_ladder_level: config.required_ladder_level,
    exact_required_fields: config.exact_required_fields,
    source_of_truth_by_field: config.exact_required_fields.map((field) => ({
      field,
      source_of_truth: {
        artifact: 'web/data/screener-quote-cache.json',
        source_system_owner: config.source_system_owner,
        source_system_owner_paths: config.source_system_owner_paths
      },
      nullability_requirement: 'non-null required for family admission',
      completeness_requirement: '100% non-null across candidate rows for decision-governing activation',
      freshness_requirement: config.freshness_requirement,
      normalization_extraction_rules: config.normalization_extraction_rules,
      current_source_statistics: fieldStats(field),
      fallback_default_behavior_if_field_missing: 'do not admit this row into the family; preserve parent long-side behavior only'
    })),
    nullability_and_completeness: {
      required_fields_nullable_in_source: true,
      family_admission_requires_non_null_for_all_required_fields: true,
      current_candidate_completeness_gate: 'strict_complete_field_set'
    },
    freshness_requirements: {
      quote_cache_generated_at_utc: quoteGeneratedAt,
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_snapshot_lag_hours: quoteSnapshotLagHours,
      ready_for_decision_governing: freshnessReady,
      requirement: config.freshness_requirement
    },
    normalization_extraction_rules: config.normalization_extraction_rules,
    fallback_default_behavior_if_field_missing: 'family remains blocked; row stays in the parent long-side family contract only',
    hard_block_vs_soft_block_classification: config.hard_soft_block_classification,
    runtime_exposure_class: config.runtime_exposure_class,
    target_runtime_exposure_class: config.target_runtime_exposure_class,
    readiness: {
      schema_ready: true,
      source_ready: sourceReady,
      extraction_ready: extractionReady,
      contract_complete: true
    },
    current_status: {
      eligible_row_count: subfamily.eligible_row_count,
      eligible_pct_of_base_population: subfamily.eligible_pct_of_base_population,
      base_population_row_count: subfamily.base_population_row_count,
      current_ladder_distribution: subfamily.current_ladder_distribution,
      primary_block_reason: blocked.primary_block_reason
    },
    current_quote_profile_fields_already_available_but_not_contractized: availableButNotContractized,
    quote_fields_truly_absent_from_current_quote_schema: trulyAbsentFromQuoteSchema,
    quote_fields_with_key_presence_gaps: keyMissingFields,
    minimal_field_set_needed_to_unlock: config.minimal_field_set_needed_to_unlock,
    expected_eligible_row_lift_if_contracts_completed_upper_bound: {
      basis: 'Upper bound under the current strict field-set gate from A5.2; this does not assume future threshold tuning.',
      currently_eligible_rows: subfamily.eligible_row_count,
      base_population_row_count: subfamily.base_population_row_count,
      additional_rows_if_full_contract_and_full_source_completeness_hold: subfamily.base_population_row_count - subfamily.eligible_row_count,
      total_eligible_rows_upper_bound: subfamily.base_population_row_count,
      additional_rows_pct_of_base_population: toPct(subfamily.base_population_row_count - subfamily.eligible_row_count, subfamily.base_population_row_count)
    },
    evidence_paths: [
      'long_side_rulebook_decomposition_latest.json',
      'long_side_subfamily_blocked_dependency_matrix_latest.json',
      ...config.source_system_owner_paths
    ]
  };
});

const snapshotFamilyContracts = snapshotFamiliesConfig.map((config) => {
  const subfamily = subfamilyById.get(config.id);
  const blocked = blockedById.get(config.id);
  if (!subfamily || !blocked) {
    throw new Error(`Missing source artifact entry for ${config.id}`);
  }

  return {
    id: config.id,
    track: 'A5.4S',
    purpose: config.purpose,
    parent_family: config.parent_family,
    required_ladder_level: config.required_ladder_level,
    exact_required_fields: config.exact_required_fields,
    source_of_truth_by_field: config.source_of_truth_design.map((item) => ({
      field: item.field,
      source_of_truth: {
        canonical_source: item.canonical_source,
        source_system_owner: item.owner,
        source_system_owner_paths: item.owner_paths
      },
      nullability_requirement: 'non-null required for family admission once the field exists',
      completeness_requirement: '100% presence across candidate rows before decision-governing activation',
      freshness_requirement: config.freshness_requirement,
      normalization_extraction_rules: config.normalization_extraction_rules,
      fallback_default_behavior_if_field_missing: config.fallback_if_missing
    })),
    nullability_and_completeness: {
      required_fields_nullable_in_source: false,
      family_admission_requires_non_null_for_all_required_fields: true,
      current_candidate_completeness_gate: 'presence_only_contract_not_yet_materialized'
    },
    freshness_requirements: {
      snapshot_generated_at_utc: snapshotGeneratedAt,
      requirement: config.freshness_requirement
    },
    normalization_extraction_rules: config.normalization_extraction_rules,
    fallback_default_behavior_if_field_missing: config.fallback_if_missing,
    hard_block_vs_soft_block_classification: config.hard_soft_block_classification,
    runtime_exposure_class: config.runtime_exposure_class,
    target_runtime_exposure_class: config.target_runtime_exposure_class,
    readiness: {
      schema_ready: false,
      source_ready: false,
      extraction_ready: false,
      contract_complete: true
    },
    current_status: {
      eligible_row_count: subfamily.eligible_row_count,
      eligible_pct_of_base_population: subfamily.eligible_pct_of_base_population,
      base_population_row_count: subfamily.base_population_row_count,
      current_ladder_distribution: subfamily.current_ladder_distribution,
      primary_block_reason: blocked.primary_block_reason
    },
    exact_snapshot_schema_additions_needed: config.exact_snapshot_schema_additions_needed,
    recommended_field_origin: config.recommended_field_origin,
    minimal_field_set_needed_to_unlock: config.minimal_field_set_needed_to_unlock,
    expected_eligible_row_lift_if_contracts_completed_upper_bound: {
      basis: 'Upper bound under the current presence-only gate from A5.2/A4.1; value thresholds are not yet approved.',
      currently_eligible_rows: subfamily.eligible_row_count,
      base_population_row_count: subfamily.base_population_row_count,
      additional_rows_if_required_fields_are_materialized: subfamily.base_population_row_count - subfamily.eligible_row_count,
      total_eligible_rows_upper_bound: subfamily.base_population_row_count,
      additional_rows_pct_of_base_population: toPct(subfamily.base_population_row_count - subfamily.eligible_row_count, subfamily.base_population_row_count)
    },
    evidence_paths: [
      'long_side_rulebook_decomposition_latest.json',
      'long_side_subfamily_blocked_dependency_matrix_latest.json',
      'web/scripts/runtime_decision_provenance.mjs:378',
      'web/scripts/runtime_decision_provenance.mjs:397',
      'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:98',
      'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:100',
      'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md:101',
      'LOAD_DIRECTIVE_NEXT_CHAT.md:206'
    ]
  };
});

const blockedFamilyFieldContracts = {
  analysis_name: 'A5_4_blocked_family_field_contracts',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  scope: 'Blocked-family contract definition only. No production activation, no ranking change, no allocator change, and no refresh/oracle/L5-learning run.',
  source_truth: [
    'long_side_rulebook_decomposition_latest.json',
    'long_side_subfamily_blocked_dependency_matrix_latest.json',
    'web/data/screener-quote-cache.json',
    'uf_snapshot.json',
    'web/scripts/get_history_json.py',
    'uf_mdg_snapshot.py',
    'rebuild_uf_snapshot.py',
    'web/scripts/runtime_decision_provenance.mjs',
    'web_user_data/TFE_5_3_Implementation_Plan_v2_4.md',
    'web_user_data/TFE_Specification_v2_4.tex',
    'L5_CURRENT_SYSTEM_FULL_SPEC.md',
    'LOAD_DIRECTIVE_NEXT_CHAT.md'
  ],
  quote_field_track: {
    id: 'A5.4Q',
    priority: 1,
    families: quoteFamilyContracts,
    summary: {
      quote_cache_generated_at_utc: quoteGeneratedAt,
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_snapshot_lag_hours: quoteSnapshotLagHours,
      quote_symbols_cached: quoteSymbolsCached,
      quote_fields_are_schema_present_but_sparse: true,
      required_quote_fields_absent_from_schema: []
    }
  },
  snapshot_event_track: {
    id: 'A5.4S',
    priority: 2,
    families: snapshotFamilyContracts,
    summary: {
      snapshot_generated_at_utc: snapshotGeneratedAt,
      runtime_provenance_recency_consumer_exists: true,
      runtime_provenance_epoch_consumer_exists: true,
      current_snapshot_schema_missing_recency_epoch_fields: true,
      epoch_microprobe_evidence: {
        source: 'LOAD_DIRECTIVE_NEXT_CHAT.md:206',
        structural_recency_removed_flip: 0.7,
        regime_code_removed_flip: 0.0125,
        gap_removed_flip: 0.0125
      }
    }
  },
  recommendation: {
    recommended_next_step: 'further_A5.4S_work',
    rationale: 'Quote-family contracts are now explicit, but current quote/source readiness remains poor: required fields are schema-defined yet mostly null, and the active quote cache is older than the active snapshot. Structural recency contract work appears lower effort and higher ROI because the missing fields are inside the local snapshot/runtime path and A2 evidence already shows structural recency dominates epoch-feature sensitivity.',
    why_not_A5_5_now: 'Admin/internal activation readiness for quote-field families would formalize families whose source completeness and freshness are still materially unready.'
  }
};

const quoteFieldContracts = {
  analysis_name: 'A5_4Q_quote_field_contracts',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  quote_cache_context: {
    generated_at_utc: quoteGeneratedAt,
    source_snapshot: quoteCache.source_snapshot || null,
    symbols_cached: quoteSymbolsCached,
    symbols_total: Number(quoteCache.symbols_total || quoteSymbolsCached),
    active_snapshot_generated_at_utc: snapshotGeneratedAt,
    quote_snapshot_lag_hours: quoteSnapshotLagHours
  },
  families: quoteFamilyContracts
};

const snapshotEventContracts = {
  analysis_name: 'A5_4S_snapshot_event_contracts',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  snapshot_context: {
    generated_at_utc: snapshotGeneratedAt,
    total_snapshot_rows: totalSnapshotRows,
    current_snapshot_row_contract_has_no_recency_fields: true,
    current_snapshot_row_contract_has_no_epoch_fields: true
  },
  families: snapshotFamilyContracts
};

const blockedFamilyReadiness = {
  analysis_name: 'A5_4_blocked_family_readiness',
  generated_at_utc: GENERATED_AT,
  status: 'admin_internal_contract_work_only',
  cp_profile: 'CP-0',
  families: [...quoteFamilyContracts, ...snapshotFamilyContracts].map((family) => ({
    id: family.id,
    track: family.track,
    required_ladder_level: family.required_ladder_level,
    readiness: family.readiness,
    current_status: family.current_status,
    expected_eligible_row_lift_if_contracts_completed_upper_bound: family.expected_eligible_row_lift_if_contracts_completed_upper_bound
  })),
  recommendation: blockedFamilyFieldContracts.recommendation
};

function markdownForContracts(allContracts, quoteContracts, snapshotContracts, readiness) {
  const lines = [];
  lines.push('# Blocked Family Field Contracts (Latest)');
  lines.push('');
  lines.push(`- Generated at UTC: ${allContracts.generated_at_utc}`);
  lines.push(`- Scope: ${allContracts.scope}`);
  lines.push(`- Quote cache generated_at_utc: ${quoteGeneratedAt}`);
  lines.push(`- Snapshot generated_at_utc: ${snapshotGeneratedAt}`);
  lines.push(`- Quote-to-snapshot lag hours: ${quoteSnapshotLagHours}`);
  lines.push('');
  lines.push('## A5.4Q Quote-Field Contracts');
  lines.push('');
  for (const family of quoteContracts.families) {
    lines.push(`### ${family.id}`);
    lines.push(`- Purpose: ${family.purpose}`);
    lines.push(`- Parent family: ${family.parent_family}`);
    lines.push(`- Required ladder level: ${family.required_ladder_level}`);
    lines.push(`- Current eligible rows: ${family.current_status.eligible_row_count} / ${family.current_status.base_population_row_count}`);
    lines.push(`- Primary block: ${family.current_status.primary_block_reason.key} (${family.current_status.primary_block_reason.count})`);
    lines.push(`- Minimal field set to unlock: ${family.minimal_field_set_needed_to_unlock.join(', ')}`);
    lines.push(`- Available but not contractized: ${family.current_quote_profile_fields_already_available_but_not_contractized.join(', ') || 'none'}`);
    lines.push(`- Truly absent from quote schema: ${family.quote_fields_truly_absent_from_current_quote_schema.join(', ') || 'none'}`);
    lines.push(`- Readiness: schema=${family.readiness.schema_ready ? 'ready' : 'not ready'}, source=${family.readiness.source_ready ? 'ready' : 'not ready'}, extraction=${family.readiness.extraction_ready ? 'ready' : 'not ready'}, contract=${family.readiness.contract_complete ? 'complete' : 'incomplete'}`);
    lines.push(`- Expected eligible-row lift upper bound: +${family.expected_eligible_row_lift_if_contracts_completed_upper_bound.additional_rows_if_full_contract_and_full_source_completeness_hold}`);
    lines.push('');
  }
  lines.push('## A5.4S Snapshot/Event Contracts');
  lines.push('');
  for (const family of snapshotContracts.families) {
    lines.push(`### ${family.id}`);
    lines.push(`- Purpose: ${family.purpose}`);
    lines.push(`- Parent family: ${family.parent_family}`);
    lines.push(`- Required ladder level: ${family.required_ladder_level}`);
    lines.push(`- Current eligible rows: ${family.current_status.eligible_row_count} / ${family.current_status.base_population_row_count}`);
    lines.push(`- Primary block: ${family.current_status.primary_block_reason.key} (${family.current_status.primary_block_reason.count})`);
    lines.push(`- Exact snapshot schema additions needed: ${family.exact_snapshot_schema_additions_needed.join(', ')}`);
    lines.push(`- Recommended field origin: ${family.recommended_field_origin}`);
    lines.push(`- Minimal field set to unlock: ${family.minimal_field_set_needed_to_unlock.join(', ')}`);
    lines.push(`- Readiness: schema=${family.readiness.schema_ready ? 'ready' : 'not ready'}, source=${family.readiness.source_ready ? 'ready' : 'not ready'}, extraction=${family.readiness.extraction_ready ? 'ready' : 'not ready'}, contract=${family.readiness.contract_complete ? 'complete' : 'incomplete'}`);
    lines.push(`- Expected eligible-row lift upper bound: +${family.expected_eligible_row_lift_if_contracts_completed_upper_bound.additional_rows_if_required_fields_are_materialized}`);
    lines.push('');
  }
  lines.push('## Recommendation');
  lines.push('');
  lines.push(`- Recommended next step: ${readiness.recommendation.recommended_next_step}`);
  lines.push(`- Rationale: ${readiness.recommendation.rationale}`);
  lines.push(`- Why not A5.5 now: ${readiness.recommendation.why_not_A5_5_now}`);
  lines.push('');
  lines.push('## Safe Scope Checks');
  lines.push('');
  lines.push('- No production behavior activation');
  lines.push('- No ranking changes');
  lines.push('- No allocator changes');
  lines.push('- No refresh/oracle/L5-learning run');
  return `${lines.join('\n')}\n`;
}

writeJson(path.join(ROOT, 'blocked_family_field_contracts_latest.json'), blockedFamilyFieldContracts);
writeJson(path.join(ROOT, 'quote_field_contracts_latest.json'), quoteFieldContracts);
writeJson(path.join(ROOT, 'snapshot_event_contracts_latest.json'), snapshotEventContracts);
writeJson(path.join(ROOT, 'blocked_family_readiness_latest.json'), blockedFamilyReadiness);
writeText(path.join(ROOT, 'blocked_family_field_contracts_latest.md'), markdownForContracts(blockedFamilyFieldContracts, quoteFieldContracts, snapshotEventContracts, blockedFamilyReadiness));

console.log(JSON.stringify({
  status: 'ok',
  blocked_family_field_contracts_latest_json: path.join(ROOT, 'blocked_family_field_contracts_latest.json'),
  blocked_family_field_contracts_latest_md: path.join(ROOT, 'blocked_family_field_contracts_latest.md'),
  quote_field_contracts_latest_json: path.join(ROOT, 'quote_field_contracts_latest.json'),
  snapshot_event_contracts_latest_json: path.join(ROOT, 'snapshot_event_contracts_latest.json'),
  blocked_family_readiness_latest_json: path.join(ROOT, 'blocked_family_readiness_latest.json')
}, null, 2));
