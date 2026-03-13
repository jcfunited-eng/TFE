"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { UIEvent } from "react";
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

type RecommendationRow = {
  ticker: string;
  assetType: "equities" | "index" | "crypto" | "etf" | "other";
  price: number | null;
  decision: "Accumulate" | "Hold" | "Avoid";
  decisionReason: string;
  decisionReasonCode: string;
  confidence: number;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  classification: "BUY" | "HOLD" | "SELL";
  regime: string;
  assessmentStatus?: "ASSESSED" | "NOT_ASSESSED";
  assessmentLabel?: string;
};

type RecommendationsPayload = {
  topUnder50: RecommendationRow[];
  topByAssetType: {
    equities: RecommendationRow[];
    index: RecommendationRow[];
    crypto: RecommendationRow[];
    etf: RecommendationRow[];
  };
  allMarket: RecommendationRow[];
  universeStats?: {
    totalRows?: number;
    processedRows?: number;
    excludedRows?: number;
  };
  decisionSummary?: {
    accumulate?: number;
    hold?: number;
    avoid?: number;
  };
  recommendationHealth?: {
    totalRows?: number;
    assessedRows?: number;
    notAssessedRows?: number;
    assessedRate?: number;
    notAssessedRate?: number;
    accuracyScoringScope?: "ASSESSED_ONLY";
    policyMappedRows?: number;
    fallbackRows?: number;
    insufficientBarsRows?: number;
    coverageRate?: number;
    fallbackRate?: number;
    alerts?: string[];
  };
  snapshotSource?: string;
  data_source?: string;
  run_id?: string | null;
  generated_at_utc?: string | null;
  freshness?: {
    snapshot_age_minutes?: number;
    snapshot_max_age_minutes?: number;
    stale?: boolean;
  };
  error?: string;
};

type WatchlistPayload = {
  symbols: string[];
  error?: string;
};

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

type SortKey = "ticker" | "assetType" | "price" | "decision" | "regime" | "barCount";
type DecisionFilterKey = "Accumulate" | "Hold" | "Avoid";
type FullRangeField = "price" | "barCount";
type FullAssetFilter = "all" | "equities" | "index" | "crypto" | "etf" | "other";

type SortState = {
  key: SortKey;
  direction: SortDirection;
};

const RECOMMENDATIONS_FETCH_TIMEOUT_MS = 130000;
const FULL_MARKET_INITIAL_ROWS = 250;
const FULL_MARKET_PAGE_SIZE = 250;
const FULL_MARKET_AUTO_LOAD_THRESHOLD_PX = 96;

function normalizeTicker(input: string): string {
  return input.trim().toUpperCase();
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return value.toFixed(decimals);
}

function fmtSigned(value: number, decimals = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  const prefix = n > 0 ? "+" : "";
  return `${prefix}${n.toFixed(decimals)}`;
}

