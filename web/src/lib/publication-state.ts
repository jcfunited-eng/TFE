import type { Pool } from "pg";

import {
  columnExists,
  type AttemptFailure,
  isPostgresConfigured,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  resolveRuntimeSource as resolveSourceName,
  resolveRuntimeSource as resolveRuntimeSourceValue,
  RUNTIME_DECISIONS_TABLE,
  RUNTIME_REFRESH_RUNS_TABLE,
  runtimeSourceIsPostgres,
  tableExists,
  toIsoOrNull,
  toLowerTextOrNull,
  toNumberOrNull,
  toTextOrNull,
} from "@/lib/runtime-db";
import { resolveCanonicalPublicationBundleContract } from "@/lib/publication-bundle-contract";
import {
  readStep1ProofStore,
  selectStep1ActivePublicationPointerRow,
  selectStep1AssessmentReportRow,
  selectStep1PublicationBundleRow,
  selectStep1RuntimeRefreshRunRow,
} from "./step1/schema";

const STEP1_ACTIVE_PUBLICATION_POINTER_TABLE = "active_publication_pointer";
const STEP1_PUBLICATION_BUNDLES_TABLE = "publication_bundles";
const STEP1_ACTIVE_POINTER_SOURCE_ENV = "TFE_STEP1_ACTIVE_POINTER_SOURCE";
const STEP1_FILE_PROOF_STORE_PATH_ENV = "TFE_STEP1_FILE_PROOF_STORE_PATH";
const STEP1_TARGET_ENVIRONMENT_ENV = "TFE_STEP1_TARGET_ENVIRONMENT";

export type PublicationActivationState =
  | "activated"
  | "pointer_missing"
  | "pointer_invalid"
  | "activation_failed";

export type PublicationServingState = "allowed" | "blocked";

export type PublicationBlockingReasonCode =
  | "RUNTIME_SOURCE_NOT_POSTGRES"
  | "POSTGRES_NOT_CONFIGURED"
  | "RUNTIME_REFRESH_RUNS_UNAVAILABLE"
  | "ACTIVE_POINTER_MISSING"
  | "ACTIVE_POINTER_INVALID"
  | "ACTIVATION_FAILED"
  | "VALIDATION_STATUS_NOT_PASS"
  | "MISSING_PUBLICATION_IDS"
  | "QUOTE_BINDING_NOT_ALIGNED"
  | "PUBLISHED_RUN_ID_MISSING"
  | "RUNTIME_SNAPSHOT_UNAVAILABLE"
  | "RUNTIME_QUOTE_UNAVAILABLE"
  | "RUNTIME_SNAPSHOT_RUN_MISMATCH"
  | "RUNTIME_QUOTE_RUN_MISMATCH"
  | "SNAPSHOT_STALE"
  | "UNKNOWN_BLOCK";

type RefreshRunColumnPresence = {
  bundleGeneratedAtUtc: boolean;
  snapshotPublicationId: boolean;
  quotePublicationId: boolean;
  quoteBindingStatus: boolean;
  validationStatus: boolean;
  isActivePublication: boolean;
  activationState: boolean;
  servingState: boolean;
  blockingReasonCode: boolean;
  blockingReasonDetail: boolean;
  failureCode: boolean;
  failureDetail: boolean;
  updatedAt: boolean;
};

