"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import ClientPortal from "@/components/ClientPortal";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type MarketTimeframe,
  type ScreenerChartControls,
  type ScreenerChartInterval,
  type ScreenerChartRange,
} from "@/components/ScreenerChart";
import type { MarketQuoteSummary } from "@/lib/market-analysis";

type WatchlistMetricRow = {
  ticker: string;
  decision: "Accumulate" | "Hold" | "Avoid";
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL";
  price: number | null;
  changePct: number | null;
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
type SortKey =
  | "ticker"
  | "decision"
  | "classification"
  | "price"
  | "changePct"
  | "regime"
  | "stability"
  | "maxDrawdown"
  | "barCount";

type SortState = {
  key: SortKey;
  direction: SortDirection;
};

function normalize(input: string): string {
  return input.trim().toUpperCase();
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function fmtText(value: unknown, fallback = "n/a"): string {
  const text = String(value ?? "").trim();
  return text ? text : fallback;
}

function fmtNumber(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toFixed(decimals);
}

function fmtPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function fmtPercent(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(decimals)}%`;
}

function fmtCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n/a";
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

function decisionClass(decision: "Accumulate" | "Hold" | "Avoid"): "is-buy" | "is-hold" | "is-sell" {
  if (decision === "Accumulate") return "is-buy";
  if (decision === "Avoid") return "is-sell";
  return "is-hold";
}

function compareString(a: string, b: string, direction: SortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function compareNumber(a: number | null, b: number | null, direction: SortDirection): number {
  const left = a ?? Number.NEGATIVE_INFINITY;
  const right = b ?? Number.NEGATIVE_INFINITY;
  const base = left - right;
  return direction === "asc" ? base : -base;
}

function sortRows(rows: WatchlistMetricRow[], sort: SortState): WatchlistMetricRow[] {
  const next = [...rows];

  next.sort((left, right) => {
    if (sort.key === "ticker") return compareString(left.ticker, right.ticker, sort.direction);
    if (sort.key === "decision") return compareString(left.decision, right.decision, sort.direction);
    if (sort.key === "classification") return compareString(left.classification, right.classification, sort.direction);
    if (sort.key === "price") return compareNumber(left.price, right.price, sort.direction);
    if (sort.key === "changePct") return compareNumber(left.changePct, right.changePct, sort.direction);
    if (sort.key === "regime") return compareString(left.regime, right.regime, sort.direction);
    if (sort.key === "stability") return compareNumber(left.stability_score, right.stability_score, sort.direction);
    if (sort.key === "maxDrawdown") return compareNumber(left.max_dd, right.max_dd, sort.direction);
    return compareNumber(left.barCount, right.barCount, sort.direction);
  });

  return next;
}

function SortHeader({
  label,
  sort,
  column,
  align = "left",
  onChange,
}: {
  label: string;
  sort: SortState;
  column: SortKey;
  align?: "left" | "right";
  onChange: (next: SortState) => void;
}) {
  const active = sort.key === column;
  const arrow = !active ? "" : sort.direction === "asc" ? " ↑" : " ↓";

  return (
    <button
      type="button"
      className="tfe-sort-btn"
      style={{ justifyContent: align === "right" ? "flex-end" : "flex-start" }}
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

function thAriaSort(sort: SortState, column: SortKey): "ascending" | "descending" | "none" {
  if (sort.key !== column) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
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
  onClose,
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
  onClose: () => void;
}) {
  const decision = ufMetric?.decision ?? "Hold";
  const classification = ufMetric?.classification ?? "HOLD";
  const decisionReason =
    ufMetric?.decisionReason ?? (chartNote || "Native Engine decision context is unavailable for this ticker.");
  const decisionReasonCode = ufMetric?.decisionReasonCode ?? "UNAVAILABLE";
  const displayPrice = toNumberOrNull(chartSummary?.close) ?? toNumberOrNull(quoteSummary.price) ?? ufMetric?.price ?? null;
  const displayChangePct =
    toNumberOrNull(chartSummary?.changePct) ?? toNumberOrNull(quoteSummary.changePct) ?? ufMetric?.changePct ?? null;
  const coverage = ufMetric ? `${ufMetric.barCount}/${ufMetric.minBarsForAccumulate}` : "n/a";
  const insufficientData = insufficientDataMessage(ufMetric);
  const marketContextCards = [
    { label: "52W High", value: fmtPrice(toNumberOrNull(chartSummary?.high52) ?? toNumberOrNull(quoteSummary.high52)) },
    { label: "52W Low", value: fmtPrice(toNumberOrNull(chartSummary?.low52) ?? toNumberOrNull(quoteSummary.low52)) },
    { label: "Avg Volume", value: fmtCompactNumber(toNumberOrNull(quoteSummary.avgVolume)) },
    { label: "Exchange", value: fmtText(quoteSummary.exchange) },
  ];

  return (
    <ClientPortal>
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(11, 18, 15, 0.68)",
          zIndex: 1200,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "20px",
        }}
        onClick={onClose}
      >
        <div
          className="tfe-panel"
          style={{
            width: "min(1120px, 100%)",
            maxHeight: "92vh",
            overflow: "auto",
            padding: "1rem",
            display: "grid",
            gap: "1rem",
          }}
          onClick={(event) => event.stopPropagation()}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
            <div>
              <h2 style={{ margin: 0 }}>
                {ticker} <span className={`tfe-chip ${decisionClass(decision)}`}>{decision}</span>
              </h2>
              <p className="tfe-muted" style={{ margin: "0.35rem 0 0" }}>
                {fmtText(quoteSummary.companyName, "Native Engine watchlist analysis")}
              </p>
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
              Close
            </button>
          </div>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>L5 Decision Context</h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "0.75rem",
              }}
            >
              <div className="tfe-panel">
                <strong>Decision</strong>
                <div>{decision}</div>
              </div>
              <div className="tfe-panel">
                <strong>Classification</strong>
                <div>{classification}</div>
              </div>
              <div className="tfe-panel">
                <strong>Reason Code</strong>
                <div>{fmtText(decisionReasonCode)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Coverage</strong>
                <div>{coverage}</div>
              </div>
            </div>
            <p className="tfe-muted" style={{ margin: 0 }}>
              {decisionReason}
            </p>
            {insufficientData ? <p className="tfe-muted" style={{ margin: 0 }}>Insufficient Data: {insufficientData}</p> : null}
          </section>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Native Engine Metrics</h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "0.75rem",
              }}
            >
              <div className="tfe-panel">
                <strong>Price</strong>
                <div>{fmtPrice(displayPrice)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Change</strong>
                <div>{fmtPercent(displayChangePct)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Regime</strong>
                <div>{fmtText(ufMetric?.regime)}</div>
              </div>
              <div className="tfe-panel">
                <strong>S_UF</strong>
                <div>{fmtNumber(ufMetric?.S_UF, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>R_UF</strong>
                <div>{fmtNumber(ufMetric?.R_UF, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Stability</strong>
                <div>{fmtNumber(ufMetric?.stability_score, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Max DD</strong>
                <div>{fmtNumber(ufMetric?.max_dd, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Coverage</strong>
                <div>{coverage}</div>
              </div>
            </div>
          </section>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Chart</h3>
            {chartLoading ? <p className="tfe-muted">Loading chart...</p> : null}
            {chartError ? <p className="tfe-error">{chartError}</p> : null}
            {!chartLoading && !chartError && chartBars.length > 0 ? (
              <ScreenerChart
                ticker={ticker}
                bars={chartBars}
                controls={chartControls}
                loading={chartLoading}
                onControlsChange={onChartControlsChange}
              />
            ) : null}
            {!chartLoading && !chartError && chartBars.length === 0 ? (
              <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
            ) : null}
          </section>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Market Context</h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "0.75rem",
              }}
            >
              {marketContextCards.map((card) => (
                <div key={card.label} className="tfe-panel">
                  <strong>{card.label}</strong>
                  <div>{card.value}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </ClientPortal>
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
  const [tableSort, setTableSort] = useState<SortState>({ key: "ticker", direction: "asc" });
  const [tickerSearch, setTickerSearch] = useState("");

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
    void save(symbols.filter((currentSymbol) => currentSymbol !== symbol));
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

  const sortedMetrics = useMemo(() => {
    const q = tickerSearch.trim().toUpperCase();
    const base = q ? metrics.filter((r) => r.ticker.includes(q)) : metrics;
    return sortRows(base, tableSort);
  }, [metrics, tableSort, tickerSearch]);
  const selectedMetric = useMemo(
    () => sortedMetrics.find((metric) => metric.ticker === selectedTicker) ?? null,
    [selectedTicker, sortedMetrics],
  );
  const activeMetric = selectedMetric ?? lookupMetric;

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
        <h2 style={{ margin: 0 }}>Watchlist Lookup</h2>
        <form
          onSubmit={onAdd}
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) auto auto",
            gap: "0.75rem",
          }}
        >
          <input
            className="tfe-input"
            value={input}
            onChange={(event) => setInput(event.target.value.toUpperCase())}
            placeholder="AAPL"
            autoComplete="off"
            spellCheck={false}
          />
          <button className="btn btn-ghost btn-sm" type="button" onClick={() => void onLookupTicker()} disabled={loading || chartLoading}>
            {chartLoading ? "Looking..." : "Lookup"}
          </button>
          <button className="btn btn-primary btn-sm" type="submit" disabled={loading}>
            {loading ? "Saving..." : "Add"}
          </button>
        </form>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={() => void load()} disabled={loading}>
            Reload
          </button>
          {message ? <span className="tfe-success">{message}</span> : null}
          {error ? <span className="tfe-error">{error}</span> : null}
        </div>
      </section>

      <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
          <h2 style={{ margin: 0 }}>Watchlist Symbols</h2>
          <span className="tfe-muted">{symbols.length} symbols</span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
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
              >
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void loadChart(symbol)}
                  style={{ borderRadius: 0 }}
                  title={`Open analysis for ${symbol}`}
                >
                  {symbol}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onRemove(symbol);
                  }}
                  disabled={loading}
                  style={{ borderRadius: 0, borderLeft: "1px solid rgba(31,77,58,0.2)" }}
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

      <section className="tfe-panel" style={{ overflowX: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", marginBottom: "0.75rem" }}>
          <h2 style={{ margin: 0 }}>Native Engine Watchlist</h2>
          <span className="tfe-muted">{loading ? "Loading watchlist..." : `${sortedMetrics.length} rows`}</span>
        </div>
        <div style={{ marginBottom: "0.5rem" }}>
          <input
            className="tfe-input"
            type="search"
            placeholder="Filter by ticker…"
            value={tickerSearch}
            onChange={(e) => setTickerSearch(e.target.value)}
            aria-label="Filter watchlist by ticker"
            style={{ maxWidth: 200 }}
          />
        </div>
        <table className="tfe-table">
          <caption className="sr-only">Native Engine Watchlist Metrics</caption>
          <thead>
            <tr>
              <th scope="col" aria-sort={thAriaSort(tableSort, "ticker")} style={{ textAlign: "left" }}>
                <SortHeader label="Ticker" column="ticker" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "decision")} style={{ textAlign: "left" }}>
                <SortHeader label="Decision" column="decision" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "classification")} style={{ textAlign: "left" }}>
                <SortHeader label="Class" column="classification" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "price")} style={{ textAlign: "right" }}>
                <SortHeader label="Price" column="price" align="right" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "changePct")} style={{ textAlign: "right" }}>
                <SortHeader label="Change" column="changePct" align="right" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "regime")} style={{ textAlign: "left" }}>
                <SortHeader label="Regime" column="regime" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "stability")} style={{ textAlign: "right" }}>
                <SortHeader label="Stability" column="stability" align="right" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "maxDrawdown")} style={{ textAlign: "right" }}>
                <SortHeader label="Max DD" column="maxDrawdown" align="right" sort={tableSort} onChange={setTableSort} />
              </th>
              <th scope="col" aria-sort={thAriaSort(tableSort, "barCount")} style={{ textAlign: "right" }}>
                <SortHeader label="Bars" column="barCount" align="right" sort={tableSort} onChange={setTableSort} />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedMetrics.length === 0 ? (
              <tr>
                <td colSpan={9}>
                  <span className="tfe-muted">No metrics loaded yet.</span>
                </td>
              </tr>
            ) : (
              sortedMetrics.map((row, index) => {
                const active = analysisOpen && selectedTicker === row.ticker;

                return (
                  <tr key={`${row.ticker}-${row.regime}-${row.barCount}-${index}`} style={active ? { background: "rgba(133,213,160,0.12)" } : undefined}>
                    <td>
                      <button
                        type="button"
                        className="tfe-ticker-btn"
                        onClick={() => void loadChart(row.ticker)}
                        title={`Open analysis for ${row.ticker}`}
                      >
                        {row.ticker}
                      </button>
                    </td>
                    <td>
                      <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                    </td>
                    <td>{row.classification}</td>
                    <td style={{ textAlign: "right" }}>{fmtPrice(row.price)}</td>
                    <td style={{ textAlign: "right" }}>{fmtPercent(row.changePct)}</td>
                    <td>{row.regime || "—"}</td>
                    <td style={{ textAlign: "right" }}>{fmtNumber(row.stability_score, 2)}</td>
                    <td style={{ textAlign: "right" }}>{fmtNumber(row.max_dd, 2)}</td>
                    <td style={{ textAlign: "right" }}>
                      {row.barCount}/{row.minBarsForAccumulate}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>

      {analysisOpen && selectedTicker ? (
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
          onClose={closeAnalysis}
        />
      ) : null}

      {missingSymbols.length > 0 ? (
        <p className="tfe-muted">
          Missing from dataset: <code>{missingSymbols.join(", ")}</code>
        </p>
      ) : null}
    </div>
  );
}
