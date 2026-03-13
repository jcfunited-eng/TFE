import { publicationCandidateIsValid, type PublicationRefreshRunRow } from "@/lib/publication-state";
import {
  columnExists,
  isPostgresConfigured,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  runtimeSourceIsPostgres,
  tableExists,
  toIsoOrNull,
  toLowerTextOrNull,
  toNumberOrNull,
  toTextOrNull,
  RUNTIME_DECISIONS_TABLE,
  RUNTIME_REFRESH_RUNS_TABLE,
  type AttemptFailure,
} from "@/lib/runtime-db";
import type { Pool } from "pg";

type RuntimeRefreshRunColumnPresence = {
  bundleGeneratedAtUtc: boolean;
  snapshotPublicationId: boolean;
  quotePublicationId: boolean;
  quoteBindingStatus: boolean;
  validationStatus: boolean;
  isActivePublication: boolean;
  updatedAt: boolean;
};

type RuntimeActiveRowMeta = {
  runId: string | null;
  generatedAtUtc: string | null;
  error: string | null;
};

export type RuntimePublicationBundleMeta = {
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
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export type RuntimeServingPublicationBundleMeta = RuntimePublicationBundleMeta & {
  activeRuntimeRunId: string | null;
  activeRuntimeGeneratedAtUtc: string | null;
  activeRuntimeBundleValid: boolean;
  fallbackApplied: boolean;
  fallbackReason: string | null;
};


function emptyBundleMeta(
  runId: string | null,
  sourcePath: string | null,
  failures: AttemptFailure[],
): RuntimePublicationBundleMeta {
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
    sourcePath,
    failures,
  };
}

function toServingBundleMeta(
  base: RuntimePublicationBundleMeta,
  extras: {
    activeRuntimeRunId: string | null;
    activeRuntimeGeneratedAtUtc: string | null;
    activeRuntimeBundleValid: boolean;
    fallbackApplied: boolean;
    fallbackReason: string | null;
  },
): RuntimeServingPublicationBundleMeta {
  return {
    ...base,
    activeRuntimeRunId: extras.activeRuntimeRunId,
    activeRuntimeGeneratedAtUtc: extras.activeRuntimeGeneratedAtUtc,
    activeRuntimeBundleValid: extras.activeRuntimeBundleValid,
    fallbackApplied: extras.fallbackApplied,
    fallbackReason: extras.fallbackReason,
  };
}

async function loadRefreshRunColumnPresence(pool: Pool): Promise<RuntimeRefreshRunColumnPresence> {
  const [
    bundleGeneratedAtUtc,
    snapshotPublicationId,
    quotePublicationId,
    quoteBindingStatus,
    validationStatus,
    isActivePublication,
    updatedAt,
  ] = await Promise.all([
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "bundle_generated_at_utc"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "snapshot_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_publication_id"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "quote_binding_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "validation_status"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "is_active_publication"),
    columnExists(pool, RUNTIME_REFRESH_RUNS_TABLE, "updated_at"),
  ]);

  return {
    bundleGeneratedAtUtc,
    snapshotPublicationId,
    quotePublicationId,
    quoteBindingStatus,
    validationStatus,
    isActivePublication,
    updatedAt,
  };
}

function refreshRunSelectColumns(columns: RuntimeRefreshRunColumnPresence): string[] {
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
  ];
}

function refreshRunOrderClause(columns: RuntimeRefreshRunColumnPresence): string {
  if (columns.updatedAt) {
    return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST, updated_at DESC NULLS LAST";
  }
  return "ORDER BY completed_at DESC NULLS LAST, report_generated_at_utc DESC NULLS LAST";
}

function mapRefreshRunRow(
  row: Record<string, unknown> | null | undefined,
  sourcePath: string,
  failures: AttemptFailure[],
): RuntimePublicationBundleMeta {
  if (!row) {
    return emptyBundleMeta(null, sourcePath, failures);
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
    sourcePath,
    failures,
  };
}