export type PublicationRefreshRunRow = {
  runId: string | null;
  generatedAtUtc: string | null;
  completedAtUtc: string | null;
  reportGeneratedAtUtc: string | null;
  bundleGeneratedAtUtc: string | null;
  snapshotPublicationId: string | null;
  quotePublicationId: string | null;
  quoteBindingStatus: string | null;
  validationStatus: string | null;
  mode: string | null;
  triggerSource: string | null;
  rowsWritten: number | null;
  reportStatus: string | null;
  isActivePublication: boolean;
  activationState: PublicationActivationState | null;
  servingState: PublicationServingState | null;
  blockingReasonCode: string | null;
  blockingReasonDetail: string | null;
  failureCode: string | null;
  failureDetail: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export type RuntimeSnapshotServingContext = {
  available: boolean;
  runId: string | null;
  generatedAtUtc: string | null;
};

export type RuntimeQuoteServingContext = {
  available: boolean;
  runId: string | null;
};

export type CanonicalPublicationState = PublicationRefreshRunRow & {
  candidateValid: boolean;
  activationState: PublicationActivationState;
  servingState: PublicationServingState;
  blockingReasonCode: PublicationBlockingReasonCode | null;
  blockingReasonDetail: string | null;
  activeRuntimeRunId: string | null;
  activeRuntimeGeneratedAtUtc: string | null;
  snapshotRunId: string | null;
  quoteRunId: string | null;
  freshness: {
    generatedAtUtc: string | null;
    generatedAtValid: boolean;
    snapshotAgeMinutes: number | null;
    snapshotMaxAgeMinutes: number;
    stale: boolean;
  };
  latestRunId: string | null;
};

export type PublicationContractFields = {
  run_id: string | null;
  generated_at_utc: string | null;
  validation_status: string | null;
  snapshot_publication_id: string | null;
  quote_publication_id: string | null;
  quote_binding_status: string | null;
  serving_state: PublicationServingState;
  activation_state: PublicationActivationState;
  blocking_reason_code: PublicationBlockingReasonCode | null;
  blocking_reason_detail: string | null;
};

type CanonicalPublicationStateInput = {
  snapshot?: RuntimeSnapshotServingContext | null;
  quote?: RuntimeQuoteServingContext | null;
  maxAgeMinutes?: number;
  nowMs?: number;
};

type RuntimeActiveRowMeta = {
  runId: string | null;
  generatedAtUtc: string | null;
  error: string | null;
};

export type ActivePublicationBundlePointerResolution = {
  publicationBundleId: string | null;
  runId: string | null;
  targetEnvironment: string | null;
  sourceKind: "active_publication_pointer" | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export type Step1CutoverActivePublicationResolution = {
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
  candidateValid: boolean;
  blockingReasonCode: PublicationBlockingReasonCode | null;
  blockingReasonDetail: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

type PersistPublicationStateParams = {
  runId: string;
  activationState: PublicationActivationState;
  servingState: PublicationServingState;
  blockingReasonCode: string | null;
  blockingReasonDetail: string | null;
  failureCode?: string | null;
  failureDetail?: string | null;
};

function step1ActivePointerSourceEnabled(): boolean {
  return String(process.env[STEP1_ACTIVE_POINTER_SOURCE_ENV] ?? "").trim().toLowerCase() === "cutover";
}

function step1FileProofStorePath(): string | null {
  const value = String(process.env[STEP1_FILE_PROOF_STORE_PATH_ENV] ?? "").trim();
  return value || null;
}

function step1TargetEnvironment(): string {
  return String(process.env[STEP1_TARGET_ENVIRONMENT_ENV] ?? "production").trim() || "production";
}

function step1ActivePointerSourcePath(targetEnvironment: string): string {
  const proofStorePath = step1FileProofStorePath();
  if (proofStorePath) {
    return `${proofStorePath}#active_publication_pointer/${targetEnvironment}`;
  }
  return postgresSourcePath(STEP1_ACTIVE_PUBLICATION_POINTER_TABLE);
}

async function resolveStep1ProofStoreActivePublicationBundleId(
  targetEnvironment: string,
): Promise<ActivePublicationBundlePointerResolution> {
  const storePath = step1FileProofStorePath();
  const sourcePath = step1ActivePointerSourcePath(targetEnvironment);
  const failures: AttemptFailure[] = [];
  if (!storePath) {
    failures.push({
      path: sourcePath,
      reason: "TFE_STEP1_FILE_PROOF_STORE_PATH is not configured.",
    });
    return {
      publicationBundleId: null,
      runId: null,
      targetEnvironment,
      sourceKind: "active_publication_pointer",
      sourcePath,
      failures,
    };
  }

  const store = await readStep1ProofStore(storePath);
  const pointerRow = selectStep1ActivePublicationPointerRow(store, targetEnvironment);
  if (!pointerRow) {
    failures.push({
      path: sourcePath,
      reason: `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`,
    });
    return {
      publicationBundleId: null,
      runId: null,
      targetEnvironment,
      sourceKind: "active_publication_pointer",
      sourcePath,
      failures,
    };
  }

  const bundleRow = selectStep1PublicationBundleRow(store, pointerRow.publication_bundle_id);
  if (!bundleRow) {
    failures.push({
      path: sourcePath,
      reason: `publication_bundles row missing for publication_bundle_id='${pointerRow.publication_bundle_id}'.`,
    });
    return {
      publicationBundleId: null,
      runId: pointerRow.run_id,
      targetEnvironment,
      sourceKind: "active_publication_pointer",
      sourcePath,
      failures,
    };
  }

  return {
    publicationBundleId: bundleRow.publication_bundle_id,
    runId: pointerRow.run_id,
    targetEnvironment,
    sourceKind: "active_publication_pointer",
    sourcePath,
    failures,
  };
}

async function resolveStep1PostgresActivePublicationBundleId(
  pool: Pool,
  targetEnvironment: string,
): Promise<ActivePublicationBundlePointerResolution> {
  const sourcePath = postgresSourcePath(STEP1_ACTIVE_PUBLICATION_POINTER_TABLE);
  const failures: AttemptFailure[] = [];
  const [pointerTableExists, bundleTableExists] = await Promise.all([
    tableExists(pool, STEP1_ACTIVE_PUBLICATION_POINTER_TABLE),
    tableExists(pool, STEP1_PUBLICATION_BUNDLES_TABLE),
  ]);
  if (!pointerTableExists || !bundleTableExists) {
    failures.push({
      path: sourcePath,
      reason: "Step 1 publication pointer tables are not available.",
    });
    return {
      publicationBundleId: null,
      runId: null,
      targetEnvironment,
      sourceKind: "active_publication_pointer",
      sourcePath,
      failures,
    };
  }

  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT
        p.publication_bundle_id,
        p.run_id,
        p.target_environment
      FROM ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE} AS p
      INNER JOIN ${STEP1_PUBLICATION_BUNDLES_TABLE} AS b
        ON b.publication_bundle_id = p.publication_bundle_id
      WHERE p.target_environment = $1
      LIMIT 1
    `,
    [targetEnvironment],
  );

  if (result.rows.length === 0) {
    failures.push({
      path: sourcePath,
      reason: `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`,
    });
    return {
      publicationBundleId: null,
      runId: null,
      targetEnvironment,
      sourceKind: "active_publication_pointer",
      sourcePath,
      failures,
    };
  }

  return {
    publicationBundleId: toTextOrNull(result.rows[0]?.publication_bundle_id),
    runId: toTextOrNull(result.rows[0]?.run_id),
    targetEnvironment: toTextOrNull(result.rows[0]?.target_environment) ?? targetEnvironment,
    sourceKind: "active_publication_pointer",
    sourcePath,
    failures,
  };
}

export async function resolveAdminActivePublicationBundleId(): Promise<ActivePublicationBundlePointerResolution> {
  const targetEnvironment = step1TargetEnvironment();
  if (!step1ActivePointerSourceEnabled()) {
    return {
      publicationBundleId: null,
      runId: null,
      targetEnvironment,
      sourceKind: null,
      sourcePath: null,
      failures: [],
    };
  }

  const resolution = await resolveCanonicalPublicationBundleContract({
    targetEnvironment,
    proofStorePath: step1FileProofStorePath(),
  });
  return {
    publicationBundleId: resolution.publicationBundleId,
    runId: resolution.runId,
    targetEnvironment: resolution.targetEnvironment ?? targetEnvironment,
    sourceKind: "active_publication_pointer",
    sourcePath: resolution.sourcePath,
    failures: resolution.failures,
  };
}

function buildStep1CutoverResolution(params: {
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
  candidateValid: boolean;
  blockingReasonCode: PublicationBlockingReasonCode | null;
  blockingReasonDetail: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
}): Step1CutoverActivePublicationResolution {
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
    candidateValid: params.candidateValid,
    blockingReasonCode: params.blockingReasonCode,
    blockingReasonDetail: params.blockingReasonDetail,
    sourcePath: params.sourcePath,
    failures: params.failures,
  };
}

async function resolveStep1CutoverActivePublicationFromProofStore(
  targetEnvironment: string,
): Promise<Step1CutoverActivePublicationResolution> {
  const storePath = step1FileProofStorePath();
  const sourcePath = step1ActivePointerSourcePath(targetEnvironment);
  const failures: AttemptFailure[] = [];
  if (!storePath) {
    failures.push({
      path: sourcePath,
      reason: "TFE_STEP1_FILE_PROOF_STORE_PATH is not configured.",
    });
    return buildStep1CutoverResolution({
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
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: "TFE_STEP1_FILE_PROOF_STORE_PATH is not configured.",
      sourcePath,
      failures,
    });
  }

  const store = await readStep1ProofStore(storePath);
  const pointerRow = selectStep1ActivePublicationPointerRow(store, targetEnvironment);
  if (!pointerRow) {
    failures.push({
      path: sourcePath,
      reason: `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`,
    });
    return buildStep1CutoverResolution({
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
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`,
      sourcePath,
      failures,
    });
  }

  const publicationBundleRow = selectStep1PublicationBundleRow(store, pointerRow.publication_bundle_id);
  if (!publicationBundleRow) {
    const detail = `publication_bundles row missing for publication_bundle_id='${pointerRow.publication_bundle_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildStep1CutoverResolution({
      runId: pointerRow.run_id,
      publicationBundleId: pointerRow.publication_bundle_id,
      assessmentReportId: null,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(pointerRow.updated_at),
      completedAtUtc: null,
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: null,
      mode: null,
      triggerSource: null,
      reportStatus: null,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const assessmentReportRow = selectStep1AssessmentReportRow(store, publicationBundleRow.assessment_report_id);
  if (!assessmentReportRow) {
    const detail = `assessment_reports row missing for assessment_report_id='${publicationBundleRow.assessment_report_id}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildStep1CutoverResolution({
      runId: publicationBundleRow.run_id,
      publicationBundleId: publicationBundleRow.publication_bundle_id,
      assessmentReportId: publicationBundleRow.assessment_report_id,
      targetEnvironment,
      generatedAtUtc: toIsoOrNull(publicationBundleRow.created_at),
      completedAtUtc: toIsoOrNull(publicationBundleRow.created_at),
      reportGeneratedAtUtc: null,
      bundleGeneratedAtUtc: toIsoOrNull(publicationBundleRow.created_at),
      mode: null,
      triggerSource: null,
      reportStatus: null,
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_INVALID",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const mirrorRunRow = selectStep1RuntimeRefreshRunRow(store, publicationBundleRow.run_id);
  const candidateValid = assessmentReportRow.disposition === "pass" && assessmentReportRow.publication_allowed === true;
  const blockingReasonDetail = candidateValid
    ? null
    : `assessment_report_id='${assessmentReportRow.assessment_report_id}' disposition='${assessmentReportRow.disposition}' publication_allowed=${assessmentReportRow.publication_allowed}.`;

  return buildStep1CutoverResolution({
    runId: publicationBundleRow.run_id,
    publicationBundleId: publicationBundleRow.publication_bundle_id,
    assessmentReportId: publicationBundleRow.assessment_report_id,
    targetEnvironment,
    generatedAtUtc: toIsoOrNull(publicationBundleRow.created_at)
      ?? toIsoOrNull(assessmentReportRow.created_at)
      ?? toIsoOrNull(pointerRow.updated_at),
    completedAtUtc: toIsoOrNull(mirrorRunRow?.completed_at) ?? toIsoOrNull(publicationBundleRow.created_at),
    reportGeneratedAtUtc: toIsoOrNull(mirrorRunRow?.report_generated_at_utc) ?? toIsoOrNull(assessmentReportRow.created_at),
    bundleGeneratedAtUtc: toIsoOrNull(publicationBundleRow.created_at),
    mode: toTextOrNull(mirrorRunRow?.mode),
    triggerSource: toTextOrNull(mirrorRunRow?.trigger_source),
    reportStatus: toLowerTextOrNull(mirrorRunRow?.report_status) ?? (candidateValid ? "ok" : "error"),
    candidateValid,
    blockingReasonCode: candidateValid ? null : "ACTIVE_POINTER_INVALID",
    blockingReasonDetail,
    sourcePath,
    failures,
  });
}

