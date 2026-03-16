"use client";

import { useEffect, useMemo, useState } from "react";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type ScreenerChartControls,
  type ScreenerChartInterval,
  type ScreenerChartRange,
  type MarketTimeframe,
} from "@/components/ScreenerChart";
import ClientPortal from "@/components/ClientPortal";
import { buildMarketStatColumns, type MarketQuoteSummary } from "@/lib/market-analysis";
import { useFlyoutPanel } from "@/lib/use-flyout-panel";

type DecisionLabel = "Accumulate" | "Hold" | "Avoid";

type PortfolioLot = {
  id: string;
  ticker: string;
  units: number;
  unitCost: number;
  addedAt: string;
  updatedAt: string;
};

type PositionRow = {
  ticker: string;
  assetType: "Equities" | "Index" | "Crypto" | "ETF" | "Other";
  units: number;
  avgCost: number;
  costBasis: number;
  currentPrice: number | null;
  marketValue: number | null;
  unrealizedPnL: number | null;
  unrealizedPnLPct: number | null;
  decision: DecisionLabel;
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL";
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
};

type PortfolioSummary = {
  totalLots: number;
  totalPositions: number;
  totalUnits: number;
  totalCostBasis: number;
  totalMarketValue: number | null;
  totalUnrealizedPnL: number | null;
  totalUnrealizedPnLPct: number | null;
  realizedPnL: number | null;
  realizedPnLPct: number | null;
  realizedPnLStatus: "unavailable_no_trade_ledger" | "computed_from_trade_ledger";
  realizedPnLMethod: "trade_ledger_required" | "trade_ledger_v1";
};

type PortfolioBenchmarkComparison = {
  symbol: "SPY";
  portfolioReturnPct: number | null;
  benchmarkReturnPct: number | null;
  relativeReturnPctPoints: number | null;
  status: "unavailable_same_dates_same_dollars_ledger_required" | "computed_same_dates_same_dollars_v1";
  method: "same_dates_same_dollars_ledger_required" | "same_dates_same_dollars_v1";
};

type AllocatorAction = "BUY_MORE" | "TRIM" | "EXIT" | "HOLD";

type AllocatorRow = {
  ticker: string;
  decision: DecisionLabel;
  classification: "BUY" | "HOLD" | "SELL";
  confidence: number;
  currentWeightPct: number;
  targetWeightPct: number;
  currentValue: number;
  targetValue: number;
  driftPctPoints: number;
  action: AllocatorAction;
  rebalanceDollar: number;
  rebalanceUnits: number | null;
  reason: string;
};

type AllocatorPlan = {
  generatedAtUtc: string;
  method: "PFSC_STRUCTURAL_ALLOCATOR_V1";
  rebalanceThresholdPctPoints: number;
  portfolioValueUsed: number;
  status: "ok" | "no_priced_positions" | "no_allocatable_scores";
  missingPriceTickers: string[];
  totals: {
    buyDollar: number;
    trimDollar: number;
    exitDollar: number;
  };
  rows: AllocatorRow[];
};

type UnresolvedPortfolioTicker = {
  ticker: string;
  status: "missing" | "invalid";
  lots: number;
  units: number;
  costBasis: number;
};

type PortfolioProvenance = {
  status: "ok" | "partial";
  sourcePath: string | null;
  failureCount: number;
  rows_required: number;
  rows_valid: number;
  missingTickers: string[];
  invalidTickers: string[];
  unresolvedTickers: UnresolvedPortfolioTicker[];
};

type PortfolioResponse = {
  lots: PortfolioLot[];
  positions: PositionRow[];
  summary: PortfolioSummary;
  benchmark?: PortfolioBenchmarkComparison;
  allocatorPlan?: AllocatorPlan;
  warning?: string | null;
  provenance?: PortfolioProvenance;
  source?: string;
  snapshotSource?: string;
  quoteSource?: string;
  data_source?: string;
  run_id?: string | null;
  generated_at_utc?: string | null;
  error?: string;
};

type ChartBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type ChartSummary = {
  open: number;
  high: number;
  low: number;
  prevClose: number;
  close: number;
  change: number;
  changePct: number;
  high52: number;
  low52: number;
};

type QuoteSummary = MarketQuoteSummary;

type UfMetric = {
  ticker: string;
  decision: DecisionLabel;
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL";
  price: number | null;
  regime: string;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  stability_score: number | null;
  max_dd: number | null;
};

type ChartResponse = {
  ticker: string;
  bars: ChartBar[];
  summary: ChartSummary | null;
  quote?: QuoteSummary;
  interval?: string;
  range?: string;
  ufMetric?: UfMetric | null;
  note?: string | null;
  error?: string;
};

type PositionSortKey =
  | "ticker"
  | "assetType"
  | "units"
  | "avgCost"
  | "currentPrice"
  | "marketValue"
  | "costBasis"
  | "gainValue"
  | "lossValue"
  | "unrealizedPnLPct"
  | "decision";

type LotSortKey = "ticker" | "units" | "unitCost" | "addedAt" | "updatedAt";

type SortDirection = "asc" | "desc";

type SortState<T extends string> = {
  key: T;
  direction: SortDirection;
};

type PieSlice = {
  ticker: string;
  color: string;
  value: number;
  pct: number;
  path: string;
};

const PIE_COLORS = ["#2e7f62", "#6dbc8a", "#a1cf91", "#d8c77d", "#97c6d9", "#7588c3", "#7ab58c", "#b77f5a"];

function normalizeTicker(input: string): string {
  return input.trim().toUpperCase();
}

function toNumber(input: string): number {
  const n = Number(input);
  return Number.isFinite(n) ? n : 0;
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return value.toFixed(decimals);
}

function fmtCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function fmtSignedCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${fmtCurrency(value)}`;
}

function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  const pct = value * 100;
  const prefix = pct > 0 ? "+" : "";
  return `${prefix}${pct.toFixed(2)}%`;
}

function fmtCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "N/A";
  const n = value;
  if (Math.abs(n) >= 1_000_000_000_000) return `${(n / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(n) >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
}

function fmtSigned(value: number, decimals = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  const prefix = n > 0 ? "+" : "";
  return `${prefix}${n.toFixed(decimals)}`;
}

function parseIsoTime(value: string | null | undefined): number | null {
  if (!value) return null;
  const ts = Date.parse(value);
  if (!Number.isFinite(ts)) return null;
  return ts;
}

function formatFreshnessAge(generatedAtUtc: string | null | undefined): string {
  const ts = parseIsoTime(generatedAtUtc);
  if (ts === null) return "N/A";

  const deltaMs = Date.now() - ts;
  if (!Number.isFinite(deltaMs)) return "N/A";
  const mins = Math.max(0, Math.floor(deltaMs / 60000));
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${remMins}m`;
}

function freshnessBadge(generatedAtUtc: string | null | undefined): { label: string; tone: "is-good" | "is-warn" } {
  const ts = parseIsoTime(generatedAtUtc);
  if (ts === null) {
    return { label: "N/A", tone: "is-warn" };
  }

  const deltaMs = Date.now() - ts;
  if (!Number.isFinite(deltaMs)) {
    return { label: "N/A", tone: "is-warn" };
  }

  const mins = Math.max(0, Math.floor(deltaMs / 60000));
  if (mins <= 1440) {
    return { label: `Fresh (${formatFreshnessAge(generatedAtUtc)})`, tone: "is-good" };
  }
  return { label: `Stale (${formatFreshnessAge(generatedAtUtc)})`, tone: "is-warn" };
}

function formatRealizedStatusLabel(value: PortfolioSummary["realizedPnLStatus"] | null | undefined): string {
  if (value === "computed_from_trade_ledger") return "Computed from trade ledger";
  if (value === "unavailable_no_trade_ledger") return "Unavailable: no trade ledger";
  return "N/A";
}

function formatRealizedMethodLabel(value: PortfolioSummary["realizedPnLMethod"] | null | undefined): string {
  if (value === "trade_ledger_v1") return "trade_ledger_v1";
  if (value === "trade_ledger_required") return "trade_ledger_required";
  return "N/A";
}

function formatBenchmarkStatusLabel(value: PortfolioBenchmarkComparison["status"] | null | undefined): string {
  if (value === "computed_same_dates_same_dollars_v1") return "Computed: same dates/same dollars";
  if (value === "unavailable_same_dates_same_dollars_ledger_required") return "Unavailable: ledger required";
  return "N/A";
}

function formatBenchmarkMethodLabel(value: PortfolioBenchmarkComparison["method"] | null | undefined): string {
  if (value === "same_dates_same_dollars_v1") return "same_dates_same_dollars_v1";
  if (value === "same_dates_same_dollars_ledger_required") return "same_dates_same_dollars_ledger_required";
  return "N/A";
}

function formatRealizedStatusShort(value: PortfolioSummary["realizedPnLStatus"] | null | undefined): string {
  if (value === "computed_from_trade_ledger") return "Computed";
  if (value === "unavailable_no_trade_ledger") return "Ledger Required";
  return "N/A";
}

function formatBenchmarkStatusShort(value: PortfolioBenchmarkComparison["status"] | null | undefined): string {
  if (value === "computed_same_dates_same_dollars_v1") return "Computed";
  if (value === "unavailable_same_dates_same_dollars_ledger_required") return "Ledger Required";
  return "N/A";
}

function fmtPctPoints(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)} pp`;
}

function normalizeChartInterval(value: string | undefined, fallback: ScreenerChartInterval): ScreenerChartInterval {
  if (value === "1m") return "1m";
  if (value === "5m") return "5m";
  if (value === "15m") return "15m";
  if (value === "30m") return "30m";
  if (value === "60m") return "60m";
  if (value === "1wk") return "1wk";
  if (value === "1mo") return "1mo";
  if (value === "1d") return "1d";
  return fallback;
}

function normalizeChartRange(value: string | undefined, fallback: ScreenerChartRange): ScreenerChartRange {
  if (value === "1d") return "1d";
  if (value === "5d") return "5d";
  if (value === "1mo") return "1mo";
  if (value === "3mo") return "3mo";
  if (value === "6mo") return "6mo";
  if (value === "ytd") return "ytd";
  if (value === "1y") return "1y";
  if (value === "2y") return "2y";
  if (value === "5y") return "5y";
  if (value === "max") return "max";
  return fallback;
}

function timeframeFromInterval(interval: ScreenerChartInterval): MarketTimeframe {
  if (interval === "1wk") return "weekly";
  if (interval === "1mo") return "monthly";
  if (interval === "1d") return "daily";
  return "intraday";
}

function fmtPercent(value: number | null | undefined, decimalInput = false, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const scaled = decimalInput ? value * 100 : value;
  return `${fmtSigned(scaled, decimals)}%`;
}

function fmtText(value: string | null | undefined): string {
  if (!value) return "n/a";
  return value;
}

function inferTone(value: string): "up" | "down" | null {
  const v = value.trim();
  if (v.startsWith("+")) return "up";
  if (v.startsWith("-")) return "down";
  return null;
}

function pathFromPoints(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) return "";
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
}

function decisionClass(decision: DecisionLabel): "accumulate" | "hold" | "trim" {
  if (decision === "Accumulate") return "accumulate";
  if (decision === "Avoid") return "trim";
  return "hold";
}

function portfolioDecisionLabel(decision: DecisionLabel): "Accumulate" | "Hold" | "Trim" {
  if (decision === "Avoid") return "Trim";
  return decision;
}

function compareNumber(a: number | null, b: number | null, direction: SortDirection): number {
  const av = a === null ? Number.NEGATIVE_INFINITY : a;
  const bv = b === null ? Number.NEGATIVE_INFINITY : b;
  const base = av - bv;
  return direction === "asc" ? base : -base;
}

function compareString(a: string, b: string, direction: SortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function gainValue(row: PositionRow): number {
  return (row.unrealizedPnL ?? 0) > 0 ? row.unrealizedPnL ?? 0 : 0;
}

function lossValue(row: PositionRow): number {
  return (row.unrealizedPnL ?? 0) < 0 ? Math.abs(row.unrealizedPnL ?? 0) : 0;
}

function sortPositions(rows: PositionRow[], sort: SortState<PositionSortKey>): PositionRow[] {
  const next = [...rows];

  next.sort((a, b) => {
    if (sort.key === "ticker") return compareString(a.ticker, b.ticker, sort.direction);
    if (sort.key === "assetType") return compareString(a.assetType, b.assetType, sort.direction);
    if (sort.key === "units") return compareNumber(a.units, b.units, sort.direction);
    if (sort.key === "avgCost") return compareNumber(a.avgCost, b.avgCost, sort.direction);
    if (sort.key === "currentPrice") return compareNumber(a.currentPrice, b.currentPrice, sort.direction);
    if (sort.key === "marketValue") return compareNumber(a.marketValue, b.marketValue, sort.direction);
    if (sort.key === "costBasis") return compareNumber(a.costBasis, b.costBasis, sort.direction);
    if (sort.key === "gainValue") return compareNumber(gainValue(a), gainValue(b), sort.direction);
    if (sort.key === "lossValue") return compareNumber(lossValue(a), lossValue(b), sort.direction);
    if (sort.key === "unrealizedPnLPct") return compareNumber(a.unrealizedPnLPct, b.unrealizedPnLPct, sort.direction);
    if (sort.key === "decision") {
      return compareString(portfolioDecisionLabel(a.decision), portfolioDecisionLabel(b.decision), sort.direction);
    }
    return compareString(a.ticker, b.ticker, "asc");
  });

  return next;
}

function sortLots(rows: PortfolioLot[], sort: SortState<LotSortKey>): PortfolioLot[] {
  const next = [...rows];

  next.sort((a, b) => {
    if (sort.key === "ticker") return compareString(a.ticker, b.ticker, sort.direction);
    if (sort.key === "units") return compareNumber(a.units, b.units, sort.direction);
    if (sort.key === "unitCost") return compareNumber(a.unitCost, b.unitCost, sort.direction);
    if (sort.key === "addedAt") return compareString(a.addedAt, b.addedAt, sort.direction);
    if (sort.key === "updatedAt") return compareString(a.updatedAt, b.updatedAt, sort.direction);
    return compareString(a.ticker, b.ticker, "asc");
  });

  return next;
}

function SortHeader<T extends string>({
  label,
  sort,
  column,
  onChange,
}: {
  label: string;
  sort: SortState<T>;
  column: T;
  onChange: (next: SortState<T>) => void;
}) {
  const active = sort.key === column;
  const arrow = !active ? "" : sort.direction === "asc" ? " ▲" : " ▼";

  return (
    <button
      type="button"
      className="tfe-sort-btn"
      onClick={() => {
        if (!active) {
          onChange({ key: column, direction: "asc" });
          return;
        }
        onChange({ key: column, direction: sort.direction === "asc" ? "desc" : "asc" });
      }}
      aria-label={`Sort by ${label}`}
    >
      {label}
      {arrow}
    </button>
  );
}

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number): { x: number; y: number } {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleRad),
    y: cy + radius * Math.sin(angleRad),
  };
}

