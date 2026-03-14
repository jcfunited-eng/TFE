export type RefreshPhaseLedgerTruthRow = {
  phase_name: string;
  process_status: string;
  output_contract: Record<string, unknown> | null;
  failure_code: string | null;
  failure_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  last_heartbeat_at: string | null;
};

export type PreActivationCriticalTruthAssessment = {
  ok: boolean;
  failureCode: string | null;
  failureDetail: string | null;
  blockingPhaseName: string | null;
  blockingProcessStatus: string | null;
  blockingOutputStatus: string | null;
  phaseSummaries: string[];
};

export const PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES = [
  "snapshot_rebuild",
  "runtime_postgres_sync",
  "validation_gate",
] as const;

type PreActivationCriticalPhaseName = (typeof PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES)[number];

const EXPECTED_OUTPUT_STATUS: Record<PreActivationCriticalPhaseName, string> = {
  snapshot_rebuild: "ok",
  runtime_postgres_sync: "ok",
  validation_gate: "pass",
};

const NON_TERMINAL_PHASE_STATUSES = new Set(["running", "launched", "deferred"]);
const FAILED_PHASE_STATUSES = new Set(["failed", "blocked"]);

function toLowerTextOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim().toLowerCase();
  return text || null;
}

export function phaseOutputStatus(phase: RefreshPhaseLedgerTruthRow | undefined): string | null {
  if (!phase || !phase.output_contract || Array.isArray(phase.output_contract)) {
    return null;
  }
  return toLowerTextOrNull(phase.output_contract.status);
}

export function phaseSummary(phaseName: string, phase: RefreshPhaseLedgerTruthRow | undefined): string {
  if (!phase) return `${phaseName}=missing`;
  return `${phaseName}=${toLowerTextOrNull(phase.process_status) ?? "unknown"}:${phaseOutputStatus(phase) ?? "unknown"}`;
}

export function publicationCriticalPhaseSucceeded(
  phaseName: PreActivationCriticalPhaseName,
  phase: RefreshPhaseLedgerTruthRow | undefined,
): boolean {
  if (!phase) return false;
  if (toLowerTextOrNull(phase.process_status) !== "completed") return false;
  return phaseOutputStatus(phase) === EXPECTED_OUTPUT_STATUS[phaseName];
}

export function assessPreActivationPublicationCriticalTruth(
  phaseRows: RefreshPhaseLedgerTruthRow[],
  contextLabel: string,
): PreActivationCriticalTruthAssessment {
  const phaseByName = new Map(
    phaseRows.map((row) => [String(row.phase_name ?? "").trim(), row] as const),
  );
  const phaseSummaries = PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES.map((phaseName) =>
    phaseSummary(phaseName, phaseByName.get(phaseName)),
  );

  for (const phaseName of PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES) {
    const phase = phaseByName.get(phaseName);
    const processStatus = toLowerTextOrNull(phase?.process_status);
    const outputStatus = phaseOutputStatus(phase);
    const expectedOutputStatus = EXPECTED_OUTPUT_STATUS[phaseName];
    const summaryText = phaseSummaries.join(", ");

    if (!phase) {
      return {
        ok: false,
        failureCode: "PUBLICATION_CRITICAL_PHASE_MISSING_AT_TERMINALIZATION",
        failureDetail:
          `Publication-critical phase truth is incomplete during ${contextLabel}. `
          + `phase='${phaseName}' is missing. phase_summaries=${summaryText}.`,
        blockingPhaseName: phaseName,
        blockingProcessStatus: null,
        blockingOutputStatus: null,
        phaseSummaries,
      };
    }

    if (processStatus && NON_TERMINAL_PHASE_STATUSES.has(processStatus)) {
      return {
        ok: false,
        failureCode: "PUBLICATION_CRITICAL_PHASE_NON_TERMINAL_AT_TERMINALIZATION",
        failureDetail:
          `Publication-critical phase truth is non-terminal during ${contextLabel}. `
          + `phase='${phaseName}' process_status='${processStatus}' output_status='${outputStatus ?? "null"}'. `
          + `phase_summaries=${summaryText}.`,
        blockingPhaseName: phaseName,
        blockingProcessStatus: processStatus,
        blockingOutputStatus: outputStatus,
        phaseSummaries,
      };
    }

    if (processStatus && FAILED_PHASE_STATUSES.has(processStatus)) {
      return {
        ok: false,
        failureCode: phase.failure_code || "PUBLICATION_CRITICAL_PHASE_FAILED_AT_TERMINALIZATION",
        failureDetail:
          `Publication-critical phase truth is failed during ${contextLabel}. `
          + `phase='${phaseName}' process_status='${processStatus}' output_status='${outputStatus ?? "null"}' `
          + `failure_code='${phase.failure_code ?? "null"}' failure_detail='${phase.failure_detail ?? "null"}'. `
          + `phase_summaries=${summaryText}.`,
        blockingPhaseName: phaseName,
        blockingProcessStatus: processStatus,
        blockingOutputStatus: outputStatus,
        phaseSummaries,
      };
    }

    if (processStatus !== "completed" || outputStatus !== expectedOutputStatus) {
      return {
        ok: false,
        failureCode: "PUBLICATION_CRITICAL_PHASE_OUTPUT_NOT_SUCCESS_AT_TERMINALIZATION",
        failureDetail:
          `Publication-critical phase truth is not success-terminal during ${contextLabel}. `
          + `phase='${phaseName}' process_status='${processStatus ?? "null"}' `
          + `output_status='${outputStatus ?? "null"}' expected_output_status='${expectedOutputStatus}'. `
          + `phase_summaries=${summaryText}.`,
        blockingPhaseName: phaseName,
        blockingProcessStatus: processStatus,
        blockingOutputStatus: outputStatus,
        phaseSummaries,
      };
    }
  }

  return {
    ok: true,
    failureCode: null,
    failureDetail: null,
    blockingPhaseName: null,
    blockingProcessStatus: null,
    blockingOutputStatus: null,
    phaseSummaries,
  };
}
