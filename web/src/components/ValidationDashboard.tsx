"use client";

import { useEffect, useState, useCallback } from "react";
import styles from "./AdminConsoleClient.module.css";

type DashboardData = {
  generated_at_utc: string;
  validation_start: string;
  validation_day: number;
  milestones: {
    day_10_kinetic_buffer: { target_date: string; days_remaining: number };
    day_30_win_rate: { target_date: string; days_remaining: number };
    day_60_validation_complete: { target_date: string; days_remaining: number };
  };
  structural_state: {
    spy_dk: number | null;
    spy_s_uf: number | null;
    spy_regime: string;
    total_accumulate: number;
    decision_distribution: { label: string; count: number }[];
  };
  portfolio: {
    open_positions: { signal_class: string; status: string; count: number; invested: number }[];
    total_open: number;
    execution_mode: string;
    auto_tfe: string;
    risk_per_trade: string;
  };
  expectancy: {
    value: number;
    target: number;
    threshold: number;
    status: string;
    closed_trades: number;
    win_rate: number | null;
    avg_win_pct: number;
    avg_loss_pct: number;
    total_realized_pl: number;
    wins: number;
    losses: number;
  };
  exits: { reason: string; count: number; total_pl: number; avg_pl_pct: number }[];
  signals_today: { signal_class: string; status: string; count: number }[];
  positions: {
    ticker: string;
    signal_class: string;
    status: string;
    shares: number | null;
    entry: number | null;
    exit: number | null;
    p_l: number | null;
    p_l_pct: number | null;
    exit_reason: string | null;
    created_at: string;
    exit_at: string | null;
  }[];
  refresh_history: {
    run_id: string;
    trigger: string;
    status: string;
    started: string;
    completed: string;
    duration_seconds: number;
    rows: number | null;
  }[];
  circuit_breaker_events: unknown[];
  fundamentals: {
    total_accumulate: number;
    with_complete_data: number;
    coverage_pct: number | null;
  };
};

