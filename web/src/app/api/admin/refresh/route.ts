import { spawn, type ChildProcess } from "node:child_process";
import { randomUUID, timingSafeEqual } from "node:crypto";
import { closeSync, openSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { Pool } from "pg";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import {
  loadCanonicalPublicationState,
  loadRuntimeRefreshRunById,
  persistPublicationStateForRun,
  publicationCandidateIsValid,
  setActivePublicationRun as setCanonicalActivePublicationRun,
  type PublicationServingState,
} from "@/lib/publication-state";
import {
  assessPreActivationPublicationCriticalTruth,
  buildTerminalFailurePhaseTruthReconciliation,
  phaseSummary,
  PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES as PUBLICATION_CRITICAL_PHASES,
  publicationCriticalPhaseSucceeded,
} from "@/lib/refresh-terminal-truth";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";
import {
  ADMIN_REFRESH_PERSIST_KEYS,
  appendAdminRefreshHistorySnapshotLine,
  readAdminRefreshPersist,
  writeAdminRefreshPersist,
} from "@/lib/admin-refresh-persist";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

type RefreshMode = "snapshot" | "universe_snapshot";
type RefreshTriggerSource = "manual" | "scheduled" | "program";
type RefreshHistoryPhase = "start" | "start_failed" | "complete";
type RefreshHistoryStatus = "running" | "ok" | "error";

type RefreshReport = {
  generated_at_utc?: string;
  elapsed_seconds?: number;
  rows_written?: number;
  skipped_count?: number;
  status?: string;
  refresh_mode?: string;
};

type RefreshStatusRecord = {
  running: boolean;
  pid?: number;
  run_id?: string;
  requested_mode?: RefreshMode;
  trigger_source?: RefreshTriggerSource;
  requested_by?: string;
  started_at?: string;
  completed_at?: string;
  last_error?: string;
  report_generated_at_utc?: string;
  last_report?: RefreshReport;
  completion_logged_for_run_id?: string;
  activation_state?: string;
  serving_state?: string;
  blocking_reason_code?: string | null;
  blocking_reason_detail?: string | null;
  current_phase?: string;
  current_phase_process_status?: string;
  current_phase_started_at?: string;
  current_phase_completed_at?: string;
  current_phase_last_heartbeat_at?: string;
  current_phase_failure_code?: string | null;
  current_phase_failure_detail?: string | null;
};

type RefreshPhaseLedgerRecord = {
  phase_name: string;
  input_contract: Record<string, unknown> | null;
  process_status: string;
  started_at: string | null;
  completed_at: string | null;
  output_contract: Record<string, unknown> | null;
  failure_code: string | null;
  failure_detail: string | null;
  last_heartbeat_at: string | null;
};

type RefreshChildLifecycle = {
  settled: boolean;
};

type PublicationActivationRow = {
  validationStatus: string | null;
  snapshotPublicationId: string | null;
  quotePublicationId: string | null;
  quoteBindingStatus: string | null;
};

type PublicationActivationScriptResult = {
  ok: boolean;
  exitCode: number | null;
  exitSignal: NodeJS.Signals | null;
  stdoutTail: string;
  stderrTail: string;
  payload: Record<string, unknown> | null;
  error?: string;
};

type PublicationActivationResult = {
  valid: boolean;
  candidateValid: boolean;
  activationState: string;
  servingState: string;
  blockingReasonCode: string | null;
  blockingReasonDetail: string | null;
  attemptedActivation: boolean;
  beforeRow: PublicationActivationRow | null;
  afterRow: PublicationActivationRow | null;
  failureReasons: string[];
  syncResult?: PublicationActivationScriptResult;
  validationResult?: PublicationActivationScriptResult;
};

type CriticalRefreshFailureError = Error & {
  failureCode?: string;
  failureDetail?: string;
};

type TerminalActivationOutcome = {
  completionStatus: RefreshHistoryStatus;
  completionError: string | undefined;
  terminalReportStatus: string;
  activationState: string | undefined;
  servingState: string | undefined;
  blockingReasonCode: string | null | undefined;
  blockingReasonDetail: string | null | undefined;
};

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isRefreshStatusRecord(value: unknown): value is RefreshStatusRecord {
  if (!isObjectRecord(value)) return false;
  return typeof value.running === "boolean";
}

const ROOT_DIR = resolveWorkspaceRoot();
const STATUS_PATH = path.join(ROOT_DIR, "admin_refresh_status.json");
const LOG_PATH = path.join(ROOT_DIR, "admin_refresh_latest.log");
const HISTORY_PATH = path.join(ROOT_DIR, "admin_refresh_history.jsonl");
const REPORT_PATH = path.join(ROOT_DIR, "uf_snapshot_rebuild_report.json");
const ORACLE_MANIFEST_PATH = path.join(ROOT_DIR, "backups", "runtime", "oracle_program", "program_manifest.json");
const ORACLE_TARGET_RETURN_LIFT = 4.0;
const ORACLE_EPOCH_SCHEMA = "v1";
const INTERNAL_TOKEN_HEADER = "x-tfe-internal-refresh-token";
const REFRESH_SCRIPT = "run_refresh_with_l5_learning.py";
const RUNTIME_SYNC_SCRIPT = "web/scripts/sync_runtime_postgres.mjs";
const VALIDATION_GATE_SCRIPT = "web/scripts/run_validation_gate_v1.mjs";
const ACTIVE_REFRESH_CHILDREN = new Map<string, RefreshChildLifecycle>();
const DEFAULT_DB_PORT = 5432;
let runtimeRefreshPool: Pool | null = null;
let runtimeRefreshInitPromise: Promise<void> | null = null;

function nowIso(): string {
  return new Date().toISOString();
}

function isRefreshMode(value: unknown): value is RefreshMode {
  return value === "snapshot" || value === "universe_snapshot";
}

function normalizeRefreshMode(value: unknown): RefreshMode | undefined {
  return isRefreshMode(value) ? value : undefined;
}

function normalizeReportStatus(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim().toLowerCase();
  return normalized || undefined;
}

function isTerminalReportStatus(reportStatus: string | undefined): boolean {
  if (!reportStatus) return false;
  return reportStatus === "ok" || reportStatus === "error" || reportStatus === "no_rows_written";
}

function completionStatusFromReport(
  reportStatus: string | undefined,
): RefreshHistoryStatus {
  if (reportStatus === "ok") return "ok";
  return "error";
}

function completionErrorFromReport(
  reportStatus: string | undefined,
  fallbackError: string | undefined,
): string | undefined {
  if (reportStatus === "ok") return undefined;
  if (reportStatus === "no_rows_written") {
    return "Refresh finished with no rows written. Check report/log.";
  }
  if (reportStatus) {
    return `Refresh finished with report status '${reportStatus}'. Check report/log.`;
  }
  return fallbackError ?? "Refresh finished without a terminal report status. Check report/log.";
}

const NON_CRITICAL_FINALIZATION_FAILURE_CODE = "REFRESH_TERMINAL_REPORT_MISSING_AFTER_CRITICAL_SUCCESS";

async function recoverMissingTerminalReportAfterPublicationCriticalSuccess(params: {
  runId: string;
  exitError: string;
}): Promise<string | null> {
  const phaseRows = await loadRuntimeRefreshPhaseLedger(params.runId);
  if (phaseRows.length === 0) return null;

  const phaseByName = new Map(phaseRows.map((row) => [row.phase_name, row] as const));
  const criticalSuccess = PUBLICATION_CRITICAL_PHASES.every((phaseName) =>
    publicationCriticalPhaseSucceeded(phaseName, phaseByName.get(phaseName)),
  );
  if (!criticalSuccess) return null;

  const criticalSummaries = PUBLICATION_CRITICAL_PHASES.map((phaseName) =>
    phaseSummary(phaseName, phaseByName.get(phaseName)),
  );
  const followupSummary = phaseSummary("quote_cache_refresh", phaseByName.get("quote_cache_refresh"));
  return `${params.exitError} Publication-critical phases already completed in the phase ledger. critical_phases=${criticalSummaries.join(",")}; followup_phase=${followupSummary}.`;
}

async function enforcePreActivationCriticalTruthBeforeTerminalOk(params: {
  runId: string;
  completedAtIso: string;
  contextLabel: string;
}): Promise<{
  ok: boolean;
  failureCode: string | null;
  failureDetail: string | null;
}> {
  const phaseRows = await loadRuntimeRefreshPhaseLedger(params.runId);
  const assessment = assessPreActivationPublicationCriticalTruth(phaseRows, params.contextLabel);
  if (assessment.ok) {
    return {
      ok: true,
      failureCode: null,
      failureDetail: null,
    };
  }

  const failureCode =
    toTextOrNull(assessment.failureCode)
    ?? "PUBLICATION_CRITICAL_PHASE_TERMINAL_TRUTH_FAILED";
  const failureDetail =
    toTextOrNull(assessment.failureDetail)
    ?? "Publication-critical terminal truth could not be verified.";

  const blockingPhase = assessment.blockingPhaseName
    ? phaseRows.find((row) => row.phase_name === assessment.blockingPhaseName)
    : undefined;
  const blockingProcessStatus = toLowerTextOrNull(assessment.blockingProcessStatus);
  if (
    assessment.blockingPhaseName
    && blockingProcessStatus
    && ["running", "launched", "deferred"].includes(blockingProcessStatus)
  ) {
    try {
      const blockingOutputContract = isObjectRecord(blockingPhase?.output_contract)
        ? blockingPhase.output_contract
        : null;
      await upsertRuntimeRefreshPhaseLedger({
        runId: params.runId,
        phaseName: assessment.blockingPhaseName,
        processStatus: "failed",
        inputContract: isObjectRecord(blockingPhase?.input_contract) ? blockingPhase.input_contract : null,
        outputContract: {
          ...(blockingOutputContract ?? {}),
          status: "error",
          failure_code: failureCode,
          failure_detail: failureDetail,
        },
        startedAtIso: blockingPhase?.started_at ?? params.completedAtIso,
        completedAtIso: params.completedAtIso,
        failureCode,
        failureDetail,
        lastHeartbeatAtIso: params.completedAtIso,
      });
    } catch (error) {
      throw createCriticalRefreshFailureError(
        "PUBLICATION_CRITICAL_PHASE_TERMINAL_TRUTH_PERSIST_FAILED",
        error instanceof Error ? error.message : "Unknown phase-ledger terminal-truth persistence failure.",
      );
    }
  }

  try {
    await persistPublicationStateForRun({
      runId: params.runId,
      activationState: "activation_failed",
      servingState: "blocked",
      blockingReasonCode: failureCode,
      blockingReasonDetail: failureDetail,
      failureCode,
      failureDetail,
    });
  } catch (error) {
    throw createCriticalRefreshFailureError(
      "PUBLICATION_CRITICAL_PHASE_TERMINAL_STATE_WRITE_FAILED",
      error instanceof Error ? error.message : "Unknown publication-state terminal-truth persistence failure.",
    );
  }

  return {
    ok: false,
    failureCode,
    failureDetail,
  };
}

async function reconcileActivePhaseTruthForTerminalRunError(params: {
  runId: string;
  baseStatus: RefreshStatusRecord | null;
  completedAtIso: string;
  failureCode: string;
  failureDetail: string;
  contextLabel: string;
}): Promise<void> {
  const phaseRows = await loadRuntimeRefreshPhaseLedger(params.runId);
  const reconciliation = buildTerminalFailurePhaseTruthReconciliation({
    phaseRows,
    currentPhase: {
      current_phase: params.baseStatus?.current_phase ?? null,
      current_phase_process_status: params.baseStatus?.current_phase_process_status ?? null,
      current_phase_started_at: params.baseStatus?.current_phase_started_at ?? null,
      current_phase_completed_at: params.baseStatus?.current_phase_completed_at ?? null,
      current_phase_last_heartbeat_at: params.baseStatus?.current_phase_last_heartbeat_at ?? null,
      current_phase_failure_code: params.baseStatus?.current_phase_failure_code ?? null,
      current_phase_failure_detail: params.baseStatus?.current_phase_failure_detail ?? null,
    },
    completedAtIso: params.completedAtIso,
    failureCode: params.failureCode,
    failureDetail: params.failureDetail,
    contextLabel: params.contextLabel,
  });
  if (!reconciliation.shouldPersist || !reconciliation.phaseName || !reconciliation.processStatus) {
    return;
  }

  try {
    await upsertRuntimeRefreshPhaseLedger({
      runId: params.runId,
      phaseName: reconciliation.phaseName,
      processStatus: reconciliation.processStatus,
      inputContract: reconciliation.inputContract,
      outputContract: reconciliation.outputContract,
      startedAtIso: reconciliation.startedAtIso,
      completedAtIso: reconciliation.completedAtIso,
      failureCode: reconciliation.failureCode,
      failureDetail: reconciliation.failureDetail,
      lastHeartbeatAtIso: reconciliation.lastHeartbeatAtIso,
    });
  } catch (error) {
    throw createCriticalRefreshFailureError(
      "ACTIVE_PHASE_TERMINAL_TRUTH_PERSIST_FAILED",
      error instanceof Error ? error.message : "Unknown active-phase terminal-truth persistence failure.",
    );
  }
}

function reportBelongsToRun(report: RefreshReport | null, startedAtIso: string): boolean {
  const startedAtMs = Date.parse(String(startedAtIso));
  const reportGeneratedMs = Date.parse(String(report?.generated_at_utc ?? ""));
  return Number.isFinite(startedAtMs) && Number.isFinite(reportGeneratedMs) && reportGeneratedMs >= startedAtMs;
}

function formatRefreshExitError(
  exitCode: number | null,
  exitSignal: NodeJS.Signals | null,
  spawnErrorMessage: string | undefined,
): string {
  if (spawnErrorMessage) {
    return spawnErrorMessage;
  }
  const codeText = typeof exitCode === "number" ? String(exitCode) : "unknown";
  const signalText = exitSignal ? ` signal=${exitSignal}` : "";
  return `Refresh process exited before recording a terminal report for this run. exit_code=${codeText}${signalText}`;
}

async function isRefreshProcessAlive(pid: number | undefined): Promise<boolean> {
  if (typeof pid !== "number" || pid <= 0) return false;

  try {
    process.kill(pid, 0);
  } catch {
    return false;
  }

  const scriptPath = REFRESH_SCRIPT;
  const scriptBasename = path.basename(scriptPath);
  const markers = new Set<string>([scriptPath, scriptBasename]);
  if (scriptBasename.endsWith(".py")) {
    markers.add(scriptBasename.slice(0, -3));
  }

  try {
    const raw = await readFile(`/proc/${pid}/cmdline`, "utf-8");
    const cmdline = raw.replace(/\u0000/g, " ").trim();
    if (!cmdline) {
      return false;
    }
    for (const marker of markers) {
      if (marker && cmdline.includes(marker)) {
        return true;
      }
    }
    return false;
  } catch {
    return true;
  }
}

function resolvePythonBin(): string {
  const configured = String(process.env.TFE_PYTHON_BIN ?? "").trim();
  if (configured) return configured;
  return "python3";
}

function isRuntimeDbConfigured(): boolean {
  const host = String(process.env.PGHOST ?? process.env.TFE_DB_HOST ?? "").trim();
  const database = String(process.env.PGDATABASE ?? process.env.TFE_DB_NAME ?? "").trim();
  const user = String(process.env.PGUSER ?? process.env.TFE_DB_USER ?? "").trim();
  const password = String(process.env.PGPASSWORD ?? process.env.TFE_DB_PASSWORD ?? "").trim();
  return Boolean(host && database && user && password);
}

function readRequiredDbEnv(...names: string[]): string {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function readDbPort(): number {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DB_PORT;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

function resolveDbSslRejectUnauthorized(): boolean {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true")
    .trim()
    .toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

function resolveRuntimeRefreshPool(): Pool {
  if (runtimeRefreshPool) return runtimeRefreshPool;

  const host = readRequiredDbEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredDbEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredDbEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredDbEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readDbPort();
  const rejectUnauthorized = resolveDbSslRejectUnauthorized();

  runtimeRefreshPool = new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 4,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-web-refresh-start-contract",
  });

  return runtimeRefreshPool;
}

async function ensureRuntimeRefreshRunsTable(): Promise<void> {
  if (runtimeRefreshInitPromise) {
    await runtimeRefreshInitPromise;
    return;
  }

  const pool = resolveRuntimeRefreshPool();
  runtimeRefreshInitPromise = (async () => {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS runtime_refresh_runs (
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
        is_active_publication BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    await pool.query(`
      ALTER TABLE runtime_refresh_runs
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
      ADD COLUMN IF NOT EXISTS is_active_publication BOOLEAN NOT NULL DEFAULT FALSE
    `);
    await pool.query(`
      CREATE TABLE IF NOT EXISTS runtime_refresh_run_phases (
        run_id TEXT NOT NULL REFERENCES runtime_refresh_runs(run_id) ON DELETE CASCADE,
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
      ON runtime_refresh_run_phases (run_id)
    `);
    await pool.query(`
      CREATE INDEX IF NOT EXISTS idx_runtime_refresh_run_phases_running
      ON runtime_refresh_run_phases (run_id, process_status, last_heartbeat_at DESC)
    `);
    await pool.query(`
      CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_refresh_runs_single_active_publication
      ON runtime_refresh_runs ((1))
      WHERE is_active_publication IS TRUE
    `);
  })();

  try {
    await runtimeRefreshInitPromise;
  } catch (error) {
    runtimeRefreshInitPromise = null;
    throw error;
  }
}

async function upsertRuntimeRefreshRunStartStrict(params: {
  runId: string;
  mode: RefreshMode;
  triggerSource: RefreshTriggerSource;
  requestedBy: string;
  startedAtIso: string;
}): Promise<void> {
  if (!isRuntimeDbConfigured()) {
    throw new Error(
      "Runtime Postgres is not configured; cannot enforce running-status contract for runtime_refresh_runs.",
    );
  }

  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  await pool.query(
    `
      INSERT INTO runtime_refresh_runs (
        run_id, mode, trigger_source, requested_by, started_at, completed_at, report_status, updated_at
      )
      VALUES ($1, $2, $3, $4, $5::timestamptz, NULL, $6, NOW())
      ON CONFLICT (run_id)
      DO UPDATE SET
        mode = EXCLUDED.mode,
        trigger_source = EXCLUDED.trigger_source,
        requested_by = EXCLUDED.requested_by,
        started_at = EXCLUDED.started_at,
        completed_at = NULL,
        report_status = EXCLUDED.report_status,
        updated_at = NOW()
    `,
    [params.runId, params.mode, params.triggerSource, params.requestedBy, params.startedAtIso, "running"],
  );
}

async function upsertRuntimeRefreshRunTerminalStrict(params: {
  runId: string;
  mode: RefreshMode | undefined;
  triggerSource: RefreshTriggerSource | undefined;
  requestedBy: string | undefined;
  startedAtIso: string | undefined;
  completedAtIso: string;
  reportGeneratedAtIso?: string;
  rowsWritten?: number;
  reportStatus?: string;
  optimizerShortCycle?: string;
  optimizerCycleRequestedRuns?: number;
  optimizerCycleCompletedRuns?: number;
  optimizerSessionId?: string;
  optimizerTargetReturnLiftPct?: number;
  optimizerBestScore?: number;
  optimizerTargetMet?: boolean;
  epochLibraryConfidenceSchema?: string;
  epochLibraryStatus?: string;
}): Promise<void> {
  if (!isRuntimeDbConfigured()) {
    throw new Error(
      "Runtime Postgres is not configured; cannot durably persist terminal runtime_refresh_runs state.",
    );
  }

  const normalizedReportStatus =
    typeof params.reportStatus === "string" && params.reportStatus.trim()
      ? params.reportStatus.trim().toLowerCase()
      : "error";

  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  await pool.query(
    `
      INSERT INTO runtime_refresh_runs (
        run_id, mode, trigger_source, requested_by, started_at, completed_at, report_generated_at_utc,
        rows_written, report_status, optimizer_short_cycle, optimizer_cycle_requested_runs, optimizer_cycle_completed_runs,
        optimizer_session_id, optimizer_target_return_lift_pct, optimizer_best_score, optimizer_target_met,
        epoch_library_confidence_schema, epoch_library_status, updated_at
      )
      VALUES (
        $1, $2, $3, $4, $5::timestamptz, $6::timestamptz, $7::timestamptz,
        $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()
      )
      ON CONFLICT (run_id)
      DO UPDATE SET
        mode = COALESCE(EXCLUDED.mode, runtime_refresh_runs.mode),
        trigger_source = COALESCE(EXCLUDED.trigger_source, runtime_refresh_runs.trigger_source),
        requested_by = COALESCE(EXCLUDED.requested_by, runtime_refresh_runs.requested_by),
        started_at = COALESCE(EXCLUDED.started_at, runtime_refresh_runs.started_at),
        completed_at = EXCLUDED.completed_at,
        report_generated_at_utc = COALESCE(EXCLUDED.report_generated_at_utc, runtime_refresh_runs.report_generated_at_utc),
        rows_written = COALESCE(EXCLUDED.rows_written, runtime_refresh_runs.rows_written),
        report_status = COALESCE(EXCLUDED.report_status, runtime_refresh_runs.report_status),
        optimizer_short_cycle = COALESCE(EXCLUDED.optimizer_short_cycle, runtime_refresh_runs.optimizer_short_cycle),
        optimizer_cycle_requested_runs = COALESCE(EXCLUDED.optimizer_cycle_requested_runs, runtime_refresh_runs.optimizer_cycle_requested_runs),
        optimizer_cycle_completed_runs = COALESCE(EXCLUDED.optimizer_cycle_completed_runs, runtime_refresh_runs.optimizer_cycle_completed_runs),
        optimizer_session_id = COALESCE(EXCLUDED.optimizer_session_id, runtime_refresh_runs.optimizer_session_id),
        optimizer_target_return_lift_pct = COALESCE(EXCLUDED.optimizer_target_return_lift_pct, runtime_refresh_runs.optimizer_target_return_lift_pct),
        optimizer_best_score = COALESCE(EXCLUDED.optimizer_best_score, runtime_refresh_runs.optimizer_best_score),
        optimizer_target_met = COALESCE(EXCLUDED.optimizer_target_met, runtime_refresh_runs.optimizer_target_met),
        epoch_library_confidence_schema = COALESCE(EXCLUDED.epoch_library_confidence_schema, runtime_refresh_runs.epoch_library_confidence_schema),
        epoch_library_status = COALESCE(EXCLUDED.epoch_library_status, runtime_refresh_runs.epoch_library_status),
        updated_at = NOW()
    `,
    [
      params.runId,
      params.mode ?? null,
      params.triggerSource ?? null,
      params.requestedBy ?? null,
      params.startedAtIso ?? null,
      params.completedAtIso,
      params.reportGeneratedAtIso ?? null,
      typeof params.rowsWritten === "number" && Number.isFinite(params.rowsWritten) ? params.rowsWritten : null,
      normalizedReportStatus,
      params.optimizerShortCycle ?? null,
      typeof params.optimizerCycleRequestedRuns === "number" && Number.isFinite(params.optimizerCycleRequestedRuns)
        ? params.optimizerCycleRequestedRuns
        : null,
      typeof params.optimizerCycleCompletedRuns === "number" && Number.isFinite(params.optimizerCycleCompletedRuns)
        ? params.optimizerCycleCompletedRuns
        : null,
      params.optimizerSessionId ?? null,
      typeof params.optimizerTargetReturnLiftPct === "number" && Number.isFinite(params.optimizerTargetReturnLiftPct)
        ? params.optimizerTargetReturnLiftPct
        : null,
      typeof params.optimizerBestScore === "number" && Number.isFinite(params.optimizerBestScore)
        ? params.optimizerBestScore
        : null,
      typeof params.optimizerTargetMet === "boolean" ? params.optimizerTargetMet : null,
      params.epochLibraryConfidenceSchema ?? null,
      params.epochLibraryStatus ?? null,
    ],
  );
}

async function upsertRuntimeRefreshPhaseLedger(params: {
  runId: string;
  phaseName: string;
  processStatus: string;
  inputContract?: Record<string, unknown> | null;
  outputContract?: Record<string, unknown> | null;
  startedAtIso?: string | null;
  completedAtIso?: string | null;
  failureCode?: string | null;
  failureDetail?: string | null;
  lastHeartbeatAtIso?: string | null;
}): Promise<void> {
  if (!isRuntimeDbConfigured()) {
    throw new Error("Runtime Postgres is not configured; cannot persist refresh phase ledger state.");
  }

  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  await pool.query(
    `
      INSERT INTO runtime_refresh_run_phases (
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
        NOW()
      )
      ON CONFLICT (run_id, phase_name)
      DO UPDATE SET
        input_contract = COALESCE(EXCLUDED.input_contract, runtime_refresh_run_phases.input_contract),
        process_status = EXCLUDED.process_status,
        started_at = COALESCE(EXCLUDED.started_at, runtime_refresh_run_phases.started_at),
        completed_at = EXCLUDED.completed_at,
        output_contract = COALESCE(EXCLUDED.output_contract, runtime_refresh_run_phases.output_contract),
        failure_code = EXCLUDED.failure_code,
        failure_detail = EXCLUDED.failure_detail,
        last_heartbeat_at = COALESCE(EXCLUDED.last_heartbeat_at, runtime_refresh_run_phases.last_heartbeat_at),
        updated_at = NOW()
    `,
    [
      params.runId,
      params.phaseName,
      params.inputContract ? JSON.stringify(params.inputContract) : null,
      params.processStatus,
      params.startedAtIso ?? null,
      params.completedAtIso ?? null,
      params.outputContract ? JSON.stringify(params.outputContract) : null,
      params.failureCode ?? null,
      params.failureDetail ?? null,
      params.lastHeartbeatAtIso ?? params.startedAtIso ?? null,
    ],
  );

  await pool.query(
    `
      UPDATE runtime_refresh_runs
      SET current_phase = $2,
          current_phase_process_status = $3,
          current_phase_started_at = COALESCE($4::timestamptz, current_phase_started_at),
          current_phase_completed_at = $5::timestamptz,
          current_phase_last_heartbeat_at = COALESCE($6::timestamptz, current_phase_last_heartbeat_at),
          current_phase_failure_code = $7,
          current_phase_failure_detail = $8,
          failure_code = CASE
            WHEN $3 IN ('failed', 'blocked') THEN COALESCE($7, failure_code)
            ELSE failure_code
          END,
          failure_detail = CASE
            WHEN $3 IN ('failed', 'blocked') THEN COALESCE($8, failure_detail)
            ELSE failure_detail
          END,
          updated_at = NOW()
      WHERE run_id = $1
    `,
    [
      params.runId,
      params.phaseName,
      params.processStatus,
      params.startedAtIso ?? null,
      params.completedAtIso ?? null,
      params.lastHeartbeatAtIso ?? params.startedAtIso ?? null,
      params.failureCode ?? null,
      params.failureDetail ?? null,
    ],
  );
}

async function loadRuntimeRefreshPhaseLedger(runId: string): Promise<RefreshPhaseLedgerRecord[]> {
  if (!isRuntimeDbConfigured()) return [];
  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  const result = await pool.query<{
    phase_name: string;
    input_contract: Record<string, unknown> | null;
    process_status: string;
    started_at: Date | null;
    completed_at: Date | null;
    output_contract: Record<string, unknown> | null;
    failure_code: string | null;
    failure_detail: string | null;
    last_heartbeat_at: Date | null;
  }>(
    `
      SELECT
        phase_name,
        input_contract,
        process_status,
        started_at,
        completed_at,
        output_contract,
        failure_code,
        failure_detail,
        last_heartbeat_at
      FROM runtime_refresh_run_phases
      WHERE run_id = $1
      ORDER BY COALESCE(started_at, last_heartbeat_at, completed_at) ASC, phase_name ASC
    `,
    [runId],
  );
  return result.rows.map((row) => ({
    phase_name: row.phase_name,
    input_contract: isObjectRecord(row.input_contract) ? row.input_contract : null,
    process_status: row.process_status,
    started_at: row.started_at instanceof Date ? row.started_at.toISOString() : null,
    completed_at: row.completed_at instanceof Date ? row.completed_at.toISOString() : null,
    output_contract: isObjectRecord(row.output_contract) ? row.output_contract : null,
    failure_code: toTextOrNull(row.failure_code),
    failure_detail: toTextOrNull(row.failure_detail),
    last_heartbeat_at: row.last_heartbeat_at instanceof Date ? row.last_heartbeat_at.toISOString() : null,
  }));
}

async function readStatusRecordFromRuntimeDb(): Promise<RefreshStatusRecord | null> {
  if (!isRuntimeDbConfigured()) return null;
  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  const result = await pool.query<{
    run_id: string;
    mode: string | null;
    trigger_source: string | null;
    requested_by: string | null;
    started_at: Date | null;
    completed_at: Date | null;
    report_generated_at_utc: Date | null;
    report_status: string | null;
    activation_state: string | null;
    serving_state: string | null;
    blocking_reason_code: string | null;
    blocking_reason_detail: string | null;
    failure_code: string | null;
    failure_detail: string | null;
    current_phase: string | null;
    current_phase_process_status: string | null;
    current_phase_started_at: Date | null;
    current_phase_completed_at: Date | null;
    current_phase_last_heartbeat_at: Date | null;
    current_phase_failure_code: string | null;
    current_phase_failure_detail: string | null;
  }>(
    `
      SELECT
        run_id,
        mode,
        trigger_source,
        requested_by,
        started_at,
        completed_at,
        report_generated_at_utc,
        report_status,
        activation_state,
        serving_state,
        blocking_reason_code,
        blocking_reason_detail,
        failure_code,
        failure_detail,
        current_phase,
        current_phase_process_status,
        current_phase_started_at,
        current_phase_completed_at,
        current_phase_last_heartbeat_at,
        current_phase_failure_code,
        current_phase_failure_detail
      FROM runtime_refresh_runs
      ORDER BY COALESCE(started_at, created_at) DESC, created_at DESC
      LIMIT 1
    `,
  );
  const row = result.rows[0];
  if (!row) return null;
  const reportStatus = normalizeReportStatus(row.report_status);
  return {
    running: !row.completed_at && reportStatus === "running",
    run_id: row.run_id,
    requested_mode: normalizeRefreshMode(row.mode),
    trigger_source: (row.trigger_source as RefreshTriggerSource | null) ?? undefined,
    requested_by: toTextOrNull(row.requested_by) ?? undefined,
    started_at: row.started_at instanceof Date ? row.started_at.toISOString() : undefined,
    completed_at: row.completed_at instanceof Date ? row.completed_at.toISOString() : undefined,
    report_generated_at_utc: row.report_generated_at_utc instanceof Date ? row.report_generated_at_utc.toISOString() : undefined,
    last_error: toTextOrNull(row.failure_detail) ?? toTextOrNull(row.blocking_reason_detail) ?? undefined,
    activation_state: toTextOrNull(row.activation_state) ?? undefined,
    serving_state: toTextOrNull(row.serving_state) ?? undefined,
    blocking_reason_code: toTextOrNull(row.blocking_reason_code),
    blocking_reason_detail: toTextOrNull(row.blocking_reason_detail),
    current_phase: toTextOrNull(row.current_phase) ?? undefined,
    current_phase_process_status: toTextOrNull(row.current_phase_process_status) ?? undefined,
    current_phase_started_at: row.current_phase_started_at instanceof Date ? row.current_phase_started_at.toISOString() : undefined,
    current_phase_completed_at: row.current_phase_completed_at instanceof Date ? row.current_phase_completed_at.toISOString() : undefined,
    current_phase_last_heartbeat_at: row.current_phase_last_heartbeat_at instanceof Date ? row.current_phase_last_heartbeat_at.toISOString() : undefined,
    current_phase_failure_code: toTextOrNull(row.current_phase_failure_code),
    current_phase_failure_detail: toTextOrNull(row.current_phase_failure_detail),
  };
}

function toTextOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function toLowerTextOrNull(value: unknown): string | null {
  const text = toTextOrNull(value);
  return text ? text.toLowerCase() : null;
}

function publicationActivationRowIsValid(row: PublicationActivationRow | null): boolean {
  if (!row) return false;
  if (row.validationStatus !== "pass") return false;
  if (!row.snapshotPublicationId) return false;
  if (!row.quotePublicationId) return false;
  if (row.quoteBindingStatus !== "aligned") return false;
  return true;
}

function publicationActivationFailureReasons(row: PublicationActivationRow | null): string[] {
  if (!row) return ["runtime_refresh_run_missing"];
  const reasons: string[] = [];
  if (row.validationStatus !== "pass") reasons.push("validation_status_not_pass");
  if (!row.snapshotPublicationId || !row.quotePublicationId) reasons.push("missing_publication_ids");
  if (row.quoteBindingStatus !== "aligned") reasons.push("quote_binding_not_aligned");
  return reasons;
}

function appendTailLines(buffer: string[], chunk: string, maxLines = 40): void {
  const lines = chunk.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trimEnd();
    if (!trimmed) continue;
    buffer.push(trimmed);
    if (buffer.length > maxLines) {
      buffer.shift();
    }
  }
}

function extractJsonObject(text: string): Record<string, unknown> | null {
  const raw = String(text ?? "").trim();
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return isObjectRecord(parsed) ? parsed : null;
  } catch {
    // Fall through to best-effort object extraction.
  }

  const firstBrace = raw.indexOf("{");
  const lastBrace = raw.lastIndexOf("}");
  if (firstBrace < 0 || lastBrace < firstBrace) return null;

  try {
    const parsed = JSON.parse(raw.slice(firstBrace, lastBrace + 1));
    return isObjectRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

async function runNodeScriptForPublicationActivation(
  scriptPath: string,
  envOverrides: Record<string, string>,
): Promise<PublicationActivationScriptResult> {
  return await new Promise<PublicationActivationScriptResult>((resolve) => {
    const stdoutLines: string[] = [];
    const stderrLines: string[] = [];
    const child = spawn("node", [scriptPath], {
      cwd: ROOT_DIR,
      env: {
        ...process.env,
        ...envOverrides,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });

    child.stdout?.setEncoding("utf-8");
    child.stderr?.setEncoding("utf-8");

    child.stdout?.on("data", (chunk: string | Buffer) => {
      appendTailLines(stdoutLines, String(chunk ?? ""));
    });
    child.stderr?.on("data", (chunk: string | Buffer) => {
      appendTailLines(stderrLines, String(chunk ?? ""));
    });

    child.once("error", (error) => {
      resolve({
        ok: false,
        exitCode: null,
        exitSignal: null,
        stdoutTail: stdoutLines.join("\n"),
        stderrTail: stderrLines.join("\n"),
        payload: null,
        error: `spawn_error:${error.message}`,
      });
    });

    child.once("close", (code, signal) => {
      const stdoutTail = stdoutLines.join("\n");
      const stderrTail = stderrLines.join("\n");
      const payload = extractJsonObject(stdoutTail);
      const exitCode = typeof code === "number" ? code : null;
      resolve({
        ok: exitCode === 0,
        exitCode,
        exitSignal: signal ?? null,
        stdoutTail,
        stderrTail,
        payload,
      });
    });
  });
}

async function readPublicationActivationRow(runId: string): Promise<PublicationActivationRow | null> {
  if (!isRuntimeDbConfigured()) return null;
  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  const result = await pool.query<{
    validation_status: string | null;
    snapshot_publication_id: string | null;
    quote_publication_id: string | null;
    quote_binding_status: string | null;
  }>(
    `
      SELECT
        NULLIF(LOWER(TRIM(COALESCE(validation_status, ''))), '') AS validation_status,
        NULLIF(TRIM(COALESCE(snapshot_publication_id, '')), '') AS snapshot_publication_id,
        NULLIF(TRIM(COALESCE(quote_publication_id, '')), '') AS quote_publication_id,
        NULLIF(LOWER(TRIM(COALESCE(quote_binding_status, ''))), '') AS quote_binding_status
      FROM runtime_refresh_runs
      WHERE run_id = $1
      LIMIT 1
    `,
    [runId],
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    validationStatus: toLowerTextOrNull(row.validation_status),
    snapshotPublicationId: toTextOrNull(row.snapshot_publication_id),
    quotePublicationId: toTextOrNull(row.quote_publication_id),
    quoteBindingStatus: toLowerTextOrNull(row.quote_binding_status),
  };
}

async function setActivePublicationRun(runId: string): Promise<boolean> {
  if (!isRuntimeDbConfigured()) return false;
  await ensureRuntimeRefreshRunsTable();
  const pool = resolveRuntimeRefreshPool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");
    const result = await client.query(
      `
        UPDATE runtime_refresh_runs
        SET is_active_publication = CASE WHEN run_id = $1 THEN TRUE ELSE FALSE END,
            updated_at = NOW()
        WHERE is_active_publication IS TRUE OR run_id = $1
      `,
      [runId],
    );
    await client.query("COMMIT");
    return Number(result.rowCount ?? 0) > 0;
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch {
      // Ignore rollback failures.
    }
    throw error;
  } finally {
    client.release();
  }
}

function resolveActivationRefreshMode(report: RefreshReport | null, requestedMode: RefreshMode | undefined): string {
  const fromReport = toTextOrNull(report?.refresh_mode);
  if (fromReport) return fromReport;
  if (requestedMode === "snapshot") {
    return "targeted_pfsc";
  }
  if (requestedMode === "universe_snapshot") {
    return "full_universe";
  }
  return "full_universe";
}

function buildPublicationActivationFailureMessage(result: PublicationActivationResult): string {
  const reasons = result.failureReasons.length > 0 ? result.failureReasons.join(",") : "unknown";
  const syncExit = result.syncResult ? `${result.syncResult.exitCode ?? "null"}` : "not_run";
  const validationExit = result.validationResult ? `${result.validationResult.exitCode ?? "null"}` : "not_run";
  return `Candidate publish completed but serving is ${result.servingState}. activation_state=${result.activationState}; blocking_reason_code=${result.blockingReasonCode ?? "null"}; blocking_reason_detail=${result.blockingReasonDetail ?? "null"}; reasons=${reasons}; sync_exit=${syncExit}; validation_exit=${validationExit}`;
}

function createCriticalRefreshFailureError(failureCode: string, failureDetail: string): CriticalRefreshFailureError {
  const error = new Error(`${failureCode}: ${failureDetail}`) as CriticalRefreshFailureError;
  error.failureCode = failureCode;
  error.failureDetail = failureDetail;
  return error;
}

function extractCriticalRefreshFailure(
  error: unknown,
  fallbackCode: string,
): { failureCode: string; failureDetail: string } {
  const failureCode = String(
    (error as CriticalRefreshFailureError | undefined)?.failureCode ?? fallbackCode,
  ).trim() || fallbackCode;
  const failureDetail = String(
    (error as CriticalRefreshFailureError | undefined)?.failureDetail
      ?? (error instanceof Error ? error.message : "Unknown critical refresh failure."),
  ).trim() || "Unknown critical refresh failure.";
  return { failureCode, failureDetail };
}

async function recordCriticalRefreshFailure(params: {
  runId?: string;
  mode?: RefreshMode;
  source?: RefreshTriggerSource;
  requestedBy?: string;
  startedAtIso?: string;
  completedAtIso?: string;
  baseStatus?: RefreshStatusRecord | null;
  failureCode: string;
  failureDetail: string;
}): Promise<RefreshStatusRecord> {
  const completedAtIso = params.completedAtIso ?? nowIso();
  const base = params.baseStatus ?? null;
  const runId = String(params.runId ?? base?.run_id ?? "").trim() || undefined;
  const nextStatus: RefreshStatusRecord = {
    ...(base ?? { running: false }),
    running: false,
    run_id: runId,
    requested_mode: params.mode ?? normalizeRefreshMode(base?.requested_mode),
    trigger_source: params.source ?? base?.trigger_source,
    requested_by: params.requestedBy ?? base?.requested_by,
    started_at: params.startedAtIso ?? base?.started_at,
    completed_at: completedAtIso,
    last_error: `${params.failureCode}: ${params.failureDetail}`,
    completion_logged_for_run_id: runId ?? base?.completion_logged_for_run_id,
    activation_state: "activation_failed",
    serving_state: "blocked",
    blocking_reason_code: params.failureCode,
    blocking_reason_detail: params.failureDetail,
  };

  const historyEntry = {
    event: "refresh_critical_failure",
    phase: "critical_failure",
    run_id: runId ?? null,
    mode: nextStatus.requested_mode,
    trigger_source: nextStatus.trigger_source,
    requested_by: nextStatus.requested_by,
    started_at: nextStatus.started_at,
    completed_at: completedAtIso,
    failure_code: params.failureCode,
    failure_detail: params.failureDetail,
    status: "error",
    logged_at_utc: nowIso(),
  };

  try {
    await writeFile(STATUS_PATH, JSON.stringify(nextStatus, null, 2), "utf-8");
  } catch (statusError) {
    console.error("refresh_critical_failure_status_write_failed", statusError);
  }

  try {
    await writeAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.statusRecord, {
      status: nextStatus,
      updated_at_utc: nowIso(),
    });
  } catch (persistError) {
    console.error("refresh_critical_failure_status_persist_failed", persistError);
  }

  try {
    await writeFile(HISTORY_PATH, `${JSON.stringify(historyEntry)}\n`, { encoding: "utf-8", flag: "a" });
  } catch (historyError) {
    console.error("refresh_critical_failure_history_write_failed", historyError);
  }

  try {
    await appendAdminRefreshHistorySnapshotLine(historyEntry, HISTORY_PATH);
  } catch (historyPersistError) {
    console.error("refresh_critical_failure_history_persist_failed", historyPersistError);
  }

  if (runId) {
    try {
      await reconcileActivePhaseTruthForTerminalRunError({
        runId,
        baseStatus: nextStatus,
        completedAtIso,
        failureCode: params.failureCode,
        failureDetail: params.failureDetail,
        contextLabel: "record_critical_refresh_failure",
      });
    } catch (phaseTruthError) {
      console.error("refresh_critical_failure_phase_truth_write_failed", phaseTruthError);
    }

    try {
      await persistPublicationStateForRun({
        runId,
        activationState: "activation_failed",
        servingState: "blocked",
        blockingReasonCode: params.failureCode,
        blockingReasonDetail: params.failureDetail,
        failureCode: params.failureCode,
        failureDetail: params.failureDetail,
      });
    } catch (publicationStateError) {
      console.error("refresh_critical_failure_publication_state_write_failed", publicationStateError);
    }
  }

  return nextStatus;
}

async function evaluateTerminalActivation(params: {
  runId: string | undefined;
  requestedMode: RefreshMode | undefined;
  triggerSource: RefreshTriggerSource | undefined;
  requestedBy: string | undefined;
  startedAtIso: string | undefined;
  completedAtIso: string;
  report: RefreshReport | null;
  baseStatus: RefreshStatusRecord | null;
}): Promise<TerminalActivationOutcome> {
  const base = params.baseStatus;
  const publicationActivationInput: Record<string, unknown> = {
    requested_mode: params.requestedMode ?? null,
    trigger_source: params.triggerSource ?? null,
    requested_by: params.requestedBy ?? null,
    refresh_started_at: params.startedAtIso ?? null,
    refresh_completed_at: params.completedAtIso,
    refresh_report_status: params.report?.status ?? null,
    refresh_report_generated_at_utc: params.report?.generated_at_utc ?? null,
  };
  const publicationActivationStartedAtIso = nowIso();

  if (!params.runId) {
    return {
      completionStatus: "error",
      completionError: "Refresh reported ok but run_id is missing; publication activation contract cannot be verified.",
      terminalReportStatus: "error",
      activationState: "activation_failed",
      servingState: "blocked",
      blockingReasonCode: "RUN_ID_MISSING",
      blockingReasonDetail: "Refresh reported ok but run_id is missing; publication activation contract cannot be verified.",
    };
  }

  let activationResult: PublicationActivationResult;
  try {
    await upsertRuntimeRefreshPhaseLedger({
      runId: params.runId,
      phaseName: "publication_activation",
      processStatus: "running",
      inputContract: publicationActivationInput,
      startedAtIso: publicationActivationStartedAtIso,
      lastHeartbeatAtIso: publicationActivationStartedAtIso,
    });
    activationResult = await enforcePublicationActivationContract({
      runId: params.runId,
      requestedMode: params.requestedMode,
      triggerSource: params.triggerSource,
      requestedBy: params.requestedBy,
      startedAtIso: params.startedAtIso,
      completedAtIso: params.completedAtIso,
      report: params.report,
    });
  } catch (error) {
    await upsertRuntimeRefreshPhaseLedger({
      runId: params.runId,
      phaseName: "publication_activation",
      processStatus: "failed",
      inputContract: publicationActivationInput,
      outputContract: {
        status: "error",
      },
      startedAtIso: publicationActivationStartedAtIso,
      completedAtIso: nowIso(),
      failureCode: "PUBLICATION_ACTIVATION_CONTRACT_FAILED",
      failureDetail: error instanceof Error ? error.message : "Unknown publication activation contract failure.",
      lastHeartbeatAtIso: nowIso(),
    });
    throw createCriticalRefreshFailureError(
      "PUBLICATION_ACTIVATION_CONTRACT_FAILED",
      error instanceof Error ? error.message : "Unknown publication activation contract failure.",
    );
  }

  const outcome: TerminalActivationOutcome = {
    completionStatus: "ok",
    completionError: undefined,
    terminalReportStatus: "ok",
    activationState: activationResult.activationState,
    servingState: activationResult.servingState,
    blockingReasonCode: activationResult.blockingReasonCode,
    blockingReasonDetail: activationResult.blockingReasonDetail,
  };

  if (!activationResult.candidateValid) {
    await upsertRuntimeRefreshPhaseLedger({
      runId: params.runId,
      phaseName: "publication_activation",
      processStatus: "failed",
      inputContract: publicationActivationInput,
      outputContract: {
        candidate_valid: activationResult.candidateValid,
        activation_state: activationResult.activationState,
        serving_state: activationResult.servingState,
        blocking_reason_code: activationResult.blockingReasonCode,
        blocking_reason_detail: activationResult.blockingReasonDetail,
        failure_reasons: activationResult.failureReasons,
      },
      startedAtIso: publicationActivationStartedAtIso,
      completedAtIso: params.completedAtIso,
      failureCode: activationResult.blockingReasonCode ?? "publication_candidate_invalid",
      failureDetail: activationResult.blockingReasonDetail ?? buildPublicationActivationFailureMessage(activationResult),
      lastHeartbeatAtIso: params.completedAtIso,
    });
    return {
      ...outcome,
      completionStatus: "error",
      completionError: buildPublicationActivationFailureMessage(activationResult),
      terminalReportStatus: "error",
    };
  }

  if (activationResult.servingState === "blocked") {
    await upsertRuntimeRefreshPhaseLedger({
      runId: params.runId,
      phaseName: "publication_activation",
      processStatus: "blocked",
      inputContract: publicationActivationInput,
      outputContract: {
        candidate_valid: activationResult.candidateValid,
        activation_state: activationResult.activationState,
        serving_state: activationResult.servingState,
        blocking_reason_code: activationResult.blockingReasonCode,
        blocking_reason_detail: activationResult.blockingReasonDetail,
        failure_reasons: activationResult.failureReasons,
      },
      startedAtIso: publicationActivationStartedAtIso,
      completedAtIso: params.completedAtIso,
      failureCode: activationResult.blockingReasonCode,
      failureDetail: activationResult.blockingReasonDetail ?? buildPublicationActivationFailureMessage(activationResult),
      lastHeartbeatAtIso: params.completedAtIso,
    });
    return {
      ...outcome,
      completionError: buildPublicationActivationFailureMessage(activationResult),
    };
  }

  await upsertRuntimeRefreshPhaseLedger({
    runId: params.runId,
    phaseName: "publication_activation",
    processStatus: "completed",
    inputContract: publicationActivationInput,
    outputContract: {
      candidate_valid: activationResult.candidateValid,
      activation_state: activationResult.activationState,
      serving_state: activationResult.servingState,
      blocking_reason_code: activationResult.blockingReasonCode,
      blocking_reason_detail: activationResult.blockingReasonDetail,
      failure_reasons: activationResult.failureReasons,
    },
    startedAtIso: publicationActivationStartedAtIso,
    completedAtIso: params.completedAtIso,
    lastHeartbeatAtIso: params.completedAtIso,
  });

  return {
    ...outcome,
    activationState: activationResult.activationState ?? base?.activation_state,
    servingState: activationResult.servingState ?? base?.serving_state,
    blockingReasonCode: activationResult.blockingReasonCode ?? base?.blocking_reason_code ?? null,
    blockingReasonDetail: activationResult.blockingReasonDetail ?? base?.blocking_reason_detail ?? null,
  };
}

async function enforcePublicationActivationContract(params: {
  runId: string;
  requestedMode: RefreshMode | undefined;
  triggerSource: RefreshTriggerSource | undefined;
  requestedBy: string | undefined;
  startedAtIso: string | undefined;
  completedAtIso: string;
  report: RefreshReport | null;
}): Promise<PublicationActivationResult> {
  if (!isRuntimeDbConfigured()) {
    return {
      valid: false,
      candidateValid: false,
      activationState: "pointer_missing",
      servingState: "blocked",
      blockingReasonCode: "POSTGRES_NOT_CONFIGURED",
      blockingReasonDetail: "Runtime Postgres is not configured; publication state cannot be evaluated.",
      attemptedActivation: false,
      beforeRow: null,
      afterRow: null,
      failureReasons: ["POSTGRES_NOT_CONFIGURED"],
    };
  }

  const beforeRow = await readPublicationActivationRow(params.runId);
  const envOverrides: Record<string, string> = {
    TFE_REFRESH_RUN_ID: params.runId,
    TFE_REFRESH_REQUESTED_MODE: resolveActivationRefreshMode(params.report, params.requestedMode),
    TFE_REFRESH_TRIGGER_SOURCE: String(params.triggerSource ?? ""),
    TFE_REFRESH_REQUESTED_BY: String(params.requestedBy ?? ""),
    TFE_REFRESH_STARTED_AT: String(params.startedAtIso ?? params.completedAtIso),
    TFE_REFRESH_COMPLETED_AT: String(params.completedAtIso),
    TFE_ALLOW_DEFERRED_QUOTE_CACHE_FALLBACK: "1",
  };

  const syncResult = await runNodeScriptForPublicationActivation(RUNTIME_SYNC_SCRIPT, envOverrides);
  const validationResult = syncResult.ok
    ? await runNodeScriptForPublicationActivation(VALIDATION_GATE_SCRIPT, envOverrides)
    : undefined;

  const afterRow = await readPublicationActivationRow(params.runId);
  const afterRefreshRow = await loadRuntimeRefreshRunById(params.runId);
  const candidateValid = publicationCandidateIsValid(afterRefreshRow);
  const reasons = publicationActivationFailureReasons(afterRow);
  if (!syncResult.ok) reasons.push("runtime_sync_failed");
  if (validationResult && !validationResult.ok) reasons.push("validation_gate_failed");

  if (!candidateValid) {
    const blockingReasonCode = afterRefreshRow.validationStatus !== "pass"
      ? "validation_status_not_pass"
      : !afterRefreshRow.snapshotPublicationId || !afterRefreshRow.quotePublicationId
        ? "missing_publication_ids"
        : afterRefreshRow.quoteBindingStatus !== "aligned"
          ? "quote_binding_not_aligned"
          : "candidate_publish_invalid";
    const blockingReasonDetail =
      afterRefreshRow.validationStatus !== "pass"
        ? `validation_status='${afterRefreshRow.validationStatus ?? "null"}'`
        : !afterRefreshRow.snapshotPublicationId || !afterRefreshRow.quotePublicationId
          ? "snapshot_publication_id or quote_publication_id is missing"
          : afterRefreshRow.quoteBindingStatus !== "aligned"
            ? `quote_binding_status='${afterRefreshRow.quoteBindingStatus ?? "null"}'`
            : "Candidate publication row is invalid.";

    await persistPublicationStateForRun({
      runId: params.runId,
      activationState: "pointer_invalid",
      servingState: "blocked",
      blockingReasonCode,
      blockingReasonDetail,
      failureCode: blockingReasonCode,
      failureDetail: blockingReasonDetail,
    });

    return {
      valid: false,
      candidateValid: false,
      activationState: "pointer_invalid",
      servingState: "blocked",
      blockingReasonCode,
      blockingReasonDetail,
      attemptedActivation: true,
      beforeRow,
      afterRow,
      failureReasons: Array.from(new Set(reasons)),
      syncResult,
      validationResult,
    };
  }

  let activationState = "activated";
  let servingState: PublicationServingState = "blocked";
  let blockingReasonCode: string | null = null;
  let blockingReasonDetail: string | null = null;

  try {
    const activePointerUpdated = await setCanonicalActivePublicationRun(params.runId);
    if (!activePointerUpdated) {
      activationState = "activation_failed";
      blockingReasonCode = "active_publication_pointer_update_failed";
      blockingReasonDetail = "Candidate publish is valid, but the active publication pointer was not updated.";
      reasons.push("active_publication_pointer_update_failed");
    }
  } catch (error) {
    activationState = "activation_failed";
    blockingReasonCode = "active_publication_pointer_update_failed";
    blockingReasonDetail = error instanceof Error
      ? error.message
      : "Candidate publish is valid, but the active publication pointer update threw an error.";
    reasons.push("active_publication_pointer_update_failed");
  }

  if (activationState === "activated") {
    const publicationState = await loadCanonicalPublicationState({
      snapshot: {
        available: true,
        runId: params.runId,
        generatedAtUtc: afterRefreshRow.generatedAtUtc,
      },
      quote: {
        available: true,
        runId: params.runId,
      },
    });
    activationState = publicationState.activationState;
    servingState = publicationState.servingState;
    blockingReasonCode = publicationState.blockingReasonCode;
    blockingReasonDetail = publicationState.blockingReasonDetail;
  }

  await persistPublicationStateForRun({
    runId: params.runId,
    activationState: activationState === "activated" ? "activated" : "activation_failed",
    servingState,
    blockingReasonCode,
    blockingReasonDetail,
    failureCode: blockingReasonCode,
    failureDetail: blockingReasonDetail,
  });

  return {
    valid: candidateValid,
    candidateValid,
    activationState: activationState === "activated" ? "activated" : "activation_failed",
    servingState,
    blockingReasonCode,
    blockingReasonDetail,
    attemptedActivation: true,
    beforeRow,
    afterRow,
    failureReasons: Array.from(new Set(reasons)),
    syncResult,
    validationResult,
  };
}

function hasValidInternalToken(request: Request): boolean {
  const expected = String(process.env.TFE_INTERNAL_REFRESH_TOKEN ?? "");
  if (!expected) return false;

  const provided = String(request.headers.get(INTERNAL_TOKEN_HEADER) ?? "");
  if (!provided) return false;

  const expectedBytes = Buffer.from(expected, "utf-8");
  const providedBytes = Buffer.from(provided, "utf-8");

  if (expectedBytes.length !== providedBytes.length) return false;

  return timingSafeEqual(expectedBytes, providedBytes);
}

function normalizeUserAgent(value: string | null): string {
  return String(value ?? "").trim().toLowerCase();
}

function resolveTriggerSource(internalAuthorized: boolean, request: Request): RefreshTriggerSource {
  if (!internalAuthorized) return "manual";

  const userAgent = normalizeUserAgent(request.headers.get("user-agent"));
  if (userAgent.includes("eventbridge")) return "scheduled";
  return "program";
}

async function appendHistoryEntry(entry: Record<string, unknown>): Promise<void> {
  const payload = { ...entry, logged_at_utc: nowIso() };
  try {
    await writeFile(HISTORY_PATH, `${JSON.stringify(payload)}\n`, { encoding: "utf-8", flag: "a" });
  } catch {
    // History logging must not block refresh operations.
  }
  try {
    await appendAdminRefreshHistorySnapshotLine(payload, HISTORY_PATH);
  } catch {
    // Persistence must not block refresh operations.
  }
}

async function writeStartHistoryEntry(
  phase: RefreshHistoryPhase,
  runId: string,
  mode: RefreshMode,
  source: RefreshTriggerSource,
  requestedBy: string,
  details?: { pid?: number; error?: string },
): Promise<void> {
  await appendHistoryEntry({
    event: "refresh_update",
    phase,
    run_id: runId,
    mode,
    trigger_source: source,
    requested_by: requestedBy,
    pid: details?.pid,
    status: phase === "start" ? "running" : "error",
    error: details?.error,
  });
}

async function writeCompletionHistoryEntry(
  runId: string,
  mode: RefreshMode | undefined,
  source: RefreshTriggerSource | undefined,
  requestedBy: string | undefined,
  status: RefreshHistoryStatus,
  details?: {
    rowsWritten?: number;
    elapsedSeconds?: number;
    refreshReportStatus?: string;
    optimizerShortCycle?: string;
    optimizerCycleRequestedRuns?: number;
    optimizerCycleCompletedRuns?: number;
    optimizerSessionId?: string;
    optimizerTargetReturnLiftPct?: number;
    optimizerBestScore?: number;
    optimizerTargetMet?: boolean;
    epochLibraryConfidenceSchema?: string;
    epochLibraryStatus?: string;
    error?: string;
  },
): Promise<void> {
  await appendHistoryEntry({
    event: "refresh_update",
    phase: "complete",
    run_id: runId,
    mode,
    trigger_source: source,
    requested_by: requestedBy,
    status,
    rows_written: details?.rowsWritten,
    elapsed_seconds: details?.elapsedSeconds,
    refresh_report_status: details?.refreshReportStatus,
    optimizer_short_cycle: details?.optimizerShortCycle,
    optimizer_cycle_requested_runs: details?.optimizerCycleRequestedRuns,
    optimizer_cycle_completed_runs: details?.optimizerCycleCompletedRuns,
    optimizer_session_id: details?.optimizerSessionId,
    optimizer_target_return_lift_pct: details?.optimizerTargetReturnLiftPct,
    optimizer_best_score: details?.optimizerBestScore,
    optimizer_target_met: details?.optimizerTargetMet,
    epoch_library_confidence_schema: details?.epochLibraryConfidenceSchema,
    epoch_library_status: details?.epochLibraryStatus,
    error: details?.error,
  });
}

async function readStatusRecord(): Promise<RefreshStatusRecord | null> {
  try {
    const fromRuntimeDb = await readStatusRecordFromRuntimeDb();
    if (fromRuntimeDb) {
      return fromRuntimeDb;
    }
  } catch {
    // Fall through to legacy file-backed state only when runtime DB read is unavailable.
  }

  let fromFile: RefreshStatusRecord | null = null;
  try {
    const raw = await readFile(STATUS_PATH, "utf-8");
    const parsed = JSON.parse(raw) as RefreshStatusRecord;
    if (typeof parsed === "object" && parsed !== null) {
      fromFile = parsed;
    }
  } catch {
    // fall through to persisted fallback
  }

  let fromPersisted: RefreshStatusRecord | null = null;
  try {
    const persisted = await readAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.statusRecord);
    const statusCandidate = persisted?.status;
    if (isRefreshStatusRecord(statusCandidate)) {
      fromPersisted = statusCandidate;
    }
  } catch {
    // fall through
  }

  if (fromFile && fromPersisted) {
    const fileTs = Date.parse(String(fromFile.report_generated_at_utc ?? fromFile.started_at ?? ""));
    const persistedTs = Date.parse(String(fromPersisted.report_generated_at_utc ?? fromPersisted.started_at ?? ""));
    if (Number.isFinite(fileTs) && Number.isFinite(persistedTs)) {
      return persistedTs >= fileTs ? fromPersisted : fromFile;
    }
    if (Number.isFinite(persistedTs)) return fromPersisted;
    if (Number.isFinite(fileTs)) return fromFile;
    return fromPersisted;
  }

  return fromPersisted ?? fromFile;
}

async function writeStatusRecord(record: RefreshStatusRecord): Promise<void> {
  await writeFile(STATUS_PATH, JSON.stringify(record, null, 2), "utf-8");
  await writeAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.statusRecord, {
    status: record,
    updated_at_utc: nowIso(),
  });
}

