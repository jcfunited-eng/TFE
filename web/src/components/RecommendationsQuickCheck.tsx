"use client";

import { useEffect, useState, useMemo } from "react";
import ClientPortal from "@/components/ClientPortal";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type ScreenerChartControls,
} from "@/components/ScreenerChart";

type SignalClass = "3WA" | "W1" | "standard";

type RecommendationRow = {
  ticker: string;
  sector: string;
  marketCap: number;
  currentRatio: number;
  freeCashFlow: number;
  grossMargin: number;
  grossProfit: number;
  operatingCashFlow: number;
  revenues: number;
  decision: "Accumulate";
  decisionReason: string;
  isNewListing?: boolean;
  signalClass?: SignalClass;
  regime?: string;
  stabilityScore?: number | null;
  maxDrawdown?: number | null;
  barCount?: number | null;
  minBarsForAccumulate?: number;
  externalResearchUrl?: string;
};

type RecommendationsPayload = {
  totalAccumulate: number;
  buckets: {
    titans: RecommendationRow[];
    heavyweights: RecommendationRow[];
    midTier: RecommendationRow[];
    hunters: RecommendationRow[];
  };
  error?: string;
};

type SortKey = keyof Pick<
  RecommendationRow,
  "ticker" | "sector" | "marketCap" | "currentRatio" | "freeCashFlow" | "grossMargin"
>;
type SortDir = "asc" | "desc";

type ChartBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type ChartSummary = {
  open: number; high: number; low: number; prevClose: number;
  close: number; change: number; changePct: number;
  high52: number; low52: number;
};

type QuoteSummary = {
  companyName?: string | null;
  price?: number | null;
  changePct?: number | null;
  netFlows1MonthPct?: number | null;
  netFlows3MonthPct?: number | null;
  netFlowsYtdPct?: number | null;
};

type ChartResponse = {
  bars: ChartBar[];
  summary: ChartSummary | null;
  quote?: QuoteSummary;
  note?: string | null;
  error?: string;
};

function formatMoney(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  if (Math.abs(value) >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  return value.toFixed(2);
}

function formatRatio(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  return value.toFixed(2);
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

function fmtPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toFixed(decimals);
}

const PAGE_SIZE = 25;

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "ticker", label: "Ticker" },
  { key: "sector", label: "Sector" },
  { key: "marketCap", label: "Market Cap" },
  { key: "currentRatio", label: "Current Ratio" },
  { key: "freeCashFlow", label: "Free Cash Flow" },
  { key: "grossMargin", label: "Gross Margin" },
];

function compareRows(a: RecommendationRow, b: RecommendationRow, key: SortKey, dir: SortDir): number {
  const aVal = a[key];
  const bVal = b[key];
  let cmp = 0;
  if (typeof aVal === "string" && typeof bVal === "string") {
    cmp = aVal.localeCompare(bVal);
  } else {
    const aNum = Number(aVal);
    const bNum = Number(bVal);
    if (!Number.isFinite(aNum) && !Number.isFinite(bNum)) cmp = 0;
    else if (!Number.isFinite(aNum)) cmp = 1;
    else if (!Number.isFinite(bNum)) cmp = -1;
    else cmp = aNum - bNum;
  }
  return dir === "asc" ? cmp : -cmp;
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span style={{ opacity: 0.3, marginLeft: 4 }}>↕</span>;
  return <span style={{ marginLeft: 4 }}>{dir === "asc" ? "↑" : "↓"}</span>;
}

