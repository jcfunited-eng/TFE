"use client";

import { useCallback, useEffect, useRef, useState } from "react";


type PEE1Config = {
  execution_mode: "paper" | "live";
  auto_tfe_enabled: boolean;
  vault_funded_amount: number;
  risk_per_trade_pct: number;
};

type CustodyStatus =
  | "matched"
  | "broker_only"
  | "frozen_corporate_action"
  | "ledger_only"
  | "quantity_mismatch"
  | "duplicate_ledger"
  | "pending_order"
  | "submitted_without_broker_order"
  | "broker_unavailable";

type CustodySummary = {
  brokerPositions: number | null;
  ledgerSymbols: number;
  matched: number;
  discrepancies: number;
  unknownBecauseBrokerUnavailable: number;
  byStatus: Record<CustodyStatus, number>;
};

type PEE1Position = {
  id: string;
  ledger_ids: number[];
  ticker: string;
  signal_class: string;
  shares: number;
  ledger_shares: number;
  broker_shares: number | null;
  entry_price: number | null;
  current_price: number | null;
  market_value: number | null;
  dollar_allocation: number | null;
  unrealized_pl: number | null;
  unrealized_pl_pct: number | null;
  status: CustodyStatus;
  custody_status: CustodyStatus;
  custody_note: string;
  spy_dk: number | null;
  s_uf: number | null;
  bar_count: number | null;
  signal_detected_at: string;
  entry_filled_at: string | null;
  alpaca_order_id: string | null;
};

type ClosedTrade = {
  ticker: string;
  signal_class: string;
  shares: number;
  entry: number | null;
  exit: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  exit_reason: string;
  closed_at: string | null;
};

type PEE1Summary = {
  funded_amount: number;
  cash_on_hand: number | null;
  total_invested: number | null;
  portfolio_value: number | null;
  total_pl: number | null;
  total_pl_pct: number | null;
  pl_baseline: number;
  pl_method: string;
  total_realized: null;
  total_realized_status: string;
  ledger_realized: number | null;
  total_unrealized: number | null;
  open_positions: number | null;
  ledger_open_positions: number;
  open_orders: number | null;
  total_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  win_rate: string;
  win_rate_note: string;
  exit_reasons: Record<string, number>;
  recent_closed_trades: ClosedTrade[];
  execution_mode: string;
  auto_tfe_enabled: boolean;
  entries_halted: boolean;
  risk_per_trade_pct: number;
  alpaca_equity: number | null;
  alpaca_cash: number | null;
  broker_status: "available" | "partial" | "unavailable";
  broker_reasons: string[];
  broker_as_of: string;
  custody: CustodySummary;
};


function fmt(value: number | null, digits = 2): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}


function money(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value < 0 ? "−" : ""}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}


function pnlColor(value: number | null): string {
  if (value === null || value === 0) return "#64748b";
  return value > 0 ? "#15803d" : "#dc2626";
}


function displayDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleDateString();
}


function signalBadge(signalClass: string) {
  const palette: Record<string, string> = {
    "3WA": "#7c3aed",
    W1: "#16a34a",
    CH3: "#d97706",
    manual: "#64748b",
    BROKER: "#0f766e",
  };
  return (
    <span style={{ background: palette[signalClass] ?? "#374151", color: "#fff", borderRadius: 4, padding: "2px 7px", fontSize: "0.7rem", fontWeight: 700 }}>
      {signalClass}
    </span>
  );
}


function custodyColor(status: CustodyStatus): string {
  if (status === "matched" || status === "pending_order") return "#15803d";
  if (status === "broker_unavailable") return "#a16207";
  return "#dc2626";
}


async function readJson<T>(response: Response): Promise<T> {
  const body = await response.text();
  if (!body) throw new Error(`Empty response from ${response.url} (HTTP ${response.status})`);
  const parsed = JSON.parse(body) as T & { error?: string };
  if (!response.ok) throw new Error(parsed.error ?? `HTTP ${response.status}`);
  return parsed;
}