async function readReportSummary(): Promise<RefreshReport | null> {
  try {
    const raw = await readFile(REPORT_PATH, "utf-8");
    const report = JSON.parse(raw) as Record<string, unknown>;
    if (typeof report !== "object" || report === null) return null;

    return {
      generated_at_utc: typeof report.generated_at_utc === "string" ? report.generated_at_utc : undefined,
      elapsed_seconds: typeof report.elapsed_seconds === "number" ? report.elapsed_seconds : undefined,
      rows_written: typeof report.rows_written === "number" ? report.rows_written : undefined,
      skipped_count: typeof report.skipped_count === "number" ? report.skipped_count : undefined,
      status: typeof report.status === "string" ? report.status : undefined,
      refresh_mode: typeof report.refresh_mode === "string" ? report.refresh_mode : undefined,
    };
  } catch {
    return null;
  }
}

function toNumberOrUndefined(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  return value;
}

function reportGeneratedAtMs(report: RefreshReport | undefined): number {
  const ts = Date.parse(String(report?.generated_at_utc ?? ""));
  if (!Number.isFinite(ts)) return Number.NEGATIVE_INFINITY;
  return ts;
}

function normalizeEpochStatus(schema: string | undefined, status: string | undefined): string | undefined {
  if (status === "ok" || status === "missing_or_invalid") return status;
  if (!schema) return undefined;
  return schema === ORACLE_EPOCH_SCHEMA ? "ok" : "missing_or_invalid";
}

