import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { readAdminRefreshPersist, writeAdminRefreshPersist } from "@/lib/admin-refresh-persist";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

const ROOT_DIR = resolveWorkspaceRoot();
const L5_LATEST_PATH = path.join(ROOT_DIR, "l5_policy_learning_latest.json");
const L5_OUTPUT_DIR = path.join(ROOT_DIR, "backups", "runtime", "l5_policy_learning");
const LIVE_ACCURACY_DIR = path.join(ROOT_DIR, "backups", "runtime", "model_accuracy");
const LIVE_ACCURACY_EPOCH_PATH = path.join(LIVE_ACCURACY_DIR, "live_accuracy_epoch.json");
const LIVE_ACCURACY_EPOCH_PERSIST_KEY = "model_accuracy_live_epoch_v1";
const PROVENANCE_PERSISTENCE_PATH = path.join(ROOT_DIR, "current_l5_provenance_persistence_latest.json");
const PROVENANCE_PARITY_PATH = path.join(ROOT_DIR, "provenance_persistence_parity_latest.json");
const HORIZONS = [5, 20, 60] as const;
const HORIZON_MIN_DAYS: Record<(typeof HORIZONS)[number], number> = {
  5: 5,
  20: 20,
  60: 60,
};

type JsonRecord = Record<string, unknown>;

type HorizonPayload = {
  horizon_days: (typeof HORIZONS)[number];
  evaluations: number | null;
  beat_benchmark_pct: number | null;
  beat_benchmark_raw_pct: number | null;
  action_mean_return_pct: number | null;
  excess_mean_return_pct: number | null;
  excess_positive_rate_pct: number | null;
  mapped_rate_pct: number | null;
};

type HorizonMaturity = {
  horizon_days: (typeof HORIZONS)[number];
  min_days: number;
  days_since_live_epoch: number;
  ready: boolean;
};

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringOrNull(value: unknown): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text : null;
}

function resolveFilePath(rawPath: string): string {
  if (path.isAbsolute(rawPath)) return rawPath;
  return path.resolve(ROOT_DIR, rawPath);
}

function isoNow(): string {
  return new Date().toISOString();
}

function parseIsoMs(value: string | null): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function wholeDaysBetween(startIso: string, endIso: string): number {
  const startMs = parseIsoMs(startIso);
  const endMs = parseIsoMs(endIso);
  if (startMs === null || endMs === null || endMs < startMs) return 0;
  return Math.floor((endMs - startMs) / (24 * 60 * 60 * 1000));
}

function buildHorizonMaturity(daysSinceLiveEpoch: number): HorizonMaturity[] {
  return HORIZONS.map((horizonDays) => {
    const minDays = HORIZON_MIN_DAYS[horizonDays];
    return {
      horizon_days: horizonDays,
      min_days: minDays,
      days_since_live_epoch: daysSinceLiveEpoch,
      ready: daysSinceLiveEpoch >= minDays,
    };
  });
}

function applyHorizonMaturity(horizons: HorizonPayload[], daysSinceLiveEpoch: number) {
  const horizonMaturity = buildHorizonMaturity(daysSinceLiveEpoch);
  const readyHorizons = new Set(horizonMaturity.filter((item) => item.ready).map((item) => item.horizon_days));
  const visibleHorizons = horizons.filter((item) => readyHorizons.has(item.horizon_days));
  const withheldHorizonDays = horizonMaturity.filter((item) => !item.ready).map((item) => item.horizon_days);

  return {
    horizonMaturity,
    visibleHorizons,
    withheldHorizonDays,
    liveEligible: visibleHorizons.length > 0,
  };
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

async function readJsonRecord(filePath: string): Promise<JsonRecord> {
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`JSON payload is not an object: ${filePath}`);
  }
  return parsed as JsonRecord;
}

async function readOptionalJsonRecord(filePath: string): Promise<JsonRecord | null> {
  try {
    await stat(filePath);
    return await readJsonRecord(filePath);
  } catch {
    return null;
  }
}

function earlierIso(a: string | null, b: string | null): string | null {
  const aMs = parseIsoMs(a);
  const bMs = parseIsoMs(b);
  if (aMs === null) return b;
  if (bMs === null) return a;
  return aMs <= bMs ? a : b;
}

