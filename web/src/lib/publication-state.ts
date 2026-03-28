import type { Pool } from "pg";

import {
  columnExists,
  type AttemptFailure,
  isPostgresConfigured,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  RUNTIME_DECISIONS_TABLE,
  RUNTIME_REFRESH_RUNS_TABLE,
  runtimeSourceIsPostgres,
  tableExists,
  toIsoOrNull,
  toLowerTextOrNull,
  toNumberOrNull,
  toTextOrNull,
} from "@/lib/runtime-db";

const BYPASS_PUBLICATION_ID = "BYPASS_ACTIVE";
const BYPASS_QUOTE_BINDING_STATUS = "bypass_active";
const BYPASS_VALIDATION_STATUS = "pass";

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
  completedAt: boolean;
  reportGeneratedAtUtc: boolean;
  bundleGeneratedAtUtc: boolean;
  snapshotPublicationId: boolean;
  quotePublicationId: boolean;
  quoteBindingStatus: boolean;
  validationStatus: boolean;
  mode: boolean;
  triggerSource: boolean;
  rowsWritten: boolean;
  reportStatus: boolean;
  isActivePublication: boolean;
  activationState: boolean;
  servingState: boolean;
  blockingReasonCode: boolean;
  blockingReasonDetail: boolean;
  failureCode: boolean;
  failureDetail: boolean;
  updatedAt: boolean;
};