function normalizeTargetMet(value: unknown, bestScore: number | undefined, target: number): boolean | undefined {
  if (typeof value === "boolean") return value;
  if (typeof bestScore !== "number") return undefined;
  return bestScore >= target;
}

function resolveSummaryPath(manifestDir: string, latestSummaryPath: string | undefined): string | null {
  if (!latestSummaryPath) return null;
  const trimmed = latestSummaryPath.trim();
  if (!trimmed) return null;
  if (path.isAbsolute(trimmed)) return trimmed;
  return path.resolve(manifestDir, trimmed);
}

async function readOracleRunEvidence(): Promise<{
  optimizerShortCycle?: string;
  optimizerCycleRequestedRuns?: number;
  optimizerCycleCompletedRuns?: number;
  optimizerSessionId?: string;
  optimizerTargetReturnLiftPct?: number;
  optimizerBestScore?: number;
  optimizerTargetMet?: boolean;
  epochLibraryConfidenceSchema?: string;
  epochLibraryStatus?: string;
}> {
  try {
    const manifestRaw = await readFile(ORACLE_MANIFEST_PATH, "utf-8");
    const manifest = JSON.parse(manifestRaw) as Record<string, unknown>;
    const latest = manifest.latest_session as Record<string, unknown> | undefined;
    if (!latest || typeof latest !== "object") return {};

    const summaryPath = resolveSummaryPath(path.dirname(ORACLE_MANIFEST_PATH), String(latest.summary_path ?? ""));
    if (!summaryPath) return {};

    const summaryRaw = await readFile(summaryPath, "utf-8");
    const summary = JSON.parse(summaryRaw) as Record<string, unknown>;

    const end = summary.end as Record<string, unknown> | undefined;
    const bestScore = toNumberOrUndefined(end?.best_score);
    const target = toNumberOrUndefined(summary.success_target_return_lift_pct) ?? ORACLE_TARGET_RETURN_LIFT;
    const optimizerTargetMet = normalizeTargetMet(summary.target_met_for_prepare_promote, bestScore, target);

    const epochSchemaRaw =
      typeof summary.epoch_library_confidence_schema === "string"
        ? summary.epoch_library_confidence_schema
        : typeof end?.latest_epoch_library_confidence_schema === "string"
          ? end.latest_epoch_library_confidence_schema
          : undefined;
    const epochSchema = epochSchemaRaw?.trim() || undefined;
    const epochStatus = normalizeEpochStatus(
      epochSchema,
      typeof summary.epoch_library_status === "string" ? summary.epoch_library_status : undefined,
    );

    return {
      optimizerShortCycle: "run",
      optimizerCycleRequestedRuns: toNumberOrUndefined(summary.requested_additional_runs),
      optimizerCycleCompletedRuns: toNumberOrUndefined(summary.actual_additional_runs),
      optimizerSessionId: typeof summary.session_id === "string" ? summary.session_id : undefined,
      optimizerTargetReturnLiftPct: target,
      optimizerBestScore: bestScore,
      optimizerTargetMet,
      epochLibraryConfidenceSchema: epochSchema,
      epochLibraryStatus: epochStatus,
    };
  } catch {
    return {};
  }
}