function donutSlicePath(
  cx: number,
  cy: number,
  outerRadius: number,
  innerRadius: number,
  startDeg: number,
  endDeg: number,
): string {
  const startOuter = polarToCartesian(cx, cy, outerRadius, startDeg);
  const endOuter = polarToCartesian(cx, cy, outerRadius, endDeg);
  const startInner = polarToCartesian(cx, cy, innerRadius, endDeg);
  const endInner = polarToCartesian(cx, cy, innerRadius, startDeg);

  const largeArc = endDeg - startDeg > 180 ? 1 : 0;

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${startInner.x} ${startInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${endInner.x} ${endInner.y}`,
    "Z",
  ].join(" ");
}

function buildPieSlices(positions: PositionRow[]): PieSlice[] {
  const usable = positions
    .filter((row) => row.marketValue !== null && row.marketValue > 0)
    .sort((a, b) => (b.marketValue ?? 0) - (a.marketValue ?? 0));

  const total = usable.reduce((sum, row) => sum + (row.marketValue ?? 0), 0);
  if (total <= 0) return [];

  let cursor = 0;
  const slices: PieSlice[] = [];

  for (let index = 0; index < usable.length; index += 1) {
    const row = usable[index];
    const value = row.marketValue ?? 0;
    const pct = value / total;
    const start = cursor * 360;
    const end = (cursor + pct) * 360;
    cursor += pct;

    slices.push({
      ticker: row.ticker,
      color: PIE_COLORS[index % PIE_COLORS.length],
      value,
      pct,
      path: donutSlicePath(110, 110, 100, 56, start, end),
    });
  }

  return slices;
}

function AnalysisPanel({
  ticker,
  position,
  chartLoading,
  chartError,
  chartSummary,
  chartNote,
  quoteSummary,
  chartBars,
  chartControls,
  onChartControlsChange,
  ufMetric,
}: {
  ticker: string;
  position: PositionRow | null;
  chartLoading: boolean;
  chartError: string;
  chartSummary: ChartSummary | null;
  chartNote: string;
  quoteSummary: QuoteSummary;
  chartBars: ChartBar[];
  chartControls: ScreenerChartControls;
  onChartControlsChange: (next: ScreenerChartControls) => void;
  ufMetric: UfMetric | null;
}) {
  const decisionRaw = ufMetric?.decision ?? position?.decision ?? "Hold";
  const decisionLabel = portfolioDecisionLabel(decisionRaw);
  const showInsufficientData =
    ufMetric?.decision === "Hold" &&
    (ufMetric.decisionReasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS" ||
      ufMetric.decisionReasonCode === "INSUFFICIENT_EVIDENCE_BARS");
  const hasChart = Boolean(chartSummary);
  const peerLine = "SPY IVV SPLG VTI QQQ VTV DIA VIG VYM VUG";
  const heldByLine = "KHPI TSPX OVL OVLH SPYA RSEE LFEQ HNDL BAMO OCIO";

  const statColumns = useMemo(
    () =>
      buildMarketStatColumns({
        quote: quoteSummary,
        chartSummary,
        chartBars,
      }),
    [chartBars, chartSummary, quoteSummary],
  );

  const statRowCount = useMemo(() => Math.max(...statColumns.map((column) => column.length)), [statColumns]);

  const holdingsLegend = useMemo(
    () => [
      { name: "Electronic Technology", value: 25.3, color: "#8a6fe8" },
      { name: "Technology Services", value: 19.7, color: "#2dbb9a" },
      { name: "Finance", value: 13.9, color: "#ef9f2a" },
      { name: "Retail Trade", value: 7.9, color: "#1ab7d8" },
      { name: "Health Technology", value: 7.8, color: "#e44f90" },
      { name: "Consumer Non Durables", value: 3.3, color: "#9c6ce2" },
      { name: "Energy Minerals", value: 2.4, color: "#5aa7f0" },
      { name: "Other", value: 19.7, color: "#dbdbdb" },
    ],
    [],
  );

  const donutGradient = useMemo(() => {
    let start = 0;
    const stops: string[] = [];
    for (const slice of holdingsLegend) {
      const end = start + (slice.value / 100) * 360;
      stops.push(`${slice.color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`);
      start = end;
    }
    return `conic-gradient(${stops.join(", ")})`;
  }, [holdingsLegend]);

  const topHoldings = [
    { name: "NVIDIA Corp", pct: "7.83%", sector: "Electronic Technology" },
    { name: "Apple Inc", pct: "6.46%", sector: "Electronic Technology" },
    { name: "Microsoft Corporation", pct: "5.39%", sector: "Technology Services" },
    { name: "Amazon.com Inc.", pct: "3.92%", sector: "Retail Trade" },
    { name: "Alphabet Inc - Class A", pct: "3.31%", sector: "Technology Services" },
    { name: "Alphabet Inc - Class C", pct: "2.65%", sector: "Technology Services" },
    { name: "Broadcom Inc", pct: "2.64%", sector: "Electronic Technology" },
    { name: "Meta Platforms Inc - Class A", pct: "2.63%", sector: "Technology Services" },
    { name: "Tesla Inc", pct: "2.04%", sector: "Consumer Durables" },
    { name: "Berkshire Hathaway Inc - Class B", pct: "1.48%", sector: "Finance" },
  ];

  const flowChart = useMemo(() => {
    const source = chartBars.slice(-140);
    if (source.length < 2) {
      return {
        width: 1000,
        height: 230,
        points: [] as Array<{ x: number; y: number }>,
        bars: [] as Array<{ x: number; y: number; w: number; h: number; up: boolean }>,
        minClose: null as number | null,
        maxClose: null as number | null,
        lastClose: null as number | null,
        netChange: null as number | null,
        netChangePct: null as number | null,
        avgVol: null as number | null,
      };
    }

    const width = 1000;
    const height = 230;
    const left = 22;
    const right = width - 22;
    const lineTop = 16;
    const lineBottom = 162;
    const barBase = 178;
    const barMax = 40;

    const closes = source.map((bar) => bar.close);
    const volumes = source.map((bar) => Math.max(0, bar.volume));
    const minClose = Math.min(...closes);
    const maxClose = Math.max(...closes);
    const closeSpan = Math.max(maxClose - minClose, 0.000001);
    const maxVol = Math.max(...volumes, 1);
    const firstClose = closes[0] ?? null;
    const lastClose = closes[closes.length - 1] ?? null;
    const netChange = firstClose !== null && lastClose !== null ? lastClose - firstClose : null;
    const netChangePct = netChange !== null && firstClose !== null && firstClose !== 0 ? (netChange / firstClose) * 100 : null;
    const avgVol = volumes.length > 0 ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : null;

    const points = source.map((bar, index) => {
      const ratio = index / Math.max(source.length - 1, 1);
      const x = left + ratio * (right - left);
      const y = lineBottom - ((bar.close - minClose) / closeSpan) * (lineBottom - lineTop);
      return { x, y };
    });

    const barWidth = Math.max(((right - left) / source.length) * 0.6, 1.3);
    const bars = source.map((bar, index) => {
      const ratio = index / Math.max(source.length - 1, 1);
      const x = left + ratio * (right - left) - barWidth / 2;
      const h = (Math.max(0, bar.volume) / maxVol) * barMax;
      const prevClose = index > 0 ? source[index - 1].close : bar.close;
      const up = bar.close >= prevClose;
      return {
        x,
        y: up ? barBase - h : barBase,
        w: barWidth,
        h,
        up,
      };
    });

    return { width, height, points, bars, minClose, maxClose, lastClose, netChange, netChangePct, avgVol };
  }, [chartBars]);

  const flowPath = useMemo(() => pathFromPoints(flowChart.points), [flowChart.points]);

  return (
    <div className="tfe-analysis-panel">
      <h3 style={{ margin: "0 0 8px", fontSize: "0.96rem" }}>
        {ticker} Analysis <span className={`tfe-chip ${decisionClass(decisionRaw)}`}>{decisionLabel}</span>
      </h3>

      {chartLoading ? <p className="tfe-muted">Loading analysis...</p> : null}
      {chartError ? <p className="tfe-error">{chartError}</p> : null}

      {!chartLoading && !chartError ? (
        <div className="tfe-screener-analysis-stack">
          <div className="tfe-screener-info-strip">
            <span>
              <strong>Peers:</strong> {peerLine}
            </span>
            <span>
              <strong>Held by:</strong> {heldByLine}
            </span>
          </div>

          {hasChart ? (
            <ScreenerChart
              ticker={ticker}
              bars={chartBars}
              controls={chartControls}
              loading={chartLoading}
              onControlsChange={onChartControlsChange}
            />
          ) : (
            <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
          )}

          {showInsufficientData ? (
            <p className="tfe-muted">Insufficient Data: {ufMetric?.decisionReason || "Insufficient Data"}</p>
          ) : null}

          <section className="tfe-screener-panel">
            <table className="tfe-screener-stat-table">
              <tbody>
                {Array.from({ length: statRowCount }).map((_, rowIndex) => (
                  <tr key={`screener-stat-row-${rowIndex}`}>
                    {statColumns.map((column, columnIndex) => {
                      const cell = column[rowIndex];
                      const value = fmtText(cell?.value);
                      const tone = inferTone(value);
                      return [
                        <td key={`screener-stat-cell-label-${columnIndex}-${rowIndex}`} className="k">
                          {cell?.label ?? ""}
                        </td>,
                        <td key={`screener-stat-cell-value-${columnIndex}-${rowIndex}`} className={tone ? `v tone-${tone}` : "v"}>
                          {value}
                        </td>,
                      ];
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="tfe-screener-duo">
            <section className="tfe-screener-panel">
              <div className="tfe-screener-panel-head">
                <h4>Holdings Breakdown</h4>
                <span>View Holdings as</span>
              </div>

              <div className="tfe-screener-holdings-wrap">
                <div className="tfe-screener-donut-wrap">
                  <div className="tfe-screener-donut" style={{ backgroundImage: donutGradient }} />
                </div>
                <div className="tfe-screener-legend">
                  {holdingsLegend.map((slice) => (
                    <div key={slice.name} className="tfe-screener-legend-item">
                      <span className="tfe-color-dot" style={{ background: slice.color }} />
                      <span>{slice.name}</span>
                      <span>{slice.value.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="tfe-screener-panel">
              <div className="tfe-screener-panel-head">
                <h4>Top 10 Holdings</h4>
                <span>View Holdings as</span>
              </div>
              <table className="tfe-screener-holdings-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>% Holdings</th>
                    <th>Sector</th>
                  </tr>
                </thead>
                <tbody>
                  {topHoldings.map((holding) => (
                    <tr key={`${holding.name}-${holding.pct}`}>
                      <td>{holding.name}</td>
                      <td>{holding.pct}</td>
                      <td>{holding.sector}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="tfe-screener-panel-foot">10 Holdings</div>
            </section>
          </div>

          <section className="tfe-screener-panel">
            <div className="tfe-screener-panel-head">
              <h4>Fund Flows</h4>
            </div>

            {flowChart.points.length < 2 ? (
              <p className="tfe-muted">No flow chart data available.</p>
            ) : (
              <>
                <div className="tfe-screener-flow-metrics">
                  <span>Last: {fmtNum(flowChart.lastClose, 2)}</span>
                  <span>
                    Range: {fmtNum(flowChart.minClose, 2)} - {fmtNum(flowChart.maxClose, 2)}
                  </span>
                  <span>
                    Net: {fmtSigned(flowChart.netChange ?? Number.NaN, 2)} ({fmtSigned(flowChart.netChangePct ?? Number.NaN, 2)}%)
                  </span>
                  <span>Avg Vol: {fmtCompactNumber(flowChart.avgVol)}</span>
                </div>
                <svg viewBox={`0 0 ${flowChart.width} ${flowChart.height}`} className="tfe-screener-flow-canvas" aria-label="Fund flows chart">
                  <rect x="0" y="0" width={flowChart.width} height={flowChart.height} fill="rgba(247,250,247,0.86)" />
                  {[0, 1, 2, 3, 4].map((gridIndex) => {
                    const ratio = 1 - gridIndex / 4;
                    const y = 16 + (gridIndex / 4) * 146;
                    const min = flowChart.minClose ?? 0;
                    const max = flowChart.maxClose ?? min;
                    const price = min + ratio * (max - min);

                    return (
                      <g key={`flow-grid-${gridIndex}`}>
                        <line x1="20" y1={y} x2={flowChart.width - 20} y2={y} stroke="rgba(31,56,47,0.14)" strokeWidth="1" />
                        <text x={flowChart.width - 6} y={y + 3} textAnchor="end" fontSize="10" fill="rgba(31,56,47,0.72)">
                          {fmtNum(price, 2)}
                        </text>
                      </g>
                    );
                  })}

                  {flowChart.bars.map((bar, index) => (
                    <rect
                      key={`flow-bar-${index}`}
                      x={bar.x}
                      y={bar.y}
                      width={bar.w}
                      height={bar.h}
                      fill={bar.up ? "rgba(57,182,114,0.70)" : "rgba(219,87,87,0.68)"}
                      rx="1"
                    />
                  ))}

                  <path d={flowPath} fill="none" stroke="#4d90e2" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

export default function PortfolioAdvisorManager() {
  const [inputTicker, setInputTicker] = useState("AAPL");
  const [inputUnits, setInputUnits] = useState("1");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");

  const [lots, setLots] = useState<PortfolioLot[]>([]);
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [benchmark, setBenchmark] = useState<PortfolioBenchmarkComparison | null>(null);
  const [allocatorPlan, setAllocatorPlan] = useState<AllocatorPlan | null>(null);
  const [portfolioProvenance, setPortfolioProvenance] = useState<PortfolioProvenance>({
    status: "ok",
    sourcePath: null,
    failureCount: 0,
    rows_required: 0,
    rows_valid: 0,
    missingTickers: [],
    invalidTickers: [],
    unresolvedTickers: [],
  });
  const [portfolioMeta, setPortfolioMeta] = useState<{
    source: string;
    snapshotSource: string;
    quoteSource: string;
    dataSource: string;
    runId: string;
    generatedAtUtc: string;
  }>({
    source: "",
    snapshotSource: "",
    quoteSource: "",
    dataSource: "",
    runId: "",
    generatedAtUtc: "",
  });

  const [selectedTicker, setSelectedTicker] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [lookupMetric, setLookupMetric] = useState<UfMetric | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const {
    flyoutMaximized,
    flyoutPanelStyle,
    toggleFlyoutMaximize,
    onFlyoutHeaderPointerDown,
    onFlyoutHeaderPointerMove,
    onFlyoutHeaderPointerUp,
    onFlyoutHeaderPointerCancel,
    onFlyoutResizePointerDown,
    onFlyoutResizePointerMove,
    onFlyoutResizePointerUp,
    onFlyoutResizePointerCancel,
  } = useFlyoutPanel(analysisOpen, closeAnalysis);

  const [positionSort, setPositionSort] = useState<SortState<PositionSortKey>>({ key: "ticker", direction: "asc" });
  const [lotSort, setLotSort] = useState<SortState<LotSortKey>>({ key: "addedAt", direction: "desc" });

  const [editingLotId, setEditingLotId] = useState("");
  const [editUnits, setEditUnits] = useState("");
  const [editUnitCost, setEditUnitCost] = useState("");

  async function loadPortfolio() {
    setLoading(true);
    setError("");
    setWarning("");

    try {
      const response = await fetch("/api/portfolio", { method: "GET", cache: "no-store" });
      const payload = (await response.json()) as PortfolioResponse;

      if (!response.ok) {
        setPortfolioProvenance({
          status: "ok",
          sourcePath: null,
          failureCount: 0,
          rows_required: 0,
          rows_valid: 0,
          missingTickers: [],
          invalidTickers: [],
          unresolvedTickers: [],
        });
        setError(payload.error ?? "Failed to load portfolio.");
        return;
      }

      setLots(payload.lots ?? []);
      setPositions(payload.positions ?? []);
      setSummary(payload.summary ?? null);
      setBenchmark(payload.benchmark ?? null);
      setAllocatorPlan(payload.allocatorPlan ?? null);
      setWarning(String(payload.warning ?? ""));
      setPortfolioProvenance(
        payload.provenance ?? {
          status: "ok",
          sourcePath: null,
          failureCount: 0,
          rows_required: 0,
          rows_valid: 0,
          missingTickers: [],
          invalidTickers: [],
          unresolvedTickers: [],
        },
      );
      setPortfolioMeta({
        source: String(payload.source ?? ""),
        snapshotSource: String(payload.snapshotSource ?? ""),
        quoteSource: String(payload.quoteSource ?? ""),
        dataSource: String(payload.data_source ?? ""),
        runId: String(payload.run_id ?? ""),
        generatedAtUtc: String(payload.generated_at_utc ?? ""),
      });
    } catch {
      setPortfolioProvenance({
        status: "ok",
        sourcePath: null,
        failureCount: 0,
        rows_required: 0,
        rows_valid: 0,
        missingTickers: [],
        invalidTickers: [],
        unresolvedTickers: [],
      });
      setError("Failed to load portfolio due to network error.");
    } finally {
      setLoading(false);
    }
  }

  async function loadChart(ticker: string, options?: { forceOpen?: boolean; controls?: ScreenerChartControls }) {
    const clean = normalizeTicker(ticker);
    if (!clean) return;

    const forceOpen = options?.forceOpen ?? false;
    const nextControls = options?.controls ?? chartControls;

    if (selectedTicker === clean && !forceOpen) {
      setAnalysisOpen(false);
      setSelectedTicker("");
      setLookupMetric(null);
      setChartSummary(null);
      setChartBars([]);
      setQuoteSummary({});
      setChartError("");
      setChartNote("");
      return;
    }

    setChartControls(nextControls);
    setSelectedTicker(clean);
    setAnalysisOpen(true);
    setChartLoading(true);
    setChartError("");
    setChartNote("");
    setLookupMetric(null);

    try {
      const params = new URLSearchParams({
        ticker: clean,
        interval: nextControls.interval,
        range: nextControls.range,
      });

      const res = await fetch(`/api/watchlist/chart?${params.toString()}`, {
        method: "GET",
        cache: "no-store",
      });

      const data = (await res.json()) as ChartResponse;

      if (!res.ok) {
        setChartBars([]);
        setChartSummary(null);
        setQuoteSummary({});
        setLookupMetric(null);
        setChartNote("");
        setChartError(data.error ?? "Failed to load chart.");
        return;
      }

      setChartBars(Array.isArray(data.bars) ? data.bars : []);
      setChartSummary(data.summary ?? null);
      setQuoteSummary(data.quote ?? {});
      setLookupMetric(data.ufMetric ?? null);
      setChartNote(data.note ?? "");
      const resolvedInterval = normalizeChartInterval(data.interval, nextControls.interval);
      const resolvedRange = normalizeChartRange(data.range, nextControls.range);
      setChartControls({
        ...nextControls,
        interval: resolvedInterval,
        range: resolvedRange,
        timeframe: timeframeFromInterval(resolvedInterval),
      });
      setMessage(`Loaded ${clean} analysis.`);
    } catch {
      setChartBars([]);
      setChartSummary(null);
      setQuoteSummary({});
      setLookupMetric(null);
      setChartNote("");
      setChartError("Failed to load chart due to network error.");
    } finally {
      setChartLoading(false);
    }
  }

  function closeAnalysis() {
    setAnalysisOpen(false);
    setSelectedTicker("");
  }

  async function onLookup() {
    const ticker = normalizeTicker(inputTicker);

    if (!ticker) {
      setError("Enter a ticker symbol.");
      return;
    }

    setError("");
    await loadChart(ticker, { forceOpen: true });
  }

  async function onAddToPortfolio() {
    const ticker = normalizeTicker(inputTicker);
    const units = toNumber(inputUnits);

    if (!ticker) {
      setError("Ticker is required.");
      return;
    }

    if (!(units > 0)) {
      setError("Units must be greater than zero.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    let resolvedUnitCost = 0;

    if (selectedTicker === ticker && chartSummary && chartSummary.close > 0) {
      resolvedUnitCost = chartSummary.close;
    }

    try {
      const body: { ticker: string; units: number; unitCost?: number } = {
        ticker,
        units,
      };

      if (resolvedUnitCost > 0) {
        body.unitCost = resolvedUnitCost;
      }

      const res = await fetch("/api/portfolio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = (await res.json()) as { error?: string };

      if (!res.ok) {
        setError(data.error ?? "Failed to add portfolio lot.");
        return;
      }

      setMessage(`${ticker} added to portfolio.`);
      setInputUnits("1");
      await loadPortfolio();
    } catch {
      setError("Failed to add portfolio lot due to network error.");
    } finally {
      setLoading(false);
    }
  }

  function onStartEdit(lot: PortfolioLot) {
    setEditingLotId(lot.id);
    setEditUnits(String(lot.units));
    setEditUnitCost(String(lot.unitCost));
  }

  function onCancelEdit() {
    setEditingLotId("");
    setEditUnits("");
    setEditUnitCost("");
  }

  async function onSaveEdit() {
    if (!editingLotId) return;

    const units = toNumber(editUnits);
    const unitCost = toNumber(editUnitCost);

    if (!(units > 0)) {
      setError("Edited units must be greater than zero.");
      return;
    }

    if (!(unitCost >= 0)) {
      setError("Edited unit cost must be zero or greater.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/portfolio", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: editingLotId, units, unitCost }),
      });

      const data = (await res.json()) as { error?: string };

      if (!res.ok) {
        setError(data.error ?? "Failed to update lot.");
        return;
      }

      setMessage("Portfolio lot updated.");
      onCancelEdit();
      await loadPortfolio();
    } catch {
      setError("Failed to update lot due to network error.");
    } finally {
      setLoading(false);
    }
  }

  async function onRemoveLot(lotId: string) {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`/api/portfolio?id=${encodeURIComponent(lotId)}`, { method: "DELETE" });
      const data = (await res.json()) as { error?: string };

      if (!res.ok) {
        setError(data.error ?? "Failed to remove lot.");
        return;
      }

      setMessage("Portfolio lot removed.");
      if (editingLotId === lotId) onCancelEdit();
      await loadPortfolio();
    } catch {
      setError("Failed to remove lot due to network error.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPortfolio();
  }, []);

  useEffect(() => {
    if (!analysisOpen) return;

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeAnalysis();
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("keydown", handleKey);
    };
  }, [analysisOpen]);

  const sortedPositions = useMemo(() => sortPositions(positions, positionSort), [positions, positionSort]);
  const sortedLots = useMemo(() => sortLots(lots, lotSort), [lots, lotSort]);
  const freshness = useMemo(() => freshnessBadge(portfolioMeta.generatedAtUtc || null), [portfolioMeta.generatedAtUtc]);

  const selectedPosition = useMemo(
    () => sortedPositions.find((row) => row.ticker === selectedTicker) ?? null,
    [sortedPositions, selectedTicker],
  );

  const activeUfMetric = useMemo(() => {
    if (lookupMetric) return lookupMetric;
    if (!selectedPosition) return null;

    return {
      ticker: selectedPosition.ticker,
      decision: selectedPosition.decision,
      decisionReason: selectedPosition.decisionReason,
      decisionReasonCode: selectedPosition.decisionReasonCode,
      classification: selectedPosition.classification,
      price: selectedPosition.currentPrice,
      regime: "UNKNOWN",
      S_UF: selectedPosition.S_UF,
      R_UF: selectedPosition.R_UF,
      barCount: selectedPosition.barCount,
      minBarsForAccumulate: selectedPosition.minBarsForAccumulate,
      stability_score: null,
      max_dd: null,
    } as UfMetric;
  }, [lookupMetric, selectedPosition]);

  const pieSlices = useMemo(() => buildPieSlices(sortedPositions), [sortedPositions]);
  const actionableAllocatorRows = useMemo(
    () => (allocatorPlan?.rows ?? []).filter((row) => row.action !== "HOLD"),
    [allocatorPlan],
  );

  const assetMixRows = useMemo(() => {
    const order: Array<PositionRow["assetType"]> = ["Equities", "ETF", "Index", "Crypto", "Other"];
    const totals = new Map<PositionRow["assetType"], number>([
      ["Equities", 0],
      ["ETF", 0],
      ["Index", 0],
      ["Crypto", 0],
      ["Other", 0],
    ]);

    for (const row of sortedPositions) {
      const value = row.marketValue ?? row.costBasis;
      if (!Number.isFinite(value) || value <= 0) continue;
      totals.set(row.assetType, (totals.get(row.assetType) ?? 0) + value);
    }

    let total = 0;
    for (const value of totals.values()) {
      total += value;
    }

    return order.map((type) => {
      const value = totals.get(type) ?? 0;
      const pct = total > 0 ? value / total : 0;
      return { type, value, pct };
    });
  }, [sortedPositions]);

  return (
    <div className="section-stack portfolio-advisor-view">
      <section className="tfe-panel">
        <h2 style={{ margin: "0 0 8px" }}>Portfolio Lookup and Add</h2>

        <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "minmax(0, 1.6fr) 200px auto auto" }}>
          <input
            className="tfe-input"
            value={inputTicker}
            onChange={(event) => setInputTicker(event.target.value.toUpperCase())}
            placeholder="Ticker"
            autoComplete="off"
            spellCheck={false}
          />

          <input
            className="tfe-input"
            value={inputUnits}
            onChange={(event) => setInputUnits(event.target.value)}
            placeholder="Units"
            inputMode="decimal"
          />

          <button className="btn btn-ghost" type="button" onClick={() => void onLookup()} disabled={loading || chartLoading}>
            {chartLoading ? "Looking..." : "Lookup"}
          </button>

          <button className="btn btn-primary" type="button" onClick={() => void onAddToPortfolio()} disabled={loading}>
            {loading ? "Saving..." : "Add to Portfolio"}
          </button>
        </div>

        <p className="tfe-muted" style={{ marginTop: 8 }}>
          Units are required. Add uses looked-up close price when available, otherwise current snapshot price.
        </p>

        <div className="tfe-toolbar-actions">
          <button className="btn btn-ghost" type="button" onClick={() => void loadPortfolio()} disabled={loading}>
            Reload Portfolio
          </button>
          {message ? <span className="tfe-success">{message}</span> : null}
          {error ? <span className="tfe-error">{error}</span> : null}
        </div>
        {warning ? (
          <p className="tfe-error" style={{ marginTop: 8, marginBottom: 0 }}>
            {warning}
          </p>
        ) : null}
      </section>

      <section className="tfe-panel">
        <h2 style={{ margin: "0 0 6px" }}>Portfolio Confidence</h2>
        <p className="tfe-muted" style={{ margin: "0 0 10px" }}>
          Quick status for runtime provenance and contract readiness.
        </p>
        <div className="tfe-status-row">
          <div className={`tfe-status-pill ${portfolioMeta.dataSource === "postgres" ? "is-good" : "is-warn"}`}>
            <span className="k">Data Source</span>
            <span className="v">{portfolioMeta.dataSource || "N/A"}</span>
          </div>
          <div className={`tfe-status-pill ${freshness.tone}`}>
            <span className="k">Freshness</span>
            <span className="v">{freshness.label}</span>
          </div>
          <div className={`tfe-status-pill ${summary?.realizedPnLStatus === "computed_from_trade_ledger" ? "is-good" : "is-warn"}`}>
            <span className="k">Realized P/L</span>
            <span className="v">{formatRealizedStatusShort(summary?.realizedPnLStatus)}</span>
          </div>
          <div
            className={`tfe-status-pill ${
              benchmark?.status === "computed_same_dates_same_dollars_v1" ? "is-good" : "is-warn"
            }`}
          >
            <span className="k">Benchmark Compare</span>
            <span className="v">{formatBenchmarkStatusShort(benchmark?.status)}</span>
          </div>
          <div className={`tfe-status-pill ${portfolioProvenance.status === "ok" ? "is-good" : "is-warn"}`}>
            <span className="k">Published Provenance</span>
            <span className="v">
              {portfolioProvenance.status === "ok"
                ? "Complete"
                : `Partial (${portfolioProvenance.unresolvedTickers.map((row) => row.ticker).join(", ")})`}
            </span>
          </div>
        </div>
      </section>

      <section className="section-stack">
        <h2>Runtime Provenance</h2>
        <section className="tfe-summary-grid">
        <article className="tfe-summary-card">
          <div className="k">Data Source</div>
          <div className="v">{portfolioMeta.dataSource || "N/A"}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Runtime Run ID</div>
          <div className="v" title={portfolioMeta.runId || "N/A"}>{portfolioMeta.runId || "N/A"}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Generated (UTC)</div>
          <div className="v" title={portfolioMeta.generatedAtUtc || "N/A"}>{portfolioMeta.generatedAtUtc || "N/A"}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Data Freshness</div>
          <div className="v">{formatFreshnessAge(portfolioMeta.generatedAtUtc || null)}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Snapshot Source</div>
          <div className="v" title={portfolioMeta.snapshotSource || "N/A"}>{portfolioMeta.snapshotSource || "N/A"}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Quote Source</div>
          <div className="v" title={portfolioMeta.quoteSource || "N/A"}>{portfolioMeta.quoteSource || "N/A"}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Published Provenance</div>
          <div className="v">{portfolioProvenance.status === "ok" ? "Complete" : "Partial"}</div>
          <div className="k" style={{ marginTop: 6 }}>
            {portfolioProvenance.unresolvedTickers.length > 0
              ? portfolioProvenance.unresolvedTickers.map((row) => row.ticker).join(", ")
              : "All saved tickers resolved"}
          </div>
        </article>
        </section>
      </section>

      <section className="section-stack">
        <h2>Performance And Benchmark Snapshot</h2>
        <section className="tfe-summary-grid">
        <article className="tfe-summary-card">
          <div className="k">Total Market Value</div>
          <div className="v">{fmtCurrency(summary?.totalMarketValue ?? null)}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Total Cost Basis</div>
          <div className="v">{fmtCurrency(summary?.totalCostBasis ?? null)}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Unrealized P/L</div>
          <div className={`v ${(summary?.totalUnrealizedPnL ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtSignedCurrency(summary?.totalUnrealizedPnL ?? null)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Unrealized P/L %</div>
          <div className={`v ${(summary?.totalUnrealizedPnLPct ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtPct(summary?.totalUnrealizedPnLPct ?? null)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Realized P/L</div>
          <div className={`v ${(summary?.realizedPnL ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtSignedCurrency(summary?.realizedPnL ?? null)}
          </div>
          <div className="k" style={{ marginTop: 6 }}>
            {formatRealizedStatusLabel(summary?.realizedPnLStatus)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Realized P/L %</div>
          <div className={`v ${(summary?.realizedPnLPct ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtPct(summary?.realizedPnLPct ?? null)}
          </div>
          <div className="k" style={{ marginTop: 6 }}>
            {formatRealizedMethodLabel(summary?.realizedPnLMethod)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Benchmark ({benchmark?.symbol ?? "SPY"})</div>
          <div className={`v ${(benchmark?.benchmarkReturnPct ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtPct(benchmark?.benchmarkReturnPct ?? null)}
          </div>
          <div className="k" style={{ marginTop: 6 }}>
            {formatBenchmarkStatusLabel(benchmark?.status)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Relative vs SPY</div>
          <div className={`v ${(benchmark?.relativeReturnPctPoints ?? 0) >= 0 ? "good" : "bad"}`}>
            {fmtPctPoints(benchmark?.relativeReturnPctPoints ?? null)}
          </div>
          <div className="k" style={{ marginTop: 6 }}>
            {formatBenchmarkMethodLabel(benchmark?.method)}
          </div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Positions</div>
          <div className="v">{summary?.totalPositions ?? 0}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Lots</div>
          <div className="v">{summary?.totalLots ?? 0}</div>
        </article>
        </section>
      </section>

      <section className="tfe-grid-2">
        <article className="tfe-panel">
          <h3>Portfolio Allocation (By Market Value)</h3>

          {pieSlices.length === 0 ? (
            <p className="tfe-muted">No priced positions yet.</p>
          ) : (
            <>
              <svg viewBox="0 0 220 220" className="tfe-donut" aria-label="Portfolio allocation donut chart">
                {pieSlices.map((slice) => (
                  <path key={slice.ticker} d={slice.path} fill={slice.color} stroke="rgba(255,255,255,0.6)" strokeWidth="1" />
                ))}
                <circle cx="110" cy="110" r="46" fill="rgba(248,252,247,0.95)" />
                <text x="110" y="104" textAnchor="middle" fontSize="12" fill="#2a5f49" fontWeight="700">
                  Total
                </text>
                <text x="110" y="123" textAnchor="middle" fontSize="11" fill="#2a5f49">
                  {fmtCompactNumber(summary?.totalMarketValue ?? null)}
                </text>
              </svg>

              <div className="tfe-legend">
                {pieSlices.map((slice) => (
                  <div key={slice.ticker} className="tfe-legend-item">
                    <span className="tfe-color-dot" style={{ background: slice.color }} />
                    <span>{slice.ticker}</span>
                    <span>{`${(slice.pct * 100).toFixed(1)}%`}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </article>

        <article className="tfe-panel">
          <h3>Asset Mix</h3>
          <div className="tfe-table-wrap" style={{ maxHeight: 280 }}>
            <table className="tfe-table" style={{ minWidth: 560 }}>
              <thead>
                <tr>
                  <th>Type</th>
                  <th style={{ textAlign: "right" }}>Current %</th>
                  <th style={{ textAlign: "right" }}>Current Value</th>
                  <th style={{ textAlign: "right" }}>Target</th>
                  <th style={{ textAlign: "right" }}>Diff</th>
                </tr>
              </thead>
              <tbody>
                {assetMixRows.map((row) => (
                  <tr key={row.type}>
                    <td>{row.type}</td>
                    <td style={{ textAlign: "right" }}>{(row.pct * 100).toFixed(1)}%</td>
                    <td style={{ textAlign: "right" }}>{fmtCurrency(row.value)}</td>
                    <td style={{ textAlign: "right" }}>-</td>
                    <td style={{ textAlign: "right" }}>-</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="tfe-muted" style={{ marginTop: 8 }}>
            Target and diff are placeholders until target-allocation settings are added.
          </p>
        </article>
      </section>

      <section className="section-stack">
        <h2>PFSC Rebalance Plan</h2>

        <section className="tfe-summary-grid">
          <article className="tfe-summary-card">
            <div className="k">Policy Status</div>
            <div className="v">{allocatorPlan?.status ?? "n/a"}</div>
          </article>
          <article className="tfe-summary-card">
            <div className="k">Buy Budget</div>
            <div className="v">{fmtCurrency(allocatorPlan?.totals.buyDollar ?? null)}</div>
          </article>
          <article className="tfe-summary-card">
            <div className="k">Trim Budget</div>
            <div className="v">{fmtCurrency(allocatorPlan?.totals.trimDollar ?? null)}</div>
          </article>
          <article className="tfe-summary-card">
            <div className="k">Exit Budget</div>
            <div className="v">{fmtCurrency(allocatorPlan?.totals.exitDollar ?? null)}</div>
          </article>
          <article className="tfe-summary-card">
            <div className="k">Threshold</div>
            <div className="v">
              {allocatorPlan ? `${allocatorPlan.rebalanceThresholdPctPoints.toFixed(1)} pp` : "n/a"}
            </div>
          </article>
          <article className="tfe-summary-card">
            <div className="k">Actions</div>
            <div className="v">{actionableAllocatorRows.length}</div>
          </article>
        </section>

        {allocatorPlan?.missingPriceTickers?.length ? (
          <p className="tfe-muted">
            Missing priced positions: {allocatorPlan.missingPriceTickers.join(", ")}
          </p>
        ) : null}

        <div className="tfe-table-wrap" style={{ maxHeight: 420 }}>
          <table className="tfe-table" style={{ minWidth: 1120 }}>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Action</th>
                <th style={{ textAlign: "right" }}>Current %</th>
                <th style={{ textAlign: "right" }}>Target %</th>
                <th style={{ textAlign: "right" }}>Drift (pp)</th>
                <th style={{ textAlign: "right" }}>Rebalance $</th>
                <th style={{ textAlign: "right" }}>Units</th>
                <th style={{ textAlign: "right" }}>Confidence</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {actionableAllocatorRows.length === 0 ? (
                <tr>
                  <td colSpan={9}>No rebalance actions right now.</td>
                </tr>
              ) : (
                actionableAllocatorRows.map((row) => (
                  <tr key={`${row.ticker}-${row.action}`}>
                    <td>{row.ticker}</td>
                    <td>{row.action}</td>
                    <td style={{ textAlign: "right" }}>{row.currentWeightPct.toFixed(2)}%</td>
                    <td style={{ textAlign: "right" }}>{row.targetWeightPct.toFixed(2)}%</td>
                    <td style={{ textAlign: "right" }}>{row.driftPctPoints.toFixed(2)}</td>
                    <td style={{ textAlign: "right" }}>{fmtSignedCurrency(row.rebalanceDollar)}</td>
                    <td style={{ textAlign: "right" }}>{row.rebalanceUnits == null ? "n/a" : row.rebalanceUnits.toFixed(4)}</td>
                    <td style={{ textAlign: "right" }}>{row.confidence.toFixed(3)}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section-stack">
        <h2>Portfolio Positions</h2>

        <div className="tfe-table-wrap" style={{ maxHeight: 620 }}>
          <table className="tfe-table">
            <thead>
              <tr>
                <th>
                  <SortHeader label="Ticker" column="ticker" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th>
                  <SortHeader label="Asset Type" column="assetType" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Units" column="units" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Avg Cost" column="avgCost" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Price" column="currentPrice" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Market Value" column="marketValue" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Cost Basis" column="costBasis" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Gain $" column="gainValue" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Loss $" column="lossValue" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Net P/L %" column="unrealizedPnLPct" sort={positionSort} onChange={setPositionSort} />
                </th>
                <th>
                  <SortHeader label="Decision" column="decision" sort={positionSort} onChange={setPositionSort} />
                </th>
              </tr>
            </thead>

            <tbody>
              {sortedPositions.length === 0 ? (
                <tr>
                  <td colSpan={11}>No positions yet.</td>
                </tr>
              ) : (
                sortedPositions.map((row, rowIndex) => {
                  const active = analysisOpen && selectedTicker === row.ticker;
                  const decisionLabel = portfolioDecisionLabel(row.decision);
                  const gain = gainValue(row);
                  const loss = lossValue(row);

                  return (
                    <tr key={`${row.ticker}-${row.assetType}-${row.barCount}-${rowIndex}`} className={active ? "active-row" : ""}>
                      <td>
                        <button
                          type="button"
                          className="tfe-row-button"
                          onClick={() => void loadChart(row.ticker)}
                          title={`Open analysis for ${row.ticker}`}
                        >
                          {row.ticker}
                        </button>
                      </td>
                      <td>{row.assetType}</td>
                      <td style={{ textAlign: "right" }}>{fmtNum(row.units, 4)}</td>
                      <td style={{ textAlign: "right" }}>{fmtCurrency(row.avgCost)}</td>
                      <td style={{ textAlign: "right" }}>{fmtCurrency(row.currentPrice)}</td>
                      <td style={{ textAlign: "right" }}>{fmtCurrency(row.marketValue)}</td>
                      <td style={{ textAlign: "right" }}>{fmtCurrency(row.costBasis)}</td>
                      <td style={{ textAlign: "right", color: gain > 0 ? "#1b6c46" : "inherit" }}>
                        {gain > 0 ? fmtCurrency(gain) : "-"}
                      </td>
                      <td style={{ textAlign: "right", color: loss > 0 ? "#9a3030" : "inherit" }}>
                        {loss > 0 ? `-${fmtCurrency(loss)}` : "-"}
                      </td>
                      <td style={{ textAlign: "right", color: (row.unrealizedPnLPct ?? 0) >= 0 ? "#1b6c46" : "#9a3030" }}>
                        {fmtPct(row.unrealizedPnLPct)}
                      </td>
                      <td>
                        <span className={`tfe-chip ${decisionClass(row.decision)}`}>{decisionLabel}</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {analysisOpen && selectedTicker ? (
        <ClientPortal>
          <div className="tfe-flyout-backdrop" role="presentation" onClick={() => closeAnalysis()}>
            <section
              className="tfe-flyout-panel"
              role="dialog"
              aria-modal="true"
              aria-label={`${selectedTicker} analysis`}
              onClick={(event) => event.stopPropagation()}
              style={flyoutPanelStyle}
            >
              <header
                className={`tfe-flyout-header tfe-flyout-drag-handle${flyoutMaximized ? " is-maximized" : ""}`}
                onPointerDown={onFlyoutHeaderPointerDown}
                onPointerMove={onFlyoutHeaderPointerMove}
                onPointerUp={onFlyoutHeaderPointerUp}
                onPointerCancel={onFlyoutHeaderPointerCancel}
              >
                <h2 style={{ margin: 0, fontSize: "1rem" }}>{selectedTicker} Details</h2>
                <div className="tfe-flyout-actions">
                  <button type="button" className="btn btn-ghost tfe-flyout-btn" data-flyout-control="true" onClick={() => toggleFlyoutMaximize()}>
                    {flyoutMaximized ? "Restore" : "Maximize"}
                  </button>
                  <button type="button" className="btn btn-ghost tfe-flyout-btn" data-flyout-control="true" onClick={() => closeAnalysis()}>
                    Close
                  </button>
                </div>
              </header>

              <div className="tfe-flyout-body">
                <AnalysisPanel
                  ticker={selectedTicker}
                  position={selectedPosition}
                  chartLoading={chartLoading}
                  chartError={chartError}
                  chartSummary={chartSummary}
                  chartNote={chartNote}
                  quoteSummary={quoteSummary}
                  chartBars={chartBars}
                  chartControls={chartControls}
                  onChartControlsChange={(next) => {
                    void loadChart(selectedTicker, { forceOpen: true, controls: next });
                  }}
                  ufMetric={activeUfMetric}
                />
              </div>
              <div
                className={`tfe-flyout-resize-handle${flyoutMaximized ? " is-disabled" : ""}`}
                data-flyout-control="true"
                role="presentation"
                onPointerDown={onFlyoutResizePointerDown}
                onPointerMove={onFlyoutResizePointerMove}
                onPointerUp={onFlyoutResizePointerUp}
                onPointerCancel={onFlyoutResizePointerCancel}
              />
            </section>
          </div>
        </ClientPortal>
      ) : null}

      <section className="section-stack">
        <h2>Manual Lots (Edit or Remove)</h2>

        <div className="tfe-table-wrap" style={{ maxHeight: 440 }}>
          <table className="tfe-table" style={{ minWidth: 980 }}>
            <thead>
              <tr>
                <th>
                  <SortHeader label="Ticker" column="ticker" sort={lotSort} onChange={setLotSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Units" column="units" sort={lotSort} onChange={setLotSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Unit Cost" column="unitCost" sort={lotSort} onChange={setLotSort} />
                </th>
                <th>
                  <SortHeader label="Added" column="addedAt" sort={lotSort} onChange={setLotSort} />
                </th>
                <th>
                  <SortHeader label="Updated" column="updatedAt" sort={lotSort} onChange={setLotSort} />
                </th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {sortedLots.length === 0 ? (
                <tr>
                  <td colSpan={6}>No lots yet.</td>
                </tr>
              ) : (
                sortedLots.map((lot) => {
                  const editing = editingLotId === lot.id;

                  return (
                    <tr key={lot.id}>
                      <td>{lot.ticker}</td>
                      <td style={{ textAlign: "right" }}>{fmtNum(lot.units, 4)}</td>
                      <td style={{ textAlign: "right" }}>{fmtCurrency(lot.unitCost)}</td>
                      <td>{new Date(lot.addedAt).toLocaleString()}</td>
                      <td>{new Date(lot.updatedAt).toLocaleString()}</td>
                      <td>
                        {editing ? (
                          <div className="tfe-inline-edit">
                            <input
                              className="tfe-input"
                              value={editUnits}
                              onChange={(event) => setEditUnits(event.target.value)}
                              placeholder="Units"
                            />
                            <input
                              className="tfe-input"
                              value={editUnitCost}
                              onChange={(event) => setEditUnitCost(event.target.value)}
                              placeholder="Unit cost"
                            />
                            <button className="btn btn-primary" type="button" onClick={() => void onSaveEdit()}>
                              Save
                            </button>
                            <button className="btn btn-ghost" type="button" onClick={() => onCancelEdit()}>
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="tfe-toolbar-actions">
                            <button className="btn btn-ghost" type="button" onClick={() => onStartEdit(lot)}>
                              Edit
                            </button>
                            <button className="btn btn-ghost" type="button" onClick={() => void onRemoveLot(lot.id)}>
                              Remove
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