function parseOptionalNumber(value: string): number | null {
  const text = value.trim();
  if (!text) return null;
  const n = Number(text);
  if (!Number.isFinite(n)) return null;
  return n;
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

function formatIsoUtc(value: string | null | undefined): string {
  const text = String(value ?? "").trim();
  if (!text) return "N/A";
  const ms = Date.parse(text);
  if (!Number.isFinite(ms)) return text;
  return new Date(ms).toISOString();
}

function formatAgeMinutes(value: number | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return "N/A";
  if (n < 1) return `${Math.round(n * 60)}s`;
  const whole = Math.floor(n);
  const days = Math.floor(whole / 1440);
  const hours = Math.floor((whole % 1440) / 60);
  const mins = whole % 60;
  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function formatPctRate(value: number | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  return `${(n * 100).toFixed(2)}%`;
}

function shortRunId(value: string | null | undefined): string {
  const text = String(value ?? "").trim();
  if (!text) return "N/A";
  if (text.length <= 32) return text;
  return `${text.slice(0, 14)}...${text.slice(-10)}`;
}

function decisionClass(decision: "Accumulate" | "Hold" | "Avoid"): "accumulate" | "hold" | "avoid" {
  if (decision === "Accumulate") return "accumulate";
  if (decision === "Avoid") return "avoid";
  return "hold";
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

function sortRows(rows: RecommendationRow[], sort: SortState): RecommendationRow[] {
  const next = [...rows];

  next.sort((a, b) => {
    if (sort.key === "ticker") return compareString(a.ticker, b.ticker, sort.direction);
    if (sort.key === "assetType") return compareString(a.assetType, b.assetType, sort.direction);
    if (sort.key === "price") return compareNumber(a.price, b.price, sort.direction);
    if (sort.key === "decision") return compareString(a.decision, b.decision, sort.direction);
    if (sort.key === "regime") return compareString(a.regime, b.regime, sort.direction);
    if (sort.key === "barCount") return compareNumber(a.barCount, b.barCount, sort.direction);
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

function notAssessedLabel(row: RecommendationRow): string | null {
  if (row.assessmentStatus === "NOT_ASSESSED" && row.assessmentLabel) {
    return row.assessmentLabel;
  }
  if (row.decisionReasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS" || row.decisionReasonCode === "INSUFFICIENT_EVIDENCE_BARS") {
    return "Not Assessed (Insufficient Data)";
  }
  if (row.decisionReasonCode !== "PSCF_POLICY_DECISION") {
    return "Not Assessed (Fallback Hold)";
  }
  return null;
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

function formatAssetType(assetType: RecommendationRow["assetType"]): string {
  if (assetType === "etf") return "ETF";
  if (assetType === "equities") return "Equities (Stocks)";
  if (assetType === "index") return "Index";
  if (assetType === "crypto") return "Crypto";
  return "Other";
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
  row,
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
  row: RecommendationRow | null;
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
  const decision = row?.decision ?? ufMetric?.decision ?? "Hold";
  const insufficientData = insufficientDataMessage(ufMetric);
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
        {ticker} Analysis <span className={`tfe-chip ${decisionClass(decision)}`}>{decision}</span>
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

function RecommendationTable({
  title,
  rows,
  sort,
  onSortChange,
  activeTicker,
  analysisOpen,
  onOpen,
  maxHeight,
  onTableScroll,
}: {
  title: string;
  rows: RecommendationRow[];
  sort: SortState;
  onSortChange: (next: SortState) => void;
  activeTicker: string;
  analysisOpen: boolean;
  onOpen: (ticker: string) => void;
  maxHeight: number;
  onTableScroll?: (event: UIEvent<HTMLDivElement>) => void;
}) {
  const totalColumns = 5;

  return (
    <section className="section-stack">
      <h2>{title}</h2>

      <div className="tfe-table-wrap" style={{ maxHeight }} onScroll={onTableScroll}>
        <table className="tfe-table">
          <thead>
            <tr>
              <th>
                <SortHeader label="Ticker" column="ticker" sort={sort} onChange={onSortChange} />
              </th>
              <th>
                <SortHeader label="Asset" column="assetType" sort={sort} onChange={onSortChange} />
              </th>
              <th style={{ textAlign: "right" }}>
                <SortHeader label="Price" column="price" sort={sort} onChange={onSortChange} />
              </th>
              <th>
                <SortHeader label="Decision" column="decision" sort={sort} onChange={onSortChange} />
              </th>
              <th>
                <SortHeader label="Regime" column="regime" sort={sort} onChange={onSortChange} />
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={totalColumns}>No symbols available.</td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => {
                const key = `${row.assetType}-${row.ticker}-${row.regime}-${row.barCount}-${rowIndex}`;
                const active = analysisOpen && activeTicker === row.ticker;
                const rowAssessmentLabel = notAssessedLabel(row);

                return (
                  <tr key={key} className={active ? "active-row" : ""}>
                    <td>
                      <button
                        type="button"
                        className="tfe-row-button"
                        onClick={() => onOpen(row.ticker)}
                        title={`Open analysis for ${row.ticker}`}
                      >
                        {row.ticker}
                      </button>
                    </td>
                    <td>{formatAssetType(row.assetType)}</td>
                    <td style={{ textAlign: "right" }}>{fmtNum(row.price, 2)}</td>
                    <td>
                      <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                      {rowAssessmentLabel ? (
                        <div className="tfe-muted" style={{ fontSize: "0.72rem", marginTop: 4 }}>
                          {rowAssessmentLabel}
                        </div>
                      ) : null}
                    </td>
                    <td>{row.regime}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function RecommendationsQuickCheck() {
  const [symbolInput, setSymbolInput] = useState("AAPL");
  const [assetFilter, setAssetFilter] = useState<"equities" | "index" | "crypto" | "etf">("equities");
  const [fullMarketFilter, setFullMarketFilter] = useState("");
  const [fullDecisionFilter, setFullDecisionFilter] = useState<"all" | DecisionFilterKey>("all");
  const [fullAssetFilter, setFullAssetFilter] = useState<FullAssetFilter>("all");
  const [fullRangeField, setFullRangeField] = useState<FullRangeField>("price");
  const [fullRangeMin, setFullRangeMin] = useState("");
  const [fullRangeMax, setFullRangeMax] = useState("");

  const [loadingAdd, setLoadingAdd] = useState(false);
  const [loadingLists, setLoadingLists] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [lists, setLists] = useState<RecommendationsPayload | null>(null);

  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [lookupMetric, setLookupMetric] = useState<WatchlistMetricRow | null>(null);
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

  const [under50Sort, setUnder50Sort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [topAssetSort, setTopAssetSort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [fullSort, setFullSort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [fullMarketVisibleCount, setFullMarketVisibleCount] = useState(FULL_MARKET_INITIAL_ROWS);
  const [lastLoadComparison, setLastLoadComparison] = useState<{
    status: "first_load" | "same_as_previous_load" | "changed_since_previous_load";
    previousSignature: string | null;
  }>({
    status: "first_load",
    previousSignature: null,
  });

  const selectedTop10Rows = useMemo(() => {
    if (!lists) return [] as RecommendationRow[];
    return lists.topByAssetType[assetFilter];
  }, [lists, assetFilter]);

  const minRangeValue = useMemo(() => parseOptionalNumber(fullRangeMin), [fullRangeMin]);
  const maxRangeValue = useMemo(() => parseOptionalNumber(fullRangeMax), [fullRangeMax]);

  const filteredFullMarketRows = useMemo(() => {
    if (!lists) return [] as RecommendationRow[];
    const query = fullMarketFilter.trim().toUpperCase();
    return lists.allMarket.filter((row) => {
      if (fullDecisionFilter !== "all" && row.decision !== fullDecisionFilter) return false;
      if (fullAssetFilter !== "all" && row.assetType !== fullAssetFilter) return false;

      if (query) {
        const textMatch =
          row.ticker.includes(query) ||
          row.assetType.toUpperCase().includes(query) ||
          row.decision.toUpperCase().includes(query) ||
          row.regime.toUpperCase().includes(query);
        if (!textMatch) return false;
      }

      let numericValue: number | null;
      if (fullRangeField === "price") {
        numericValue = row.price;
      } else {
        numericValue = row.barCount;
      }

      if (minRangeValue !== null) {
        if (numericValue === null || numericValue < minRangeValue) return false;
      }
      if (maxRangeValue !== null) {
        if (numericValue === null || numericValue > maxRangeValue) return false;
      }

      return true;
    });
  }, [
    fullDecisionFilter,
    fullAssetFilter,
    fullMarketFilter,
    fullRangeField,
    lists,
    maxRangeValue,
    minRangeValue,
  ]);

  const topUnder50RowsSorted = useMemo(() => sortRows(lists?.topUnder50 ?? [], under50Sort), [lists, under50Sort]);
  const topAssetRowsSorted = useMemo(() => sortRows(selectedTop10Rows, topAssetSort), [selectedTop10Rows, topAssetSort]);
  const fullRowsSorted = useMemo(() => sortRows(filteredFullMarketRows, fullSort), [filteredFullMarketRows, fullSort]);
  const fullRowsVisible = useMemo(
    () => fullRowsSorted.slice(0, Math.max(FULL_MARKET_INITIAL_ROWS, fullMarketVisibleCount)),
    [fullRowsSorted, fullMarketVisibleCount],
  );
  const selectedAnalysisRow = useMemo(() => {
    const pools = [topUnder50RowsSorted, topAssetRowsSorted, fullRowsSorted];
    for (const rows of pools) {
      const match = rows.find((row) => row.ticker === selectedTicker);
      if (match) return match;
    }
    return null;
  }, [fullRowsSorted, selectedTicker, topAssetRowsSorted, topUnder50RowsSorted]);

  const recommendationsSignature = useMemo(() => {
    if (!lists) return "";
    const decisionSummary = lists.decisionSummary ?? {};
    const freshness = lists.freshness ?? {};
    return JSON.stringify({
      run_id: String(lists.run_id ?? ""),
      generated_at_utc: String(lists.generated_at_utc ?? ""),
      decisionSummary: {
        accumulate: Number(decisionSummary.accumulate ?? 0),
        hold: Number(decisionSummary.hold ?? 0),
        avoid: Number(decisionSummary.avoid ?? 0),
      },
      stale: Boolean(freshness.stale),
    });
  }, [lists]);

  useEffect(() => {
    setFullMarketVisibleCount(FULL_MARKET_INITIAL_ROWS);
  }, [fullDecisionFilter, fullAssetFilter, fullMarketFilter, fullRangeField, fullRangeMax, fullRangeMin]);

  const selectDecisionFilter = useCallback((decision: DecisionFilterKey) => {
    setFullDecisionFilter(decision);
  }, []);

  const resetDecisionFilter = useCallback(() => {
    setFullDecisionFilter("all");
  }, []);

  const loadMoreFullRows = useCallback(() => {
    setFullMarketVisibleCount((current) => {
      if (current >= fullRowsSorted.length) return current;
      return Math.min(current + FULL_MARKET_PAGE_SIZE, fullRowsSorted.length);
    });
  }, [fullRowsSorted.length]);

  const onFullMarketTableScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      const element = event.currentTarget;
      const remaining = element.scrollHeight - element.scrollTop - element.clientHeight;
      if (remaining <= FULL_MARKET_AUTO_LOAD_THRESHOLD_PX) {
        loadMoreFullRows();
      }
    },
    [loadMoreFullRows],
  );

  async function loadRecommendations() {
    setLoadingLists(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutHandle = window.setTimeout(() => controller.abort(), RECOMMENDATIONS_FETCH_TIMEOUT_MS);
      const response = await fetch("/api/recommendations/list", {
        method: "GET",
        cache: "no-store",
        signal: controller.signal,
      });
      window.clearTimeout(timeoutHandle);
      const payload = (await response.json()) as RecommendationsPayload;

      if (!response.ok) {
        setLists(null);
        setError(payload.error ?? "Failed to load recommendations.");
        return;
      }

      setLists(payload);
    } catch (error) {
      setLists(null);
      if (error instanceof DOMException && error.name === "AbortError") {
        setError(`Loading recommendations timed out after ${Math.floor(RECOMMENDATIONS_FETCH_TIMEOUT_MS / 1000)} seconds.`);
        return;
      }
      setError("Failed to load recommendations due to network error.");
    } finally {
      setLoadingLists(false);
    }
  }

  async function loadChart(symbol: string, controls?: ScreenerChartControls) {
    const clean = normalizeTicker(symbol);
    if (!clean) return;
    const nextControls = controls ?? chartControls;

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
      setMessage(`Loaded ${clean} analysis.`);
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

  async function toggleRow(ticker: string) {
    if (analysisOpen && selectedTicker === ticker) {
      closeAnalysis();
      return;
    }
    await loadChart(ticker);
  }

  async function addToWatchlist() {
    const cleanTicker = normalizeTicker(symbolInput);

    if (!cleanTicker) {
      setError("Enter a ticker symbol.");
      return;
    }

    setLoadingAdd(true);
    setError(null);
    setMessage(null);

    try {
      const loadResponse = await fetch("/api/watchlist", { method: "GET", cache: "no-store" });
      const loadPayload = (await loadResponse.json()) as WatchlistPayload;

      if (!loadResponse.ok) {
        setError(loadPayload.error ?? "Failed to load watchlist.");
        return;
      }

      const current = Array.isArray(loadPayload.symbols)
        ? loadPayload.symbols.map((s) => String(s).toUpperCase())
        : [];

      if (current.includes(cleanTicker)) {
        setMessage("Symbol already in Watchlist");
        return;
      }

      const saveResponse = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: [...current, cleanTicker] }),
      });

      const savePayload = (await saveResponse.json()) as { error?: string };

      if (!saveResponse.ok) {
        setError(savePayload.error ?? "Failed to save watchlist.");
        return;
      }

      setMessage("Symbol Added to Watchlist");
    } catch {
      setError("Failed to update watchlist due to network error.");
    } finally {
      setLoadingAdd(false);
    }
  }

  useEffect(() => {
    void loadRecommendations();
  }, []);

  useEffect(() => {
    if (!recommendationsSignature) return;

    const storageKey = "tfe_recommendations_signature_latest";
    try {
      const previous = window.localStorage.getItem(storageKey);
      if (!previous) {
        setLastLoadComparison({ status: "first_load", previousSignature: null });
      } else if (previous === recommendationsSignature) {
        setLastLoadComparison({ status: "same_as_previous_load", previousSignature: previous });
      } else {
        setLastLoadComparison({ status: "changed_since_previous_load", previousSignature: previous });
      }
      window.localStorage.setItem(storageKey, recommendationsSignature);
    } catch {
      setLastLoadComparison({ status: "first_load", previousSignature: null });
    }
  }, [recommendationsSignature]);

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

  return (
    <div className="section-stack">
      <p className="tfe-muted" style={{ marginTop: 0 }}>
        Consistent decision rules are applied across recommendations, watchlist, ticker lookup, and portfolio outputs. Only Watchlist and Portfolio pages have live market data.
      </p>

      <section className="tfe-panel">
        <h2 style={{ margin: "0 0 8px" }}>Watchlist Shortcut</h2>
        <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "minmax(0, 1fr) auto" }}>
          <input
            className="tfe-input"
            value={symbolInput}
            onChange={(event) => setSymbolInput(event.target.value.toUpperCase())}
            placeholder="AAPL"
            autoComplete="off"
            spellCheck={false}
          />
          <button className="btn btn-primary" type="button" onClick={() => void addToWatchlist()} disabled={loadingAdd || chartLoading}>
            {loadingAdd ? "Adding..." : "Add to Watchlist"}
          </button>
        </div>

        {error ? <p className="tfe-error" style={{ marginTop: 8 }}>{error}</p> : null}
        {message ? <p className="tfe-success" style={{ marginTop: 8 }}>{message}</p> : null}
      </section>

      {loadingLists ? <p className="tfe-muted">Loading recommendations...</p> : null}

      {lists ? (
        <>
          <section className="tfe-panel">
            <h2 style={{ margin: "0 0 6px" }}>Recommendation Runtime Status</h2>
            <p className="tfe-muted" style={{ marginTop: 0, marginBottom: 8 }}>
              This shows the exact recommendation snapshot currently rendered by this page.
            </p>

            <div className="tfe-status-row">
              <div className={`tfe-status-pill ${String(lists.data_source ?? "").toLowerCase() === "postgres" ? "is-good" : "is-warn"}`}>
                <span className="k">Data Source</span>
                <span className="v">{lists.data_source || "N/A"}</span>
              </div>

              <div className={`tfe-status-pill ${lists.freshness?.stale ? "is-warn" : "is-good"}`}>
                <span className="k">Freshness</span>
                <span className="v">
                  {lists.freshness?.stale ? "Stale" : "Fresh"} ({formatAgeMinutes(lists.freshness?.snapshot_age_minutes)})
                </span>
              </div>

              <div className="tfe-status-pill">
                <span className="k">Snapshot Generated (UTC)</span>
                <span className="v">{formatIsoUtc(lists.generated_at_utc)}</span>
              </div>

              <div className="tfe-status-pill">
                <span className="k">Runtime Run ID</span>
                <span className="v" title={lists.run_id || "N/A"}>{shortRunId(lists.run_id)}</span>
              </div>

              <div
                className={`tfe-status-pill ${
                  lastLoadComparison.status === "changed_since_previous_load" ? "is-good" : "is-warn"
                }`}
              >
                <span className="k">Changed Since Last Page Load</span>
                <span className="v">
                  {lastLoadComparison.status === "first_load"
                    ? "First Load"
                    : lastLoadComparison.status === "changed_since_previous_load"
                      ? "Changed"
                      : "Unchanged"}
                </span>
              </div>
            </div>

            <div className="tfe-summary-grid" style={{ marginTop: 8 }}>
              <div className="tfe-summary-card">
                <div className="k">Accumulate</div>
                <div className="v">{Number(lists.decisionSummary?.accumulate ?? 0)}</div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Hold</div>
                <div className="v">{Number(lists.decisionSummary?.hold ?? 0)}</div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Avoid</div>
                <div className="v">{Number(lists.decisionSummary?.avoid ?? 0)}</div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Assessed Rows</div>
                <div className="v">
                  {Number(lists.recommendationHealth?.assessedRows ?? lists.recommendationHealth?.policyMappedRows ?? 0)}
                </div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Not Assessed Rows</div>
                <div className="v">
                  {Number(lists.recommendationHealth?.notAssessedRows ?? lists.recommendationHealth?.fallbackRows ?? 0)}
                </div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Assessed Rate</div>
                <div className="v">
                  {formatPctRate(
                    lists.recommendationHealth?.assessedRate ?? lists.recommendationHealth?.coverageRate,
                  )}
                </div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Not Assessed Rate</div>
                <div className="v">
                  {formatPctRate(
                    lists.recommendationHealth?.notAssessedRate ?? lists.recommendationHealth?.fallbackRate,
                  )}
                </div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Insufficient Data Rows</div>
                <div className="v">{Number(lists.recommendationHealth?.insufficientBarsRows ?? 0)}</div>
              </div>
              <div className="tfe-summary-card">
                <div className="k">Snapshot Source</div>
                <div className="v" title={lists.snapshotSource || "N/A"}>{lists.snapshotSource ? "Postgres Runtime Snapshot" : "N/A"}</div>
              </div>
            </div>

            {Array.isArray(lists.recommendationHealth?.alerts) && lists.recommendationHealth?.alerts.length > 0 ? (
              <p className="tfe-error" style={{ marginTop: 8, marginBottom: 0 }}>
                Health alerts: {lists.recommendationHealth?.alerts.join(", ")}
              </p>
            ) : null}

            <p className="tfe-muted" style={{ marginTop: 8, marginBottom: 0 }}>
              Accuracy scope: assessed symbols only. Not assessed symbols are visible and excluded from accuracy scoring.
            </p>
          </section>

          <p className="tfe-muted" style={{ marginTop: 0, marginBottom: 8 }}>
            Recommendation decisions come from daily market scans. Listed prices use the latest cached quote feed and may lag live market prints.
          </p>
          <RecommendationTable
            title="Top 5 Under $50"
            rows={topUnder50RowsSorted}
            sort={under50Sort}
            onSortChange={setUnder50Sort}
            activeTicker={selectedTicker}
            analysisOpen={analysisOpen}
            onOpen={(ticker) => void toggleRow(ticker)}
            maxHeight={360}
          />

          <section className="section-stack">
            <h2>Top 10 by Asset Class</h2>
            <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "280px" }}>
              <div className="tfe-field">
                <label htmlFor="asset-filter">Asset Class</label>
                <select
                  id="asset-filter"
                  className="tfe-select"
                  value={assetFilter}
                  onChange={(event) => setAssetFilter(event.target.value as "equities" | "index" | "crypto" | "etf")}
                >
                  <option value="equities">Equities</option>
                  <option value="index">Index</option>
                  <option value="crypto">Crypto</option>
                  <option value="etf">ETF</option>
                </select>
              </div>
            </div>

            <RecommendationTable
              title={`Top 10 ${assetFilter}`}
              rows={topAssetRowsSorted}
              sort={topAssetSort}
              onSortChange={setTopAssetSort}
              activeTicker={selectedTicker}
              analysisOpen={analysisOpen}
              onOpen={(ticker) => void toggleRow(ticker)}
              maxHeight={420}
            />
          </section>

          <section className="section-stack">
            <h2>Full Market Assessment</h2>
            <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "repeat(4, auto) minmax(0, 1fr)" }}>
              <button
                type="button"
                className={fullDecisionFilter === "Accumulate" ? "btn" : "btn btn-primary"}
                onClick={() => selectDecisionFilter("Accumulate")}
              >
                Accumulate
              </button>
              <button
                type="button"
                className={fullDecisionFilter === "Hold" ? "btn" : "btn btn-primary"}
                onClick={() => selectDecisionFilter("Hold")}
              >
                Hold
              </button>
              <button
                type="button"
                className={fullDecisionFilter === "Avoid" ? "btn" : "btn btn-primary"}
                onClick={() => selectDecisionFilter("Avoid")}
              >
                Avoid
              </button>
              <button
                type="button"
                className={fullDecisionFilter === "all" ? "btn" : "btn btn-primary"}
                onClick={resetDecisionFilter}
              >
                See All
              </button>
              <div className="tfe-muted" style={{ alignSelf: "center" }}>
                {fullRowsVisible.length} shown / {fullRowsSorted.length} matching / {lists.allMarket.length} total
              </div>
            </div>

            <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "220px 140px 140px minmax(0, 1fr)" }}>
              <div className="tfe-field">
                <label htmlFor="full-range-field">Min/Max Field</label>
                <select
                  id="full-range-field"
                  className="tfe-select"
                  value={fullRangeField}
                  onChange={(event) => setFullRangeField(event.target.value as FullRangeField)}
                >
                  <option value="price">Price</option>
                  <option value="barCount">Bars</option>
                </select>
              </div>
              <div className="tfe-field">
                <label htmlFor="full-range-min">Min</label>
                <input
                  id="full-range-min"
                  className="tfe-input"
                  type="number"
                  step="any"
                  value={fullRangeMin}
                  onChange={(event) => setFullRangeMin(event.target.value)}
                  placeholder="no minimum"
                />
              </div>
              <div className="tfe-field">
                <label htmlFor="full-range-max">Max</label>
                <input
                  id="full-range-max"
                  className="tfe-input"
                  type="number"
                  step="any"
                  value={fullRangeMax}
                  onChange={(event) => setFullRangeMax(event.target.value)}
                  placeholder="no maximum"
                />
              </div>
            </div>

            <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "220px minmax(0, 1fr)" }}>
              <div className="tfe-field">
                <label htmlFor="full-asset-filter">Asset Filter</label>
                <select
                  id="full-asset-filter"
                  className="tfe-select"
                  value={fullAssetFilter}
                  onChange={(event) => setFullAssetFilter(event.target.value as FullAssetFilter)}
                >
                  <option value="all">All Assets</option>
                  <option value="equities">Equities</option>
                  <option value="index">Index</option>
                  <option value="crypto">Crypto</option>
                  <option value="etf">ETF</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <input
                className="tfe-input"
                value={fullMarketFilter}
                onChange={(event) => setFullMarketFilter(event.target.value)}
                placeholder="Search ticker, decision, regime, or asset type"
              />
            </div>

            <RecommendationTable
              title="All Processed Symbols"
              rows={fullRowsVisible}
              sort={fullSort}
              onSortChange={setFullSort}
              activeTicker={selectedTicker}
              analysisOpen={analysisOpen}
              onOpen={(ticker) => void toggleRow(ticker)}
              maxHeight={760}
              onTableScroll={onFullMarketTableScroll}
            />
          </section>
        </>
      ) : null}

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
                  row={selectedAnalysisRow}
                  chartLoading={chartLoading}
                  chartError={chartError}
                  chartSummary={chartSummary}
                  chartNote={chartNote}
                  quoteSummary={quoteSummary}
                  chartBars={chartBars}
                  chartControls={chartControls}
                  onChartControlsChange={(next) => {
                    void loadChart(selectedTicker, next);
                  }}
                  ufMetric={lookupMetric}
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

      <p className="tfe-muted">For research use only. Not financial advice. No trade execution.</p>
    </div>
  );
}
