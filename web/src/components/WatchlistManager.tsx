"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
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

type WatchlistMetricRow = {
  ticker: string;
  decision: "Accumulate" | "Hold" | "Avoid";
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

type WatchlistResponse = {
  symbols: string[];
  metrics?: WatchlistMetricRow[];
  missingSymbols?: string[];
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

type ChartResponse = {
  ticker: string;
  bars: ChartBar[];
  summary: ChartSummary | null;
  quote?: QuoteSummary;
  interval?: string;
  range?: string;
  ufMetric?: WatchlistMetricRow | null;
  note?: string | null;
  error?: string;
};

type SortDirection = "asc" | "desc";
type SortKey = "ticker" | "decision" | "price" | "regime";

type SortState = {
  key: SortKey;
  direction: SortDirection;
};

function normalize(input: string): string {
  return input.trim().toUpperCase();
}

function fmtNum(value: number | null | undefined, decimals = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return value.toFixed(decimals);
}

function fmtSigned(value: number, decimals = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  const prefix = n > 0 ? "+" : "";
  return `${prefix}${n.toFixed(decimals)}`;
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

function decisionClass(decision: "Accumulate" | "Hold" | "Avoid"): "accumulate" | "hold" | "avoid" {
  if (decision === "Accumulate") return "accumulate";
  if (decision === "Avoid") return "avoid";
  return "hold";
}

function compareString(a: string, b: string, direction: SortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function compareNumber(a: number | null, b: number | null, direction: SortDirection): number {
  const av = a === null ? Number.NEGATIVE_INFINITY : a;
  const bv = b === null ? Number.NEGATIVE_INFINITY : b;
  const base = av - bv;
  return direction === "asc" ? base : -base;
}

function sortRows(rows: WatchlistMetricRow[], sort: SortState): WatchlistMetricRow[] {
  const next = [...rows];

  next.sort((a, b) => {
    if (sort.key === "ticker") return compareString(a.ticker, b.ticker, sort.direction);
    if (sort.key === "decision") return compareString(a.decision, b.decision, sort.direction);
    if (sort.key === "price") return compareNumber(a.price, b.price, sort.direction);
    if (sort.key === "regime") return compareString(a.regime, b.regime, sort.direction);
    return compareString(a.ticker, b.ticker, "asc");
  });

  return next;
}

function SortHeader({
  label,
  sort,
  column,
  onChange,
}: {
  label: string;
  sort: SortState;
  column: SortKey;
  onChange: (next: SortState) => void;
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

function insufficientDataMessage(metric: WatchlistMetricRow | null): string | null {
  if (!metric) return null;
  if (metric.decision !== "Hold") return null;
  if (
    metric.decisionReasonCode !== "PSCF_FALLBACK_INSUFFICIENT_BARS" &&
    metric.decisionReasonCode !== "INSUFFICIENT_EVIDENCE_BARS"
  ) {
    return null;
  }
  return metric.decisionReason || "Insufficient Data";
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

function AnalysisPanel({
  ticker,
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
  chartLoading: boolean;
  chartError: string;
  chartSummary: ChartSummary | null;
  chartNote: string;
  quoteSummary: QuoteSummary;
  chartBars: ChartBar[];
  chartControls: ScreenerChartControls;
  onChartControlsChange: (next: ScreenerChartControls) => void;
  ufMetric: WatchlistMetricRow | null;
}) {
  const hasChart = Boolean(chartSummary);
  const decision = ufMetric?.decision ?? "Hold";
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
  const insufficientData = insufficientDataMessage(ufMetric);
  const decisionChip = (
    <span className={`tfe-chip ${decisionClass(decision)}`}>{decision}</span>
  );

  return (
    <div className="tfe-analysis-panel">
      <h3 style={{ margin: "0 0 8px", fontSize: "0.96rem" }}>
        {ticker} Analysis {decisionChip}
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

          {insufficientData ? <p className="tfe-muted">Insufficient Data: {insufficientData}</p> : null}

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

export default function WatchlistManager() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<WatchlistMetricRow[]>([]);
  const [missingSymbols, setMissingSymbols] = useState<string[]>([]);

  const [input, setInput] = useState("AAPL");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [selectedTicker, setSelectedTicker] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [lookupMetric, setLookupMetric] = useState<WatchlistMetricRow | null>(null);
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

  const [tableSort, setTableSort] = useState<SortState>({ key: "ticker", direction: "asc" });

  async function load() {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const res = await fetch("/api/watchlist", { method: "GET", cache: "no-store" });
      const data = (await res.json()) as WatchlistResponse;

      if (!res.ok) {
        setError(data.error ?? "Failed to load watchlist.");
        return;
      }

      setSymbols(data.symbols ?? []);
      setMetrics(data.metrics ?? []);
      setMissingSymbols(data.missingSymbols ?? []);
      setMessage("Watchlist loaded.");
    } catch {
      setError("Failed to load watchlist due to network error.");
    } finally {
      setLoading(false);
    }
  }

  async function save(nextSymbols: string[]) {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const res = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: nextSymbols }),
      });

      const data = (await res.json()) as WatchlistResponse;

      if (!res.ok) {
        setError(data.error ?? "Failed to save watchlist.");
        return;
      }

      setSymbols(data.symbols ?? []);
      setMessage("Watchlist saved.");
      await load();
    } catch {
      setError("Failed to save watchlist due to network error.");
    } finally {
      setLoading(false);
    }
  }

  async function loadChart(ticker: string, options?: { forceOpen?: boolean; controls?: ScreenerChartControls }) {
    const forceOpen = options?.forceOpen ?? false;
    const nextControls = options?.controls ?? chartControls;

    if (selectedTicker === ticker && !forceOpen) {
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
    setSelectedTicker(ticker);
    setAnalysisOpen(true);
    setChartLoading(true);
    setChartError("");
    setChartNote("");
    setLookupMetric(null);

    try {
      const params = new URLSearchParams({
        ticker,
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
        setChartNote("");
        setLookupMetric(null);
        setChartError(data.error ?? "Failed to load chart.");
        return;
      }

      setChartBars(Array.isArray(data.bars) ? data.bars : []);
      setChartSummary(data.summary ?? null);
      setQuoteSummary(data.quote ?? {});
      setChartNote(typeof data.note === "string" ? data.note : "");
      setLookupMetric(data.ufMetric ?? null);
      const resolvedInterval = normalizeChartInterval(data.interval, nextControls.interval);
      const resolvedRange = normalizeChartRange(data.range, nextControls.range);
      setChartControls({
        ...nextControls,
        interval: resolvedInterval,
        range: resolvedRange,
        timeframe: timeframeFromInterval(resolvedInterval),
      });
      setMessage(`Loaded ${ticker} analysis.`);
    } catch {
      setChartBars([]);
      setChartSummary(null);
      setQuoteSummary({});
      setChartNote("");
      setLookupMetric(null);
      setChartError("Failed to load chart due to network error.");
    } finally {
      setChartLoading(false);
    }
  }

  function closeAnalysis() {
    setAnalysisOpen(false);
    setSelectedTicker("");
  }

  async function onLookupTicker() {
    const symbol = normalize(input);

    if (!symbol) {
      setError("Enter a ticker symbol.");
      return;
    }

    setError("");
    await loadChart(symbol, { forceOpen: true });
  }

  function onAdd(event: FormEvent) {
    event.preventDefault();
    const symbol = normalize(input);

    if (!symbol) {
      setError("Enter a ticker symbol.");
      return;
    }

    if (symbols.includes(symbol)) {
      setError(`${symbol} is already in watchlist.`);
      return;
    }

    void save([...symbols, symbol]);
  }

  function onRemove(symbol: string) {
    void save(symbols.filter((s) => s !== symbol));
  }

  useEffect(() => {
    void load();
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

  const sortedMetrics = useMemo(() => sortRows(metrics, tableSort), [metrics, tableSort]);

  const selectedMetric = useMemo(
    () => sortedMetrics.find((m) => m.ticker === selectedTicker) ?? null,
    [sortedMetrics, selectedTicker],
  );

  const activeMetric = selectedMetric ?? lookupMetric;

  return (
    <div className="section-stack">
      <form onSubmit={onAdd} className="tfe-panel">
        <h2 style={{ margin: "0 0 8px" }}>Ticker Lookup</h2>

        <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "minmax(0, 1fr) auto auto" }}>
          <input
            className="tfe-input"
            value={input}
            onChange={(event) => setInput(event.target.value.toUpperCase())}
            placeholder="AAPL"
            autoComplete="off"
            spellCheck={false}
          />
          <button className="btn btn-ghost" type="button" onClick={() => void onLookupTicker()} disabled={loading || chartLoading}>
            {chartLoading ? "Looking..." : "Lookup"}
          </button>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Saving..." : "Add"}
          </button>
        </div>

        <div className="tfe-toolbar-actions" style={{ marginTop: 8 }}>
          <button className="btn btn-ghost" type="button" onClick={() => void load()} disabled={loading}>
            Reload
          </button>
          {message ? <span className="tfe-success">{message}</span> : null}
          {error ? <span className="tfe-error">{error}</span> : null}
        </div>
      </form>

      <section className="tfe-panel">
        <h2 style={{ margin: "0 0 8px" }}>Watchlist Symbols</h2>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {symbols.map((symbol) => {
            const active = analysisOpen && selectedTicker === symbol;

            return (
              <div
                key={symbol}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  border: active ? "1px solid rgba(31,77,58,0.66)" : "1px solid rgba(31,77,58,0.28)",
                  background: active ? "rgba(133,213,160,0.28)" : "rgba(248,252,247,0.72)",
                  borderRadius: 999,
                  overflow: "hidden",
                }}
                title={`Open analysis for ${symbol}`}
              >
                <button
                  type="button"
                  className="tfe-row-button"
                  onClick={() => void loadChart(symbol)}
                  style={{ padding: "5px 10px" }}
                >
                  {symbol}
                </button>

                <button
                  type="button"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onRemove(symbol);
                  }}
                  disabled={loading}
                  style={{
                    border: 0,
                    borderLeft: "1px solid rgba(31,77,58,0.2)",
                    background: "transparent",
                    color: "inherit",
                    padding: "5px 9px",
                    fontWeight: 700,
                    cursor: "pointer",
                    lineHeight: 1,
                    fontSize: "0.9rem",
                  }}
                  aria-label={`Remove ${symbol}`}
                  title={`Remove ${symbol}`}
                >
                  ×
                </button>
              </div>
            );
          })}
          {symbols.length === 0 ? <span className="tfe-muted">No symbols yet.</span> : null}
        </div>
      </section>

      <section className="section-stack">
        <h2>Watchlist Assessment</h2>

        <div className="tfe-table-wrap" style={{ maxHeight: 620 }}>
          <table className="tfe-table">
            <thead>
              <tr>
                <th>
                  <SortHeader label="Ticker" column="ticker" sort={tableSort} onChange={setTableSort} />
                </th>
                <th>
                  <SortHeader label="Decision" column="decision" sort={tableSort} onChange={setTableSort} />
                </th>
                <th style={{ textAlign: "right" }}>
                  <SortHeader label="Price" column="price" sort={tableSort} onChange={setTableSort} />
                </th>
                <th>
                  <SortHeader label="Regime" column="regime" sort={tableSort} onChange={setTableSort} />
                </th>
              </tr>
            </thead>

            <tbody>
              {sortedMetrics.length === 0 ? (
                <tr>
                  <td colSpan={4}>No metrics loaded yet.</td>
                </tr>
              ) : (
                sortedMetrics.map((row, rowIndex) => {
                  const active = analysisOpen && selectedTicker === row.ticker;

                  return (
                    <tr key={`${row.ticker}-${row.regime}-${row.barCount}-${rowIndex}`} className={active ? "active-row" : ""}>
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
                      <td>
                        <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                      </td>
                      <td style={{ textAlign: "right" }}>{fmtNum(row.price, 2)}</td>
                      <td>{row.regime}</td>
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
                  ufMetric={activeMetric}
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

      {missingSymbols.length > 0 ? (
        <p className="tfe-muted">
          Missing from dataset: <code>{missingSymbols.join(", ")}</code>
        </p>
      ) : null}
    </div>
  );
}
