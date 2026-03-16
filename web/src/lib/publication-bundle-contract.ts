import { readFile } from "node:fs/promises";
import type { Pool } from "pg";

import {
  isPostgresConfigured,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  RUNTIME_REFRESH_RUNS_TABLE,
  runtimeSourceIsPostgres,
  tableExists,
  toIsoOrNull,
  toLowerTextOrNull,
  toTextOrNull,
  type AttemptFailure,
} from "@/lib/runtime-db";
import {
  parseStoredStep1PublicationBundleManifest,
  readStep1ProofStore,
  resolveStep1PublicationManifestPath,
  selectStep1ActivePublicationPointerRow,
  selectStep1PublicationBundleRow,
  selectStep1RuntimeRefreshRunRow,
  sha256Text,
  stableJsonStringify,
  type Step1AssessmentReportArtifact,
  type Step1AssessmentReportRow,
  type Step1CandidateBundleManifest,
  type Step1PublicationBundleManifest,
  type Step1ProofStore,
} from "./step1/schema";

const STEP1_ACTIVE_PUBLICATION_POINTER_TABLE = "active_publication_pointer";
const STEP1_ASSESSMENT_REPORTS_TABLE = "assessment_reports";
const STEP1_PUBLICATION_BUNDLES_TABLE = "publication_bundles";

type PublicationBundleMirrorRunMeta = {
  runId: string | null;
  completedAtUtc: string | null;
  reportGeneratedAtUtc: string | null;
  mode: string | null;
  triggerSource: string | null;
  reportStatus: string | null;
};

export type PublicationBundleContractBlockingReasonCode =
  | "RUNTIME_SOURCE_NOT_POSTGRES"
  | "POSTGRES_NOT_CONFIGURED"
  | "ACTIVE_POINTER_MISSING"
  | "ACTIVE_POINTER_INVALID";

