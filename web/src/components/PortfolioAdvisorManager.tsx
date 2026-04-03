"use client";

import { useEffect, useMemo, useState } from "react";

import ClientPortal from "@/components/ClientPortal";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type ScreenerChartControls,
} from "@/components/ScreenerChart";

type DecisionLabel = "Accumulate" | "Hold" | "Avoid" | "Unavailable";
type SortDirection = "asc" | "desc";
type PositionSortKey =
  | "ticker"
  | "assetType"
  | "units"
  | "avgCost"
  | "currentPrice"
  | "marketValue"
  | "unrealizedPnLPct"
  | "decision"
  | "S_UF"
  | "R_UF"
  | "barCount";

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
  changePct: number | null;
  decision: DecisionLabel;
  decisionAvailable: boolean;
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL" | "UNAVAILABLE";
  publishedDecisionStatus: "ok" | "missing" | "invalid";
  regime: string;
  stabilityScore: number | null;
  maxDrawdown: number | null;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  externalResearchUrl: string;
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

type PortfolioProvenance = {
  status: "ok" | "partial";
  sourcePath: string | null;
  failureCount: number;
  rows_required: number;
  rows_valid: number;
  missingTickers: string[];
  invalidTickers: string[];
  unresolvedTickers: Array<{
    ticker: string;
    status: "missing" | "invalid";
    lots: number;
    units: number;
    costBasis: number;
  }>;
};

type PortfolioResponse = {
  lots: PortfolioLot[];
  positions: PositionRow[];
  summary: PortfolioSummary;
  warning?: string | null;
  provenance?: PortfolioProvenance;
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
  price?: number | null;
  change?: number | null;
  changePct?: number | null;
  volume?: number | null;
  avgVolume?: number | null;
  netFlows1MonthPct?: number | null;
  netFlows3MonthPct?: number | null;
  netFlowsYtdPct?: number | null;
};

