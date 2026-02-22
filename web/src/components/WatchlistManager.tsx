"use client";

import { FormEvent, Fragment, useEffect, useMemo, useState } from "react";

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
                    <linearGradient id={`lineGradWatchlist-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(107,188,137,0.95)" />
                      <stop offset="100%" stopColor="rgba(107,188,137,0.2)" />
                    </linearGradient>
                  </defs>
                  <rect x="0" y="0" width="960" height="260" fill="rgba(16, 36, 27, 0.08)" />
                  <polyline fill="none" stroke={`url(#lineGradWatchlist-${ticker})`} strokeWidth="2.8" points={sparkPath} />
                </svg>
              </>
            ) : (
              <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
            )}
          </div>

          <aside className="tfe-signal-card">
            <h4>TFE Signal Card</h4>

            <div className="tfe-kv">Decision</div>
            <div className="tfe-value">{ufMetric?.decision ?? "Unavailable"}</div>
            {ufMetric?.decision ? <div className={`tfe-chip ${decisionClass(ufMetric.decision)}`}>{ufMetric.decision}</div> : null}

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
  const [lookupMetric, setLookupMetric] = useState<WatchlistMetricRow | null>(null);

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

  async function loadChart(ticker: string, options?: { forceOpen?: boolean }) {
    const forceOpen = options?.forceOpen ?? false;

    if (selectedTicker === ticker && !forceOpen) {
      setSelectedTicker("");
      setLookupMetric(null);
      setChartSummary(null);
      setChartBars([]);
      setQuoteSummary({});
      setChartError("");
      return;
    }

    setSelectedTicker(ticker);
    setChartLoading(true);
    setChartError("");
    setChartNote("");
    setLookupMetric(null);

    try {
      const res = await fetch(`/api/watchlist/chart?ticker=${encodeURIComponent(ticker)}&days=365`, {
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

  const sortedMetrics = useMemo(() => sortRows(metrics, tableSort), [metrics, tableSort]);

  const selectedMetric = useMemo(
    () => sortedMetrics.find((m) => m.ticker === selectedTicker) ?? null,
    [sortedMetrics, selectedTicker],
  );

  const activeMetric = selectedMetric ?? lookupMetric;
  const selectedTickerInTable = useMemo(
    () => sortedMetrics.some((row) => row.ticker === selectedTicker),
    [sortedMetrics, selectedTicker],
  );

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

      {selectedTicker && !selectedTickerInTable ? (
        <section className="tfe-panel">
          <AnalysisPanel
            ticker={selectedTicker}
            chartLoading={chartLoading}
            chartError={chartError}
            chartSummary={chartSummary}
            chartNote={chartNote}
            quoteSummary={quoteSummary}
            chartBars={chartBars}
            ufMetric={activeMetric}
          />
        </section>
      ) : null}

      <section className="tfe-panel">
        <h2 style={{ margin: "0 0 8px" }}>Watchlist Symbols</h2>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {symbols.map((symbol) => {
            const active = selectedTicker === symbol;

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
                  const active = selectedTicker === row.ticker;

                  return (
                    <Fragment key={`${row.ticker}-${row.regime}-${row.barCount}-${rowIndex}`}>
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
                        <td>
                          <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                        </td>
                        <td style={{ textAlign: "right" }}>{fmtNum(row.price, 2)}</td>
                        <td>{row.regime}</td>
                      </tr>

                      {active ? (
                        <tr>
                          <td colSpan={4} style={{ padding: 0 }}>
                            <AnalysisPanel
                              ticker={row.ticker}
                              chartLoading={chartLoading && selectedTicker === row.ticker}
                              chartError={selectedTicker === row.ticker ? chartError : ""}
                              chartSummary={selectedTicker === row.ticker ? chartSummary : null}
                              chartNote={selectedTicker === row.ticker ? chartNote : ""}
                              quoteSummary={selectedTicker === row.ticker ? quoteSummary : {}}
                              chartBars={selectedTicker === row.ticker ? chartBars : []}
                              ufMetric={selectedTicker === row.ticker ? activeMetric : null}
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

      {missingSymbols.length > 0 ? (
        <p className="tfe-muted">
          Missing from dataset: <code>{missingSymbols.join(", ")}</code>
        </p>
      ) : null}
    </div>
  );
}