export default function PortfolioTFEManager() {
  const [summary, setSummary] = useState<PEE1Summary | null>(null);
  const [positions, setPositions] = useState<PEE1Position[]>([]);
  const [config, setConfig] = useState<PEE1Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [closedSortKey, setClosedSortKey] = useState<keyof ClosedTrade>("closed_at");
  const [closedSortDesc, setClosedSortDesc] = useState(true);
  // Frozen delisted remnants (broker-held, awaiting corporate-action
  // settlement) are real but unactionable — they collapse to one
  // footnote instead of standing rows. Custody stays truthful; the
  // list shows only what an engine can act on.
  const visiblePositions = positions.filter((p) => p.custody_status !== "frozen_corporate_action");
  const frozenRemnants = positions.filter((p) => p.custody_status === "frozen_corporate_action");
  const [notInitialized, setNotInitialized] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [fundedInput, setFundedInput] = useState("");
  const refreshInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [summaryResponse, positionsResponse, configResponse] = await Promise.all([
        fetch("/api/portfolio/pee1-summary", { cache: "no-store" }),
        fetch("/api/portfolio/pee1-positions", { cache: "no-store" }),
        fetch("/api/portfolio/pee1-config", { cache: "no-store" }),
      ]);
      if (summaryResponse.status === 503 || positionsResponse.status === 503 || configResponse.status === 503) {
        setNotInitialized(true);
        return;
      }
      const [summaryValue, positionsValue, configValue] = await Promise.all([
        readJson<PEE1Summary>(summaryResponse),
        readJson<{ positions: PEE1Position[] }>(positionsResponse),
        readJson<PEE1Config>(configResponse),
      ]);
      setSummary(summaryValue);
      setPositions(positionsValue.positions);
      setConfig(configValue);
      setFundedInput((current) => current || String(configValue.vault_funded_amount ?? 0));
      setNotInitialized(false);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Portfolio load failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    refreshInterval.current = setInterval(() => void load(), 30_000);
    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
    };
  }, [load]);

  async function saveConfig(patch: Partial<PEE1Config>) {
    setSavingConfig(true);
    try {
      const response = await fetch("/api/portfolio/pee1-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      await readJson(response);
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Configuration save failed");
    } finally {
      setSavingConfig(false);
    }
  }

  async function saveFundedAmount() {
    const value = Number(fundedInput);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Recorded baseline must be greater than zero.");
      return;
    }
    await saveConfig({ vault_funded_amount: value });
  }

  if (loading) return <div style={{ padding: 24, color: "#64748b" }}>Loading broker custody…</div>;
  if (notInitialized) return <div className="tfe-panel" style={{ padding: 20, color: "#a16207" }}>The portfolio ledger is not initialized.</div>;
  if (error) return <div className="tfe-panel" style={{ padding: 20, color: "#dc2626" }}>Portfolio unavailable: {error}</div>;

  const custody = summary?.custody;
  const discrepancy = (custody?.discrepancies ?? 0) > 0;
  const cardStyle = { padding: "14px 16px", textAlign: "center" as const };
  const inputStyle = { padding: "6px 9px", borderRadius: 6, border: "1px solid rgba(0,0,0,.18)", fontSize: "0.86rem" };

  const metrics = [
    { label: "Broker Equity", value: money(summary?.portfolio_value ?? null) },
    { label: "Broker Cash", value: money(summary?.cash_on_hand ?? null) },
    { label: "Broker Gross Market Value", value: money(summary?.total_invested ?? null) },
    { label: "Broker P&L vs Baseline", value: money(summary?.total_pl ?? null), color: pnlColor(summary?.total_pl ?? null), sub: summary?.total_pl_pct === null || summary?.total_pl_pct === undefined ? null : `${summary.total_pl_pct >= 0 ? "+" : ""}${fmt(summary.total_pl_pct)}%` },
    { label: "Broker Unrealized", value: money(summary?.total_unrealized ?? null), color: pnlColor(summary?.total_unrealized ?? null) },
    { label: "Ledger Realized", value: money(summary?.ledger_realized ?? null), color: pnlColor(summary?.ledger_realized ?? null), sub: "Not broker account realized P&L" },
    { label: "Ledger Strategy Win Rate", value: summary?.win_rate ?? "—", sub: summary ? `${summary.wins}W / ${summary.losses}L` : null },
    { label: "Broker Positions", value: summary?.open_positions === null || summary?.open_positions === undefined ? "—" : String(summary.open_positions), sub: summary ? `${summary.ledger_open_positions} ledger symbols` : null },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="tfe-panel" style={{ padding: "14px 18px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 18, alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: "0.82rem" }}>
            Mode
            <span style={{ borderRadius: 16, padding: "5px 14px", color: "#fff", background: "#2563eb", fontWeight: 700 }}>
              PAPER ONLY
            </span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: "0.82rem" }}>
            Auto-TFE
            <button onClick={() => config && saveConfig({ auto_tfe_enabled: !config.auto_tfe_enabled })} disabled={savingConfig} style={{ border: 0, borderRadius: 16, padding: "5px 14px", color: "#fff", background: config?.auto_tfe_enabled ? "#16a34a" : "#64748b", fontWeight: 700, cursor: "pointer" }}>
              {config?.auto_tfe_enabled ? "ON" : "OFF"}
            </button>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600, fontSize: "0.82rem" }}>
            Recorded baseline $
            <input type="number" value={fundedInput} onChange={(event) => setFundedInput(event.target.value)} onBlur={saveFundedAmount} min={1} step={100} style={{ ...inputStyle, width: 110 }} />
          </label>
          <span style={{ color: "#64748b", fontSize: "0.78rem" }}>Risk is owned by each channel law; no generic website override is active.</span>
        </div>
      </div>

      <div className="tfe-panel" style={{ padding: "12px 16px", borderColor: discrepancy ? "rgba(220,38,38,.45)" : "rgba(21,128,61,.35)" }}>
        <strong style={{ color: discrepancy ? "#dc2626" : "#15803d" }}>
          Custody {summary?.broker_status === "available" ? "observed" : "incomplete"}: {custody?.brokerPositions ?? "—"} broker positions · {custody?.ledgerSymbols ?? "—"} ledger symbols · {custody?.discrepancies ?? "—"} discrepancies
        </strong>
        <div style={{ marginTop: 4, color: "#64748b", fontSize: "0.78rem" }}>
          Snapshot {displayDate(summary?.broker_as_of ?? null)}. BROKER_ONLY holdings are visible but remain unclassified. Broker feed failures do not become zero balances or flat marks.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(165px,1fr))", gap: 10 }}>
        {metrics.map((metric) => (
          <div key={metric.label} className="tfe-panel" style={cardStyle}>
            <div style={{ fontSize: "0.67rem", color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em" }}>{metric.label}</div>
            <div style={{ fontSize: "1.16rem", fontWeight: 700, marginTop: 4, color: metric.color ?? "inherit" }}>{metric.value}</div>
            {metric.sub && <div style={{ fontSize: "0.68rem", color: "#64748b", marginTop: 3 }}>{metric.sub}</div>}
          </div>
        ))}
      </div>

      <div className="tfe-panel" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(0,0,0,.08)", display: "flex", gap: 8, alignItems: "center" }}>
          <h3 style={{ margin: 0, fontSize: ".95rem" }}>Broker / ledger position custody</h3>
          <span style={{ background: "#e2e8f0", borderRadius: 12, padding: "2px 8px", fontSize: ".72rem" }}>{visiblePositions.length}</span>
        </div>
        {visiblePositions.length === 0 ? <div style={{ padding: 22, color: "#64748b" }}>No broker holdings or open ledger rows.</div> : (
          <div style={{ overflowX: "auto" }}>
            <table className="tfe-table">
              <caption style={{ position: "absolute", width: 1, height: 1, overflow: "hidden" }}>Broker and ledger custody reconciliation</caption>
              <thead><tr>{["Ticker", "Ledger class", "Broker qty", "Ledger qty", "Entry", "Broker mark", "Market value", "Unrealized", "Return", "Custody", "Ledger detected"].map((heading) => <th key={heading} scope="col" style={{ whiteSpace: "nowrap" }}>{heading}</th>)}</tr></thead>
              <tbody>{visiblePositions.map((position) => (
                <tr key={position.id}>
                  <td style={{ fontWeight: 700 }}>{position.ticker}</td>
                  <td>{signalBadge(position.signal_class)}</td>
                  <td style={{ textAlign: "right" }}>{position.broker_shares === null ? "—" : fmt(position.broker_shares, 4)}</td>
                  <td style={{ textAlign: "right" }}>{fmt(position.ledger_shares, 4)}</td>
                  <td style={{ textAlign: "right" }}>{money(position.entry_price)}</td>
                  <td style={{ textAlign: "right" }}>{money(position.current_price)}</td>
                  <td style={{ textAlign: "right" }}>{money(position.market_value)}</td>
                  <td style={{ textAlign: "right", color: pnlColor(position.unrealized_pl), fontWeight: 600 }}>{money(position.unrealized_pl)}</td>
                  <td style={{ textAlign: "right", color: pnlColor(position.unrealized_pl_pct) }}>{position.unrealized_pl_pct === null ? "—" : `${position.unrealized_pl_pct >= 0 ? "+" : ""}${fmt(position.unrealized_pl_pct)}%`}</td>
                  <td title={position.custody_note}><span style={{ color: custodyColor(position.custody_status), fontWeight: 700, fontSize: ".7rem" }}>{position.custody_status.toUpperCase()}</span></td>
                  <td>{displayDate(position.signal_detected_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        {frozenRemnants.length ? (
          <div style={{ padding: "10px 18px", borderTop: "1px solid rgba(0,0,0,.06)", color: "#64748b", fontSize: ".74rem" }}>
            {frozenRemnants.length} delisted remnant{frozenRemnants.length > 1 ? "s" : ""} ({frozenRemnants.map((p) => p.ticker).join(", ")}) held at the broker awaiting corporate-action settlement — untradable, excluded from this list, leaves the account when the broker processes the action.
          </div>
        ) : null}
      </div>

      {summary?.recent_closed_trades.length ? (
        <div className="tfe-panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(0,0,0,.08)" }}>
            <h3 style={{ margin: 0, fontSize: ".95rem" }}>Ledger closed-trade history</h3>
            <div style={{ color: "#64748b", fontSize: ".74rem", marginTop: 3 }}>Provenance record only; not a complete broker realized-P&amp;L statement.</div>
          </div>
          <div style={{ overflowX: "auto" }}><table className="tfe-table">
            <thead><tr>{([
              ["closed_at", "Closed"], ["ticker", "Ticker"], ["signal_class", "Class"],
              ["shares", "Shares"], ["entry", "Entry"], ["exit", "Exit"],
              ["pnl", "Ledger P&L"], ["pnl_pct", "Return"], ["exit_reason", "Reason"],
            ] as const).map(([key, heading]) => (
              <th key={key} scope="col" title="Click to sort"
                style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
                onClick={() => {
                  if (closedSortKey === key) setClosedSortDesc((d) => !d);
                  else { setClosedSortKey(key); setClosedSortDesc(true); }
                }}>
                {heading}{closedSortKey === key ? (closedSortDesc ? " ▼" : " ▲") : ""}
              </th>
            ))}</tr></thead>
            <tbody>{[...summary.recent_closed_trades].sort((a, b) => {
              const av = a[closedSortKey];
              const bv = b[closedSortKey];
              const cmp = typeof av === "number" && typeof bv === "number"
                ? av - bv
                : String(av ?? "").localeCompare(String(bv ?? ""));
              return closedSortDesc ? -cmp : cmp;
            }).map((trade, index) => <tr key={`${trade.ticker}:${trade.closed_at}:${index}`}>
              <td>{displayDate(trade.closed_at)}</td><td style={{ fontWeight: 700 }}>{trade.ticker}</td><td>{signalBadge(trade.signal_class)}</td>
              <td style={{ textAlign: "right" }}>{fmt(trade.shares, 4)}</td><td style={{ textAlign: "right" }}>{money(trade.entry)}</td><td style={{ textAlign: "right" }}>{money(trade.exit)}</td>
              <td style={{ textAlign: "right", color: pnlColor(trade.pnl), fontWeight: 700 }}>{money(trade.pnl)}</td>
              <td style={{ textAlign: "right", color: pnlColor(trade.pnl_pct) }}>{trade.pnl_pct === null ? "—" : `${trade.pnl_pct >= 0 ? "+" : ""}${fmt(trade.pnl_pct)}%`}</td>
              <td>{trade.exit_reason.replaceAll("_", " ")}</td>
            </tr>)}</tbody>
          </table></div>
        </div>
      ) : null}

      <div className="tfe-panel" style={{ padding: "16px 18px" }}>
        <h3 style={{ margin: 0, fontSize: ".95rem" }}>Order custody</h3>
        <div style={{ color: summary?.entries_halted ? "#a16207" : "#64748b", marginTop: 7, fontSize: ".8rem" }}>
          {summary?.entries_halted
            ? "Automatic entries are halted. Existing-position exits remain supervised."
            : "Only the supervised automatic paper pipeline may originate orders. Manual and ledger-only order creation are disabled."}
        </div>
      </div>
    </div>
  );
}