type CanonicalPublicationStateInput = {
  snapshot?: RuntimeSnapshotServingContext | null;
  quote?: RuntimeQuoteServingContext | null;
  maxAgeMinutes?: number;
  nowMs?: number;
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

type RuntimeServingMeta = {
  runId: string | null;
  generatedAtUtc: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

type RefreshRunRowRecord = Record<string, unknown>;

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
  servingRunId: string | null;
  servingFallbackApplied: boolean;
  servingFallbackReason: string | null;
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

function bypassSourcePath(): string {
  return `${postgresSourcePath(RUNTIME_DECISIONS_TABLE)}?mode=bypass_active`;
}

function bypassFailures(): AttemptFailure[] {
  return [];
}

function normalizeMaxAgeMinutes(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 1800;
  const whole = Math.floor(n);
  if (whole < 1) return 1;
  if (whole > 20160) return 20160;
  return whole;
}

function runtimeRefreshOrderClause(columns: RefreshRunColumnPresence): string {
  if (columns.updatedAt) {
    return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST, updated_at DESC NULLS LAST";
  }
  return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST";
}

function bypassedPublicationRow(params?: {
  runId?: string | null;
  generatedAtUtc?: string | null;
  completedAtUtc?: string | null;
  reportGeneratedAtUtc?: string | null;
  bundleGeneratedAtUtc?: string | null;
  mode?: string | null;
  triggerSource?: string | null;
  rowsWritten?: number | null;
  reportStatus?: string | null;
  sourcePath?: string | null;
  failures?: AttemptFailure[];
}): PublicationRefreshRunRow {
  const generatedAtUtc = toIsoOrNull(params?.generatedAtUtc) ?? null;
  const completedAtUtc = toIsoOrNull(params?.completedAtUtc) ?? generatedAtUtc;
  const reportGeneratedAtUtc = toIsoOrNull(params?.reportGeneratedAtUtc) ?? generatedAtUtc;
  const bundleGeneratedAtUtc = toIsoOrNull(params?.bundleGeneratedAtUtc) ?? generatedAtUtc;
  return {
    runId: toTextOrNull(params?.runId) ?? null,
    generatedAtUtc,
    completedAtUtc,
    reportGeneratedAtUtc,
    bundleGeneratedAtUtc,
    snapshotPublicationId: BYPASS_PUBLICATION_ID,
    quotePublicationId: BYPASS_PUBLICATION_ID,
    quoteBindingStatus: BYPASS_QUOTE_BINDING_STATUS,
    validationStatus: BYPASS_VALIDATION_STATUS,
    mode: toTextOrNull(params?.mode) ?? null,
    triggerSource: toTextOrNull(params?.triggerSource) ?? null,
    rowsWritten: toNumberOrNull(params?.rowsWritten),
    reportStatus: toLowerTextOrNull(params?.reportStatus) ?? "ok",
    isActivePublication: true,
    activationState: "activated",
    servingState: "allowed",
    blockingReasonCode: null,
    blockingReasonDetail: null,
    failureCode: null,
    failureDetail: null,
    sourcePath: params?.sourcePath ?? bypassSourcePath(),
    failures: params?.failures ?? bypassFailures(),
  };
}

async function loadRefreshRunColumnPresence(pool: Pool): Promise<RefreshRunColumnPresence> {
  const checks = await Promise.all([
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "completed_at"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "report_generated_at_utc"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "bundle_generated_at_utc"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "snapshot_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_binding_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "validation_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "mode"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "trigger_source"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "rows_written"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "report_status"),
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
    completedAt: checks[0],
    reportGeneratedAtUtc: checks[1],
    bundleGeneratedAtUtc: checks[2],
    snapshotPublicationId: checks[3],
    quotePublicationId: checks[4],
    quoteBindingStatus: checks[5],
    validationStatus: checks[6],
    mode: checks[7],
    triggerSource: checks[8],
    rowsWritten: checks[9],
    reportStatus: checks[10],
    isActivePublication: checks[11],
    activationState: checks[12],
    servingState: checks[13],
    blockingReasonCode: checks[14],
    blockingReasonDetail: checks[15],
    failureCode: checks[16],
    failureDetail: checks[17],
    updatedAt: checks[18],
  };
}

function refreshRunSelectColumns(columns: RefreshRunColumnPresence): string[] {
  return [
    "run_id",
    columns.completedAt ? "completed_at" : "NULL::timestamptz AS completed_at",
    columns.reportGeneratedAtUtc ? "report_generated_at_utc" : "NULL::timestamptz AS report_generated_at_utc",
    columns.bundleGeneratedAtUtc ? "bundle_generated_at_utc" : "NULL::timestamptz AS bundle_generated_at_utc",
    columns.snapshotPublicationId ? "snapshot_publication_id" : "NULL::text AS snapshot_publication_id",
    columns.quotePublicationId ? "quote_publication_id" : "NULL::text AS quote_publication_id",
    columns.quoteBindingStatus ? "quote_binding_status" : "NULL::text AS quote_binding_status",
    columns.validationStatus ? "validation_status" : "NULL::text AS validation_status",
    columns.mode ? "mode" : "NULL::text AS mode",
    columns.triggerSource ? "trigger_source" : "NULL::text AS trigger_source",
    columns.rowsWritten ? "rows_written" : "NULL::bigint AS rows_written",
    columns.reportStatus ? "report_status" : "NULL::text AS report_status",
    columns.isActivePublication ? "is_active_publication" : "TRUE AS is_active_publication",
    columns.activationState ? "activation_state" : "NULL::text AS activation_state",
    columns.servingState ? "serving_state" : "NULL::text AS serving_state",
    columns.blockingReasonCode ? "blocking_reason_code" : "NULL::text AS blocking_reason_code",
    columns.blockingReasonDetail ? "blocking_reason_detail" : "NULL::text AS blocking_reason_detail",
    columns.failureCode ? "failure_code" : "NULL::text AS failure_code",
    columns.failureDetail ? "failure_detail" : "NULL::text AS failure_detail",
  ];
}

function mapRefreshRunRecord(
  row: RefreshRunRowRecord | null | undefined,
  sourcePath: string | null,
  failures: AttemptFailure[],
): PublicationRefreshRunRow {
  if (!row) {
    return bypassedPublicationRow({
      sourcePath,
      failures,
    });
  }

  const generatedAtUtc =
    toIsoOrNull(row.bundle_generated_at_utc)
    ?? toIsoOrNull(row.completed_at)
    ?? toIsoOrNull(row.report_generated_at_utc)
    ?? null;

  return bypassedPublicationRow({
    runId: toTextOrNull(row.run_id),
    generatedAtUtc,
    completedAtUtc: toIsoOrNull(row.completed_at),
    reportGeneratedAtUtc: toIsoOrNull(row.report_generated_at_utc),
    bundleGeneratedAtUtc: toIsoOrNull(row.bundle_generated_at_utc),
    mode: toTextOrNull(row.mode),
    triggerSource: toTextOrNull(row.trigger_source),
    rowsWritten: toNumberOrNull(row.rows_written),
    reportStatus: toLowerTextOrNull(row.report_status) ?? "ok",
    sourcePath,
    failures,
  });
}

async function readLatestRuntimeDecisionMeta(): Promise<RuntimeServingMeta> {
  const sourcePath = postgresSourcePath(RUNTIME_DECISIONS_TABLE);
  const failures: AttemptFailure[] = [];

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return { runId: null, generatedAtUtc: null, sourcePath: null, failures };
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return { runId: null, generatedAtUtc: null, sourcePath: null, failures };
  }

  try {
    const pool = resolveRuntimePostgresPool();
    if (!(await tableExists(pool, RUNTIME_DECISIONS_TABLE))) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_DECISIONS_TABLE}' does not exist.`,
      });
      return { runId: null, generatedAtUtc: null, sourcePath: null, failures };
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
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_DECISIONS_TABLE}' is empty.`,
      });
      return { runId: null, generatedAtUtc: null, sourcePath: null, failures };
    }

    return {
      runId: toTextOrNull(result.rows[0]?.run_id),
      generatedAtUtc: toIsoOrNull(result.rows[0]?.generated_at_utc),
      sourcePath,
      failures,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown runtime decisions query error.",
    });
    return { runId: null, generatedAtUtc: null, sourcePath: null, failures };
  }
}

