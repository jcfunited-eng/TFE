import { loadServingRuntimePublicationBundleMeta } from "@/lib/runtime-publication-bundle";
import {
  postgresSourceBase,
  postgresSourcePath,
  resolveRuntimePostgresPool,
  resolveRuntimeSource,
  runtimeSourceIsPostgres,
  isPostgresConfigured,
  tableExists,
  toIsoOrNull,
  type AttemptFailure,
  RUNTIME_DECISIONS_TABLE,
  RUNTIME_DECISIONS_HISTORY_TABLE,
  RUNTIME_SYMBOLS_TABLE,
  RUNTIME_SYMBOLS_HISTORY_TABLE,
  RUNTIME_DECISION_PROVENANCE_TABLE,
} from "@/lib/runtime-db";
import type { ScreenerQuoteCacheRow } from "@/lib/screener-quote-cache";
import type { SnapshotRow } from "@/lib/uf-snapshot";
import type { Pool } from "pg";

const DEFAULT_RUNTIME_CACHE_TTL_MS = 60_000;
const DEFAULT_RUNTIME_READ_RETRY_ATTEMPTS = 2;
const DEFAULT_RUNTIME_READ_RETRY_DELAY_MS = 120;

type RuntimeSnapshotRowRecord = {
  ticker: string;
  snapshot_row_json: unknown;
  run_id: string | null;
  generated_at_utc: string | Date | null;
};

type RuntimeSymbolRowRecord = {
  ticker: string;
  profile_json: unknown;
  run_id: string | null;
  generated_at_utc: string | Date | null;
};

type RuntimeSourceMeta = {
  runId: string | null;
  generatedAtUtc: string | null;
};

type RuntimeServingBundleSelection = {
  runId: string | null;
  generatedAtUtc: string | null;
  activeRuntimeRunId: string | null;
  fallbackApplied: boolean;
  failures: AttemptFailure[];
};

type RuntimeDecisionProvenanceRowRecord = {
  ticker: string;
  run_id: string | null;
  snapshot_row_digest_sha256: string | null;
  snapshot_timestamp_utc: string | Date | null;
  runtime_sync_completed_utc: string | Date | null;
  decision_timestamp_utc: string | Date | null;
  policy_artifact_id: string | null;
  policy_artifact_hash_sha256: string | null;
  policy_source_mode: string | null;
  candidate_key_chain_json: unknown;
  matched_key: string | null;
  match_level: string | null;
  fallback_ladder_level: string | null;
  matched_exact_bool: boolean | null;
  fallback_used: boolean | null;
  fallback_reason_code: string | null;
  decision: string | null;
  decision_reason_code: string | null;
  anomaly_flags_used_json: unknown;
  structural_recency_components_used_json: unknown;
  epoch_components_used_json: unknown;
  coverage_class: string | null;
  provenance_schema_version: string | null;
  writer_component: string | null;
  writer_build_hash: string | null;
  cp_profile: string | null;
  provenance_generated_utc: string | Date | null;
  provenance_valid: boolean | null;
};

export type RuntimeSnapshotLoadResult = {
  rows: SnapshotRow[];
  sourcePath: string | null;
  attemptedPaths: string[];
  failures: AttemptFailure[];
  dataSource: "postgres";
  runId: string | null;
  generatedAtUtc: string | null;
};

export type RuntimeQuoteLoadResult = {
  quotes: Record<string, ScreenerQuoteCacheRow>;
  sourcePath: string | null;
  failures: AttemptFailure[];
  dataSource: "postgres";
  runId: string | null;
  generatedAtUtc: string | null;
};