async function readPersistedLiveAccuracyEpochUtc(): Promise<string | null> {
  const persisted = await readAdminRefreshPersist(LIVE_ACCURACY_EPOCH_PERSIST_KEY);
  return stringOrNull(persisted?.started_at_utc);
}

async function readLocalLiveAccuracyEpochUtc(): Promise<string | null> {
  try {
    const parsed = await readJsonRecord(LIVE_ACCURACY_EPOCH_PATH);
    return stringOrNull(parsed.started_at_utc);
  } catch {
    return null;
  }
}

async function readLatestReportGeneratedAtUtc(reportPath: string | null): Promise<string | null> {
  if (!reportPath) return null;
  const parsed = await readOptionalJsonRecord(reportPath);
  return stringOrNull(parsed?.generated_at_utc);
}

async function persistLiveAccuracyEpochUtc(startedAtUtc: string): Promise<void> {
  await writeAdminRefreshPersist(LIVE_ACCURACY_EPOCH_PERSIST_KEY, {
    started_at_utc: startedAtUtc,
    updated_at_utc: isoNow(),
    source: "model_accuracy_route",
  });

  await mkdir(LIVE_ACCURACY_DIR, { recursive: true });
  await writeFile(
    LIVE_ACCURACY_EPOCH_PATH,
    `${JSON.stringify({ started_at_utc: startedAtUtc }, null, 2)}\n`,
    "utf-8",
  );
}

async function resolveLiveAccuracyEpochUtc(reportPath: string | null): Promise<string> {
  const [
    persistedEpochUtc,
    localEpochUtc,
    provenancePersistence,
    provenanceParity,
    latestReportGeneratedAtUtc,
  ] = await Promise.all([
    readPersistedLiveAccuracyEpochUtc(),
    readLocalLiveAccuracyEpochUtc(),
    readOptionalJsonRecord(PROVENANCE_PERSISTENCE_PATH),
    readOptionalJsonRecord(PROVENANCE_PARITY_PATH),
    readLatestReportGeneratedAtUtc(reportPath),
  ]);

  let resolvedEpochUtc: string | null = null;
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, persistedEpochUtc);
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, localEpochUtc);
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, latestReportGeneratedAtUtc);
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, stringOrNull(provenancePersistence?.generated_at_utc));
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, stringOrNull(provenancePersistence?.latest_provenance_generated_utc));
  resolvedEpochUtc = earlierIso(resolvedEpochUtc, stringOrNull(provenanceParity?.generated_at_utc));

  const startedAtUtc = resolvedEpochUtc ?? isoNow();

  if (persistedEpochUtc !== startedAtUtc || localEpochUtc !== startedAtUtc) {
    await persistLiveAccuracyEpochUtc(startedAtUtc);
  }

  return startedAtUtc;
}

function mapComparisonFallbackHorizon(report: JsonRecord, horizon: (typeof HORIZONS)[number]): HorizonPayload {
  const comparison = (report.comparison as JsonRecord | undefined) ?? {};
  const rowsRaw = comparison.horizon_rows;
  const rows = Array.isArray(rowsRaw) ? rowsRaw : [];
  const row = rows.find((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return false;
    return numberOrNull((item as JsonRecord).horizon) === horizon;
  }) as JsonRecord | undefined;

  const excessMean = numberOrNull(row?.current_excess_mean_anomaly_accounted);
  return {
    horizon_days: horizon,
    evaluations: null,
    beat_benchmark_pct: numberOrNull(row?.current_outcome_over_index_pct_anomaly_accounted),
    beat_benchmark_raw_pct: null,
    action_mean_return_pct: null,
    excess_mean_return_pct: excessMean === null ? null : excessMean * 100,
    excess_positive_rate_pct: null,
    mapped_rate_pct: numberOrNull(row?.current_mapped_rate_pct),
  };
}