async function resolveStep1CutoverActivePublicationFromPostgres(
  pool: Pool,
  targetEnvironment: string,
): Promise<Step1CutoverActivePublicationResolution> {
  const sourcePath = postgresSourcePath(STEP1_ACTIVE_PUBLICATION_POINTER_TABLE);
  const failures: AttemptFailure[] = [];
  const assessmentReportsTable = "assessment_reports";
  const [pointerTableExists, bundleTableExists, assessmentTableExists, runtimeRunsTableExists] = await Promise.all([
    tableExists(pool, STEP1_ACTIVE_PUBLICATION_POINTER_TABLE),
    tableExists(pool, STEP1_PUBLICATION_BUNDLES_TABLE),
    tableExists(pool, assessmentReportsTable),
    tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE),
  ]);

  if (!pointerTableExists || !bundleTableExists || !assessmentTableExists) {
    const detail = "Step 1 publication authority tables are not available.";
    failures.push({ path: sourcePath, reason: detail });
    return buildStep1CutoverResolution({
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
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT
        p.publication_bundle_id,
        p.run_id,
        p.target_environment,
        p.updated_at AS pointer_updated_at,
        b.assessment_report_id,
        b.created_at AS publication_bundle_created_at,
        ar.disposition AS assessment_disposition,
        ar.publication_allowed AS assessment_publication_allowed,
        ar.created_at AS assessment_created_at
      FROM ${STEP1_ACTIVE_PUBLICATION_POINTER_TABLE} AS p
      INNER JOIN ${STEP1_PUBLICATION_BUNDLES_TABLE} AS b
        ON b.publication_bundle_id = p.publication_bundle_id
      INNER JOIN ${assessmentReportsTable} AS ar
        ON ar.run_id = b.run_id
       AND ar.assessment_report_id = b.assessment_report_id
      WHERE p.target_environment = $1
      LIMIT 1
    `,
    [targetEnvironment],
  );

  if (result.rows.length === 0) {
    const detail = `No active_publication_pointer row exists for target_environment='${targetEnvironment}'.`;
    failures.push({ path: sourcePath, reason: detail });
    return buildStep1CutoverResolution({
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
      candidateValid: false,
      blockingReasonCode: "ACTIVE_POINTER_MISSING",
      blockingReasonDetail: detail,
      sourcePath,
      failures,
    });
  }

  const row = result.rows[0];
  const runId = toTextOrNull(row.run_id);
  let mirrorRow: Record<string, unknown> | null = null;
  if (runtimeRunsTableExists && runId) {
    const mirrorResult = await pool.query<Record<string, unknown>>(
      `
        SELECT
          mode,
          trigger_source,
          report_status,
          completed_at,
          report_generated_at_utc
        FROM ${RUNTIME_REFRESH_RUNS_TABLE}
        WHERE run_id = $1
        LIMIT 1
      `,
      [runId],
    );
    mirrorRow = mirrorResult.rows[0] ?? null;
  }

  const candidateValid = toLowerTextOrNull(row.assessment_disposition) === "pass"
    && row.assessment_publication_allowed === true;
  const blockingReasonDetail = candidateValid
    ? null
    : `assessment_report_id='${toTextOrNull(row.assessment_report_id) ?? "null"}' disposition='${toLowerTextOrNull(row.assessment_disposition) ?? "null"}' publication_allowed=${row.assessment_publication_allowed === true}.`;

  return buildStep1CutoverResolution({
    runId,
    publicationBundleId: toTextOrNull(row.publication_bundle_id),
    assessmentReportId: toTextOrNull(row.assessment_report_id),
    targetEnvironment: toTextOrNull(row.target_environment) ?? targetEnvironment,
    generatedAtUtc: toIsoOrNull(row.publication_bundle_created_at)
      ?? toIsoOrNull(row.assessment_created_at)
      ?? toIsoOrNull(row.pointer_updated_at),
    completedAtUtc: toIsoOrNull(mirrorRow?.completed_at) ?? toIsoOrNull(row.publication_bundle_created_at),
    reportGeneratedAtUtc: toIsoOrNull(mirrorRow?.report_generated_at_utc) ?? toIsoOrNull(row.assessment_created_at),
    bundleGeneratedAtUtc: toIsoOrNull(row.publication_bundle_created_at),
    mode: toTextOrNull(mirrorRow?.mode),
    triggerSource: toTextOrNull(mirrorRow?.trigger_source),
    reportStatus: toLowerTextOrNull(mirrorRow?.report_status) ?? (candidateValid ? "ok" : "error"),
    candidateValid,
    blockingReasonCode: candidateValid ? null : "ACTIVE_POINTER_INVALID",
    blockingReasonDetail,
    sourcePath,
    failures,
  });
}

export async function resolveStep1CutoverActivePublicationResolution(): Promise<Step1CutoverActivePublicationResolution> {
  const targetEnvironment = step1TargetEnvironment();
  const resolution = await resolveCanonicalPublicationBundleContract({
    targetEnvironment,
    proofStorePath: step1FileProofStorePath(),
  });
  return buildStep1CutoverResolution({
    runId: resolution.runId,
    publicationBundleId: resolution.publicationBundleId,
    assessmentReportId: resolution.assessmentReportId,
    targetEnvironment: resolution.targetEnvironment ?? targetEnvironment,
    generatedAtUtc: resolution.generatedAtUtc,
    completedAtUtc: resolution.completedAtUtc,
    reportGeneratedAtUtc: resolution.reportGeneratedAtUtc,
    bundleGeneratedAtUtc: resolution.bundleGeneratedAtUtc,
    mode: resolution.mode,
    triggerSource: resolution.triggerSource,
    reportStatus: resolution.reportStatus,
    candidateValid: resolution.candidateValid,
    blockingReasonCode: resolution.blockingReasonCode,
    blockingReasonDetail: resolution.blockingReasonDetail,
    sourcePath: resolution.sourcePath,
    failures: resolution.failures,
  });
}

function buildPublicationRefreshRunRowFromStep1CutoverResolution(
  resolution: Step1CutoverActivePublicationResolution,
): PublicationRefreshRunRow {
  return {
    runId: resolution.runId,
    generatedAtUtc: resolution.generatedAtUtc,
    completedAtUtc: resolution.completedAtUtc,
    reportGeneratedAtUtc: resolution.reportGeneratedAtUtc,
    bundleGeneratedAtUtc: resolution.bundleGeneratedAtUtc,
    snapshotPublicationId: resolution.publicationBundleId,
    quotePublicationId: resolution.publicationBundleId,
    quoteBindingStatus: resolution.publicationBundleId ? (resolution.candidateValid ? "aligned" : "unbound") : null,
    validationStatus: resolution.candidateValid ? "pass" : (resolution.assessmentReportId ? "fail" : null),
    mode: resolution.mode,
    triggerSource: resolution.triggerSource,
    rowsWritten: null,
    reportStatus: resolution.reportStatus,
    isActivePublication: resolution.publicationBundleId !== null,
    activationState: resolution.candidateValid
      ? "activated"
      : resolution.blockingReasonCode === "ACTIVE_POINTER_MISSING"
        ? "pointer_missing"
        : "pointer_invalid",
    servingState: resolution.candidateValid ? "allowed" : "blocked",
    blockingReasonCode: resolution.blockingReasonCode,
    blockingReasonDetail: resolution.blockingReasonDetail,
    failureCode: null,
    failureDetail: null,
    sourcePath: resolution.sourcePath,
    failures: resolution.failures,
  };
}

function normalizePositiveInt(value: unknown, fallback: number, minimum: number, maximum: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < minimum) return minimum;
  if (whole > maximum) return maximum;
  return whole;
}

function investorServingMaxAgeMinutes(): number {
  const explicit = String(process.env.TFE_INVESTOR_SERVING_MAX_AGE_MINUTES ?? "").trim();
  if (explicit) {
    return normalizePositiveInt(explicit, 1800, 5, 20160);
  }
  return normalizePositiveInt(process.env.TFE_RECOMMENDATIONS_MAX_AGE_MINUTES, 1800, 5, 20160);
}

function emptyRefreshRunRow(runId: string | null, sourcePath: string | null, failures: AttemptFailure[]): PublicationRefreshRunRow {
  return {
    runId,
    generatedAtUtc: null,
    completedAtUtc: null,
    reportGeneratedAtUtc: null,
    bundleGeneratedAtUtc: null,
    snapshotPublicationId: null,
    quotePublicationId: null,
    quoteBindingStatus: null,
    validationStatus: null,
    mode: null,
    triggerSource: null,
    rowsWritten: null,
    reportStatus: null,
    isActivePublication: false,
    activationState: null,
    servingState: null,
    blockingReasonCode: null,
    blockingReasonDetail: null,
    failureCode: null,
    failureDetail: null,
    sourcePath,
    failures,
  };
}

function queryOrderClause(columns: RefreshRunColumnPresence): string {
  if (columns.updatedAt) {
    return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST, updated_at DESC NULLS LAST";
  }
  return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST";
}

function selectColumns(columns: RefreshRunColumnPresence): string[] {
  return [
    "run_id",
    "mode",
    "trigger_source",
    "completed_at",
    "report_generated_at_utc",
    "rows_written",
    "report_status",
    columns.bundleGeneratedAtUtc ? "bundle_generated_at_utc" : "NULL::timestamptz AS bundle_generated_at_utc",
    columns.snapshotPublicationId ? "snapshot_publication_id" : "NULL::text AS snapshot_publication_id",
    columns.quotePublicationId ? "quote_publication_id" : "NULL::text AS quote_publication_id",
    columns.quoteBindingStatus ? "quote_binding_status" : "NULL::text AS quote_binding_status",
    columns.validationStatus ? "validation_status" : "NULL::text AS validation_status",
    columns.isActivePublication ? "is_active_publication" : "FALSE AS is_active_publication",
    columns.activationState ? "activation_state" : "NULL::text AS activation_state",
    columns.servingState ? "serving_state" : "NULL::text AS serving_state",
    columns.blockingReasonCode ? "blocking_reason_code" : "NULL::text AS blocking_reason_code",
    columns.blockingReasonDetail ? "blocking_reason_detail" : "NULL::text AS blocking_reason_detail",
    columns.failureCode ? "failure_code" : "NULL::text AS failure_code",
    columns.failureDetail ? "failure_detail" : "NULL::text AS failure_detail",
  ];
}

function normalizeActivationState(value: unknown): PublicationActivationState | null {
  const text = toTextOrNull(value);
  if (
    text === "activated"
    || text === "pointer_missing"
    || text === "pointer_invalid"
    || text === "activation_failed"
  ) {
    return text;
  }
  return null;
}

function normalizeServingState(value: unknown): PublicationServingState | null {
  const text = toTextOrNull(value);
  if (text === "allowed" || text === "blocked") return text;
  return null;
}

function mapRefreshRunRow(
  row: Record<string, unknown> | null | undefined,
  sourcePath: string,
  failures: AttemptFailure[],
): PublicationRefreshRunRow {
  if (!row) {
    return emptyRefreshRunRow(null, sourcePath, failures);
  }

  const runId = toTextOrNull(row.run_id);
  const completedAtUtc = toIsoOrNull(row.completed_at);
  const reportGeneratedAtUtc = toIsoOrNull(row.report_generated_at_utc);
  const bundleGeneratedAtUtc = toIsoOrNull(row.bundle_generated_at_utc);
  const generatedAtUtc = bundleGeneratedAtUtc ?? completedAtUtc ?? reportGeneratedAtUtc;

  return {
    runId,
    generatedAtUtc,
    completedAtUtc,
    reportGeneratedAtUtc,
    bundleGeneratedAtUtc,
    snapshotPublicationId: toTextOrNull(row.snapshot_publication_id),
    quotePublicationId: toTextOrNull(row.quote_publication_id),
    quoteBindingStatus: toLowerTextOrNull(row.quote_binding_status),
    validationStatus: toLowerTextOrNull(row.validation_status),
    mode: toTextOrNull(row.mode),
    triggerSource: toTextOrNull(row.trigger_source),
    rowsWritten: toNumberOrNull(row.rows_written),
    reportStatus: toLowerTextOrNull(row.report_status),
    isActivePublication: row.is_active_publication === true,
    activationState: normalizeActivationState(row.activation_state),
    servingState: normalizeServingState(row.serving_state),
    blockingReasonCode: toTextOrNull(row.blocking_reason_code),
    blockingReasonDetail: toTextOrNull(row.blocking_reason_detail),
    failureCode: toTextOrNull(row.failure_code),
    failureDetail: toTextOrNull(row.failure_detail),
    sourcePath,
    failures,
  };
}

function rowValidityReasonCode(row: PublicationRefreshRunRow): PublicationBlockingReasonCode | null {
  if (row.validationStatus !== "pass") return "VALIDATION_STATUS_NOT_PASS";
  if (!row.snapshotPublicationId || !row.quotePublicationId) return "MISSING_PUBLICATION_IDS";
  if (row.quoteBindingStatus !== "aligned") return "QUOTE_BINDING_NOT_ALIGNED";
  if (!row.runId) return "PUBLISHED_RUN_ID_MISSING";
  return null;
}

function rowValidityReasonDetail(row: PublicationRefreshRunRow): string | null {
  if (row.validationStatus !== "pass") {
    return `validation_status='${row.validationStatus ?? "null"}' on runtime_refresh_runs row.`;
  }
  if (!row.snapshotPublicationId || !row.quotePublicationId) {
    return "snapshot_publication_id or quote_publication_id is missing on runtime_refresh_runs row.";
  }
  if (row.quoteBindingStatus !== "aligned") {
    return `quote_binding_status='${row.quoteBindingStatus ?? "null"}' on runtime_refresh_runs row.`;
  }
  if (!row.runId) {
    return "run_id is missing on runtime_refresh_runs row.";
  }
  return null;
}

export function publicationCandidateIsValid(row: PublicationRefreshRunRow | null | undefined): boolean {
  if (!row) return false;
  return rowValidityReasonCode(row) === null;
}

async function loadColumnPresence(pool: Pool): Promise<RefreshRunColumnPresence> {
  const [
    bundleGeneratedAtUtc,
    snapshotPublicationId,
    quotePublicationId,
    quoteBindingStatus,
    validationStatus,
    isActivePublication,
    activationState,
    servingState,
    blockingReasonCode,
    blockingReasonDetail,
    failureCode,
    failureDetail,
    updatedAt,
  ] = await Promise.all([
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "bundle_generated_at_utc"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "snapshot_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_binding_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "validation_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "is_active_publication"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "activation_state"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "serving_state"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "blocking_reason_code"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "blocking_reason_detail"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "failure_code"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "failure_detail"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "updated_at"),
  ]);

  return {
    bundleGeneratedAtUtc,
    snapshotPublicationId,
    quotePublicationId,
    quoteBindingStatus,
    validationStatus,
    isActivePublication,
    activationState,
    servingState,
    blockingReasonCode,
    blockingReasonDetail,
    failureCode,
    failureDetail,
    updatedAt,
  };
}

async function queryRefreshRunByRunId(
  pool: Pool,
  columns: RefreshRunColumnPresence,
  runId: string,
): Promise<PublicationRefreshRunRow | null> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns(columns).join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE run_id = $1
      LIMIT 1
    `,
    [runId],
  );

  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

async function queryLatestRefreshRun(pool: Pool, columns: RefreshRunColumnPresence): Promise<PublicationRefreshRunRow | null> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns(columns).join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      ${queryOrderClause(columns)}
      LIMIT 1
    `,
  );

  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

async function queryActiveRefreshRun(pool: Pool, columns: RefreshRunColumnPresence): Promise<PublicationRefreshRunRow | null> {
  if (step1ActivePointerSourceEnabled() && !step1FileProofStorePath()) {
    const pointerResolution = await resolveStep1PostgresActivePublicationBundleId(pool, step1TargetEnvironment());
    if (pointerResolution.runId) {
      return queryRefreshRunByRunId(pool, columns, pointerResolution.runId);
    }
    return null;
  }

  if (!columns.isActivePublication) {
    return null;
  }

  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns(columns).join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE is_active_publication IS TRUE
      ${queryOrderClause(columns)}
      LIMIT 1
    `,
  );

  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

async function loadRuntimeActiveRowMeta(pool: Pool): Promise<RuntimeActiveRowMeta> {
  const decisionsTableExists = await tableExists(pool, RUNTIME_DECISIONS_TABLE);
  if (!decisionsTableExists) {
    return {
      runId: null,
      generatedAtUtc: null,
      error: `Table '${RUNTIME_DECISIONS_TABLE}' does not exist.`,
    };
  }

  const result = await pool.query<{ run_id: string | null; generated_at_utc: string | Date | null }>(
    `
      SELECT run_id, generated_at_utc
      FROM ${RUNTIME_DECISIONS_TABLE}
      ORDER BY generated_at_utc DESC NULLS LAST, ticker ASC
      LIMIT 1
    `,
  );

  if (result.rows.length === 0) {
    return {
      runId: null,
      generatedAtUtc: null,
      error: `Table '${RUNTIME_DECISIONS_TABLE}' is empty.`,
    };
  }

  return {
    runId: toTextOrNull(result.rows[0]?.run_id),
    generatedAtUtc: toIsoOrNull(result.rows[0]?.generated_at_utc),
    error: null,
  };
}

async function loadOptionalRuntimeActiveRowMeta(): Promise<RuntimeActiveRowMeta> {
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    return {
      runId: null,
      generatedAtUtc: null,
      error: null,
    };
  }

  try {
    const pool = resolveRuntimePostgresPool();
    return await loadRuntimeActiveRowMeta(pool);
  } catch (error) {
    return {
      runId: null,
      generatedAtUtc: null,
      error: error instanceof Error ? error.message : "Unknown runtime active row query error.",
    };
  }
}