export type RuntimeDecisionPersistedProvenance = {
  ticker: string;
  runId: string;
  snapshotRowDigestSha256: string | null;
  snapshotTimestampUtc: string | null;
  runtimeSyncCompletedUtc: string | null;
  decisionTimestampUtc: string | null;
  policyArtifactId: string | null;
  policyArtifactHashSha256: string | null;
  policySourceMode: string | null;
  candidateKeyChain: string[];
  matchedKey: string | null;
  matchLevel: string | null;
  fallbackLadderLevel: string | null;
  matchedExact: boolean;
  fallbackUsed: boolean;
  fallbackReasonCode: string | null;
  decision: string | null;
  decisionReasonCode: string | null;
  anomalyFlagsUsed: Record<string, unknown>;
  structuralRecencyComponentsUsed: Record<string, unknown>;
  epochComponentsUsed: Record<string, unknown>;
  coverageClass: string | null;
  provenanceSchemaVersion: string | null;
  writerComponent: string | null;
  writerBuildHash: string | null;
  cpProfile: string | null;
  provenanceGeneratedUtc: string | null;
  provenanceValid: boolean;
};

export type RuntimeDecisionProvenanceLoadResult = {
  rows: Record<string, RuntimeDecisionPersistedProvenance>;
  sourcePath: string | null;
  failures: AttemptFailure[];
  dataSource: "postgres";
  runId: string | null;
  generatedAtUtc: string | null;
};

type SnapshotCacheEntry = {
  loadedAtMs: number;
  result: RuntimeSnapshotLoadResult;
};

type QuoteCacheEntry = {
  loadedAtMs: number;
  result: RuntimeQuoteLoadResult;
};

let snapshotCache: SnapshotCacheEntry | null = null;
let quoteCache: QuoteCacheEntry | null = null;
let snapshotLoadInFlight: Promise<RuntimeSnapshotLoadResult> | null = null;
let quoteLoadInFlight: Promise<RuntimeQuoteLoadResult> | null = null;

function readBoundedIntFromEnv(name: string, fallback: number, min: number, max: number): number {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) return fallback;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return fallback;
  const whole = Math.floor(parsed);
  if (whole < min || whole > max) return fallback;
  return whole;
}

function runtimeCacheTtlMs(): number {
  return readBoundedIntFromEnv(
    "TFE_RUNTIME_POSTGRES_CACHE_TTL_MS",
    DEFAULT_RUNTIME_CACHE_TTL_MS,
    0,
    10 * 60 * 1000,
  );
}

function runtimeReadRetryAttempts(): number {
  return readBoundedIntFromEnv(
    "TFE_RUNTIME_POSTGRES_READ_RETRY_ATTEMPTS",
    DEFAULT_RUNTIME_READ_RETRY_ATTEMPTS,
    1,
    5,
  );
}

function runtimeReadRetryDelayMs(): number {
  return readBoundedIntFromEnv(
    "TFE_RUNTIME_POSTGRES_READ_RETRY_DELAY_MS",
    DEFAULT_RUNTIME_READ_RETRY_DELAY_MS,
    25,
    2000,
  );
}

function cacheIsFresh(loadedAtMs: number, ttlMs: number): boolean {
  if (ttlMs <= 0) return false;
  return Date.now() - loadedAtMs <= ttlMs;
}

function delayMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseSnapshotRow(payload: unknown): SnapshotRow | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  return payload as SnapshotRow;
}

function parseQuoteRow(payload: unknown): ScreenerQuoteCacheRow | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  return payload as ScreenerQuoteCacheRow;
}

function parseJsonRecord(payload: unknown): Record<string, unknown> {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return {};
  return payload as Record<string, unknown>;
}

function parseStringArray(payload: unknown): string[] {
  if (!Array.isArray(payload)) return [];
  const out: string[] = [];
  for (const item of payload) {
    const text = String(item ?? "").trim();
    if (!text) continue;
    out.push(text);
  }
  return out;
}

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