async function queryRefreshRunByRunId(pool: Pool, runId: string): Promise<PublicationRefreshRunRow | null> {
  if (!(await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE))) {
    return null;
  }

  const columns = await loadRefreshRunColumnPresence(pool);
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const result = await pool.query<RefreshRunRowRecord>(
    `
      SELECT ${refreshRunSelectColumns(columns).join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE run_id = $1
      LIMIT 1
    `,
    [runId],
  );

  if (result.rows.length === 0) return null;
  return mapRefreshRunRecord(result.rows[0], sourcePath, []);
}

async function queryLatestRefreshRun(pool: Pool): Promise<PublicationRefreshRunRow | null> {
  if (!(await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE))) {
    return null;
  }

  const columns = await loadRefreshRunColumnPresence(pool);
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const result = await pool.query<RefreshRunRowRecord>(
    `
      SELECT ${refreshRunSelectColumns(columns).join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      ${runtimeRefreshOrderClause(columns)}
      LIMIT 1
    `,
  );

  if (result.rows.length === 0) return null;
  return mapRefreshRunRecord(result.rows[0], sourcePath, []);
}

function buildCanonicalState(params: {
  baseRow: PublicationRefreshRunRow;
  snapshotRunId: string | null;
  quoteRunId: string | null;
  latestRunId: string | null;
  generatedAtUtc: string | null;
  maxAgeMinutes: number;
  nowMs: number;
}): CanonicalPublicationState {
  const generatedAtUtc = toIsoOrNull(params.generatedAtUtc);
  const generatedAtMs = generatedAtUtc ? Date.parse(generatedAtUtc) : Number.NaN;
  const generatedAtValid = Number.isFinite(generatedAtMs);
  const snapshotAgeMinutes = generatedAtValid
    ? Math.max(0, Number((((params.nowMs - generatedAtMs) / 60000)).toFixed(3)))
    : null;

  return {
    ...params.baseRow,
    generatedAtUtc,
    bundleGeneratedAtUtc: generatedAtUtc,
    completedAtUtc: params.baseRow.completedAtUtc ?? generatedAtUtc,
    reportGeneratedAtUtc: params.baseRow.reportGeneratedAtUtc ?? generatedAtUtc,
    snapshotPublicationId: BYPASS_PUBLICATION_ID,
    quotePublicationId: BYPASS_PUBLICATION_ID,
    quoteBindingStatus: BYPASS_QUOTE_BINDING_STATUS,
    validationStatus: BYPASS_VALIDATION_STATUS,
    isActivePublication: true,
    activationState: "activated",
    servingState: "allowed",
    blockingReasonCode: null,
    blockingReasonDetail: null,
    failureCode: null,
    failureDetail: null,
    candidateValid: true,
    servingRunId: params.snapshotRunId ?? params.latestRunId ?? params.baseRow.runId,
    servingFallbackApplied: false,
    servingFallbackReason: null,
    activeRuntimeRunId: params.snapshotRunId ?? params.latestRunId ?? params.baseRow.runId,
    activeRuntimeGeneratedAtUtc: generatedAtUtc,
    snapshotRunId: params.snapshotRunId,
    quoteRunId: params.quoteRunId,
    freshness: {
      generatedAtUtc,
      generatedAtValid,
      snapshotAgeMinutes,
      snapshotMaxAgeMinutes: params.maxAgeMinutes,
      stale: false,
    },
    latestRunId: params.latestRunId,
  };
}

