import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "../workspace-root";
import {
  createAssessmentGatePhaseRow,
  createAssessmentReportRow,
  nowExecutionTimestampUtc,
  parseStoredStep1CandidateBundleManifest,
  resolveStep1AssessmentReportPath,
  sha256Text,
  stableJsonStringify,
  type Step1AssessmentBlockingReason,
  type Step1AssessmentDisposition,
  type Step1AssessmentEvidenceReference,
  type Step1AssessmentReportArtifact,
  type Step1AssessmentReportPersistence,
} from "./schema";

export type AssessmentReportForcedFailure = {
  reasonCode: string;
  reasonDetail: string;
  dependencyId?: string;
  dependencyClassification?: "publication_critical" | "non_critical" | "not_applicable";
};

export type AssessmentReportRecordInput = {
  runId: string;
  candidateBundleManifestPath: string;
  assessmentRuleSetId: string;
  forcedFailures?: AssessmentReportForcedFailure[];
};

export type AssessmentReportRecordResult = {
  report: Step1AssessmentReportArtifact;
  reportPath: string;
  assessmentReportRow: ReturnType<typeof createAssessmentReportRow>;
  phaseRow: ReturnType<typeof createAssessmentGatePhaseRow>;
};

export class AssessmentReportRecordError extends Error {
  code:
    | "assessment_input_missing"
    | "assessment_rule_failure"
    | "critical_dependency_unsatisfied"
    | "assessment_state_persistence_failure";
  detail: string;
  runId: string;

  constructor(params: {
    code:
      | "assessment_input_missing"
      | "assessment_rule_failure"
      | "critical_dependency_unsatisfied"
      | "assessment_state_persistence_failure";
    detail: string;
    runId: string;
  }) {
    super(
      `Assessment failed. run_id=${params.runId}; code=${params.code}; `
      + `detail=${params.detail}; publication is blocked.`,
    );
    this.name = "AssessmentReportRecordError";
    this.code = params.code;
    this.detail = params.detail;
    this.runId = params.runId;
  }
}

type CreateAssessmentReportOptions = {
  persistence: Step1AssessmentReportPersistence;
  workspaceRoot?: string;
};

function requireText(value: unknown, fieldName: string, runId: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new AssessmentReportRecordError({
      code: "assessment_input_missing",
      detail: `${fieldName} must be a non-empty string.`,
      runId,
    });
  }
  return text;
}

function normalizeForcedFailures(
  value: unknown,
  runId: string,
): Step1AssessmentBlockingReason[] {
  if (!Array.isArray(value)) return [];

  return value.map((entry, index) => {
    const item = typeof entry === "object" && entry !== null ? entry as Record<string, unknown> : null;
    const reasonCode = String(item?.reasonCode ?? "").trim();
    const reasonDetail = String(item?.reasonDetail ?? "").trim();
    const dependencyId = String(item?.dependencyId ?? "").trim() || null;
    const dependencyClassificationRaw = String(item?.dependencyClassification ?? "").trim().toLowerCase();
    const dependencyClassification =
      dependencyClassificationRaw === "publication_critical"
      || dependencyClassificationRaw === "non_critical"
      || dependencyClassificationRaw === "not_applicable"
        ? dependencyClassificationRaw
        : null;

    if (!reasonCode || !reasonDetail) {
      throw new AssessmentReportRecordError({
        code: "assessment_input_missing",
        detail: `forcedFailures[${index}] must include reasonCode and reasonDetail.`,
        runId,
      });
    }

    return {
      reason_code: reasonCode,
      reason_detail: reasonDetail,
      dependency_id: dependencyId,
      dependency_classification: dependencyClassification,
    } satisfies Step1AssessmentBlockingReason;
  });
}

