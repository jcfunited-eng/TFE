import { NextResponse } from "next/server";
import { Pool } from "pg";

import { readSessionUserFromRequest } from "@/lib/auth-session";

export const runtime = "nodejs";

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
};

type RecommendationsPayload = {
  totalAccumulate: number;
  buckets: {
    titans: RecommendationRow[];
    heavyweights: RecommendationRow[];
    midTier: RecommendationRow[];
    hunters: RecommendationRow[];
  };
};

type DbRow = {
  ticker: string;
  sector: string;
  current_ratio: number | string | null;
  free_cash_flow: number | string | null;
  gross_margin: number | string | null;
  gross_profit: number | string | null;
  market_cap: number | string | null;
  operating_cash_flow: number | string | null;
  revenues: number | string | null;
};

const UNKNOWN_SECTOR = "Unknown";
const MAX_ATTEMPTS = 3;

const ACTIVE_EPOCHS: Record<string, number> = {
  RATES_PRESSURE: 0.8,
  CONSUMER_STRESS: 0.6,
  WAR_GEOPOLITICS: 0.7,
};

const SECTOR_SENSITIVITY_MATRIX: Record<string, Record<string, number>> = {
  "Communication Services": {
    RATES_PRESSURE: -0.2,
    CONSUMER_STRESS: -0.3,
    WAR_GEOPOLITICS: -0.1,
  },
  "Consumer Discretionary": {
    RATES_PRESSURE: -0.5,
    CONSUMER_STRESS: -1.0,
    WAR_GEOPOLITICS: -0.2,
  },
  "Consumer Staples": {
    RATES_PRESSURE: 0.1,
    CONSUMER_STRESS: 0.4,
    WAR_GEOPOLITICS: -0.1,
  },
  Energy: {
    RATES_PRESSURE: 0.0,
    CONSUMER_STRESS: -0.2,
    WAR_GEOPOLITICS: 0.9,
  },
  Financials: {
    RATES_PRESSURE: 0.2,
    CONSUMER_STRESS: -0.5,
    WAR_GEOPOLITICS: -0.2,
  },
  "Health Care": {
    RATES_PRESSURE: 0.0,
    CONSUMER_STRESS: 0.3,
    WAR_GEOPOLITICS: 0.1,
  },
  Industrials: {
    RATES_PRESSURE: -0.2,
    CONSUMER_STRESS: -0.3,
    WAR_GEOPOLITICS: 0.2,
  },
  "Information Technology": {
    RATES_PRESSURE: -0.4,
    CONSUMER_STRESS: -0.3,
    WAR_GEOPOLITICS: 0.0,
  },
  Materials: {
    RATES_PRESSURE: -0.1,
    CONSUMER_STRESS: -0.3,
    WAR_GEOPOLITICS: 0.3,
  },
  "Real Estate": {
    RATES_PRESSURE: -1.0,
    CONSUMER_STRESS: -0.5,
    WAR_GEOPOLITICS: 0.0,
  },
  Utilities: {
    RATES_PRESSURE: -0.3,
    CONSUMER_STRESS: 0.2,
    WAR_GEOPOLITICS: 0.1,
  },
};

let pool: Pool | null = null;

function resolvePool(): Pool {
  if (pool) return pool;

  pool = new Pool({
    host: String(process.env.PGHOST ?? "").trim(),
    database: String(process.env.PGDATABASE ?? "").trim(),
    user: String(process.env.PGUSER ?? "").trim(),
    password: String(process.env.PGPASSWORD ?? "").trim(),
    port: Number(process.env.PGPORT ?? 5432),
    max: 4,
  });

  return pool;
}

