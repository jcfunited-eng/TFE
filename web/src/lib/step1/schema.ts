import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  isPostgresConfigured,
  resolveRuntimePostgresPool,
  RUNTIME_REFRESH_RUNS_TABLE,
} from "../runtime-db";

export const STEP1_CANDIDATE_BUILD_PHASE = "candidate_build";
export const STEP1_ASSESSMENT_GATE_PHASE = "assessment_gate";
export const STEP1_PUBLICATION_COMMIT_PHASE = "publication_commit";
export const STEP1_QUOTE_CACHE_REFRESH_PHASE = "quote_cache_refresh";
export const STEP1_REQUEST_ARTIFACT_RELATIVE_PATH = path.join("step1", "request.json");
export const STEP1_CANDIDATE_BUNDLE_MANIFEST_RELATIVE_PATH = path.join("step1", "candidate_bundle", "manifest.json");
export const STEP1_ASSESSMENT_REPORT_RELATIVE_PATH = path.join("step1", "assessment_report.json");
export const STEP1_FOLLOWUP_TICKET_RELATIVE_PATH = path.join("step1", "followup_ticket.json");
export const STEP1_FILE_PROOF_STORE_VERSION = 1;

const RUNTIME_REFRESH_RUN_PHASES_TABLE = "runtime_refresh_run_phases";
const STEP1_CANDIDATE_BUNDLES_TABLE = "candidate_bundles";
const STEP1_ASSESSMENT_REPORTS_TABLE = "assessment_reports";
const STEP1_PUBLICATION_BUNDLES_TABLE = "publication_bundles";
const STEP1_ACTIVE_PUBLICATION_POINTER_TABLE = "active_publication_pointer";
const STEP1_PUBLICATION_ACTIVATION_AUDIT_TABLE = "publication_activation_audit";
const STEP1_DEFERRED_FOLLOWUP_JOBS_TABLE = "deferred_followup_jobs";

export type Step1SourcePackageIdentityRecord = {
  source_package_id: string;
  source_identity: string;
  acquisition_timestamp_utc: string;
  source_class: string;
  raw_payload_reference: string;
  integrity_status: string;
};

export type Step1RunRequestRecord = {
  run_id: string;
  normalized_package_id: string;
  policy_set_id: string;
  model_set_id: string;
  config_set_id: string;
  bundle_class: string;
  dependency_classification_register: Record<string, unknown>;
  source_package_identities?: Step1SourcePackageIdentityRecord[];
  target_environment: string;
  requested_by: string;
  requested_at_utc: string;
};

export type Step1RuntimeRefreshRunRow = {
  run_id: string;
  mode: string;
  trigger_source: string;
  requested_by: string;
  started_at: string;
  completed_at: string | null;
  report_generated_at_utc?: string | null;
  rows_written?: number | null;
  report_status: string;
  validation_status?: string | null;
  validation_report_path?: string | null;
  request_artifact_path: string;
  bundle_generated_at_utc?: string | null;
  snapshot_publication_id?: string | null;
  quote_publication_id?: string | null;
  quote_binding_status?: string | null;
  activation_state?: string | null;
  serving_state?: string | null;
  blocking_reason_code?: string | null;
  blocking_reason_detail?: string | null;
  is_active_publication?: boolean;
  current_phase: string;
  current_phase_process_status: string;
  current_phase_started_at: string | null;
  current_phase_completed_at: string | null;
  current_phase_last_heartbeat_at: string | null;
  current_phase_failure_code: string | null;
  current_phase_failure_detail: string | null;
  failure_code: string | null;
  failure_detail: string | null;
  created_at: string;
  updated_at: string;
};