async function loadCandidateBundleManifest(
  candidateBundleManifestPath: string,
  runId: string,
): Promise<{ manifest: NonNullable<ReturnType<typeof parseStoredStep1CandidateBundleManifest>>; raw: string }> {
  try {
    const raw = await readFile(candidateBundleManifestPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    const manifest = parseStoredStep1CandidateBundleManifest(parsed);
    if (!manifest) {
      throw new Error("candidate bundle manifest is invalid.");
    }
    return { manifest, raw };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to read candidate bundle manifest.";
    throw new AssessmentReportRecordError({
      code: "assessment_input_missing",
      detail: `candidate_bundle_manifest_path read failed: ${detail}`,
      runId,
    });
  }
}

function buildEvidenceReferences(params: {
  candidateBundleManifestPath: string;
  candidateBundleManifestDigestSha256: string;
  candidateBundleId: string;
  assessmentRuleSetId: string;
}): Step1AssessmentEvidenceReference[] {
  return [
    {
      evidence_kind: "candidate_bundle_manifest",
      evidence_id: params.candidateBundleId,
      evidence_path: params.candidateBundleManifestPath,
      evidence_digest_sha256: params.candidateBundleManifestDigestSha256,
    },
    {
      evidence_kind: "assessment_rule_set",
      evidence_id: params.assessmentRuleSetId,
      evidence_path: null,
      evidence_digest_sha256: sha256Text(params.assessmentRuleSetId),
    },
  ];
}

function buildAssessmentReport(params: {
  candidateBundleManifestPath: string;
  candidateBundleManifestDigestSha256: string;
  candidateBundleId: string;
  assessmentRuleSetId: string;
  forcedFailures: Step1AssessmentBlockingReason[];
  executedAtUtc: string;
}): Step1AssessmentReportArtifact {
  const disposition: Step1AssessmentDisposition = params.forcedFailures.length > 0 ? "fail" : "pass";
  const canonicalInput = {
    candidate_bundle_id: params.candidateBundleId,
    assessment_rule_set_id: params.assessmentRuleSetId,
    disposition,
    blocking_reason_details: params.forcedFailures,
  };
  const digest = sha256Text(stableJsonStringify(canonicalInput));

  return {
    assessment_report_id: `assessment_report_v1_${digest.slice(0, 24)}`,
    candidate_bundle_id: params.candidateBundleId,
    assessment_rule_set_id: params.assessmentRuleSetId,
    disposition,
    blocking_reason_codes: params.forcedFailures.map((reason) => reason.reason_code),
    blocking_reason_details: params.forcedFailures,
    evidence_references: buildEvidenceReferences({
      candidateBundleManifestPath: params.candidateBundleManifestPath,
      candidateBundleManifestDigestSha256: params.candidateBundleManifestDigestSha256,
      candidateBundleId: params.candidateBundleId,
      assessmentRuleSetId: params.assessmentRuleSetId,
    }),
    publication_allowed: disposition === "pass",
    created_at_utc: params.executedAtUtc,
  };
}

function classifyFailureCode(report: Step1AssessmentReportArtifact): AssessmentReportRecordError["code"] {
  if (report.disposition !== "fail") return "assessment_rule_failure";
  if (report.blocking_reason_details.some((reason) => reason.dependency_classification === "publication_critical")) {
    return "critical_dependency_unsatisfied";
  }
  return "assessment_rule_failure";
}

export async function createAssessmentReportRecord(
  input: AssessmentReportRecordInput,
  options: CreateAssessmentReportOptions,
): Promise<AssessmentReportRecordResult> {
  const runId = requireText(input.runId, "run_id", input.runId || "pending");
  const candidateBundleManifestPath = requireText(
    input.candidateBundleManifestPath,
    "candidate_bundle_manifest_path",
    runId,
  );
  const assessmentRuleSetId = requireText(input.assessmentRuleSetId, "assessment_rule_set_id", runId);
  const forcedFailures = normalizeForcedFailures(input.forcedFailures, runId);
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = options.persistence;
  const executedAtUtc = nowExecutionTimestampUtc();

  const { manifest, raw } = await loadCandidateBundleManifest(candidateBundleManifestPath, runId);
  const candidateBundleManifestDigestSha256 = sha256Text(raw);
  const report = buildAssessmentReport({
    candidateBundleManifestPath,
    candidateBundleManifestDigestSha256,
    candidateBundleId: manifest.candidate_bundle_id,
    assessmentRuleSetId,
    forcedFailures,
    executedAtUtc,
  });
  const reportPath = resolveStep1AssessmentReportPath(workspaceRoot, runId);
  const assessmentReportRow = createAssessmentReportRow({
    runId,
    candidateBundleManifestPath,
    reportPath,
    createdAtUtc: report.created_at_utc,
    report,
  });
  const phaseRow = createAssessmentGatePhaseRow({
    runId,
    candidateBundleManifestPath,
    reportPath,
    completedAtUtc: report.created_at_utc,
    report,
  });

  try {
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    await persistence.ensureReady();
    await persistence.writeAssessmentReportRow(assessmentReportRow);
    await persistence.writePhaseRow(phaseRow);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown assessment state persistence failure.";
    throw new AssessmentReportRecordError({
      code: "assessment_state_persistence_failure",
      detail,
      runId,
    });
  }

  if (report.disposition === "fail") {
    throw new AssessmentReportRecordError({
      code: classifyFailureCode(report),
      detail: report.blocking_reason_details.map((reason) => `${reason.reason_code}: ${reason.reason_detail}`).join("; "),
      runId,
    });
  }

  return {
    report,
    reportPath,
    assessmentReportRow,
    phaseRow,
  };
}

export async function createAssessmentReportRecordAllowFail(
  input: AssessmentReportRecordInput,
  options: CreateAssessmentReportOptions,
): Promise<AssessmentReportRecordResult> {
  const runId = requireText(input.runId, "run_id", input.runId || "pending");
  const candidateBundleManifestPath = requireText(
    input.candidateBundleManifestPath,
    "candidate_bundle_manifest_path",
    runId,
  );
  const assessmentRuleSetId = requireText(input.assessmentRuleSetId, "assessment_rule_set_id", runId);
  const forcedFailures = normalizeForcedFailures(input.forcedFailures, runId);
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = options.persistence;
  const executedAtUtc = nowExecutionTimestampUtc();

  const { manifest, raw } = await loadCandidateBundleManifest(candidateBundleManifestPath, runId);
  const candidateBundleManifestDigestSha256 = sha256Text(raw);
  const report = buildAssessmentReport({
    candidateBundleManifestPath,
    candidateBundleManifestDigestSha256,
    candidateBundleId: manifest.candidate_bundle_id,
    assessmentRuleSetId,
    forcedFailures,
    executedAtUtc,
  });
  const reportPath = resolveStep1AssessmentReportPath(workspaceRoot, runId);
  const assessmentReportRow = createAssessmentReportRow({
    runId,
    candidateBundleManifestPath,
    reportPath,
    createdAtUtc: report.created_at_utc,
    report,
  });
  const phaseRow = createAssessmentGatePhaseRow({
    runId,
    candidateBundleManifestPath,
    reportPath,
    completedAtUtc: report.created_at_utc,
    report,
  });

  try {
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    await persistence.ensureReady();
    await persistence.writeAssessmentReportRow(assessmentReportRow);
    await persistence.writePhaseRow(phaseRow);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown assessment state persistence failure.";
    throw new AssessmentReportRecordError({
      code: "assessment_state_persistence_failure",
      detail,
      runId,
    });
  }

  return {
    report,
    reportPath,
    assessmentReportRow,
    phaseRow,
  };
}