function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(decimals)}%`;
}

function fmtDollar(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const sign = v >= 0 ? "" : "-";
  return `${sign}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function ExpectancyBar({ value, target, threshold }: { value: number; target: number; threshold: number }) {
  const maxDisplay = Math.max(target * 1.5, 0.08);
  const barWidth = Math.min(Math.max(value / maxDisplay, 0), 1) * 100;
  const thresholdPos = (threshold / maxDisplay) * 100;
  const targetPos = (target / maxDisplay) * 100;
  const color = value >= target ? "#2d8" : value >= threshold ? "#da2" : value > 0 ? "#d82" : "#d44";

  return (
    <div style={{ position: "relative", height: "24px", background: "#1a1a2e", borderRadius: "4px", overflow: "hidden", marginTop: "8px" }}>
      <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${barWidth}%`, background: color, borderRadius: "4px", transition: "width 0.5s" }} />
      <div style={{ position: "absolute", left: `${thresholdPos}%`, top: 0, height: "100%", width: "2px", background: "#888", zIndex: 2 }} />
      <div style={{ position: "absolute", left: `${targetPos}%`, top: 0, height: "100%", width: "2px", background: "#fff", zIndex: 2 }} />
      <div style={{ position: "absolute", top: "2px", right: "6px", fontSize: "11px", color: "#ccc", zIndex: 3 }}>
        E = {value >= 0 ? "+" : ""}{(value * 100).toFixed(3)}%
      </div>
    </div>
  );
}

export default function ValidationDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/validation-dashboard");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <p className={styles.inlineMsg}>Loading validation data...</p>;
  if (error) return <p className={styles.inlineMsg} style={{ color: "#f44" }}>Error: {error}</p>;
  if (!data) return <p className={styles.inlineMsg}>No data available.</p>;

  const closedPositions = data.positions.filter(p => p.status === "closed" && p.p_l !== null);
  const openPositions = data.positions.filter(p => p.status === "filled" || p.status === "submitted");

  return (
    <div className={styles.deck} style={{ gap: "1.5rem", display: "flex", flexDirection: "column" }}>

      {/* ── Validation Progress ────────────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Validation Progress</strong>
          <span style={{ fontSize: "12px", color: "#888" }}>
            Updated: {fmtTime(data.generated_at_utc)}
          </span>
        </div>
        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Validation Day</div>
            <div className={styles.metricValue}>{data.validation_day}</div>
            <div className={styles.metricSub}>of 60</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Day 10 (Kinetic Buffer)</div>
            <div className={styles.metricValue}>{data.milestones.day_10_kinetic_buffer.days_remaining}d</div>
            <div className={styles.metricSub}>{data.milestones.day_10_kinetic_buffer.target_date}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Day 30 (Win Rate)</div>
            <div className={styles.metricValue}>{data.milestones.day_30_win_rate.days_remaining}d</div>
            <div className={styles.metricSub}>{data.milestones.day_30_win_rate.target_date}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Day 60 (Complete)</div>
            <div className={styles.metricValue}>{data.milestones.day_60_validation_complete.days_remaining}d</div>
            <div className={styles.metricSub}>{data.milestones.day_60_validation_complete.target_date}</div>
          </div>
        </div>
        <button className={styles.ghostButton} onClick={fetchData} style={{ marginTop: "8px" }}>
          Refresh Dashboard
        </button>
      </div>

      {/* ── Mathematical Expectancy ───────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Mathematical Expectancy (E)</strong>
          <span style={{ fontSize: "12px", color: "#888" }}>
            E = (W &times; AvgW) &minus; (L &times; AvgL)
          </span>
        </div>
        {data.expectancy.closed_trades < 10 ? (
          <div className={styles.notice + " " + styles.noticeInfo}>
            Insufficient closed trades for expectancy calculation ({data.expectancy.closed_trades}/10 minimum).
            Expectancy will populate as positions close.
          </div>
        ) : (
          <>
            <ExpectancyBar
              value={data.expectancy.value}
              target={data.expectancy.target}
              threshold={data.expectancy.threshold}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#888", marginTop: "4px" }}>
              <span>0</span>
              <span style={{ color: "#888" }}>Threshold: +{(data.expectancy.threshold * 100).toFixed(1)}%</span>
              <span style={{ color: "#fff" }}>Target: +{(data.expectancy.target * 100).toFixed(1)}%</span>
            </div>
          </>
        )}
        <div className={styles.metrics} style={{ marginTop: "12px" }}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Win Rate</div>
            <div className={styles.metricValue}>{data.expectancy.win_rate !== null ? `${data.expectancy.win_rate}%` : "—"}</div>
            <div className={styles.metricSub}>{data.expectancy.wins}W / {data.expectancy.losses}L</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Avg Win</div>
            <div className={styles.metricValue} style={{ color: "#2d8" }}>{fmtPct(data.expectancy.avg_win_pct)}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Avg Loss</div>
            <div className={styles.metricValue} style={{ color: "#d44" }}>{fmtPct(-data.expectancy.avg_loss_pct)}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Realized P&L</div>
            <div className={styles.metricValue} style={{ color: data.expectancy.total_realized_pl >= 0 ? "#2d8" : "#d44" }}>
              {fmtDollar(data.expectancy.total_realized_pl)}
            </div>
            <div className={styles.metricSub}>{data.expectancy.closed_trades} closed trades</div>
          </div>
        </div>
      </div>

      {/* ── Structural State ──────────────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>DSF-AI Structural State</strong>
        </div>
        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>SPY D_k</div>
            <div className={styles.metricValue} style={{
              color: data.structural_state.spy_dk === 1 ? "#2d8" : data.structural_state.spy_dk === -1 ? "#d44" : "#da2"
            }}>
              {data.structural_state.spy_dk ?? "—"}
            </div>
            <div className={styles.metricSub}>
              {data.structural_state.spy_dk === 1 ? "Wave 3 ACTIVE" : data.structural_state.spy_dk === -1 ? "Wave 3 INACTIVE" : "Stillness"}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>SPY S_UF</div>
            <div className={styles.metricValue}>{data.structural_state.spy_s_uf ?? "—"}</div>
            <div className={styles.metricSub}>{data.structural_state.spy_regime}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Total Accumulate</div>
            <div className={styles.metricValue}>{data.structural_state.total_accumulate}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Decision Distribution</div>
            <div style={{ fontSize: "12px" }}>
              {data.structural_state.decision_distribution.map(d => (
                <div key={d.label}>{d.label}: {d.count.toLocaleString()}</div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Portfolio Summary ─────────────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Portfolio Performance</strong>
        </div>
        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Open Positions</div>
            <div className={styles.metricValue}>{data.portfolio.total_open}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Mode</div>
            <div className={styles.metricValue}>{data.portfolio.execution_mode.toUpperCase()}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Auto-TFE</div>
            <div className={styles.metricValue} style={{ color: data.portfolio.auto_tfe === "true" ? "#2d8" : "#d44" }}>
              {data.portfolio.auto_tfe === "true" ? "ON" : "OFF"}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Risk/Trade</div>
            <div className={styles.metricValue}>{data.portfolio.risk_per_trade}%</div>
          </div>
        </div>
      </div>

      {/* ── Exit Analysis ─────────────────────────────────────── */}
      {data.exits.length > 0 && (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <strong>Exit Breakdown</strong>
          </div>
          <div className={styles.scrollWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Exit Reason</th>
                  <th>Count</th>
                  <th>Total P&L</th>
                  <th>Avg P&L %</th>
                </tr>
              </thead>
              <tbody>
                {data.exits.map(e => (
                  <tr key={e.reason}>
                    <td>{e.reason}</td>
                    <td>{e.count}</td>
                    <td style={{ color: e.total_pl >= 0 ? "#2d8" : "#d44" }}>{fmtDollar(e.total_pl)}</td>
                    <td style={{ color: e.avg_pl_pct >= 0 ? "#2d8" : "#d44" }}>{fmtPct(e.avg_pl_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Today's Signal Activity ───────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Today&apos;s Signal Activity</strong>
        </div>
        {data.signals_today.length === 0 ? (
          <p className={styles.inlineMsg}>No signals generated today.</p>
        ) : (
          <div className={styles.scrollWrap}>
            <table className={styles.table}>
              <thead>
                <tr><th>Signal Class</th><th>Status</th><th>Count</th></tr>
              </thead>
              <tbody>
                {data.signals_today.map((s, i) => (
                  <tr key={i}><td>{s.signal_class}</td><td>{s.status}</td><td>{s.count}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Closed Trades ─────────────────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Closed Trades</strong>
          <span style={{ fontSize: "12px", color: "#888" }}>{closedPositions.length} total</span>
        </div>
        {closedPositions.length === 0 ? (
          <div className={styles.notice + " " + styles.noticeInfo}>
            No positions have been closed yet. Expectancy, win rate, and realized P&L will populate as the sentinel triggers exits.
          </div>
        ) : (
          <div className={styles.scrollWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Ticker</th><th>Signal</th><th>Entry</th><th>Exit</th>
                  <th>P&L</th><th>P&L %</th><th>Exit Reason</th><th>Closed</th>
                </tr>
              </thead>
              <tbody>
                {closedPositions.map((p, i) => (
                  <tr key={i}>
                    <td>{p.ticker}</td>
                    <td>{p.signal_class}</td>
                    <td>{p.entry ? `$${p.entry.toFixed(2)}` : "—"}</td>
                    <td>{p.exit ? `$${p.exit.toFixed(2)}` : "—"}</td>
                    <td style={{ color: (p.p_l ?? 0) >= 0 ? "#2d8" : "#d44" }}>{fmtDollar(p.p_l)}</td>
                    <td style={{ color: (p.p_l_pct ?? 0) >= 0 ? "#2d8" : "#d44" }}>{fmtPct(p.p_l_pct)}</td>
                    <td>{p.exit_reason ?? "—"}</td>
                    <td>{fmtDate(p.exit_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Infrastructure Health ─────────────────────────────── */}
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <strong>Infrastructure Health</strong>
        </div>
        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Fundamentals Coverage</div>
            <div className={styles.metricValue}>{data.fundamentals.coverage_pct ?? 0}%</div>
            <div className={styles.metricSub}>{data.fundamentals.with_complete_data} / {data.fundamentals.total_accumulate}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Circuit Breaker</div>
            <div className={styles.metricValue} style={{ color: data.circuit_breaker_events.length > 0 ? "#d44" : "#2d8" }}>
              {data.circuit_breaker_events.length > 0 ? "TRIGGERED" : "Clear"}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Recent Refreshes</div>
            <div className={styles.metricValue}>{data.refresh_history.length}</div>
            <div className={styles.metricSub}>since validation start</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Latest Refresh</div>
            <div className={styles.metricValue}>
              {data.refresh_history.length > 0
                ? `${Math.round(data.refresh_history[0].duration_seconds / 60)}m`
                : "—"}
            </div>
            <div className={styles.metricSub}>
              {data.refresh_history.length > 0 ? data.refresh_history[0].trigger : "—"}
            </div>
          </div>
        </div>

        {/* Refresh history table */}
        {data.refresh_history.length > 0 && (
          <div className={styles.scrollWrap} style={{ marginTop: "12px" }}>
            <table className={styles.table}>
              <thead>
                <tr><th>Date</th><th>Trigger</th><th>Duration</th><th>Rows</th><th>Status</th></tr>
              </thead>
              <tbody>
                {data.refresh_history.slice(0, 10).map((r, i) => (
                  <tr key={i}>
                    <td>{fmtTime(r.started)}</td>
                    <td>{r.trigger}</td>
                    <td>{Math.round(r.duration_seconds / 60)}m</td>
                    <td>{r.rows?.toLocaleString() ?? "—"}</td>
                    <td style={{ color: r.status === "ok" ? "#2d8" : "#d44" }}>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