function bundleIsValidForServing(meta: RuntimePublicationBundleMeta): boolean {
  return publicationCandidateIsValid({
    runId: meta.runId,
    generatedAtUtc: meta.generatedAtUtc,
    completedAtUtc: meta.completedAtUtc,
    reportGeneratedAtUtc: meta.reportGeneratedAtUtc,
    bundleGeneratedAtUtc: meta.bundleGeneratedAtUtc,
    snapshotPublicationId: meta.snapshotPublicationId,
    quotePublicationId: meta.quotePublicationId,
    quoteBindingStatus: meta.quoteBindingStatus,
    validationStatus: meta.validationStatus,
    mode: meta.mode,
    triggerSource: meta.triggerSource,
    rowsWritten: meta.rowsWritten,
    reportStatus: meta.reportStatus,
    isActivePublication: meta.isActivePublication,
    activationState: null,
    servingState: null,
    blockingReasonCode: null,
    blockingReasonDetail: null,
    failureCode: null,
    failureDetail: null,
    sourcePath: meta.sourcePath,
    failures: meta.failures,
  } satisfies PublicationRefreshRunRow);
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

  const row = result.rows[0];
  return {
    runId: toTextOrNull(row.run_id),
    generatedAtUtc: toIsoOrNull(row.generated_at_utc),
    error: null,
  };
}

async function queryRefreshRunByRunId(
  pool: Pool,
  columns: RuntimeRefreshRunColumnPresence,
  runId: string,
): Promise<RuntimePublicationBundleMeta | null> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const selectColumns = refreshRunSelectColumns(columns);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns.join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE run_id = $1
      LIMIT 1
    `,
    [runId],
  );
  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

async function queryLatestRefreshRun(
  pool: Pool,
  columns: RuntimeRefreshRunColumnPresence,
): Promise<RuntimePublicationBundleMeta | null> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const selectColumns = refreshRunSelectColumns(columns);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns.join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      ${refreshRunOrderClause(columns)}
      LIMIT 1
    `,
  );
  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

async function queryActivePublicationRefreshRun(
  pool: Pool,
  columns: RuntimeRefreshRunColumnPresence,
): Promise<RuntimePublicationBundleMeta | null> {
  if (!columns.isActivePublication) {
    return null;
  }

  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const selectColumns = refreshRunSelectColumns(columns);
  const result = await pool.query<Record<string, unknown>>(
    `
      SELECT ${selectColumns.join(", ")}
      FROM ${RUNTIME_REFRESH_RUNS_TABLE}
      WHERE is_active_publication IS TRUE
      ${refreshRunOrderClause(columns)}
      LIMIT 1
    `,
  );
  if (result.rows.length === 0) return null;
  return mapRefreshRunRow(result.rows[0], sourcePath, []);
}

export async function loadRuntimePublicationBundleMetaByRunId(
  runId: string | null | undefined,
): Promise<RuntimePublicationBundleMeta> {
  const normalizedRunId = toTextOrNull(runId);
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const failures: AttemptFailure[] = [];

  if (!normalizedRunId) {
    return emptyBundleMeta(null, null, failures);
  }

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return emptyBundleMeta(normalizedRunId, null, failures);
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return emptyBundleMeta(normalizedRunId, null, failures);
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const exists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!exists) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
      });
      return emptyBundleMeta(normalizedRunId, null, failures);
    }

    const columns = await loadRefreshRunColumnPresence(pool);
    const row = await queryRefreshRunByRunId(pool, columns, normalizedRunId);
    if (!row) {
      failures.push({
        path: sourcePath,
        reason: `No runtime_refresh_runs row found for run_id='${normalizedRunId}'.`,
      });
      return emptyBundleMeta(normalizedRunId, sourcePath, failures);
    }

    return {
      ...row,
      failures,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown runtime publication bundle query error.",
    });
    return emptyBundleMeta(normalizedRunId, null, failures);
  }
}

export async function loadLatestRuntimeRefreshRunMeta(): Promise<RuntimePublicationBundleMeta> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const failures: AttemptFailure[] = [];

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return emptyBundleMeta(null, null, failures);
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return emptyBundleMeta(null, null, failures);
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const exists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!exists) {
      failures.push({
        path: sourcePath,
        reason: `Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`,
      });
      return emptyBundleMeta(null, null, failures);
    }

    const columns = await loadRefreshRunColumnPresence(pool);
    const row = await queryLatestRefreshRun(pool, columns);
    if (!row) {
      failures.push({
        path: sourcePath,
        reason: "No runtime_refresh_runs rows are present.",
      });
      return emptyBundleMeta(null, sourcePath, failures);
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
    return emptyBundleMeta(null, null, failures);
  }
}