function resolveBlockedState(
  baseRow: PublicationRefreshRunRow,
  latestRunId: string | null,
  activeRuntime: RuntimeActiveRowMeta,
  snapshot: RuntimeSnapshotServingContext | null | undefined,
  quote: RuntimeQuoteServingContext | null | undefined,
  activationState: PublicationActivationState,
  code: PublicationBlockingReasonCode,
  detail: string,
  maxAgeMinutes: number,
  generatedAtUtc: string | null,
): CanonicalPublicationState {
  const parsedGeneratedAt = toIsoOrNull(generatedAtUtc);
  const parsedMs = parsedGeneratedAt ? Date.parse(parsedGeneratedAt) : Number.NaN;
  const nowMs = Date.now();
  const snapshotAgeMinutes = Number.isFinite(parsedMs) ? Number(Math.max(0, (nowMs - parsedMs) / 60000).toFixed(3)) : null;

  return {
    ...baseRow,
    candidateValid: publicationCandidateIsValid(baseRow),
    activationState,
    servingState: "blocked",
    blockingReasonCode: code,
    blockingReasonDetail: detail,
    activeRuntimeRunId: activeRuntime.runId,
    activeRuntimeGeneratedAtUtc: activeRuntime.generatedAtUtc,
    snapshotRunId: snapshot?.runId ?? null,
    quoteRunId: quote?.runId ?? null,
    freshness: {
      generatedAtUtc: parsedGeneratedAt,
      generatedAtValid: Number.isFinite(parsedMs),
      snapshotAgeMinutes,
      snapshotMaxAgeMinutes: maxAgeMinutes,
      stale: code === "SNAPSHOT_STALE",
    },
    latestRunId,
  };
}