function buildCurrentEvalHorizon(currentEval: JsonRecord, horizon: (typeof HORIZONS)[number]): HorizonPayload {
  const horizonSummaries = (currentEval.horizon_summaries as JsonRecord | undefined) ?? {};
  const summary = (horizonSummaries[String(horizon)] as JsonRecord | undefined) ?? {};
  const action = (summary.action_anomaly_accounted as JsonRecord | undefined) ?? {};
  const excess = (summary.excess_vs_spy_anomaly_accounted as JsonRecord | undefined) ?? {};
  const mapping = (summary.policy_mapping as JsonRecord | undefined) ?? {};

  const actionMean = numberOrNull(action.mean);
  const excessMean = numberOrNull(excess.mean);

  return {
    horizon_days: horizon,
    evaluations: numberOrNull(summary.evaluations),
    beat_benchmark_pct: numberOrNull(summary.outcome_over_index_pct_anomaly_accounted),
    beat_benchmark_raw_pct: numberOrNull(summary.outcome_over_index_pct),
    action_mean_return_pct: actionMean === null ? null : actionMean * 100,
    excess_mean_return_pct: excessMean === null ? null : excessMean * 100,
    excess_positive_rate_pct: (() => {
      const value = numberOrNull(excess.pct_positive);
      return value === null ? null : value * 100;
    })(),
    mapped_rate_pct: numberOrNull(mapping.mapped_rate_pct),
  };
}