export async function resolveAdminActivePublicationBundleId(): Promise<ActivePublicationBundlePointerResolution> {
  const latest = await readLatestRuntimeDecisionMeta();
  return {
    publicationBundleId: BYPASS_PUBLICATION_ID,
    runId: latest.runId,
    targetEnvironment: "production",
    sourceKind: null,
    sourcePath: latest.sourcePath ?? bypassSourcePath(),
    failures: latest.failures,
  };
}

export async function resolveStep1CutoverActivePublicationResolution(): Promise<Step1CutoverActivePublicationResolution> {
  const latest = await readLatestRuntimeDecisionMeta();
  return {
    runId: latest.runId,
    publicationBundleId: BYPASS_PUBLICATION_ID,
    assessmentReportId: null,
    targetEnvironment: "production",
    generatedAtUtc: latest.generatedAtUtc,
    completedAtUtc: latest.generatedAtUtc,
    reportGeneratedAtUtc: latest.generatedAtUtc,
    bundleGeneratedAtUtc: latest.generatedAtUtc,
    mode: "bypass_active",
    triggerSource: "runtime_postgres",
    reportStatus: "ok",
    candidateValid: true,
    blockingReasonCode: null,
    blockingReasonDetail: null,
    sourcePath: latest.sourcePath ?? bypassSourcePath(),
    failures: latest.failures,
  };
}

export function publicationCandidateIsValid(_row: PublicationRefreshRunRow | null | undefined): boolean {
  return true;
}

export async function loadRuntimeRefreshRunById(runId: string | null | undefined): Promise<PublicationRefreshRunRow> {
  const normalizedRunId = toTextOrNull(runId);
  const latestDecision = await readLatestRuntimeDecisionMeta();

  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    return bypassedPublicationRow({
      runId: normalizedRunId ?? latestDecision.runId,
      generatedAtUtc: latestDecision.generatedAtUtc,
      sourcePath: latestDecision.sourcePath ?? bypassSourcePath(),
      failures: latestDecision.failures,
    });
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const row = normalizedRunId ? await queryRefreshRunByRunId(pool, normalizedRunId) : null;
    if (row) {
      return bypassedPublicationRow({
        ...row,
        runId: row.runId ?? normalizedRunId ?? latestDecision.runId,
        generatedAtUtc: row.generatedAtUtc ?? latestDecision.generatedAtUtc,
        sourcePath: row.sourcePath ?? latestDecision.sourcePath ?? bypassSourcePath(),
        failures: [...row.failures, ...latestDecision.failures],
      });
    }
  } catch {
    // Ignore refresh table lookup failures and fall back to runtime table truth.
  }

  return bypassedPublicationRow({
    runId: normalizedRunId ?? latestDecision.runId,
    generatedAtUtc: latestDecision.generatedAtUtc,
    sourcePath: latestDecision.sourcePath ?? bypassSourcePath(),
    failures: latestDecision.failures,
  });
}

