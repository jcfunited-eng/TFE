import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { loadLivePriceMap } from "@/lib/live-price";
import { quoteCachePriceFromRow } from "@/lib/screener-quote-cache";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";

const execFileAsync = promisify(execFile);

const UNKNOWN_SECTOR = "Unknown";
const MAX_ATTEMPTS = 3;
const PYTHON_FETCH_TIMEOUT_MS = 45_000;
const FUNDAMENTAL_FETCH_MAX_BUFFER_BYTES = 4 * 1024 * 1024;

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

const RAW_FETCHER_CODE = `
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

from tfe_fundamental_fetcher import FundamentalCorpora

def load_env_file() -> None:
    cwd = Path.cwd()
    candidate_paths = [
        cwd / ".env",
        cwd.parent / ".env",
    ]
    env_path = next((path for path in candidate_paths if path.exists()), None)
    if env_path is None:
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line or line.startswith("export "):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    massive_key = str(os.environ.get("MASSIVE_API_KEY", "")).strip()
    if massive_key and not str(os.environ.get("POLYGON_API_KEY", "")).strip():
        os.environ["POLYGON_API_KEY"] = massive_key

def main() -> None:
    load_env_file()
    ticker = str(sys.argv[1] if len(sys.argv) > 1 else "").strip().upper()
    asset_class = str(sys.argv[2] if len(sys.argv) > 2 else "equity").strip()
    result = FundamentalCorpora().evaluate_ticker(ticker, asset_class=asset_class, sector_hint="Unknown")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
`;

type DecisionLabel = "Accumulate" | "Hold" | "Avoid";
type Classification = "BUY" | "HOLD" | "SELL";

type RuntimeSnapshotRow = {
  ticker?: string;
  asset_type?: unknown;
  price?: unknown;
  regime?: unknown;
  S_UF?: unknown;
  R_UF?: unknown;
  bar_count?: unknown;
  stability_score?: unknown;
  max_dd?: unknown;
};

type DbFundamentalsRow = {
  ticker: string;
  sector: string | null;
  gross_profit: number | string | null;
  current_ratio: number | string | null;
  free_cash_flow: number | string | null;
  gross_margin: number | string | null;
  long_term_debt: number | string | null;
  market_cap: number | string | null;
  operating_cash_flow: number | string | null;
  revenues: number | string | null;
  attempt_count: number | string | null;
};

type PersistableFundamentals = {
  ticker: string;
  sector: string;
  gross_profit: number | null;
  current_ratio: number | null;
  free_cash_flow: number | null;
  gross_margin: number | null;
  long_term_debt: number | null;
  market_cap: number | null;
  operating_cash_flow: number | null;
  revenues: number | null;
};

type DecisionResult = {
  decision: DecisionLabel;
  decisionReason: string;
  decisionReasonCode: string;
  classification: Classification;
};

type ExecErrorShape = {
  stderr?: string | Buffer | null;
  stdout?: string | Buffer | null;
  message?: string;
};

export type WatchlistMetricRow = {
  ticker: string;
  decision: DecisionLabel;
  decisionReason: string;
  decisionReasonCode: string;
  classification: Classification;
  price: number | null;
  regime: string;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  stability_score: number | null;
  max_dd: number | null;
};

type MetricLoadResult = {
  metrics: WatchlistMetricRow[];
  missingSymbols: string[];
};

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function classificationFromDecision(decision: DecisionLabel): Classification {
  if (decision === "Accumulate") return "BUY";
  if (decision === "Avoid") return "SELL";
  return "HOLD";
}

function inferAssetClass(ticker: string): string {
  if (ticker.startsWith("X:")) return "crypto";
  return "equity";
}

function pythonScoutErrorMessage(error: unknown): string {
  const execError = error as ExecErrorShape | undefined;
  const stderr = String(execError?.stderr ?? "").trim();
  if (stderr) return stderr;

  const stdout = String(execError?.stdout ?? "").trim();
  if (stdout) return stdout;

  const message = String(execError?.message ?? "").trim();
  if (message) return message;

  return "Unknown python scout failure.";
}

function evaluateSectorEpoch(sector: string): { ok: boolean; reason: string } {
  const normalizedSector = String(sector ?? "").trim();
  if (!(normalizedSector in SECTOR_SENSITIVITY_MATRIX)) {
    return { ok: false, reason: `Unknown sector: ${sector}` };
  }

  const sectorVector = SECTOR_SENSITIVITY_MATRIX[normalizedSector];
  const epochPressure = Object.entries(ACTIVE_EPOCHS).reduce((sum, [epochName, strength]) => {
    return sum + strength * Number(sectorVector[epochName] ?? 0) * strength;
  }, 0);

  if (epochPressure <= -0.5) {
    return { ok: false, reason: `Adverse Epoch Pressure: ${epochPressure}` };
  }

  return { ok: true, reason: "Epoch Favorable/Neutral" };
}

