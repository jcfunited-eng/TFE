import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import {
  resolveRuntimePostgresPool,
  RUNTIME_DECISIONS_TABLE,
} from "@/lib/runtime-db";

// ── Validated signal thresholds (from quarantine parquet forensics) ──────────
const CLOSE_MIN       = 5.0;
const FN_MAX          = 1.65;
const NEW_LISTING_BARS = 20;   // bar_count <= this = new listing

// ── Backtest reference stats (quarantine_12k, Mar 2021–Mar 2026) ─────────────
const BASELINE_WIN_RATE   = 54.4;
const LANE_A_WIN_RATE     = 57.5;
const LANE_A_BACKTEST_N   = 5187;
const LANE_B_WIN_RATE     = 65.3;
const LANE_B_BACKTEST_N   = 2906;

// ── Three-Wave Alignment backtest reference (quarantine_12k) ─────────────────
// Wave 1+2+3 combined (Structure A + calm species + SPY D_k=1): 86.7%, n=75
// Wave 1+3 only (Structure A + SPY D_k=1): 84.5%, n=375
// Wave 1 only (Structure A): 72.1%, n=1064
const THREE_WAVE_WIN_RATE_FULL  = 86.7;  // all three waves
const THREE_WAVE_WIN_RATE_W1W3  = 84.5;  // waves 1+3 (no species filter)
const THREE_WAVE_WIN_RATE_W1    = 72.1;  // wave 1 only

type SectorCount = { sector: string; count: number; pct: number };

type FieldStats = {
  min: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  max: number | null;
  populated: number;
  populationPct: number;
};

type LaneResult = {
  label: string;
  thresholds: Record<string, number>;
  backtestWinRate: number;
  backtestN: number;
  survivors: number;
  survivorSymbols: string[];
  sectorConcentration: SectorCount[];
};

type LaneAResult = LaneResult & { fnStats: FieldStats };

// ── Market wave state (Component 1: SPY D_k) ─────────────────────────────────
// SPY D_k=1 signals structural market expansion (Wave 3 in 3WA model).
// When active, Lane B new-listing win rate escalates toward 84.5% (Waves 1+3).
type MarketWaveState = {
  active: boolean;          // true when SPY D_k = 1
  spyDecision: string | null;  // raw decision_label from DB for SPY
  spyDk: number | null;     // raw D_k from snapshot_row_json for audit
  note: string;
};

export type SignalFilterPayload = {
  generatedAtUtc: string;
  totalAccumulate: number;
  laneA: LaneAResult;
  laneB: LaneResult;
  baselineWinRate: number;
  marketWave: MarketWaveState;
  threeWaveBacktest: {
    fullWinRate: number;   // 86.7% (Waves 1+2+3)
    w1w3WinRate: number;   // 84.5% (Waves 1+3, no species)
    w1WinRate: number;     // 72.1% (Wave 1 only)
  };
  error?: string;
};

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await readSessionUserFromRequest(request);
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  return null;
}

function safeFloat(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  const f = typeof val === "number" ? val : parseFloat(String(val));
  return isFinite(f) ? f : null;
}

function safeInt(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  const n = typeof val === "number" ? Math.round(val) : parseInt(String(val), 10);
  return isFinite(n) ? n : null;
}

function percentile(sorted: number[], pct: number): number | null {
  if (!sorted.length) return null;
  const idx = Math.floor(sorted.length * pct / 100);
  return sorted[Math.min(idx, sorted.length - 1)] ?? null;
}

function fieldStats(values: number[], total: number): FieldStats {
  const sorted = [...values].sort((a, b) => a - b);
  return {
    min:    sorted[0] ?? null,
    p25:    percentile(sorted, 25),
    median: percentile(sorted, 50),
    p75:    percentile(sorted, 75),
    max:    sorted[sorted.length - 1] ?? null,
    populated:     values.length,
    populationPct: total > 0 ? Math.round(values.length / total * 1000) / 10 : 0,
  };
}

