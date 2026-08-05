import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "../workspace-root";
import {
  createDeferredFollowupJobRow,
  createQuoteCacheRefreshPhaseRow,
  nowExecutionTimestampUtc,
  parseStoredStep1PublicationBundleManifest,
  resolveStep1FollowupTicketPath,
  sha256Text,
  stableJsonStringify,
  type Step1FollowupClassification,
  type Step1FollowupStatus,
  type Step1FollowupTicketPersistence,
  type Step1QuoteCacheFollowupTicketArtifact,
} from "./schema";

export type FollowupFailureDirective = {
  code?: "followup_launch_failure" | "state_persistence_failure";
  detail: string;
};

export type QuoteCacheFollowupTicketInput = {
  runId: string;
  publicationManifestPath: string;
  classification: Step1FollowupClassification;
  desiredStatus?: "deferred" | "launched";
  forcedFailure?: FollowupFailureDirective;
};

export type QuoteCacheFollowupTicketResult = {
  ticket: Step1QuoteCacheFollowupTicketArtifact;
  ticketPath: string;
  deferredFollowupJobRow: ReturnType<typeof createDeferredFollowupJobRow>;
  phaseRow: ReturnType<typeof createQuoteCacheRefreshPhaseRow>;
};

export class QuoteCacheFollowupTicketError extends Error {
  code:
    | "followup_ticket_write_failure"
    | "followup_launch_failure"
    | "followup_classification_violation"
    | "state_persistence_failure";
  detail: string;
  runId: string;

  constructor(params: {
    code:
      | "followup_ticket_write_failure"
      | "followup_launch_failure"
      | "followup_classification_violation"
      | "state_persistence_failure";
    detail: string;
    runId: string;
  }) {
    super(
      `Quote follow-up dispatch failed. run_id=${params.runId}; `
      + `publication remains active; follow-up code=${params.code}; detail=${params.detail}.`,
    );
    this.name = "QuoteCacheFollowupTicketError";
    this.code = params.code;
    this.detail = params.detail;
    this.runId = params.runId;
  }
}

type CreateQuoteCacheFollowupTicketOptions = {
  persistence: Step1FollowupTicketPersistence;
  workspaceRoot?: string;
};

function requireText(value: unknown, fieldName: string, runId: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `${fieldName} must be a non-empty string.`,
      runId,
    });
  }
  return text;
}

function requireClassification(value: unknown, runId: string): Step1FollowupClassification {
  const classification = String(value ?? "").trim().toLowerCase();
  if (classification !== "non_critical_follow_up") {
    throw new QuoteCacheFollowupTicketError({
      code: "followup_classification_violation",
      detail: `classification='${classification || "null"}' is not allowed for quote-cache follow-up.`,
      runId,
    });
  }
  return "non_critical_follow_up";
}

function normalizeDesiredStatus(value: unknown): "deferred" | "launched" {
  const status = String(value ?? "").trim().toLowerCase();
  if (status === "launched") return "launched";
  return "deferred";
}

function normalizeForcedFailure(
  value: unknown,
  runId: string,
): FollowupFailureDirective | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const detail = String(record.detail ?? "").trim();
  if (!detail) {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: "forcedFailure.detail must be a non-empty string when provided.",
      runId,
    });
  }
  const code = String(record.code ?? "").trim().toLowerCase();
  if (code && code !== "followup_launch_failure" && code !== "state_persistence_failure") {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `forcedFailure.code='${code}' is not supported.`,
      runId,
    });
  }
  return {
    code: code === "state_persistence_failure" ? "state_persistence_failure" : "followup_launch_failure",
    detail,
  };
}

async function loadPublicationManifest(
  publicationManifestPath: string,
  runId: string,
): Promise<NonNullable<ReturnType<typeof parseStoredStep1PublicationBundleManifest>>> {
  try {
    const raw = await readFile(publicationManifestPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    const manifest = parseStoredStep1PublicationBundleManifest(parsed);
    if (!manifest) {
      throw new Error("publication manifest is invalid.");
    }
    return manifest;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to read publication manifest.";
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `publication_manifest_path read failed: ${detail}`,
      runId,
    });
  }
}

function buildOperatorVisibleStatus(params: {
  status: Step1FollowupStatus;
  publicationBundleId: string;
  failureCode: string | null;
  failureDetail: string | null;
}): string {
  if (params.status === "failed") {
    return `quote_cache_refresh failed; publication_bundle_id=${params.publicationBundleId}; `
      + `failure_code=${params.failureCode ?? "followup_launch_failure"}; `
      + `detail=${params.failureDetail ?? "follow-up launch failed."}`;
  }
  return `quote_cache_refresh ${params.status}; publication_bundle_id=${params.publicationBundleId}; `
    + "publication remains active while follow-up proceeds independently.";
}