async function readRuntimeSourceMeta(
  pool: Pool,
  tableName: string,
  runId: string | null = null,
): Promise<RuntimeSourceMeta> {
  const normalizedRunId = String(runId ?? "").trim();
  const result = normalizedRunId
    ? await pool.query<{ run_id: string | null; generated_at_utc: string | Date | null }>(
      `
        SELECT run_id, generated_at_utc
        FROM ${tableName}
        WHERE run_id = $1
        ORDER BY generated_at_utc DESC NULLS LAST, ticker ASC
        LIMIT 1
      `,
      [normalizedRunId],
    )
    : await pool.query<{ run_id: string | null; generated_at_utc: string | Date | null }>(
      `
        SELECT run_id, generated_at_utc
        FROM ${tableName}
        ORDER BY generated_at_utc DESC NULLS LAST, ticker ASC
        LIMIT 1
      `,
    );

  if (result.rows.length === 0) {
    return { runId: null, generatedAtUtc: null };
  }

  const row = result.rows[0];
  return {
    runId: typeof row.run_id === "string" && row.run_id.trim() ? row.run_id : null,
    generatedAtUtc: toIsoOrNull(row.generated_at_utc),
  };
}

async function resolveServingBundleSelection(): Promise<RuntimeServingBundleSelection> {
  const serving = await loadServingRuntimePublicationBundleMeta();
  const failures: AttemptFailure[] = serving.failures.map((failure) => ({
    path: failure.path,
    reason: failure.reason,
  }));

  return {
    runId: serving.runId,
    generatedAtUtc: serving.generatedAtUtc,
    activeRuntimeRunId: serving.activeRuntimeRunId,
    fallbackApplied: serving.fallbackApplied,
    failures,
  };
}

function failuresContainNonRetriableConfigReason(failures: AttemptFailure[]): boolean {
  return failures.some((failure) => {
    const reason = String(failure.reason ?? "").toLowerCase();
    return (
      reason.includes("expected 'postgres'") ||
      reason.includes("not fully configured") ||
      reason.includes("missing required database env var") ||
      reason.includes("validated publication bundle")
    );
  });
}

function shouldRetrySnapshotLoad(result: RuntimeSnapshotLoadResult): boolean {
  if (result.sourcePath && result.rows.length > 0) return false;
  if (result.failures.length === 0) return false;
  if (failuresContainNonRetriableConfigReason(result.failures)) return false;
  return true;
}

function shouldRetryQuoteLoad(result: RuntimeQuoteLoadResult): boolean {
  if (result.sourcePath && Object.keys(result.quotes).length > 0) return false;
  if (result.failures.length === 0) return false;
  if (failuresContainNonRetriableConfigReason(result.failures)) return false;
  return true;
}

async function loadRuntimeSnapshotRowsFromPostgresRawWithRetry(): Promise<RuntimeSnapshotLoadResult> {
  const attempts = runtimeReadRetryAttempts();
  const retryDelayMs = runtimeReadRetryDelayMs();
  let latestResult: RuntimeSnapshotLoadResult | null = null;

  for (let attemptIndex = 0; attemptIndex < attempts; attemptIndex += 1) {
    const current = await loadRuntimeSnapshotRowsFromPostgresRaw();
    latestResult = current;

    if (current.sourcePath && current.rows.length > 0) {
      return current;
    }

    const shouldRetry = attemptIndex < attempts - 1 && shouldRetrySnapshotLoad(current);
    if (!shouldRetry) {
      return current;
    }

    await delayMs(retryDelayMs);
  }

  return (
    latestResult ?? {
      rows: [],
      sourcePath: null,
      attemptedPaths: [`${postgresSourceBase()}#${RUNTIME_DECISIONS_TABLE}`],
      failures: [
        {
          path: `${postgresSourceBase()}#${RUNTIME_DECISIONS_TABLE}`,
          reason: "Runtime snapshot retry loader returned no result.",
        },
      ],
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    }
  );
}

async function loadRuntimeQuoteCacheFromPostgresRawWithRetry(): Promise<RuntimeQuoteLoadResult> {
  const attempts = runtimeReadRetryAttempts();
  const retryDelayMs = runtimeReadRetryDelayMs();
  let latestResult: RuntimeQuoteLoadResult | null = null;

  for (let attemptIndex = 0; attemptIndex < attempts; attemptIndex += 1) {
    const current = await loadRuntimeQuoteCacheFromPostgresRaw();
    latestResult = current;

    if (current.sourcePath && Object.keys(current.quotes).length > 0) {
      return current;
    }

    const shouldRetry = attemptIndex < attempts - 1 && shouldRetryQuoteLoad(current);
    if (!shouldRetry) {
      return current;
    }

    await delayMs(retryDelayMs);
  }

  return (
    latestResult ?? {
      quotes: {},
      sourcePath: null,
      failures: [
        {
          path: `${postgresSourceBase()}#${RUNTIME_SYMBOLS_TABLE}`,
          reason: "Runtime quote retry loader returned no result.",
        },
      ],
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    }
  );
}