export type PublicationBundleContractResolution = {
  runId: string | null;
  publicationBundleId: string | null;
  assessmentReportId: string | null;
  targetEnvironment: string | null;
  generatedAtUtc: string | null;
  completedAtUtc: string | null;
  reportGeneratedAtUtc: string | null;
  bundleGeneratedAtUtc: string | null;
  mode: string | null;
  triggerSource: string | null;
  reportStatus: string | null;
  manifestPath: string | null;
  manifestDigestSha256: string | null;
  candidateValid: boolean;
  blockingReasonCode: PublicationBundleContractBlockingReasonCode | null;
  blockingReasonDetail: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export type ReadCanonicalPublicationBundleManifestArtifactResult = {
  manifest: Step1PublicationBundleManifest;
  manifestText: string;
  manifestDigestSha256: string;
};

export type PublicationBundleManifestRowMatchResult = {
  matches: boolean;
  mismatches: string[];
};

function toNonEmptyText(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

function normalizeNullishText(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

function manifestIdentityDigest(params: {
  runId: string;
  candidateBundleId: string;
  assessmentReportId: string;
  targetEnvironment: string;
}): string {
  return sha256Text(stableJsonStringify({
    run_id: params.runId,
    candidate_bundle_id: params.candidateBundleId,
    assessment_report_id: params.assessmentReportId,
    target_environment: params.targetEnvironment,
  }));
}

function activationAuditDigest(params: {
  runId: string;
  candidateBundleId: string;
  assessmentReportId: string;
  targetEnvironment: string;
  previousActivePublicationId: string | null;
}): string {
  return sha256Text(stableJsonStringify({
    run_id: params.runId,
    candidate_bundle_id: params.candidateBundleId,
    assessment_report_id: params.assessmentReportId,
    target_environment: params.targetEnvironment,
    previous_active_publication_id: params.previousActivePublicationId,
  }));
}

export function buildCanonicalPublicationBundleManifest(params: {
  runId: string;
  assessmentReport: Step1AssessmentReportArtifact;
  assessmentReportPath: string;
  candidateBundleManifestPath: string;
  candidateManifest: Step1CandidateBundleManifest;
  targetEnvironment: string;
  previousActivePublicationId: string | null;
  committedAtUtc: string;
}): Step1PublicationBundleManifest {
  const publicationBundleDigestSha256 = manifestIdentityDigest({
    runId: params.runId,
    candidateBundleId: params.candidateManifest.candidate_bundle_id,
    assessmentReportId: params.assessmentReport.assessment_report_id,
    targetEnvironment: params.targetEnvironment,
  });
  const activationAuditDigestSha256 = activationAuditDigest({
    runId: params.runId,
    candidateBundleId: params.candidateManifest.candidate_bundle_id,
    assessmentReportId: params.assessmentReport.assessment_report_id,
    targetEnvironment: params.targetEnvironment,
    previousActivePublicationId: params.previousActivePublicationId,
  });

  return {
    publication_bundle_id: `publication_bundle_v1_${publicationBundleDigestSha256.slice(0, 24)}`,
    run_id: params.runId,
    candidate_bundle_id: params.candidateManifest.candidate_bundle_id,
    assessment_report_id: params.assessmentReport.assessment_report_id,
    normalized_package_id: params.candidateManifest.normalized_package_id,
    policy_set_id: params.candidateManifest.policy_set_id,
    model_set_id: params.candidateManifest.model_set_id,
    config_set_id: params.candidateManifest.config_set_id,
    bundle_class: params.candidateManifest.bundle_class,
    target_environment: params.targetEnvironment,
    previous_active_publication_id: params.previousActivePublicationId,
    activation_audit_id: `publication_activation_v1_${activationAuditDigestSha256.slice(0, 24)}`,
    candidate_bundle_manifest_path: params.candidateBundleManifestPath,
    assessment_report_path: params.assessmentReportPath,
    committed_at_utc: params.committedAtUtc,
  };
}

export function serializeCanonicalPublicationBundleManifest(
  manifest: Step1PublicationBundleManifest,
): string {
  return `${JSON.stringify(manifest, null, 2)}\n`;
}

export function digestCanonicalPublicationBundleManifestText(
  manifestText: string,
): string {
  return sha256Text(manifestText);
}

export function buildCanonicalPublicationBundleWriteContract(params: {
  workspaceRoot: string;
  runId: string;
  assessmentReport: Step1AssessmentReportArtifact;
  assessmentReportPath: string;
  candidateBundleManifestPath: string;
  candidateManifest: Step1CandidateBundleManifest;
  targetEnvironment: string;
  previousActivePublicationId: string | null;
  committedAtUtc: string;
}): {
  manifest: Step1PublicationBundleManifest;
  manifestPath: string;
  manifestText: string;
  manifestDigestSha256: string;
} {
  const manifest = buildCanonicalPublicationBundleManifest({
    runId: params.runId,
    assessmentReport: params.assessmentReport,
    assessmentReportPath: params.assessmentReportPath,
    candidateBundleManifestPath: params.candidateBundleManifestPath,
    candidateManifest: params.candidateManifest,
    targetEnvironment: params.targetEnvironment,
    previousActivePublicationId: params.previousActivePublicationId,
    committedAtUtc: params.committedAtUtc,
  });
  const manifestPath = resolveStep1PublicationManifestPath(params.workspaceRoot, manifest.publication_bundle_id);
  const manifestText = serializeCanonicalPublicationBundleManifest(manifest);
  return {
    manifest,
    manifestPath,
    manifestText,
    manifestDigestSha256: digestCanonicalPublicationBundleManifestText(manifestText),
  };
}

export async function readCanonicalPublicationBundleManifestArtifact(
  manifestPath: string,
): Promise<ReadCanonicalPublicationBundleManifestArtifactResult> {
  const manifestText = await readFile(manifestPath, "utf8");
  const manifest = parseStoredStep1PublicationBundleManifest(JSON.parse(manifestText) as unknown);
  if (!manifest) {
    throw new Error(`publication manifest is invalid at ${manifestPath}.`);
  }
  return {
    manifest,
    manifestText,
    manifestDigestSha256: digestCanonicalPublicationBundleManifestText(manifestText),
  };
}

function manifestContractValueMap(manifest: Step1PublicationBundleManifest): Record<string, string | null> {
  return {
    publication_bundle_id: manifest.publication_bundle_id,
    run_id: manifest.run_id,
    candidate_bundle_id: manifest.candidate_bundle_id,
    assessment_report_id: manifest.assessment_report_id,
    normalized_package_id: manifest.normalized_package_id,
    policy_set_id: manifest.policy_set_id,
    model_set_id: manifest.model_set_id,
    config_set_id: manifest.config_set_id,
    bundle_class: manifest.bundle_class,
    target_environment: manifest.target_environment,
    previous_active_publication_id: manifest.previous_active_publication_id,
    activation_audit_id: manifest.activation_audit_id,
    candidate_bundle_manifest_path: manifest.candidate_bundle_manifest_path,
    assessment_report_path: manifest.assessment_report_path,
  };
}

function rowContractValueMap(params: {
  row: {
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
  };
}): Record<string, string | null> {
  return {
    publication_bundle_id: params.row.publication_bundle_id,
    run_id: params.row.run_id,
    candidate_bundle_id: params.row.candidate_bundle_id,
    assessment_report_id: params.row.assessment_report_id,
    normalized_package_id: params.row.normalized_package_id,
    policy_set_id: params.row.policy_set_id,
    model_set_id: params.row.model_set_id,
    config_set_id: params.row.config_set_id,
    bundle_class: params.row.bundle_class,
    target_environment: params.row.target_environment,
    previous_active_publication_id: params.row.previous_active_publication_id,
    activation_audit_id: params.row.activation_audit_id,
    candidate_bundle_manifest_path: params.row.candidate_bundle_manifest_path,
    assessment_report_path: params.row.assessment_report_path,
    manifest_path: params.row.manifest_path,
    manifest_digest_sha256: params.row.manifest_digest_sha256,
  };
}

export function publicationBundleRowMatchesManifestContract(params: {
  row: {
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
  };
  manifest: Step1PublicationBundleManifest;
  manifestPath: string;
  manifestDigestSha256: string;
}): PublicationBundleManifestRowMatchResult {
  const rowMap = rowContractValueMap({ row: params.row });
  const manifestMap: Record<string, string | null> = {
    ...manifestContractValueMap(params.manifest),
    manifest_path: params.manifestPath,
    manifest_digest_sha256: params.manifestDigestSha256,
  };
  const keys = Array.from(new Set([...Object.keys(rowMap), ...Object.keys(manifestMap)])).sort();
  const mismatches = keys
    .filter((key) => normalizeNullishText(rowMap[key]) !== normalizeNullishText(manifestMap[key]))
    .map((key) => {
      const left = normalizeNullishText(rowMap[key]);
      const right = normalizeNullishText(manifestMap[key]);
      return `${key}: row='${left ?? "null"}' manifest='${right ?? "null"}'`;
    });
  return {
    matches: mismatches.length === 0,
    mismatches,
  };
}

function buildResolution(params: {
  runId: string | null;
  publicationBundleId: string | null;
  assessmentReportId: string | null;
  targetEnvironment: string | null;
  generatedAtUtc: string | null;
  completedAtUtc: string | null;
  reportGeneratedAtUtc: string | null;
  bundleGeneratedAtUtc: string | null;
  mode: string | null;
  triggerSource: string | null;
  reportStatus: string | null;
  manifestPath: string | null;
  manifestDigestSha256: string | null;
  candidateValid: boolean;
  blockingReasonCode: PublicationBundleContractBlockingReasonCode | null;
  blockingReasonDetail: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
}): PublicationBundleContractResolution {
  return {
    runId: params.runId,
    publicationBundleId: params.publicationBundleId,
    assessmentReportId: params.assessmentReportId,
    targetEnvironment: params.targetEnvironment,
    generatedAtUtc: params.generatedAtUtc,
    completedAtUtc: params.completedAtUtc,
    reportGeneratedAtUtc: params.reportGeneratedAtUtc,
    bundleGeneratedAtUtc: params.bundleGeneratedAtUtc,
    mode: params.mode,
    triggerSource: params.triggerSource,
    reportStatus: params.reportStatus,
    manifestPath: params.manifestPath,
    manifestDigestSha256: params.manifestDigestSha256,
    candidateValid: params.candidateValid,
    blockingReasonCode: params.blockingReasonCode,
    blockingReasonDetail: params.blockingReasonDetail,
    sourcePath: params.sourcePath,
    failures: params.failures,
  };
}

function validatePublicationAuthority(params: {
  targetEnvironment: string;
  sourcePath: string;
  failures: AttemptFailure[];
  pointer:
    | {
        publication_bundle_id: string;
        run_id: string;
        target_environment: string;
        updated_at?: string | null;
      }
    | null;
  bundle:
    | {
        publication_bundle_id: string;
        run_id: string;
        assessment_report_id: string;
        target_environment: string;
        manifest_path: string;
        manifest_digest_sha256: string;
        created_at?: string | null;
      }
    | null;
  assessment:
    | {
        assessment_report_id: string;
        run_id: string;
        disposition: string;
        publication_allowed: boolean;
        created_at?: string | null;
      }
    | null;
  mirror: PublicationBundleMirrorRunMeta | null;
}): PublicationBundleContractResolution {
  const { targetEnvironment, sourcePath, failures, pointer, bundle, assessment, mirror } = params;

  if (!pointer) {
    const detail = `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: null,
      publicationBundleId: null,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: null,
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      manifestPath: null,
      manifestDigestSha256: null,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  if (!bundle) {
    const detail = `publication_bundles row missing for publication_bundle_id='${pointer.publication_bundle_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: pointer.run_id,
      publicationBundleId: pointer.publication_bundle_id,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(pointer.updated_at),
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      manifestPath: null,
      manifestDigestSha256: null,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  if (pointer.run_id !== bundle.run_id) {
    const detail = `active_publication_pointer.run_id='${pointer.run_id}' does not match publication_bundles.run_id='${bundle.run_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: bundle.run_id,
      publicationBundleId: bundle.publication_bundle_id,
      assessmentReportId: bundle.assessment_report_id,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(bundle.created_at) ?? toIsoOrNull(pointer.updated_at),
      completedAtUtc: mirror?.completedAtUtc ?? toIsoOrNull(bundle.created_at),
      reportGeneratedAtUtc: mirror?.reportGeneratedAtUtc ?? null,
      bundleGeneratedAtUtc: toIsoOrNull(bundle.created_at),
      mode: mirror?.mode ?? null,
      triggerSource: mirror?.triggerSource ?? null,
      reportStatus: mirror?.reportStatus ?? "error",
      manifestPath: bundle.manifest_path,
      manifestDigestSha256: bundle.manifest_digest_sha256,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  if (pointer.target_environment !== bundle.target_environment || bundle.target_environment !== targetEnvironment) {
    const detail = `active_publication_pointer.target_environment='${pointer.target_environment}' does not match publication_bundles.target_environment='${bundle.target_environment}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: bundle.run_id,
      publicationBundleId: bundle.publication_bundle_id,
      assessmentReportId: bundle.assessment_report_id,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(bundle.created_at) ?? toIsoOrNull(pointer.updated_at),
      completedAtUtc: mirror?.completedAtUtc ?? toIsoOrNull(bundle.created_at),
      reportGeneratedAtUtc: mirror?.reportGeneratedAtUtc ?? null,
      bundleGeneratedAtUtc: toIsoOrNull(bundle.created_at),
      mode: mirror?.mode ?? null,
      triggerSource: mirror?.triggerSource ?? null,
      reportStatus: mirror?.reportStatus ?? "error",
      manifestPath: bundle.manifest_path,
      manifestDigestSha256: bundle.manifest_digest_sha256,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  if (!assessment) {
    const detail = `assessment_reports row missing for assessment_report_id='${bundle.assessment_report_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: bundle.run_id,
      publicationBundleId: bundle.publication_bundle_id,
      assessmentReportId: bundle.assessment_report_id,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(bundle.created_at) ?? toIsoOrNull(pointer.updated_at),
      completedAtUtc: mirror?.completedAtUtc ?? toIsoOrNull(bundle.created_at),
      reportGeneratedAtUtc: mirror?.reportGeneratedAtUtc ?? null,
      bundleGeneratedAtUtc: toIsoOrNull(bundle.created_at),
      mode: mirror?.mode ?? null,
      triggerSource: mirror?.triggerSource ?? null,
      reportStatus: mirror?.reportStatus ?? "error",
      manifestPath: bundle.manifest_path,
      manifestDigestSha256: bundle.manifest_digest_sha256,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  if (assessment.run_id !== bundle.run_id || assessment.assessment_report_id !== bundle.assessment_report_id) {
    const detail = `assessment_reports prerequisite does not match publication_bundle_id='${bundle.publication_bundle_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: bundle.run_id,
      publicationBundleId: bundle.publication_bundle_id,
      assessmentReportId: bundle.assessment_report_id,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(bundle.created_at) ?? toIsoOrNull(assessment.created_at) ?? toIsoOrNull(pointer.updated_at),
      completedAtUtc: mirror?.completedAtUtc ?? toIsoOrNull(bundle.created_at),
      reportGeneratedAtUtc: mirror?.reportGeneratedAtUtc ?? toIsoOrNull(assessment.created_at),
      bundleGeneratedAtUtc: toIsoOrNull(bundle.created_at),
      mode: mirror?.mode ?? null,
      triggerSource: mirror?.triggerSource ?? null,
      reportStatus: mirror?.reportStatus ?? "error",
      manifestPath: bundle.manifest_path,
      manifestDigestSha256: bundle.manifest_digest_sha256,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const candidateValid = toLowerTextOrNull(assessment.disposition) === "pass" && assessment.publication_allowed === true;
  const blockingReasonDetail = candidateValid
    ? null
    : `assessment_report_id='${assessment.assessment_report_id}' disposition='${toLowerTextOrNull(assessment.disposition) ?? "null"}' publication_allowed=${assessment.publication_allowed}.`;

  return buildResolution({
    runId: bundle.run_id,
    publicationBundleId: bundle.publication_bundle_id,
    assessmentReportId: bundle.assessment_report_id,
    targetEnvironment,
    generatedAtUtc: toIsoOrNull(bundle.created_at) ?? toIsoOrNull(assessment.created_at) ?? toIsoOrNull(pointer.updated_at),
    completedAtUtc: mirror?.completedAtUtc ?? toIsoOrNull(bundle.created_at),
    reportGeneratedAtUtc: mirror?.reportGeneratedAtUtc ?? toIsoOrNull(assessment.created_at),
    bundleGeneratedAtUtc: toIsoOrNull(bundle.created_at),
    mode: mirror?.mode ?? null,
    triggerSource: mirror?.triggerSource ?? null,
    reportStatus: mirror?.reportStatus ?? (candidateValid ? "ok" : "error"),
    manifestPath: bundle.manifest_path,
    manifestDigestSha256: bundle.manifest_digest_sha256,
    candidateValid,
    blockingReasonCode: candidateValid ? null : "ACTIVE_POINTER_INVALID",
    blockingReasonDetail,
    sourcePath,
    failures,
  });
}

function mapMirrorRow(record: Record<string, unknown> | null | undefined): PublicationBundleMirrorRunMeta | null {
  if (!record) return null;
  return {
    runId: toTextOrNull(record.run_id),
    completedAtUtc: toIsoOrNull(record.completed_at),
    reportGeneratedAtUtc: toIsoOrNull(record.report_generated_at_utc),
    mode: toTextOrNull(record.mode),
    triggerSource: toTextOrNull(record.trigger_source),
    reportStatus: toLowerTextOrNull(record.report_status),
  };
}

function selectCanonicalAssessmentPrerequisiteFromProofStore(
  store: Step1ProofStore,
  params: {
    runId: string;
    assessmentReportId: string;
  },
): Step1AssessmentReportRow | null {
  const normalizedRunId = toNonEmptyText(params.runId);
  const normalizedAssessmentReportId = toNonEmptyText(params.assessmentReportId);
  if (!normalizedRunId || !normalizedAssessmentReportId) return null;
  const assessmentReports = Array.isArray(store.assessment_reports) ? store.assessment_reports : [];
  const match = assessmentReports.find((entry) => (
    toNonEmptyText(entry.run_id) === normalizedRunId
    && toNonEmptyText(entry.assessment_report_id) === normalizedAssessmentReportId
  ));
  return match ?? null;
}

async function loadMirrorRunMetaFromPostgres(
  pool: Pool,
  runId: string | null,
): Promise<PublicationBundleMirrorRunMeta | null> {
  const normalizedRunId = toNonEmptyText(runId);
  if (!normalizedRunId) return null;
  const runtimeRunsTableExists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
  if (!runtimeRunsTableExists) return null;
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT
        run_id,
        mode,
        trigger_source,
        completed_at,
        report_generated_at_utc,
        report_status
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE run_id = $1
      LIMIT 1
    `,
    [normalizedRunId],
  );
  return mapMirrorRow(result.rows[0]);
}

async function resolveCanonicalPublicationBundleContractFromProofStore(
  targetEnvironment: string,
  proofStorePath: string,
): Promise<PublicationBundleContractResolution> {
  const sourcePath = `${proofStorePath}#active_publication_pointer/${targetEnvironment}`;
  const failures: AttemptFailure[] = [];
  const store = await readStep1ProofStore(proofStorePath);
  const pointer = selectStep1ActivePublicationPointerRow(store, targetEnvironment);
  const bundle = pointer ? selectStep1PublicationBundleRow(store, pointer.publication_bundle_id) : null;
  const assessment = bundle
    ? selectCanonicalAssessmentPrerequisiteFromProofStore(store, {
        runId: bundle.run_id,
        assessmentReportId: bundle.assessment_report_id,
      })
    : null;
  const mirror = bundle ? mapMirrorRow(selectStep1RuntimeRefreshRunRow(store, bundle.run_id) as unknown as Record<string, unknown>) : null;
  return validatePublicationAuthority({
    targetEnvironment,
    sourcePath,
    failures,
    pointer,
    bundle,
    assessment,
    mirror,
  });
}

async function resolveCanonicalPublicationBundleContractFromPostgres(
  pool: Pool,
  targetEnvironment: string,
): Promise<PublicationBundleContractResolution> {
  const sourcePath = postgresSourcePath(STEP1_ACTIVE_PUBLICATION_POINTER_TABLE);
  const failures: AttemptFailure[] = [];
  const [pointerTableExists, bundleTableExists, assessmentTableExists] = await Promise.all([
    tableExists(pool, STEP1_ACTIVE_PUBLICATION_POINTER_TABLE),
    tableExists(pool, STEP1_PUBLICATION_BUNDLES_TABLE),
    tableExists(pool, STEP1_ASSESSMENT_REPORTS_TABLE),
  ]);

  if (!pointerTableExists || !bundleTableExists || !assessmentTableExists) {
    const detail = "Step 1 publication authority tables are not available.";
    failures.push({ path: sourcePath, reason: detail });
    return buildResolution({
      runId: null,
      publicationBundleId: null,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: null,
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      manifestPath: null,
      manifestDigestSha256: null,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const pointerResult = await pool.query<Record<string, unknown>>(
    `
      SELECT
        publication_bundle_id,
        run_id,
        target_environment,
        updated_at
      FROM ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE}
      WHERE target_environment = $1
      LIMIT 1
    `,
    [targetEnvironment],
  );

  const pointerRecord = pointerResult.rows[0] ?? null;
  const pointer = pointerRecord
    ? {
        publication_bundle_id: toTextOrNull(pointerRecord.publication_bundle_id) ?? "",
        run_id: toTextOrNull(pointerRecord.run_id) ?? "",
        target_environment: toTextOrNull(pointerRecord.target_environment) ?? targetEnvironment,
        updated_at: toIsoOrNull(pointerRecord.updated_at),
      }
    : null;
  const bundleResult = pointer
    ? await pool.query<Record<string, unknown>>(
        `
          SELECT
            publication_bundle_id,
            run_id,
            assessment_report_id,
            target_environment,
            manifest_path,
            manifest_digest_sha256,
            created_at
          FROM ${STEP1_PUBLICATION_BUNDLES_TABLE}
          WHERE publication_bundle_id = $1
          LIMIT 1
        `,
        [pointer.publication_bundle_id],
      )
    : { rows: [] as Record<string, unknown>[] };
  const bundleRecord = bundleResult.rows[0] ?? null;
  const bundle = bundleRecord && toNonEmptyText(bundleRecord.publication_bundle_id)
    ? {
        publication_bundle_id: toTextOrNull(bundleRecord.publication_bundle_id) ?? "",
        run_id: toTextOrNull(bundleRecord.run_id) ?? "",
        assessment_report_id: toTextOrNull(bundleRecord.assessment_report_id) ?? "",
        target_environment: toTextOrNull(bundleRecord.target_environment) ?? targetEnvironment,
        manifest_path: toTextOrNull(bundleRecord.manifest_path) ?? "",
        manifest_digest_sha256: toTextOrNull(bundleRecord.manifest_digest_sha256) ?? "",
        created_at: toIsoOrNull(bundleRecord.created_at),
      }
    : null;
  const assessmentResult = bundle
    ? await pool.query<Record<string, unknown>>(
        `
          SELECT
            assessment_report_id,
            run_id,
            disposition,
            publication_allowed,
            created_at
          FROM ${STEP1_ASSESSMENT_REPORTS_TABLE}
          WHERE run_id = $1
            AND assessment_report_id = $2
          LIMIT 1
        `,
        [bundle.run_id, bundle.assessment_report_id],
      )
    : { rows: [] as Record<string, unknown>[] };
  const assessmentRecord = assessmentResult.rows[0] ?? null;
  const assessment = assessmentRecord && toNonEmptyText(assessmentRecord.assessment_report_id)
    ? {
        assessment_report_id: toTextOrNull(assessmentRecord.assessment_report_id) ?? "",
        run_id: toTextOrNull(assessmentRecord.run_id) ?? "",
        disposition: toLowerTextOrNull(assessmentRecord.disposition) ?? "",
        publication_allowed: assessmentRecord.publication_allowed === true,
        created_at: toIsoOrNull(assessmentRecord.created_at),
      }
    : null;
  const mirror = await loadMirrorRunMetaFromPostgres(pool, bundle?.run_id ?? pointer?.run_id ?? null);

  return validatePublicationAuthority({
    targetEnvironment,
    sourcePath,
    failures,
    pointer,
    bundle,
    assessment,
    mirror,
  });
}

export async function resolveCanonicalPublicationBundleContract(params: {
  targetEnvironment: string;
  proofStorePath?: string | null;
}): Promise<PublicationBundleContractResolution> {
  const targetEnvironment = toNonEmptyText(params.targetEnvironment) ?? "production";
  const proofStorePath = toNonEmptyText(params.proofStorePath);
  if (proofStorePath) {
    return resolveCanonicalPublicationBundleContractFromProofStore(targetEnvironment, proofStorePath);
  }

  const sourcePath = postgresSourcePath(STEP1_ACTIVE_PUBLICATION_POINTER_TABLE);
  if (!runtimeSourceIsPostgres()) {
    const detail = `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`;
    return buildResolution({
      runId: null,
      publicationBundleId: null,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: null,
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      manifestPath: null,
      manifestDigestSha256: null,
      candidateValid: false,
      blockingReasonCode: "RUNTIME_SOURCE_NOT_POSTGRES",
      blockingReasonDetail: detail,
      sourcePath,
      failures: [{ path: sourcePath, reason: detail }],
    });
  }

  if (!isPostgresConfigured()) {
    const detail = "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.";
    return buildResolution({
      runId: null,
      publicationBundleId: null,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: null,
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      manifestPath: null,
      manifestDigestSha256: null,
      candidateValid: false,
      blockingReasonCode: "POSTGRES_NOT_CONFIGURED",
      blockingReasonDetail: detail,
      sourcePath,
      failures: [{ path: sourcePath, reason: detail }],
    });
  }

  const pool = resolveRuntimePostgresPool();
  return resolveCanonicalPublicationBundleContractFromPostgres(pool, targetEnvironment);
}