// ── Analysis popup panel ─────────────────────────────────────────────────────
function AnalysisPanel({
  row,
  chartBars,
  chartSummary,
  chartQuote,
  chartNote,
  chartLoading,
  chartError,
  chartControls,
  onChartControlsChange,
  onClose,
}: {
  row: RecommendationRow;
  chartBars: ChartBar[];
  chartSummary: ChartSummary | null;
  chartQuote: QuoteSummary;
  chartNote: string;
  chartLoading: boolean;
  chartError: string;
  chartControls: ScreenerChartControls;
  onChartControlsChange: (c: ScreenerChartControls) => void;
  onClose: () => void;
}) {
  const livePrice = chartSummary?.close ?? chartQuote.price ?? null;
  const changePct = chartSummary?.changePct ?? chartQuote.changePct ?? null;
  const companyName = chartQuote.companyName ?? null;
  const flowCards = [
    { label: "1M Flow", value: chartQuote.netFlows1MonthPct ?? null },
    { label: "3M Flow", value: chartQuote.netFlows3MonthPct ?? null },
    { label: "YTD Flow", value: chartQuote.netFlowsYtdPct ?? null },
  ];
  const hasFundFlows = flowCards.some((c) => c.value !== null);
  const coverage =
    row.barCount !== null && row.barCount !== undefined && row.minBarsForAccumulate !== undefined
      ? `${row.barCount}/${row.minBarsForAccumulate}`
      : "—";

  return (
    <ClientPortal>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Analysis: ${row.ticker}`}
        style={{
          position: "fixed", inset: 0,
          background: "rgba(11,18,15,0.68)",
          zIndex: 1200,
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: 20,
        }}
        onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      >
        <div
          className="tfe-panel"
          style={{ width: "min(1120px, 100%)", maxHeight: "92vh", overflow: "auto", padding: "1rem", display: "grid", gap: "1rem" }}
        >
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
            <div>
              <h2 style={{ margin: 0 }}>
                {row.ticker}{" "}
                <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#fff", background: "#16a34a", borderRadius: 4, padding: "2px 8px", verticalAlign: "middle" }}>
                  Accumulate
                </span>
                {row.signalClass === "3WA" && (
                  <span style={{ marginLeft: 6, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#7c3aed", borderRadius: 3, padding: "2px 6px", verticalAlign: "middle" }}>3WA</span>
                )}
                {(row.signalClass === "W1" || row.isNewListing) && row.signalClass !== "3WA" && (
                  <span style={{ marginLeft: 6, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#16a34a", borderRadius: 3, padding: "2px 6px", verticalAlign: "middle" }}>NEW</span>
                )}
              </h2>
              <p className="tfe-muted" style={{ margin: "0.35rem 0 0" }}>
                {companyName ?? row.sector}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexShrink: 0 }}>
              {row.externalResearchUrl && (
                <a href={row.externalResearchUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                  Research ↗
                </a>
              )}
              <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
            </div>
          </div>

          {/* Native Engine Metrics */}
          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Native Engine Metrics</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem" }}>
              <div className="tfe-panel"><strong>Price</strong><div>{fmtPrice(livePrice)}</div></div>
              <div className="tfe-panel"><strong>Change</strong><div>{fmtPct(changePct ? changePct / 100 : null)}</div></div>
              <div className="tfe-panel">
                <strong>52W Range</strong>
                <div>{fmtPrice(chartSummary?.low52 ?? null)} – {fmtPrice(chartSummary?.high52 ?? null)}</div>
              </div>
              <div className="tfe-panel"><strong>Regime</strong><div>{row.regime ?? "—"}</div></div>
              <div className="tfe-panel"><strong>Stability</strong><div>{fmtNum(row.stabilityScore)}</div></div>
              <div className="tfe-panel"><strong>Max DD</strong><div>{fmtNum(row.maxDrawdown)}</div></div>
              <div className="tfe-panel"><strong>Coverage</strong><div>{coverage}</div></div>
            </div>
          </section>

          {/* Fundamentals summary */}
          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Fundamentals</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem" }}>
              <div className="tfe-panel"><strong>Market Cap</strong><div>{formatMoney(row.marketCap)}</div></div>
              <div className="tfe-panel"><strong>Current Ratio</strong><div>{formatRatio(row.currentRatio)}</div></div>
              <div className="tfe-panel"><strong>Free Cash Flow</strong><div>{formatMoney(row.freeCashFlow)}</div></div>
              <div className="tfe-panel"><strong>Gross Margin</strong><div>{formatPercent(row.grossMargin)}</div></div>
              <div className="tfe-panel"><strong>Sector</strong><div style={{ fontSize: "0.82rem" }}>{row.sector}</div></div>
              <div className="tfe-panel"><strong>Signal</strong><div>{row.decisionReason}</div></div>
            </div>
          </section>

          {/* Chart */}
          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Chart</h3>
            {chartLoading ? <p className="tfe-muted">Loading chart…</p> : null}
            {chartError ? <p className="tfe-error">{chartError}</p> : null}
            {!chartLoading && !chartError && chartBars.length > 0 ? (
              <ScreenerChart
                ticker={row.ticker}
                bars={chartBars}
                controls={chartControls}
                loading={chartLoading}
                onControlsChange={onChartControlsChange}
              />
            ) : null}
            {!chartLoading && !chartError && chartBars.length === 0 ? (
              <p className="tfe-muted">{chartNote || `No chart data available for ${row.ticker}.`}</p>
            ) : null}
          </section>

          {/* Fund Flows */}
          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Fund Flows</h3>
            {hasFundFlows ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.75rem" }}>
                {flowCards.map((c) => (
                  <div key={c.label} className="tfe-panel">
                    <strong>{c.label}</strong>
                    <div>{fmtPct(c.value !== null ? c.value / 100 : null)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="tfe-muted">Fund flow metrics are not present in the live native-engine quote payload for this ticker.</p>
            )}
          </section>
        </div>
      </div>
    </ClientPortal>
  );
}

// ── Bucket table ─────────────────────────────────────────────────────────────
function BucketTable({
  title,
  rows,
  search,
  companyNames,
  onTickerClick,
}: {
  title: string;
  rows: RecommendationRow[];
  search: string;
  companyNames: Record<string, string>;
  onTickerClick: (row: RecommendationRow) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("marketCap");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);

  const query = search.trim().toLowerCase();

  const filtered = useMemo(() => {
    if (!query) return rows;
    return rows.filter(
      (r) =>
        r.ticker.toLowerCase().includes(query) ||
        r.sector.toLowerCase().includes(query) ||
        (companyNames[r.ticker] ?? "").toLowerCase().includes(query),
    );
  }, [rows, query, companyNames]);

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => compareRows(a, b, sortKey, sortDir)),
    [filtered, sortKey, sortDir],
  );

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages);
  const pageRows = sorted.slice((clampedPage - 1) * PAGE_SIZE, clampedPage * PAGE_SIZE);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
    setPage(1);
  }

  function handlePageInput(e: React.ChangeEvent<HTMLInputElement>) {
    const n = parseInt(e.target.value, 10);
    if (Number.isFinite(n) && n >= 1 && n <= totalPages) setPage(n);
  }

  const matchLabel =
    query && filtered.length !== rows.length
      ? ` — ${filtered.length} match${filtered.length === 1 ? "" : "es"}`
      : "";

  return (
    <section className="section-stack">
      <h2>{title}</h2>
      <div className="tfe-muted" style={{ marginBottom: 8 }}>
        {rows.length} result{rows.length === 1 ? "" : "s"}
        {matchLabel}
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="tfe-table">
          <caption className="sr-only">{title} — Accumulate Recommendations</caption>
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={
                    sortKey === col.key
                      ? sortDir === "asc" ? "ascending" : "descending"
                      : "none"
                  }
                  onClick={() => handleSort(col.key)}
                  style={{
                    cursor: "pointer",
                    userSelect: "none",
                    whiteSpace: "nowrap",
                    textAlign: col.key === "ticker" || col.key === "sector" ? "left" : "right",
                  }}
                >
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr key={`${title}-${row.ticker}`}>
                <td style={{ textAlign: "left" }}>
                  <button
                    type="button"
                    className="tfe-ticker-btn"
                    onClick={() => onTickerClick(row)}
                    title={`View analysis for ${row.ticker}${companyNames[row.ticker] ? ` — ${companyNames[row.ticker]}` : ""}`}
                  >
                    {row.ticker}
                  </button>
                  {row.signalClass === "3WA" ? (
                    <span style={{ marginLeft: 4, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#7c3aed", borderRadius: 3, padding: "1px 4px", verticalAlign: "middle", letterSpacing: "0.04em" }} title="Three-Wave Alignment — Structure A + SPY expansion. Backtest: 84.5% win.">3WA</span>
                  ) : row.signalClass === "W1" || row.isNewListing ? (
                    <span style={{ marginLeft: 4, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#16a34a", borderRadius: 3, padding: "1px 4px", verticalAlign: "middle", letterSpacing: "0.04em" }} title="Wave 1 — New listing in structural ground state. Backtest: 72.1% win.">NEW</span>
                  ) : null}
                </td>
                <td style={{ textAlign: "left" }}>{row.sector || "—"}</td>
                <td style={{ textAlign: "right" }}>{formatMoney(row.marketCap)}</td>
                <td style={{ textAlign: "right" }}>{formatRatio(row.currentRatio)}</td>
                <td style={{ textAlign: "right" }}>{formatMoney(row.freeCashFlow)}</td>
                <td style={{ textAlign: "right" }}>{formatPercent(row.grossMargin)}</td>
              </tr>
            ))}
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "left" }}>{query ? "No matches." : "No Accumulate results."}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
          <button
            className="tfe-page-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={clampedPage <= 1}
          >
            ← Prev
          </button>
          <span className="tfe-muted">
            Page{" "}
            <input
              type="number"
              min={1}
              max={totalPages}
              value={clampedPage}
              onChange={handlePageInput}
              aria-label="Go to page"
              style={{ width: 52, textAlign: "center" }}
            />{" "}
            of {totalPages}
          </span>
          <button
            className="tfe-page-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={clampedPage >= totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </section>
  );
}

// ── Root component ───────────────────────────────────────────────────────────
export default function RecommendationsQuickCheck() {
  const [payload, setPayload] = useState<RecommendationsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  // Market lock overlay removed per user request — banner handles the warning

  // Analysis popup state
  const [activeRow, setActiveRow] = useState<RecommendationRow | null>(null);
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [chartQuote, setChartQuote] = useState<QuoteSummary>({});
  const [chartNote, setChartNote] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  // company name cache for search
  const [companyNames, setCompanyNames] = useState<Record<string, string>>({});


  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/recommendations/list", {
          method: "GET",
          cache: "no-store",
        });
        const data = (await response.json()) as RecommendationsPayload;
        if (!response.ok) {
          if (!cancelled) {
            setPayload(null);
            setError(data.error ?? "Failed to load recommendations.");
          }
          return;
        }
        if (!cancelled) {
          setPayload(data);
        }
      } catch {
        if (!cancelled) {
          setPayload(null);
          setError("Failed to load recommendations.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load chart when a row is selected
  useEffect(() => {
    if (!activeRow) {
      setChartBars([]);
      setChartSummary(null);
      setChartQuote({});
      setChartNote("");
      setChartError("");
      return;
    }

    const ticker = activeRow.ticker;
    const controller = new AbortController();

    async function loadChart(): Promise<void> {
      setChartLoading(true);
      setChartError("");
      try {
        const q = new URLSearchParams();
        q.set("ticker", ticker);
        q.set("interval", chartControls.interval);
        q.set("range", chartControls.range);
        const res = await fetch(`/api/watchlist/chart?${q.toString()}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const data = (await res.json()) as ChartResponse;
        if (!res.ok) {
          setChartError(data.error ?? "Chart load failed.");
          return;
        }
        setChartBars(Array.isArray(data.bars) ? data.bars : []);
        setChartSummary(data.summary ?? null);
        const quote = data.quote ?? {};
        setChartQuote(quote);
        setChartNote(data.note ?? "");
        // Cache company name for search
        if (quote.companyName) {
          setCompanyNames((prev) => ({ ...prev, [ticker]: quote.companyName! }));
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        setChartError(e instanceof Error ? e.message : "Chart load failed.");
      } finally {
        if (!controller.signal.aborted) setChartLoading(false);
      }
    }

    void loadChart();
    return () => controller.abort();
  }, [activeRow, chartControls]);

  function openRow(row: RecommendationRow) {
    setActiveRow(row);
    setChartControls(DEFAULT_SCREENER_CHART_CONTROLS);
  }

  function closePanel() {
    setActiveRow(null);
  }

  if (loading) {
    return <p className="tfe-muted">Loading verified L5 research tool…</p>;
  }

  if (error || !payload) {
    return <p className="tfe-error">{error ?? "Recommendations unavailable."}</p>;
  }

  const allRows = [
    ...payload.buckets.titans,
    ...payload.buckets.heavyweights,
    ...payload.buckets.midTier,
    ...payload.buckets.hunters,
  ];
  const query = search.trim().toLowerCase();
  const matchCount = query
    ? allRows.filter(
        (r) =>
          r.ticker.toLowerCase().includes(query) ||
          r.sector.toLowerCase().includes(query) ||
          (companyNames[r.ticker] ?? "").toLowerCase().includes(query),
      ).length
    : null;

  return (
    <div className="section-stack">
      {/* Analysis popup */}
      {activeRow && (
        <AnalysisPanel
          row={activeRow}
          chartBars={chartBars}
          chartSummary={chartSummary}
          chartQuote={chartQuote}
          chartNote={chartNote}
          chartLoading={chartLoading}
          chartError={chartError}
          chartControls={chartControls}
          onChartControlsChange={setChartControls}
          onClose={closePanel}
        />
      )}

      <section className="surface-card">
        <h2>Strict L5 Kernel</h2>
        <div className="tfe-summary-grid" style={{ marginTop: 8 }}>
          <div className="tfe-summary-card">
            <div className="k">Accumulate</div>
            <div className="v">{payload.totalAccumulate}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Titans</div>
            <div className="v">{payload.buckets.titans.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Heavyweights</div>
            <div className="v">{payload.buckets.heavyweights.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Mid-Tier</div>
            <div className="v">{payload.buckets.midTier.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Hunters</div>
            <div className="v">{payload.buckets.hunters.length}</div>
          </div>
        </div>
      </section>

      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Search by ticker, company name, or sector…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: "1 1 280px", maxWidth: 400 }}
          aria-label="Search recommendations"
        />
        {matchCount !== null && (
          <span className="tfe-muted">
            {matchCount} result{matchCount === 1 ? "" : "s"} across all buckets
          </span>
        )}
      </div>

      <BucketTable title="The Titans" rows={payload.buckets.titans} search={search} companyNames={companyNames} onTickerClick={openRow} />
      <BucketTable title="The Heavyweights" rows={payload.buckets.heavyweights} search={search} companyNames={companyNames} onTickerClick={openRow} />
      <BucketTable title="The Mid-Tier" rows={payload.buckets.midTier} search={search} companyNames={companyNames} onTickerClick={openRow} />
      <BucketTable title="The Hunters" rows={payload.buckets.hunters} search={search} companyNames={companyNames} onTickerClick={openRow} />
    </div>
  );
}
