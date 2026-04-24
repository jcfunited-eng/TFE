import { NextResponse } from "next/server";

import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const runtime = "nodejs";

// signal_class encodes which structural attractor state the Accumulate signal
// occupies, based on Three-Wave Alignment (3WA) analysis of quarantine_12k data.
//
//  "3WA"       — Wave 1 (bar_count ≤ 20) + Wave 3 (SPY D_k=1) confirmed active.
//                Backtest win rate: 84.5% (Waves 1+3, n=375) or 86.7% with species.
//  "W1"        — Wave 1 (new listing, bar_count ≤ 20) only; SPY wave not active.
//                Backtest win rate: 72.1% (n=1064).
//  "standard"  — Established stock (bar_count > 20). F_n ≤ 1.65 backtest: 57.5%.
//
// Wave 2 (species profile) is deferred until species_profiles table is populated.
type SignalClass = "3WA" | "W1" | "CH3" | "standard";

type RecommendationRow = {
  ticker: string;
  sector: string;
  marketCap: number;
  currentRatio: number;
  freeCashFlow: number;
  grossMargin: number;
  grossProfit: number;
  operatingCashFlow: number;
  revenues: number;
  decision: "Accumulate";
  decisionReason: string;
  isNewListing: boolean;
  signalClass: SignalClass;
  // Native engine metadata for popup analysis panel
  regime: string;
  stabilityScore: number | null;
  maxDrawdown: number | null;
  barCount: number | null;
  minBarsForAccumulate: number;
  externalResearchUrl: string;
};

type RecommendationsPayload = {
  totalAccumulate: number;
  totalAccumulateInDb: number;
  filteredOutMissingFundamentals: number;
  buckets: {
    titans: RecommendationRow[];
    heavyweights: RecommendationRow[];
    midTier: RecommendationRow[];
    hunters: RecommendationRow[];
  };
};

type DbRow = {
  ticker: string;
  sector: string | null;
  market_cap: number | string | null;
  current_ratio: number | string | null;
  free_cash_flow: number | string | null;
  gross_margin: number | string | null;
  gross_profit: number | string | null;
  operating_cash_flow: number | string | null;
  revenues: number | string | null;
  decision_label: string | null;
  decision_reason: string | null;
  bar_count: number | string | null;
  regime: string | null;
  stability_score: number | string | null;
  max_dd: number | string | null;
  min_bars_for_accumulate: number | string | null;
};

function buildResearchUrl(ticker: string): string {
  return `https://finance.yahoo.com/quote/${encodeURIComponent(ticker.trim().toUpperCase())}`;
}

const UNKNOWN_SECTOR = "Unknown";

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function sortByMarketCap(rows: RecommendationRow[]): RecommendationRow[] {
  return [...rows].sort((a, b) => {
    if (b.marketCap !== a.marketCap) return b.marketCap - a.marketCap;
    return a.ticker.localeCompare(b.ticker);
  });
}

const NEW_LISTING_BAR_THRESHOLD = 20;

function classifySignal(barCount: number | null, spyWaveActive: boolean): SignalClass {
  const isNewListing = barCount !== null && barCount <= NEW_LISTING_BAR_THRESHOLD;
  if (isNewListing && spyWaveActive) return "3WA";
  if (isNewListing) return "W1";
  return "standard";
}

function toRecommendationRow(row: DbRow, spyWaveActive: boolean): RecommendationRow | null {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  const sector = String(row.sector ?? "").trim() || UNKNOWN_SECTOR;
  const marketCap = toNumber(row.market_cap);
  const currentRatio = toNumber(row.current_ratio);
  const freeCashFlow = toNumber(row.free_cash_flow);
  const grossMargin = toNumber(row.gross_margin);
  const grossProfit = toNumber(row.gross_profit);
  const operatingCashFlow = toNumber(row.operating_cash_flow);
  const revenues = toNumber(row.revenues);

  if (!ticker) return null;
  if (String(row.decision_label ?? "").trim() !== "Accumulate") return null;
  if (sector === UNKNOWN_SECTOR) return null;
  if (
    marketCap === null ||
    currentRatio === null ||
    freeCashFlow === null ||
    grossMargin === null ||
    grossProfit === null ||
    operatingCashFlow === null ||
    revenues === null
  ) {
    return null;
  }

  const barCount = toNumber(row.bar_count);
  return {
    ticker,
    sector,
    marketCap,
    currentRatio,
    freeCashFlow,
    grossMargin,
    grossProfit,
    operatingCashFlow,
    revenues,
    decision: "Accumulate",
    decisionReason: String(row.decision_reason ?? "").trim() || "Runtime decision selected from latest table.",
    isNewListing: barCount !== null && barCount <= NEW_LISTING_BAR_THRESHOLD,
    signalClass: classifySignal(barCount, spyWaveActive),
    regime: String(row.regime ?? "").trim() || "—",
    stabilityScore: toNumber(row.stability_score),
    maxDrawdown: toNumber(row.max_dd),
    barCount,
    minBarsForAccumulate: toNumber(row.min_bars_for_accumulate) ?? NEW_LISTING_BAR_THRESHOLD,
    externalResearchUrl: buildResearchUrl(ticker),
  };
}