async function finalizeRefreshRunFromChildExit(params: {
  runId: string;
  mode: RefreshMode;
  source: RefreshTriggerSource;
  requestedBy: string;
  startedAtIso: string;
  exitCode: number | null;
  exitSignal: NodeJS.Signals | null;
  spawnErrorMessage?: string;
}): Promise<void> {
  const {
    runId,
    mode,
    source,
    requestedBy,
    startedAtIso,
    exitCode,
    exitSignal,
    spawnErrorMessage,
  } = params;

  const latest = await readStatusRecord();
  const latestRunId = String(latest?.run_id ?? "").trim();
  if (!latest || latestRunId !== runId || !latest.running) {
    return;
  }

  try {
    const report = await readReportSummary();
    const reportStatus = normalizeReportStatus(report?.status);
    const reportFromCurrentRun = reportBelongsToRun(report, startedAtIso);
    const completedAtIso = nowIso();
    const missingTerminalReportError = formatRefreshExitError(exitCode, exitSignal, spawnErrorMessage);

    let completionStatus: RefreshHistoryStatus;
    let completionError: string | undefined;
    let terminalReportStatus: string | undefined = reportFromCurrentRun ? reportStatus : undefined;
    let activationState = latest.activation_state;
    let servingState = latest.serving_state;
    let blockingReasonCode = latest.blocking_reason_code;
    let blockingReasonDetail = latest.blocking_reason_detail;
    let nonCriticalFailureCode: string | null = null;
    let nonCriticalFailureDetail: string | null = null;

    if (reportFromCurrentRun && isTerminalReportStatus(reportStatus)) {
      completionStatus = completionStatusFromReport(reportStatus);
      completionError =
        completionStatus === "ok"
          ? undefined
          : completionErrorFromReport(reportStatus, missingTerminalReportError);
    } else {
      const recoveredDetail = await recoverMissingTerminalReportAfterPublicationCriticalSuccess({
        runId,
        exitError: missingTerminalReportError,
      });
      if (recoveredDetail) {
        const activationOutcome = await evaluateTerminalActivation({
          runId,
          requestedMode: mode,
          triggerSource: source,
          requestedBy,
          startedAtIso,
          completedAtIso,
          report: reportFromCurrentRun ? report : null,
          baseStatus: latest,
        });
        completionStatus = activationOutcome.completionStatus;
        completionError = activationOutcome.completionError;
        terminalReportStatus = activationOutcome.terminalReportStatus;
        activationState = activationOutcome.activationState;
        servingState = activationOutcome.servingState;
        blockingReasonCode = activationOutcome.blockingReasonCode ?? null;
        blockingReasonDetail = activationOutcome.blockingReasonDetail ?? null;
        if (
          completionStatus === "ok"
          && terminalReportStatus === "ok"
          && activationState === "activated"
          && servingState === "allowed"
          && !blockingReasonCode
        ) {
          nonCriticalFailureCode = NON_CRITICAL_FINALIZATION_FAILURE_CODE;
          nonCriticalFailureDetail = recoveredDetail;
        }
      } else {
        completionStatus = "error";
        completionError = missingTerminalReportError;
      }
    }

    if (reportFromCurrentRun && reportStatus === "ok") {
      const criticalTruth = await enforcePreActivationCriticalTruthBeforeTerminalOk({
        runId,
        completedAtIso,
        contextLabel: "refresh_child_exit_terminalization",
      });
      if (!criticalTruth.ok) {
        completionStatus = "error";
        completionError = criticalTruth.failureDetail ?? missingTerminalReportError;
        terminalReportStatus = "error";
        activationState = "activation_failed";
        servingState = "blocked";
        blockingReasonCode = criticalTruth.failureCode ?? "PUBLICATION_CRITICAL_PHASE_TERMINAL_TRUTH_FAILED";
        blockingReasonDetail = criticalTruth.failureDetail ?? missingTerminalReportError;
      } else {
        const activationOutcome = await evaluateTerminalActivation({
          runId,
          requestedMode: mode,
          triggerSource: source,
          requestedBy,
          startedAtIso,
          completedAtIso,
          report,
          baseStatus: latest,
        });
        completionStatus = activationOutcome.completionStatus;
        completionError = activationOutcome.completionError;
        terminalReportStatus = activationOutcome.terminalReportStatus;
        activationState = activationOutcome.activationState;
        servingState = activationOutcome.servingState;
        blockingReasonCode = activationOutcome.blockingReasonCode ?? null;
        blockingReasonDetail = activationOutcome.blockingReasonDetail ?? null;
      }
    }

    if (!terminalReportStatus) {
      terminalReportStatus = completionStatus === "ok" ? "ok" : "error";
    }
    const statusErrorDetail = nonCriticalFailureDetail ?? completionError;

    if (completionStatus !== "ok" || terminalReportStatus !== "ok") {
      await reconcileActivePhaseTruthForTerminalRunError({
        runId,
        baseStatus: latest,
        completedAtIso,
        failureCode:
          toTextOrNull(blockingReasonCode)
          ?? "RUN_TERMINAL_ERROR_LEFT_ACTIVE_PHASE_NON_TERMINAL",
        failureDetail:
          statusErrorDetail
          ?? toTextOrNull(blockingReasonDetail)
          ?? missingTerminalReportError,
        contextLabel: "refresh_child_exit_terminal_error_reconciliation",
      });
    }

    const shouldLogCompletion = latest.completion_logged_for_run_id !== runId;
    const oracleEvidence = shouldLogCompletion ? await readOracleRunEvidence() : {};
    if (shouldLogCompletion) {
      await writeCompletionHistoryEntry(runId, mode, source, requestedBy, completionStatus, {
        rowsWritten: reportFromCurrentRun ? report?.rows_written : undefined,
        elapsedSeconds: reportFromCurrentRun ? report?.elapsed_seconds : undefined,
        refreshReportStatus: terminalReportStatus,
        optimizerShortCycle: oracleEvidence.optimizerShortCycle,
        optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
        optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
        optimizerSessionId: oracleEvidence.optimizerSessionId,
        optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
        optimizerBestScore: oracleEvidence.optimizerBestScore,
        optimizerTargetMet: oracleEvidence.optimizerTargetMet,
        epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
        epochLibraryStatus: oracleEvidence.epochLibraryStatus,
        error: completionError,
      });
    }

    try {
      await upsertRuntimeRefreshRunTerminalStrict({
        runId,
        mode,
        triggerSource: source,
        requestedBy,
        startedAtIso,
        completedAtIso,
        reportGeneratedAtIso: reportFromCurrentRun ? report?.generated_at_utc : undefined,
        rowsWritten: reportFromCurrentRun ? report?.rows_written : undefined,
        reportStatus: terminalReportStatus,
        optimizerShortCycle: oracleEvidence.optimizerShortCycle,
        optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
        optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
        optimizerSessionId: oracleEvidence.optimizerSessionId,
        optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
        optimizerBestScore: oracleEvidence.optimizerBestScore,
        optimizerTargetMet: oracleEvidence.optimizerTargetMet,
        epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
        epochLibraryStatus: oracleEvidence.epochLibraryStatus,
      });
    } catch (error) {
      throw createCriticalRefreshFailureError(
        "RUNTIME_REFRESH_TERMINAL_PERSIST_FAILED",
        error instanceof Error ? error.message : "Unknown terminal runtime_refresh_runs persistence failure.",
      );
    }

    if (nonCriticalFailureCode && nonCriticalFailureDetail) {
      try {
        await persistPublicationStateForRun({
          runId,
          activationState: "activated",
          servingState: "allowed",
          blockingReasonCode: blockingReasonCode ?? null,
          blockingReasonDetail: blockingReasonDetail ?? nonCriticalFailureDetail,
          failureCode: nonCriticalFailureCode,
          failureDetail: nonCriticalFailureDetail,
        });
      } catch (error) {
        console.error("refresh_non_critical_finalization_state_write_failed", error);
      }
    }

    const normalized: RefreshStatusRecord = {
      ...latest,
      running: false,
      completed_at: completedAtIso,
      report_generated_at_utc: reportFromCurrentRun ? report?.generated_at_utc : latest.report_generated_at_utc,
      last_report: reportFromCurrentRun ? (report ?? latest.last_report) : latest.last_report,
      last_error: statusErrorDetail,
      completion_logged_for_run_id: runId,
      activation_state: activationState,
      serving_state: servingState,
      blocking_reason_code: blockingReasonCode,
      blocking_reason_detail: blockingReasonDetail ?? nonCriticalFailureDetail ?? completionError ?? null,
    };

    try {
      await writeStatusRecord(normalized);
    } catch (error) {
      throw createCriticalRefreshFailureError(
        "REFRESH_STATUS_WRITE_FAILED",
        error instanceof Error ? error.message : "Unknown refresh status write failure.",
      );
    }
  } catch (error) {
    const failure = extractCriticalRefreshFailure(error, "CRITICAL_REFRESH_FINALIZATION_FAILED");
    await recordCriticalRefreshFailure({
      runId,
      mode,
      source,
      requestedBy,
      startedAtIso,
      baseStatus: latest,
      failureCode: failure.failureCode,
      failureDetail: failure.failureDetail,
    });
  }
}