export type Step1RuntimeRefreshPhaseRow = {
  run_id: string;
  phase_name: string;
  input_contract: Record<string, unknown> | null;
  process_status: string;
  started_at: string | null;
  completed_at: string | null;
  output_contract: Record<string, unknown> | null;
  failure_code: string | null;
  failure_detail: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Step1AssessmentArtifactReference = {
  artifact_kind: string;
  artifact_id: string;
  artifact_path?: string | null;
  artifact_digest_sha256: string | null;
};

export type Step1CandidateBundleManifest = {
  candidate_bundle_id: string;
  normalized_package_id: string;
  policy_set_id: string;
  model_set_id: string;
  config_set_id: string;
  bundle_class: string;
  normalized_package_manifest_id: string;
  normalized_package_manifest_path: string;
  normalized_package_manifest_digest_sha256: string;
  source_package_identities: Step1SourcePackageIdentityRecord[];
  requested_run_mode: string;
  deterministic_build_timestamp_utc: string;
  target_environment: string;
  dependency_classification_register: Record<string, unknown>;
  assessment_artifact_references: Step1AssessmentArtifactReference[];
};

export type Step1CandidateBundleRow = {
  run_id: string;
  candidate_bundle_id: string;
  normalized_package_id: string;
  policy_set_id: string;
  model_set_id: string;
  config_set_id: string;
  bundle_class: string;
  requested_run_mode: string;
  target_environment: string;
  deterministic_build_timestamp_utc: string;
  dependency_classification_register: Record<string, unknown>;
  assessment_artifact_references: Step1AssessmentArtifactReference[];
  request_artifact_path: string;
  manifest_path: string;
  manifest_digest_sha256: string;
  created_at: string;
  updated_at: string;
};

export type Step1AssessmentBlockingReason = {
  reason_code: string;
  reason_detail: string;
  dependency_id: string | null;
  dependency_classification: "publication_critical" | "non_critical" | "not_applicable" | null;
};

export type Step1AssessmentEvidenceReference = {
  evidence_kind: string;
  evidence_id: string;
  evidence_path: string | null;
  evidence_digest_sha256: string | null;
};

export type Step1AssessmentDisposition = "pass" | "fail";

export type Step1AssessmentReportArtifact = {
  assessment_report_id: string;
  candidate_bundle_id: string;
  assessment_rule_set_id: string;
  disposition: Step1AssessmentDisposition;
  blocking_reason_codes: string[];
  blocking_reason_details: Step1AssessmentBlockingReason[];
  evidence_references: Step1AssessmentEvidenceReference[];
  publication_allowed: boolean;
  created_at_utc: string;
};

export type Step1AssessmentReportRow = {
  run_id: string;
  assessment_report_id: string;
  candidate_bundle_id: string;
  assessment_rule_set_id: string;
  disposition: Step1AssessmentDisposition;
  blocking_reason_codes: string[];
  blocking_reason_details: Step1AssessmentBlockingReason[];
  evidence_references: Step1AssessmentEvidenceReference[];
  candidate_bundle_manifest_path: string;
  report_path: string;
  publication_allowed: boolean;
  created_at: string;
  updated_at: string;
};

export type Step1PublicationBundleManifest = {
  publication_bundle_id: string;
  run_id: string;
  candidate_bundle_id: string;
  assessment_report_id: string;
  normalized_package_id: string;
  policy_set_id: string;
  model_set_id: string;
  config_set_id: string;
  bundle_class: string;
  target_environment: string;
  previous_active_publication_id: string | null;
  activation_audit_id: string;
  candidate_bundle_manifest_path: string;
  assessment_report_path: string;
  committed_at_utc: string;
};

export type Step1PublicationBundleRow = {
  publication_bundle_id: string;
  run_id: string;
  candidate_bundle_id: string;
  assessment_report_id: string;
  normalized_package_id: string;
  policy_set_id: string;
  model_set_id: string;
  config_set_id: string;
  bundle_class: string;
  target_environment: string;
  previous_active_publication_id: string | null;
  activation_audit_id: string;
  candidate_bundle_manifest_path: string;
  assessment_report_path: string;
  manifest_path: string;
  manifest_digest_sha256: string;
  created_at: string;
  updated_at: string;
};

export type Step1ActivePublicationPointerRow = {
  target_environment: string;
  publication_bundle_id: string;
  run_id: string;
  created_at: string;
  updated_at: string;
};

export type Step1PublicationActivationAuditRow = {
  activation_audit_id: string;
  target_environment: string;
  run_id: string;
  publication_bundle_id: string;
  previous_active_publication_id: string | null;
  new_active_publication_id: string;
  assessment_report_id: string;
  created_at: string;
};

export type Step1FollowupClassification = "non_critical_follow_up";
export type Step1FollowupStatus = "deferred" | "launched" | "failed";

export type Step1QuoteCacheFollowupTicketArtifact = {
  followup_job_id: string;
  triggering_run_id: string;
  publication_bundle_id: string;
  target_environment: string;
  phase_name: typeof STEP1_QUOTE_CACHE_REFRESH_PHASE;
  classification: Step1FollowupClassification;
  status: Step1FollowupStatus;
  publication_manifest_path: string;
  operator_visible_status: string;
  created_at_utc: string;
};

export type Step1DeferredFollowupJobRow = {
  followup_job_id: string;
  run_id: string;
  publication_bundle_id: string;
  target_environment: string;
  phase_name: typeof STEP1_QUOTE_CACHE_REFRESH_PHASE;
  classification: Step1FollowupClassification;
  status: Step1FollowupStatus;
  publication_manifest_path: string;
  ticket_path: string;
  operator_visible_status: string;
  failure_code: string | null;
  failure_detail: string | null;
  created_at: string;
  updated_at: string;
};

export type Step1ProofStore = {
  format_version: number;
  runtime_refresh_runs: Step1RuntimeRefreshRunRow[];
  runtime_refresh_run_phases: Step1RuntimeRefreshPhaseRow[];
  candidate_bundles: Step1CandidateBundleRow[];
  assessment_reports: Step1AssessmentReportRow[];
  publication_bundles: Step1PublicationBundleRow[];
  active_publication_pointer: Step1ActivePublicationPointerRow[];
  active_publication_pointer_writes: Step1ActivePublicationPointerRow[];
  publication_activation_audits: Step1PublicationActivationAuditRow[];
  deferred_followup_jobs: Step1DeferredFollowupJobRow[];
};

export type Step1RunRequestPersistence = {
  kind: "postgres" | "file-proof";
  ensureReady(): Promise<void>;
  writeRunRow(row: Step1RuntimeRefreshRunRow): Promise<void>;
  writePhaseRow(row: Step1RuntimeRefreshPhaseRow): Promise<void>;
};

export type Step1CandidateBundlePersistence = Pick<
  Step1RunRequestPersistence,
  "kind" | "ensureReady" | "writePhaseRow"
> & {
  writeCandidateBundleRow(row: Step1CandidateBundleRow): Promise<void>;
};

export type Step1AssessmentReportPersistence = Pick<
  Step1RunRequestPersistence,
  "kind" | "ensureReady" | "writePhaseRow"
> & {
  writeAssessmentReportRow(row: Step1AssessmentReportRow): Promise<void>;
};

export type Step1PublicationCommitTransaction = {
  publicationBundleRow: Step1PublicationBundleRow;
  activePublicationPointerRow: Step1ActivePublicationPointerRow;
  publicationActivationAuditRow: Step1PublicationActivationAuditRow;
  phaseRow: Step1RuntimeRefreshPhaseRow;
};

export type Step1PublicationCommitPersistence = Pick<
  Step1RunRequestPersistence,
  "kind" | "ensureReady"
> & {
  readActivePublicationPointer(targetEnvironment: string): Promise<Step1ActivePublicationPointerRow | null>;
  commitPublicationTransaction(transaction: Step1PublicationCommitTransaction): Promise<void>;
};

export type Step1FollowupTicketPersistence = Pick<
  Step1RunRequestPersistence,
  "kind" | "ensureReady" | "writePhaseRow"
> & Pick<
  Step1PublicationCommitPersistence,
  "readActivePublicationPointer"
> & {
  writeDeferredFollowupJobRow(row: Step1DeferredFollowupJobRow): Promise<void>;
};

export type Step1Persistence = Step1RunRequestPersistence
  & Step1CandidateBundlePersistence
  & Step1AssessmentReportPersistence
  & Step1PublicationCommitPersistence
  & Step1FollowupTicketPersistence;

function toIsoUtc(value: unknown, fieldName: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new Error(`${fieldName} must be a non-empty ISO timestamp.`);
  }
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${fieldName} must be a valid ISO timestamp.`);
  }
  return new Date(parsed).toISOString();
}

function asObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => String(entry ?? "").trim())
    .filter(Boolean);
}

function parseStoredStep1SourcePackageIdentityRecord(value: unknown): Step1SourcePackageIdentityRecord | null {
  const record = asObject(value);
  if (!record) return null;

  const sourcePackageId = String(record.source_package_id ?? "").trim();
  const sourceIdentity = String(record.source_identity ?? "").trim();
  const acquisitionTimestampRaw = String(record.acquisition_timestamp_utc ?? "").trim();
  const sourceClass = String(record.source_class ?? "").trim();
  const rawPayloadReference = String(record.raw_payload_reference ?? "").trim();
  const integrityStatus = String(record.integrity_status ?? "").trim();

  if (
    !sourcePackageId
    || !sourceIdentity
    || !acquisitionTimestampRaw
    || !sourceClass
    || !rawPayloadReference
    || !integrityStatus
  ) {
    return null;
  }

  return {
    source_package_id: sourcePackageId,
    source_identity: sourceIdentity,
    acquisition_timestamp_utc: toIsoUtc(
      acquisitionTimestampRaw,
      "source_package_identities.acquisition_timestamp_utc",
    ),
    source_class: sourceClass,
    raw_payload_reference: rawPayloadReference,
    integrity_status: integrityStatus,
  };
}

function parseStoredStep1SourcePackageIdentities(
  value: unknown,
): Step1SourcePackageIdentityRecord[] | undefined | null {
  if (typeof value === "undefined") {
    return undefined;
  }
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }

  const parsed = value.map((entry) => parseStoredStep1SourcePackageIdentityRecord(entry));
  if (parsed.some((entry) => entry === null)) {
    return null;
  }
  return parsed as Step1SourcePackageIdentityRecord[];
}

function emptyProofStore(): Step1ProofStore {
  return {
    format_version: STEP1_FILE_PROOF_STORE_VERSION,
    runtime_refresh_runs: [],
    runtime_refresh_run_phases: [],
    candidate_bundles: [],
    assessment_reports: [],
    publication_bundles: [],
    active_publication_pointer: [],
    active_publication_pointer_writes: [],
    publication_activation_audits: [],
    deferred_followup_jobs: [],
  };
}

async function readProofStore(storePath: string): Promise<Step1ProofStore> {
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Step1ProofStore;
    if (!parsed || typeof parsed !== "object") return emptyProofStore();
    return {
      format_version: Number(parsed.format_version) || STEP1_FILE_PROOF_STORE_VERSION,
      runtime_refresh_runs: Array.isArray(parsed.runtime_refresh_runs) ? parsed.runtime_refresh_runs : [],
      runtime_refresh_run_phases: Array.isArray(parsed.runtime_refresh_run_phases) ? parsed.runtime_refresh_run_phases : [],
      candidate_bundles: Array.isArray(parsed.candidate_bundles) ? parsed.candidate_bundles : [],
      assessment_reports: Array.isArray(parsed.assessment_reports) ? parsed.assessment_reports : [],
      publication_bundles: Array.isArray(parsed.publication_bundles) ? parsed.publication_bundles : [],
      active_publication_pointer: Array.isArray((parsed as Partial<Step1ProofStore>).active_publication_pointer)
        ? (parsed as Partial<Step1ProofStore>).active_publication_pointer as Step1ActivePublicationPointerRow[]
        : [],
      active_publication_pointer_writes: Array.isArray(parsed.active_publication_pointer_writes)
        ? parsed.active_publication_pointer_writes
        : [],
      publication_activation_audits: Array.isArray((parsed as Partial<Step1ProofStore>).publication_activation_audits)
        ? (parsed as Partial<Step1ProofStore>).publication_activation_audits as Step1PublicationActivationAuditRow[]
        : [],
      deferred_followup_jobs: Array.isArray((parsed as Partial<Step1ProofStore>).deferred_followup_jobs)
        ? (parsed as Partial<Step1ProofStore>).deferred_followup_jobs as Step1DeferredFollowupJobRow[]
        : [],
    };
  } catch {
    return emptyProofStore();
  }
}

async function writeProofStore(storePath: string, store: Step1ProofStore): Promise<void> {
  await mkdir(path.dirname(storePath), { recursive: true });
  await writeFile(storePath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
}

function upsertRunRow(rows: Step1RuntimeRefreshRunRow[], row: Step1RuntimeRefreshRunRow): Step1RuntimeRefreshRunRow[] {
  const next = rows.filter((candidate) => candidate.run_id !== row.run_id);
  next.push(row);
  next.sort((left, right) => left.run_id.localeCompare(right.run_id));
  return next;
}

function applyPhaseMirrorToRunRow(
  row: Step1RuntimeRefreshRunRow,
  phaseRow: Step1RuntimeRefreshPhaseRow,
): Step1RuntimeRefreshRunRow {
  return {
    ...row,
    current_phase: phaseRow.phase_name,
    current_phase_process_status: phaseRow.process_status,
    current_phase_started_at: phaseRow.started_at,
    current_phase_completed_at: phaseRow.completed_at,
    current_phase_last_heartbeat_at: phaseRow.last_heartbeat_at,
    current_phase_failure_code: phaseRow.failure_code,
    current_phase_failure_detail: phaseRow.failure_detail,
    updated_at: phaseRow.updated_at,
  };
}

function upsertPhaseRow(
  rows: Step1RuntimeRefreshPhaseRow[],
  row: Step1RuntimeRefreshPhaseRow,
): Step1RuntimeRefreshPhaseRow[] {
  const next = rows.filter(
    (candidate) => !(candidate.run_id === row.run_id && candidate.phase_name === row.phase_name),
  );
  next.push(row);
  next.sort((left, right) => {
    const runOrder = left.run_id.localeCompare(right.run_id);
    if (runOrder !== 0) return runOrder;
    return left.phase_name.localeCompare(right.phase_name);
  });
  return next;
}

function upsertCandidateBundleRow(
  rows: Step1CandidateBundleRow[],
  row: Step1CandidateBundleRow,
): Step1CandidateBundleRow[] {
  const next = rows.filter((candidate) => candidate.run_id !== row.run_id);
  next.push(row);
  next.sort((left, right) => left.run_id.localeCompare(right.run_id));
  return next;
}

function upsertAssessmentReportRow(
  rows: Step1AssessmentReportRow[],
  row: Step1AssessmentReportRow,
): Step1AssessmentReportRow[] {
  const next = rows.filter((candidate) => candidate.run_id !== row.run_id);
  next.push(row);
  next.sort((left, right) => left.run_id.localeCompare(right.run_id));
  return next;
}

function upsertPublicationBundleRow(
  rows: Step1PublicationBundleRow[],
  row: Step1PublicationBundleRow,
): Step1PublicationBundleRow[] {
  const next = rows.filter((candidate) => candidate.publication_bundle_id !== row.publication_bundle_id);
  next.push(row);
  next.sort((left, right) => left.publication_bundle_id.localeCompare(right.publication_bundle_id));
  return next;
}

function upsertActivePublicationPointerRow(
  rows: Step1ActivePublicationPointerRow[],
  row: Step1ActivePublicationPointerRow,
): Step1ActivePublicationPointerRow[] {
  const next = rows.filter((candidate) => candidate.target_environment !== row.target_environment);
  next.push(row);
  next.sort((left, right) => left.target_environment.localeCompare(right.target_environment));
  return next;
}

function appendActivePublicationPointerWriteRow(
  rows: Step1ActivePublicationPointerRow[],
  row: Step1ActivePublicationPointerRow,
): Step1ActivePublicationPointerRow[] {
  const next = [...rows, row];
  next.sort((left, right) => {
    const environmentOrder = left.target_environment.localeCompare(right.target_environment);
    if (environmentOrder !== 0) return environmentOrder;
    return left.updated_at.localeCompare(right.updated_at);
  });
  return next;
}

function upsertPublicationActivationAuditRow(
  rows: Step1PublicationActivationAuditRow[],
  row: Step1PublicationActivationAuditRow,
): Step1PublicationActivationAuditRow[] {
  const next = rows.filter((candidate) => candidate.activation_audit_id !== row.activation_audit_id);
  next.push(row);
  next.sort((left, right) => left.activation_audit_id.localeCompare(right.activation_audit_id));
  return next;
}

function upsertDeferredFollowupJobRow(
  rows: Step1DeferredFollowupJobRow[],
  row: Step1DeferredFollowupJobRow,
): Step1DeferredFollowupJobRow[] {
  const next = rows.filter((candidate) => candidate.followup_job_id !== row.followup_job_id);
  next.push(row);
  next.sort((left, right) => left.followup_job_id.localeCompare(right.followup_job_id));
  return next;
}

export function buildStep1RequestArtifactRelativePath(runId: string): string {
  return path.join("artifacts", "runs", runId, STEP1_REQUEST_ARTIFACT_RELATIVE_PATH);
}

export function resolveStep1RequestArtifactPath(workspaceRoot: string, runId: string): string {
  return path.join(workspaceRoot, buildStep1RequestArtifactRelativePath(runId));
}

export function buildStep1CandidateBundleManifestRelativePath(runId: string): string {
  return path.join("artifacts", "runs", runId, STEP1_CANDIDATE_BUNDLE_MANIFEST_RELATIVE_PATH);
}

export function resolveStep1CandidateBundleManifestPath(workspaceRoot: string, runId: string): string {
  return path.join(workspaceRoot, buildStep1CandidateBundleManifestRelativePath(runId));
}

export function buildStep1AssessmentReportRelativePath(runId: string): string {
  return path.join("artifacts", "runs", runId, STEP1_ASSESSMENT_REPORT_RELATIVE_PATH);
}

export function resolveStep1AssessmentReportPath(workspaceRoot: string, runId: string): string {
  return path.join(workspaceRoot, buildStep1AssessmentReportRelativePath(runId));
}

export function buildStep1PublicationManifestRelativePath(publicationBundleId: string): string {
  return path.join("artifacts", "publications", publicationBundleId, "manifest.json");
}

export function resolveStep1PublicationManifestPath(workspaceRoot: string, publicationBundleId: string): string {
  return path.join(workspaceRoot, buildStep1PublicationManifestRelativePath(publicationBundleId));
}

export function buildStep1FollowupTicketRelativePath(runId: string): string {
  return path.join("artifacts", "runs", runId, STEP1_FOLLOWUP_TICKET_RELATIVE_PATH);
}

export function resolveStep1FollowupTicketPath(workspaceRoot: string, runId: string): string {
  return path.join(workspaceRoot, buildStep1FollowupTicketRelativePath(runId));
}

export function createFileProofStep1Persistence(storePath: string): Step1Persistence {
  return {
    kind: "file-proof",
    async ensureReady(): Promise<void> {
      const store = await readProofStore(storePath);
      await writeProofStore(storePath, store);
    },
    async writeRunRow(row: Step1RuntimeRefreshRunRow): Promise<void> {
      const store = await readProofStore(storePath);
      store.runtime_refresh_runs = upsertRunRow(store.runtime_refresh_runs, row);
      await writeProofStore(storePath, store);
    },
    async writePhaseRow(row: Step1RuntimeRefreshPhaseRow): Promise<void> {
      const store = await readProofStore(storePath);
      store.runtime_refresh_run_phases = upsertPhaseRow(store.runtime_refresh_run_phases, row);
      const existingRunRow = store.runtime_refresh_runs.find((candidate) => candidate.run_id === row.run_id);
      if (existingRunRow) {
        store.runtime_refresh_runs = upsertRunRow(
          store.runtime_refresh_runs,
          applyPhaseMirrorToRunRow(existingRunRow, row),
        );
      }
      await writeProofStore(storePath, store);
    },
    async writeCandidateBundleRow(row: Step1CandidateBundleRow): Promise<void> {
      const store = await readProofStore(storePath);
      store.candidate_bundles = upsertCandidateBundleRow(store.candidate_bundles, row);
      await writeProofStore(storePath, store);
    },
    async writeAssessmentReportRow(row: Step1AssessmentReportRow): Promise<void> {
      const store = await readProofStore(storePath);
      store.assessment_reports = upsertAssessmentReportRow(store.assessment_reports, row);
      await writeProofStore(storePath, store);
    },
    async readActivePublicationPointer(targetEnvironment: string): Promise<Step1ActivePublicationPointerRow | null> {
      const store = await readProofStore(storePath);
      return selectStep1ActivePublicationPointerRow(store, targetEnvironment);
    },
    async commitPublicationTransaction(transaction: Step1PublicationCommitTransaction): Promise<void> {
      const store = await readProofStore(storePath);
      store.publication_bundles = upsertPublicationBundleRow(
        store.publication_bundles,
        transaction.publicationBundleRow,
      );
      store.active_publication_pointer = upsertActivePublicationPointerRow(
        store.active_publication_pointer,
        transaction.activePublicationPointerRow,
      );
      store.active_publication_pointer_writes = appendActivePublicationPointerWriteRow(
        store.active_publication_pointer_writes,
        transaction.activePublicationPointerRow,
      );
      store.publication_activation_audits = upsertPublicationActivationAuditRow(
        store.publication_activation_audits,
        transaction.publicationActivationAuditRow,
      );
      store.runtime_refresh_run_phases = upsertPhaseRow(store.runtime_refresh_run_phases, transaction.phaseRow);
      const existingRunRow = store.runtime_refresh_runs.find(
        (candidate) => candidate.run_id === transaction.phaseRow.run_id,
      );
      if (existingRunRow) {
        store.runtime_refresh_runs = upsertRunRow(
          store.runtime_refresh_runs,
          applyPhaseMirrorToRunRow(existingRunRow, transaction.phaseRow),
        );
      }
      await writeProofStore(storePath, store);
    },
    async writeDeferredFollowupJobRow(row: Step1DeferredFollowupJobRow): Promise<void> {
      const store = await readProofStore(storePath);
      store.deferred_followup_jobs = upsertDeferredFollowupJobRow(store.deferred_followup_jobs, row);
      await writeProofStore(storePath, store);
    },
  };
}

export function createPostgresStep1Persistence(): Step1Persistence {
  return {
    kind: "postgres",
    async ensureReady(): Promise<void> {
      if (!isPostgresConfigured()) {
        throw new Error("Runtime Postgres is not configured for Step 1 schema persistence.");
      }

      const pool = resolveRuntimePostgresPool();
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${RUNTIME_REFRESH_RUNS_TABLE} (
          run_id TEXT PRIMARY KEY,
          mode TEXT,
          trigger_source TEXT,
          requested_by TEXT,
          started_at TIMESTAMPTZ,
          completed_at TIMESTAMPTZ,
          report_generated_at_utc TIMESTAMPTZ,
          rows_written INTEGER,
          report_status TEXT,
          optimizer_short_cycle TEXT,
          optimizer_cycle_requested_runs INTEGER,
          optimizer_cycle_completed_runs INTEGER,
          optimizer_session_id TEXT,
          optimizer_target_return_lift_pct DOUBLE PRECISION,
          optimizer_best_score DOUBLE PRECISION,
          optimizer_target_met BOOLEAN,
          epoch_library_confidence_schema TEXT,
          epoch_library_status TEXT,
          validation_status TEXT,
          validation_report_path TEXT,
          request_artifact_path TEXT,
          is_active_publication BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        ALTER TABLE ${RUNTIME_REFRESH_RUNS_TABLE}
        ADD COLUMN IF NOT EXISTS bundle_generated_at_utc TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS snapshot_publication_id TEXT,
        ADD COLUMN IF NOT EXISTS quote_publication_id TEXT,
        ADD COLUMN IF NOT EXISTS quote_binding_status TEXT,
        ADD COLUMN IF NOT EXISTS activation_state TEXT,
        ADD COLUMN IF NOT EXISTS serving_state TEXT,
        ADD COLUMN IF NOT EXISTS blocking_reason_code TEXT,
        ADD COLUMN IF NOT EXISTS blocking_reason_detail TEXT,
        ADD COLUMN IF NOT EXISTS failure_code TEXT,
        ADD COLUMN IF NOT EXISTS failure_detail TEXT,
        ADD COLUMN IF NOT EXISTS current_phase TEXT,
        ADD COLUMN IF NOT EXISTS current_phase_process_status TEXT,
        ADD COLUMN IF NOT EXISTS current_phase_started_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS current_phase_completed_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS current_phase_last_heartbeat_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS current_phase_failure_code TEXT,
        ADD COLUMN IF NOT EXISTS current_phase_failure_detail TEXT,
        ADD COLUMN IF NOT EXISTS request_artifact_path TEXT,
        ADD COLUMN IF NOT EXISTS is_active_publication BOOLEAN NOT NULL DEFAULT FALSE
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${RUNTIME_REFRESH_RUN_PHASES_TABLE} (
          run_id TEXT NOT NULL REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE CASCADE,
          phase_name TEXT NOT NULL,
          input_contract JSONB,
          process_status TEXT NOT NULL,
          started_at TIMESTAMPTZ,
          completed_at TIMESTAMPTZ,
          output_contract JSONB,
          failure_code TEXT,
          failure_detail TEXT,
          last_heartbeat_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY (run_id, phase_name)
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_run_id
        ON ${RUNTIME_REFRESH_RUN_PHASES_TABLE} (run_id)
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_running
        ON ${RUNTIME_REFRESH_RUN_PHASES_TABLE} (run_id, process_status, last_heartbeat_at DESC)
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_CANDIDATE_BUNDLES_TABLE} (
          run_id TEXT PRIMARY KEY REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE CASCADE,
          candidate_bundle_id TEXT NOT NULL,
          normalized_package_id TEXT NOT NULL,
          policy_set_id TEXT NOT NULL,
          model_set_id TEXT NOT NULL,
          config_set_id TEXT NOT NULL,
          bundle_class TEXT NOT NULL,
          requested_run_mode TEXT NOT NULL,
          target_environment TEXT NOT NULL,
          deterministic_build_timestamp_utc TIMESTAMPTZ NOT NULL,
          dependency_classification_register JSONB NOT NULL,
          assessment_artifact_references JSONB NOT NULL,
          request_artifact_path TEXT NOT NULL,
          manifest_path TEXT NOT NULL,
          manifest_digest_sha256 TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_candidate_bundles_candidate_bundle_id
        ON ${STEP1_CANDIDATE_BUNDLES_TABLE} (candidate_bundle_id)
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_ASSESSMENT_REPORTS_TABLE} (
          run_id TEXT PRIMARY KEY REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE CASCADE,
          assessment_report_id TEXT NOT NULL,
          candidate_bundle_id TEXT NOT NULL,
          assessment_rule_set_id TEXT NOT NULL,
          disposition TEXT NOT NULL,
          blocking_reason_codes JSONB NOT NULL,
          blocking_reason_details JSONB NOT NULL,
          evidence_references JSONB NOT NULL,
          candidate_bundle_manifest_path TEXT NOT NULL,
          report_path TEXT NOT NULL,
          publication_allowed BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_assessment_reports_assessment_report_id
        ON ${STEP1_ASSESSMENT_REPORTS_TABLE} (assessment_report_id)
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_assessment_reports_candidate_bundle_id
        ON ${STEP1_ASSESSMENT_REPORTS_TABLE} (candidate_bundle_id)
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_PUBLICATION_BUNDLES_TABLE} (
          publication_bundle_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE CASCADE,
          candidate_bundle_id TEXT NOT NULL,
          assessment_report_id TEXT NOT NULL,
          normalized_package_id TEXT NOT NULL,
          policy_set_id TEXT NOT NULL,
          model_set_id TEXT NOT NULL,
          config_set_id TEXT NOT NULL,
          bundle_class TEXT NOT NULL,
          target_environment TEXT NOT NULL,
          previous_active_publication_id TEXT,
          activation_audit_id TEXT NOT NULL,
          candidate_bundle_manifest_path TEXT NOT NULL,
          assessment_report_path TEXT NOT NULL,
          manifest_path TEXT NOT NULL,
          manifest_digest_sha256 TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_publication_bundles_run_id
        ON ${STEP1_PUBLICATION_BUNDLES_TABLE} (run_id)
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_publication_bundles_target_environment
        ON ${STEP1_PUBLICATION_BUNDLES_TABLE} (target_environment, created_at DESC)
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE} (
          target_environment TEXT PRIMARY KEY,
          publication_bundle_id TEXT NOT NULL REFERENCES ${STEP1_PUBLICATION_BUNDLES_TABLE}(publication_bundle_id) ON DELETE RESTRICT,
          run_id TEXT NOT NULL REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE RESTRICT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_PUBLICATION_ACTIVATION_AUDIT_TABLE} (
          activation_audit_id TEXT PRIMARY KEY,
          target_environment TEXT NOT NULL,
          run_id TEXT NOT NULL REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE RESTRICT,
          publication_bundle_id TEXT NOT NULL REFERENCES ${STEP1_PUBLICATION_BUNDLES_TABLE}(publication_bundle_id) ON DELETE RESTRICT,
          previous_active_publication_id TEXT,
          new_active_publication_id TEXT NOT NULL,
          assessment_report_id TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_publication_activation_audit_target_environment
        ON ${STEP1_PUBLICATION_ACTIVATION_AUDIT_TABLE} (target_environment, created_at DESC)
      `);
      await pool.query(`
        CREATE TABLE IF NOT EXISTS ${STEP1_DEFERRED_FOLLOWUP_JOBS_TABLE} (
          followup_job_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES ${RUNTIME_REFRESH_RUNS_TABLE}(run_id) ON DELETE CASCADE,
          publication_bundle_id TEXT NOT NULL REFERENCES ${STEP1_PUBLICATION_BUNDLES_TABLE}(publication_bundle_id) ON DELETE RESTRICT,
          target_environment TEXT NOT NULL,
          phase_name TEXT NOT NULL,
          classification TEXT NOT NULL,
          status TEXT NOT NULL,
          publication_manifest_path TEXT NOT NULL,
          ticket_path TEXT NOT NULL,
          operator_visible_status TEXT NOT NULL,
          failure_code TEXT,
          failure_detail TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);
      await pool.query(`
        CREATE INDEX IF NOT EXISTS idx_deferred_followup_jobs_run_id
        ON ${STEP1_DEFERRED_FOLLOWUP_JOBS_TABLE} (run_id, created_at DESC)
      `);
    },
    async writeRunRow(row: Step1RuntimeRefreshRunRow): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      await pool.query(
        `
          INSERT INTO ${RUNTIME_REFRESH_RUNS_TABLE} (
            run_id,
            mode,
            trigger_source,
            requested_by,
            started_at,
            completed_at,
            report_generated_at_utc,
            rows_written,
            report_status,
            validation_status,
            validation_report_path,
            request_artifact_path,
            bundle_generated_at_utc,
            snapshot_publication_id,
            quote_publication_id,
            quote_binding_status,
            activation_state,
            serving_state,
            blocking_reason_code,
            blocking_reason_detail,
            is_active_publication,
            current_phase,
            current_phase_process_status,
            current_phase_started_at,
            current_phase_completed_at,
            current_phase_last_heartbeat_at,
            current_phase_failure_code,
            current_phase_failure_detail,
            failure_code,
            failure_detail,
            created_at,
            updated_at
          )
          VALUES (
            $1,
            $2,
            $3,
            $4,
            $5::timestamptz,
            $6::timestamptz,
            $7::timestamptz,
            $8,
            $9,
            $10,
            $11,
            $12,
            $13::timestamptz,
            $14,
            $15,
            $16,
            $17,
            $18,
            $19,
            $20,
            $21,
            $22,
            $23,
            $24::timestamptz,
            $25::timestamptz,
            $26::timestamptz,
            $27,
            $28,
            $29,
            $30,
            $31::timestamptz,
            $32::timestamptz
          )
          ON CONFLICT (run_id)
          DO UPDATE SET
            mode = EXCLUDED.mode,
            trigger_source = EXCLUDED.trigger_source,
            requested_by = EXCLUDED.requested_by,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            report_generated_at_utc = EXCLUDED.report_generated_at_utc,
            rows_written = EXCLUDED.rows_written,
            report_status = EXCLUDED.report_status,
            validation_status = EXCLUDED.validation_status,
            validation_report_path = EXCLUDED.validation_report_path,
            request_artifact_path = EXCLUDED.request_artifact_path,
            bundle_generated_at_utc = EXCLUDED.bundle_generated_at_utc,
            snapshot_publication_id = EXCLUDED.snapshot_publication_id,
            quote_publication_id = EXCLUDED.quote_publication_id,
            quote_binding_status = EXCLUDED.quote_binding_status,
            activation_state = EXCLUDED.activation_state,
            serving_state = EXCLUDED.serving_state,
            blocking_reason_code = EXCLUDED.blocking_reason_code,
            blocking_reason_detail = EXCLUDED.blocking_reason_detail,
            is_active_publication = EXCLUDED.is_active_publication,
            current_phase = EXCLUDED.current_phase,
            current_phase_process_status = EXCLUDED.current_phase_process_status,
            current_phase_started_at = EXCLUDED.current_phase_started_at,
            current_phase_completed_at = EXCLUDED.current_phase_completed_at,
            current_phase_last_heartbeat_at = EXCLUDED.current_phase_last_heartbeat_at,
            current_phase_failure_code = EXCLUDED.current_phase_failure_code,
            current_phase_failure_detail = EXCLUDED.current_phase_failure_detail,
            failure_code = EXCLUDED.failure_code,
            failure_detail = EXCLUDED.failure_detail,
            updated_at = EXCLUDED.updated_at
        `,
        [
          row.run_id,
          row.mode,
          row.trigger_source,
          row.requested_by,
          toIsoUtc(row.started_at, "started_at"),
          row.completed_at ? toIsoUtc(row.completed_at, "completed_at") : null,
          row.report_generated_at_utc ? toIsoUtc(row.report_generated_at_utc, "report_generated_at_utc") : null,
          row.rows_written ?? null,
          row.report_status,
          row.validation_status ?? null,
          row.validation_report_path ?? null,
          row.request_artifact_path,
          row.bundle_generated_at_utc ? toIsoUtc(row.bundle_generated_at_utc, "bundle_generated_at_utc") : null,
          row.snapshot_publication_id ?? null,
          row.quote_publication_id ?? null,
          row.quote_binding_status ?? null,
          row.activation_state ?? null,
          row.serving_state ?? null,
          row.blocking_reason_code ?? null,
          row.blocking_reason_detail ?? null,
          row.is_active_publication === true,
          row.current_phase,
          row.current_phase_process_status,
          row.current_phase_started_at ? toIsoUtc(row.current_phase_started_at, "current_phase_started_at") : null,
          row.current_phase_completed_at
            ? toIsoUtc(row.current_phase_completed_at, "current_phase_completed_at")
            : null,
          row.current_phase_last_heartbeat_at
            ? toIsoUtc(row.current_phase_last_heartbeat_at, "current_phase_last_heartbeat_at")
            : null,
          row.current_phase_failure_code,
          row.current_phase_failure_detail,
          row.failure_code,
          row.failure_detail,
          toIsoUtc(row.created_at, "created_at"),
          toIsoUtc(row.updated_at, "updated_at"),
        ],
      );
    },
    async writePhaseRow(row: Step1RuntimeRefreshPhaseRow): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      await pool.query(
        `
          INSERT INTO ${RUNTIME_REFRESH_RUN_PHASES_TABLE} (
            run_id,
            phase_name,
            input_contract,
            process_status,
            started_at,
            completed_at,
            output_contract,
            failure_code,
            failure_detail,
            last_heartbeat_at,
            created_at,
            updated_at
          )
          VALUES (
            $1,
            $2,
            $3::jsonb,
            $4,
            $5::timestamptz,
            $6::timestamptz,
            $7::jsonb,
            $8,
            $9,
            $10::timestamptz,
            $11::timestamptz,
            $12::timestamptz
          )
          ON CONFLICT (run_id, phase_name)
          DO UPDATE SET
            input_contract = EXCLUDED.input_contract,
            process_status = EXCLUDED.process_status,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            output_contract = EXCLUDED.output_contract,
            failure_code = EXCLUDED.failure_code,
            failure_detail = EXCLUDED.failure_detail,
            last_heartbeat_at = EXCLUDED.last_heartbeat_at,
            updated_at = EXCLUDED.updated_at
        `,
        [
          row.run_id,
          row.phase_name,
          row.input_contract ? JSON.stringify(row.input_contract) : null,
          row.process_status,
          row.started_at ? toIsoUtc(row.started_at, "phase.started_at") : null,
          row.completed_at ? toIsoUtc(row.completed_at, "phase.completed_at") : null,
          row.output_contract ? JSON.stringify(row.output_contract) : null,
          row.failure_code,
          row.failure_detail,
          row.last_heartbeat_at ? toIsoUtc(row.last_heartbeat_at, "phase.last_heartbeat_at") : null,
          toIsoUtc(row.created_at, "phase.created_at"),
          toIsoUtc(row.updated_at, "phase.updated_at"),
        ],
      );

      await pool.query(
        `
          UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
          SET current_phase = $2,
              current_phase_process_status = $3,
              current_phase_started_at = $4::timestamptz,
              current_phase_completed_at = $5::timestamptz,
              current_phase_last_heartbeat_at = $6::timestamptz,
              current_phase_failure_code = $7,
              current_phase_failure_detail = $8,
              updated_at = $9::timestamptz
          WHERE run_id = $1
        `,
        [
          row.run_id,
          row.phase_name,
          row.process_status,
          row.started_at ? toIsoUtc(row.started_at, "phase.started_at") : null,
          row.completed_at ? toIsoUtc(row.completed_at, "phase.completed_at") : null,
          row.last_heartbeat_at ? toIsoUtc(row.last_heartbeat_at, "phase.last_heartbeat_at") : null,
          row.failure_code,
          row.failure_detail,
          toIsoUtc(row.updated_at, "phase.updated_at"),
        ],
      );
    },
    async writeCandidateBundleRow(row: Step1CandidateBundleRow): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      await pool.query(
        `
          INSERT INTO ${STEP1_CANDIDATE_BUNDLES_TABLE} (
            run_id,
            candidate_bundle_id,
            normalized_package_id,
            policy_set_id,
            model_set_id,
            config_set_id,
            bundle_class,
            requested_run_mode,
            target_environment,
            deterministic_build_timestamp_utc,
            dependency_classification_register,
            assessment_artifact_references,
            request_artifact_path,
            manifest_path,
            manifest_digest_sha256,
            created_at,
            updated_at
          )
          VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            $6,
            $7,
            $8,
            $9,
            $10::timestamptz,
            $11::jsonb,
            $12::jsonb,
            $13,
            $14,
            $15,
            $16::timestamptz,
            $17::timestamptz
          )
          ON CONFLICT (run_id)
          DO UPDATE SET
            candidate_bundle_id = EXCLUDED.candidate_bundle_id,
            normalized_package_id = EXCLUDED.normalized_package_id,
            policy_set_id = EXCLUDED.policy_set_id,
            model_set_id = EXCLUDED.model_set_id,
            config_set_id = EXCLUDED.config_set_id,
            bundle_class = EXCLUDED.bundle_class,
            requested_run_mode = EXCLUDED.requested_run_mode,
            target_environment = EXCLUDED.target_environment,
            deterministic_build_timestamp_utc = EXCLUDED.deterministic_build_timestamp_utc,
            dependency_classification_register = EXCLUDED.dependency_classification_register,
            assessment_artifact_references = EXCLUDED.assessment_artifact_references,
            request_artifact_path = EXCLUDED.request_artifact_path,
            manifest_path = EXCLUDED.manifest_path,
            manifest_digest_sha256 = EXCLUDED.manifest_digest_sha256,
            updated_at = EXCLUDED.updated_at
        `,
        [
          row.run_id,
          row.candidate_bundle_id,
          row.normalized_package_id,
          row.policy_set_id,
          row.model_set_id,
          row.config_set_id,
          row.bundle_class,
          row.requested_run_mode,
          row.target_environment,
          toIsoUtc(row.deterministic_build_timestamp_utc, "candidate_bundle.deterministic_build_timestamp_utc"),
          JSON.stringify(row.dependency_classification_register),
          JSON.stringify(row.assessment_artifact_references),
          row.request_artifact_path,
          row.manifest_path,
          row.manifest_digest_sha256,
          toIsoUtc(row.created_at, "candidate_bundle.created_at"),
          toIsoUtc(row.updated_at, "candidate_bundle.updated_at"),
        ],
      );
    },
    async writeAssessmentReportRow(row: Step1AssessmentReportRow): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      await pool.query(
        `
          INSERT INTO ${STEP1_ASSESSMENT_REPORTS_TABLE} (
            run_id,
            assessment_report_id,
            candidate_bundle_id,
            assessment_rule_set_id,
            disposition,
            blocking_reason_codes,
            blocking_reason_details,
            evidence_references,
            candidate_bundle_manifest_path,
            report_path,
            publication_allowed,
            created_at,
            updated_at
          )
          VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            $6::jsonb,
            $7::jsonb,
            $8::jsonb,
            $9,
            $10,
            $11,
            $12::timestamptz,
            $13::timestamptz
          )
          ON CONFLICT (run_id)
          DO UPDATE SET
            assessment_report_id = EXCLUDED.assessment_report_id,
            candidate_bundle_id = EXCLUDED.candidate_bundle_id,
            assessment_rule_set_id = EXCLUDED.assessment_rule_set_id,
            disposition = EXCLUDED.disposition,
            blocking_reason_codes = EXCLUDED.blocking_reason_codes,
            blocking_reason_details = EXCLUDED.blocking_reason_details,
            evidence_references = EXCLUDED.evidence_references,
            candidate_bundle_manifest_path = EXCLUDED.candidate_bundle_manifest_path,
            report_path = EXCLUDED.report_path,
            publication_allowed = EXCLUDED.publication_allowed,
            updated_at = EXCLUDED.updated_at
        `,
        [
          row.run_id,
          row.assessment_report_id,
          row.candidate_bundle_id,
          row.assessment_rule_set_id,
          row.disposition,
          JSON.stringify(row.blocking_reason_codes),
          JSON.stringify(row.blocking_reason_details),
          JSON.stringify(row.evidence_references),
          row.candidate_bundle_manifest_path,
          row.report_path,
          row.publication_allowed,
          toIsoUtc(row.created_at, "assessment_report.created_at"),
          toIsoUtc(row.updated_at, "assessment_report.updated_at"),
        ],
      );
    },
    async readActivePublicationPointer(targetEnvironment: string): Promise<Step1ActivePublicationPointerRow | null> {
      const pool = resolveRuntimePostgresPool();
      const result = await pool.query<Record<string, unknown>>(
        `
          SELECT
            target_environment,
            publication_bundle_id,
            run_id,
            created_at,
            updated_at
          FROM ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE}
          WHERE target_environment = $1
          LIMIT 1
        `,
        [targetEnvironment],
      );
      if (result.rows.length === 0) return null;
      return parseStoredStep1ActivePublicationPointerRow(result.rows[0]);
    },
    async commitPublicationTransaction(transaction: Step1PublicationCommitTransaction): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      const client = await pool.connect();
      try {
        await client.query("BEGIN");
        try {
          const row = transaction.publicationBundleRow;
          await client.query(
            `
              INSERT INTO ${STEP1_PUBLICATION_BUNDLES_TABLE} (
                publication_bundle_id,
                run_id,
                candidate_bundle_id,
                assessment_report_id,
                normalized_package_id,
                policy_set_id,
                model_set_id,
                config_set_id,
                bundle_class,
                target_environment,
                previous_active_publication_id,
                activation_audit_id,
                candidate_bundle_manifest_path,
                assessment_report_path,
                manifest_path,
                manifest_digest_sha256,
                created_at,
                updated_at
              )
              VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9,
                $10,
                $11,
                $12,
                $13,
                $14,
                $15,
                $16,
                $17::timestamptz,
                $18::timestamptz
              )
            `,
            [
              row.publication_bundle_id,
              row.run_id,
              row.candidate_bundle_id,
              row.assessment_report_id,
              row.normalized_package_id,
              row.policy_set_id,
              row.model_set_id,
              row.config_set_id,
              row.bundle_class,
              row.target_environment,
              row.previous_active_publication_id,
              row.activation_audit_id,
              row.candidate_bundle_manifest_path,
              row.assessment_report_path,
              row.manifest_path,
              row.manifest_digest_sha256,
              toIsoUtc(row.created_at, "publication_bundle.created_at"),
              toIsoUtc(row.updated_at, "publication_bundle.updated_at"),
            ],
          );
        } catch (error) {
          const detail = error instanceof Error ? error.message : "publication bundle insert failed";
          throw new Error(`publication_bundle_write_failure:${detail}`);
        }

        try {
          const row = transaction.activePublicationPointerRow;
          await client.query(
            `
              INSERT INTO ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE} (
                target_environment,
                publication_bundle_id,
                run_id,
                created_at,
                updated_at
              )
              VALUES (
                $1,
                $2,
                $3,
                $4::timestamptz,
                $5::timestamptz
              )
              ON CONFLICT (target_environment)
              DO UPDATE SET
                publication_bundle_id = EXCLUDED.publication_bundle_id,
                run_id = EXCLUDED.run_id,
                updated_at = EXCLUDED.updated_at
            `,
            [
              row.target_environment,
              row.publication_bundle_id,
              row.run_id,
              toIsoUtc(row.created_at, "active_publication_pointer.created_at"),
              toIsoUtc(row.updated_at, "active_publication_pointer.updated_at"),
            ],
          );
        } catch (error) {
          const detail = error instanceof Error ? error.message : "active publication pointer write failed";
          throw new Error(`activation_pointer_write_failure:${detail}`);
        }

        try {
          const row = transaction.publicationActivationAuditRow;
          await client.query(
            `
              INSERT INTO ${STEP1_PUBLICATION_ACTIVATION_AUDIT_TABLE} (
                activation_audit_id,
                target_environment,
                run_id,
                publication_bundle_id,
                previous_active_publication_id,
                new_active_publication_id,
                assessment_report_id,
                created_at
              )
              VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8::timestamptz
              )
            `,
            [
              row.activation_audit_id,
              row.target_environment,
              row.run_id,
              row.publication_bundle_id,
              row.previous_active_publication_id,
              row.new_active_publication_id,
              row.assessment_report_id,
              toIsoUtc(row.created_at, "publication_activation_audit.created_at"),
            ],
          );
        } catch (error) {
          const detail = error instanceof Error ? error.message : "publication activation audit write failed";
          throw new Error(`activation_audit_write_failure:${detail}`);
        }

        try {
          const row = transaction.phaseRow;
          await client.query(
            `
              INSERT INTO ${RUNTIME_REFRESH_RUN_PHASES_TABLE} (
                run_id,
                phase_name,
                input_contract,
                process_status,
                started_at,
                completed_at,
                output_contract,
                failure_code,
                failure_detail,
                last_heartbeat_at,
                created_at,
                updated_at
              )
              VALUES (
                $1,
                $2,
                $3::jsonb,
                $4,
                $5::timestamptz,
                $6::timestamptz,
                $7::jsonb,
                $8,
                $9,
                $10::timestamptz,
                $11::timestamptz,
                $12::timestamptz
              )
              ON CONFLICT (run_id, phase_name)
              DO UPDATE SET
                input_contract = EXCLUDED.input_contract,
                process_status = EXCLUDED.process_status,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                output_contract = EXCLUDED.output_contract,
                failure_code = EXCLUDED.failure_code,
                failure_detail = EXCLUDED.failure_detail,
                last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                updated_at = EXCLUDED.updated_at
            `,
            [
              row.run_id,
              row.phase_name,
              row.input_contract ? JSON.stringify(row.input_contract) : null,
              row.process_status,
              row.started_at ? toIsoUtc(row.started_at, "publication_commit_phase.started_at") : null,
              row.completed_at ? toIsoUtc(row.completed_at, "publication_commit_phase.completed_at") : null,
              row.output_contract ? JSON.stringify(row.output_contract) : null,
              row.failure_code,
              row.failure_detail,
              row.last_heartbeat_at ? toIsoUtc(row.last_heartbeat_at, "publication_commit_phase.last_heartbeat_at") : null,
              toIsoUtc(row.created_at, "publication_commit_phase.created_at"),
              toIsoUtc(row.updated_at, "publication_commit_phase.updated_at"),
            ],
          );
          await client.query(
            `
              UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
              SET current_phase = $2,
                  current_phase_process_status = $3,
                  current_phase_started_at = $4::timestamptz,
                  current_phase_completed_at = $5::timestamptz,
                  current_phase_last_heartbeat_at = $6::timestamptz,
                  current_phase_failure_code = $7,
                  current_phase_failure_detail = $8,
                  updated_at = $9::timestamptz
              WHERE run_id = $1
            `,
            [
              row.run_id,
              row.phase_name,
              row.process_status,
              row.started_at ? toIsoUtc(row.started_at, "publication_commit_phase.started_at") : null,
              row.completed_at ? toIsoUtc(row.completed_at, "publication_commit_phase.completed_at") : null,
              row.last_heartbeat_at ? toIsoUtc(row.last_heartbeat_at, "publication_commit_phase.last_heartbeat_at") : null,
              row.failure_code,
              row.failure_detail,
              toIsoUtc(row.updated_at, "publication_commit_phase.updated_at"),
            ],
          );
        } catch (error) {
          const detail = error instanceof Error ? error.message : "publication commit phase persistence failed";
          throw new Error(`state_persistence_failure:${detail}`);
        }

        await client.query("COMMIT");
      } catch (error) {
        try {
          await client.query("ROLLBACK");
        } catch {
          // Ignore rollback failures.
        }
        throw error;
      }
      finally {
        client.release();
      }
    },
    async writeDeferredFollowupJobRow(row: Step1DeferredFollowupJobRow): Promise<void> {
      const pool = resolveRuntimePostgresPool();
      await pool.query(
        `
          INSERT INTO ${STEP1_DEFERRED_FOLLOWUP_JOBS_TABLE} (
            followup_job_id,
            run_id,
            publication_bundle_id,
            target_environment,
            phase_name,
            classification,
            status,
            publication_manifest_path,
            ticket_path,
            operator_visible_status,
            failure_code,
            failure_detail,
            created_at,
            updated_at
          )
          VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            $6,
            $7,
            $8,
            $9,
            $10,
            $11,
            $12,
            $13::timestamptz,
            $14::timestamptz
          )
          ON CONFLICT (followup_job_id)
          DO UPDATE SET
            run_id = EXCLUDED.run_id,
            publication_bundle_id = EXCLUDED.publication_bundle_id,
            target_environment = EXCLUDED.target_environment,
            phase_name = EXCLUDED.phase_name,
            classification = EXCLUDED.classification,
            status = EXCLUDED.status,
            publication_manifest_path = EXCLUDED.publication_manifest_path,
            ticket_path = EXCLUDED.ticket_path,
            operator_visible_status = EXCLUDED.operator_visible_status,
            failure_code = EXCLUDED.failure_code,
            failure_detail = EXCLUDED.failure_detail,
            updated_at = EXCLUDED.updated_at
        `,
        [
          row.followup_job_id,
          row.run_id,
          row.publication_bundle_id,
          row.target_environment,
          row.phase_name,
          row.classification,
          row.status,
          row.publication_manifest_path,
          row.ticket_path,
          row.operator_visible_status,
          row.failure_code,
          row.failure_detail,
          toIsoUtc(row.created_at, "deferred_followup_job.created_at"),
          toIsoUtc(row.updated_at, "deferred_followup_job.updated_at"),
        ],
      );
    },
  };
}

export async function readStep1ProofStore(storePath: string): Promise<Step1ProofStore> {
  return readProofStore(storePath);
}

export function createStep1RunRow(params: {
  runId: string;
  mode: string;
  triggerSource: string;
  requestedBy: string;
  requestedAtUtc: string;
  requestArtifactPath: string;
  phaseName: string;
  phaseProcessStatus: string;
}): Step1RuntimeRefreshRunRow {
  const timestamp = toIsoUtc(params.requestedAtUtc, "requestedAtUtc");
  return {
    run_id: params.runId,
    mode: params.mode,
    trigger_source: params.triggerSource,
    requested_by: params.requestedBy,
    started_at: timestamp,
    completed_at: null,
    report_status: "accepted",
    request_artifact_path: params.requestArtifactPath,
    current_phase: params.phaseName,
    current_phase_process_status: params.phaseProcessStatus,
    current_phase_started_at: timestamp,
    current_phase_completed_at: null,
    current_phase_last_heartbeat_at: timestamp,
    current_phase_failure_code: null,
    current_phase_failure_detail: null,
    failure_code: null,
    failure_detail: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

export function createStep1SuccessMirrorRunRow(params: {
  baseRunRow: Step1RuntimeRefreshRunRow;
  publicationCommittedAtUtc: string;
  followupStatus: Step1FollowupStatus;
  followupCreatedAtUtc: string;
}): Step1RuntimeRefreshRunRow {
  const publicationCommittedAtUtc = toIsoUtc(
    params.publicationCommittedAtUtc,
    "step1_success_mirror.publication_committed_at_utc",
  );
  const followupCreatedAtUtc = toIsoUtc(
    params.followupCreatedAtUtc,
    "step1_success_mirror.followup_created_at_utc",
  );

  return {
    ...params.baseRunRow,
    completed_at: publicationCommittedAtUtc,
    report_generated_at_utc: publicationCommittedAtUtc,
    report_status: "ok",
    bundle_generated_at_utc: publicationCommittedAtUtc,
    activation_state: "activated",
    serving_state: "allowed",
    blocking_reason_code: null,
    blocking_reason_detail: null,
    current_phase: STEP1_QUOTE_CACHE_REFRESH_PHASE,
    current_phase_process_status: params.followupStatus,
    current_phase_started_at: followupCreatedAtUtc,
    current_phase_completed_at: params.followupStatus === "failed" ? followupCreatedAtUtc : null,
    current_phase_last_heartbeat_at: followupCreatedAtUtc,
    current_phase_failure_code: null,
    current_phase_failure_detail: null,
    failure_code: null,
    failure_detail: null,
    updated_at: followupCreatedAtUtc,
  };
}

export function createCandidateBuildPhaseRow(params: {
  runId: string;
  requestedAtUtc: string;
  requestArtifactPath: string;
  requestRecord: Step1RunRequestRecord;
}): Step1RuntimeRefreshPhaseRow {
  const timestamp = toIsoUtc(params.requestedAtUtc, "requestedAtUtc");
  return {
    run_id: params.runId,
    phase_name: STEP1_CANDIDATE_BUILD_PHASE,
    input_contract: {
      request_artifact_path: params.requestArtifactPath,
      normalized_package_id: params.requestRecord.normalized_package_id,
      policy_set_id: params.requestRecord.policy_set_id,
      model_set_id: params.requestRecord.model_set_id,
      config_set_id: params.requestRecord.config_set_id,
      bundle_class: params.requestRecord.bundle_class,
      source_package_identities: params.requestRecord.source_package_identities ?? [],
      target_environment: params.requestRecord.target_environment,
      dependency_classification_register: params.requestRecord.dependency_classification_register,
    },
    process_status: "pending",
    started_at: timestamp,
    completed_at: null,
    output_contract: null,
    failure_code: null,
    failure_detail: null,
    last_heartbeat_at: timestamp,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

export function createCandidateBuildCompletedPhaseRow(params: {
  runId: string;
  startedAtUtc: string;
  completedAtUtc: string;
  requestArtifactPath: string;
  requestRecord: Step1RunRequestRecord;
  manifestPath: string;
  candidateBundleId: string;
  manifestDigestSha256: string;
  normalizedPackageManifestId: string;
  normalizedPackageManifestPath: string;
  normalizedPackageManifestDigestSha256: string;
  sourcePackageIds: string[];
}): Step1RuntimeRefreshPhaseRow {
  const startedAtUtc = toIsoUtc(params.startedAtUtc, "startedAtUtc");
  const completedAtUtc = toIsoUtc(params.completedAtUtc, "completedAtUtc");
  return {
    run_id: params.runId,
    phase_name: STEP1_CANDIDATE_BUILD_PHASE,
    input_contract: {
      request_artifact_path: params.requestArtifactPath,
      normalized_package_id: params.requestRecord.normalized_package_id,
      policy_set_id: params.requestRecord.policy_set_id,
      model_set_id: params.requestRecord.model_set_id,
      config_set_id: params.requestRecord.config_set_id,
      bundle_class: params.requestRecord.bundle_class,
      source_package_identities: params.requestRecord.source_package_identities ?? [],
      target_environment: params.requestRecord.target_environment,
      dependency_classification_register: params.requestRecord.dependency_classification_register,
    },
    process_status: "completed",
    started_at: startedAtUtc,
    completed_at: completedAtUtc,
    output_contract: {
      candidate_bundle_id: params.candidateBundleId,
      candidate_bundle_manifest_path: params.manifestPath,
      manifest_digest_sha256: params.manifestDigestSha256,
      normalized_package_id: params.requestRecord.normalized_package_id,
      normalized_package_manifest_id: params.normalizedPackageManifestId,
      normalized_package_manifest_path: params.normalizedPackageManifestPath,
      normalized_package_manifest_digest_sha256: params.normalizedPackageManifestDigestSha256,
      source_package_ids: params.sourcePackageIds,
    },
    failure_code: null,
    failure_detail: null,
    last_heartbeat_at: completedAtUtc,
    created_at: startedAtUtc,
    updated_at: completedAtUtc,
  };
}

export function sha256Text(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

export function stableJsonStringify(value: unknown): string {
  const canonicalize = (current: unknown): unknown => {
    if (Array.isArray(current)) {
      return current.map((entry) => canonicalize(entry));
    }
    if (current && typeof current === "object") {
      const record = current as Record<string, unknown>;
      const entries = Object.keys(record)
        .sort((left, right) => left.localeCompare(right))
        .map((key) => [key, canonicalize(record[key])] as const);
      return Object.fromEntries(entries);
    }
    return current;
  };

  return JSON.stringify(canonicalize(value));
}

export function deterministicTimestampFromDigest(hexDigest: string): string {
  const normalized = String(hexDigest ?? "").trim().toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(normalized)) {
    throw new Error("deterministicTimestampFromDigest requires a 64-character hex digest.");
  }

  const baseMs = Date.UTC(2020, 0, 1, 0, 0, 0, 0);
  const spanSeconds = 20 * 365 * 24 * 60 * 60;
  const offsetSeconds = Number.parseInt(normalized.slice(0, 12), 16) % spanSeconds;
  return new Date(baseMs + offsetSeconds * 1000).toISOString();
}

export function nowExecutionTimestampUtc(): string {
  return new Date().toISOString();
}

export function createCandidateBundleRow(params: {
  runId: string;
  requestArtifactPath: string;
  manifestPath: string;
  manifestDigestSha256: string;
  createdAtUtc: string;
  manifest: Step1CandidateBundleManifest;
}): Step1CandidateBundleRow {
  const createdAtUtc = toIsoUtc(params.createdAtUtc, "createdAtUtc");
  return {
    run_id: params.runId,
    candidate_bundle_id: params.manifest.candidate_bundle_id,
    normalized_package_id: params.manifest.normalized_package_id,
    policy_set_id: params.manifest.policy_set_id,
    model_set_id: params.manifest.model_set_id,
    config_set_id: params.manifest.config_set_id,
    bundle_class: params.manifest.bundle_class,
    requested_run_mode: params.manifest.requested_run_mode,
    target_environment: params.manifest.target_environment,
    deterministic_build_timestamp_utc: params.manifest.deterministic_build_timestamp_utc,
    dependency_classification_register: params.manifest.dependency_classification_register,
    assessment_artifact_references: params.manifest.assessment_artifact_references,
    request_artifact_path: params.requestArtifactPath,
    manifest_path: params.manifestPath,
    manifest_digest_sha256: params.manifestDigestSha256,
    created_at: createdAtUtc,
    updated_at: createdAtUtc,
  };
}

function assessmentFailureCode(
  blockingReasonDetails: Step1AssessmentBlockingReason[],
  disposition: Step1AssessmentDisposition,
): string | null {
  if (disposition !== "fail") return null;
  if (blockingReasonDetails.some((reason) => reason.dependency_classification === "publication_critical")) {
    return "critical_dependency_unsatisfied";
  }
  return "assessment_failure";
}

function assessmentFailureDetail(
  blockingReasonDetails: Step1AssessmentBlockingReason[],
  disposition: Step1AssessmentDisposition,
): string | null {
  if (disposition !== "fail") return null;
  const details = blockingReasonDetails
    .map((reason) => `${reason.reason_code}: ${reason.reason_detail}`)
    .join("; ");
  return details || "Assessment failed with one or more blocking reasons.";
}

function firstEvidenceReferenceByKind(
  evidenceReferences: Step1AssessmentEvidenceReference[],
  evidenceKind: string,
): Step1AssessmentEvidenceReference | null {
  return evidenceReferences.find((entry) => entry.evidence_kind === evidenceKind) ?? null;
}

function evidenceIdsByKind(
  evidenceReferences: Step1AssessmentEvidenceReference[],
  evidenceKind: string,
): string[] {
  return evidenceReferences
    .filter((entry) => entry.evidence_kind === evidenceKind)
    .map((entry) => entry.evidence_id);
}

export function createAssessmentReportRow(params: {
  runId: string;
  candidateBundleManifestPath: string;
  reportPath: string;
  createdAtUtc: string;
  report: Step1AssessmentReportArtifact;
}): Step1AssessmentReportRow {
  const createdAtUtc = toIsoUtc(params.createdAtUtc, "createdAtUtc");
  return {
    run_id: params.runId,
    assessment_report_id: params.report.assessment_report_id,
    candidate_bundle_id: params.report.candidate_bundle_id,
    assessment_rule_set_id: params.report.assessment_rule_set_id,
    disposition: params.report.disposition,
    blocking_reason_codes: params.report.blocking_reason_codes,
    blocking_reason_details: params.report.blocking_reason_details,
    evidence_references: params.report.evidence_references,
    candidate_bundle_manifest_path: params.candidateBundleManifestPath,
    report_path: params.reportPath,
    publication_allowed: params.report.publication_allowed,
    created_at: createdAtUtc,
    updated_at: createdAtUtc,
  };
}

export function createAssessmentGatePhaseRow(params: {
  runId: string;
  candidateBundleManifestPath: string;
  reportPath: string;
  completedAtUtc: string;
  report: Step1AssessmentReportArtifact;
}): Step1RuntimeRefreshPhaseRow {
  const completedAtUtc = toIsoUtc(params.completedAtUtc, "completedAtUtc");
  const normalizedPackageIdentity = firstEvidenceReferenceByKind(
    params.report.evidence_references,
    "normalized_package_identity",
  );
  const normalizedPackageManifest = firstEvidenceReferenceByKind(
    params.report.evidence_references,
    "normalized_package_manifest",
  );
  const sourcePackageIds = evidenceIdsByKind(params.report.evidence_references, "source_package_manifest");
  return {
    run_id: params.runId,
    phase_name: STEP1_ASSESSMENT_GATE_PHASE,
    input_contract: {
      candidate_bundle_manifest_path: params.candidateBundleManifestPath,
      assessment_rule_set_id: params.report.assessment_rule_set_id,
      candidate_bundle_id: params.report.candidate_bundle_id,
      normalized_package_id: normalizedPackageIdentity?.evidence_id ?? null,
      normalized_package_manifest_path: normalizedPackageManifest?.evidence_path ?? null,
      source_package_ids: sourcePackageIds,
    },
    process_status: params.report.disposition === "pass" ? "completed" : "blocked",
    started_at: completedAtUtc,
    completed_at: completedAtUtc,
    output_contract: {
      assessment_report_id: params.report.assessment_report_id,
      assessment_report_path: params.reportPath,
      candidate_bundle_id: params.report.candidate_bundle_id,
      normalized_package_id: normalizedPackageIdentity?.evidence_id ?? null,
      source_package_ids: sourcePackageIds,
      disposition: params.report.disposition,
      publication_allowed: params.report.publication_allowed,
      blocking_reason_codes: params.report.blocking_reason_codes,
    },
    failure_code: assessmentFailureCode(params.report.blocking_reason_details, params.report.disposition),
    failure_detail: assessmentFailureDetail(params.report.blocking_reason_details, params.report.disposition),
    last_heartbeat_at: completedAtUtc,
    created_at: completedAtUtc,
    updated_at: completedAtUtc,
  };
}

export function createPublicationBundleRow(params: {
  manifest: Step1PublicationBundleManifest;
  manifestPath: string;
  manifestDigestSha256: string;
}): Step1PublicationBundleRow {
  const committedAtUtc = toIsoUtc(params.manifest.committed_at_utc, "publication_bundle.committed_at_utc");
  return {
    publication_bundle_id: params.manifest.publication_bundle_id,
    run_id: params.manifest.run_id,
    candidate_bundle_id: params.manifest.candidate_bundle_id,
    assessment_report_id: params.manifest.assessment_report_id,
    normalized_package_id: params.manifest.normalized_package_id,
    policy_set_id: params.manifest.policy_set_id,
    model_set_id: params.manifest.model_set_id,
    config_set_id: params.manifest.config_set_id,
    bundle_class: params.manifest.bundle_class,
    target_environment: params.manifest.target_environment,
    previous_active_publication_id: params.manifest.previous_active_publication_id,
    activation_audit_id: params.manifest.activation_audit_id,
    candidate_bundle_manifest_path: params.manifest.candidate_bundle_manifest_path,
    assessment_report_path: params.manifest.assessment_report_path,
    manifest_path: params.manifestPath,
    manifest_digest_sha256: params.manifestDigestSha256,
    created_at: committedAtUtc,
    updated_at: committedAtUtc,
  };
}

export function createActivePublicationPointerRow(params: {
  targetEnvironment: string;
  publicationBundleId: string;
  runId: string;
  committedAtUtc: string;
}): Step1ActivePublicationPointerRow {
  const committedAtUtc = toIsoUtc(params.committedAtUtc, "active_publication_pointer.committed_at_utc");
  return {
    target_environment: params.targetEnvironment,
    publication_bundle_id: params.publicationBundleId,
    run_id: params.runId,
    created_at: committedAtUtc,
    updated_at: committedAtUtc,
  };
}

export function createPublicationActivationAuditRow(params: {
  activationAuditId: string;
  targetEnvironment: string;
  runId: string;
  publicationBundleId: string;
  previousActivePublicationId: string | null;
  newActivePublicationId: string;
  assessmentReportId: string;
  committedAtUtc: string;
}): Step1PublicationActivationAuditRow {
  const committedAtUtc = toIsoUtc(params.committedAtUtc, "publication_activation_audit.committed_at_utc");
  return {
    activation_audit_id: params.activationAuditId,
    target_environment: params.targetEnvironment,
    run_id: params.runId,
    publication_bundle_id: params.publicationBundleId,
    previous_active_publication_id: params.previousActivePublicationId,
    new_active_publication_id: params.newActivePublicationId,
    assessment_report_id: params.assessmentReportId,
    created_at: committedAtUtc,
  };
}

export function createPublicationCommitPhaseRow(params: {
  runId: string;
  targetEnvironment: string;
  candidateBundleId: string;
  assessmentReportId: string;
  assessmentReportPath: string;
  publicationBundleId: string;
  publicationManifestPath: string;
  activationAuditId: string;
  previousActivePublicationId: string | null;
  committedAtUtc: string;
}): Step1RuntimeRefreshPhaseRow {
  const committedAtUtc = toIsoUtc(params.committedAtUtc, "publication_commit.completedAtUtc");
  return {
    run_id: params.runId,
    phase_name: STEP1_PUBLICATION_COMMIT_PHASE,
    input_contract: {
      assessment_report_id: params.assessmentReportId,
      assessment_report_path: params.assessmentReportPath,
      candidate_bundle_id: params.candidateBundleId,
      target_environment: params.targetEnvironment,
    },
    process_status: "completed",
    started_at: committedAtUtc,
    completed_at: committedAtUtc,
    output_contract: {
      publication_bundle_id: params.publicationBundleId,
      publication_manifest_path: params.publicationManifestPath,
      activation_audit_id: params.activationAuditId,
      previous_active_publication_id: params.previousActivePublicationId,
      new_active_publication_id: params.publicationBundleId,
    },
    failure_code: null,
    failure_detail: null,
    last_heartbeat_at: committedAtUtc,
    created_at: committedAtUtc,
    updated_at: committedAtUtc,
  };
}

export function createDeferredFollowupJobRow(params: {
  ticket: Step1QuoteCacheFollowupTicketArtifact;
  ticketPath: string;
  failureCode: string | null;
  failureDetail: string | null;
}): Step1DeferredFollowupJobRow {
  const createdAtUtc = toIsoUtc(params.ticket.created_at_utc, "followup_ticket.created_at_utc");
  return {
    followup_job_id: params.ticket.followup_job_id,
    run_id: params.ticket.triggering_run_id,
    publication_bundle_id: params.ticket.publication_bundle_id,
    target_environment: params.ticket.target_environment,
    phase_name: params.ticket.phase_name,
    classification: params.ticket.classification,
    status: params.ticket.status,
    publication_manifest_path: params.ticket.publication_manifest_path,
    ticket_path: params.ticketPath,
    operator_visible_status: params.ticket.operator_visible_status,
    failure_code: params.failureCode,
    failure_detail: params.failureDetail,
    created_at: createdAtUtc,
    updated_at: createdAtUtc,
  };
}

export function createQuoteCacheRefreshPhaseRow(params: {
  ticket: Step1QuoteCacheFollowupTicketArtifact;
  ticketPath: string;
  failureCode: string | null;
  failureDetail: string | null;
}): Step1RuntimeRefreshPhaseRow {
  const createdAtUtc = toIsoUtc(params.ticket.created_at_utc, "followup_ticket.created_at_utc");
  return {
    run_id: params.ticket.triggering_run_id,
    phase_name: STEP1_QUOTE_CACHE_REFRESH_PHASE,
    input_contract: {
      publication_bundle_id: params.ticket.publication_bundle_id,
      publication_manifest_path: params.ticket.publication_manifest_path,
      classification: params.ticket.classification,
      target_environment: params.ticket.target_environment,
    },
    process_status: params.ticket.status,
    started_at: createdAtUtc,
    completed_at: params.ticket.status === "failed" ? createdAtUtc : null,
    output_contract: {
      followup_job_id: params.ticket.followup_job_id,
      ticket_path: params.ticketPath,
      operator_visible_status: params.ticket.operator_visible_status,
    },
    failure_code: params.failureCode,
    failure_detail: params.failureDetail,
    last_heartbeat_at: createdAtUtc,
    created_at: createdAtUtc,
    updated_at: createdAtUtc,
  };
}

export function parseStoredStep1RunRequestRecord(value: unknown): Step1RunRequestRecord | null {
  const record = asObject(value);
  if (!record) return null;

  const runId = String(record.run_id ?? "").trim();
  const normalizedPackageId = String(record.normalized_package_id ?? "").trim();
  const policySetId = String(record.policy_set_id ?? "").trim();
  const modelSetId = String(record.model_set_id ?? "").trim();
  const configSetId = String(record.config_set_id ?? "").trim();
  const bundleClass = String(record.bundle_class ?? "").trim();
  const targetEnvironment = String(record.target_environment ?? "").trim();
  const requestedBy = String(record.requested_by ?? "").trim();
  const requestedAtUtcRaw = String(record.requested_at_utc ?? "").trim();
  const dependencyClassificationRegister = asObject(record.dependency_classification_register);
  const sourcePackageIdentities = parseStoredStep1SourcePackageIdentities(record.source_package_identities);

  if (
    !runId
    || !normalizedPackageId
    || !policySetId
    || !modelSetId
    || !configSetId
    || !bundleClass
    || !targetEnvironment
    || !requestedBy
    || !requestedAtUtcRaw
    || !dependencyClassificationRegister
    || sourcePackageIdentities === null
  ) {
    return null;
  }

  return {
    run_id: runId,
    normalized_package_id: normalizedPackageId,
    policy_set_id: policySetId,
    model_set_id: modelSetId,
    config_set_id: configSetId,
    bundle_class: bundleClass,
    dependency_classification_register: dependencyClassificationRegister,
    ...(typeof sourcePackageIdentities === "undefined"
      ? {}
      : { source_package_identities: sourcePackageIdentities }),
    target_environment: targetEnvironment,
    requested_by: requestedBy,
    requested_at_utc: toIsoUtc(requestedAtUtcRaw, "requested_at_utc"),
  };
}

export function parseStoredStep1CandidateBundleManifest(value: unknown): Step1CandidateBundleManifest | null {
  const record = asObject(value);
  if (!record) return null;

  const candidateBundleId = String(record.candidate_bundle_id ?? "").trim();
  const normalizedPackageId = String(record.normalized_package_id ?? "").trim();
  const policySetId = String(record.policy_set_id ?? "").trim();
  const modelSetId = String(record.model_set_id ?? "").trim();
  const configSetId = String(record.config_set_id ?? "").trim();
  const bundleClass = String(record.bundle_class ?? "").trim();
  const normalizedPackageManifestId = String(record.normalized_package_manifest_id ?? "").trim();
  const normalizedPackageManifestPath = String(record.normalized_package_manifest_path ?? "").trim();
  const normalizedPackageManifestDigestSha256 = String(record.normalized_package_manifest_digest_sha256 ?? "").trim();
  const requestedRunMode = String(record.requested_run_mode ?? "").trim();
  const deterministicBuildTimestampRaw = String(record.deterministic_build_timestamp_utc ?? "").trim();
  const targetEnvironment = String(record.target_environment ?? "").trim();
  const dependencyClassificationRegister = asObject(record.dependency_classification_register);
  const sourcePackageIdentities = parseStoredStep1SourcePackageIdentities(record.source_package_identities);

  if (
    !candidateBundleId
    || !normalizedPackageId
    || !policySetId
    || !modelSetId
    || !configSetId
    || !bundleClass
    || !normalizedPackageManifestId
    || !normalizedPackageManifestPath
    || !normalizedPackageManifestDigestSha256
    || !requestedRunMode
    || !deterministicBuildTimestampRaw
    || !targetEnvironment
    || !dependencyClassificationRegister
    || !sourcePackageIdentities
  ) {
    return null;
  }

  const assessmentArtifactReferences = Array.isArray(record.assessment_artifact_references)
    ? record.assessment_artifact_references
        .map((entry) => {
          const item = asObject(entry);
          if (!item) return null;
          const artifactKind = String(item.artifact_kind ?? "").trim();
          const artifactId = String(item.artifact_id ?? "").trim();
          const artifactPath = String(item.artifact_path ?? "").trim() || null;
          const digest = String(item.artifact_digest_sha256 ?? "").trim() || null;
          if (!artifactKind || !artifactId) return null;
          return {
            artifact_kind: artifactKind,
            artifact_id: artifactId,
            artifact_path: artifactPath,
            artifact_digest_sha256: digest,
          } satisfies Step1AssessmentArtifactReference;
        })
        .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
    : [];

  if (assessmentArtifactReferences.length === 0) {
    return null;
  }

  return {
    candidate_bundle_id: candidateBundleId,
    normalized_package_id: normalizedPackageId,
    policy_set_id: policySetId,
    model_set_id: modelSetId,
    config_set_id: configSetId,
    bundle_class: bundleClass,
    normalized_package_manifest_id: normalizedPackageManifestId,
    normalized_package_manifest_path: normalizedPackageManifestPath,
    normalized_package_manifest_digest_sha256: normalizedPackageManifestDigestSha256,
    source_package_identities: sourcePackageIdentities,
    requested_run_mode: requestedRunMode,
    deterministic_build_timestamp_utc: toIsoUtc(
      deterministicBuildTimestampRaw,
      "candidate_bundle.deterministic_build_timestamp_utc",
    ),
    target_environment: targetEnvironment,
    dependency_classification_register: dependencyClassificationRegister,
    assessment_artifact_references: assessmentArtifactReferences,
  };
}

export function parseStoredStep1AssessmentReportArtifact(value: unknown): Step1AssessmentReportArtifact | null {
  const record = asObject(value);
  if (!record) return null;

  const assessmentReportId = String(record.assessment_report_id ?? "").trim();
  const candidateBundleId = String(record.candidate_bundle_id ?? "").trim();
  const assessmentRuleSetId = String(record.assessment_rule_set_id ?? "").trim();
  const dispositionRaw = String(record.disposition ?? "").trim().toLowerCase();
  const createdAtUtcRaw = String(record.created_at_utc ?? "").trim();

  if (
    !assessmentReportId
    || !candidateBundleId
    || !assessmentRuleSetId
    || !createdAtUtcRaw
    || (dispositionRaw !== "pass" && dispositionRaw !== "fail")
  ) {
    return null;
  }

  const blockingReasonDetails = Array.isArray(record.blocking_reason_details)
    ? record.blocking_reason_details
        .map((entry) => {
          const item = asObject(entry);
          if (!item) return null;
          const reasonCode = String(item.reason_code ?? "").trim();
          const reasonDetail = String(item.reason_detail ?? "").trim();
          const dependencyId = String(item.dependency_id ?? "").trim() || null;
          const dependencyClassificationRaw = String(item.dependency_classification ?? "").trim().toLowerCase();
          const dependencyClassification =
            dependencyClassificationRaw === "publication_critical"
            || dependencyClassificationRaw === "non_critical"
            || dependencyClassificationRaw === "not_applicable"
              ? dependencyClassificationRaw
              : null;
          if (!reasonCode || !reasonDetail) return null;
          return {
            reason_code: reasonCode,
            reason_detail: reasonDetail,
            dependency_id: dependencyId,
            dependency_classification: dependencyClassification,
          } satisfies Step1AssessmentBlockingReason;
        })
        .filter((entry): entry is Step1AssessmentBlockingReason => entry !== null)
    : [];

  const evidenceReferences = Array.isArray(record.evidence_references)
    ? record.evidence_references
        .map((entry) => {
          const item = asObject(entry);
          if (!item) return null;
          const evidenceKind = String(item.evidence_kind ?? "").trim();
          const evidenceId = String(item.evidence_id ?? "").trim();
          const evidencePath = String(item.evidence_path ?? "").trim() || null;
          const evidenceDigest = String(item.evidence_digest_sha256 ?? "").trim() || null;
          if (!evidenceKind || !evidenceId) return null;
          return {
            evidence_kind: evidenceKind,
            evidence_id: evidenceId,
            evidence_path: evidencePath,
            evidence_digest_sha256: evidenceDigest,
          } satisfies Step1AssessmentEvidenceReference;
        })
        .filter((entry): entry is Step1AssessmentEvidenceReference => entry !== null)
    : [];

  return {
    assessment_report_id: assessmentReportId,
    candidate_bundle_id: candidateBundleId,
    assessment_rule_set_id: assessmentRuleSetId,
    disposition: dispositionRaw,
    blocking_reason_codes: asStringArray(record.blocking_reason_codes),
    blocking_reason_details: blockingReasonDetails,
    evidence_references: evidenceReferences,
    publication_allowed: record.publication_allowed === true,
    created_at_utc: toIsoUtc(createdAtUtcRaw, "assessment_report.created_at_utc"),
  };
}

export function parseStoredStep1PublicationBundleManifest(value: unknown): Step1PublicationBundleManifest | null {
  const record = asObject(value);
  if (!record) return null;

  const publicationBundleId = String(record.publication_bundle_id ?? "").trim();
  const runId = String(record.run_id ?? "").trim();
  const candidateBundleId = String(record.candidate_bundle_id ?? "").trim();
  const assessmentReportId = String(record.assessment_report_id ?? "").trim();
  const normalizedPackageId = String(record.normalized_package_id ?? "").trim();
  const policySetId = String(record.policy_set_id ?? "").trim();
  const modelSetId = String(record.model_set_id ?? "").trim();
  const configSetId = String(record.config_set_id ?? "").trim();
  const bundleClass = String(record.bundle_class ?? "").trim();
  const targetEnvironment = String(record.target_environment ?? "").trim();
  const activationAuditId = String(record.activation_audit_id ?? "").trim();
  const candidateBundleManifestPath = String(record.candidate_bundle_manifest_path ?? "").trim();
  const assessmentReportPath = String(record.assessment_report_path ?? "").trim();
  const committedAtUtcRaw = String(record.committed_at_utc ?? "").trim();

  if (
    !publicationBundleId
    || !runId
    || !candidateBundleId
    || !assessmentReportId
    || !normalizedPackageId
    || !policySetId
    || !modelSetId
    || !configSetId
    || !bundleClass
    || !targetEnvironment
    || !activationAuditId
    || !candidateBundleManifestPath
    || !assessmentReportPath
    || !committedAtUtcRaw
  ) {
    return null;
  }

  const previousActivePublicationId = String(record.previous_active_publication_id ?? "").trim() || null;

  return {
    publication_bundle_id: publicationBundleId,
    run_id: runId,
    candidate_bundle_id: candidateBundleId,
    assessment_report_id: assessmentReportId,
    normalized_package_id: normalizedPackageId,
    policy_set_id: policySetId,
    model_set_id: modelSetId,
    config_set_id: configSetId,
    bundle_class: bundleClass,
    target_environment: targetEnvironment,
    previous_active_publication_id: previousActivePublicationId,
    activation_audit_id: activationAuditId,
    candidate_bundle_manifest_path: candidateBundleManifestPath,
    assessment_report_path: assessmentReportPath,
    committed_at_utc: toIsoUtc(committedAtUtcRaw, "publication_bundle.committed_at_utc"),
  };
}

export function parseStoredStep1ActivePublicationPointerRow(value: unknown): Step1ActivePublicationPointerRow | null {
  const record = asObject(value);
  if (!record) return null;

  const targetEnvironment = String(record.target_environment ?? "").trim();
  const publicationBundleId = String(record.publication_bundle_id ?? "").trim();
  const runId = String(record.run_id ?? "").trim();
  const createdAtRaw = String(record.created_at ?? "").trim();
  const updatedAtRaw = String(record.updated_at ?? "").trim();

  if (!targetEnvironment || !publicationBundleId || !runId || !createdAtRaw || !updatedAtRaw) {
    return null;
  }

  return {
    target_environment: targetEnvironment,
    publication_bundle_id: publicationBundleId,
    run_id: runId,
    created_at: toIsoUtc(createdAtRaw, "active_publication_pointer.created_at"),
    updated_at: toIsoUtc(updatedAtRaw, "active_publication_pointer.updated_at"),
  };
}

export function parseStoredStep1PublicationActivationAuditRow(
  value: unknown,
): Step1PublicationActivationAuditRow | null {
  const record = asObject(value);
  if (!record) return null;

  const activationAuditId = String(record.activation_audit_id ?? "").trim();
  const targetEnvironment = String(record.target_environment ?? "").trim();
  const runId = String(record.run_id ?? "").trim();
  const publicationBundleId = String(record.publication_bundle_id ?? "").trim();
  const newActivePublicationId = String(record.new_active_publication_id ?? "").trim();
  const assessmentReportId = String(record.assessment_report_id ?? "").trim();
  const createdAtRaw = String(record.created_at ?? "").trim();

  if (
    !activationAuditId
    || !targetEnvironment
    || !runId
    || !publicationBundleId
    || !newActivePublicationId
    || !assessmentReportId
    || !createdAtRaw
  ) {
    return null;
  }

  return {
    activation_audit_id: activationAuditId,
    target_environment: targetEnvironment,
    run_id: runId,
    publication_bundle_id: publicationBundleId,
    previous_active_publication_id: String(record.previous_active_publication_id ?? "").trim() || null,
    new_active_publication_id: newActivePublicationId,
    assessment_report_id: assessmentReportId,
    created_at: toIsoUtc(createdAtRaw, "publication_activation_audit.created_at"),
  };
}

export function selectStep1ActivePublicationPointerRow(
  store: Step1ProofStore,
  targetEnvironment: string,
): Step1ActivePublicationPointerRow | null {
  const normalizedTargetEnvironment = String(targetEnvironment ?? "").trim();
  if (!normalizedTargetEnvironment) return null;
  const matches = (Array.isArray(store.active_publication_pointer) ? store.active_publication_pointer : [])
    .map((entry) => parseStoredStep1ActivePublicationPointerRow(entry))
    .filter((entry): entry is Step1ActivePublicationPointerRow => entry !== null)
    .filter((entry) => entry.target_environment === normalizedTargetEnvironment);
  if (matches.length === 0) return null;
  matches.sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  return matches[0] ?? null;
}

export function selectStep1PublicationBundleRow(
  store: Step1ProofStore,
  publicationBundleId: string,
): Step1PublicationBundleRow | null {
  const normalizedPublicationBundleId = String(publicationBundleId ?? "").trim();
  if (!normalizedPublicationBundleId) return null;
  const match = (Array.isArray(store.publication_bundles) ? store.publication_bundles : [])
    .find((entry) => String(entry.publication_bundle_id ?? "").trim() === normalizedPublicationBundleId);
  return match ?? null;
}

export function selectStep1AssessmentReportRow(
  store: Step1ProofStore,
  assessmentReportId: string,
): Step1AssessmentReportRow | null {
  const normalizedAssessmentReportId = String(assessmentReportId ?? "").trim();
  if (!normalizedAssessmentReportId) return null;
  const match = (Array.isArray(store.assessment_reports) ? store.assessment_reports : [])
    .find((entry) => String(entry.assessment_report_id ?? "").trim() === normalizedAssessmentReportId);
  return match ?? null;
}

export function selectStep1RuntimeRefreshRunRow(
  store: Step1ProofStore,
  runId: string,
): Step1RuntimeRefreshRunRow | null {
  const normalizedRunId = String(runId ?? "").trim();
  if (!normalizedRunId) return null;
  const match = (Array.isArray(store.runtime_refresh_runs) ? store.runtime_refresh_runs : [])
    .find((entry) => String(entry.run_id ?? "").trim() === normalizedRunId);
  return match ?? null;
}