function toPersistableFundamentals(row: DbFundamentalsRow): PersistableFundamentals {
  return {
    ticker: normalizeTicker(row.ticker),
    sector: String(row.sector ?? "").trim() || UNKNOWN_SECTOR,
    gross_profit: toNumberOrNull(row.gross_profit),
    current_ratio: toNumberOrNull(row.current_ratio),
    free_cash_flow: toNumberOrNull(row.free_cash_flow),
    gross_margin: toNumberOrNull(row.gross_margin),
    long_term_debt: toNumberOrNull(row.long_term_debt),
    market_cap: toNumberOrNull(row.market_cap),
    operating_cash_flow: toNumberOrNull(row.operating_cash_flow),
    revenues: toNumberOrNull(row.revenues),
  };
}

function decideFundamentals(row: PersistableFundamentals): DecisionResult {
  if (row.sector === UNKNOWN_SECTOR) {
    return {
      decision: "Avoid",
      decisionReason: "Unknown sector: Unknown",
      decisionReasonCode: "L5_UNKNOWN_SECTOR",
      classification: "SELL",
    };
  }

  const missing: string[] = [];
  if (row.current_ratio === null) missing.push("current_ratio");
  if (row.free_cash_flow === null) missing.push("free_cash_flow");
  if (row.gross_margin === null) missing.push("gross_margin");
  if (row.gross_profit === null) missing.push("gross_profit");
  if (row.operating_cash_flow === null) missing.push("operating_cash_flow");
  if (row.revenues === null) missing.push("revenues");

  if (missing.length > 0) {
    return {
      decision: "Hold",
      decisionReason: `Missing live metric(s): ${missing.join(", ")}`,
      decisionReasonCode: "L5_MISSING_LIVE_METRICS",
      classification: "HOLD",
    };
  }

  const marketCap = row.market_cap ?? 0;
  let assignedTier = "Tier 3";
  let currentRatioFloor = 1.2;
  if (marketCap >= 200_000_000_000) {
    assignedTier = "Tier 1";
    currentRatioFloor = 0.75;
  } else if (marketCap >= 2_000_000_000) {
    assignedTier = "Tier 2";
    currentRatioFloor = 1.0;
  }

  if ((row.revenues ?? 0) <= 0) {
    return {
      decision: "Avoid",
      decisionReason: "Domain C Failure: revenues missing or nonpositive",
      decisionReasonCode: "L5_DOMAIN_C_REVENUES",
      classification: "SELL",
    };
  }

  if ((row.current_ratio ?? 0) <= currentRatioFloor) {
    return {
      decision: "Avoid",
      decisionReason: `Domain A Failure: ${assignedTier} requires Current Ratio > ${currentRatioFloor}`,
      decisionReasonCode: "L5_DOMAIN_A_CURRENT_RATIO",
      classification: "SELL",
    };
  }

  if ((row.free_cash_flow ?? 0) <= 0) {
    return {
      decision: "Avoid",
      decisionReason: "Domain B Failure: Free Cash Flow <= 0",
      decisionReasonCode: "L5_DOMAIN_B_FREE_CASH_FLOW",
      classification: "SELL",
    };
  }

  if ((row.gross_margin ?? 0) <= 0) {
    return {
      decision: "Avoid",
      decisionReason: "Domain C Failure: Gross Margin <= 0",
      decisionReasonCode: "L5_DOMAIN_C_GROSS_MARGIN",
      classification: "SELL",
    };
  }

  if ((row.gross_profit ?? 0) <= 0) {
    return {
      decision: "Avoid",
      decisionReason: "Domain C Failure: Gross Profit <= 0",
      decisionReasonCode: "L5_DOMAIN_C_GROSS_PROFIT",
      classification: "SELL",
    };
  }

  if ((row.operating_cash_flow ?? 0) <= 0) {
    return {
      decision: "Avoid",
      decisionReason: "Domain B Failure: Operating Cash Flow <= 0",
      decisionReasonCode: "L5_DOMAIN_B_OPERATING_CASH_FLOW",
      classification: "SELL",
    };
  }

  const epoch = evaluateSectorEpoch(row.sector);
  if (!epoch.ok) {
    return {
      decision: "Avoid",
      decisionReason: epoch.reason,
      decisionReasonCode: "L5_EPOCH_FAILURE",
      classification: "SELL",
    };
  }

  return {
    decision: "Accumulate",
    decisionReason: "Passed live-ingested fundamentals and Epoch constraints.",
    decisionReasonCode: "L5_ACCUMULATE",
    classification: "BUY",
  };
}

