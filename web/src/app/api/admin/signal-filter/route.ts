import { NextResponse } from "next/server";

import { getCurrentServerUser } from "@/lib/server-auth";
import {
  resolveRuntimePostgresPool,
  RUNTIME_DECISIONS_TABLE,
} from "@/lib/runtime-db";

// ── Validated signal thresholds (from quarantine parquet forensics) ──────────
const CLOSE_MIN       = 5.0;
const FN_MAX          = 1.65;
const NEW_LISTING_BARS = 20;   // bar_count <= this = new listing

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
  backtestWinRate: null;
  backtestN: null;
  survivors: number;
  survivorSymbols: string[];
  sectorConcentration: SectorCount[];
};

type LaneAResult = LaneResult & { fnStats: FieldStats };

// ── Market wave state (Component 1: SPY D_k) ─────────────────────────────────
// SPY D_k=1 signals structural market expansion (Wave 3 in 3WA model).
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
  baselineWinRate: null;
  marketWave: MarketWaveState;
  fieldCoverage: "reduced_projection";
  evidenceStatus: "performance_claims_withheld_no_receipted_artifact";
  error?: string;
};

async function requireAdmin(): Promise<NextResponse | null> {
  const user = await getCurrentServerUser();
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
  const res = await pool.query<{ decision_label: string | null; snapshot_row_json: unknown }>(
    `SELECT decision_label, snapshot_row_json
     FROM ${RUNTIME_DECISIONS_TABLE}
     WHERE ticker = 'SPY'
     LIMIT 1`
  );
  if (res.rows.length === 0) throw new Error("SPY field row is unavailable");
  const row = res.rows[0];
  if (!row.snapshot_row_json || typeof row.snapshot_row_json !== "object" || Array.isArray(row.snapshot_row_json)) {
    throw new Error("SPY field payload is invalid");
  }
  const dk = safeFloat((row.snapshot_row_json as Record<string, unknown>)["D_k"]);
  if (dk === null) throw new Error("SPY D_k is unavailable");
  const active = dk === 1;
  return {
    active,
    spyDecision: row.decision_label ?? null,
    spyDk: dk,
    note: active
      ? "Observed SPY D_k=1. This is one reduced field observation, not a full-field performance claim."
      : `Observed SPY D_k=${dk}. This is one reduced field observation, not a full-field performance claim.`,
  };
}

export async function GET() {
  const denied = await requireAdmin();
  if (denied) return denied;

  const pool = resolveRuntimePostgresPool();

  const emptyLaneA: LaneAResult = {
    label: `Reduced F_n projection (bar_count > ${NEW_LISTING_BARS})`,
    thresholds: { closeMin: CLOSE_MIN, fnMax: FN_MAX, barCountMin: NEW_LISTING_BARS },
    backtestWinRate: null,
    backtestN: null,
    survivors: 0,
    survivorSymbols: [],
    sectorConcentration: [],
    fnStats: fieldStats([], 0),
  };

  const emptyLaneB: LaneResult = {
    label: `Reduced coverage projection (bar_count ≤ ${NEW_LISTING_BARS})`,
    thresholds: { closeMin: CLOSE_MIN, barCountMax: NEW_LISTING_BARS },
    backtestWinRate: null,
    backtestN: null,
    survivors: 0,
    survivorSymbols: [],
    sectorConcentration: [],
  };

  try {
    const [result, marketWave] = await Promise.all([
      pool.query<{ ticker: string; snapshot_row_json: unknown; resolved_sector: string }>(
        `SELECT r.ticker, r.snapshot_row_json,
                COALESCE(NULLIF(f.sector, 'Unknown'), NULLIF(s.sector, ''), 'Unknown') AS resolved_sector
         FROM ${RUNTIME_DECISIONS_TABLE} r
         LEFT JOIN runtime_symbols s ON s.ticker = r.ticker
         LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
         WHERE r.decision_label = 'Accumulate'
         ORDER BY r.ticker`
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
        baselineWinRate: null,
        marketWave,
        fieldCoverage: "reduced_projection",
        evidenceStatus: "performance_claims_withheld_no_receipted_artifact",
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
      const sector   = typeof r.resolved_sector === "string" && r.resolved_sector.trim()
        ? r.resolved_sector.trim()
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
      label: `Reduced F_n projection (bar_count > ${NEW_LISTING_BARS})`,
      thresholds: { closeMin: CLOSE_MIN, fnMax: FN_MAX, barCountMin: NEW_LISTING_BARS },
      backtestWinRate: null,
      backtestN: null,
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
      label: `Reduced coverage projection (bar_count ≤ ${NEW_LISTING_BARS})`,
      thresholds: { closeMin: CLOSE_MIN, barCountMax: NEW_LISTING_BARS },
      backtestWinRate: null,
      backtestN: null,
      survivors: laneBRows.length,
      survivorSymbols: laneBRows.map(p => p.ticker).sort(),
      sectorConcentration: laneBRows.length > 0 ? sectorConcentration(laneBRows.map(p => ({ sector: p.sector }))) : [],
    };

    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      totalAccumulate: total,
      laneA,
      laneB,
      baselineWinRate: null,
      marketWave,
      fieldCoverage: "reduced_projection",
      evidenceStatus: "performance_claims_withheld_no_receipted_artifact",
    } satisfies SignalFilterPayload);

  } catch (error) {
    const message = error instanceof Error ? error.message : "Signal filter query failed.";
    const unavailableWave: MarketWaveState = { active: false, spyDecision: null, spyDk: null, note: "Market wave unavailable due to query error" };
    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      totalAccumulate: 0,
      laneA: emptyLaneA,
      laneB: emptyLaneB,
      baselineWinRate: null,
      marketWave: unavailableWave,
      fieldCoverage: "reduced_projection",
      evidenceStatus: "performance_claims_withheld_no_receipted_artifact",
      error: message,
    } satisfies SignalFilterPayload, { status: 503 });
  }
}