export async function loadRuntimeRefreshRunById(runId: string | null | undefined): Promise<PublicationRefreshRunRow> {
  const normalizedRunId = toTextOrNull(runId);
  const failures: AttemptFailure[] = [];
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);

  if (!normalizedRunId) {
    return emptyRefreshRunRow(null, sourcePath, failures);
  }

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSourceValue()}'; expected 'postgres'.`,
    });
    return emptyRefreshRunRow(normalizedRunId, sourcePath, failures);
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return emptyRefreshRunRow(normalizedRunId, sourcePath, failures);
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const exists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!exists) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
      });
      return emptyRefreshRunRow(normalizedRunId, sourcePath, failures);
    }

    const columns = await loadColumnPresence(pool);
    const row = await queryRefreshRunByRunId(pool, columns, normalizedRunId);
    if (!row) {
      failures.push({
        path: sourcePath,
        reason: `No runtime_refresh_runs row found for run_id='${normalizedRunId}'.`,
      });
      return emptyRefreshRunRow(normalizedRunId, sourcePath, failures);
    }

    return {
      ...row,
      failures,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown runtime refresh run query error.",
    });
    return emptyRefreshRunRow(normalizedRunId, sourcePath, failures);
  }
}

export async function loadLatestRuntimeRefreshRunState(): Promise<PublicationRefreshRunRow> {
  const failures: AttemptFailure[] = [];
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveSourceName()}'; expected 'postgres'.`,
    });
    return emptyRefreshRunRow(null, sourcePath, failures);
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return emptyRefreshRunRow(null, sourcePath, failures);
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const exists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!exists) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
      });
      return emptyRefreshRunRow(null, sourcePath, failures);
    }

    const columns = await loadColumnPresence(pool);
    const row = await queryLatestRefreshRun(pool, columns);
    if (!row) {
      failures.push({
        path: sourcePath,
        reason: "No runtime_refresh_runs rows are present.",
      });
      return emptyRefreshRunRow(null, sourcePath, failures);
    }

    return {
      ...row,
      failures,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown latest runtime refresh query error.",
    });
    return emptyRefreshRunRow(null, sourcePath, failures);
  }
}