function sectorConcentration(items: { sector: string }[]): SectorCount[] {
  const map = new Map<string, number>();
  for (const { sector } of items) {
    map.set(sector, (map.get(sector) ?? 0) + 1);
  }
  return [...map.entries()]
    .map(([sector, count]) => ({
      sector,
      count,
      pct: Math.round(count / items.length * 1000) / 10,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);
}

async function queryMarketWave(pool: ReturnType<typeof resolveRuntimePostgresPool>): Promise<MarketWaveState> {
  try {
    const res = await pool.query<{ decision_label: string | null; snapshot_row_json: unknown }>(
      `SELECT decision_label, snapshot_row_json
       FROM ${RUNTIME_DECISIONS_TABLE}
       WHERE ticker = 'SPY'
       LIMIT 1`
    );
    if (res.rows.length === 0) {
      return { active: false, spyDecision: null, spyDk: null, note: "SPY not found in runtime_decisions_latest" };
    }
    const row = res.rows[0];
    const snap = row.snapshot_row_json && typeof row.snapshot_row_json === "object" && !Array.isArray(row.snapshot_row_json)
      ? (row.snapshot_row_json as Record<string, unknown>)
      : {};
    const dk = safeFloat(snap["D_k"]);
    const active = row.decision_label === "Accumulate" || dk === 1;
    return {
      active,
      spyDecision: row.decision_label ?? null,
      spyDk: dk,
      note: active
        ? "SPY in structural expansion (D_k=1) — Wave 3 active. Lane B escalates toward 84.5%."
        : "SPY not in structural expansion — Wave 3 inactive. Standard win rates apply.",
    };
  } catch {
    return { active: false, spyDecision: null, spyDk: null, note: "Market wave query failed — SPY state unknown" };
  }
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const pool = resolveRuntimePostgresPool();

  const emptyLaneA: LaneAResult = {
    label: `F_n Established (bar_count > ${NEW_LISTING_BARS})`,
    thresholds: { closeMin: CLOSE_MIN, fnMax: FN_MAX, barCountMin: NEW_LISTING_BARS },
    backtestWinRate: LANE_A_WIN_RATE,
    backtestN: LANE_A_BACKTEST_N,
    survivors: 0,
    survivorSymbols: [],
    sectorConcentration: [],
    fnStats: fieldStats([], 0),
  };

  const emptyLaneB: LaneResult = {
    label: `New Listing (bar_count ≤ ${NEW_LISTING_BARS})`,
    thresholds: { closeMin: CLOSE_MIN, barCountMax: NEW_LISTING_BARS },
    backtestWinRate: LANE_B_WIN_RATE,
    backtestN: LANE_B_BACKTEST_N,
    survivors: 0,
    survivorSymbols: [],
    sectorConcentration: [],
  };

  const threeWaveBacktest = {
    fullWinRate: THREE_WAVE_WIN_RATE_FULL,
    w1w3WinRate: THREE_WAVE_WIN_RATE_W1W3,
    w1WinRate: THREE_WAVE_WIN_RATE_W1,
  };

  try {
    const [result, marketWave] = await Promise.all([
      pool.query<{ ticker: string; snapshot_row_json: unknown }>(
        `SELECT ticker, snapshot_row_json FROM ${RUNTIME_DECISIONS_TABLE} WHERE decision_label = 'Accumulate' ORDER BY ticker`
      ),
      queryMarketWave(pool),
    ]);

    const rows = result.rows;
    const total = rows.length;

    if (total === 0) {
      return NextResponse.json({
        generatedAtUtc: new Date().toISOString(),
        totalAccumulate: 0,
        laneA: emptyLaneA,
        laneB: emptyLaneB,
        baselineWinRate: BASELINE_WIN_RATE,
        marketWave,
        threeWaveBacktest,
      } satisfies SignalFilterPayload);
    }

    type ParsedRow = {
      ticker: string;
      close: number | null;
      fn: number | null;
      barCount: number | null;
      sector: string;
    };

    const parsed: ParsedRow[] = rows.map((r) => {
      const snap =
        r.snapshot_row_json && typeof r.snapshot_row_json === "object" && !Array.isArray(r.snapshot_row_json)
          ? (r.snapshot_row_json as Record<string, unknown>)
          : {};

      const close    = safeFloat(snap["price"] ?? snap["close"] ?? snap["Close"]);
      const fn       = safeFloat(snap["F_n"] ?? snap["f_n"]);
      const barCount = safeInt(snap["bar_count"]);
      const sector   = typeof snap["sector"] === "string" && snap["sector"].trim()
        ? snap["sector"].trim()
        : "Unknown";

      return { ticker: r.ticker, close, fn, barCount, sector };
    });

    // ── Lane A: F_n established ───────────────────────────────────────────────
    const laneARows = parsed.filter(
      p => p.close !== null && p.close >= CLOSE_MIN &&
           p.fn !== null && p.fn <= FN_MAX &&
           p.barCount !== null && p.barCount > NEW_LISTING_BARS
    );
    const fnVals = laneARows.flatMap(p => p.fn !== null ? [p.fn] : []);

    const laneA: LaneAResult = {
      label: `F_n Established (bar_count > ${NEW_LISTING_BARS})`,
      thresholds: { closeMin: CLOSE_MIN, fnMax: FN_MAX, barCountMin: NEW_LISTING_BARS },
      backtestWinRate: LANE_A_WIN_RATE,
      backtestN: LANE_A_BACKTEST_N,
      survivors: laneARows.length,
      survivorSymbols: laneARows.map(p => p.ticker).sort(),
      sectorConcentration: laneARows.length > 0 ? sectorConcentration(laneARows.map(p => ({ sector: p.sector }))) : [],
      fnStats: fieldStats(fnVals, laneARows.length),
    };

    // ── Lane B: New listing ───────────────────────────────────────────────────
    const laneBRows = parsed.filter(
      p => p.close !== null && p.close >= CLOSE_MIN &&
           p.barCount !== null && p.barCount <= NEW_LISTING_BARS
    );

    const laneB: LaneResult = {
      label: `New Listing (bar_count ≤ ${NEW_LISTING_BARS})`,
      thresholds: { closeMin: CLOSE_MIN, barCountMax: NEW_LISTING_BARS },
      backtestWinRate: LANE_B_WIN_RATE,
      backtestN: LANE_B_BACKTEST_N,
      survivors: laneBRows.length,
      survivorSymbols: laneBRows.map(p => p.ticker).sort(),
      sectorConcentration: laneBRows.length > 0 ? sectorConcentration(laneBRows.map(p => ({ sector: p.sector }))) : [],
    };

    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      totalAccumulate: total,
      laneA,
      laneB,
      baselineWinRate: BASELINE_WIN_RATE,
      marketWave,
      threeWaveBacktest,
    } satisfies SignalFilterPayload);

  } catch (error) {
    const message = error instanceof Error ? error.message : "Signal filter query failed.";
    const fallbackWave: MarketWaveState = { active: false, spyDecision: null, spyDk: null, note: "Market wave unavailable due to query error" };
    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      totalAccumulate: 0,
      laneA: emptyLaneA,
      laneB: emptyLaneB,
      baselineWinRate: BASELINE_WIN_RATE,
      marketWave: fallbackWave,
      threeWaveBacktest,
      error: message,
    } satisfies SignalFilterPayload);
  }
}