async function querySpyWaveActive(pool: ReturnType<typeof resolveRuntimePostgresPool>): Promise<boolean> {
  try {
    const res = await pool.query<{ decision_label: string | null; snapshot_row_json: unknown }>(
      `SELECT decision_label, snapshot_row_json FROM runtime_decisions_latest WHERE ticker = 'SPY' LIMIT 1`
    );
    if (res.rows.length === 0) return false;
    const row = res.rows[0];
    const snap = row.snapshot_row_json && typeof row.snapshot_row_json === "object" && !Array.isArray(row.snapshot_row_json)
      ? (row.snapshot_row_json as Record<string, unknown>)
      : {};
    const dk = Number(snap["D_k"]);
    return row.decision_label === "Accumulate" || dk === 1;
  } catch {
    return false;
  }
}

async function loadAccumulateRows(): Promise<{ filtered: RecommendationRow[]; totalDbRows: number }> {
  const query = `
    SELECT
      r.ticker,
      COALESCE(NULLIF(TRIM(f.sector), ''), NULLIF(TRIM(r.snapshot_row_json->>'sector'), '')) AS sector,
      COALESCE(
        f.market_cap,
        CAST(NULLIF(r.snapshot_row_json->>'market_cap', '') AS DOUBLE PRECISION)
      ) AS market_cap,
      COALESCE(
        f.current_ratio,
        CAST(NULLIF(r.snapshot_row_json->>'current_ratio', '') AS DOUBLE PRECISION)
      ) AS current_ratio,
      COALESCE(
        f.free_cash_flow,
        CAST(NULLIF(r.snapshot_row_json->>'free_cash_flow', '') AS DOUBLE PRECISION)
      ) AS free_cash_flow,
      COALESCE(
        f.gross_margin,
        CAST(NULLIF(r.snapshot_row_json->>'gross_margin', '') AS DOUBLE PRECISION)
      ) AS gross_margin,
      COALESCE(
        f.gross_profit,
        CAST(NULLIF(r.snapshot_row_json->>'gross_profit', '') AS DOUBLE PRECISION)
      ) AS gross_profit,
      COALESCE(
        f.operating_cash_flow,
        CAST(NULLIF(r.snapshot_row_json->>'operating_cash_flow', '') AS DOUBLE PRECISION)
      ) AS operating_cash_flow,
      COALESCE(
        f.revenues,
        CAST(NULLIF(r.snapshot_row_json->>'revenues', '') AS DOUBLE PRECISION)
      ) AS revenues,
      r.decision_label,
      COALESCE(NULLIF(TRIM(r.reason_text), ''), NULLIF(TRIM(r.reason_code), '')) AS decision_reason,
      CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) AS bar_count,
      NULLIF(TRIM(r.snapshot_row_json->>'regime'), '') AS regime,
      CAST(NULLIF(r.snapshot_row_json->>'stability_score', '') AS DOUBLE PRECISION) AS stability_score,
      CAST(NULLIF(r.snapshot_row_json->>'max_dd', '') AS DOUBLE PRECISION) AS max_dd,
      CAST(NULLIF(r.snapshot_row_json->>'min_bars_for_accumulate', '') AS INTEGER) AS min_bars_for_accumulate
    FROM runtime_decisions_latest AS r
    LEFT JOIN l5_fundamentals_normalized AS f
      ON f.ticker = r.ticker
    WHERE r.decision_label = 'Accumulate'
    ORDER BY
      COALESCE(
        f.market_cap,
        CAST(NULLIF(r.snapshot_row_json->>'market_cap', '') AS DOUBLE PRECISION),
        0
      ) DESC,
      r.ticker ASC
  `;

  const pool = resolveRuntimePostgresPool();
  const [result, spyWaveActive] = await Promise.all([
    pool.query<DbRow>(query),
    querySpyWaveActive(pool),
  ]);
  const rows: RecommendationRow[] = [];
  let filteredOutCount = 0;
  for (const row of result.rows) {
    const mapped = toRecommendationRow(row, spyWaveActive);
    if (mapped) rows.push(mapped);
    else filteredOutCount++;
  }
  if (filteredOutCount > 0) {
    console.warn(
      `[RECOMMENDS] ${filteredOutCount} of ${result.rows.length} Accumulate tickers filtered out (missing fundamentals or sector). ${rows.length} passed.`,
    );
  }
  return { filtered: sortByMarketCap(rows), totalDbRows: result.rows.length };
}

function buildPayload(rows: RecommendationRow[], totalDbRows?: number): RecommendationsPayload {
  return {
    totalAccumulate: rows.length,
    totalAccumulateInDb: totalDbRows ?? rows.length,
    filteredOutMissingFundamentals: (totalDbRows ?? rows.length) - rows.length,
    buckets: {
      titans: rows.filter((row) => row.marketCap >= 200_000_000_000),
      heavyweights: rows.filter((row) => row.marketCap >= 50_000_000_000 && row.marketCap < 200_000_000_000),
      midTier: rows.filter((row) => row.marketCap >= 10_000_000_000 && row.marketCap < 50_000_000_000),
      hunters: rows.filter((row) => row.marketCap < 10_000_000_000),
    },
  };
}

export async function GET(request: Request) {
  const sessionUser = await getCurrentServerUser();
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  try {
    const rows = await loadAccumulateRows();
    return NextResponse.json(buildPayload(rows.filtered, rows.totalDbRows));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown recommendations load error.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