type UfMetric = {
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

function fmtPercentRatio(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const pct = value * 100;
  const prefix = pct > 0 ? "+" : "";
  return `${prefix}${pct.toFixed(decimals)}%`;
}

function fmtPercentValue(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(decimals)}%`;
}

function fmtDateTime(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
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

function sortPositions(rows: PositionRow[], key: PositionSortKey, direction: SortDirection): PositionRow[] {
  const next = [...rows];
  next.sort((left, right) => {
    if (key === "ticker") return compareText(left.ticker, right.ticker, direction);
    if (key === "assetType") return compareText(left.assetType, right.assetType, direction);
    if (key === "units") return compareNumber(left.units, right.units, direction);
    if (key === "avgCost") return compareNumber(left.avgCost, right.avgCost, direction);
    if (key === "currentPrice") return compareNumber(left.currentPrice, right.currentPrice, direction);
    if (key === "marketValue") return compareNumber(left.marketValue, right.marketValue, direction);
    if (key === "unrealizedPnLPct") return compareNumber(left.unrealizedPnLPct, right.unrealizedPnLPct, direction);
    if (key === "decision") return compareText(left.decision, right.decision, direction);
    if (key === "S_UF") return compareNumber(left.S_UF, right.S_UF, direction);
    if (key === "R_UF") return compareNumber(left.R_UF, right.R_UF, direction);
    return compareNumber(left.barCount, right.barCount, direction);
  });
  return next;
}

function decisionClass(value: DecisionLabel | UfMetric["decision"]): string {
  if (value === "Accumulate") return "is-buy";
  if (value === "Avoid") return "is-sell";
  return "is-hold";
}

function AnalysisPanel({
  position,
  chartLoading,
  chartError,
  chartBars,
  chartSummary,
  chartQuote,
  chartNote,
  chartControls,
  onChartControlsChange,
  ufMetric,
  onClose,
}: {
  position: PositionRow;
  chartLoading: boolean;
  chartError: string;
  chartBars: ChartBar[];
  chartSummary: ChartSummary | null;
  chartQuote: QuoteSummary;
  chartNote: string;
  chartControls: ScreenerChartControls;
  onChartControlsChange: (next: ScreenerChartControls) => void;
  ufMetric: UfMetric | null;
  onClose: () => void;
}) {
  const displayPrice = toNumberOrNull(chartSummary?.close) ?? toNumberOrNull(chartQuote.price) ?? position.currentPrice;
  const changePct = toNumberOrNull(chartSummary?.changePct) ?? toNumberOrNull(chartQuote.changePct) ?? position.changePct;
  const flowCards = [
    { label: "1M Flow", value: toNumberOrNull(chartQuote.netFlows1MonthPct) },
    { label: "3M Flow", value: toNumberOrNull(chartQuote.netFlows3MonthPct) },
    { label: "YTD Flow", value: toNumberOrNull(chartQuote.netFlowsYtdPct) },
  ];
  const hasFundFlowMetrics = flowCards.some((card) => card.value !== null);
  const regime = ufMetric?.regime ?? position.regime;
  const stability = toNumberOrNull(ufMetric?.stability_score) ?? position.stabilityScore;
  const maxDrawdown = toNumberOrNull(ufMetric?.max_dd) ?? position.maxDrawdown;
  const decision = ufMetric?.decision ?? position.decision;
  const decisionReason = ufMetric?.decisionReason ?? position.decisionReason;
  const decisionReasonCode = ufMetric?.decisionReasonCode ?? position.decisionReasonCode;
  const classification = ufMetric?.classification ?? position.classification;
  const structuralSupport = toNumberOrNull(ufMetric?.S_UF) ?? position.S_UF;
  const structuralResistance = toNumberOrNull(ufMetric?.R_UF) ?? position.R_UF;

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
                {position.ticker} <span className={`tfe-chip ${decisionClass(decision)}`}>{decision}</span>
              </h2>
              <p className="tfe-muted" style={{ margin: "0.35rem 0 0" }}>
                {decisionReason}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <a href={position.externalResearchUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                Research ↗
              </a>
              <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
                Close
              </button>
            </div>
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
                <strong>Published Status</strong>
                <div>{fmtText(position.publishedDecisionStatus)}</div>
              </div>
            </div>
            <p className="tfe-muted" style={{ margin: 0 }}>
              {decisionReason}
            </p>
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
                <div>{fmtPercentValue(changePct)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Market Value</strong>
                <div>{fmtPrice(position.marketValue)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Net P/L</strong>
                <div>{fmtPercentRatio(position.unrealizedPnLPct)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Regime</strong>
                <div>{fmtText(regime)}</div>
              </div>
              <div className="tfe-panel">
                <strong>S_UF</strong>
                <div>{fmtNumber(structuralSupport, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>R_UF</strong>
                <div>{fmtNumber(structuralResistance, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Stability</strong>
                <div>{fmtNumber(stability, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Max DD</strong>
                <div>{fmtNumber(maxDrawdown, 2)}</div>
              </div>
              <div className="tfe-panel">
                <strong>Coverage</strong>
                <div>
                  {position.barCount}/{position.minBarsForAccumulate}
                </div>
              </div>
            </div>
          </section>

          <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Chart</h3>
            {chartLoading ? <p className="tfe-muted">Loading chart...</p> : null}
            {chartError ? <p className="tfe-error">{chartError}</p> : null}
            {!chartLoading && !chartError && chartBars.length > 0 ? (
              <ScreenerChart
                ticker={position.ticker}
                bars={chartBars}
                controls={chartControls}
                loading={chartLoading}
                onControlsChange={onChartControlsChange}
              />
            ) : null}
            {!chartLoading && !chartError && chartBars.length === 0 ? (
              <p className="tfe-muted">{chartNote || `No chart data available for ${position.ticker}.`}</p>
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
              <p className="tfe-muted">Fund flow metrics are not present in the live portfolio analysis payload for this ticker.</p>
            )}
          </section>
        </div>
      </div>
    </ClientPortal>
  );
}

export default function PortfolioAdvisorManager() {
  const [inputTicker, setInputTicker] = useState("");
  const [inputUnits, setInputUnits] = useState("1");
  const [inputUnitCost, setInputUnitCost] = useState("0");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [warning, setWarning] = useState("");
  const [lots, setLots] = useState<PortfolioLot[]>([]);
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [provenance, setProvenance] = useState<PortfolioProvenance | null>(null);
  const [sortKey, setSortKey] = useState<PositionSortKey>("ticker");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [selectedPosition, setSelectedPosition] = useState<PositionRow | null>(null);
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [chartQuote, setChartQuote] = useState<QuoteSummary>({});
  const [chartNote, setChartNote] = useState("");
  const [chartUfMetric, setChartUfMetric] = useState<UfMetric | null>(null);

  async function loadPortfolio(): Promise<void> {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/portfolio", {
        method: "GET",
        cache: "no-store",
      });
      const payload = (await response.json()) as PortfolioResponse;

      if (!response.ok) {
        setLots([]);
        setPositions([]);
        setSummary(null);
        setProvenance(null);
        setWarning("");
        setError(payload.error || "Portfolio load failed.");
        return;
      }

      setLots(Array.isArray(payload.lots) ? payload.lots : []);
      setPositions(Array.isArray(payload.positions) ? payload.positions : []);
      setSummary(payload.summary ?? null);
      setProvenance(payload.provenance ?? null);
      setWarning(payload.warning ?? "");
    } catch (loadError) {
      setLots([]);
      setPositions([]);
      setSummary(null);
      setProvenance(null);
      setWarning("");
      setError(loadError instanceof Error ? loadError.message : "Portfolio load failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPortfolio();
  }, []);

  useEffect(() => {
    if (!selectedPosition) {
      setChartLoading(false);
      setChartError("");
      setChartBars([]);
      setChartSummary(null);
      setChartQuote({});
      setChartNote("");
      setChartUfMetric(null);
      return;
    }

    const selectedTicker = selectedPosition.ticker;
    const controller = new AbortController();

    async function loadChart(): Promise<void> {
      setChartLoading(true);
      setChartError("");

      try {
        const query = new URLSearchParams();
        query.set("ticker", normalizeTicker(selectedTicker));
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
          setChartUfMetric(null);
          setChartError(payload.error || "Chart load failed.");
          return;
        }

        setChartBars(Array.isArray(payload.bars) ? payload.bars : []);
        setChartSummary(payload.summary ?? null);
        setChartQuote(payload.quote ?? {});
        setChartNote(payload.note ?? "");
        setChartUfMetric(payload.ufMetric ?? null);
      } catch (loadError) {
        if (controller.signal.aborted) return;
        setChartBars([]);
        setChartSummary(null);
        setChartQuote({});
        setChartNote("");
        setChartUfMetric(null);
        setChartError(loadError instanceof Error ? loadError.message : "Chart load failed.");
      } finally {
        if (!controller.signal.aborted) {
          setChartLoading(false);
        }
      }
    }

    void loadChart();
    return () => controller.abort();
  }, [chartControls, selectedPosition]);

  const sortedPositions = useMemo(
    () => sortPositions(positions, sortKey, sortDirection),
    [positions, sortDirection, sortKey],
  );

  function toggleSort(nextKey: PositionSortKey): void {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection("asc");
  }

  async function handleAddLot(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch("/api/portfolio", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticker: normalizeTicker(inputTicker),
          units: Number(inputUnits),
          unitCost: Number(inputUnitCost),
        }),
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        setError(payload.error || "Failed to add lot.");
        return;
      }

      setMessage(`Added ${normalizeTicker(inputTicker)} to the manual portfolio.`);
      setInputTicker("");
      setInputUnits("1");
      setInputUnitCost("0");
      await loadPortfolio();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to add lot.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteLot(lotId: string): Promise<void> {
    if (!window.confirm("Remove this lot from the manual portfolio?")) return;

    setSaving(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`/api/portfolio?id=${encodeURIComponent(lotId)}`, {
        method: "DELETE",
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        setError(payload.error || "Failed to delete lot.");
        return;
      }

      setMessage("Lot removed.");
      await loadPortfolio();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Failed to delete lot.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <section className="tfe-panel" style={{ display: "grid", gap: "0.75rem" }}>
        <h2 style={{ margin: 0 }}>Manual Portfolio</h2>
        <form
          onSubmit={(event) => {
            void handleAddLot(event);
          }}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "0.75rem",
          }}
        >
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Ticker</span>
            <input value={inputTicker} onChange={(event) => setInputTicker(event.target.value)} placeholder="AAPL" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Units</span>
            <input value={inputUnits} onChange={(event) => setInputUnits(event.target.value)} inputMode="decimal" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>Unit Cost</span>
            <input value={inputUnitCost} onChange={(event) => setInputUnitCost(event.target.value)} inputMode="decimal" />
          </label>
          <div style={{ display: "flex", alignItems: "end" }}>
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
              {saving ? "Saving..." : "Add Lot"}
            </button>
          </div>
        </form>
      </section>

      {error ? <p className="tfe-error">{error}</p> : null}
      {message ? <p className="tfe-muted">{message}</p> : null}
      {warning ? <p className="tfe-muted">{warning}</p> : null}

      {summary ? (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "0.75rem",
          }}
        >
          <div className="tfe-panel">
            <strong>Positions</strong>
            <div>{summary.totalPositions}</div>
          </div>
          <div className="tfe-panel">
            <strong>Total Market Value</strong>
            <div>{fmtPrice(summary.totalMarketValue)}</div>
          </div>
          <div className="tfe-panel">
            <strong>Total Cost Basis</strong>
            <div>{fmtPrice(summary.totalCostBasis)}</div>
          </div>
          <div className="tfe-panel">
            <strong>Unrealized P/L</strong>
            <div>{fmtPrice(summary.totalUnrealizedPnL)}</div>
          </div>
          <div className="tfe-panel">
            <strong>Unrealized P/L %</strong>
            <div>{fmtPercentRatio(summary.totalUnrealizedPnLPct)}</div>
          </div>
        </section>
      ) : null}

      <section className="tfe-panel" style={{ overflowX: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", marginBottom: "0.75rem" }}>
          <h2 style={{ margin: 0 }}>Positions</h2>
          <span className="tfe-muted">{loading ? "Loading positions..." : `${positions.length} positions`}</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <caption className="sr-only">Portfolio Positions</caption>
          <thead>
            <tr>
              {(
                [
                  ["ticker", "Ticker"],
                  ["assetType", "Asset"],
                  ["units", "Units"],
                  ["avgCost", "Avg Cost"],
                  ["currentPrice", "Price"],
                  ["marketValue", "Market Value"],
                  ["unrealizedPnLPct", "Net P/L %"],
                  ["decision", "Decision"],
                  ["S_UF", "S_UF"],
                  ["R_UF", "R_UF"],
                  ["barCount", "Bars"],
                ] as [PositionSortKey, string][]
              ).map(([key, label]) => {
                const isText = key === "ticker" || key === "assetType" || key === "decision";
                const ariaSort: "ascending" | "descending" | "none" =
                  sortKey === key ? (sortDirection === "asc" ? "ascending" : "descending") : "none";
                return (
                  <th
                    key={key}
                    scope="col"
                    aria-sort={ariaSort}
                    style={{ textAlign: isText ? "left" : "right", padding: "0.75rem 0.6rem" }}
                  >
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => toggleSort(key)}>
                      {label}
                      {sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : ""}
                    </button>
                  </th>
                );
              })}
              <th scope="col" style={{ textAlign: "right", padding: "0.75rem 0.6rem" }}>Research</th>
            </tr>
          </thead>
          <tbody>
            {sortedPositions.map((row) => (
              <tr key={row.ticker}>
                <td style={{ padding: "0.75rem 0.6rem" }}>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelectedPosition(row)}>
                    {row.ticker}
                  </button>
                </td>
                <td style={{ padding: "0.75rem 0.6rem" }}>{row.assetType}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtNumber(row.units, 4)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtPrice(row.avgCost)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtPrice(row.currentPrice)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtPrice(row.marketValue)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtPercentRatio(row.unrealizedPnLPct)}</td>
                <td style={{ padding: "0.75rem 0.6rem" }}>
                  <span className={`tfe-chip ${decisionClass(row.decision)}`}>{row.decision}</span>
                </td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtNumber(row.S_UF, 2)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtNumber(row.R_UF, 2)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>
                  {row.barCount}/{row.minBarsForAccumulate}
                </td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right", whiteSpace: "nowrap" }}>
                  <a href={row.externalResearchUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                    Research ↗
                  </a>
                </td>
              </tr>
            ))}
            {!loading && sortedPositions.length === 0 ? (
              <tr>
                <td colSpan={12} style={{ padding: "1rem" }}>
                  <span className="tfe-muted">No manual positions have been added yet.</span>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <section className="tfe-panel" style={{ overflowX: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", marginBottom: "0.75rem" }}>
          <h2 style={{ margin: 0 }}>Lots</h2>
          <span className="tfe-muted">{lots.length} lots</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <caption className="sr-only">Portfolio Lots</caption>
          <thead>
            <tr>
              <th scope="col" style={{ textAlign: "left", padding: "0.75rem 0.6rem" }}>Ticker</th>
              <th scope="col" style={{ textAlign: "right", padding: "0.75rem 0.6rem" }}>Units</th>
              <th scope="col" style={{ textAlign: "right", padding: "0.75rem 0.6rem" }}>Unit Cost</th>
              <th scope="col" style={{ textAlign: "left", padding: "0.75rem 0.6rem" }}>Added</th>
              <th scope="col" style={{ textAlign: "left", padding: "0.75rem 0.6rem" }}>Updated</th>
              <th scope="col" style={{ textAlign: "right", padding: "0.75rem 0.6rem" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {lots.map((lot) => (
              <tr key={lot.id}>
                <td style={{ padding: "0.75rem 0.6rem" }}>{lot.ticker}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtNumber(lot.units, 4)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>{fmtPrice(lot.unitCost)}</td>
                <td style={{ padding: "0.75rem 0.6rem" }}>{fmtDateTime(lot.addedAt)}</td>
                <td style={{ padding: "0.75rem 0.6rem" }}>{fmtDateTime(lot.updatedAt)}</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "right" }}>
                  <button type="button" className="btn btn-ghost btn-sm" disabled={saving} onClick={() => void handleDeleteLot(lot.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {lots.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: "1rem" }}>
                  <span className="tfe-muted">No lots are stored for this manual portfolio.</span>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      {provenance && provenance.unresolvedTickers.length > 0 ? (
        <section className="tfe-panel">
          <h2 style={{ marginTop: 0 }}>Unresolved Tickers</h2>
          <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
            {provenance.unresolvedTickers.map((item) => (
              <li key={`${item.ticker}-${item.status}`}>
                {item.ticker}: {item.status}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {selectedPosition ? (
        <AnalysisPanel
          position={selectedPosition}
          chartLoading={chartLoading}
          chartError={chartError}
          chartBars={chartBars}
          chartSummary={chartSummary}
          chartQuote={chartQuote}
          chartNote={chartNote}
          chartControls={chartControls}
          onChartControlsChange={setChartControls}
          ufMetric={chartUfMetric}
          onClose={() => setSelectedPosition(null)}
        />
      ) : null}
    </div>
  );
}
