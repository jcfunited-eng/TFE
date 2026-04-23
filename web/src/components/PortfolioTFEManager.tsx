"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type PEE1Config = {
  execution_mode: "paper" | "live";
  auto_tfe_enabled: boolean;
  vault_funded_amount: number;
  risk_per_trade_pct: number;
};

type PEE1Position = {
  id: number;
  ticker: string;
  signal_class: string;
  shares: number;
  entry_price: number | null;
  current_price: number | null;
  dollar_allocation: number | null;
  unrealized_pl: number | null;
  unrealized_pl_pct: number | null;
  status: string;
  spy_dk: number | null;
  s_uf: number | null;
  bar_count: number | null;
  signal_detected_at: string;
  entry_filled_at: string | null;
  alpaca_order_id: string | null;
};

type PEE1Summary = {
  funded_amount: number;
  cash_on_hand: number;
  total_invested: number;
  portfolio_value: number;
  total_pl: number;
  total_pl_pct: number | null;
  total_realized: number;
  total_unrealized: number;
  open_positions: number;
  total_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  win_rate: string;
  exit_reasons: Record<string, number>;
  execution_mode: string;
  auto_tfe_enabled: boolean;
  risk_per_trade_pct: number;
  alpaca_equity: number | null;
  alpaca_cash: number | null;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null, digits = 2): string {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtDollar(n: number | null): string {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const abs = Math.abs(n);
  const prefix = n < 0 ? "-$" : "$";
  return prefix + abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function plColor(n: number | null): string {
  if (n === null) return "#888";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ef4444";
  return "#888";
}

function signalBadge(cls: string): React.ReactNode {
  if (cls === "3WA") return <span style={{ background: "#7c3aed", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.04em" }}>3WA</span>;
  if (cls === "W1")  return <span style={{ background: "#16a34a", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: "0.72rem", fontWeight: 700 }}>W1</span>;
  if (cls === "CH3") return <span style={{ background: "#d97706", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.04em" }}>CH3 ⚡</span>;
  if (cls === "manual") return <span style={{ background: "#64748b", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: "0.72rem", fontWeight: 700 }}>MANUAL</span>;
  return <span style={{ background: "#374151", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: "0.72rem" }}>{cls}</span>;
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function PortfolioTFEManager() {
  const [summary, setSummary]     = useState<PEE1Summary | null>(null);
  const [positions, setPositions] = useState<PEE1Position[]>([]);
  const [config, setConfig]       = useState<PEE1Config | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [notInit, setNotInit]     = useState(false);

  // Config save state
  const [savingConfig, setSavingConfig] = useState(false);
  const [fundedInput, setFundedInput]   = useState("");
  const [riskInput, setRiskInput]       = useState("");

  // Manual order state
  const [orderSide, setOrderSide]         = useState<"buy" | "sell">("buy");
  const [orderTicker, setOrderTicker]     = useState("");
  const [orderShares, setOrderShares]     = useState("");
  const [orderType, setOrderType]         = useState<"market" | "limit">("market");
  const [orderLimitPrice, setOrderLimitPrice] = useState("");
  const [orderNotes, setOrderNotes]       = useState("");
  const [placingOrder, setPlacingOrder]   = useState(false);
  const [orderMsg, setOrderMsg]           = useState<{ text: string; ok: boolean } | null>(null);

  const refreshInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [sumRes, posRes, cfgRes] = await Promise.all([
        fetch("/api/portfolio/pee1-summary"),
        fetch("/api/portfolio/pee1-positions"),
        fetch("/api/portfolio/pee1-config"),
      ]);

      if (sumRes.status === 401 || sumRes.status === 403) {
        setError("Access denied — admin account required.");
        setLoading(false);
        return;
      }

      if (sumRes.status === 503 || posRes.status === 503) {
        setNotInit(true);
        setLoading(false);
        return;
      }

      // Guard: only call .json() if response has a body
      const readJson = async (res: Response) => {
        const text = await res.text();
        if (!text) throw new Error(`Empty response (status ${res.status})`);
        return JSON.parse(text) as unknown;
      };

      const [sumData, posData, cfgData] = await Promise.all([
        readJson(sumRes) as Promise<PEE1Summary & { error?: string }>,
        readJson(posRes) as Promise<{ positions: PEE1Position[]; error?: string }>,
        readJson(cfgRes) as Promise<PEE1Config & { error?: string }>,
      ]);

      if (cfgData.error === "tables_not_initialized") { setNotInit(true); setLoading(false); return; }

      setSummary(sumData);
      setPositions(posData.positions ?? []);
      setConfig(cfgData);
      if (!fundedInput) setFundedInput(String(cfgData.vault_funded_amount ?? 0));
      if (!riskInput)   setRiskInput(String(cfgData.risk_per_trade_pct ?? 1.5));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
    refreshInterval.current = setInterval(load, 30_000);
    return () => { if (refreshInterval.current) clearInterval(refreshInterval.current); };
  }, [load]);

  async function saveConfig(patch: Partial<PEE1Config>) {
    setSavingConfig(true);
    try {
      await fetch("/api/portfolio/pee1-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      await load();
    } finally {
      setSavingConfig(false);
    }
  }

  async function toggleMode() {
    if (!config) return;
    const next = config.execution_mode === "paper" ? "live" : "paper";
    if (next === "live") {
      const ok = window.confirm(
        "Switch to LIVE trading?\n\nThis will use REAL MONEY. All orders placed by PEE-1 will be live trades on your Alpaca account.\n\nType OK to confirm."
      );
      if (!ok) return;
    }
    await saveConfig({ execution_mode: next });
  }

  async function toggleAutoTFE() {
    if (!config) return;
    const next = !config.auto_tfe_enabled;
    await saveConfig({ auto_tfe_enabled: next });
  }

  async function saveFundedAmount() {
    const n = parseFloat(fundedInput);
    if (isNaN(n) || n < 0) return;
    await saveConfig({ vault_funded_amount: n });
  }

  async function saveRisk() {
    const n = parseFloat(riskInput);
    if (isNaN(n) || n < 0.1 || n > 5) return;
    await saveConfig({ risk_per_trade_pct: n });
  }

  async function placeManualOrder() {
    setOrderMsg(null);
    const ticker = orderTicker.trim().toUpperCase();
    const shares = parseFloat(orderShares);
    const limitPrice = orderType === "limit" ? parseFloat(orderLimitPrice) : undefined;

    if (!ticker) { setOrderMsg({ text: "Ticker is required.", ok: false }); return; }
    if (isNaN(shares) || shares <= 0) { setOrderMsg({ text: "Shares must be a positive number.", ok: false }); return; }
    if (orderType === "limit" && (!limitPrice || isNaN(limitPrice) || limitPrice <= 0)) {
      setOrderMsg({ text: "Limit price required for limit orders.", ok: false }); return;
    }

    setPlacingOrder(true);
    try {
      const res = await fetch("/api/portfolio/pee1-place-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          side: orderSide,
          shares,
          order_type: orderType,
          limit_price: limitPrice,
          notes: orderNotes,
        }),
      });
      const data = await res.json() as { ok?: boolean; error?: string; warning?: string; alpaca_status?: string; execution_mode?: string };
      if (data.ok) {
        const mode = data.execution_mode === "live" ? "LIVE" : "paper";
        const status = data.alpaca_status ?? "submitted";
        const warn = data.warning ? ` ⚠ ${data.warning}` : "";
        setOrderMsg({ text: `Order ${status} on Alpaca (${mode}).${warn}`, ok: true });
        setOrderTicker(""); setOrderShares(""); setOrderLimitPrice(""); setOrderNotes("");
        await load();
      } else {
        setOrderMsg({ text: data.error ?? "Order failed.", ok: false });
      }
    } finally {
      setPlacingOrder(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) return <div style={{ padding: 24, color: "#888" }}>Loading portfolio...</div>;

  if (notInit) return (
    <div className="tfe-panel" style={{ padding: 24, borderColor: "rgba(234,179,8,0.4)" }}>
      <h3 style={{ margin: "0 0 8px", color: "#b45309" }}>DB Setup Required</h3>
      <p style={{ margin: 0, fontSize: "0.9rem", color: "#78716c" }}>
        The PEE-1 portfolio tables have not been initialized yet. Run the DB migrations to activate automated trading.
      </p>
      <code style={{ display: "block", marginTop: 12, fontSize: "0.78rem", color: "#57534e", background: "rgba(0,0,0,0.04)", padding: "8px 12px", borderRadius: 6 }}>
        psql $DATABASE_URL -f 001_personal_trade_ledger.sql{"\n"}
        psql $DATABASE_URL -f 002_pee1_config_and_circuit_breaker.sql{"\n"}
        psql $DATABASE_URL -f 003_pee1_portfolio_config.sql
      </code>
    </div>
  );

  if (error) return <div style={{ padding: 24, color: "#ef4444" }}>{error}</div>;

  const isLive = config?.execution_mode === "live";
  const autoOn = config?.auto_tfe_enabled ?? false;
  const pl = summary?.total_pl ?? 0;
  const plPct = summary?.total_pl_pct ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Control Bar ─────────────────────────────────────────────────── */}
      <div className="tfe-panel" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center" }}>

          {/* Paper / Live toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#374151" }}>Mode</span>
            <button
              onClick={toggleMode}
              disabled={savingConfig}
              style={{
                padding: "5px 14px",
                borderRadius: 20,
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.78rem",
                letterSpacing: "0.06em",
                background: isLive ? "#ef4444" : "#2563eb",
                color: "#fff",
                opacity: savingConfig ? 0.6 : 1,
              }}
            >
              {isLive ? "LIVE" : "PAPER"}
            </button>
            {isLive && <span style={{ fontSize: "0.72rem", color: "#ef4444", fontWeight: 600 }}>REAL MONEY</span>}
          </div>

          <div style={{ width: 1, height: 32, background: "rgba(0,0,0,0.1)" }} />

          {/* Auto-TFE toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#374151" }}>Auto-TFE</span>
            <button
              onClick={toggleAutoTFE}
              disabled={savingConfig}
              style={{
                padding: "5px 14px",
                borderRadius: 20,
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.78rem",
                letterSpacing: "0.06em",
                background: autoOn ? "#16a34a" : "#6b7280",
                color: "#fff",
                opacity: savingConfig ? 0.6 : 1,
              }}
            >
              {autoOn ? "ON" : "OFF"}
            </button>
            <span style={{ fontSize: "0.72rem", color: autoOn ? "#16a34a" : "#6b7280" }}>
              {autoOn ? "TFE will trade automatically" : "Signals computed, no orders placed"}
            </span>
          </div>

          <div style={{ width: 1, height: 32, background: "rgba(0,0,0,0.1)" }} />

          {/* Funded amount */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#374151" }}>Funded</span>
            <span style={{ fontSize: "0.78rem", color: "#64748b" }}>$</span>
            <input
              type="number"
              value={fundedInput}
              onChange={e => setFundedInput(e.target.value)}
              onBlur={saveFundedAmount}
              min={0}
              step={100}
              style={{ width: 110, padding: "4px 8px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.88rem" }}
            />
          </div>

          <div style={{ width: 1, height: 32, background: "rgba(0,0,0,0.1)" }} />

          {/* Risk per trade */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#374151" }}>Risk/Trade</span>
            <input
              type="number"
              value={riskInput}
              onChange={e => setRiskInput(e.target.value)}
              onBlur={saveRisk}
              min={0.1}
              max={5}
              step={0.1}
              style={{ width: 60, padding: "4px 8px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.88rem" }}
            />
            <span style={{ fontSize: "0.78rem", color: "#64748b" }}>%</span>
          </div>
        </div>
      </div>

      {/* ── Metrics Bar ─────────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        {[
          { label: "Portfolio Value", value: fmtDollar(summary?.portfolio_value ?? null) },
          { label: "Cash on Hand",    value: fmtDollar(summary?.cash_on_hand ?? null) },
          { label: "Invested",        value: fmtDollar(summary?.total_invested ?? null) },
          { label: "Total P&L",       value: fmtDollar(pl), color: plColor(pl), sub: plPct !== null ? `${plPct >= 0 ? "+" : ""}${fmt(plPct)}%` : null },
          { label: "Realized",        value: fmtDollar(summary?.total_realized ?? null), color: plColor(summary?.total_realized ?? null) },
          { label: "Unrealized",      value: fmtDollar(summary?.total_unrealized ?? null), color: plColor(summary?.total_unrealized ?? null) },
          { label: "Win Rate",        value: summary?.win_rate ?? "—", sub: summary ? `${summary.wins}W / ${summary.losses}L` : null },
          { label: "Open Positions",  value: String(summary?.open_positions ?? "—") },
        ].map(m => (
          <div key={m.label} className="tfe-panel" style={{ padding: "14px 16px", textAlign: "center" }}>
            <div style={{ fontSize: "0.72rem", color: "#6b7280", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{m.label}</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: m.color ?? "#111" }}>{m.value}</div>
            {m.sub && <div style={{ fontSize: "0.72rem", color: m.color ?? "#6b7280", marginTop: 2 }}>{m.sub}</div>}
          </div>
        ))}
      </div>

      {/* Alpaca account equity row (if available) */}
      {(summary?.alpaca_equity ?? null) !== null && (
        <div style={{ fontSize: "0.78rem", color: "#6b7280", textAlign: "right", marginTop: -8 }}>
          Alpaca account: equity {fmtDollar(summary?.alpaca_equity ?? null)} · cash {fmtDollar(summary?.alpaca_cash ?? null)}
        </div>
      )}

      {/* ── Positions Table ──────────────────────────────────────────────────── */}
      <div className="tfe-panel" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700 }}>Open Positions</h3>
          <span style={{ background: "#e5e7eb", borderRadius: 10, padding: "2px 8px", fontSize: "0.72rem", fontWeight: 600 }}>{positions.length}</span>
        </div>
        {positions.length === 0 ? (
          <div style={{ padding: "24px 20px", color: "#9ca3af", fontSize: "0.88rem" }}>
            No open positions. {autoOn ? "TFE will open positions on the next daily run when 3WA signals appear." : "Auto-TFE is off — enable it to start trading."}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tfe-table">
              <caption style={{position:"absolute",width:"1px",height:"1px",padding:0,margin:"-1px",overflow:"hidden",clip:"rect(0,0,0,0)",whiteSpace:"nowrap",border:0}}>PEE-1 Open Positions</caption>
              <thead>
                <tr style={{ background: "rgba(0,0,0,0.03)", textAlign: "left" }}>
                  {(["Ticker", "Signal", "Shares", "Entry", "Current", "Unreal. P&L", "P&L %", "Status", "Detected"]).map(h => {
                    const isNumeric = h === "Shares" || h === "Entry" || h === "Current" || h === "Unreal. P&L" || h === "P&L %";
                    return (
                      <th
                        key={h}
                        scope="col"
                        style={{
                          whiteSpace: "nowrap",
                          textAlign: isNumeric ? "right" : "left",
                        }}
                      >{h}</th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={pos.id} style={{ borderTop: "1px solid rgba(0,0,0,0.05)", background: i % 2 === 0 ? "transparent" : "rgba(0,0,0,0.015)" }}>
                    <td style={{ fontWeight: 700, fontFamily: "var(--font-geist-mono, monospace)", textAlign: "left" }}>{pos.ticker}</td>
                    <td style={{ textAlign: "left" }}>{signalBadge(pos.signal_class)}</td>
                    <td style={{ textAlign: "right" }}>{pos.shares.toLocaleString()}</td>
                    <td style={{ textAlign: "right" }}>{fmtDollar(pos.entry_price)}</td>
                    <td style={{ textAlign: "right" }}>{fmtDollar(pos.current_price)}</td>
                    <td style={{ fontWeight: 600, color: plColor(pos.unrealized_pl), textAlign: "right" }}>{fmtDollar(pos.unrealized_pl)}</td>
                    <td style={{ color: plColor(pos.unrealized_pl_pct), textAlign: "right" }}>
                      {pos.unrealized_pl_pct !== null ? `${pos.unrealized_pl_pct >= 0 ? "+" : ""}${fmt(pos.unrealized_pl_pct)}%` : "—"}
                    </td>
                    <td>
                      <span style={{ fontSize: "0.72rem", background: pos.status === "filled" ? "rgba(22,163,74,0.12)" : "rgba(37,99,235,0.1)", color: pos.status === "filled" ? "#15803d" : "#1d4ed8", borderRadius: 4, padding: "2px 6px", fontWeight: 600 }}>
                        {pos.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: "#6b7280" }}>
                      {new Date(pos.signal_detected_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Exit Reasons (if any closed trades) ─────────────────────────────── */}
      {summary && Object.keys(summary.exit_reasons).length > 0 && (
        <div className="tfe-panel" style={{ padding: "14px 20px" }}>
          <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", fontWeight: 700 }}>Exit Breakdown ({summary.closed_trades} closed trades)</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(summary.exit_reasons).map(([reason, count]) => (
              <div key={reason} style={{ background: "rgba(0,0,0,0.04)", borderRadius: 6, padding: "4px 12px", fontSize: "0.8rem" }}>
                <span style={{ fontWeight: 600 }}>{reason.replace(/_/g, " ")}</span>
                <span style={{ color: "#6b7280", marginLeft: 6 }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Manual Order ────────────────────────────────────────────────────── */}
      <div className="tfe-panel" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700 }}>Place Manual Order</h3>
          <span style={{ background: "#64748b", color: "#fff", borderRadius: 4, padding: "1px 7px", fontSize: "0.72rem", fontWeight: 700 }}>MANUAL</span>
          <span style={{ fontSize: "0.75rem", color: "#9ca3af", marginLeft: 4 }}>Sent directly to Alpaca · not managed by TFE engine</span>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>

          {/* Buy / Sell toggle */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Side</label>
            <div style={{ display: "flex", borderRadius: 6, overflow: "hidden", border: "1px solid rgba(0,0,0,0.15)" }}>
              <button
                onClick={() => setOrderSide("buy")}
                style={{
                  padding: "6px 16px",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  background: orderSide === "buy" ? "#16a34a" : "#f3f4f6",
                  color: orderSide === "buy" ? "#fff" : "#6b7280",
                  transition: "background 0.15s",
                }}
              >BUY</button>
              <button
                onClick={() => setOrderSide("sell")}
                style={{
                  padding: "6px 16px",
                  border: "none",
                  borderLeft: "1px solid rgba(0,0,0,0.1)",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  background: orderSide === "sell" ? "#ef4444" : "#f3f4f6",
                  color: orderSide === "sell" ? "#fff" : "#6b7280",
                  transition: "background 0.15s",
                }}
              >SELL</button>
            </div>
          </div>

          {/* Ticker */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Ticker</label>
            <input
              value={orderTicker}
              onChange={e => setOrderTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
              style={{ width: 90, padding: "6px 10px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.9rem", fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
            />
          </div>

          {/* Shares */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Shares</label>
            <input
              type="number"
              value={orderShares}
              onChange={e => setOrderShares(e.target.value)}
              placeholder="10"
              min={0.0001}
              step={1}
              style={{ width: 90, padding: "6px 10px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.9rem" }}
            />
          </div>

          {/* Order type toggle */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Type</label>
            <div style={{ display: "flex", borderRadius: 6, overflow: "hidden", border: "1px solid rgba(0,0,0,0.15)" }}>
              <button
                onClick={() => setOrderType("market")}
                style={{
                  padding: "6px 12px",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.82rem",
                  background: orderType === "market" ? "#2563eb" : "#f3f4f6",
                  color: orderType === "market" ? "#fff" : "#6b7280",
                  transition: "background 0.15s",
                }}
              >Market</button>
              <button
                onClick={() => setOrderType("limit")}
                style={{
                  padding: "6px 12px",
                  border: "none",
                  borderLeft: "1px solid rgba(0,0,0,0.1)",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.82rem",
                  background: orderType === "limit" ? "#2563eb" : "#f3f4f6",
                  color: orderType === "limit" ? "#fff" : "#6b7280",
                  transition: "background 0.15s",
                }}
              >Limit</button>
            </div>
          </div>

          {/* Limit price (shown only for limit orders) */}
          {orderType === "limit" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Limit Price ($)</label>
              <input
                type="number"
                value={orderLimitPrice}
                onChange={e => setOrderLimitPrice(e.target.value)}
                placeholder="150.00"
                min={0.01}
                step={0.01}
                style={{ width: 110, padding: "6px 10px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.9rem" }}
              />
            </div>
          )}

          {/* Notes */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 140 }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>Notes (optional)</label>
            <input
              value={orderNotes}
              onChange={e => setOrderNotes(e.target.value)}
              placeholder="Optional notes"
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid rgba(0,0,0,0.15)", fontSize: "0.88rem" }}
            />
          </div>

          {/* Submit */}
          <button
            onClick={placeManualOrder}
            disabled={placingOrder}
            style={{
              padding: "7px 20px",
              borderRadius: 6,
              border: "none",
              cursor: placingOrder ? "not-allowed" : "pointer",
              background: orderSide === "sell" ? "#ef4444" : "#16a34a",
              color: "#fff",
              fontWeight: 700,
              fontSize: "0.85rem",
              opacity: placingOrder ? 0.6 : 1,
              height: 36,
              whiteSpace: "nowrap",
            }}
          >
            {placingOrder ? "Placing..." : `Place ${orderSide === "sell" ? "Sell" : "Buy"} Order`}
          </button>
        </div>

        {orderMsg && (
          <p style={{ margin: "10px 0 0", fontSize: "0.82rem", color: orderMsg.ok ? "#16a34a" : "#ef4444" }}>{orderMsg.text}</p>
        )}
      </div>

    </div>
  );
}
