import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "../workspace-root";
import { buildCanonicalPublicationBundleWriteContract } from "../publication-bundle-contract";
import {
  createActivePublicationPointerRow,
  createPublicationActivationAuditRow,
  createPublicationBundleRow,
  createPublicationCommitPhaseRow,
  nowExecutionTimestampUtc,
  parseStoredStep1AssessmentReportArtifact,
  parseStoredStep1CandidateBundleManifest,
  type Step1AssessmentEvidenceReference,
  type Step1PublicationBundleManifest,
  type Step1PublicationCommitPersistence,
} from "./schema";

export type PublicationCommitRecordInput = {
  runId: string;
  assessmentReportPath: string;
  targetEnvironment: string;
};

export type PublicationCommitRecordResult = {
  manifest: Step1PublicationBundleManifest;
  manifestPath: string;
  manifestDigestSha256: string;
  publicationBundleRow: ReturnType<typeof createPublicationBundleRow>;
  activePublicationPointerRow: ReturnType<typeof createActivePublicationPointerRow>;
  publicationActivationAuditRow: ReturnType<typeof createPublicationActivationAuditRow>;
  phaseRow: ReturnType<typeof createPublicationCommitPhaseRow>;
};

export class PublicationCommitRecordError extends Error {
  code:
    | "assessment_not_pass"
    | "publication_bundle_write_failure"
    | "activation_pointer_write_failure"
    | "activation_audit_write_failure"
    | "state_persistence_failure";
  detail: string;
  runId: string;

  constructor(params: {
    code:
      | "assessment_not_pass"
      | "publication_bundle_write_failure"
      | "activation_pointer_write_failure"
      | "activation_audit_write_failure"
      | "state_persistence_failure";
    detail: string;
    runId: string;
  }) {
    super(
      `Publication commit failed. run_id=${params.runId}; code=${params.code}; `
      + `detail=${params.detail}; prior active publication remains authoritative.`,
    );
    this.name = "PublicationCommitRecordError";
    this.code = params.code;
    this.detail = params.detail;
    this.runId = params.runId;
  }
}

type CreatePublicationCommitOptions = {
  persistence: Step1PublicationCommitPersistence;
  workspaceRoot?: string;
};

function requireText(value: unknown, fieldName: string, runId: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new PublicationCommitRecordError({
      code: "state_persistence_failure",
      detail: `${fieldName} must be a non-empty string.`,
      runId,
    });
  }
  return text;
}

