"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import type { UIEvent } from "react";

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

type ChartResponse = {
  ticker: string;
  bars: ChartBar[];
  summary: ChartSummary | null;
  quote?: QuoteSummary;
  ufMetric?: WatchlistMetricRow | null;
  note?: string | null;
  error?: string;
};

type SortDirection = "asc" | "desc";

type SortKey = "ticker" | "assetType" | "price" | "decision" | "regime" | "sUf" | "rUf" | "barCount" | "confidence";
type DecisionFilterKey = "Accumulate" | "Hold" | "Avoid";
type FullRangeField = "price" | "S_UF" | "R_UF" | "barCount" | "confidence";
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
    if (sort.key === "sUf") return compareNumber(a.S_UF, b.S_UF, sort.direction);
    if (sort.key === "rUf") return compareNumber(a.R_UF, b.R_UF, sort.direction);
    if (sort.key === "barCount") return compareNumber(a.barCount, b.barCount, sort.direction);
    if (sort.key === "confidence") return compareNumber(a.confidence, b.confidence, sort.direction);
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
  if (metric.decisionReasonCode !== "INSUFFICIENT_EVIDENCE_BARS") return null;
  return metric.decisionReason || "Insufficient Data";
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
  ufMetric: WatchlistMetricRow | null;
}) {
  const closeSeries = useMemo(() => chartBars.map((b) => b.close), [chartBars]);
  const sparkPath = useMemo(() => linePath(closeSeries, 960, 260, 16), [closeSeries]);
  const decision = ufMetric?.decision ?? null;
  const insufficientData = insufficientDataMessage(ufMetric);
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
                    <linearGradient id={`lineGradRecommendations-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(107,188,137,0.95)" />
                      <stop offset="100%" stopColor="rgba(107,188,137,0.2)" />
                    </linearGradient>
                  </defs>
                  <rect x="0" y="0" width="960" height="260" fill="rgba(16, 36, 27, 0.08)" />
                  <polyline
                    fill="none"
                    stroke={`url(#lineGradRecommendations-${ticker})`}
                    strokeWidth="2.8"
                    points={sparkPath}
                  />
                </svg>
              </>
            ) : (
              <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
            )}
          </div>

          <aside className="tfe-signal-card">
            <h4>TFE Signal Card</h4>

            <div className="tfe-kv">Decision</div>
            <div className="tfe-value">{decision ?? "Unavailable"}</div>

            {decision ? <div className={`tfe-chip ${decisionClass(decision)}`}>{decision}</div> : null}

            <div style={{ marginTop: 10 }}>
              <div className="tfe-kv">UF Confidence</div>
              <div className="tfe-value">{fmtNum(ufConfidence, 3)}</div>
              <div style={{ fontSize: "0.8rem" }}>
                S_UF {fmtNum(ufMetric?.S_UF ?? null, 3)} | R_UF {fmtNum(ufMetric?.R_UF ?? null, 3)}
              </div>
            </div>

            {insufficientData ? (
              <div style={{ marginTop: 10 }}>
                <div className="tfe-kv">Insufficient Data</div>
                <div style={{ fontSize: "0.8rem" }}>{insufficientData}</div>
              </div>
            ) : null}
          </aside>
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
  expandedTicker,
  onToggle,
  selectedTicker,
  chartLoading,
  chartError,
  chartSummary,
  chartNote,
  quoteSummary,
  chartBars,
  ufMetric,
  maxHeight,
  showUfColumns,
  onTableScroll,
}: {
  title: string;
  rows: RecommendationRow[];
  sort: SortState;
  onSortChange: (next: SortState) => void;
  expandedTicker: string;
  onToggle: (ticker: string) => void;
  selectedTicker: string;
  chartLoading: boolean;
  chartError: string;
  chartSummary: ChartSummary | null;
  chartNote: string;
  quoteSummary: QuoteSummary;
  chartBars: ChartBar[];
  ufMetric: WatchlistMetricRow | null;
  maxHeight: number;
  showUfColumns: boolean;
  onTableScroll?: (event: UIEvent<HTMLDivElement>) => void;
}) {
  const baseColumns = 5;
  const ufColumns = showUfColumns ? 4 : 0;
  const totalColumns = baseColumns + ufColumns;

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
              {showUfColumns ? (
                <>
                  <th style={{ textAlign: "right" }}>
                    <SortHeader label="S_UF" column="sUf" sort={sort} onChange={onSortChange} />
                  </th>
                  <th style={{ textAlign: "right" }}>
                    <SortHeader label="R_UF" column="rUf" sort={sort} onChange={onSortChange} />
                  </th>
                  <th style={{ textAlign: "right" }}>
                    <SortHeader label="Bars" column="barCount" sort={sort} onChange={onSortChange} />
                  </th>
                  <th style={{ textAlign: "right" }}>
                    <SortHeader label="UF Confidence" column="confidence" sort={sort} onChange={onSortChange} />
                  </th>
                </>
              ) : null}
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
                const active = expandedTicker === row.ticker;

                return (
                  <Fragment key={key}>
                    <tr className={active ? "active-row" : ""}>
                      <td>
                        <button
                          type="button"
                          className="tfe-row-button"
                          onClick={() => onToggle(row.ticker)}
                          title={`Open analysis for ${row.ticker}`}
                        >
                          {row.ticker}
                        </button>
                      </td>
                      <td style={{ textTransform: "capitalize" }}>{row.assetType}</td>
                      <td style={{ textAlign: "right" }}>{fmtNum(row.price, 2)}</td>
                      <td>
                        <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                      </td>
                      <td>{row.regime}</td>
                      {showUfColumns ? (
                        <>
                          <td style={{ textAlign: "right" }}>{fmtNum(row.S_UF, 3)}</td>
                          <td style={{ textAlign: "right" }}>{fmtNum(row.R_UF, 3)}</td>
                          <td style={{ textAlign: "right" }}>{row.barCount}</td>
                          <td style={{ textAlign: "right" }}>{fmtNum(row.confidence, 3)}</td>
                        </>
                      ) : null}
                    </tr>

                    {active ? (
                      <tr>
                        <td colSpan={totalColumns} style={{ padding: 0 }}>
                          <AnalysisPanel
                            ticker={row.ticker}
                            chartLoading={chartLoading && selectedTicker === row.ticker}
                            chartError={selectedTicker === row.ticker ? chartError : ""}
                            chartSummary={selectedTicker === row.ticker ? chartSummary : null}
                            chartNote={selectedTicker === row.ticker ? chartNote : ""}
                            quoteSummary={selectedTicker === row.ticker ? quoteSummary : {}}
                            chartBars={selectedTicker === row.ticker ? chartBars : []}
                            ufMetric={selectedTicker === row.ticker ? ufMetric : null}
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

  const [expandedTicker, setExpandedTicker] = useState<string>("");
  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [lookupMetric, setLookupMetric] = useState<WatchlistMetricRow | null>(null);

  const [under50Sort, setUnder50Sort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [topAssetSort, setTopAssetSort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [fullSort, setFullSort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [fullMarketVisibleCount, setFullMarketVisibleCount] = useState(FULL_MARKET_INITIAL_ROWS);

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
      } else if (fullRangeField === "S_UF") {
        numericValue = row.S_UF;
      } else if (fullRangeField === "R_UF") {
        numericValue = row.R_UF;
      } else if (fullRangeField === "barCount") {
        numericValue = row.barCount;
      } else {
        numericValue = row.confidence;
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

  async function loadChart(symbol: string) {
    const clean = normalizeTicker(symbol);
    if (!clean) return;

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

  async function toggleRow(ticker: string) {
    if (expandedTicker === ticker) {
      setExpandedTicker("");
      return;
    }

    setExpandedTicker(ticker);

    if (selectedTicker !== ticker) {
      await loadChart(ticker);
    }
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

  return (
    <div className="section-stack">
      <p className="tfe-muted" style={{ marginTop: 0 }}>
        Consistent decision rules are applied across recommendations, watchlist, ticker lookup, and portfolio outputs.
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
          <RecommendationTable
            title="Top 5 Under $50"
            rows={topUnder50RowsSorted}
            sort={under50Sort}
            onSortChange={setUnder50Sort}
            expandedTicker={expandedTicker}
            onToggle={(ticker) => void toggleRow(ticker)}
            selectedTicker={selectedTicker}
            chartLoading={chartLoading}
            chartError={chartError}
            chartSummary={chartSummary}
            chartNote={chartNote}
            quoteSummary={quoteSummary}
            chartBars={chartBars}
            ufMetric={lookupMetric}
            maxHeight={360}
            showUfColumns={false}
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
              expandedTicker={expandedTicker}
              onToggle={(ticker) => void toggleRow(ticker)}
              selectedTicker={selectedTicker}
              chartLoading={chartLoading}
              chartError={chartError}
              chartSummary={chartSummary}
              chartNote={chartNote}
              quoteSummary={quoteSummary}
              chartBars={chartBars}
              ufMetric={lookupMetric}
              maxHeight={420}
              showUfColumns={false}
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
                  <option value="confidence">UF Confidence</option>
                  <option value="price">Price</option>
                  <option value="S_UF">S_UF</option>
                  <option value="R_UF">R_UF</option>
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
              expandedTicker={expandedTicker}
              onToggle={(ticker) => void toggleRow(ticker)}
              selectedTicker={selectedTicker}
              chartLoading={chartLoading}
              chartError={chartError}
              chartSummary={chartSummary}
              chartNote={chartNote}
              quoteSummary={quoteSummary}
              chartBars={chartBars}
              ufMetric={lookupMetric}
              maxHeight={760}
              showUfColumns={true}
              onTableScroll={onFullMarketTableScroll}
            />
          </section>
        </>
      ) : null}

      <p className="tfe-muted">For research use only. Not financial advice. No trade execution.</p>
    </div>
  );
}