function registerRefreshChildLifecycle(params: {
  runId: string;
  child: ChildProcess;
  mode: RefreshMode;
  source: RefreshTriggerSource;
  requestedBy: string;
  startedAtIso: string;
}): void {
  const { runId, child, mode, source, requestedBy, startedAtIso } = params;
  if (ACTIVE_REFRESH_CHILDREN.has(runId)) {
    return;
  }

  const lifecycle: RefreshChildLifecycle = { settled: false };
  ACTIVE_REFRESH_CHILDREN.set(runId, lifecycle);

  const settle = (args: {
    exitCode: number | null;
    exitSignal: NodeJS.Signals | null;
    spawnErrorMessage?: string;
  }): void => {
    if (lifecycle.settled) return;
    lifecycle.settled = true;
    ACTIVE_REFRESH_CHILDREN.delete(runId);
    void finalizeRefreshRunFromChildExit({
      runId,
      mode,
      source,
      requestedBy,
      startedAtIso,
      exitCode: args.exitCode,
      exitSignal: args.exitSignal,
      spawnErrorMessage: args.spawnErrorMessage,
    }).catch((error) => {
      const failure = extractCriticalRefreshFailure(error, "CRITICAL_REFRESH_FINALIZATION_FAILED");
      void recordCriticalRefreshFailure({
        runId,
        mode,
        source,
        requestedBy,
        startedAtIso,
        failureCode: failure.failureCode,
        failureDetail: failure.failureDetail,
      });
    });
  };

  child.once("error", (error) => {
    settle({
      exitCode: child.exitCode ?? null,
      exitSignal: child.signalCode ?? null,
      spawnErrorMessage: `Refresh process spawn error: ${error.message}`,
    });
  });

  child.once("exit", (code, signal) => {
    settle({
      exitCode: typeof code === "number" ? code : null,
      exitSignal: signal ?? null,
    });
  });

  if (typeof child.exitCode === "number" || child.signalCode) {
    settle({
      exitCode: typeof child.exitCode === "number" ? child.exitCode : null,
      exitSignal: child.signalCode ?? null,
    });
  }
}

