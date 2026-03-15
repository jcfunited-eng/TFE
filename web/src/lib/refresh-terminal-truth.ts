export type RefreshPhaseLedgerTruthRow = {
  phase_name: string;
  input_contract?: Record<string, unknown> | null;
  process_status: string;
  output_contract: Record<string, unknown> | null;
  failure_code: string | null;
  failure_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  last_heartbeat_at: string | null;
};

export type RunCurrentPhaseMirrorTruth = {
  current_phase: string | null;
  current_phase_process_status: string | null;
  current_phase_started_at: string | null;
  current_phase_completed_at: string | null;
  current_phase_last_heartbeat_at: string | null;
  current_phase_failure_code: string | null;
  current_phase_failure_detail: string | null;
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

export type TerminalFailurePhaseTruthReconciliation = {
  shouldPersist: boolean;
  phaseName: string | null;
  processStatus: string | null;
  startedAtIso: string | null;
  completedAtIso: string | null;
  lastHeartbeatAtIso: string | null;
  inputContract: Record<string, unknown> | null;
  outputContract: Record<string, unknown> | null;
  failureCode: string | null;
  failureDetail: string | null;
  reason: string;
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

function toTextOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

function toLowerTextOrNull(value: unknown): string | null {
  const text = toTextOrNull(value);
  return text ? text.toLowerCase() : null;
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function phaseMomentIso(phase: RefreshPhaseLedgerTruthRow | undefined): string | null {
  if (!phase) return null;
  return phase.last_heartbeat_at ?? phase.started_at ?? phase.completed_at ?? null;
}

function phaseMomentMs(phase: RefreshPhaseLedgerTruthRow | undefined): number {
  const iso = phaseMomentIso(phase);
  if (!iso) return Number.NEGATIVE_INFINITY;
  const parsed = Date.parse(iso);
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
}

function latestNonTerminalPhase(phaseRows: RefreshPhaseLedgerTruthRow[]): RefreshPhaseLedgerTruthRow | undefined {
  let selected: RefreshPhaseLedgerTruthRow | undefined;
  for (const phase of phaseRows) {
    if (!isNonTerminalPhaseProcessStatus(phase.process_status)) {
      continue;
    }
    if (!selected || phaseMomentMs(phase) >= phaseMomentMs(selected)) {
      selected = phase;
    }
  }
  return selected;
}

export function isNonTerminalPhaseProcessStatus(value: unknown): boolean {
  const normalized = toLowerTextOrNull(value);
  return Boolean(normalized && NON_TERMINAL_PHASE_STATUSES.has(normalized));
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
      // If a later critical phase has already completed, this phase's non-terminal
      // status is a stale ledger artifact — the phase-complete write to the ledger
      // failed (e.g. DB connection timeout) but the phase itself succeeded, as
      // proven by later phases completing. Treat it as implicitly completed.
      const phaseIndex = PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES.indexOf(
        phaseName as PreActivationCriticalPhaseName,
      );
      const laterPhaseAlreadyCompleted = PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES
        .slice(phaseIndex + 1)
        .some((laterName) => toLowerTextOrNull(phaseByName.get(laterName)?.process_status) === "completed");
      if (laterPhaseAlreadyCompleted) {
        continue;
      }
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

export function buildTerminalFailurePhaseTruthReconciliation(params: {
  phaseRows: RefreshPhaseLedgerTruthRow[];
  currentPhase: RunCurrentPhaseMirrorTruth;
  completedAtIso: string;
  failureCode: string;
  failureDetail: string;
  contextLabel: string;
}): TerminalFailurePhaseTruthReconciliation {
  const phaseByName = new Map(
    params.phaseRows.map((row) => [String(row.phase_name ?? "").trim(), row] as const),
  );
  const mirrorPhaseName = toTextOrNull(params.currentPhase.current_phase);
  const mirrorPhase = mirrorPhaseName ? phaseByName.get(mirrorPhaseName) : undefined;
  const mirrorProcessStatus = toLowerTextOrNull(params.currentPhase.current_phase_process_status);

  if (mirrorPhaseName && mirrorProcessStatus && NON_TERMINAL_PHASE_STATUSES.has(mirrorProcessStatus)) {
    const targetFailureCode =
      toTextOrNull(mirrorPhase?.failure_code)
      ?? toTextOrNull(params.currentPhase.current_phase_failure_code)
      ?? params.failureCode;
    const targetFailureDetail =
      toTextOrNull(mirrorPhase?.failure_detail)
      ?? toTextOrNull(params.currentPhase.current_phase_failure_detail)
      ?? params.failureDetail;
    const existingOutput = isObjectRecord(mirrorPhase?.output_contract) ? mirrorPhase.output_contract : null;
    return {
      shouldPersist: true,
      phaseName: mirrorPhaseName,
      processStatus: "failed",
      startedAtIso:
        toTextOrNull(mirrorPhase?.started_at)
        ?? toTextOrNull(params.currentPhase.current_phase_started_at)
        ?? params.completedAtIso,
      completedAtIso: params.completedAtIso,
      lastHeartbeatAtIso: params.completedAtIso,
      inputContract: isObjectRecord(mirrorPhase?.input_contract) ? mirrorPhase.input_contract : null,
      outputContract: {
        ...(existingOutput ?? {}),
        status: "error",
        failure_code: targetFailureCode,
        failure_detail: targetFailureDetail,
      },
      failureCode: targetFailureCode,
      failureDetail: targetFailureDetail,
      reason:
        `${params.contextLabel}:run_header_current_phase_was_non_terminal; `
        + `phase='${mirrorPhaseName}' process_status='${mirrorProcessStatus}'.`,
    };
  }

  if (mirrorPhase && isNonTerminalPhaseProcessStatus(mirrorPhase.process_status)) {
    const targetFailureCode = toTextOrNull(mirrorPhase.failure_code) ?? params.failureCode;
    const targetFailureDetail = toTextOrNull(mirrorPhase.failure_detail) ?? params.failureDetail;
    const existingOutput = isObjectRecord(mirrorPhase.output_contract) ? mirrorPhase.output_contract : null;
    return {
      shouldPersist: true,
      phaseName: mirrorPhase.phase_name,
      processStatus: "failed",
      startedAtIso: toTextOrNull(mirrorPhase.started_at) ?? params.completedAtIso,
      completedAtIso: params.completedAtIso,
      lastHeartbeatAtIso: params.completedAtIso,
      inputContract: isObjectRecord(mirrorPhase.input_contract) ? mirrorPhase.input_contract : null,
      outputContract: {
        ...(existingOutput ?? {}),
        status: "error",
        failure_code: targetFailureCode,
        failure_detail: targetFailureDetail,
      },
      failureCode: targetFailureCode,
      failureDetail: targetFailureDetail,
      reason:
        `${params.contextLabel}:ledger_current_phase_was_non_terminal; `
        + `phase='${mirrorPhase.phase_name}' process_status='${toLowerTextOrNull(mirrorPhase.process_status)}'.`,
    };
  }

  const latestRunningPhase = latestNonTerminalPhase(params.phaseRows);
  if (latestRunningPhase) {
    const targetFailureCode = toTextOrNull(latestRunningPhase.failure_code) ?? params.failureCode;
    const targetFailureDetail = toTextOrNull(latestRunningPhase.failure_detail) ?? params.failureDetail;
    const existingOutput = isObjectRecord(latestRunningPhase.output_contract) ? latestRunningPhase.output_contract : null;
    return {
      shouldPersist: true,
      phaseName: latestRunningPhase.phase_name,
      processStatus: "failed",
      startedAtIso: toTextOrNull(latestRunningPhase.started_at) ?? params.completedAtIso,
      completedAtIso: params.completedAtIso,
      lastHeartbeatAtIso: params.completedAtIso,
      inputContract: isObjectRecord(latestRunningPhase.input_contract) ? latestRunningPhase.input_contract : null,
      outputContract: {
        ...(existingOutput ?? {}),
        status: "error",
        failure_code: targetFailureCode,
        failure_detail: targetFailureDetail,
      },
      failureCode: targetFailureCode,
      failureDetail: targetFailureDetail,
      reason:
        `${params.contextLabel}:latest_non_terminal_phase_was_selected; `
        + `phase='${latestRunningPhase.phase_name}' process_status='${toLowerTextOrNull(latestRunningPhase.process_status)}'.`,
    };
  }

  if (mirrorPhaseName && mirrorPhase) {
    const ledgerProcessStatus = toLowerTextOrNull(mirrorPhase.process_status);
    const mirrorFailureCode = toTextOrNull(params.currentPhase.current_phase_failure_code);
    const mirrorFailureDetail = toTextOrNull(params.currentPhase.current_phase_failure_detail);
    const ledgerFailureCode = toTextOrNull(mirrorPhase.failure_code);
    const ledgerFailureDetail = toTextOrNull(mirrorPhase.failure_detail);
    const mirrorMatchesLedger =
      mirrorProcessStatus === ledgerProcessStatus
      && mirrorFailureCode === ledgerFailureCode
      && mirrorFailureDetail === ledgerFailureDetail;

    if (!mirrorMatchesLedger) {
      return {
        shouldPersist: true,
        phaseName: mirrorPhaseName,
        processStatus: ledgerProcessStatus ?? "failed",
        startedAtIso: toTextOrNull(mirrorPhase.started_at) ?? toTextOrNull(params.currentPhase.current_phase_started_at),
        completedAtIso:
          toTextOrNull(mirrorPhase.completed_at)
          ?? toTextOrNull(params.currentPhase.current_phase_completed_at)
          ?? params.completedAtIso,
        lastHeartbeatAtIso:
          toTextOrNull(mirrorPhase.last_heartbeat_at)
          ?? toTextOrNull(params.currentPhase.current_phase_last_heartbeat_at)
          ?? params.completedAtIso,
        inputContract: isObjectRecord(mirrorPhase.input_contract) ? mirrorPhase.input_contract : null,
        outputContract: isObjectRecord(mirrorPhase.output_contract) ? mirrorPhase.output_contract : null,
        failureCode: ledgerFailureCode,
        failureDetail: ledgerFailureDetail,
        reason:
          `${params.contextLabel}:run_header_mirror_did_not_match_terminal_child_phase; `
          + `phase='${mirrorPhaseName}' mirror_process_status='${mirrorProcessStatus ?? "null"}' `
          + `ledger_process_status='${ledgerProcessStatus ?? "null"}'.`,
      };
    }
  }

  return {
    shouldPersist: false,
    phaseName: null,
    processStatus: null,
    startedAtIso: null,
    completedAtIso: null,
    lastHeartbeatAtIso: null,
    inputContract: null,
    outputContract: null,
    failureCode: null,
    failureDetail: null,
    reason: `${params.contextLabel}:no_non_terminal_phase_truth_needed_reconciliation.`,
  };
}