export async function ensurePublicationStateColumns(): Promise<void> {
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    return;
  }

  const pool = resolveRuntimePostgresPool();
  await pool.query(`
    ALTER TABLE ${RUNTIME_REFRESH_RUNS_TABLE}
    ADD COLUMN IF NOT EXISTS activation_state TEXT,
    ADD COLUMN IF NOT EXISTS serving_state TEXT,
    ADD COLUMN IF NOT EXISTS blocking_reason_code TEXT,
    ADD COLUMN IF NOT EXISTS blocking_reason_detail TEXT,
    ADD COLUMN IF NOT EXISTS failure_code TEXT,
    ADD COLUMN IF NOT EXISTS failure_detail TEXT
  `);
}

export async function setActivePublicationRun(runId: string): Promise<boolean> {
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    return false;
  }

  await ensurePublicationStateColumns();
  const pool = resolveRuntimePostgresPool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");
    const result = await client.query(
      `
        UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
        SET is_active_publication = CASE WHEN run_id = $1 THEN TRUE ELSE FALSE END,
            updated_at = NOW()
        WHERE is_active_publication IS TRUE OR run_id = $1
      `,
      [runId],
    );
    await client.query("COMMIT");
    return Number(result.rowCount ?? 0) > 0;
  } catch {
    try {
      await client.query("ROLLBACK");
    } catch {
      // Ignore rollback failures.
    }
    throw new Error(`Failed to update active publication pointer for run_id='${runId}'.`);
  } finally {
    client.release();
  }
}

