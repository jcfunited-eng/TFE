"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import ClientPortal from "@/components/ClientPortal";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type ScreenerChartControls,
} from "@/components/ScreenerChart";

type ScreenerTab = "overview" | "performance" | "technical" | "etf";
type Decision = "Accumulate" | "Hold" | "Avoid";
type AssetType = "equities" | "index" | "crypto" | "etf" | "other";
type SortDirection = "asc" | "desc";
type SortKey = "ticker" | "assetType" | "price" | "changePct" | "decision" | "regime" | "stabilityScore" | "maxDrawdown" | "barCount";

type ScreenerRow = {
  ticker: string;
  assetType: AssetType;
  decision: Decision;
  classification: "BUY" | "HOLD" | "SELL";
  regime: string;
  price: number | null;
  barCount: number;
  minBarsForAccumulate: number;
  stabilityScore: number | null;
  maxDrawdown: number | null;
  externalResearchUrl: string;
};

type QuoteSummary = {
  companyName?: string | null;
  assetType?: string | null;
  quoteType?: string | null;
  price?: number | null;
  change?: number | null;
  changePct?: number | null;
  volume?: number | null;
  avgVolume?: number | null;
  relVolume?: number | null;
  high52?: number | null;
  low52?: number | null;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  atr14?: number | null;
  rsi14?: number | null;
  netFlows1MonthPct?: number | null;
  netFlows3MonthPct?: number | null;
  netFlowsYtdPct?: number | null;
};

