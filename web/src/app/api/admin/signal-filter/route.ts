import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import {
  resolveRuntimePostgresPool,
  RUNTIME_DECISIONS_TABLE,
} from "@/lib/runtime-db";

// Sequential cognitive filter thresholds
const CLOSE_MIN   = 5.0;
const RAW_XM_MAX  = 0.50;
const FN_MAX      = 1.65;

type FilterStage = {
  label: string;
  count: number;
  pct: number;
};

type SectorCount = {
  sector: string;
  count: number;
  pct: number;
};

type FieldStats = {
  min: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  max: number | null;
  populated: number;
  populationPct: number;
};

export type SignalFilterPayload = {
  generatedAtUtc: string;
  thresholds: {
    closeMin: number;
    rawXmMax: number;
    fnMax: number;
  };
  totalAccumulate: number;
  fieldPopulation: {
    close: FieldStats;
    rawXm: FieldStats;
    fn: FieldStats;
  };
  filterStages: FilterStage[];
  survivors: number;
  survivorSymbols: string[];
  sectorConcentration: SectorCount[];
  fnNotPopulated: boolean;
  rawXmNotPopulated: boolean;
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

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const pool = resolveRuntimePostgresPool();

  try {
    const result = await pool.query<{ ticker: string; snapshot_row_json: unknown }>(
      `SELECT ticker, snapshot_row_json FROM ${RUNTIME_DECISIONS_TABLE} WHERE decision_label = 'Accumulate' ORDER BY ticker`
    );

    const rows = result.rows;
    const total = rows.length;

    if (total === 0) {
      return NextResponse.json({
        generatedAtUtc: new Date().toISOString(),
        thresholds: { closeMin: CLOSE_MIN, rawXmMax: RAW_XM_MAX, fnMax: FN_MAX },
        totalAccumulate: 0,
        fieldPopulation: {
          close: fieldStats([], 0),
          rawXm: fieldStats([], 0),
          fn:    fieldStats([], 0),
        },
        filterStages: [],
        survivors: 0,
        survivorSymbols: [],
        sectorConcentration: [],
        fnNotPopulated: true,
        rawXmNotPopulated: true,
      } satisfies SignalFilterPayload);
    }

    // Parse each row's snapshot JSON
    type ParsedRow = {
      ticker: string;
      close: number | null;
      rawXm: number | null;
      fn: number | null;
      sector: string;
    };

    const parsed: ParsedRow[] = rows.map((r) => {
      const snap =
        r.snapshot_row_json && typeof r.snapshot_row_json === "object" && !Array.isArray(r.snapshot_row_json)
          ? (r.snapshot_row_json as Record<string, unknown>)
          : {};

      const close  = safeFloat(snap["price"] ?? snap["close"] ?? snap["Close"]);
      const rawXm  = safeFloat(snap["raw_x_m"]);
      const fn     = safeFloat(snap["F_n"] ?? snap["f_n"]);
      const sector = typeof snap["sector"] === "string" && snap["sector"].trim()
        ? snap["sector"].trim()
        : "Unknown";

      return { ticker: r.ticker, close, rawXm, fn, sector };
    });

    // Field distributions
    const closeVals = parsed.flatMap(p => p.close !== null ? [p.close] : []);
    const xmVals    = parsed.flatMap(p => p.rawXm !== null ? [p.rawXm] : []);
    const fnVals    = parsed.flatMap(p => p.fn    !== null ? [p.fn]    : []);

    // Filter stages
    const afterClose = parsed.filter(p => p.close !== null && p.close >= CLOSE_MIN);
    const afterXm    = afterClose.filter(p => p.rawXm !== null && p.rawXm <= RAW_XM_MAX);
    const afterFn    = afterXm.filter(p => p.fn !== null && p.fn <= FN_MAX);

    const filterStages: FilterStage[] = [
      { label: `Close ≥ ${CLOSE_MIN}`,      count: afterClose.length, pct: Math.round(afterClose.length / total * 1000) / 10 },
      { label: `raw_x_m ≤ ${RAW_XM_MAX}`,  count: afterXm.length,   pct: Math.round(afterXm.length   / total * 1000) / 10 },
      { label: `F_n ≤ ${FN_MAX}`,           count: afterFn.length,   pct: Math.round(afterFn.length   / total * 1000) / 10 },
    ];

    // Sector concentration
    const sectorMap = new Map<string, number>();
    for (const p of afterFn) {
      sectorMap.set(p.sector, (sectorMap.get(p.sector) ?? 0) + 1);
    }
    const sectorConcentration: SectorCount[] = [...sectorMap.entries()]
      .map(([sector, count]) => ({
        sector,
        count,
        pct: Math.round(count / afterFn.length * 1000) / 10,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15);

    const survivorSymbols = afterFn.map(p => p.ticker).sort();

    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      thresholds: { closeMin: CLOSE_MIN, rawXmMax: RAW_XM_MAX, fnMax: FN_MAX },
      totalAccumulate: total,
      fieldPopulation: {
        close: fieldStats(closeVals, total),
        rawXm: fieldStats(xmVals, total),
        fn:    fieldStats(fnVals, total),
      },
      filterStages,
      survivors: afterFn.length,
      survivorSymbols,
      sectorConcentration,
      fnNotPopulated:    fnVals.length === 0,
      rawXmNotPopulated: xmVals.length === 0,
    } satisfies SignalFilterPayload);

  } catch (error) {
    const message = error instanceof Error ? error.message : "Signal filter query failed.";
    return NextResponse.json({
      generatedAtUtc: new Date().toISOString(),
      thresholds: { closeMin: CLOSE_MIN, rawXmMax: RAW_XM_MAX, fnMax: FN_MAX },
      totalAccumulate: 0,
      fieldPopulation: {
        close: fieldStats([], 0),
        rawXm: fieldStats([], 0),
        fn:    fieldStats([], 0),
      },
      filterStages: [],
      survivors: 0,
      survivorSymbols: [],
      sectorConcentration: [],
      fnNotPopulated: true,
      rawXmNotPopulated: true,
      error: message,
    } satisfies SignalFilterPayload);
  }
}