async function queryExistingFundamentals(symbols: string[]): Promise<Map<string, PersistableFundamentals>> {
  if (symbols.length === 0) return new Map<string, PersistableFundamentals>();

  const result = await resolveRuntimePostgresPool().query<DbFundamentalsRow>(
    `
      SELECT
        ticker,
        sector,
        gross_profit,
        current_ratio,
        free_cash_flow,
        gross_margin,
        long_term_debt,
        market_cap,
        operating_cash_flow,
        revenues,
        attempt_count
      FROM l5_fundamentals_normalized
      WHERE ticker = ANY($1::text[])
    `,
    [symbols],
  );

  const rows = new Map<string, PersistableFundamentals>();
  for (const row of result.rows) {
    const ticker = normalizeTicker(row.ticker);
    if (!ticker) continue;
    rows.set(ticker, toPersistableFundamentals(row));
  }
  return rows;
}

async function fetchRawFundamentals(ticker: string): Promise<PersistableFundamentals | null> {
  try {
    const result = await execFileAsync(
      "python3",
      ["-c", RAW_FETCHER_CODE, ticker, inferAssetClass(ticker)],
      {
        cwd: process.cwd(),
        timeout: PYTHON_FETCH_TIMEOUT_MS,
        maxBuffer: FUNDAMENTAL_FETCH_MAX_BUFFER_BYTES,
      },
    );

    const payload = JSON.parse(String(result.stdout ?? "").trim()) as Record<string, unknown>;
    const metrics = payload.metrics && typeof payload.metrics === "object" && !Array.isArray(payload.metrics)
      ? payload.metrics as Record<string, unknown>
      : {};

    const grossProfit = toNumberOrNull(metrics.gross_profit);
    const revenues = toNumberOrNull(metrics.revenues);
    const grossMarginRaw = toNumberOrNull(metrics.gross_margin);
    const grossMargin = grossMarginRaw ?? (
      grossProfit !== null && revenues !== null && revenues > 0 ? grossProfit / revenues : null
    );

    return {
      ticker,
      sector: String(payload.sector ?? "").trim() || UNKNOWN_SECTOR,
      gross_profit: grossProfit,
      current_ratio: toNumberOrNull(metrics.current_ratio),
      free_cash_flow: toNumberOrNull(metrics.free_cash_flow),
      gross_margin: grossMargin,
      long_term_debt: toNumberOrNull(metrics.long_term_debt),
      market_cap: toNumberOrNull(metrics.market_cap),
      operating_cash_flow: toNumberOrNull(metrics.operating_cash_flow),
      revenues,
    };
  } catch (error) {
    throw new Error(pythonScoutErrorMessage(error));
  }
}

async function upsertFundamentals(rows: PersistableFundamentals[]): Promise<void> {
  if (rows.length === 0) return;

  const values: unknown[] = [];
  const placeholders = rows.map((row, index) => {
    const base = index * 10;
    values.push(
      row.ticker,
      row.sector,
      row.gross_profit,
      row.current_ratio,
      row.free_cash_flow,
      row.gross_margin,
      row.long_term_debt,
      row.market_cap,
      row.operating_cash_flow,
      row.revenues,
    );
    return `($${base + 1}, $${base + 2}, $${base + 3}, $${base + 4}, $${base + 5}, $${base + 6}, $${base + 7}, $${base + 8}, $${base + 9}, $${base + 10})`;
  });

  await resolveRuntimePostgresPool().query(
    `
      INSERT INTO l5_fundamentals_normalized (
        ticker,
        sector,
        gross_profit,
        current_ratio,
        free_cash_flow,
        gross_margin,
        long_term_debt,
        market_cap,
        operating_cash_flow,
        revenues
      )
      VALUES ${placeholders.join(", ")}
      ON CONFLICT (ticker)
      DO UPDATE SET
        sector = EXCLUDED.sector,
        gross_profit = EXCLUDED.gross_profit,
        current_ratio = EXCLUDED.current_ratio,
        free_cash_flow = EXCLUDED.free_cash_flow,
        gross_margin = EXCLUDED.gross_margin,
        long_term_debt = EXCLUDED.long_term_debt,
        market_cap = EXCLUDED.market_cap,
        operating_cash_flow = EXCLUDED.operating_cash_flow,
        revenues = EXCLUDED.revenues,
        updated_at = CURRENT_TIMESTAMP
    `,
    values,
  );
}