async function resolveLatestReportPath(): Promise<string | null> {
  try {
    await stat(L5_LATEST_PATH);
    return L5_LATEST_PATH;
  } catch {
    // fallback to newest stamped report file
  }

  try {
    const entries = await readdir(L5_OUTPUT_DIR, { withFileTypes: true });
    const candidates = entries
      .filter((entry) => entry.isFile() && entry.name.startsWith("l5-policy-learning-report-") && entry.name.endsWith(".json"))
      .map((entry) => entry.name);

    if (candidates.length === 0) return null;

    const ranked = await Promise.all(
      candidates.map(async (name) => {
        const fullPath = path.join(L5_OUTPUT_DIR, name);
        const fileStat = await stat(fullPath);
        return { fullPath, mtimeMs: fileStat.mtimeMs };
      }),
    );

    ranked.sort((a, b) => b.mtimeMs - a.mtimeMs);
    return ranked[0]?.fullPath ?? null;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  try {
    const nowUtc = isoNow();
    const reportPath = await resolveLatestReportPath();
    const liveEpochStartUtc = await resolveLiveAccuracyEpochUtc(reportPath);
    const daysSinceLiveEpoch = wholeDaysBetween(liveEpochStartUtc, nowUtc);
    const epochMaturity = applyHorizonMaturity(HORIZONS.map((horizon) => ({
      horizon_days: horizon,
      evaluations: null,
      beat_benchmark_pct: null,
      beat_benchmark_raw_pct: null,
      action_mean_return_pct: null,
      excess_mean_return_pct: null,
      excess_positive_rate_pct: null,
      mapped_rate_pct: null,
    })), daysSinceLiveEpoch);

    if (!epochMaturity.liveEligible) {
      return NextResponse.json({
        exists: true,
        source: "live_maturity_gate",
        generatedAtUtc: null,
        reportPath: L5_LATEST_PATH,
        currentEvalPath: null,
        reportUpdatedAtUtc: null,
        updatedAtUtc: nowUtc,
        liveEligible: false,
        liveEpochStartUtc,
        daysSinceLiveEpoch,
        liveMinDays: HORIZON_MIN_DAYS[5],
        horizonMaturity: epochMaturity.horizonMaturity,
        withheldHorizonDays: epochMaturity.withheldHorizonDays,
        horizons: [],
        methodology:
          "Forward-live decision accuracy is withheld until horizon maturity to avoid day-0/day-1 false precision.",
        message: `Live accuracy gate active: day ${daysSinceLiveEpoch} of ${HORIZON_MIN_DAYS[5]} for 5D (20D/60D unlock later).`,
      });
    }

    if (!reportPath) {
      return NextResponse.json({
        exists: false,
        reportPath: L5_LATEST_PATH,
        currentEvalPath: null,
        generatedAtUtc: null,
        liveEligible: true,
        liveEpochStartUtc,
        daysSinceLiveEpoch,
        liveMinDays: HORIZON_MIN_DAYS[5],
        horizonMaturity: epochMaturity.horizonMaturity,
        withheldHorizonDays: epochMaturity.withheldHorizonDays,
        updatedAtUtc: null,
        horizons: [],
        error: "No L5 policy learning report found.",
      });
    }

    const [reportStat, report] = await Promise.all([stat(reportPath), readJsonRecord(reportPath)]);
    const artifacts = (report.artifacts as JsonRecord | undefined) ?? {};
    const currentEvalPathRaw = stringOrNull(artifacts.current_eval_path);
    const generatedAtUtc = stringOrNull(report.generated_at_utc);

    if (!currentEvalPathRaw) {
      const allHorizons = HORIZONS.map((horizon) => mapComparisonFallbackHorizon(report, horizon));
      const maturity = applyHorizonMaturity(allHorizons, daysSinceLiveEpoch);

      return NextResponse.json({
        exists: true,
        reportPath,
        currentEvalPath: null,
        generatedAtUtc,
        reportUpdatedAtUtc: reportStat.mtime.toISOString(),
        updatedAtUtc: reportStat.mtime.toISOString(),
        liveEligible: true,
        liveEpochStartUtc,
        daysSinceLiveEpoch,
        liveMinDays: HORIZON_MIN_DAYS[5],
        source: "comparison_horizon_rows",
        horizonMaturity: maturity.horizonMaturity,
        withheldHorizonDays: maturity.withheldHorizonDays,
        horizons: maturity.visibleHorizons,
        methodology:
          "Fallback from latest L5 comparison horizon rows when current runtime evaluation artifact is unavailable in runtime image. Visibility is maturity-gated by live epoch (5D/20D/60D).",
      });
    }

    const currentEvalPath = resolveFilePath(currentEvalPathRaw);
    try {
      const [currentEvalStat, currentEval] = await Promise.all([stat(currentEvalPath), readJsonRecord(currentEvalPath)]);
      const allHorizons = HORIZONS.map((horizon) => buildCurrentEvalHorizon(currentEval, horizon));
      const maturity = applyHorizonMaturity(allHorizons, daysSinceLiveEpoch);

      return NextResponse.json({
        exists: true,
        reportPath,
        currentEvalPath,
        generatedAtUtc,
        reportUpdatedAtUtc: reportStat.mtime.toISOString(),
        updatedAtUtc: currentEvalStat.mtime.toISOString(),
        liveEligible: true,
        liveEpochStartUtc,
        daysSinceLiveEpoch,
        liveMinDays: HORIZON_MIN_DAYS[5],
        source: "current_eval",
        horizonMaturity: maturity.horizonMaturity,
        withheldHorizonDays: maturity.withheldHorizonDays,
        horizons: maturity.visibleHorizons,
        methodology:
          "Realized horizon outcomes from current runtime policy evaluation against observed forward returns; beat_benchmark_pct means decisions outperforming benchmark at each horizon. Visibility is maturity-gated by live epoch (5D/20D/60D).",
      });
    } catch (error) {
      const fallbackError = error instanceof Error ? error.message : "Current runtime evaluation artifact unreadable.";
      const allHorizons = HORIZONS.map((horizon) => mapComparisonFallbackHorizon(report, horizon));
      const maturity = applyHorizonMaturity(allHorizons, daysSinceLiveEpoch);

      return NextResponse.json({
        exists: true,
        reportPath,
        currentEvalPath,
        generatedAtUtc,
        reportUpdatedAtUtc: reportStat.mtime.toISOString(),
        updatedAtUtc: reportStat.mtime.toISOString(),
        liveEligible: true,
        liveEpochStartUtc,
        daysSinceLiveEpoch,
        liveMinDays: HORIZON_MIN_DAYS[5],
        source: "comparison_horizon_rows",
        horizonMaturity: maturity.horizonMaturity,
        withheldHorizonDays: maturity.withheldHorizonDays,
        horizons: maturity.visibleHorizons,
        methodology:
          "Fallback from latest L5 comparison horizon rows when current runtime evaluation artifact is unavailable in runtime image. Visibility is maturity-gated by live epoch (5D/20D/60D).",
        warning: fallbackError,
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load model accuracy metrics.";
    return NextResponse.json(
      {
        exists: false,
        reportPath: L5_LATEST_PATH,
        currentEvalPath: null,
        generatedAtUtc: null,
        liveEligible: false,
        liveEpochStartUtc: null,
        daysSinceLiveEpoch: null,
        liveMinDays: HORIZON_MIN_DAYS[5],
        updatedAtUtc: null,
        horizons: [],
        error: message,
      },
      { status: 500 },
    );
  }
}