async function normalizeStatus(): Promise<RefreshStatusRecord> {
  const existing = await readStatusRecord();
  const base: RefreshStatusRecord = existing ?? { running: false };
  try {
    const requestedMode = normalizeRefreshMode(base.requested_mode);
    const report = await readReportSummary();
    const reportStatus = normalizeReportStatus(report?.status);
    const startedAtMs = Number.isFinite(Date.parse(String(base.started_at ?? "")))
      ? Date.parse(String(base.started_at ?? ""))
      : Number.NaN;
    const reportGeneratedMs = Number.isFinite(Date.parse(String(report?.generated_at_utc ?? "")))
      ? Date.parse(String(report?.generated_at_utc ?? ""))
      : Number.NaN;
    const reportIsFromCurrentRun =
      base.running &&
      Number.isFinite(startedAtMs) &&
      Number.isFinite(reportGeneratedMs) &&
      reportGeneratedMs >= startedAtMs;
    const refreshProcessAlive = base.running ? await isRefreshProcessAlive(base.pid) : false;

    if (reportIsFromCurrentRun && isTerminalReportStatus(reportStatus)) {
      if (base.running && refreshProcessAlive) {
        const normalized: RefreshStatusRecord = {
          ...base,
          report_generated_at_utc: report?.generated_at_utc,
          last_report: report ?? base.last_report,
        };
        await writeStatusRecord(normalized);
        return normalized;
      }

      let completionStatus = completionStatusFromReport(reportStatus);
      let completionError =
        completionStatus === "ok" ? undefined : completionErrorFromReport(reportStatus, base.last_error);
      const runId = String(base.run_id ?? "").trim() || undefined;
      let terminalReportStatus: string | undefined = reportStatus;
      const completedAtIso = nowIso();
      let activationState = base.activation_state;
      let servingState = base.serving_state;
      let blockingReasonCode = base.blocking_reason_code;
      let blockingReasonDetail = base.blocking_reason_detail;

      if (reportStatus === "ok") {
        if (!runId) {
          completionStatus = "error";
          completionError = "Refresh reported ok but run_id is missing; publication-critical terminal truth cannot be verified.";
          terminalReportStatus = "error";
          activationState = "activation_failed";
          servingState = "blocked";
          blockingReasonCode = "RUN_ID_MISSING";
          blockingReasonDetail = "Refresh reported ok but run_id is missing; publication-critical terminal truth cannot be verified.";
        } else {
          const criticalTruth = await enforcePreActivationCriticalTruthBeforeTerminalOk({
            runId,
            completedAtIso,
            contextLabel: "refresh_status_normalization_terminalization",
          });
          if (!criticalTruth.ok) {
            completionStatus = "error";
            completionError = criticalTruth.failureDetail
              ?? base.last_error
              ?? "Publication-critical terminal truth failed during refresh status normalization.";
            terminalReportStatus = "error";
            activationState = "activation_failed";
            servingState = "blocked";
            blockingReasonCode = criticalTruth.failureCode ?? "PUBLICATION_CRITICAL_PHASE_TERMINAL_TRUTH_FAILED";
            blockingReasonDetail = criticalTruth.failureDetail
              ?? base.last_error
              ?? "Publication-critical terminal truth failed during refresh status normalization.";
          } else {
            const activationOutcome = await evaluateTerminalActivation({
              runId,
              requestedMode,
              triggerSource: base.trigger_source,
              requestedBy: base.requested_by,
              startedAtIso: base.started_at,
              completedAtIso,
              report,
              baseStatus: base,
            });
            completionStatus = activationOutcome.completionStatus;
            completionError = activationOutcome.completionError;
            terminalReportStatus = activationOutcome.terminalReportStatus;
            activationState = activationOutcome.activationState;
            servingState = activationOutcome.servingState;
            blockingReasonCode = activationOutcome.blockingReasonCode ?? null;
            blockingReasonDetail = activationOutcome.blockingReasonDetail ?? null;
          }
        }
      }

      if (!terminalReportStatus) {
        terminalReportStatus = completionStatus === "ok" ? "ok" : "error";
      }

      if ((completionStatus !== "ok" || terminalReportStatus !== "ok") && runId) {
        await reconcileActivePhaseTruthForTerminalRunError({
          runId,
          baseStatus: base,
          completedAtIso,
          failureCode:
            toTextOrNull(blockingReasonCode)
            ?? "RUN_TERMINAL_ERROR_LEFT_ACTIVE_PHASE_NON_TERMINAL",
          failureDetail:
            completionError
            ?? toTextOrNull(blockingReasonDetail)
            ?? base.last_error
            ?? "Refresh terminalized with error while the active phase remained non-terminal.",
          contextLabel: "refresh_status_report_terminal_error_reconciliation",
        });
      }

      const shouldLogCompletion = Boolean(runId && base.completion_logged_for_run_id !== runId);
      const oracleEvidence = shouldLogCompletion && runId ? await readOracleRunEvidence() : {};
      if (shouldLogCompletion && runId) {
        await writeCompletionHistoryEntry(runId, requestedMode, base.trigger_source, base.requested_by, completionStatus, {
          rowsWritten: report?.rows_written,
          elapsedSeconds: report?.elapsed_seconds,
          refreshReportStatus: terminalReportStatus,
          optimizerShortCycle: oracleEvidence.optimizerShortCycle,
          optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
          optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
          optimizerSessionId: oracleEvidence.optimizerSessionId,
          optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
          optimizerBestScore: oracleEvidence.optimizerBestScore,
          optimizerTargetMet: oracleEvidence.optimizerTargetMet,
          epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
          epochLibraryStatus: oracleEvidence.epochLibraryStatus,
          error: completionError,
        });
      }

      try {
        await upsertRuntimeRefreshRunTerminalStrict({
          runId: runId ?? String(base.run_id ?? "").trim(),
          mode: requestedMode,
          triggerSource: base.trigger_source,
          requestedBy: base.requested_by,
          startedAtIso: base.started_at,
          completedAtIso,
          reportGeneratedAtIso: report?.generated_at_utc,
          rowsWritten: report?.rows_written,
          reportStatus: terminalReportStatus,
          optimizerShortCycle: oracleEvidence.optimizerShortCycle,
          optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
          optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
          optimizerSessionId: oracleEvidence.optimizerSessionId,
          optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
          optimizerBestScore: oracleEvidence.optimizerBestScore,
          optimizerTargetMet: oracleEvidence.optimizerTargetMet,
          epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
          epochLibraryStatus: oracleEvidence.epochLibraryStatus,
        });
      } catch (error) {
        throw createCriticalRefreshFailureError(
          "RUNTIME_REFRESH_TERMINAL_PERSIST_FAILED",
          error instanceof Error ? error.message : "Unknown terminal runtime_refresh_runs persistence failure.",
        );
      }

      const normalized: RefreshStatusRecord = {
        ...base,
        running: false,
        completed_at: completedAtIso,
        report_generated_at_utc: report?.generated_at_utc,
        last_report: report ?? base.last_report,
        last_error: completionError,
        completion_logged_for_run_id: runId ?? base.completion_logged_for_run_id,
        activation_state: activationState,
        serving_state: servingState,
        blocking_reason_code: blockingReasonCode,
        blocking_reason_detail: blockingReasonDetail ?? completionError ?? null,
      };
      await writeStatusRecord(normalized);
      return normalized;
    }

    if (reportIsFromCurrentRun) {
      const normalized: RefreshStatusRecord = {
        ...base,
        report_generated_at_utc: report?.generated_at_utc,
        last_report: report ?? base.last_report,
      };
      await writeStatusRecord(normalized);
      return normalized;
    }

    if (base.running && !refreshProcessAlive) {
      let completionStatus = completionStatusFromReport(reportStatus);
      const staleError = "Cleared stale refresh state because refresh process is no longer active.";
      let completionError =
        completionStatus === "ok" ? undefined : completionErrorFromReport(reportStatus, base.last_error ?? staleError);

      const runId = String(base.run_id ?? "").trim() || undefined;
      let terminalReportStatus: string | undefined = reportStatus;
      const completedAtIso = nowIso();
      let activationState = base.activation_state;
      let servingState = base.serving_state;
      let blockingReasonCode = base.blocking_reason_code;
      let blockingReasonDetail = base.blocking_reason_detail;

      if (reportStatus === "ok") {
        if (!runId) {
          completionStatus = "error";
          completionError = "Refresh reported ok but run_id is missing; publication-critical terminal truth cannot be verified.";
          terminalReportStatus = "error";
          activationState = "activation_failed";
          servingState = "blocked";
          blockingReasonCode = "RUN_ID_MISSING";
          blockingReasonDetail = "Refresh reported ok but run_id is missing; publication-critical terminal truth cannot be verified.";
        } else {
          const criticalTruth = await enforcePreActivationCriticalTruthBeforeTerminalOk({
            runId,
            completedAtIso,
            contextLabel: "refresh_status_stale_process_cleanup",
          });
          if (!criticalTruth.ok) {
            completionStatus = "error";
            completionError = criticalTruth.failureDetail ?? (base.last_error ?? staleError);
            terminalReportStatus = "error";
            activationState = "activation_failed";
            servingState = "blocked";
            blockingReasonCode = criticalTruth.failureCode ?? "PUBLICATION_CRITICAL_PHASE_TERMINAL_TRUTH_FAILED";
            blockingReasonDetail = criticalTruth.failureDetail ?? (base.last_error ?? staleError);
          } else {
            const activationOutcome = await evaluateTerminalActivation({
              runId,
              requestedMode,
              triggerSource: base.trigger_source,
              requestedBy: base.requested_by,
              startedAtIso: base.started_at,
              completedAtIso,
              report,
              baseStatus: base,
            });
            completionStatus = activationOutcome.completionStatus;
            completionError = activationOutcome.completionError;
            terminalReportStatus = activationOutcome.terminalReportStatus;
            activationState = activationOutcome.activationState;
            servingState = activationOutcome.servingState;
            blockingReasonCode = activationOutcome.blockingReasonCode ?? null;
            blockingReasonDetail = activationOutcome.blockingReasonDetail ?? null;
          }
        }
      }

      if (!terminalReportStatus) {
        terminalReportStatus = completionStatus === "ok" ? "ok" : "error";
      }

      if ((completionStatus !== "ok" || terminalReportStatus !== "ok") && runId) {
        await reconcileActivePhaseTruthForTerminalRunError({
          runId,
          baseStatus: base,
          completedAtIso,
          failureCode:
            toTextOrNull(blockingReasonCode)
            ?? "RUN_TERMINAL_ERROR_LEFT_ACTIVE_PHASE_NON_TERMINAL",
          failureDetail:
            completionError
            ?? toTextOrNull(blockingReasonDetail)
            ?? base.last_error
            ?? staleError,
          contextLabel: "refresh_status_stale_process_error_reconciliation",
        });
      }

      const shouldLogCompletion = Boolean(runId && base.completion_logged_for_run_id !== runId);
      const oracleEvidence = shouldLogCompletion && runId ? await readOracleRunEvidence() : {};
      if (shouldLogCompletion && runId) {
        await writeCompletionHistoryEntry(
          runId,
          requestedMode,
          base.trigger_source,
          base.requested_by,
          completionStatus,
          {
            rowsWritten: report?.rows_written,
            elapsedSeconds: report?.elapsed_seconds,
            refreshReportStatus: terminalReportStatus,
            optimizerShortCycle: oracleEvidence.optimizerShortCycle,
            optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
            optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
            optimizerSessionId: oracleEvidence.optimizerSessionId,
            optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
            optimizerBestScore: oracleEvidence.optimizerBestScore,
            optimizerTargetMet: oracleEvidence.optimizerTargetMet,
            epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
            epochLibraryStatus: oracleEvidence.epochLibraryStatus,
            error: completionError,
          },
        );
      }

      try {
        await upsertRuntimeRefreshRunTerminalStrict({
          runId: runId ?? String(base.run_id ?? "").trim(),
          mode: requestedMode,
          triggerSource: base.trigger_source,
          requestedBy: base.requested_by,
          startedAtIso: base.started_at,
          completedAtIso,
          reportGeneratedAtIso: report?.generated_at_utc,
          rowsWritten: report?.rows_written,
          reportStatus: terminalReportStatus,
          optimizerShortCycle: oracleEvidence.optimizerShortCycle,
          optimizerCycleRequestedRuns: oracleEvidence.optimizerCycleRequestedRuns,
          optimizerCycleCompletedRuns: oracleEvidence.optimizerCycleCompletedRuns,
          optimizerSessionId: oracleEvidence.optimizerSessionId,
          optimizerTargetReturnLiftPct: oracleEvidence.optimizerTargetReturnLiftPct,
          optimizerBestScore: oracleEvidence.optimizerBestScore,
          optimizerTargetMet: oracleEvidence.optimizerTargetMet,
          epochLibraryConfidenceSchema: oracleEvidence.epochLibraryConfidenceSchema,
          epochLibraryStatus: oracleEvidence.epochLibraryStatus,
        });
      } catch (error) {
        throw createCriticalRefreshFailureError(
          "RUNTIME_REFRESH_TERMINAL_PERSIST_FAILED",
          error instanceof Error ? error.message : "Unknown terminal runtime_refresh_runs persistence failure.",
        );
      }

      const normalized: RefreshStatusRecord = {
        ...base,
        running: false,
        completed_at: completedAtIso,
        report_generated_at_utc: report?.generated_at_utc,
        last_report: report ?? base.last_report,
        last_error: completionError,
        completion_logged_for_run_id: runId ?? base.completion_logged_for_run_id,
        activation_state: activationState,
        serving_state: servingState,
        blocking_reason_code: blockingReasonCode,
        blocking_reason_detail: blockingReasonDetail ?? completionError ?? null,
      };
      await writeStatusRecord(normalized);
      return normalized;
    }

    if (!base.running && report) {
      const existingReportMs = reportGeneratedAtMs(base.last_report);
      const incomingReportMs = reportGeneratedAtMs(report);
      if (incomingReportMs < existingReportMs) {
        return base;
      }

      const normalized: RefreshStatusRecord = {
        ...base,
        report_generated_at_utc: report.generated_at_utc,
        last_report: report,
      };
      await writeStatusRecord(normalized);
      return normalized;
    }

    return base;
  } catch (error) {
    const failure = extractCriticalRefreshFailure(error, "CRITICAL_REFRESH_STATUS_NORMALIZATION_FAILED");
    return await recordCriticalRefreshFailure({
      runId: String(base.run_id ?? "").trim() || undefined,
      mode: normalizeRefreshMode(base.requested_mode),
      source: base.trigger_source,
      requestedBy: base.requested_by,
      startedAtIso: base.started_at,
      baseStatus: base,
      failureCode: failure.failureCode,
      failureDetail: failure.failureDetail,
    });
  }
}