async function loadDisplayContext(symbols: string[]): Promise<{
  snapshotByTicker: Map<string, RuntimeSnapshotRow>;
  quoteRows: Record<string, Record<string, unknown>>;
  livePrices: Map<string, { price: number | null }>;
}> {
  const [snapshot, quoteCache] = await Promise.all([
    loadRuntimeSnapshotRowsFromPostgres(),
    loadRuntimeQuoteCacheFromPostgres(),
  ]);

  const normalized = new Set(symbols.map((ticker) => normalizeTicker(ticker)).filter(Boolean));
  const snapshotByTicker = new Map<string, RuntimeSnapshotRow>();

  for (const row of snapshot.rows as RuntimeSnapshotRow[]) {
    const ticker = normalizeTicker(row.ticker);
    if (!ticker || !normalized.has(ticker) || snapshotByTicker.has(ticker)) continue;
    snapshotByTicker.set(ticker, row);
  }

  const livePrices = await loadLivePriceMap(
    symbols.map((ticker) => ({
      ticker,
      assetType: snapshotByTicker.get(ticker)?.asset_type,
    })),
  );

  return {
    snapshotByTicker,
    quoteRows: quoteCache.quotes as Record<string, Record<string, unknown>>,
    livePrices: livePrices as Map<string, { price: number | null }>,
  };
}

function toMetricRow(
  ticker: string,
  decision: DecisionResult,
  displayRow: RuntimeSnapshotRow | undefined,
  livePrice: number | null,
  quotePrice: number | null,
): WatchlistMetricRow {
  const fallbackPrice = toNumberOrNull(displayRow?.price);

  return {
    ticker,
    decision: decision.decision,
    decisionReason: decision.decisionReason,
    decisionReasonCode: decision.decisionReasonCode,
    classification: decision.classification,
    price: livePrice ?? quotePrice ?? fallbackPrice,
    regime: String(displayRow?.regime ?? "UNKNOWN"),
    S_UF: toNumber(displayRow?.S_UF),
    R_UF: toNumber(displayRow?.R_UF),
    barCount: Math.max(0, Math.floor(toNumber(displayRow?.bar_count))),
    minBarsForAccumulate: 0,
    stability_score: toNumberOrNull(displayRow?.stability_score),
    max_dd: toNumberOrNull(displayRow?.max_dd),
  };
}

export async function loadOrIngestWatchlistMetrics(symbols: string[]): Promise<MetricLoadResult> {
  const normalizedSymbols = Array.from(new Set(symbols.map((ticker) => normalizeTicker(ticker)).filter(Boolean)));
  if (normalizedSymbols.length === 0) {
    return { metrics: [], missingSymbols: [] };
  }

  const existing = await queryExistingFundamentals(normalizedSymbols);
  const missing = normalizedSymbols.filter((ticker) => !existing.has(ticker));

  const ingestedRows: PersistableFundamentals[] = [];
  const missingSymbols: string[] = [];

  for (const ticker of missing) {
    const fetched = await fetchRawFundamentals(ticker);
    if (!fetched) {
      missingSymbols.push(ticker);
      continue;
    }
    ingestedRows.push(fetched);
    existing.set(ticker, fetched);
  }

  await upsertFundamentals(ingestedRows);

  const display = await loadDisplayContext(normalizedSymbols);
  const metrics: WatchlistMetricRow[] = [];

  for (const ticker of normalizedSymbols) {
    const fundamentals = existing.get(ticker);
    if (!fundamentals) {
      missingSymbols.push(ticker);
      continue;
    }

    const decision = decideFundamentals(fundamentals);
    const quoteRow = display.quoteRows[ticker];
    const quotePrice = quoteCachePriceFromRow(quoteRow);
    const livePrice = display.livePrices.get(ticker)?.price ?? null;
    const displayRow = display.snapshotByTicker.get(ticker);

    metrics.push(toMetricRow(ticker, decision, displayRow, livePrice, quotePrice));
  }

  return {
    metrics,
    missingSymbols: Array.from(new Set(missingSymbols)).sort(),
  };
}

export async function loadOrIngestWatchlistMetric(ticker: string): Promise<WatchlistMetricRow | null> {
  const normalized = normalizeTicker(ticker);
  if (!normalized) return null;
  const result = await loadOrIngestWatchlistMetrics([normalized]);
  return result.metrics[0] ?? null;
}