export async function loadLatestRuntimeRefreshRunState(): Promise<PublicationRefreshRunRow> {
  const latestDecision = await readLatestRuntimeDecisionMeta();

  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) {
    return bypassedPublicationRow({
      runId: latestDecision.runId,
      generatedAtUtc: latestDecision.generatedAtUtc,
      sourcePath: latestDecision.sourcePath ?? bypassSourcePath(),
      failures: latestDecision.failures,
    });
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const row = await queryLatestRefreshRun(pool);
    if (row) {
      return bypassedPublicationRow({
        ...row,
        runId: row.runId ?? latestDecision.runId,
        generatedAtUtc: row.generatedAtUtc ?? latestDecision.generatedAtUtc,
        sourcePath: row.sourcePath ?? latestDecision.sourcePath ?? bypassSourcePath(),
        failures: [...row.failures, ...latestDecision.failures],
      });
    }
  } catch {
    // Ignore refresh table lookup failures and fall back to runtime table truth.
  }

  return bypassedPublicationRow({
    runId: latestDecision.runId,
    generatedAtUtc: latestDecision.generatedAtUtc,
    sourcePath: latestDecision.sourcePath ?? bypassSourcePath(),
    failures: latestDecision.failures,
  });
}

export async function ensurePublicationStateColumns(): Promise<void> {
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) return;

  const pool = resolveRuntimePostgresPool();
  if (!(await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE))) return;

  await pool.query(
    `
      ALTER TABLE ${RUNTIME_REFRESH_RUNS_TABLE}
      ADD COLUMN IF NOT EXISTS is_active_publication boolean NOT NULL DEFAULT FALSE,
      ADD COLUMN IF NOT EXISTS activation_state text,
      ADD COLUMN IF NOT EXISTS serving_state text,
      ADD COLUMN IF NOT EXISTS blocking_reason_code text,
      ADD COLUMN IF NOT EXISTS blocking_reason_detail text,
      ADD COLUMN IF NOT EXISTS failure_code text,
      ADD COLUMN IF NOT EXISTS failure_detail text,
      ADD COLUMN IF NOT EXISTS snapshot_publication_id text,
      ADD COLUMN IF NOT EXISTS quote_publication_id text,
      ADD COLUMN IF NOT EXISTS quote_binding_status text,
      ADD COLUMN IF NOT EXISTS validation_status text
    `,
  );
}