function buildRefreshArgs(mode: RefreshMode): string[] {
  const args = [REFRESH_SCRIPT];

  if (mode === "snapshot") {
    // Investor-facing snapshot refresh should use the targeted PFSC path so
    // the serving publication can refresh in minutes instead of rebuilding the
    // full universe.
    args.push("--refresh-mode", "targeted_pfsc", "--skip-l5-learning");
    return args;
  }

  args.push("--refresh-mode", "full_universe", "--force-refresh-universe");
  return args;
}

function buildRefreshEnv(mode: RefreshMode, baseEnv: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...baseEnv };

  if (mode === "snapshot") {
    env.TFE_REFRESH_SKIP_FINVIZ_REFRESH = "1";
    env.TFE_REFRESH_BUILD_PROFILE_OVERRIDES = "0";
    env.TFE_QUOTE_CACHE_WORKERS = "24";
  }

  return env;
}

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await readSessionUserFromRequest(request);
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  if (user.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }

  return null;
}

async function resolveRequestedMode(request: Request): Promise<{ mode?: unknown; parseError?: string }> {
  const url = new URL(request.url);
  const fromQuery = url.searchParams.get("mode");
  if (fromQuery) {
    return { mode: fromQuery };
  }

  let text = "";
  try {
    text = await request.text();
  } catch {
    return { parseError: "Failed to read request body." };
  }

  const trimmed = text.trim();
  if (!trimmed) {
    return { mode: undefined };
  }

  try {
    const parsed = JSON.parse(trimmed) as { mode?: unknown };
    return { mode: parsed.mode };
  } catch {
    return { parseError: "Invalid JSON body." };
  }
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const status = await normalizeStatus();
  const phaseLedger = status.run_id ? await loadRuntimeRefreshPhaseLedger(status.run_id) : [];
  const snapshot = await loadRuntimeSnapshotRowsFromPostgres();
  const quote = await loadRuntimeQuoteCacheFromPostgres();
  const publicationState = await loadCanonicalPublicationState({
    snapshot: {
      available: Boolean(snapshot.sourcePath && snapshot.rows.length > 0),
      runId: snapshot.runId,
      generatedAtUtc: snapshot.generatedAtUtc,
    },
    quote: {
      available: Boolean(quote.sourcePath && Object.keys(quote.quotes).length > 0),
      runId: quote.runId,
    },
  });
  return NextResponse.json({ status, phaseLedger, publicationState, refreshScript: REFRESH_SCRIPT });
}