export async function persistPublicationStateForRun(params: PersistPublicationStateParams): Promise<void> {
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    throw new Error("Runtime Postgres is not configured; cannot persist publication state.");
  }

  await ensurePublicationStateColumns();
  const pool = resolveRuntimePostgresPool();
  await pool.query(
    `
      UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
      SET activation_state = $2,
          serving_state = $3,
          blocking_reason_code = $4,
          blocking_reason_detail = $5,
          failure_code = $6,
          failure_detail = $7,
          updated_at = NOW()
      WHERE run_id = $1
    `,
    [
      params.runId,
      params.activationState,
      params.servingState,
      params.blockingReasonCode,
      params.blockingReasonDetail,
      params.failureCode ?? null,
      params.failureDetail ?? null,
    ],
  );
}

export async function loadCanonicalPublicationState(
  input: CanonicalPublicationStateInput = {},
): Promise<CanonicalPublicationState> {
  if (step1ActivePointerSourceEnabled()) {
    const maxAgeMinutes = normalizePositiveInt(input.maxAgeMinutes, investorServingMaxAgeMinutes(), 5, 20160);
    const nowMs = Number.isFinite(Number(input.nowMs)) ? Number(input.nowMs) : Date.now();
    const snapshot = input.snapshot ?? null;
    const quote = input.quote ?? null;
    const resolution = await resolveStep1CutoverActivePublicationResolution();
    const activeRuntime = await loadOptionalRuntimeActiveRowMeta();
    const activeRuntimeFailures: AttemptFailure[] = [];
    if (activeRuntime.error) {
      activeRuntimeFailures.push({
        path: postgresSourcePath(RUNTIME_DECISIONS_TABLE),
        reason: activeRuntime.error,
      });
    }

    const baseRow = buildPublicationRefreshRunRowFromStep1CutoverResolution(resolution);
    const baseWithFailures = {
      ...baseRow,
      failures: [...baseRow.failures, ...activeRuntimeFailures],
      sourcePath: baseRow.sourcePath ?? resolution.sourcePath,
    };
    const latestRunId = baseRow.runId;

    if (!resolution.candidateValid) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        baseRow.activationState ?? "pointer_invalid",
        resolution.blockingReasonCode ?? "ACTIVE_POINTER_INVALID",
        resolution.blockingReasonDetail ?? "Active Step 1 publication pointer is not valid for serving.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        baseRow.activationState ?? "pointer_invalid",
        "PUBLISHED_RUN_ID_MISSING",
        "Active Step 1 publication pointer row is missing run_id.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!snapshot?.available) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        "activated",
        "RUNTIME_SNAPSHOT_UNAVAILABLE",
        "Investor serving is blocked because the active published snapshot is unavailable from runtime Postgres.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!quote?.available) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        "activated",
        "RUNTIME_QUOTE_UNAVAILABLE",
        "Investor serving is blocked because the active published quote cache is unavailable from runtime Postgres.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (snapshot.runId !== baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        "activated",
        "RUNTIME_SNAPSHOT_RUN_MISMATCH",
        `Runtime snapshot run_id='${snapshot.runId ?? "null"}' does not match active publication run_id='${baseRow.runId}'.`,
        maxAgeMinutes,
        baseRow.generatedAtUtc ?? snapshot.generatedAtUtc,
      );
    }

    if (quote.runId !== baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        "activated",
        "RUNTIME_QUOTE_RUN_MISMATCH",
        `Runtime quote run_id='${quote.runId ?? "null"}' does not match active publication run_id='${baseRow.runId}'.`,
        maxAgeMinutes,
        baseRow.generatedAtUtc ?? snapshot.generatedAtUtc,
      );
    }

    const generatedAtUtc = toIsoOrNull(baseRow.generatedAtUtc ?? snapshot.generatedAtUtc);
    const generatedAtMs = generatedAtUtc ? Date.parse(generatedAtUtc) : Number.NaN;
    const snapshotAgeMinutes = Number.isFinite(generatedAtMs)
      ? Number(Math.max(0, (nowMs - generatedAtMs) / 60000).toFixed(3))
      : null;
    const stale = !Number.isFinite(generatedAtMs) || ((snapshotAgeMinutes ?? Number.POSITIVE_INFINITY) > maxAgeMinutes);

    if (stale) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        "activated",
        "SNAPSHOT_STALE",
        generatedAtUtc
          ? `Published snapshot age ${snapshotAgeMinutes ?? "unknown"} minutes exceeds max age ${maxAgeMinutes}.`
          : "Published snapshot generated_at_utc is missing or invalid.",
        maxAgeMinutes,
        generatedAtUtc,
      );
    }

    return {
      ...baseWithFailures,
      candidateValid: true,
      activationState: "activated",
      servingState: "allowed",
      blockingReasonCode: null,
      blockingReasonDetail: null,
      activeRuntimeRunId: activeRuntime.runId,
      activeRuntimeGeneratedAtUtc: activeRuntime.generatedAtUtc,
      snapshotRunId: snapshot.runId,
      quoteRunId: quote.runId,
      freshness: {
        generatedAtUtc,
        generatedAtValid: true,
        snapshotAgeMinutes,
        snapshotMaxAgeMinutes: maxAgeMinutes,
        stale: false,
      },
      latestRunId,
    };
  }

  const failures: AttemptFailure[] = [];
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const maxAgeMinutes = normalizePositiveInt(input.maxAgeMinutes, investorServingMaxAgeMinutes(), 5, 20160);
  const nowMs = Number.isFinite(Number(input.nowMs)) ? Number(input.nowMs) : Date.now();
  const snapshot = input.snapshot ?? null;
  const quote = input.quote ?? null;

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return resolveBlockedState(
      emptyRefreshRunRow(null, sourcePath, failures),
      null,
      { runId: null, generatedAtUtc: null, error: null },
      snapshot,
      quote,
      "pointer_missing",
      "RUNTIME_SOURCE_NOT_POSTGRES",
      `Runtime source is '${resolveRuntimeSource()}'; investor serving requires canonical Postgres publication state.`,
      maxAgeMinutes,
      null,
    );
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return resolveBlockedState(
      emptyRefreshRunRow(null, sourcePath, failures),
      null,
      { runId: null, generatedAtUtc: null, error: null },
      snapshot,
      quote,
      "pointer_missing",
      "POSTGRES_NOT_CONFIGURED",
      "Investor serving is blocked because canonical Postgres publication state is not configured.",
      maxAgeMinutes,
      null,
    );
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const runsTableExists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!runsTableExists) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
      });
      return resolveBlockedState(
        emptyRefreshRunRow(null, sourcePath, failures),
        null,
        { runId: null, generatedAtUtc: null, error: null },
        snapshot,
        quote,
        "pointer_missing",
        "RUNTIME_REFRESH_RUNS_UNAVAILABLE",
        `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
        maxAgeMinutes,
        null,
      );
    }

    const columns = await loadColumnPresence(pool);
    const [latestRow, activeRow, activeRuntime] = await Promise.all([
      queryLatestRefreshRun(pool, columns),
      queryActiveRefreshRun(pool, columns),
      loadRuntimeActiveRowMeta(pool),
    ]);

    if (activeRuntime.error) {
      failures.push({
        path: postgresSourcePath(RUNTIME_DECISIONS_TABLE),
        reason: activeRuntime.error,
      });
    }

    const latestRunId = latestRow?.runId ?? null;
    const activeRowValid = publicationCandidateIsValid(activeRow);

    let activationState: PublicationActivationState;
    let baseRow: PublicationRefreshRunRow;
    if (activeRow && activeRowValid) {
      activationState = "activated";
      baseRow = activeRow;
    } else if (!activeRow && latestRow?.activationState === "activation_failed") {
      activationState = "activation_failed";
      baseRow = latestRow;
    } else if (!activeRow) {
      activationState = "pointer_missing";
      baseRow = latestRow ?? emptyRefreshRunRow(null, sourcePath, failures);
    } else {
      activationState = "pointer_invalid";
      baseRow = activeRow;
    }

    const baseWithFailures = {
      ...baseRow,
      failures: [...baseRow.failures, ...failures],
      sourcePath: baseRow.sourcePath ?? sourcePath,
    };

    if (activationState === "activation_failed") {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "ACTIVATION_FAILED",
        baseRow.failureDetail
          ?? baseRow.blockingReasonDetail
          ?? "The latest candidate publication finished but activation did not complete.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (activationState === "pointer_missing") {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "ACTIVE_POINTER_MISSING",
        "No active publication pointer is set in runtime_refresh_runs.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (activationState === "pointer_invalid") {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "ACTIVE_POINTER_INVALID",
        rowValidityReasonDetail(baseRow) ?? "Active publication pointer row is not valid for serving.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "PUBLISHED_RUN_ID_MISSING",
        "Active publication row is missing run_id.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!snapshot?.available) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "RUNTIME_SNAPSHOT_UNAVAILABLE",
        "Investor serving is blocked because the active published snapshot is unavailable from runtime Postgres.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (!quote?.available) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "RUNTIME_QUOTE_UNAVAILABLE",
        "Investor serving is blocked because the active published quote cache is unavailable from runtime Postgres.",
        maxAgeMinutes,
        baseRow.generatedAtUtc,
      );
    }

    if (snapshot.runId !== baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "RUNTIME_SNAPSHOT_RUN_MISMATCH",
        `Runtime snapshot run_id='${snapshot.runId ?? "null"}' does not match active publication run_id='${baseRow.runId}'.`,
        maxAgeMinutes,
        baseRow.generatedAtUtc ?? snapshot.generatedAtUtc,
      );
    }

    if (quote.runId !== baseRow.runId) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "RUNTIME_QUOTE_RUN_MISMATCH",
        `Runtime quote run_id='${quote.runId ?? "null"}' does not match active publication run_id='${baseRow.runId}'.`,
        maxAgeMinutes,
        baseRow.generatedAtUtc ?? snapshot.generatedAtUtc,
      );
    }

    const generatedAtUtc = toIsoOrNull(baseRow.generatedAtUtc ?? snapshot.generatedAtUtc);
    const generatedAtMs = generatedAtUtc ? Date.parse(generatedAtUtc) : Number.NaN;
    const snapshotAgeMinutes = Number.isFinite(generatedAtMs)
      ? Number(Math.max(0, (nowMs - generatedAtMs) / 60000).toFixed(3))
      : null;
    const stale = !Number.isFinite(generatedAtMs) || ((snapshotAgeMinutes ?? Number.POSITIVE_INFINITY) > maxAgeMinutes);

    if (stale) {
      return resolveBlockedState(
        baseWithFailures,
        latestRunId,
        activeRuntime,
        snapshot,
        quote,
        activationState,
        "SNAPSHOT_STALE",
        generatedAtUtc
          ? `Published snapshot age ${snapshotAgeMinutes ?? "unknown"} minutes exceeds max age ${maxAgeMinutes}.`
          : "Published snapshot generated_at_utc is missing or invalid.",
        maxAgeMinutes,
        generatedAtUtc,
      );
    }

    return {
      ...baseWithFailures,
      candidateValid: true,
      activationState,
      servingState: "allowed",
      blockingReasonCode: null,
      blockingReasonDetail: null,
      activeRuntimeRunId: activeRuntime.runId,
      activeRuntimeGeneratedAtUtc: activeRuntime.generatedAtUtc,
      snapshotRunId: snapshot.runId,
      quoteRunId: quote.runId,
      freshness: {
        generatedAtUtc,
        generatedAtValid: true,
        snapshotAgeMinutes,
        snapshotMaxAgeMinutes: maxAgeMinutes,
        stale: false,
      },
      latestRunId,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown canonical publication state query error.",
    });
    return resolveBlockedState(
      emptyRefreshRunRow(null, sourcePath, failures),
      null,
      { runId: null, generatedAtUtc: null, error: null },
      snapshot,
      quote,
      "pointer_missing",
      "UNKNOWN_BLOCK",
      error instanceof Error ? error.message : "Unknown canonical publication state query error.",
      maxAgeMinutes,
      null,
    );
  }
}

export function publicationContractFields(state: CanonicalPublicationState): PublicationContractFields {
  return {
    run_id: state.runId,
    generated_at_utc: state.freshness.generatedAtUtc ?? state.generatedAtUtc,
    validation_status: state.validationStatus,
    snapshot_publication_id: state.snapshotPublicationId,
    quote_publication_id: state.quotePublicationId,
    quote_binding_status: state.quoteBindingStatus,
    serving_state: state.servingState,
    activation_state: state.activationState,
    blocking_reason_code: state.blockingReasonCode,
    blocking_reason_detail: state.blockingReasonDetail,
  };
}