async function loadRuntimeSnapshotRowsFromPostgresRaw(): Promise<RuntimeSnapshotLoadResult> {
  const defaultSourcePath = `${postgresSourceBase()}#${RUNTIME_DECISIONS_TABLE}`;
  const attemptedPaths = [defaultSourcePath];
  const failures: AttemptFailure[] = [];

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: defaultSourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return {
      rows: [],
      sourcePath: null,
      attemptedPaths,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: defaultSourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return {
      rows: [],
      sourcePath: null,
      attemptedPaths,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const servingBundle = await resolveServingBundleSelection();
    failures.push(...servingBundle.failures);

    const selectedRunId = String(servingBundle.runId ?? "").trim();
    if (!selectedRunId) {
      failures.push({
        path: defaultSourcePath,
        reason: "No validated publication bundle is available for runtime snapshot serving.",
      });
      return {
        rows: [],
        sourcePath: null,
        attemptedPaths,
        failures,
        dataSource: "postgres",
        runId: null,
        generatedAtUtc: null,
      };
    }

    const useHistoryTable = servingBundle.activeRuntimeRunId !== selectedRunId;
    const selectedTable = useHistoryTable ? RUNTIME_DECISIONS_HISTORY_TABLE : RUNTIME_DECISIONS_TABLE;
    const sourcePath = `${postgresSourceBase()}#${selectedTable}?run_id=${selectedRunId}`;
    attemptedPaths.push(sourcePath);

    if (useHistoryTable) {
      const historyExists = await tableExists(pool, selectedTable);
      if (!historyExists) {
        failures.push({
          path: sourcePath,
          reason: `Fallback snapshot table '${selectedTable}' does not exist.`,
        });
        return {
          rows: [],
          sourcePath: null,
          attemptedPaths,
          failures,
          dataSource: "postgres",
          runId: selectedRunId,
          generatedAtUtc: servingBundle.generatedAtUtc,
        };
      }
    }

    const [rowsResult, meta] = await Promise.all([
      pool.query<RuntimeSnapshotRowRecord>(
        `
          SELECT ticker, snapshot_row_json, run_id, generated_at_utc
          FROM ${selectedTable}
          WHERE run_id = $1
          ORDER BY ticker ASC
        `,
        [selectedRunId],
      ),
      readRuntimeSourceMeta(pool, selectedTable, selectedRunId),
    ]);

    const rows: SnapshotRow[] = [];
    for (const record of rowsResult.rows) {
      const ticker = normalizeTicker(record.ticker);
      if (!ticker) continue;
      const parsed = parseSnapshotRow(record.snapshot_row_json);
      if (!parsed) continue;
      rows.push({
        ...parsed,
        ticker,
      });
    }

    if (rows.length === 0) {
      failures.push({
        path: sourcePath,
        reason: "Runtime decisions table is empty.",
      });
      return {
        rows: [],
        sourcePath: null,
        attemptedPaths,
        failures,
        dataSource: "postgres",
        runId: selectedRunId,
        generatedAtUtc: servingBundle.generatedAtUtc ?? meta.generatedAtUtc,
      };
    }

    return {
      rows,
      sourcePath,
      attemptedPaths,
      failures,
      dataSource: "postgres",
      runId: selectedRunId,
      generatedAtUtc: servingBundle.generatedAtUtc ?? meta.generatedAtUtc,
    };
  } catch (error) {
    failures.push({
      path: defaultSourcePath,
      reason: error instanceof Error ? error.message : "Unknown runtime decisions query error.",
    });
    return {
      rows: [],
      sourcePath: null,
      attemptedPaths,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }
}

async function loadRuntimeQuoteCacheFromPostgresRaw(): Promise<RuntimeQuoteLoadResult> {
  const defaultSourcePath = `${postgresSourceBase()}#${RUNTIME_SYMBOLS_TABLE}`;
  const failures: AttemptFailure[] = [];

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: defaultSourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return {
      quotes: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: defaultSourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return {
      quotes: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const servingBundle = await resolveServingBundleSelection();
    failures.push(...servingBundle.failures);

    const selectedRunId = String(servingBundle.runId ?? "").trim();
    if (!selectedRunId) {
      failures.push({
        path: defaultSourcePath,
        reason: "No validated publication bundle is available for runtime quote serving.",
      });
      return {
        quotes: {},
        sourcePath: null,
        failures,
        dataSource: "postgres",
        runId: null,
        generatedAtUtc: null,
      };
    }

    const useHistoryTable = servingBundle.activeRuntimeRunId !== selectedRunId;
    const selectedTable = useHistoryTable ? RUNTIME_SYMBOLS_HISTORY_TABLE : RUNTIME_SYMBOLS_TABLE;
    const sourcePath = `${postgresSourceBase()}#${selectedTable}?run_id=${selectedRunId}`;

    if (useHistoryTable) {
      const historyExists = await tableExists(pool, selectedTable);
      if (!historyExists) {
        failures.push({
          path: sourcePath,
          reason: `Fallback quote table '${selectedTable}' does not exist.`,
        });
        return {
          quotes: {},
          sourcePath: null,
          failures,
          dataSource: "postgres",
          runId: selectedRunId,
          generatedAtUtc: servingBundle.generatedAtUtc,
        };
      }
    }

    const [rowsResult, meta] = await Promise.all([
      pool.query<RuntimeSymbolRowRecord>(
        `
          SELECT ticker, profile_json, run_id, generated_at_utc
          FROM ${selectedTable}
          WHERE run_id = $1
          ORDER BY ticker ASC
        `,
        [selectedRunId],
      ),
      readRuntimeSourceMeta(pool, selectedTable, selectedRunId),
    ]);

    const quotes: Record<string, ScreenerQuoteCacheRow> = {};
    for (const record of rowsResult.rows) {
      const ticker = normalizeTicker(record.ticker);
      if (!ticker) continue;
      const parsed = parseQuoteRow(record.profile_json);
      if (!parsed) continue;
      quotes[ticker] = parsed;
    }

    if (Object.keys(quotes).length === 0) {
      failures.push({
        path: sourcePath,
        reason: "Runtime symbols table has no profile rows.",
      });
      return {
        quotes: {},
        sourcePath: null,
        failures,
        dataSource: "postgres",
        runId: selectedRunId,
        generatedAtUtc: servingBundle.generatedAtUtc ?? meta.generatedAtUtc,
      };
    }

    return {
      quotes,
      sourcePath,
      failures,
      dataSource: "postgres",
      runId: selectedRunId,
      generatedAtUtc: servingBundle.generatedAtUtc ?? meta.generatedAtUtc,
    };
  } catch (error) {
    failures.push({
      path: defaultSourcePath,
      reason: error instanceof Error ? error.message : "Unknown runtime symbols query error.",
    });
    return {
      quotes: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }
}

export async function loadRuntimeSnapshotRowsFromPostgres(): Promise<RuntimeSnapshotLoadResult> {
  const ttlMs = runtimeCacheTtlMs();
  if (snapshotCache && cacheIsFresh(snapshotCache.loadedAtMs, ttlMs)) {
    return snapshotCache.result;
  }

  if (snapshotLoadInFlight) {
    return snapshotLoadInFlight;
  }

  snapshotLoadInFlight = (async () => {
    const current = await loadRuntimeSnapshotRowsFromPostgresRawWithRetry();

    if (current.sourcePath && current.rows.length > 0) {
      snapshotCache = {
        loadedAtMs: Date.now(),
        result: current,
      };
    } else {
      snapshotCache = null;
    }

    return current;
  })();

  try {
    return await snapshotLoadInFlight;
  } finally {
    snapshotLoadInFlight = null;
  }
}

export async function loadRuntimeQuoteCacheFromPostgres(): Promise<RuntimeQuoteLoadResult> {
  const ttlMs = runtimeCacheTtlMs();
  if (quoteCache && cacheIsFresh(quoteCache.loadedAtMs, ttlMs)) {
    return quoteCache.result;
  }

  if (quoteLoadInFlight) {
    return quoteLoadInFlight;
  }

  quoteLoadInFlight = (async () => {
    const current = await loadRuntimeQuoteCacheFromPostgresRawWithRetry();

    if (current.sourcePath && Object.keys(current.quotes).length > 0) {
      quoteCache = {
        loadedAtMs: Date.now(),
        result: current,
      };
    } else {
      quoteCache = null;
    }

    return current;
  })();

  try {
    return await quoteLoadInFlight;
  } finally {
    quoteLoadInFlight = null;
  }
}

export async function loadRuntimeDecisionProvenanceByRunIdFromPostgres(
  runId: string | null,
): Promise<RuntimeDecisionProvenanceLoadResult> {
  const normalizedRunId = String(runId ?? "").trim();
  const sourcePath = `${postgresSourceBase()}#${RUNTIME_DECISION_PROVENANCE_TABLE}${normalizedRunId ? `?run_id=${normalizedRunId}` : ""}`;
  const failures: AttemptFailure[] = [];

  if (!runtimeSourceIsPostgres()) {
    failures.push({
      path: sourcePath,
      reason: `Runtime source is '${resolveRuntimeSource()}'; expected 'postgres'.`,
    });
    return {
      rows: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: normalizedRunId || null,
      generatedAtUtc: null,
    };
  }

  if (!isPostgresConfigured()) {
    failures.push({
      path: sourcePath,
      reason: "Postgres runtime source required, but PGHOST/PGDATABASE/PGUSER/PGPASSWORD is not fully configured.",
    });
    return {
      rows: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: normalizedRunId || null,
      generatedAtUtc: null,
    };
  }

  if (!normalizedRunId) {
    failures.push({
      path: sourcePath,
      reason: "Run ID is required to load persisted decision provenance.",
    });
    return {
      rows: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: null,
      generatedAtUtc: null,
    };
  }

  try {
    const pool = resolveRuntimePostgresPool();
    const provenanceTableExists = await tableExists(pool, RUNTIME_DECISION_PROVENANCE_TABLE);
    if (!provenanceTableExists) {
      failures.push({
        path: sourcePath,
        reason: `Persisted provenance table '${RUNTIME_DECISION_PROVENANCE_TABLE}' does not exist.`,
      });
      return {
        rows: {},
        sourcePath: null,
        failures,
        dataSource: "postgres",
        runId: normalizedRunId,
        generatedAtUtc: null,
      };
    }

    const result = await pool.query<RuntimeDecisionProvenanceRowRecord>(
      `
        SELECT
          ticker,
          run_id,
          snapshot_row_digest_sha256,
          snapshot_timestamp_utc,
          runtime_sync_completed_utc,
          decision_timestamp_utc,
          policy_artifact_id,
          policy_artifact_hash_sha256,
          policy_source_mode,
          candidate_key_chain_json,
          matched_key,
          match_level,
          fallback_ladder_level,
          matched_exact_bool,
          fallback_used,
          fallback_reason_code,
          decision,
          decision_reason_code,
          anomaly_flags_used_json,
          structural_recency_components_used_json,
          epoch_components_used_json,
          coverage_class,
          provenance_schema_version,
          writer_component,
          writer_build_hash,
          cp_profile,
          provenance_generated_utc,
          provenance_valid
        FROM ${RUNTIME_DECISION_PROVENANCE_TABLE}
        WHERE run_id = $1
        ORDER BY ticker ASC
      `,
      [normalizedRunId],
    );

    if (result.rows.length === 0) {
      failures.push({
        path: sourcePath,
        reason: `No persisted decision provenance rows for run_id='${normalizedRunId}'.`,
      });
      return {
        rows: {},
        sourcePath: null,
        failures,
        dataSource: "postgres",
        runId: normalizedRunId,
        generatedAtUtc: null,
      };
    }

    const rows: Record<string, RuntimeDecisionPersistedProvenance> = {};
    let latestGeneratedAtUtc: string | null = null;

    for (const record of result.rows) {
      const ticker = normalizeTicker(record.ticker);
      if (!ticker) continue;

      const provenanceGeneratedAtUtc = toIsoOrNull(record.provenance_generated_utc);
      if (provenanceGeneratedAtUtc) {
        if (!latestGeneratedAtUtc || Date.parse(provenanceGeneratedAtUtc) > Date.parse(latestGeneratedAtUtc)) {
          latestGeneratedAtUtc = provenanceGeneratedAtUtc;
        }
      }

      rows[ticker] = {
        ticker,
        runId: String(record.run_id ?? normalizedRunId),
        snapshotRowDigestSha256: typeof record.snapshot_row_digest_sha256 === "string" ? record.snapshot_row_digest_sha256 : null,
        snapshotTimestampUtc: toIsoOrNull(record.snapshot_timestamp_utc),
        runtimeSyncCompletedUtc: toIsoOrNull(record.runtime_sync_completed_utc),
        decisionTimestampUtc: toIsoOrNull(record.decision_timestamp_utc),
        policyArtifactId: typeof record.policy_artifact_id === "string" ? record.policy_artifact_id : null,
        policyArtifactHashSha256:
          typeof record.policy_artifact_hash_sha256 === "string" ? record.policy_artifact_hash_sha256 : null,
        policySourceMode: typeof record.policy_source_mode === "string" ? record.policy_source_mode : null,
        candidateKeyChain: parseStringArray(record.candidate_key_chain_json),
        matchedKey: typeof record.matched_key === "string" ? record.matched_key : null,
        matchLevel: typeof record.match_level === "string" ? record.match_level : null,
        fallbackLadderLevel:
          typeof record.fallback_ladder_level === "string" ? record.fallback_ladder_level : null,
        matchedExact: record.matched_exact_bool === true,
        fallbackUsed: record.fallback_used === true,
        fallbackReasonCode: typeof record.fallback_reason_code === "string" ? record.fallback_reason_code : null,
        decision: typeof record.decision === "string" ? record.decision : null,
        decisionReasonCode: typeof record.decision_reason_code === "string" ? record.decision_reason_code : null,
        anomalyFlagsUsed: parseJsonRecord(record.anomaly_flags_used_json),
        structuralRecencyComponentsUsed: parseJsonRecord(record.structural_recency_components_used_json),
        epochComponentsUsed: parseJsonRecord(record.epoch_components_used_json),
        coverageClass: typeof record.coverage_class === "string" ? record.coverage_class : null,
        provenanceSchemaVersion:
          typeof record.provenance_schema_version === "string" ? record.provenance_schema_version : null,
        writerComponent: typeof record.writer_component === "string" ? record.writer_component : null,
        writerBuildHash: typeof record.writer_build_hash === "string" ? record.writer_build_hash : null,
        cpProfile: typeof record.cp_profile === "string" ? record.cp_profile : null,
        provenanceGeneratedUtc: provenanceGeneratedAtUtc,
        provenanceValid: record.provenance_valid === true,
      };
    }

    return {
      rows,
      sourcePath,
      failures,
      dataSource: "postgres",
      runId: normalizedRunId,
      generatedAtUtc: latestGeneratedAtUtc,
    };
  } catch (error) {
    failures.push({
      path: sourcePath,
      reason: error instanceof Error ? error.message : "Unknown persisted provenance query error.",
    });
    return {
      rows: {},
      sourcePath: null,
      failures,
      dataSource: "postgres",
      runId: normalizedRunId,
      generatedAtUtc: null,
    };
  }
}
