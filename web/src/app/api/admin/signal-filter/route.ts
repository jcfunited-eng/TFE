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

export type SignalFilterPayload = {
  generatedAtUtc: string;
  totalAccumulate: number;
  laneA: LaneAResult;
  laneB: LaneResult;
  baselineWinRate: number;
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

  try {
    const result = await pool.query<{ ticker: string; snapshot_row_json: unknown }>(
      `SELECT ticker, snapshot_row_json FROM ${RUNTIME_DECISIONS_TABLE} WHERE decision_label = 'Accumulate' ORDER BY ticker`
    );

    const rows = result.rows;
    const total = rows.length;

    if (total === 0) {
      return NextResponse.json({
        generatedAtUtc: new Date().toISOString(),
        totalAccumulate: 0,
        laneA: emptyLaneA,
        laneB: emptyLaneB,
        baselineWinRate: BASELINE_WIN_RATE,
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
    } satisfies SignalFilterPayload);

  } catch (error) {
    const message = error instanceof Error ? error.message : "Signal filter query failed.";
    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      totalAccumulate: 0,
      laneA: emptyLaneA,
      laneB: emptyLaneB,
      baselineWinRate: BASELINE_WIN_RATE,
      error: message,
    } satisfies SignalFilterPayload);
  }
}