type ScreenerResponse = {
  tab: ScreenerTab;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  rows: ScreenerRow[];
  pageQuotes?: Record<string, QuoteSummary>;
  options?: {
    regimes?: string[];
    assetTypes?: AssetType[];
    decisions?: Decision[];
  };
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

type UfMetric = {
  ticker: string;
  decision: Decision;
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

type TableColumn = {
  id: string;
  label: string;
  align?: "left" | "right";
  sortKey?: SortKey;
  render: (row: ScreenerRow, quote: QuoteSummary) => ReactNode;
};

type ScreenerAnalysisState = {
  row: ScreenerRow;
  quote: QuoteSummary;
};

const DATA_TABS: Array<{ key: ScreenerTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "performance", label: "Performance" },
  { key: "technical", label: "Technical" },
  { key: "etf", label: "ETF" },
];

const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_ASSET_OPTIONS: AssetType[] = ["equities", "index", "crypto", "etf", "other"];
const DEFAULT_DECISION_OPTIONS: Decision[] = ["Accumulate", "Hold", "Avoid"];

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
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

function fmtCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function fmtPercentValue(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(decimals)}%`;
}

function fmtRatioPercent(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return fmtPercentValue(value * 100, decimals);
}

function fmtCoverage(row: ScreenerRow): string {
  if (row.minBarsForAccumulate <= 0) return `${row.barCount}`;
  return `${row.barCount}/${row.minBarsForAccumulate}`;
}

function decisionClass(decision: Decision): string {
  if (decision === "Accumulate") return "is-buy";
  if (decision === "Avoid") return "is-sell";
  return "is-hold";
}

function compareText(a: string, b: string, direction: SortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function compareNumber(a: number | null, b: number | null, direction: SortDirection): number {
  const left = a ?? Number.NEGATIVE_INFINITY;
  const right = b ?? Number.NEGATIVE_INFINITY;
  const base = left - right;
  return direction === "asc" ? base : -base;
}

function buildRowPrice(row: ScreenerRow, quote: QuoteSummary): number | null {
  return toNumberOrNull(quote.price) ?? row.price;
}

function buildRowChangePct(quote: QuoteSummary): number | null {
  return toNumberOrNull(quote.changePct);
}

function sortRows(rows: ScreenerRow[], quotes: Record<string, QuoteSummary>, sortKey: SortKey, direction: SortDirection): ScreenerRow[] {
  const next = [...rows];
  next.sort((left, right) => {
    const leftQuote = quotes[left.ticker] ?? {};
    const rightQuote = quotes[right.ticker] ?? {};

    if (sortKey === "ticker") return compareText(left.ticker, right.ticker, direction);
    if (sortKey === "assetType") return compareText(left.assetType, right.assetType, direction);
    if (sortKey === "price") return compareNumber(buildRowPrice(left, leftQuote), buildRowPrice(right, rightQuote), direction);
    if (sortKey === "changePct") return compareNumber(buildRowChangePct(leftQuote), buildRowChangePct(rightQuote), direction);
    if (sortKey === "decision") return compareText(left.decision, right.decision, direction);
    if (sortKey === "regime") return compareText(left.regime, right.regime, direction);
    if (sortKey === "stabilityScore") return compareNumber(left.stabilityScore, right.stabilityScore, direction);
    if (sortKey === "maxDrawdown") return compareNumber(left.maxDrawdown, right.maxDrawdown, direction);
    return compareNumber(left.barCount, right.barCount, direction);
  });
  return next;
}

function buildColumns(tab: ScreenerTab, onOpen: (row: ScreenerRow, quote: QuoteSummary) => void): TableColumn[] {
  const tickerColumn: TableColumn = {
    id: "ticker",
    label: "Ticker",
    sortKey: "ticker",
    render: (row, quote) => (
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => onOpen(row, quote)}>
        {row.ticker}
        {row.decision === "Accumulate" && row.barCount > 0 && row.barCount <= 20 ? (
          <span style={{ marginLeft: 5, fontSize: "0.6rem", fontWeight: 700, color: "#fff", background: "#16a34a", borderRadius: 3, padding: "1px 4px", verticalAlign: "middle", letterSpacing: "0.04em" }} title="New listing — structural ground state. Backtest: 72%+ win.">NEW</span>
        ) : null}
      </button>
    ),
  };

  const assetTypeColumn: TableColumn = {
    id: "assetType",
    label: "Asset",
    sortKey: "assetType",
    render: (row) => fmtText(row.assetType),
  };

  const priceColumn: TableColumn = {
    id: "price",
    label: "Price",
    align: "right",
    sortKey: "price",
    render: (row, quote) => fmtPrice(buildRowPrice(row, quote)),
  };

  const changeColumn: TableColumn = {
    id: "changePct",
    label: "Change",
    align: "right",
    sortKey: "changePct",
    render: (_row, quote) => fmtPercentValue(toNumberOrNull(quote.changePct)),
  };

  const volumeColumn: TableColumn = {
    id: "volume",
    label: "Volume",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(toNumberOrNull(quote.volume)),
  };

  const avgVolumeColumn: TableColumn = {
    id: "avgVolume",
    label: "Avg Vol",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(toNumberOrNull(quote.avgVolume)),
  };

  const relVolumeColumn: TableColumn = {
    id: "relVolume",
    label: "Rel Vol",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.relVolume), 2),
  };

  const regimeColumn: TableColumn = {
    id: "regime",
    label: "Regime",
    sortKey: "regime",
    render: (row) => fmtText(row.regime),
  };

  const decisionColumn: TableColumn = {
    id: "decision",
    label: "Decision",
    sortKey: "decision",
    render: (row) => <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>,
  };

  const stabilityColumn: TableColumn = {
    id: "stabilityScore",
    label: "Stability",
    align: "right",
    sortKey: "stabilityScore",
    render: (row) => fmtNumber(row.stabilityScore, 2),
  };

  const maxDrawdownColumn: TableColumn = {
    id: "maxDrawdown",
    label: "Max DD",
    align: "right",
    sortKey: "maxDrawdown",
    render: (row) => fmtNumber(row.maxDrawdown, 2),
  };

  const barsColumn: TableColumn = {
    id: "barCount",
    label: "Bars",
    align: "right",
    sortKey: "barCount",
    render: (row) => fmtCoverage(row),
  };

  const sma20Column: TableColumn = {
    id: "sma20",
    label: "SMA20",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.sma20), 2),
  };

  const sma50Column: TableColumn = {
    id: "sma50",
    label: "SMA50",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.sma50), 2),
  };

  const sma200Column: TableColumn = {
    id: "sma200",
    label: "SMA200",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.sma200), 2),
  };

  const rsiColumn: TableColumn = {
    id: "rsi14",
    label: "RSI14",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.rsi14), 2),
  };

  const atrColumn: TableColumn = {
    id: "atr14",
    label: "ATR14",
    align: "right",
    render: (_row, quote) => fmtNumber(toNumberOrNull(quote.atr14), 2),
  };

  const researchColumn: TableColumn = {
    id: "research",
    label: "Research",
    align: "right",
    render: (row) => (
      <a href={row.externalResearchUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
        Research ↗
      </a>
    ),
  };

  if (tab === "performance") {
    return [
      tickerColumn,
      priceColumn,
      changeColumn,
      volumeColumn,
      avgVolumeColumn,
      relVolumeColumn,
      regimeColumn,
      decisionColumn,
      barsColumn,
      researchColumn,
    ];
  }

  if (tab === "technical") {
    return [
      tickerColumn,
      priceColumn,
      changeColumn,
      sma20Column,
      sma50Column,
      sma200Column,
      rsiColumn,
      atrColumn,
      regimeColumn,
      researchColumn,
    ];
  }

  return [
    tickerColumn,
    assetTypeColumn,
    priceColumn,
    changeColumn,
    regimeColumn,
    decisionColumn,
    stabilityColumn,
    maxDrawdownColumn,
    barsColumn,
    researchColumn,
  ];
}

function AnalysisPanel({
  analysis,
  chartLoading,
  chartError,
  chartBars,
  chartSummary,
  chartQuote,
  chartNote,
  chartControls,
  onChartControlsChange,
  onClose,
}: {
  analysis: ScreenerAnalysisState;
  chartLoading: boolean;
  chartError: string;
  chartBars: ChartBar[];
  chartSummary: ChartSummary | null;
  chartQuote: QuoteSummary;
  chartNote: string;
  chartControls: ScreenerChartControls;
  onChartControlsChange: (next: ScreenerChartControls) => void;
  onClose: () => void;
}) {
  const mergedQuote: QuoteSummary = { ...analysis.quote, ...chartQuote };
  const row = analysis.row;
  const livePrice = toNumberOrNull(chartSummary?.close) ?? toNumberOrNull(mergedQuote.price) ?? row.price;
  const changePct = toNumberOrNull(chartSummary?.changePct) ?? toNumberOrNull(mergedQuote.changePct);
  const flowCards = [
    { label: "1M Flow", value: toNumberOrNull(mergedQuote.netFlows1MonthPct) },
    { label: "3M Flow", value: toNumberOrNull(mergedQuote.netFlows3MonthPct) },
    { label: "YTD Flow", value: toNumberOrNull(mergedQuote.netFlowsYtdPct) },
  ];
  const hasFundFlowMetrics = flowCards.some((card) => card.value !== null);
  const ufMetric = {
    regime: row.regime,
    decision: row.decision,
    stabilityScore: row.stabilityScore,
    maxDrawdown: row.maxDrawdown,
    coverage: fmtCoverage(row),
  };

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
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
            <div>
              <h2 style={{ margin: 0 }}>
                {row.ticker} <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
              </h2>
              <p className="tfe-muted" style={{ margin: "0.35rem 0 0" }}>
                {fmtText(mergedQuote.companyName, "Native Engine analysis")}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <a href={row.externalResearchUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                Research ↗
              </a>
              <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
                Close
              </button>
            </div>
          </div>

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
                <div>{fmtPrice(livePrice)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Change</strong>
                <div>{fmtPercentValue(changePct)}</div>
              </div>
              <div className="tfe-panel">
                <strong>52W Range</strong>
                <div>
                  {fmtPrice(toNumberOrNull(chartSummary?.low52))} - {fmtPrice(toNumberOrNull(chartSummary?.high52))}
                </div>
              </div>
              <div className="tfe-panel">
                <strong>Regime</strong>
                <div>{fmtText(ufMetric.regime)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Stability</strong>
                <div>{fmtNumber(ufMetric.stabilityScore, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Max DD</strong>
                <div>{fmtNumber(ufMetric.maxDrawdown, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Coverage</strong>
                <div>{ufMetric.coverage}</div>
              </div>
            </div>
          </section>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Chart</h3>
            {chartLoading ? <p className="tfe-muted">Loading chart...</p> : null}
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

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Fund Flows</h3>
            {hasFundFlowMetrics ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                  gap: "0.75rem",
                }}
              >
                {flowCards.map((card) => (
                  <div key={card.label} className="tfe-panel">
                    <strong>{card.label}</strong>
                    <div>{fmtPercentValue(card.value)}</div>
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

export default function ScreenerWorkbench() {
  const [tab, setTab] = useState<ScreenerTab>("overview");
  const [search, setSearch] = useState("");
  const [assetType, setAssetType] = useState("all");
  const [decision, setDecision] = useState("all");
  const [regime, setRegime] = useState("all");
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [pageQuotes, setPageQuotes] = useState<Record<string, QuoteSummary>>({});
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [assetOptions, setAssetOptions] = useState<AssetType[]>(DEFAULT_ASSET_OPTIONS);
  const [decisionOptions, setDecisionOptions] = useState<Decision[]>(DEFAULT_DECISION_OPTIONS);
  const [regimeOptions, setRegimeOptions] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<ScreenerAnalysisState | null>(null);
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [chartQuote, setChartQuote] = useState<QuoteSummary>({});
  const [chartNote, setChartNote] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadRows(): Promise<void> {
      setLoading(true);
      setError("");

      try {
        const query = new URLSearchParams();
        query.set("tab", tab);
        query.set("page", String(page));
        query.set("pageSize", String(DEFAULT_PAGE_SIZE));
        if (search.trim()) query.set("search", search.trim());
        if (assetType !== "all") query.set("assetType", assetType);
        if (decision !== "all") query.set("decision", decision);
        if (regime !== "all") query.set("regime", regime);

        const response = await fetch(`/api/screener?${query.toString()}`, {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });

        const payload = (await response.json()) as ScreenerResponse;
        if (!response.ok) {
          setRows([]);
          setPageQuotes({});
          setTotal(0);
          setTotalPages(1);
          setError(payload.error || "Screener load failed.");
          return;
        }

        setRows(Array.isArray(payload.rows) ? payload.rows : []);
        setPageQuotes(payload.pageQuotes && typeof payload.pageQuotes === "object" ? payload.pageQuotes : {});
        setTotal(Number.isFinite(payload.total) ? payload.total : 0);
        setTotalPages(Number.isFinite(payload.totalPages) && payload.totalPages > 0 ? payload.totalPages : 1);
        setAssetOptions(Array.isArray(payload.options?.assetTypes) ? payload.options.assetTypes : DEFAULT_ASSET_OPTIONS);
        setDecisionOptions(Array.isArray(payload.options?.decisions) ? payload.options.decisions : DEFAULT_DECISION_OPTIONS);
        setRegimeOptions(Array.isArray(payload.options?.regimes) ? payload.options.regimes : []);
      } catch (loadError) {
        if (controller.signal.aborted) return;
        setRows([]);
        setPageQuotes({});
        setTotal(0);
        setTotalPages(1);
        setError(loadError instanceof Error ? loadError.message : "Screener load failed.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadRows();
    return () => controller.abort();
  }, [assetType, decision, page, regime, search, tab]);

  useEffect(() => {
    if (!analysis) {
      setChartLoading(false);
      setChartError("");
      setChartBars([]);
      setChartSummary(null);
      setChartQuote({});
      setChartNote("");
      return;
    }

    const analysisTicker = analysis.row.ticker;
    const controller = new AbortController();

    async function loadChart(): Promise<void> {
      setChartLoading(true);
      setChartError("");

      try {
        const query = new URLSearchParams();
        query.set("ticker", normalizeTicker(analysisTicker));
        query.set("interval", chartControls.interval);
        query.set("range", chartControls.range);
        const response = await fetch(`/api/watchlist/chart?${query.toString()}`, {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });
        const payload = (await response.json()) as ChartResponse;

        if (!response.ok) {
          setChartBars([]);
          setChartSummary(null);
          setChartQuote({});
          setChartNote("");
          setChartError(payload.error || "Chart load failed.");
          return;
        }

        setChartBars(Array.isArray(payload.bars) ? payload.bars : []);
        setChartSummary(payload.summary ?? null);
        setChartQuote(payload.quote ?? {});
        setChartNote(payload.note ?? "");
      } catch (loadError) {
        if (controller.signal.aborted) return;
        setChartBars([]);
        setChartSummary(null);
        setChartQuote({});
        setChartNote("");
        setChartError(loadError instanceof Error ? loadError.message : "Chart load failed.");
      } finally {
        if (!controller.signal.aborted) {
          setChartLoading(false);
        }
      }
    }

    void loadChart();
    return () => controller.abort();
  }, [analysis, chartControls]);

  const sortedRows = useMemo(
    () => sortRows(rows, pageQuotes, sortKey, sortDirection),
    [pageQuotes, rows, sortDirection, sortKey],
  );

  const columns = useMemo(
    () =>
      buildColumns(tab, (row, quote) => {
        setAnalysis({ row, quote });
      }),
    [tab],
  );

  function resetToFirstPage(nextTab: ScreenerTab): void {
    setTab(nextTab);
    setPage(1);
  }

  function toggleSort(nextSortKey: SortKey): void {
    if (sortKey === nextSortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextSortKey);
    setSortDirection("asc");
  }

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <section className="tfe-panel" style={{ display: "grid", gap: "0.9rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {DATA_TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={item.key === tab ? "btn btn-primary btn-sm" : "btn btn-ghost btn-sm"}
              onClick={() => resetToFirstPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "0.75rem",
          }}
        >
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Search</span>
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Ticker"
            />
          </label>

          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Asset</span>
            <select
              value={assetType}
              onChange={(event) => {
                setAssetType(event.target.value);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              {assetOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Decision</span>
            <select
              value={decision}
              onChange={(event) => {
                setDecision(event.target.value);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              {decisionOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Regime</span>
            <select
              value={regime}
              onChange={(event) => {
                setRegime(event.target.value);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              {regimeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <span className="tfe-muted">
            {loading ? "Loading native engine rows..." : `${total.toLocaleString()} rows matched. Page ${page} of ${totalPages}.`}
          </span>
          <span className="tfe-muted">Fundamental taxonomy columns are intentionally removed from this UI.</span>
        </div>
      </section>

      {error ? <p className="tfe-error">{error}</p> : null}

      <section className="tfe-panel" style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <caption className="sr-only">Native Engine Screener Results</caption>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.id}
                  scope="col"
                  aria-sort={
                    column.sortKey && sortKey === column.sortKey
                      ? sortDirection === "asc"
                        ? "ascending"
                        : "descending"
                      : column.sortKey
                        ? "none"
                        : undefined
                  }
                  style={{
                    textAlign: column.align ?? "left",
                    padding: "0.75rem 0.6rem",
                    whiteSpace: "nowrap",
                  }}
                >
                  {column.sortKey ? (
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => toggleSort(column.sortKey ?? "ticker")}>
                      {column.label}
                      {sortKey === column.sortKey ? (sortDirection === "asc" ? " ↑" : " ↓") : ""}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => {
              const quote = pageQuotes[row.ticker] ?? {};
              return (
                <tr key={row.ticker}>
                  {columns.map((column) => (
                    <td
                      key={`${row.ticker}-${column.id}`}
                      style={{
                        padding: "0.75rem 0.6rem",
                        textAlign: column.align ?? "left",
                        verticalAlign: "top",
                        whiteSpace: column.id === "research" ? "nowrap" : "normal",
                      }}
                    >
                      {column.render(row, quote)}
                    </td>
                  ))}
                </tr>
              );
            })}
            {!loading && sortedRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: "1rem" }}>
                  <span className="tfe-muted">No rows matched the current native-engine filters.</span>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" className="btn btn-ghost btn-sm" disabled={page <= 1 || loading} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          Previous
        </button>
        <span className="tfe-muted">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={page >= totalPages || loading}
          onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
        >
          Next
        </button>
      </div>

      {analysis ? (
        <AnalysisPanel
          analysis={analysis}
          chartLoading={chartLoading}
          chartError={chartError}
          chartBars={chartBars}
          chartSummary={chartSummary}
          chartQuote={chartQuote}
          chartNote={chartNote}
          chartControls={chartControls}
          onChartControlsChange={setChartControls}
          onClose={() => setAnalysis(null)}
        />
      ) : null}
    </div>
  );
}