export async function POST(request: Request) {
  const internalAuthorized = hasValidInternalToken(request);
  let requestedBy = "internal_token";
  if (!internalAuthorized) {
    const denied = await requireAdmin(request);
    if (denied) return denied;
    const sessionUser = await readSessionUserFromRequest(request);
    requestedBy = sessionUser?.username ?? "admin";
  }

  const modeInput = await resolveRequestedMode(request);
  if (modeInput.parseError) {
    return NextResponse.json({ error: modeInput.parseError }, { status: 400 });
  }

  const modeValue = modeInput.mode;
  if (!isRefreshMode(modeValue)) {
    return NextResponse.json(
      { error: "mode must be 'snapshot' or 'universe_snapshot' (query or JSON body)." },
      { status: 400 },
    );
  }

  const currentStatus = await normalizeStatus();
  if (currentStatus.running) {
    return NextResponse.json({ error: "A refresh job is already running.", status: currentStatus }, { status: 409 });
  }

  const args = buildRefreshArgs(modeValue);
  const pythonBin = resolvePythonBin();
  const runId = randomUUID();
  const triggerSource = resolveTriggerSource(internalAuthorized, request);

  try {
    const logFd = openSync(LOG_PATH, "a");
    const startedAtIso = nowIso();

    const child = spawn(pythonBin, args, {
      cwd: ROOT_DIR,
      detached: true,
      stdio: ["ignore", logFd, logFd],
      env: {
        ...buildRefreshEnv(modeValue, process.env),
        PYTHONUNBUFFERED: String(process.env.PYTHONUNBUFFERED ?? "1"),
        TFE_REFRESH_HISTORY_PATH: HISTORY_PATH,
        TFE_REFRESH_RUN_ID: runId,
        TFE_REFRESH_REQUESTED_MODE: modeValue,
        TFE_REFRESH_TRIGGER_SOURCE: triggerSource,
        TFE_REFRESH_REQUESTED_BY: requestedBy,
        TFE_REFRESH_STARTED_AT: startedAtIso,
      },
    });

    closeSync(logFd);
    child.unref();

    try {
      await upsertRuntimeRefreshRunStartStrict({
        runId,
        mode: modeValue,
        triggerSource,
        requestedBy,
        startedAtIso,
      });
    } catch (error) {
      try {
        if (typeof child.pid === "number" && child.pid > 0) {
          process.kill(child.pid, "SIGTERM");
        }
      } catch {
        // Best-effort child termination.
      }
      const message = error instanceof Error ? error.message : "runtime_refresh_runs_start_upsert_failed";
      throw new Error(`Failed to persist runtime_refresh_runs start row for run_id=${runId}: ${message}`);
    }

    const nextStatus: RefreshStatusRecord = {
      running: true,
      pid: child.pid,
      run_id: runId,
      requested_mode: modeValue,
      trigger_source: triggerSource,
      requested_by: requestedBy,
      started_at: startedAtIso,
      completed_at: undefined,
      last_error: undefined,
      report_generated_at_utc: currentStatus.report_generated_at_utc,
      last_report: currentStatus.last_report,
      completion_logged_for_run_id: undefined,
    };

    await writeStatusRecord(nextStatus);
    await writeStartHistoryEntry("start", runId, modeValue, triggerSource, requestedBy, {
      pid: child.pid,
    });
    registerRefreshChildLifecycle({
      runId,
      child,
      mode: modeValue,
      source: triggerSource,
      requestedBy,
      startedAtIso,
    });

    return NextResponse.json({ status: nextStatus, internalAuthorized, refreshScript: REFRESH_SCRIPT });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to start refresh.";
    const failedAtIso = nowIso();
    const failedStatus: RefreshStatusRecord = {
      running: false,
      run_id: runId,
      requested_mode: modeValue,
      trigger_source: triggerSource,
      requested_by: requestedBy,
      started_at: failedAtIso,
      completed_at: failedAtIso,
      last_error: message,
      report_generated_at_utc: currentStatus.report_generated_at_utc,
      last_report: currentStatus.last_report,
      completion_logged_for_run_id: runId,
      activation_state: "activation_failed",
      serving_state: "blocked",
      blocking_reason_code: "REFRESH_START_FAILED",
      blocking_reason_detail: message,
    };

    try {
      await upsertRuntimeRefreshRunTerminalStrict({
        runId,
        mode: modeValue,
        triggerSource,
        requestedBy,
        startedAtIso: failedAtIso,
        completedAtIso: failedAtIso,
        reportStatus: "error",
      });
    } catch (terminalPersistError) {
      const failure = extractCriticalRefreshFailure(
        createCriticalRefreshFailureError(
          "RUNTIME_REFRESH_TERMINAL_PERSIST_FAILED",
          terminalPersistError instanceof Error
            ? terminalPersistError.message
            : "Unknown terminal runtime_refresh_runs persistence failure.",
        ),
        "RUNTIME_REFRESH_TERMINAL_PERSIST_FAILED",
      );
      await recordCriticalRefreshFailure({
        runId,
        mode: modeValue,
        source: triggerSource,
        requestedBy,
        startedAtIso: failedAtIso,
        baseStatus: failedStatus,
        failureCode: failure.failureCode,
        failureDetail: failure.failureDetail,
      });
    }

    try {
      await writeStatusRecord(failedStatus);
    } catch (statusWriteError) {
      const failure = extractCriticalRefreshFailure(
        createCriticalRefreshFailureError(
          "REFRESH_STATUS_WRITE_FAILED",
          statusWriteError instanceof Error ? statusWriteError.message : "Unknown refresh status write failure.",
        ),
        "REFRESH_STATUS_WRITE_FAILED",
      );
      await recordCriticalRefreshFailure({
        runId,
        mode: modeValue,
        source: triggerSource,
        requestedBy,
        startedAtIso: failedAtIso,
        baseStatus: failedStatus,
        failureCode: failure.failureCode,
        failureDetail: failure.failureDetail,
      });
    }

    await writeStartHistoryEntry("start_failed", runId, modeValue, triggerSource, requestedBy, {
      error: message,
    });
    return NextResponse.json({ error: message, status: failedStatus, refreshScript: REFRESH_SCRIPT }, { status: 500 });
  }
}
