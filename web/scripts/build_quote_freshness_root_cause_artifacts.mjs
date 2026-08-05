#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const ROOT = '/workspaces/Tao_Financial_Engine';
const GENERATED_AT = new Date().toISOString();
const VALIDATION_MAX_AGE_HOURS = 30;

function parseJsonLike(text) {
  return JSON.parse(
    String(text)
      .replace(/\bNaN\b/g, 'null')
      .replace(/\b-Infinity\b/g, 'null')
      .replace(/\bInfinity\b/g, 'null')
  );
}

function readJson(filePath) {
  return parseJsonLike(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function statUtc(filePath) {
  return fs.statSync(filePath).mtime.toISOString();
}

function sha256(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(filePath, value) {
  fs.writeFileSync(filePath, `${value}\n`, 'utf8');
}

function toIsoOrNull(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const ms = Date.parse(text);
  if (!Number.isFinite(ms)) return null;
  return new Date(ms).toISOString();
}

function hoursBetween(olderIso, newerIso) {
  const older = Date.parse(String(olderIso || ''));
  const newer = Date.parse(String(newerIso || ''));
  if (!Number.isFinite(older) || !Number.isFinite(newer)) return null;
  return Number(((newer - older) / 3600000).toFixed(3));
}

function uniqueTickerCount(rows) {
  const set = new Set();
  for (const row of Array.isArray(rows) ? rows : []) {
    const ticker = String(row?.ticker ?? '').trim().toUpperCase();
    if (ticker) set.add(ticker);
  }
  return set.size;
}

function hasField(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj || {}, key);
}

function evidence(pathRef, detail) {
  return { path: pathRef, detail };
}

function lines(items) {
  return items.join('\n');
}

const snapshotPath = path.join(ROOT, 'uf_snapshot.json');
const quotePath = path.join(ROOT, 'web', 'data', 'screener-quote-cache.json');
const quoteFailuresPath = path.join(ROOT, 'web', 'data', 'screener-quote-cache.failures.json');
const refreshStatusPath = path.join(ROOT, 'admin_refresh_status.json');
const rebuildReportPath = path.join(ROOT, 'uf_snapshot_rebuild_report.json');
const refreshLogPath = path.join(ROOT, 'admin_refresh_latest.log');
const sourceReadinessPath = path.join(ROOT, 'quote_source_readiness_gate_latest.json');
const familyBlockersPath = path.join(ROOT, 'quote_family_activation_blockers_latest.json');

const snapshot = readJson(snapshotPath);
const quoteCache = readJson(quotePath);
const quoteFailures = readJson(quoteFailuresPath);
const refreshStatus = readJson(refreshStatusPath);
const rebuildReport = readJson(rebuildReportPath);
const sourceReadiness = readJson(sourceReadinessPath);
const familyBlockers = readJson(familyBlockersPath);
const refreshLogText = readText(refreshLogPath);

const snapshotGeneratedAt = toIsoOrNull(snapshot.generated_at_utc);
const quoteGeneratedAt = toIsoOrNull(quoteCache.generated_at_utc);
const refreshStatusStartedAt = toIsoOrNull(refreshStatus.started_at);
const refreshStatusCompletedAt = toIsoOrNull(refreshStatus.completed_at);
const refreshStatusReportGeneratedAt = toIsoOrNull(refreshStatus.report_generated_at_utc);
const rebuildReportGeneratedAt = toIsoOrNull(rebuildReport.generated_at_utc);

const snapshotRowCount = Array.isArray(snapshot.rows) ? snapshot.rows.length : 0;
const snapshotUniqueTickerCount = uniqueTickerCount(snapshot.rows);
const quoteSymbolCount = Number(quoteCache.symbols_cached || 0);
const quoteSymbolTotal = Number(quoteCache.symbols_total || 0);
const quoteLagVsSnapshotHours = hoursBetween(quoteGeneratedAt, snapshotGeneratedAt);
const quoteAgeHoursNow = hoursBetween(quoteGeneratedAt, GENERATED_AT);
const snapshotAgeHoursNow = hoursBetween(snapshotGeneratedAt, GENERATED_AT);
const refreshLogHasMarchSnapshot = refreshLogText.includes('2026-03-06') || refreshLogText.includes('2026-03-06T');
const publicationIdsPresent = {
  snapshot_run_id: hasField(snapshot, 'run_id'),
  snapshot_publication_id: hasField(snapshot, 'publication_id'),
  quote_run_id: hasField(quoteCache, 'run_id'),
  quote_publication_id: hasField(quoteCache, 'publication_id'),
  quote_source_snapshot_publication_id: hasField(quoteCache, 'source_snapshot_publication_id'),
};
const publicationIdentityPresent = Object.values(publicationIdsPresent).every(Boolean);
const sourceSnapshotPathMatch = String(quoteCache.source_snapshot || '') === snapshotPath;

const separateServingTimestampIssue = {
  id: 'runtime_sync_timestamp_source_mismatch',
  helpful: true,
  scope: 'serving_status_only',
  current_workspace_patch_present: true,
  deployed: false,
  effect: 'Recommendations and Portfolio can appear stale when runtime sync stamps rows with rebuild-report generated_at_utc instead of snapshot payload generated_at_utc.',
  evidence_paths: [
    evidence('web/scripts/sync_runtime_postgres.mjs:220-253', 'resolveGeneratedAt now prefers snapshot payload generated_at_utc, records generated_at_source, and flags timestampMismatch.'),
    evidence('web/scripts/sync_runtime_postgres.mjs:632-633', 'Runtime sync uses resolveGeneratedAt for the effective generatedAtUtc stamp.'),
    evidence('web/scripts/sync_runtime_postgres.mjs:1069-1072', 'Sync summary now exposes generated_at_source, snapshot_generated_at_utc, report_generated_at_utc, and timestamp_mismatch_detected.'),
    evidence('uf_snapshot.json', 'Active snapshot generated_at_utc is 2026-03-06T15:45:02Z.'),
    evidence('uf_snapshot_rebuild_report.json', 'Rebuild report generated_at_utc is 2026-03-01T14:32:22.314353Z.'),
  ],
  interpretation: 'This is separate from the stale quote artifact. It explains false stale badges in serving surfaces but does not repair quote publication alignment.',
};

const publicationAlignment = {
  analysis_name: 'Q1_quote_publication_alignment',
  generated_at_utc: GENERATED_AT,
  cp_profile: 'CP-0',
  active_snapshot: {
    path: snapshotPath,
    sha256: sha256(snapshotPath),
    generated_at_utc: snapshotGeneratedAt,
    mtime_utc: statUtc(snapshotPath),
    row_count: snapshotRowCount,
    unique_ticker_count: snapshotUniqueTickerCount,
    run_id: snapshot.run_id ?? null,
    publication_id: snapshot.publication_id ?? null,
  },
  active_quote_cache: {
    path: quotePath,
    sha256: sha256(quotePath),
    generated_at_utc: quoteGeneratedAt,
    mtime_utc: statUtc(quotePath),
    source_snapshot: quoteCache.source_snapshot ?? null,
    symbols_cached: quoteSymbolCount,
    symbols_total: quoteSymbolTotal,
    run_id: quoteCache.run_id ?? null,
    publication_id: quoteCache.publication_id ?? null,
    source_snapshot_publication_id: quoteCache.source_snapshot_publication_id ?? null,
  },
  checks: {
    source_snapshot_path_match: sourceSnapshotPathMatch,
    quote_generated_after_snapshot: quoteGeneratedAt !== null && snapshotGeneratedAt !== null ? quoteGeneratedAt >= snapshotGeneratedAt : false,
    quote_age_within_validation_window: quoteAgeHoursNow !== null ? quoteAgeHoursNow <= VALIDATION_MAX_AGE_HOURS : false,
    publication_identity_present: publicationIdentityPresent,
    runtime_sync_reads_active_quote_path: true,
  },
  metrics: {
    quote_lag_vs_snapshot_hours: quoteLagVsSnapshotHours,
    quote_age_hours_now: quoteAgeHoursNow,
    snapshot_age_hours_now: snapshotAgeHoursNow,
  },
  verdict: {
    publication_alignment_pass: false,
    status: 'failed',
    reasons: [
      'active_snapshot_is_newer_than_active_quote_publication',
      'quote_age_exceeds_validation_window',
      'publication_identity_metadata_missing',
    ],
  },
  separate_serving_status_issue: separateServingTimestampIssue,
  evidence_paths: [
    evidence('web/scripts/sync_runtime_postgres.mjs:615-637', 'Runtime sync is hard-bound to uf_snapshot.json and web/data/screener-quote-cache.json.'),
    evidence('web/src/lib/screener-quote-cache.ts:48-56', 'Runtime quote loader candidate set includes the active repo-local path.'),
    evidence('web/src/lib/screener-quote-cache.ts:116-130', 'The first readable candidate becomes the active cache source.'),
    evidence('uf_snapshot.json', 'Active snapshot generated_at_utc is 2026-03-06T15:45:02Z.'),
    evidence('web/data/screener-quote-cache.json', 'Active quote cache generated_at_utc is 2026-02-28T04:07:55.837488+00:00.'),
  ],
};

const questionAnswers = [
  {
    id: 'did_quote_refresh_execute_for_active_snapshot_run',
    answer: 'not_provable_from_current_artifacts',
    current_behavior: 'The active snapshot publication is dated 2026-03-06T15:45:02Z, but the active quote artifact is still dated 2026-02-28T04:07:55.837488+00:00. Local refresh bookkeeping artifacts do not show a matching March 6 quote refresh or aligned publication record.',
    expected_behavior: 'The refresh wrapper should rebuild the snapshot, then run quote cache refresh, then publish aligned artifacts for the same refresh/publication boundary.',
    timestamps: {
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_generated_at_utc: quoteGeneratedAt,
      refresh_status_started_at_utc: refreshStatusStartedAt,
      refresh_status_completed_at_utc: refreshStatusCompletedAt,
      refresh_status_report_generated_at_utc: refreshStatusReportGeneratedAt,
      rebuild_report_generated_at_utc: rebuildReportGeneratedAt,
    },
    run_ids_or_publication_ids: {
      snapshot_run_id: snapshot.run_id ?? null,
      snapshot_publication_id: snapshot.publication_id ?? null,
      quote_run_id: quoteCache.run_id ?? null,
      quote_publication_id: quoteCache.publication_id ?? null,
    },
    evidence_paths: [
      evidence('run_refresh_with_l5_learning.py:960-972', 'Code truth says quote cache refresh should run immediately after snapshot rebuild.'),
      evidence('L5_CURRENT_SYSTEM_FULL_SPEC.md:49-62', 'Spec/code-truth sequence requires quote cache refresh before runtime sync.'),
      evidence('admin_refresh_status.json', 'Current bookkeeping content points to an older run and does not identify a March 6 quote refresh.'),
      evidence('uf_snapshot_rebuild_report.json', 'Current rebuild report generated_at_utc is 2026-03-01T14:32:22.314353Z, not March 6.'),
      evidence('admin_refresh_latest.log', refreshLogHasMarchSnapshot ? 'Refresh log contains March 6 publication evidence.' : 'Refresh log tail does not contain March 6 publication evidence.'),
    ],
  },
  {
    id: 'was_resulting_quote_artifact_published',
    answer: 'no_evidence_of_publication_to_active_path',
    current_behavior: 'The active quote artifact at web/data/screener-quote-cache.json still carries a February 28 publication timestamp.',
    expected_behavior: 'Any successful quote refresh against the active snapshot should republish the active quote path and advance generated_at_utc, even when there are zero pending symbols.',
    timestamps: {
      quote_generated_at_utc: quoteGeneratedAt,
      quote_failures_generated_at_utc: toIsoOrNull(quoteFailures.generated_at_utc),
      quote_file_mtime_utc: statUtc(quotePath),
    },
    run_ids_or_publication_ids: {
      quote_run_id: quoteCache.run_id ?? null,
      quote_publication_id: quoteCache.publication_id ?? null,
      source_snapshot_publication_id: quoteCache.source_snapshot_publication_id ?? null,
    },
    evidence_paths: [
      evidence('web/scripts/build_screener_quote_cache.py:556-567', 'Quote builder republishes the active output file with a fresh generated_at_utc.'),
      evidence('web/scripts/build_screener_quote_cache.py:700-705', 'Builder republishes even when pending=0.'),
      evidence('web/data/screener-quote-cache.json', 'The active quote artifact timestamp did not advance to match the March 6 snapshot publication.'),
    ],
  },
  {
    id: 'is_runtime_sync_selecting_the_wrong_quote_artifact',
    answer: 'no',
    current_behavior: 'Runtime sync and the quote-cache loader both resolve to the repo-local active quote path. A separate workspace patch exists for serving timestamp resolution, but that affects stale badges, not quote file selection.',
    expected_behavior: 'Runtime should bind to the active published quote artifact; the issue here is that the active artifact is stale, not that runtime selected an unintended file.',
    timestamps: {
      active_quote_generated_at_utc: quoteGeneratedAt,
      active_snapshot_generated_at_utc: snapshotGeneratedAt,
      snapshot_report_generated_at_utc: rebuildReportGeneratedAt,
    },
    run_ids_or_publication_ids: {
      quote_publication_id: quoteCache.publication_id ?? null,
      snapshot_publication_id: snapshot.publication_id ?? null,
    },
    evidence_paths: [
      evidence('web/scripts/sync_runtime_postgres.mjs:615-637', 'Runtime sync reads web/data/screener-quote-cache.json directly.'),
      evidence('web/src/lib/screener-quote-cache.ts:48-56', 'Quote loader candidate order includes the same active path.'),
      evidence('web/src/lib/screener-quote-cache.ts:116-130', 'Loader returns the first readable populated cache file.'),
      evidence('web/scripts/sync_runtime_postgres.mjs:220-253', 'Separate serving timestamp fix exists in workspace and is orthogonal to quote artifact selection.'),
    ],
  },
  {
    id: 'are_snapshot_and_quote_cache_from_different_run_ids_or_publication_ids',
    answer: 'identity_not_provable_metadata_missing_publication_times_diverge',
    current_behavior: 'The quote artifact references the active snapshot path but neither artifact carries run_id or publication_id fields needed to prove same-publication lineage. The timestamps diverge by 155.618 hours.',
    expected_behavior: 'Snapshot and quote artifacts should carry explicit run_id/publication_id binding so same-publication lineage is machine-checkable.',
    timestamps: {
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_generated_at_utc: quoteGeneratedAt,
      lag_hours: quoteLagVsSnapshotHours,
    },
    run_ids_or_publication_ids: {
      snapshot_run_id: snapshot.run_id ?? null,
      snapshot_publication_id: snapshot.publication_id ?? null,
      quote_run_id: quoteCache.run_id ?? null,
      quote_publication_id: quoteCache.publication_id ?? null,
      quote_source_snapshot_publication_id: quoteCache.source_snapshot_publication_id ?? null,
    },
    evidence_paths: [
      evidence('uf_snapshot.json', 'Snapshot publication identity fields are absent.'),
      evidence('web/data/screener-quote-cache.json', 'Quote publication identity fields are absent; only source_snapshot path is present.'),
    ],
  },
  {
    id: 'what_is_causing_the_stale_condition',
    answer: 'primary_publication_alignment_failure_secondary_refresh_bookkeeping_gap_with_separate_serving_timestamp_bug',
    current_behavior: 'The active snapshot is newer than the active quote publication, runtime is reading the correct active quote path, and the artifact pair lacks publication identity fields. Refresh bookkeeping does not trace the active snapshot publication. Separately, sync timestamp-source mismatch can make serving surfaces look stale even when data is fresh.',
    expected_behavior: 'Publication alignment should be explicit and enforced; quote-family eligibility should fail closed when quote publication lags snapshot publication or lineage cannot be proven. Serving surfaces should stamp runtime rows with the true snapshot publication time.',
    timestamps: {
      snapshot_generated_at_utc: snapshotGeneratedAt,
      quote_generated_at_utc: quoteGeneratedAt,
      rebuild_report_generated_at_utc: rebuildReportGeneratedAt,
      lag_hours: quoteLagVsSnapshotHours,
      quote_age_hours_now: quoteAgeHoursNow,
    },
    run_ids_or_publication_ids: {
      snapshot_run_id: snapshot.run_id ?? null,
      snapshot_publication_id: snapshot.publication_id ?? null,
      quote_run_id: quoteCache.run_id ?? null,
      quote_publication_id: quoteCache.publication_id ?? null,
    },
    cause_classification: {
      producer_failure: 'not_proven',
      scheduler_failure: 'not_proven',
      publication_selection_failure: 'primary',
      runtime_read_path_failure: 'ruled_out_as_primary_for_quote_selection',
      timestamp_timezone_mismatch: 'ruled_out_as_primary',
      validation_threshold_mismatch: 'ruled_out_as_primary',
      refresh_bookkeeping_gap: 'secondary',
      serving_timestamp_source_mismatch: 'separate_parallel_issue',
    },
    evidence_paths: [
      evidence('quote_source_readiness_gate_latest.json', 'Current source readiness already shows publication_alignment_with_snapshot=false and quote_age_within_validation_window=false.'),
      evidence('admin_refresh_status.json', 'Refresh bookkeeping content does not line up with the active March 6 snapshot publication.'),
      evidence('admin_refresh_latest.log', 'Local refresh log is from February 20 and does not document the active publication chain.'),
      evidence('web/scripts/sync_runtime_postgres.mjs:220-253', 'Separate workspace patch proves a runtime sync timestamp-source defect affecting serving freshness.'),
    ],
  },
];

const rootCause = {
  analysis_name: 'Q1_quote_freshness_root_cause_audit',
  generated_at_utc: GENERATED_AT,
  status: 'audit_complete_no_runtime_behavior_change',
  cp_profile: 'CP-0',
  active_artifacts: {
    snapshot: publicationAlignment.active_snapshot,
    quote_cache: publicationAlignment.active_quote_cache,
    quote_failures: {
      path: quoteFailuresPath,
      generated_at_utc: toIsoOrNull(quoteFailures.generated_at_utc),
      mtime_utc: statUtc(quoteFailuresPath),
      failure_count: Number(quoteFailures.failure_count || 0),
    },
    refresh_status: {
      path: refreshStatusPath,
      mtime_utc: statUtc(refreshStatusPath),
      requested_mode: refreshStatus.requested_mode ?? null,
      started_at_utc: refreshStatusStartedAt,
      completed_at_utc: refreshStatusCompletedAt,
      report_generated_at_utc: refreshStatusReportGeneratedAt,
      last_report_status: refreshStatus.last_report?.status ?? null,
      last_report_rows_written: refreshStatus.last_report?.rows_written ?? null,
    },
    rebuild_report: {
      path: rebuildReportPath,
      mtime_utc: statUtc(rebuildReportPath),
      generated_at_utc: rebuildReportGeneratedAt,
      refresh_mode: rebuildReport.refresh_mode ?? null,
      rows_written: rebuildReport.rows_written ?? null,
      status: rebuildReport.status ?? null,
    },
    refresh_log: {
      path: refreshLogPath,
      mtime_utc: statUtc(refreshLogPath),
      contains_march_6_publication_evidence: refreshLogHasMarchSnapshot,
    },
  },
  metrics: {
    snapshot_row_count: snapshotRowCount,
    snapshot_unique_ticker_count: snapshotUniqueTickerCount,
    quote_symbols_cached: quoteSymbolCount,
    quote_symbols_total: quoteSymbolTotal,
    quote_lag_vs_snapshot_hours: quoteLagVsSnapshotHours,
    quote_age_hours_now: quoteAgeHoursNow,
    validation_max_age_hours: VALIDATION_MAX_AGE_HOURS,
  },
  q1_answers: questionAnswers,
  diagnosis: {
    primary_root_cause: 'publication_alignment_failure',
    supporting_root_cause: 'refresh_bookkeeping_gap',
    separate_serving_status_issue: separateServingTimestampIssue,
    ruled_out_as_primary: [
      'runtime_read_path_failure_for_quote_selection',
      'timestamp_timezone_mismatch',
      'validation_threshold_mismatch',
    ],
    unresolved_without_further_run_lineage: [
      'producer_failure',
      'scheduler_failure',
    ],
  },
  recommendation: {
    explicit_recommendation: 'fix_publication_alignment_now',
    why: 'The runtime is reading the correct active quote file, but that file was not republished for the active snapshot publication and there is no publication identity contract to prove same-run lineage. The serving timestamp bug should be handled separately.',
  },
};

const quotePublicationContract = lines([
  '# Quote Publication Contract (Latest)',
  '',
  '## Purpose',
  '',
  'Define the minimum publication identity and alignment rules required before quote-governed families may become eligible.',
  '',
  '## Required artifact identity fields',
  '',
  'Snapshot artifact (`uf_snapshot.json`) must publish:',
  '- `generated_at_utc`',
  '- `refresh_run_id`',
  '- `snapshot_publication_id`',
  '- `snapshot_digest_sha256`',
  '',
  'Quote artifact (`web/data/screener-quote-cache.json`) must publish:',
  '- `generated_at_utc`',
  '- `refresh_run_id`',
  '- `quote_publication_id`',
  '- `quote_digest_sha256`',
  '- `source_snapshot_publication_id`',
  '- `source_snapshot_digest_sha256`',
  '',
  '## Required alignment rules',
  '',
  '- Quote-family eligibility requires `source_snapshot_publication_id == snapshot_publication_id`.',
  '- Quote-family eligibility requires `source_snapshot_digest_sha256 == snapshot_digest_sha256`.',
  '- Quote-family eligibility requires `quote.generated_at_utc >= snapshot.generated_at_utc`.',
  '- Quote-family eligibility requires quote age to remain within the freshness SLA.',
  '',
  '## Allowed mismatch behavior',
  '',
  '- If publication identity is missing, quote-governed families fail closed.',
  '- If publication identity mismatches, quote-governed families fail closed.',
  '- If quote freshness fails, quote-governed families fail closed.',
  '- Non-quote families remain unaffected.',
  '- Serving-status timestamp bugs must not be treated as proof of quote publication freshness.',
  '',
  '## Runtime obligations',
  '',
  '- Runtime sync may continue to read the active quote artifact path.',
  '- Runtime sync must persist the active quote publication identity beside any quote-governed readiness status once this contract is implemented.',
  '- Admin/internal surfaces must show the exact block reason: `quote_publication_alignment_failed`, `quote_publication_identity_missing`, or `quote_age_exceeded_sla`.',
  '',
  '## Current gap',
  '',
  'Current active artifacts expose `generated_at_utc` and `source_snapshot` path only. They do not expose publication identity fields, so same-publication lineage cannot be proved today.',
]);

const quoteSla = lines([
  '# Quote Freshness SLA (Latest)',
  '',
  '## Basis',
  '',
  '- Refresh wrapper order in current code truth: snapshot rebuild -> quote cache refresh -> profile override refresh -> runtime sync -> validation gate.',
  `- Validation freshness gate default: \`TFE_VALIDATION_MAX_AGE_HOURS = ${VALIDATION_MAX_AGE_HOURS}\`.`,
  '- Runtime Postgres cache TTL default: `60000 ms`.',
  '- Runtime Postgres max stale fallback default: `900000 ms` (15 minutes).',
  '',
  '## SLA',
  '',
  '- Quote-governed families require publication alignment with the active snapshot publication.',
  `- Quote-governed families require quote age <= ${VALIDATION_MAX_AGE_HOURS} hours.`,
  '- A matching file path is not sufficient. Same-publication identity must be present and match.',
  '- The 15-minute stale-cache fallback is a transient runtime read allowance only. It does not permit quote-family eligibility.',
  '- A serving-surface timestamp mismatch does not clear a stale quote publication.',
  '',
  '## Current observed state',
  '',
  `- Active snapshot generated_at_utc: ${snapshotGeneratedAt}`,
  `- Active quote generated_at_utc: ${quoteGeneratedAt}`,
  `- Active rebuild report generated_at_utc: ${rebuildReportGeneratedAt}`,
  `- Quote lag behind snapshot: ${quoteLagVsSnapshotHours} hours`,
  `- Quote age versus now: ${quoteAgeHoursNow} hours`,
  `- Quote path matches active snapshot path reference: ${sourceSnapshotPathMatch}`,
  `- Publication identity present on both artifacts: ${publicationIdentityPresent}`,
  '',
  '## Fail-closed rules',
  '',
  '- If quote publication is older than snapshot publication, quote-governed families are blocked.',
  '- If publication identity fields are missing, quote-governed families are blocked.',
  `- If quote age exceeds ${VALIDATION_MAX_AGE_HOURS} hours, quote-governed families are blocked.`,
  '- Non-quote families remain unaffected.',
  '',
  '## Current conclusion',
  '',
  'Quote-family activation remains blocked until publication alignment is fixed. Serving freshness bugs should be remediated in parallel but not used to waive the quote block.',
]);

const remediationPlan = lines([
  '# Quote Freshness Remediation Plan (Latest)',
  '',
  '## Goal',
  '',
  'Fix quote publication alignment without changing ranking, allocator semantics, or non-quote family behavior.',
  '',
  '## Recommended fix',
  '',
  'Fix publication alignment now.',
  '',
  '## Why this is the recommended option',
  '',
  '- Runtime is reading the intended active quote file.',
  '- The active quote file was not republished for the active snapshot publication.',
  '- The current artifact contract cannot prove same-publication lineage because publication identity metadata is missing.',
  '- The separate sync timestamp bug is real but orthogonal; fixing it does not refresh the quote artifact.',
  '',
  '## Safe remediation scope',
  '',
  '1. Add publication identity fields to snapshot and quote artifacts.',
  '2. Bind quote publication to snapshot publication at write time.',
  '3. Fail closed for quote-governed family eligibility when publication identity is missing or mismatched.',
  '4. Leave ranking, allocator behavior, and non-quote families unchanged.',
  '',
  '## Concrete implementation target',
  '',
  '- Snapshot publisher writes `refresh_run_id`, `snapshot_publication_id`, and `snapshot_digest_sha256`.',
  '- Quote publisher writes `refresh_run_id`, `quote_publication_id`, `source_snapshot_publication_id`, and `source_snapshot_digest_sha256`.',
  '- Runtime/admin readiness checks block quote families when snapshot/quote publication IDs differ or quote timestamp predates snapshot timestamp.',
  '- Refresh bookkeeping records quote publish outcome for the same publication boundary.',
  '- Keep the separate sync timestamp-source fix isolated to serving freshness semantics.',
  '',
  '## Not recommended as first fix',
  '',
  '- Adding freshness heuristics without publication identity.',
  '- Treating runtime read-path selection as the primary failure.',
  '- Treating the serving timestamp bug as proof that quote freshness is already solved.',
  '- Activating quote families before publication alignment and freshness pass.',
  '',
  '## Optional safe implementation status',
  '',
  'No code fix was applied in this audit step. The obvious problem is publication alignment, but the safe production fix should add publication identity and fail-closed checks together rather than patching only one symptom.',
]);

const activationBlocks = {
  analysis_name: 'Q3_quote_freshness_activation_blocks',
  generated_at_utc: GENERATED_AT,
  cp_profile: 'CP-0',
  quote_family_activation_globally_blocked: true,
  explicit_recommendation: 'fix_publication_alignment_now',
  global_blockers: [
    {
      id: 'quote_publication_alignment_failed',
      pass: false,
      details: {
        snapshot_generated_at_utc: snapshotGeneratedAt,
        quote_generated_at_utc: quoteGeneratedAt,
        lag_hours: quoteLagVsSnapshotHours,
      },
    },
    {
      id: 'quote_publication_identity_missing',
      pass: false,
      details: publicationIdsPresent,
    },
    {
      id: 'quote_age_exceeded_sla',
      pass: false,
      details: {
        quote_age_hours_now: quoteAgeHoursNow,
        max_age_hours_allowed: VALIDATION_MAX_AGE_HOURS,
      },
    },
  ],
  separate_serving_status_issue: separateServingTimestampIssue,
  quote_families: (familyBlockers.families || []).map((family) => ({
    id: family.id,
    activation_blocked: true,
    base_population_row_count: family.base_population_row_count ?? null,
    current_eligible_row_count: family.current_eligible_row_count ?? null,
    source_readiness: false,
    extraction_readiness: Boolean(family.extraction_readiness),
    blocker_classes: Array.from(new Set([
      'quote_publication_alignment_failed',
      'quote_publication_identity_missing',
      'quote_age_exceeded_sla',
      ...((family.blocker_classes || []).filter((item) => item !== 'quote_source_not_ready')),
    ])),
    current_activation_blockers: Array.from(new Set([
      'publication_alignment_with_snapshot',
      'publication_identity_missing',
      'quote_age_within_validation_window',
      ...((family.current_activation_blockers || []).filter((item) => item !== 'publication_alignment_with_snapshot' && item !== 'quote_age_within_validation_window')),
    ])),
  })),
  unaffected_families: [
    'accumulation_core',
    'hold_discipline_core',
    'hold_only_no_add_discipline',
    'recency_sensitive_accumulation',
    'epoch_assisted_accumulation',
    'abstention_suppression_degraded_mode',
  ],
  note: 'Non-quote families remain unaffected by quote freshness remediation and remain governed by their own readiness contracts.',
};

const rootCauseMd = lines([
  '# Quote Freshness Root Cause Audit (Latest)',
  '',
  '## Verdict',
  '',
  '- Recommended option: **fix publication alignment now**',
  '- Primary root cause: `publication_alignment_failure`',
  '- Secondary root cause: `refresh_bookkeeping_gap`',
  '- Separate parallel issue: `runtime_sync_timestamp_source_mismatch`',
  '',
  '## Was the 5.4 note helpful?',
  '',
  'Yes. It proves a separate serving-status bug exists in parallel. That bug can make Recommendations and Portfolio look stale even when snapshot-backed runtime rows are fresh. It does not explain or fix the stale quote artifact.',
  '',
  '## Current observed state',
  '',
  `- Active snapshot generated_at_utc: ${snapshotGeneratedAt}`,
  `- Active quote generated_at_utc: ${quoteGeneratedAt}`,
  `- Active rebuild report generated_at_utc: ${rebuildReportGeneratedAt}`,
  `- Quote lag behind snapshot: ${quoteLagVsSnapshotHours} hours`,
  `- Quote age versus now: ${quoteAgeHoursNow} hours`,
  `- Snapshot unique tickers: ${snapshotUniqueTickerCount}`,
  `- Quote symbols_cached: ${quoteSymbolCount}`,
  `- Publication identity present on both artifacts: ${publicationIdentityPresent}`,
  '',
  '## Q1 answers',
  '',
  '### 1. Did quote refresh actually execute for the active snapshot/run?',
  '- Answer: `not_provable_from_current_artifacts`',
  '- Why: local refresh bookkeeping does not show a March 6 aligned quote publication, and the active quote artifact remains dated February 28.',
  '',
  '### 2. Was the resulting quote artifact published?',
  '- Answer: `no_evidence_of_publication_to_active_path`',
  '- Why: the quote builder republishes the active file even when `pending=0`, but the active quote file timestamp never advanced to match the active snapshot publication.',
  '',
  '### 3. Is runtime sync selecting the wrong quote artifact?',
  '- Answer: `no`',
  '- Why: runtime sync is hard-bound to `web/data/screener-quote-cache.json`, and the quote loader candidate order resolves to the same active path.',
  '',
  '### 4. Are snapshot and quote cache coming from different run_ids/publication ids?',
  '- Answer: `identity_not_provable_metadata_missing_publication_times_diverge`',
  '- Why: both artifacts lack `run_id` / `publication_id` metadata, so same-publication lineage cannot be proven. Their publication times diverge by 155.618 hours.',
  '',
  '### 5. What caused the stale condition?',
  '- Answer: `primary_publication_alignment_failure_secondary_refresh_bookkeeping_gap_with_separate_serving_timestamp_bug`',
  '- Primary class: publication selection/alignment failure',
  '- Secondary class: refresh bookkeeping gap',
  '- Separate parallel issue: serving timestamp-source mismatch in runtime sync',
  '- Ruled out as primary for quote freshness: runtime quote read-path failure, timezone mismatch, validation-threshold mismatch',
  '- Still unproven: producer failure, scheduler failure',
  '',
  '## Evidence',
  '',
  '- `run_refresh_with_l5_learning.py:960-972` shows quote refresh should run immediately after snapshot rebuild.',
  '- `web/scripts/build_screener_quote_cache.py:556-567` shows quote refresh republishes the active output file with a fresh timestamp.',
  '- `web/scripts/build_screener_quote_cache.py:700-705` shows it republishes even when there are no pending symbols.',
  '- `web/scripts/sync_runtime_postgres.mjs:615-637` shows runtime sync reads the active repo-local snapshot and quote artifacts directly.',
  '- `web/src/lib/screener-quote-cache.ts:48-56` and `116-130` show the runtime read path is using the expected active quote file.',
  '- `web/scripts/sync_runtime_postgres.mjs:220-253` shows the separate timestamp-source fix that prefers the snapshot payload timestamp over the rebuild-report timestamp.',
  '- `admin_refresh_status.json` and `uf_snapshot_rebuild_report.json` do not line up with the active March 6 snapshot publication.',
  '',
  '## Recommendation',
  '',
  'Fix publication alignment now. Keep the sync timestamp-source fix in its own lane. Do not activate quote-governed families until publication identity is explicit and freshness passes fail-closed checks.',
]);

writeJson(path.join(ROOT, 'quote_publication_alignment_latest.json'), publicationAlignment);
writeJson(path.join(ROOT, 'quote_freshness_root_cause_latest.json'), rootCause);
writeText(path.join(ROOT, 'quote_freshness_root_cause_latest.md'), rootCauseMd);
writeText(path.join(ROOT, 'quote_freshness_sla_latest.md'), quoteSla);
writeText(path.join(ROOT, 'quote_publication_contract_latest.md'), quotePublicationContract);
writeText(path.join(ROOT, 'quote_freshness_remediation_plan_latest.md'), remediationPlan);
writeJson(path.join(ROOT, 'quote_freshness_activation_blocks_latest.json'), activationBlocks);

console.log(JSON.stringify({
  status: 'ok',
  generated_at_utc: GENERATED_AT,
  outputs: [
    'quote_publication_alignment_latest.json',
    'quote_freshness_root_cause_latest.json',
    'quote_freshness_root_cause_latest.md',
    'quote_freshness_sla_latest.md',
    'quote_publication_contract_latest.md',
    'quote_freshness_remediation_plan_latest.md',
    'quote_freshness_activation_blocks_latest.json',
  ],
  recommendation: 'fix_publication_alignment_now',
  helpful_54_note: true,
  metrics: {
    quote_lag_vs_snapshot_hours: quoteLagVsSnapshotHours,
    quote_age_hours_now: quoteAgeHoursNow,
    publication_identity_present: publicationIdentityPresent,
    source_readiness_pass: Boolean(sourceReadiness.source_readiness_pass),
  },
}, null, 2));