function buildTicketArtifact(params: {
  runId: string;
  publicationManifestPath: string;
  publicationBundleId: string;
  targetEnvironment: string;
  classification: Step1FollowupClassification;
  status: Step1FollowupStatus;
  createdAtUtc: string;
  failureCode: string | null;
  failureDetail: string | null;
}): Step1QuoteCacheFollowupTicketArtifact {
  const identity = {
    run_id: params.runId,
    publication_bundle_id: params.publicationBundleId,
    phase_name: "quote_cache_refresh",
    classification: params.classification,
  };
  const digest = sha256Text(stableJsonStringify(identity));
  return {
    followup_job_id: `followup_job_v1_${digest.slice(0, 24)}`,
    triggering_run_id: params.runId,
    publication_bundle_id: params.publicationBundleId,
    target_environment: params.targetEnvironment,
    phase_name: "quote_cache_refresh",
    classification: params.classification,
    status: params.status,
    publication_manifest_path: params.publicationManifestPath,
    operator_visible_status: buildOperatorVisibleStatus({
      status: params.status,
      publicationBundleId: params.publicationBundleId,
      failureCode: params.failureCode,
      failureDetail: params.failureDetail,
    }),
    created_at_utc: params.createdAtUtc,
  };
}

export async function createQuoteCacheFollowupTicket(
  input: QuoteCacheFollowupTicketInput,
  options: CreateQuoteCacheFollowupTicketOptions,
): Promise<QuoteCacheFollowupTicketResult> {
  const runId = requireText(input.runId, "run_id", input.runId || "pending");
  const publicationManifestPath = requireText(input.publicationManifestPath, "publication_manifest_path", runId);
  const classification = requireClassification(input.classification, runId);
  const desiredStatus = normalizeDesiredStatus(input.desiredStatus);
  const forcedFailure = normalizeForcedFailure(input.forcedFailure, runId);
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = options.persistence;

  const publicationManifest = await loadPublicationManifest(publicationManifestPath, runId);
  if (publicationManifest.run_id !== runId) {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `publication_manifest.run_id=${publicationManifest.run_id} does not match input run_id=${runId}.`,
      runId,
    });
  }

  const activePointer = await persistence.readActivePublicationPointer(publicationManifest.target_environment);
  if (!activePointer) {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `active_publication_pointer missing for target_environment=${publicationManifest.target_environment}.`,
      runId,
    });
  }

  if (activePointer.publication_bundle_id !== publicationManifest.publication_bundle_id) {
    throw new QuoteCacheFollowupTicketError({
      code: "state_persistence_failure",
      detail: `active_publication_pointer publication_bundle_id=${activePointer.publication_bundle_id} `
        + `does not match publication_manifest publication_bundle_id=${publicationManifest.publication_bundle_id}.`,
      runId,
    });
  }

  const createdAtUtc = nowExecutionTimestampUtc();
  const failureCode = forcedFailure?.code ?? null;
  const failureDetail = forcedFailure?.detail ?? null;
  const status: Step1FollowupStatus = forcedFailure ? "failed" : desiredStatus;
  const ticket = buildTicketArtifact({
    runId,
    publicationManifestPath,
    publicationBundleId: activePointer.publication_bundle_id,
    targetEnvironment: publicationManifest.target_environment,
    classification,
    status,
    createdAtUtc,
    failureCode,
    failureDetail,
  });
  const ticketPath = resolveStep1FollowupTicketPath(workspaceRoot, runId);
  const deferredFollowupJobRow = createDeferredFollowupJobRow({
    ticket,
    ticketPath,
    failureCode,
    failureDetail,
  });
  const phaseRow = createQuoteCacheRefreshPhaseRow({
    ticket,
    ticketPath,
    failureCode,
    failureDetail,
  });

  try {
    await mkdir(path.dirname(ticketPath), { recursive: true });
    await writeFile(ticketPath, `${JSON.stringify(ticket, null, 2)}\n`, "utf8");
    await persistence.ensureReady();
    await persistence.writeDeferredFollowupJobRow(deferredFollowupJobRow);
    await persistence.writePhaseRow(phaseRow);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to persist follow-up ticket.";
    throw new QuoteCacheFollowupTicketError({
      code: "followup_ticket_write_failure",
      detail,
      runId,
    });
  }

  if (forcedFailure) {
    throw new QuoteCacheFollowupTicketError({
      code: forcedFailure.code ?? "followup_launch_failure",
      detail: forcedFailure.detail,
      runId,
    });
  }

  return {
    ticket,
    ticketPath,
    deferredFollowupJobRow,
    phaseRow,
  };
}
