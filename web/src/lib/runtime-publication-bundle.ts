import {
  loadLatestRuntimeRefreshRunState,
  loadRuntimeRefreshRunById,
  type PublicationRefreshRunRow,
} from "@/lib/publication-state";
import {
  type AttemptFailure,
  isPostgresConfigured,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  RUNTIME_DECISIONS_TABLE,
  runtimeSourceIsPostgres,
  tableExists,
  toIsoOrNull,
  toTextOrNull,
} from "@/lib/runtime-db";

const BYPASS_PUBLICATION_ID = "BYPASS_ACTIVE";
const BYPASS_QUOTE_BINDING_STATUS = "bypass_active";
const BYPASS_VALIDATION_STATUS = "pass";

type RuntimeActiveRowMeta = {
  runId: string | null;
  generatedAtUtc: string | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export type InvestorActivePublicationBundleResolution = {
  publicationBundleId: string | null;
  runId: string | null;
  targetEnvironment: string | null;
  sourceKind: "active_publication_pointer" | null;
  sourcePath: string | null;
  failures: AttemptFailure[];
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

function mapRefreshRowToBundleMeta(row: PublicationRefreshRunRow): RuntimePublicationBundleMeta {
  return {
    runId: row.runId,
    generatedAtUtc: row.generatedAtUtc,
    completedAtUtc: row.completedAtUtc,
    reportGeneratedAtUtc: row.reportGeneratedAtUtc,
    bundleGeneratedAtUtc: row.bundleGeneratedAtUtc,
    snapshotPublicationId: BYPASS_PUBLICATION_ID,
    quotePublicationId: BYPASS_PUBLICATION_ID,
    quoteBindingStatus: BYPASS_QUOTE_BINDING_STATUS,
    validationStatus: BYPASS_VALIDATION_STATUS,
    mode: row.mode,
    triggerSource: row.triggerSource,
    rowsWritten: row.rowsWritten,
    reportStatus: row.reportStatus,
    isActivePublication: true,
    sourcePath: row.sourcePath,
    failures: row.failures,
  };
}

function mapToServingMeta(
  base: RuntimePublicationBundleMeta,
  activeRuntimeRunId: string | null,
  activeRuntimeGeneratedAtUtc: string | null,
): RuntimeServingPublicationBundleMeta {
  return {
    ...base,
    activeRuntimeRunId,
    activeRuntimeGeneratedAtUtc,
    activeRuntimeBundleValid: true,
    fallbackApplied: false,
    fallbackReason: null,
  };
}

async function readLatestRuntimeDecisionMeta(): Promise<RuntimeActiveRowMeta> {
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

export async function resolveInvestorActivePublicationBundleId(): Promise<InvestorActivePublicationBundleResolution> {
  const active = await readLatestRuntimeDecisionMeta();
  return {
    publicationBundleId: BYPASS_PUBLICATION_ID,
    runId: active.runId,
    targetEnvironment: "production",
    sourceKind: null,
    sourcePath: active.sourcePath,
    failures: active.failures,
  };
}

export async function loadRuntimePublicationBundleMetaByRunId(
  runId: string | null | undefined,
): Promise<RuntimePublicationBundleMeta> {
  const normalizedRunId = toTextOrNull(runId);
  const refreshRow = await loadRuntimeRefreshRunById(normalizedRunId);
  const active = await readLatestRuntimeDecisionMeta();
  const base = mapRefreshRowToBundleMeta(refreshRow);

  return {
    ...base,
    runId: base.runId ?? normalizedRunId ?? active.runId,
    generatedAtUtc: base.generatedAtUtc ?? active.generatedAtUtc,
    completedAtUtc: base.completedAtUtc ?? active.generatedAtUtc,
    reportGeneratedAtUtc: base.reportGeneratedAtUtc ?? active.generatedAtUtc,
    bundleGeneratedAtUtc: base.bundleGeneratedAtUtc ?? active.generatedAtUtc,
    sourcePath: base.sourcePath ?? active.sourcePath,
    failures: [...base.failures, ...active.failures],
  };
}

export async function loadLatestRuntimeRefreshRunMeta(): Promise<RuntimePublicationBundleMeta> {
  const refreshRow = await loadLatestRuntimeRefreshRunState();
  const active = await readLatestRuntimeDecisionMeta();
  const base = mapRefreshRowToBundleMeta(refreshRow);

  return {
    ...base,
    runId: base.runId ?? active.runId,
    generatedAtUtc: base.generatedAtUtc ?? active.generatedAtUtc,
    completedAtUtc: base.completedAtUtc ?? active.generatedAtUtc,
    reportGeneratedAtUtc: base.reportGeneratedAtUtc ?? active.generatedAtUtc,
    bundleGeneratedAtUtc: base.bundleGeneratedAtUtc ?? active.generatedAtUtc,
    sourcePath: base.sourcePath ?? active.sourcePath,
    failures: [...base.failures, ...active.failures],
  };
}

export async function loadServingRuntimePublicationBundleMeta(): Promise<RuntimeServingPublicationBundleMeta> {
  const latest = await loadLatestRuntimeRefreshRunMeta();
  const active = await readLatestRuntimeDecisionMeta();

  return mapToServingMeta(
    {
      ...latest,
      runId: latest.runId ?? active.runId,
      generatedAtUtc: latest.generatedAtUtc ?? active.generatedAtUtc,
      completedAtUtc: latest.completedAtUtc ?? active.generatedAtUtc,
      reportGeneratedAtUtc: latest.reportGeneratedAtUtc ?? active.generatedAtUtc,
      bundleGeneratedAtUtc: latest.bundleGeneratedAtUtc ?? active.generatedAtUtc,
      sourcePath: latest.sourcePath ?? active.sourcePath,
      failures: [...latest.failures, ...active.failures],
    },
    active.runId ?? latest.runId,
    active.generatedAtUtc ?? latest.generatedAtUtc,
  );
}