function toNumber(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function sortByMarketCap(rows: RecommendationRow[]): RecommendationRow[] {
  return [...rows].sort((a, b) => {
    if (b.marketCap !== a.marketCap) return b.marketCap - a.marketCap;
    return a.ticker.localeCompare(b.ticker);
  });
}

function evaluateSectorEpoch(sector: string): { ok: boolean; reason: string } {
  const normalizedSector = String(sector ?? "").trim();
  if (!(normalizedSector in SECTOR_SENSITIVITY_MATRIX)) {
    return { ok: false, reason: `Unknown sector: ${sector}` };
  }

  const sectorVector = SECTOR_SENSITIVITY_MATRIX[normalizedSector];
  const epochPressure = Object.entries(ACTIVE_EPOCHS).reduce((sum, [epochName, strength]) => {
    return sum + strength * Number(sectorVector[epochName] ?? 0);
  }, 0);

  if (epochPressure <= -0.5) {
    return { ok: false, reason: `Adverse Epoch Pressure: ${epochPressure}` };
  }

  return { ok: true, reason: "Epoch Favorable/Neutral" };
}

function toAccumulateRow(row: DbRow): RecommendationRow | null {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  const sector = String(row.sector ?? "").trim() || UNKNOWN_SECTOR;
  if (!ticker || sector === UNKNOWN_SECTOR) return null;

  const currentRatio = toNumber(row.current_ratio);
  const freeCashFlow = toNumber(row.free_cash_flow);
  const grossMargin = toNumber(row.gross_margin);
  const grossProfit = toNumber(row.gross_profit);
  const marketCap = toNumber(row.market_cap) ?? 0;
  const operatingCashFlow = toNumber(row.operating_cash_flow);
  const revenues = toNumber(row.revenues);

  if (
    currentRatio === null ||
    freeCashFlow === null ||
    grossMargin === null ||
    grossProfit === null ||
    operatingCashFlow === null ||
    revenues === null
  ) {
    return null;
  }

  if (revenues <= 0) return null;

  let currentRatioFloor = 1.2;
  if (marketCap >= 200_000_000_000) {
    currentRatioFloor = 0.75;
  } else if (marketCap >= 2_000_000_000) {
    currentRatioFloor = 1.0;
  }

  if (currentRatio <= currentRatioFloor) return null;
  if (freeCashFlow <= 0) return null;
  if (grossMargin <= 0) return null;
  if (grossProfit <= 0) return null;
  if (operatingCashFlow <= 0) return null;

  const epoch = evaluateSectorEpoch(sector);
  if (!epoch.ok) return null;

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
    decisionReason: "Passed normalized fundamentals and Epoch constraints.",
  };
}

async function loadAccumulateRows(): Promise<RecommendationRow[]> {
  const query = `
    SELECT
      ticker,
      sector,
      current_ratio,
      free_cash_flow,
      gross_margin,
      gross_profit,
      market_cap,
      operating_cash_flow,
      revenues
    FROM l5_fundamentals_normalized
    WHERE sector <> 'Unknown'
      AND COALESCE(attempt_count, 0) < $1
      AND current_ratio IS NOT NULL
      AND free_cash_flow IS NOT NULL
      AND gross_margin IS NOT NULL
      AND gross_profit IS NOT NULL
      AND operating_cash_flow IS NOT NULL
      AND revenues IS NOT NULL
    ORDER BY COALESCE(market_cap, 0) DESC, ticker ASC
  `;

  const result = await resolvePool().query<DbRow>(query, [MAX_ATTEMPTS]);
  const rows: RecommendationRow[] = [];
  for (const row of result.rows) {
    const evaluated = toAccumulateRow(row);
    if (evaluated) rows.push(evaluated);
  }
  return sortByMarketCap(rows);
}

function buildPayload(rows: RecommendationRow[]): RecommendationsPayload {
  return {
    totalAccumulate: rows.length,
    buckets: {
      titans: rows.filter((row) => row.marketCap >= 200_000_000_000),
      heavyweights: rows.filter((row) => row.marketCap >= 50_000_000_000 && row.marketCap < 200_000_000_000),
      midTier: rows.filter((row) => row.marketCap >= 10_000_000_000 && row.marketCap < 50_000_000_000),
      hunters: rows.filter((row) => row.marketCap < 10_000_000_000),
    },
  };
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  try {
    const rows = await loadAccumulateRows();
    return NextResponse.json(buildPayload(rows));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown recommendations load error.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