export async function loadServingRuntimePublicationBundleMeta(): Promise<RuntimeServingPublicationBundleMeta> {
  const sourcePath = postgresSourcePath(RUNTIME_REFRESH_RUNS_TABLE);
  const failures: AttemptFailure[] = [];

  const failResult = (
    reason: string,
    options?: {
      activeRuntimeRunId?: string | null;
      activeRuntimeGeneratedAtUtc?: string | null;
      activeRuntimeBundleValid?: boolean;
      fallbackApplied?: boolean;
      fallbackReason?: string | null;
    },
  ): RuntimeServingPublicationBundleMeta => {
    failures.push({ path: sourcePath, reason });
    return toServingBundleMeta(
      emptyBundleMeta(null, null, failures),
      {
        activeRuntimeRunId: options?.activeRuntimeRunId ?? null,
        activeRuntimeGeneratedAtUtc: options?.activeRuntimeGeneratedAtUtc ?? null,
        activeRuntimeBundleValid: options?.activeRuntimeBundleValid ?? false,
        fallbackApplied: options?.fallbackApplied ?? false,
        fallbackReason: options?.fallbackReason ?? null,
      },
    );
  };

  if (!runtimeSourceIsPostgres()) {
    return failResult(`Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`);
  }

  if (!isPostgresConfigured()) {
    return failResult("Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.");
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const runsTableExists = await tableExists(pool, RUNTIME_REFRESH_RUNS_TABLE);
    if (!runsTableExists) {
      return failResult(`Table '${RUNTIME_REFRESH_RUNS_TABLE}' does not exist.`);
    }

    const columns = await loadRefreshRunColumnPresence(pool);
    const activeRuntimeMeta = await loadRuntimeActiveRowMeta(pool);
    if (activeRuntimeMeta.error) {
      failures.push({
        path: postgresSourcePath(RUNTIME_DECISIONS_TABLE),
        reason: activeRuntimeMeta.error,
      });
    }

    const activeRuntimeRunId = activeRuntimeMeta.runId;
    const activeRuntimeGeneratedAtUtc = activeRuntimeMeta.generatedAtUtc;
    const activePublicationMeta = await queryActivePublicationRefreshRun(pool, columns);
    const activePublicationValid = activePublicationMeta ? bundleIsValidForServing(activePublicationMeta) : false;

    if (activePublicationMeta && activePublicationValid) {
      return toServingBundleMeta(
        {
          ...activePublicationMeta,
          failures,
        },
        {
          activeRuntimeRunId,
          activeRuntimeGeneratedAtUtc,
          activeRuntimeBundleValid: true,
          fallbackApplied: activeRuntimeRunId !== null && activeRuntimeRunId !== activePublicationMeta.runId,
          fallbackReason:
            activeRuntimeRunId !== null && activeRuntimeRunId !== activePublicationMeta.runId
              ? "runtime_latest_differs_from_active_publication"
              : null,
        },
      );
    }

    const requiredColumnsPresent = columns.validationStatus
      && columns.snapshotPublicationId
      && columns.quotePublicationId
      && columns.quoteBindingStatus
      && columns.isActivePublication;
    if (!requiredColumnsPresent) {
      failures.push({
        path: sourcePath,
        reason:
          "Validated publication gating requires runtime_refresh_runs columns: validation_status, snapshot_publication_id, quote_publication_id, quote_binding_status, is_active_publication.",
      });
      return toServingBundleMeta(
        emptyBundleMeta(null, null, failures),
        {
          activeRuntimeRunId,
          activeRuntimeGeneratedAtUtc,
          activeRuntimeBundleValid: false,
          fallbackApplied: false,
          fallbackReason: "validated_publication_pointer_columns_missing",
        },
      );
    }

    if (!activePublicationMeta) {
      failures.push({
        path: sourcePath,
        reason: "No active publication pointer is set.",
      });
      return toServingBundleMeta(
        emptyBundleMeta(null, null, failures),
        {
          activeRuntimeRunId,
          activeRuntimeGeneratedAtUtc,
          activeRuntimeBundleValid: false,
          fallbackApplied: false,
          fallbackReason: "no_active_publication_pointer",
        },
      );
    }

    failures.push({
      path: sourcePath,
      reason: `Active publication pointer run_id='${activePublicationMeta.runId ?? "unknown"}' is not valid for serving.`,
    });
    return toServingBundleMeta(
      emptyBundleMeta(activePublicationMeta.runId, sourcePath, failures),
      {
        activeRuntimeRunId,
        activeRuntimeGeneratedAtUtc,
        activeRuntimeBundleValid: false,
        fallbackApplied: false,
        fallbackReason: "active_publication_invalid",
      },
    );
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown serving publication bundle query error.";
    return failResult(reason);
  }
}
