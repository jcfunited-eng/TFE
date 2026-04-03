"use client";

import React, { useState, useEffect, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────
interface LedgerRow {
  id: number;
  ticker: string;
  run_id: string | null;
  signal_class: string | null;
  status: string;
  exit_reason: string | null;
  spy_dk: number | null;
  s_uf: number | null;
  bar_count: number | null;
  f_n: number | null;
  signal_detected_at: string | null;
  entry_filled_at: string | null;
  exit_filled_at: string | null;
  entry_limit_price: string | null;
  entry_filled_price: string | null;
  take_profit_price: string | null;
  stop_loss_price: string | null;
  exit_filled_price: string | null;
  shares: number | null;
  dollar_allocation: string | null;
  p_l: string | null;
  p_l_pct: string | null;
  atr_14: string | null;
  vault_equity_at_signal: string | null;
  alpaca_order_id: string | null;
  rationale_json: Record<string, unknown> | null;
  created_at: string;
}

interface StealthRow {
  id: number;
  parent_ledger_id: number | null;
  ticker: string;
  agent_index: number;
  total_agents: number;
  shares: number;
  order_type: string;
  scheduled_at: string;
  executed_at: string | null;
  status: string;
  alpaca_order_id: string | null;
  ledger_id: number | null;
  error: string | null;
}

interface CircuitBreakerRow {
  id: number;
  trigger_reason: string;
  triggered_at: string;
  expires_at: string;
  drawdown_pct: string | null;
  threshold_pct: string | null;
  cleared_at: string | null;
}

interface AuditSummary {
  total: number;
  open: number;
  closed: number;
  rejected: number;
  wins: number;
  losses: number;
  total_pl: number;
  win_rate: string;
  exit_reasons: Record<string, number>;
  by_signal_class: Record<string, number>;
}

interface AuditData {
  rows: LedgerRow[];
  totalRows: number;
  limit: number;
  offset: number;
  stealth: StealthRow[];
  circuitBreaker: CircuitBreakerRow[];
  summary: AuditSummary;
}

// ── Helpers ───────────────────────────────────────────────────────────────
function fmt(v: string | number | null | undefined, decimals = 2): string {
  const n = parseFloat(String(v ?? ""));
  return isFinite(n) ? n.toFixed(decimals) : "—";
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  const d = new Date(s);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString("en-US", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function statusColor(status: string): string {
  if (status === "closed")   return "text-gray-400";
  if (status === "submitted" || status === "filled") return "text-sky-400";
  if (status === "rejected") return "text-red-400";
  if (status === "pending")  return "text-yellow-400";
  return "text-gray-400";
}

function plColor(pl: string | null): string {
  const n = parseFloat(pl ?? "");
  if (!isFinite(n)) return "text-gray-500";
  return n > 0 ? "text-green-400" : n < 0 ? "text-red-400" : "text-gray-400";
}

function signalBadge(cls: string | null): string {
  if (cls === "3WA")    return "bg-purple-900 text-purple-200 border border-purple-700";
  if (cls === "W1")     return "bg-green-900 text-green-200 border border-green-700";
  if (cls === "manual") return "bg-gray-700 text-gray-300 border border-gray-600";
  return "bg-gray-800 text-gray-400 border border-gray-700";
}

// ── CSV export ────────────────────────────────────────────────────────────
function exportCSV(rows: LedgerRow[]) {
  const headers = [
    "id","ticker","signal_class","status","exit_reason",
    "spy_dk","s_uf","bar_count","f_n",
    "signal_detected_at","entry_filled_at","exit_filled_at",
    "entry_filled_price","exit_filled_price","shares","dollar_allocation",
    "p_l","p_l_pct","atr_14","vault_equity_at_signal","alpaca_order_id",
  ];
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [
    headers.join(","),
    ...rows.map(r =>
      headers.map(h => esc((r as unknown as Record<string, unknown>)[h])).join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = `pee1_audit_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

// ── Main component ────────────────────────────────────────────────────────
export default function AuditorReport() {
  const [data,    setData]    = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  // Filter state
  const [statusFilter, setStatusFilter] = useState("all");
  const [tickerFilter, setTickerFilter] = useState("");
  const [activeTab,    setActiveTab]    = useState<"trades"|"stealth"|"cb">("trades");

  // Expanded row details
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ status: statusFilter, limit: "200" });
      if (tickerFilter) params.set("ticker", tickerFilter.toUpperCase());
      const res = await fetch(`/api/admin/auditor?${params.toString()}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, tickerFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const { summary, rows, stealth, circuitBreaker } = data ?? {};

  return (
    <div className="space-y-6 font-mono text-xs">

      {/* ── Header + controls ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-base font-semibold text-white mr-2">PEE-1 Trade Auditor</h2>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1 text-xs"
        >
          {["all","open","closed","rejected"].map(s => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>

        {/* Ticker filter */}
        <input
          type="text"
          placeholder="Ticker…"
          value={tickerFilter}
          onChange={e => setTickerFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1 text-xs w-24 uppercase"
        />

        <button
          onClick={fetchData}
          className="bg-gray-700 hover:bg-gray-600 text-gray-200 rounded px-3 py-1 text-xs"
        >
          Refresh
        </button>

        {rows && rows.length > 0 && (
          <button
            onClick={() => exportCSV(rows)}
            className="bg-sky-900 hover:bg-sky-800 text-sky-200 border border-sky-700 rounded px-3 py-1 text-xs ml-auto"
          >
            Export CSV
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 rounded p-3">
          {error}
        </div>
      )}

      {/* ── Summary bar ────────────────────────────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
          {[
            { label: "Total",    value: summary.total },
            { label: "Open",     value: summary.open },
            { label: "Closed",   value: summary.closed },
            { label: "Rejected", value: summary.rejected },
            { label: "Wins",     value: summary.wins },
            { label: "Losses",   value: summary.losses },
            { label: "Win Rate", value: summary.win_rate },
            { label: "P&L",      value: `$${summary.total_pl.toFixed(2)}`, color: summary.total_pl >= 0 ? "text-green-400" : "text-red-400" },
          ].map(card => (
            <div key={card.label} className="bg-gray-800 border border-gray-700 rounded p-2 text-center">
              <div className={`text-sm font-bold ${card.color ?? "text-white"}`}>{card.value}</div>
              <div className="text-gray-500 text-[10px] mt-0.5">{card.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 border-b border-gray-700">
        {(["trades","stealth","cb"] as const).map(tab => {
          const labels = { trades: `Trades (${data?.totalRows ?? 0})`, stealth: `Stealth Queue (${stealth?.length ?? 0})`, cb: `Circuit Breaker (${circuitBreaker?.length ?? 0})` };
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 text-xs border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {labels[tab]}
            </button>
          );
        })}
      </div>

      {loading && (
        <div className="text-gray-500 text-center py-8">Loading…</div>
      )}

      {/* ── Trade ledger table ───────────────────────────────────────────── */}
      {!loading && activeTab === "trades" && rows && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-gray-500 text-[10px] border-b border-gray-700">
                <th className="pr-3 py-1">Ticker</th>
                <th className="pr-3 py-1">Class</th>
                <th className="pr-3 py-1">Status</th>
                <th className="pr-3 py-1">Signal At</th>
                <th className="pr-3 py-1">Shares</th>
                <th className="pr-3 py-1">Entry$</th>
                <th className="pr-3 py-1">TP$</th>
                <th className="pr-3 py-1">SL$</th>
                <th className="pr-3 py-1">Fill$</th>
                <th className="pr-3 py-1">Exit$</th>
                <th className="pr-3 py-1">P&L</th>
                <th className="pr-3 py-1">ATR</th>
                <th className="pr-3 py-1">s_uf</th>
                <th className="pr-3 py-1">bar</th>
                <th className="pr-3 py-1">f_n</th>
                <th className="pr-3 py-1">Exit Reason</th>
                <th className="py-1">Order ID</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={17} className="text-center text-gray-600 py-8">No rows</td></tr>
              )}
              {rows.map(row => (
                <React.Fragment key={row.id}>
                  <tr
                    className="border-b border-gray-800 hover:bg-gray-800/40 cursor-pointer"
                    onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}
                  >
                    <td className="pr-3 py-1 font-bold text-white">{row.ticker}</td>
                    <td className="pr-3 py-1">
                      <span className={`rounded px-1 py-0.5 text-[10px] ${signalBadge(row.signal_class)}`}>
                        {row.signal_class ?? "—"}
                      </span>
                    </td>
                    <td className={`pr-3 py-1 ${statusColor(row.status)}`}>{row.status}</td>
                    <td className="pr-3 py-1 text-gray-400">{fmtDate(row.signal_detected_at)}</td>
                    <td className="pr-3 py-1 text-gray-300">{row.shares ?? "—"}</td>
                    <td className="pr-3 py-1 text-gray-300">{fmt(row.entry_limit_price)}</td>
                    <td className="pr-3 py-1 text-green-600">{fmt(row.take_profit_price)}</td>
                    <td className="pr-3 py-1 text-red-600">{fmt(row.stop_loss_price)}</td>
                    <td className="pr-3 py-1 text-sky-300">{fmt(row.entry_filled_price)}</td>
                    <td className="pr-3 py-1 text-sky-300">{fmt(row.exit_filled_price)}</td>
                    <td className={`pr-3 py-1 font-semibold ${plColor(row.p_l)}`}>
                      {row.p_l ? `$${fmt(row.p_l)}` : "—"}
                    </td>
                    <td className="pr-3 py-1 text-gray-500">{fmt(row.atr_14, 4)}</td>
                    <td className="pr-3 py-1 text-gray-400">{fmt(row.s_uf, 3)}</td>
                    <td className="pr-3 py-1 text-gray-400">{row.bar_count ?? "—"}</td>
                    <td className="pr-3 py-1 text-gray-400">{fmt(row.f_n, 3)}</td>
                    <td className="pr-3 py-1 text-gray-500 max-w-[120px] truncate">{row.exit_reason ?? "—"}</td>
                    <td className="py-1 text-gray-600 text-[9px] max-w-[80px] truncate">{row.alpaca_order_id ?? "—"}</td>
                  </tr>

                  {/* Expanded detail row — signal provenance + rationale */}
                  {expandedId === row.id && (
                    <tr className="bg-gray-900/60 border-b border-gray-700">
                      <td colSpan={17} className="py-3 px-4">
                        <div className="grid grid-cols-2 gap-4 text-[10px]">
                          <div>
                            <div className="text-gray-500 font-semibold mb-1">Signal Provenance</div>
                            <div className="space-y-0.5 text-gray-400">
                              <div>run_id: <span className="text-gray-300">{row.run_id ?? "—"}</span></div>
                              <div>signal_detected_at: <span className="text-gray-300">{fmtDate(row.signal_detected_at)}</span></div>
                              <div>entry_filled_at: <span className="text-gray-300">{fmtDate(row.entry_filled_at)}</span></div>
                              <div>exit_filled_at: <span className="text-gray-300">{fmtDate(row.exit_filled_at)}</span></div>
                              <div>vault_equity_at_signal: <span className="text-gray-300">${fmt(row.vault_equity_at_signal)}</span></div>
                              <div>dollar_allocation: <span className="text-gray-300">${fmt(row.dollar_allocation)}</span></div>
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500 font-semibold mb-1">Rationale JSON</div>
                            <pre className="text-[9px] text-gray-400 whitespace-pre-wrap break-all max-h-32 overflow-y-auto bg-gray-950 rounded p-2">
                              {JSON.stringify(row.rationale_json, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Stealth queue table ───────────────────────────────────────────── */}
      {!loading && activeTab === "stealth" && stealth && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-gray-500 text-[10px] border-b border-gray-700">
                <th className="pr-3 py-1">QID</th>
                <th className="pr-3 py-1">Ticker</th>
                <th className="pr-3 py-1">Agent</th>
                <th className="pr-3 py-1">Type</th>
                <th className="pr-3 py-1">Shares</th>
                <th className="pr-3 py-1">Entry$</th>
                <th className="pr-3 py-1">Status</th>
                <th className="pr-3 py-1">Scheduled</th>
                <th className="pr-3 py-1">Executed</th>
                <th className="pr-3 py-1">Alpaca ID</th>
                <th className="py-1">Error</th>
              </tr>
            </thead>
            <tbody>
              {stealth.length === 0 && (
                <tr><td colSpan={11} className="text-center text-gray-600 py-8">No stealth queue rows</td></tr>
              )}
              {stealth.map(row => (
                <tr key={row.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="pr-3 py-1 text-gray-500">{row.id}</td>
                  <td className="pr-3 py-1 font-bold text-white">{row.ticker}</td>
                  <td className="pr-3 py-1 text-gray-400">{row.agent_index}/{row.total_agents - 1}</td>
                  <td className="pr-3 py-1">
                    <span className={`rounded px-1 py-0.5 text-[10px] ${row.order_type === "midpoint" ? "bg-amber-900 text-amber-200 border border-amber-700" : "bg-sky-900 text-sky-200 border border-sky-700"}`}>
                      {row.order_type}
                    </span>
                  </td>
                  <td className="pr-3 py-1 text-gray-300">{row.shares}</td>
                  <td className="pr-3 py-1 text-gray-300">{fmt(row.entry_limit_price)}</td>
                  <td className={`pr-3 py-1 ${statusColor(row.status)}`}>{row.status}</td>
                  <td className="pr-3 py-1 text-gray-400">{fmtDate(row.scheduled_at)}</td>
                  <td className="pr-3 py-1 text-gray-400">{fmtDate(row.executed_at)}</td>
                  <td className="pr-3 py-1 text-gray-600 text-[9px]">{row.alpaca_order_id ?? "—"}</td>
                  <td className="py-1 text-red-400 text-[9px] max-w-[160px] truncate">{row.error ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Circuit breaker log ──────────────────────────────────────────── */}
      {!loading && activeTab === "cb" && circuitBreaker && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-gray-500 text-[10px] border-b border-gray-700">
                <th className="pr-3 py-1">ID</th>
                <th className="pr-3 py-1">Reason</th>
                <th className="pr-3 py-1">Triggered</th>
                <th className="pr-3 py-1">Expires</th>
                <th className="pr-3 py-1">Drawdown%</th>
                <th className="pr-3 py-1">Threshold%</th>
                <th className="py-1">Cleared</th>
              </tr>
            </thead>
            <tbody>
              {circuitBreaker.length === 0 && (
                <tr><td colSpan={7} className="text-center text-gray-600 py-8">No circuit breaker events</td></tr>
              )}
              {circuitBreaker.map(row => {
                const isActive = !row.cleared_at && new Date(row.expires_at) > new Date();
                return (
                  <tr key={row.id} className={`border-b border-gray-800 ${isActive ? "bg-red-950/30" : ""}`}>
                    <td className="pr-3 py-1 text-gray-500">{row.id}</td>
                    <td className="pr-3 py-1 text-red-300">{row.trigger_reason}</td>
                    <td className="pr-3 py-1 text-gray-400">{fmtDate(row.triggered_at)}</td>
                    <td className={`pr-3 py-1 ${isActive ? "text-red-400 font-semibold" : "text-gray-500"}`}>{fmtDate(row.expires_at)}</td>
                    <td className="pr-3 py-1 text-red-300">{fmt(row.drawdown_pct, 2)}%</td>
                    <td className="pr-3 py-1 text-gray-400">{fmt(row.threshold_pct, 2)}%</td>
                    <td className="py-1 text-green-500">{row.cleared_at ? fmtDate(row.cleared_at) : isActive ? "ACTIVE" : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Exit breakdown + class breakdown ────────────────────────────── */}
      {!loading && summary && activeTab === "trades" && (
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <div className="text-gray-500 text-[10px] font-semibold mb-1">Exit Reasons</div>
            <div className="space-y-0.5">
              {Object.entries(summary.exit_reasons).map(([reason, count]) => (
                <div key={reason} className="flex justify-between text-[10px]">
                  <span className="text-gray-400">{reason}</span>
                  <span className="text-gray-300">{count}</span>
                </div>
              ))}
              {Object.keys(summary.exit_reasons).length === 0 && (
                <div className="text-gray-600 text-[10px]">—</div>
              )}
            </div>
          </div>
          <div>
            <div className="text-gray-500 text-[10px] font-semibold mb-1">By Signal Class</div>
            <div className="space-y-0.5">
              {Object.entries(summary.by_signal_class).map(([cls, count]) => (
                <div key={cls} className="flex justify-between text-[10px]">
                  <span className={`rounded px-1 text-[10px] ${signalBadge(cls)}`}>{cls}</span>
                  <span className="text-gray-300">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