export async function setActivePublicationRun(runId: string): Promise<boolean> {
  const normalizedRunId = toTextOrNull(runId);
  if (!normalizedRunId) return true;
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) return true;

  await ensurePublicationStateColumns();
  const pool = resolveRuntimePostgresPool();
  if (!(await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE))) return true;

  await pool.query("BEGIN");
  try {
    await pool.query(
      `
        UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
        SET is_active_publication = CASE WHEN run_id = $1 THEN TRUE ELSE FALSE END,
            snapshot_publication_id = CASE WHEN run_id = $1 THEN $2 ELSE snapshot_publication_id END,
            quote_publication_id = CASE WHEN run_id = $1 THEN $2 ELSE quote_publication_id END,
            quote_binding_status = CASE WHEN run_id = $1 THEN $3 ELSE quote_binding_status END,
            validation_status = CASE WHEN run_id = $1 THEN $4 ELSE validation_status END,
            activation_state = CASE WHEN run_id = $1 THEN 'activated' ELSE activation_state END,
            serving_state = CASE WHEN run_id = $1 THEN 'allowed' ELSE serving_state END,
            blocking_reason_code = CASE WHEN run_id = $1 THEN NULL ELSE blocking_reason_code END,
            blocking_reason_detail = CASE WHEN run_id = $1 THEN NULL ELSE blocking_reason_detail END,
            failure_code = CASE WHEN run_id = $1 THEN NULL ELSE failure_code END,
            failure_detail = CASE WHEN run_id = $1 THEN NULL ELSE failure_detail END,
            updated_at = NOW()
      `,
      [normalizedRunId, BYPASS_PUBLICATION_ID, BYPASS_QUOTE_BINDING_STATUS, BYPASS_VALIDATION_STATUS],
    );
    await pool.query("COMMIT");
    return true;
  } catch (error) {
    try {
      await pool.query("ROLLBACK");
    } catch {
      // Ignore rollback errors.
    }
    throw error;
  }
}

export async function persistPublicationStateForRun(params: PersistPublicationStateParams): Promise<void> {
  const normalizedRunId = toTextOrNull(params.runId);
  if (!normalizedRunId) return;
  if (!runtimeSourceIsPostgres() || !isPostgresConfigured()) return;

  await ensurePublicationStateColumns();
  const pool = resolveRuntimePostgresPool();
  if (!(await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE))) return;

  await pool.query(
    `
      UPDATE ${RUNTIME_REFRESH_RUNS_TABLE}
      SET snapshot_publication_id = $2,
          quote_publication_id = $2,
          quote_binding_status = $3,
          validation_status = $4,
          activation_state = 'activated',
          serving_state = 'allowed',
          blocking_reason_code = NULL,
          blocking_reason_detail = NULL,
          failure_code = NULL,
          failure_detail = NULL,
          updated_at = NOW()
      WHERE run_id = $1
    `,
    [normalizedRunId, BYPASS_PUBLICATION_ID, BYPASS_QUOTE_BINDING_STATUS, BYPASS_VALIDATION_STATUS],
  );
}

export async function loadCanonicalPublicationState(
  input: CanonicalPublicationStateInput = {},
): Promise<CanonicalPublicationState> {
  const maxAgeMinutes = normalizeMaxAgeMinutes(input.maxAgeMinutes);
  const nowMs = Number.isFinite(Number(input.nowMs)) ? Number(input.nowMs) : Date.now();
  const latestDecision = await readLatestRuntimeDecisionMeta();

  const snapshotRunId = toTextOrNull(input.snapshot?.runId) ?? latestDecision.runId;
  const snapshotGeneratedAtUtc = toIsoOrNull(input.snapshot?.generatedAtUtc) ?? latestDecision.generatedAtUtc;
  const quoteRunId = toTextOrNull(input.quote?.runId) ?? snapshotRunId;

  const baseRow = await loadRuntimeRefreshRunById(snapshotRunId);
  return buildCanonicalState({
    baseRow,
    snapshotRunId,
    quoteRunId,
    latestRunId: latestDecision.runId ?? snapshotRunId,
    generatedAtUtc: snapshotGeneratedAtUtc ?? baseRow.generatedAtUtc,
    maxAgeMinutes,
    nowMs,
  });
}

export function publicationContractFields(state: CanonicalPublicationState): PublicationContractFields {
  return {
    run_id: state.runId,
    generated_at_utc: state.generatedAtUtc,
    validation_status: BYPASS_VALIDATION_STATUS,
    snapshot_publication_id: BYPASS_PUBLICATION_ID,
    quote_publication_id: BYPASS_PUBLICATION_ID,
    quote_binding_status: BYPASS_QUOTE_BINDING_STATUS,
    serving_state: "allowed",
    activation_state: "activated",
    blocking_reason_code: null,
    blocking_reason_detail: null,
  };
}
