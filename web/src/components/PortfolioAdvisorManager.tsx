"use client";

import { Fragment, useEffect, useMemo, useState } from "react";

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

type PortfolioResponse = {
  lots: PortfolioLot[];
  positions: PositionRow[];
  summary: PortfolioSummary;
  allocatorPlan?: AllocatorPlan;
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

type QuoteSummary = {
  marketCap?: number | null;
  peRatio?: number | null;
  beta?: number | null;
  eps?: number | null;
  avgVolume?: number | null;
  dividendYield?: number | null;
  target1Y?: number | null;
  bid?: number | null;
  ask?: number | null;
};

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

function linePath(points: number[], width: number, height: number, pad: number): string {
  if (points.length < 2) return "";

  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (const p of points) {
    if (p < min) min = p;
    if (p > max) max = p;
  }

  const span = max - min || 1;
  const usableW = width - pad * 2;
  const usableH = height - pad * 2;

  return points
    .map((p, i) => {
      const x = pad + (i / (points.length - 1)) * usableW;
      const y = height - pad - ((p - min) / span) * usableH;
      return `${x},${y}`;
    })
    .join(" ");
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
  chartLoading,
  chartError,
  chartSummary,
  chartNote,
  quoteSummary,
  chartBars,
  ufMetric,
}: {
  ticker: string;
  chartLoading: boolean;
  chartError: string;
  chartSummary: ChartSummary | null;
  chartNote: string;
  quoteSummary: QuoteSummary;
  chartBars: ChartBar[];
  ufMetric: UfMetric | null;
}) {
  const closeSeries = useMemo(() => chartBars.map((b) => b.close), [chartBars]);
  const sparkPath = useMemo(() => linePath(closeSeries, 960, 260, 16), [closeSeries]);
  const decisionLabel = ufMetric ? portfolioDecisionLabel(ufMetric.decision) : null;
  const showInsufficientData =
    ufMetric?.decision === "Hold" && ufMetric.decisionReasonCode === "INSUFFICIENT_EVIDENCE_BARS";
  const ufConfidence = ufMetric ? (ufMetric.S_UF + ufMetric.R_UF) / 2 : null;
  const hasChart = Boolean(chartSummary);

  return (
    <div className="tfe-analysis-panel">
      <h3 style={{ margin: "0 0 8px", fontSize: "0.94rem" }}>{ticker} Analysis</h3>

      {chartLoading ? <p className="tfe-muted">Loading analysis...</p> : null}
      {chartError ? <p className="tfe-error">{chartError}</p> : null}

      {!chartLoading && !chartError ? (
        <div className="tfe-analysis-grid">
          <div>
            {hasChart ? (
              <>
                <div className="tfe-metric-grid">
                  <div>Open: {fmtNum(chartSummary?.open, 2)}</div>
                  <div>High: {fmtNum(chartSummary?.high, 2)}</div>
                  <div>Low: {fmtNum(chartSummary?.low, 2)}</div>
                  <div>Prev Close: {fmtNum(chartSummary?.prevClose, 2)}</div>
                  <div>Change $: {fmtSigned(chartSummary?.change ?? 0, 2)}</div>
                  <div>Change %: {fmtSigned(chartSummary?.changePct ?? 0, 2)}%</div>
                  <div>52W High: {fmtNum(chartSummary?.high52, 2)}</div>
                  <div>52W Low: {fmtNum(chartSummary?.low52, 2)}</div>
                  <div>Mkt Cap: {fmtCompactNumber(quoteSummary.marketCap)}</div>
                  <div>PE: {fmtNum(quoteSummary.peRatio ?? null, 2)}</div>
                  <div>Beta: {fmtNum(quoteSummary.beta ?? null, 2)}</div>
                  <div>EPS: {fmtNum(quoteSummary.eps ?? null, 2)}</div>
                  <div>Avg Vol: {fmtCompactNumber(quoteSummary.avgVolume)}</div>
                  <div>
                    Div Yield: {quoteSummary.dividendYield == null ? "N/A" : `${(quoteSummary.dividendYield * 100).toFixed(2)}%`}
                  </div>
                  <div>Bid: {fmtNum(quoteSummary.bid ?? null, 2)}</div>
                  <div>Ask: {fmtNum(quoteSummary.ask ?? null, 2)}</div>
                </div>

                <svg viewBox="0 0 960 260" className="tfe-chart" aria-label={`${ticker} chart`}>
                  <defs>
                    <linearGradient id={`lineGradPortfolio-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(107,188,137,0.95)" />
                      <stop offset="100%" stopColor="rgba(107,188,137,0.2)" />
                    </linearGradient>
                  </defs>
                  <rect x="0" y="0" width="960" height="260" fill="rgba(16, 36, 27, 0.08)" />
                  <polyline fill="none" stroke={`url(#lineGradPortfolio-${ticker})`} strokeWidth="2.8" points={sparkPath} />
                </svg>
              </>
            ) : (
              <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
            )}
          </div>

          <aside className="tfe-signal-card">
            <h4>Portfolio Signal Card</h4>

            <div className="tfe-kv">Decision</div>
            <div className="tfe-value">{decisionLabel ?? "Unavailable"}</div>
            {decisionLabel ? <div className={`tfe-chip ${decisionClass(ufMetric!.decision)}`}>{decisionLabel}</div> : null}

            <div style={{ marginTop: 10 }}>
              <div className="tfe-kv">UF Confidence</div>
              <div className="tfe-value">{fmtNum(ufConfidence, 3)}</div>
              <div style={{ fontSize: "0.8rem" }}>
                S_UF {fmtNum(ufMetric?.S_UF ?? null, 3)} | R_UF {fmtNum(ufMetric?.R_UF ?? null, 3)}
              </div>
            </div>

            {showInsufficientData ? (
              <div style={{ marginTop: 10 }}>
                <div className="tfe-kv">Insufficient Data</div>
                <div style={{ fontSize: "0.8rem" }}>{ufMetric?.decisionReason || "Insufficient Data"}</div>
              </div>
            ) : null}
          </aside>
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

  const [lots, setLots] = useState<PortfolioLot[]>([]);
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [allocatorPlan, setAllocatorPlan] = useState<AllocatorPlan | null>(null);

  const [selectedTicker, setSelectedTicker] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [lookupMetric, setLookupMetric] = useState<UfMetric | null>(null);

  const [positionSort, setPositionSort] = useState<SortState<PositionSortKey>>({ key: "ticker", direction: "asc" });
  const [lotSort, setLotSort] = useState<SortState<LotSortKey>>({ key: "addedAt", direction: "desc" });

  const [editingLotId, setEditingLotId] = useState("");
  const [editUnits, setEditUnits] = useState("");
  const [editUnitCost, setEditUnitCost] = useState("");

  async function loadPortfolio() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/portfolio", { method: "GET", cache: "no-store" });
      const payload = (await response.json()) as PortfolioResponse;

      if (!response.ok) {
        setError(payload.error ?? "Failed to load portfolio.");
        return;
      }

      setLots(payload.lots ?? []);
      setPositions(payload.positions ?? []);
      setSummary(payload.summary ?? null);
      setAllocatorPlan(payload.allocatorPlan ?? null);
    } catch {
      setError("Failed to load portfolio due to network error.");
    } finally {
      setLoading(false);
    }
  }

  async function loadChart(ticker: string, options?: { forceOpen?: boolean }) {
    const clean = normalizeTicker(ticker);
    if (!clean) return;

    const forceOpen = options?.forceOpen ?? false;

    if (selectedTicker === clean && !forceOpen) {
      setSelectedTicker("");
      setLookupMetric(null);
      setChartSummary(null);
      setChartBars([]);
      setQuoteSummary({});
      setChartError("");
      setChartNote("");
      return;
    }

    setSelectedTicker(clean);
    setChartLoading(true);
    setChartError("");
    setChartNote("");
    setLookupMetric(null);

    try {
      const res = await fetch(`/api/watchlist/chart?ticker=${encodeURIComponent(clean)}&days=365`, {
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

  const sortedPositions = useMemo(() => sortPositions(positions, positionSort), [positions, positionSort]);
  const sortedLots = useMemo(() => sortLots(lots, lotSort), [lots, lotSort]);

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

  const selectedTickerInPositions = useMemo(
    () => sortedPositions.some((position) => position.ticker === selectedTicker),
    [sortedPositions, selectedTicker],
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
    <div className="section-stack">
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
      </section>

      {selectedTicker && !selectedTickerInPositions ? (
        <section className="tfe-panel">
          <AnalysisPanel
            ticker={selectedTicker}
            chartLoading={chartLoading}
            chartError={chartError}
            chartSummary={chartSummary}
            chartNote={chartNote}
            quoteSummary={quoteSummary}
            chartBars={chartBars}
            ufMetric={activeUfMetric}
          />
        </section>
      ) : null}

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
          <div className="k">Positions</div>
          <div className="v">{summary?.totalPositions ?? 0}</div>
        </article>

        <article className="tfe-summary-card">
          <div className="k">Lots</div>
          <div className="v">{summary?.totalLots ?? 0}</div>
        </article>
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
                  const active = selectedTicker === row.ticker;
                  const decisionLabel = portfolioDecisionLabel(row.decision);
                  const gain = gainValue(row);
                  const loss = lossValue(row);

                  return (
                    <Fragment key={`${row.ticker}-${row.assetType}-${row.barCount}-${rowIndex}`}>
                      <tr className={active ? "active-row" : ""}>
                        <td>
                          <button
                            type="button"
                            className="tfe-row-button"
                            onClick={() => void loadChart(row.ticker)}
                            title={`Toggle analysis for ${row.ticker}`}
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

                      {active ? (
                        <tr>
                          <td colSpan={11} style={{ padding: 0 }}>
                            <AnalysisPanel
                              ticker={row.ticker}
                              chartLoading={chartLoading && selectedTicker === row.ticker}
                              chartError={selectedTicker === row.ticker ? chartError : ""}
                              chartSummary={selectedTicker === row.ticker ? chartSummary : null}
                              chartNote={selectedTicker === row.ticker ? chartNote : ""}
                              quoteSummary={selectedTicker === row.ticker ? quoteSummary : {}}
                              chartBars={selectedTicker === row.ticker ? chartBars : []}
                              ufMetric={selectedTicker === row.ticker ? activeUfMetric : null}
                            />
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

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