async function loadAssessmentReport(
  assessmentReportPath: string,
  runId: string,
): Promise<NonNullable<ReturnType<typeof parseStoredStep1AssessmentReportArtifact>>> {
  try {
    const raw = await readFile(assessmentReportPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    const report = parseStoredStep1AssessmentReportArtifact(parsed);
    if (!report) {
      throw new Error("assessment report is invalid.");
    }
    return report;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to read assessment report.";
    throw new PublicationCommitRecordError({
      code: "state_persistence_failure",
      detail: `assessment_report_path read failed: ${detail}`,
      runId,
    });
  }
}

function findEvidencePath(
  evidenceReferences: Step1AssessmentEvidenceReference[],
  evidenceKind: string,
): string | null {
  const match = evidenceReferences.find((entry) => entry.evidence_kind === evidenceKind);
  return String(match?.evidence_path ?? "").trim() || null;
}

async function loadCandidateBundleManifest(
  candidateBundleManifestPath: string,
  runId: string,
): Promise<NonNullable<ReturnType<typeof parseStoredStep1CandidateBundleManifest>>> {
  try {
    const raw = await readFile(candidateBundleManifestPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    const manifest = parseStoredStep1CandidateBundleManifest(parsed);
    if (!manifest) {
      throw new Error("candidate bundle manifest is invalid.");
    }
    return manifest;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to read candidate bundle manifest.";
    throw new PublicationCommitRecordError({
      code: "state_persistence_failure",
      detail: `candidate_bundle_manifest_path read failed: ${detail}`,
      runId,
    });
  }
}

function classifyPersistenceFailure(
  error: unknown,
  runId: string,
): PublicationCommitRecordError {
  const detail = error instanceof Error ? error.message : "Unknown publication commit persistence failure.";
  const [rawCode, ...rest] = detail.split(":");
  const normalizedCode = rawCode.trim();
  const normalizedDetail = rest.join(":").trim() || detail;
  if (
    normalizedCode === "publication_bundle_write_failure"
    || normalizedCode === "activation_pointer_write_failure"
    || normalizedCode === "activation_audit_write_failure"
    || normalizedCode === "state_persistence_failure"
  ) {
    return new PublicationCommitRecordError({
      code: normalizedCode,
      detail: normalizedDetail,
      runId,
    });
  }
  return new PublicationCommitRecordError({
    code: "state_persistence_failure",
    detail,
    runId,
  });
}

export async function createPublicationCommitRecord(
  input: PublicationCommitRecordInput,
  options: CreatePublicationCommitOptions,
): Promise<PublicationCommitRecordResult> {
  const runId = requireText(input.runId, "run_id", input.runId || "pending");
  const assessmentReportPath = requireText(input.assessmentReportPath, "assessment_report_path", runId);
  const targetEnvironment = requireText(input.targetEnvironment, "target_environment", runId);
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = options.persistence;

  const report = await loadAssessmentReport(assessmentReportPath, runId);
  if (report.disposition !== "pass" || report.publication_allowed !== true) {
    throw new PublicationCommitRecordError({
      code: "assessment_not_pass",
      detail: `assessment_report_id=${report.assessment_report_id}; disposition=${report.disposition}; publication_allowed=${report.publication_allowed}`,
      runId,
    });
  }

  const candidateBundleManifestPath = findEvidencePath(report.evidence_references, "candidate_bundle_manifest");
  if (!candidateBundleManifestPath) {
    throw new PublicationCommitRecordError({
      code: "state_persistence_failure",
      detail: "assessment report is missing candidate_bundle_manifest evidence.",
      runId,
    });
  }

  const candidateManifest = await loadCandidateBundleManifest(candidateBundleManifestPath, runId);
  const previousActivePointer = await persistence.readActivePublicationPointer(targetEnvironment);
  const committedAtUtc = nowExecutionTimestampUtc();
  const publicationContract = buildCanonicalPublicationBundleWriteContract({
    workspaceRoot,
    runId,
    assessmentReport: report,
    assessmentReportPath,
    candidateBundleManifestPath,
    candidateManifest,
    targetEnvironment,
    previousActivePublicationId: previousActivePointer?.publication_bundle_id ?? null,
    committedAtUtc,
  });
  const manifest = publicationContract.manifest;
  const manifestPath = publicationContract.manifestPath;
  const manifestDigestSha256 = publicationContract.manifestDigestSha256;
  const publicationBundleRow = createPublicationBundleRow({
    manifest,
    manifestPath,
    manifestDigestSha256,
  });
  const activePublicationPointerRow = createActivePublicationPointerRow({
    targetEnvironment,
    publicationBundleId: manifest.publication_bundle_id,
    runId,
    committedAtUtc,
  });
  const publicationActivationAuditRow = createPublicationActivationAuditRow({
    activationAuditId: manifest.activation_audit_id,
    targetEnvironment,
    runId,
    publicationBundleId: manifest.publication_bundle_id,
    previousActivePublicationId: manifest.previous_active_publication_id,
    newActivePublicationId: manifest.publication_bundle_id,
    assessmentReportId: manifest.assessment_report_id,
    committedAtUtc,
  });
  const phaseRow = createPublicationCommitPhaseRow({
    runId,
    targetEnvironment,
    candidateBundleId: manifest.candidate_bundle_id,
    assessmentReportId: manifest.assessment_report_id,
    assessmentReportPath,
    publicationBundleId: manifest.publication_bundle_id,
    publicationManifestPath: manifestPath,
    activationAuditId: manifest.activation_audit_id,
    previousActivePublicationId: manifest.previous_active_publication_id,
    committedAtUtc,
  });

  try {
    await mkdir(path.dirname(manifestPath), { recursive: true });
    await writeFile(manifestPath, publicationContract.manifestText, "utf8");
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to write publication manifest.";
    throw new PublicationCommitRecordError({
      code: "publication_bundle_write_failure",
      detail,
      runId,
    });
  }

  try {
    await persistence.ensureReady();
    await persistence.commitPublicationTransaction({
      publicationBundleRow,
      activePublicationPointerRow,
      publicationActivationAuditRow,
      phaseRow,
    });
  } catch (error) {
    throw classifyPersistenceFailure(error, runId);
  }

  return {
    manifest,
    manifestPath,
    manifestDigestSha256,
    publicationBundleRow,
    activePublicationPointerRow,
    publicationActivationAuditRow,
    phaseRow,
  };
}
