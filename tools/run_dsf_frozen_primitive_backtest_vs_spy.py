#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_repo_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


_load_repo_env(REPO_ROOT / ".env")

from risk import annualized_volatility, daily_returns, max_drawdown
from tfe_market_data_service import Bar, HistoryRequest, Timespan
from unified_market_data_service import get_unified_market_data


RUNTIME_ROOT = REPO_ROOT / "backups" / "runtime"
ARCHIVE_DB = RUNTIME_ROOT / "dsf_historical_full_surface_snapshot_archive_v2.sqlite"
PRIMITIVE_RUNNER = REPO_ROOT / "tools" / "run_dsf_full_field_sortable_v3_rationalized.py"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"

INITIAL_CAPITAL = 100_000.0
SLIPPAGE_BPS_PER_TRADE = 10.0
SLIPPAGE_RATE = SLIPPAGE_BPS_PER_TRADE / 10000.0


@dataclass(frozen=True)
class SnapshotDecisionRow:
    symbol: str
    asset_type: str
    snapshot_timestamp_utc: str
    S_UF: float
    R_UF: float
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float
    bar_count: int


@dataclass
class TradeRecord:
    signal_timestamp_utc: str
    execution_timestamp_utc: str
    symbol: str
    action: str
    shares_delta: float
    execution_open: float
    notional: float
    slippage_cost: float
    portfolio_equity_at_open: float
    decision_at_signal: str


def _load_primitive_module():
    spec = importlib.util.spec_from_file_location("frozen_primitive_module", PRIMITIVE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load primitive runner: {PRIMITIVE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRIMITIVE = _load_primitive_module()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _csv_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_archive_rows(db_path: Path) -> tuple[list[str], dict[str, list[SnapshotDecisionRow]]]:
    if not db_path.exists():
        raise RuntimeError(f"missing archive db: {db_path}")
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT snapshot_timestamp_utc, symbol, asset_type, S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, bar_count
        FROM snapshot_rows
        ORDER BY snapshot_timestamp_utc ASC, symbol ASC
        """
    ).fetchall()
    snapshot_rows: dict[str, list[SnapshotDecisionRow]] = {}
    for row in rows:
        snapshot_rows.setdefault(row[0], []).append(
            SnapshotDecisionRow(
                snapshot_timestamp_utc=str(row[0]),
                symbol=str(row[1]),
                asset_type=str(row[2]),
                S_UF=float(row[3]),
                R_UF=float(row[4]),
                D_k=float(row[5]),
                M_k=float(row[6]),
                R_rev_k=float(row[7]),
                U_star_k=float(row[8]),
                C_k=float(row[9]),
                P_k=float(row[10]),
                B_k=float(row[11]),
                bar_count=int(row[12]),
            )
        )
    timestamps = sorted(snapshot_rows.keys(), key=parse_utc)
    return timestamps, snapshot_rows


def evaluate_decision(row: SnapshotDecisionRow) -> dict[str, Any]:
    m_hat = PRIMITIVE.clip(float(row.M_k), -1.0, 1.0)
    s = float(row.S_UF) - float(row.U_star_k)
    r = float(row.R_UF) - float(row.U_star_k)
    core = min(max(s, 0.0), max(r, 0.0))
    edge = max(max(s, 0.0), max(r, 0.0)) - core
    live = core + PRIMITIVE.RATIONALIZED_PARAMS["beta"] * edge
    contested = (1.0 - PRIMITIVE.RATIONALIZED_PARAMS["beta"]) * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(-max(s, r), 0.0)

    d_nonadverse = (1.0 + float(row.D_k)) / 2.0
    d_adverse = max(-float(row.D_k), 0.0)
    m_continue = (1.0 + m_hat) / 2.0
    m_bend = (1.0 - m_hat) / 2.0

    motion = (
        PRIMITIVE.RATIONALIZED_PARAMS["motion_weight"] * (d_nonadverse ** PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])
        + (1.0 - PRIMITIVE.RATIONALIZED_PARAMS["motion_weight"]) * (m_continue ** PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])
    ) ** (1.0 / PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])

    adverse_break = d_adverse * m_bend
    reversal_break = float(row.R_rev_k) * ((1.0 - balance) ** PRIMITIVE.RATIONALIZED_PARAMS["reversal_balance_power"])
    carry_break = (-float(row.B_k)) * float(row.R_rev_k) * ((1.0 - balance) ** PRIMITIVE.RATIONALIZED_PARAMS["carry_balance_power"]) * (1.0 - adverse_break)
    burden = (
        PRIMITIVE.RATIONALIZED_PARAMS["burden_scale"]
        * (float(row.C_k) / (1.0 + float(row.C_k)))
        * (float(row.P_k) / (1.0 + float(row.P_k)))
    )
    break_agreement = max(adverse_break, reversal_break, carry_break)

    accumulate_basin = live * motion * (1.0 - float(row.R_rev_k)) * (1.0 - adverse_break) * (1.0 - burden)
    hold_basin = contested * (1.0 - break_agreement) + live * float(row.R_rev_k) * balance + live * (1.0 - float(row.R_rev_k)) * (
        (1.0 - motion) * (1.0 - adverse_break) + motion * burden
    )
    avoid_basin = rupture + (live + contested) * break_agreement
    decision = PRIMITIVE.decide(accumulate_basin, hold_basin, avoid_basin)

    return {
        "decision": decision,
        "Accumulate_basin": accumulate_basin,
        "Hold_basin": hold_basin,
        "Avoid_basin": avoid_basin,
    }


def fetch_symbol_bars(symbol: str, start: datetime, end: datetime) -> list[Bar]:
    client = get_unified_market_data()
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )
    result = client.get_history(req)
    bars = list(getattr(result, "bars", []) or [])
    return sorted(bars, key=lambda bar: bar.timestamp)


def bars_to_maps(bars: list[Bar]) -> dict[datetime, Bar]:
    return {bar.timestamp.astimezone(timezone.utc): bar for bar in bars}


def next_market_open_after(ts: datetime, spy_bars: list[Bar]) -> tuple[datetime, float]:
    for bar in spy_bars:
        bar_ts = bar.timestamp.astimezone(timezone.utc)
        if bar_ts > ts:
            return bar_ts, float(bar.open)
    raise RuntimeError(f"no next market open after snapshot timestamp {ts.isoformat()}")


def next_common_open_after(
    ts: datetime,
    required_symbols: list[str],
    spy_bars: list[Bar],
    open_maps: dict[str, dict[datetime, float]],
) -> datetime:
    if not required_symbols:
        return next_market_open_after(ts, spy_bars)[0]
    for bar in spy_bars:
        bar_ts = bar.timestamp.astimezone(timezone.utc)
        if bar_ts <= ts:
            continue
        if all((open_maps.get(symbol, {}).get(bar_ts) or 0.0) > 0.0 for symbol in required_symbols):
            return bar_ts
    raise RuntimeError(
        f"no common next-open execution day after {ts.isoformat()} for symbols: {required_symbols}"
    )


def solve_target_value(open_equity: float, current_values: dict[str, float], target_symbols: list[str]) -> float:
    if not target_symbols:
        return 0.0
    lo = 0.0
    hi = open_equity / float(len(target_symbols))

    def total_with_cost(v: float) -> float:
        gross = v * float(len(target_symbols))
        costs = 0.0
        for symbol in target_symbols:
            current = current_values.get(symbol, 0.0)
            costs += abs(v - current) * SLIPPAGE_RATE
        for symbol, current in current_values.items():
            if symbol not in target_symbols:
                costs += abs(current) * SLIPPAGE_RATE
        return gross + costs

    for _ in range(80):
        mid = (lo + hi) / 2.0
        if total_with_cost(mid) <= open_equity:
            lo = mid
        else:
            hi = mid
    return lo


def daily_equity_series(
    holdings_periods: list[dict[str, Any]],
    cash_periods: list[dict[str, Any]],
    close_maps: dict[str, dict[datetime, float]],
    calendar: list[datetime],
) -> pd.Series:
    values: list[float] = []
    dates: list[pd.Timestamp] = []
    for day in calendar:
        cash_value = 0.0
        for period in cash_periods:
            if period["start"] <= day <= period["end"]:
                cash_value += float(period["cash"])

        holdings_value = 0.0
        for period in holdings_periods:
            if not (period["start"] <= day <= period["end"]):
                continue
            symbol = str(period["symbol"])
            price_map = close_maps[symbol]
            eligible_days = [ts for ts in price_map.keys() if ts <= day]
            if not eligible_days:
                raise RuntimeError(f"missing close history for held symbol {symbol} on {day.isoformat()}")
            px = price_map[max(eligible_days)]
            holdings_value += float(period["shares"]) * float(px)

        dates.append(pd.Timestamp(day))
        values.append(cash_value + holdings_value)
    return pd.Series(values, index=pd.DatetimeIndex(dates), name="dsf_equity")


def benchmark_series(spy_bars: list[Bar], start_exec_day: datetime, initial_capital: float) -> pd.Series:
    spy_open = None
    for bar in spy_bars:
        ts = bar.timestamp.astimezone(timezone.utc)
        if ts == start_exec_day:
            spy_open = float(bar.open)
            break
    if spy_open is None or spy_open <= 0.0:
        raise RuntimeError(f"missing SPY open on benchmark start day {start_exec_day.isoformat()}")
    shares = initial_capital / (spy_open * (1.0 + SLIPPAGE_RATE))
    values = []
    dates = []
    for bar in spy_bars:
        ts = bar.timestamp.astimezone(timezone.utc)
        if ts < start_exec_day:
            continue
        values.append(shares * float(bar.close))
        dates.append(pd.Timestamp(ts))
    return pd.Series(values, index=pd.DatetimeIndex(dates), name="spy_equity")


def total_return(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first <= 0.0:
        return 0.0
    return (last / first) - 1.0


def cagr(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first <= 0.0 or last <= 0.0:
        return 0.0
    days = max(1.0, float((series.index[-1] - series.index[0]).days))
    return (last / first) ** (365.25 / days) - 1.0


def monthly_return_table(series: pd.Series) -> list[dict[str, Any]]:
    if series.empty:
        return []
    monthly = series.resample("ME").last().pct_change().dropna()
    return [{"month": idx.strftime("%Y-%m"), "return": float(val)} for idx, val in monthly.items()]


def annual_return_table(series: pd.Series) -> list[dict[str, Any]]:
    if series.empty:
        return []
    annual = series.resample("YE").last().pct_change().dropna()
    return [{"year": idx.strftime("%Y"), "return": float(val)} for idx, val in annual.items()]


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# DSF Frozen Primitive Backtest vs SPY",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- archive_db_path: `{summary['archive_db_path']}`",
        f"- slippage_bps_per_trade: `{summary['slippage_bps_per_trade']}`",
        f"- snapshot_timestamps: `{summary['snapshot_timestamps']}`",
        f"- signal_rows_scored: `{summary['signal_rows_scored']}`",
        f"- ever_accumulate_symbol_count: `{summary['ever_accumulate_symbol_count']}`",
        f"- final_verdict: `{summary['final_verdict']}`",
        "",
        "## DSF Portfolio",
        "",
        f"- final_account_value: `{summary['dsf']['final_account_value']}`",
        f"- total_return: `{summary['dsf']['total_return']}`",
        f"- CAGR: `{summary['dsf']['cagr']}`",
        f"- max_drawdown: `{summary['dsf']['max_drawdown']}`",
        f"- volatility: `{summary['dsf']['volatility']}`",
        f"- turnover: `{summary['dsf']['turnover']}`",
        f"- total_trade_count: `{summary['dsf']['total_trade_count']}`",
        f"- average_holding_period_days: `{summary['dsf']['average_holding_period_days']}`",
        "",
        "## SPY",
        "",
        f"- final_account_value: `{summary['spy']['final_account_value']}`",
        f"- total_return: `{summary['spy']['total_return']}`",
        f"- CAGR: `{summary['spy']['cagr']}`",
        f"- max_drawdown: `{summary['spy']['max_drawdown']}`",
        f"- volatility: `{summary['spy']['volatility']}`",
        "",
        "## Lift vs SPY",
        "",
        f"- total_return_difference: `{summary['lift']['total_return_difference']}`",
        f"- cagr_difference: `{summary['lift']['cagr_difference']}`",
        f"- final_wealth_ratio: `{summary['lift']['final_wealth_ratio']}`",
    ]
    return "\n".join(lines)


def run_slack(summary_json: Path) -> None:
    payload = {
        "text": f"Codex completed DSF frozen primitive backtest vs SPY. summary={summary_json.name}"
    }
    if SLACK_SCRIPT.exists():
        subprocess.run(
            [str(SLACK_SCRIPT)],
            cwd=str(REPO_ROOT),
            input=json.dumps(payload) + "\n",
            text=True,
            check=True,
        )


def main() -> int:
    timestamps, snapshot_rows = load_archive_rows(ARCHIVE_DB)
    if not timestamps:
        raise RuntimeError("archive has no snapshot timestamps")

    decisions_by_ts: dict[str, dict[str, str]] = {}
    counts_by_ts: dict[str, dict[str, int]] = {}
    ever_accumulate_symbols: set[str] = set()
    signal_rows_scored = 0

    for ts in timestamps:
        decisions: dict[str, str] = {}
        counts = {"Accumulate": 0, "Hold": 0, "Avoid": 0}
        for row in snapshot_rows[ts]:
            result = evaluate_decision(row)
            decision = str(result["decision"])
            decisions[row.symbol] = decision
            counts[decision] += 1
            signal_rows_scored += 1
            if decision == "Accumulate":
                ever_accumulate_symbols.add(row.symbol)
        decisions_by_ts[ts] = decisions
        counts_by_ts[ts] = counts

    if not ever_accumulate_symbols:
        raise RuntimeError("frozen primitive produced no Accumulate symbols across archive dates")

    start_ts = parse_utc(timestamps[0])
    fetch_start = start_ts - pd.Timedelta(days=7)
    fetch_end = datetime.now(timezone.utc)

    price_symbols = sorted(set(ever_accumulate_symbols) | {"SPY"})
    bars_by_symbol: dict[str, list[Bar]] = {}
    for idx, symbol in enumerate(price_symbols, start=1):
        print(f"[bars] {idx}/{len(price_symbols)} {symbol}")
        bars_by_symbol[symbol] = fetch_symbol_bars(symbol, fetch_start, fetch_end)
        if not bars_by_symbol[symbol]:
            raise RuntimeError(f"missing adjusted daily bars for {symbol}")

    spy_bars = bars_by_symbol["SPY"]
    current_cash = INITIAL_CAPITAL
    holdings: dict[str, float] = {}
    holding_start_day: dict[str, datetime] = {}
    trade_records: list[TradeRecord] = []
    cash_periods: list[dict[str, Any]] = []
    holdings_periods: list[dict[str, Any]] = []
    total_traded_notional = 0.0
    completed_holding_days: list[float] = []
    backtest_start_exec_day: datetime | None = None

    close_maps = {
        symbol: {bar.timestamp.astimezone(timezone.utc): float(bar.close) for bar in bars}
        for symbol, bars in bars_by_symbol.items()
    }
    open_maps = {
        symbol: {bar.timestamp.astimezone(timezone.utc): float(bar.open) for bar in bars}
        for symbol, bars in bars_by_symbol.items()
    }

    for idx, ts in enumerate(timestamps):
        signal_dt = parse_utc(ts)
        decisions = decisions_by_ts[ts]
        held_symbols = sorted(holdings.keys())
        missing_held = [symbol for symbol in held_symbols if symbol not in decisions]
        if missing_held:
            raise RuntimeError(f"held symbols missing from snapshot at {ts}: {missing_held}")

        hold_symbols = sorted(symbol for symbol in held_symbols if decisions[symbol] == "Hold")
        accumulate_symbols = sorted(symbol for symbol, decision in decisions.items() if decision == "Accumulate")
        target_symbols = sorted(set(hold_symbols) | set(accumulate_symbols))

        needed_prices = sorted(set(held_symbols) | set(target_symbols))
        exec_day = next_common_open_after(signal_dt, needed_prices, spy_bars, open_maps)
        if backtest_start_exec_day is None:
            backtest_start_exec_day = exec_day
        open_prices: dict[str, float] = {}
        for symbol in needed_prices:
            price = open_maps.get(symbol, {}).get(exec_day)
            if price is None or price <= 0.0:
                raise RuntimeError(f"missing next-open execution price for {symbol} on {exec_day.isoformat()}")
            open_prices[symbol] = price

        open_equity = current_cash + sum(float(holdings[symbol]) * open_prices[symbol] for symbol in held_symbols)
        current_values = {symbol: float(holdings[symbol]) * open_prices[symbol] for symbol in held_symbols}
        target_value = solve_target_value(open_equity, current_values, target_symbols)

        trade_cost_total = 0.0
        next_holdings: dict[str, float] = {}

        for symbol in sorted(set(held_symbols) | set(target_symbols)):
            price = open_prices[symbol]
            current_shares = float(holdings.get(symbol, 0.0))
            current_value = current_shares * price
            desired_value = target_value if symbol in target_symbols else 0.0
            desired_shares = desired_value / price if price > 0.0 else 0.0
            delta_shares = desired_shares - current_shares
            notional = abs(delta_shares) * price
            trade_cost = notional * SLIPPAGE_RATE
            trade_cost_total += trade_cost

            if abs(delta_shares) > 1e-12:
                total_traded_notional += notional
                action = "BUY" if delta_shares > 0 else "SELL"
                signal_decision = decisions.get(symbol, "MISSING")
                trade_records.append(
                    TradeRecord(
                        signal_timestamp_utc=ts,
                        execution_timestamp_utc=exec_day.isoformat().replace("+00:00", "Z"),
                        symbol=symbol,
                        action=action,
                        shares_delta=float(delta_shares),
                        execution_open=float(price),
                        notional=float(notional),
                        slippage_cost=float(trade_cost),
                        portfolio_equity_at_open=float(open_equity),
                        decision_at_signal=str(signal_decision),
                    )
                )

            if desired_shares > 1e-12:
                next_holdings[symbol] = desired_shares

            if current_shares > 1e-12 and desired_shares <= 1e-12:
                start_day = holding_start_day.pop(symbol)
                completed_holding_days.append(float((exec_day - start_day).days))
                holdings_periods.append({"symbol": symbol, "shares": current_shares, "start": start_day, "end": exec_day})

        current_cash = max(0.0, open_equity - (target_value * float(len(target_symbols))) - trade_cost_total)

        for symbol in target_symbols:
            if symbol not in holding_start_day:
                holding_start_day[symbol] = exec_day

        holdings = next_holdings

        next_exec_day = None
        if idx + 1 < len(timestamps):
            next_exec_day, _ = next_market_open_after(parse_utc(timestamps[idx + 1]), spy_bars)
            cash_periods.append({"cash": current_cash, "start": exec_day, "end": next_exec_day})
        else:
            cash_periods.append({"cash": current_cash, "start": exec_day, "end": spy_bars[-1].timestamp.astimezone(timezone.utc)})

    if backtest_start_exec_day is None:
        raise RuntimeError("could not determine first execution day")

    final_end_day = spy_bars[-1].timestamp.astimezone(timezone.utc)
    for symbol, shares in holdings.items():
        holdings_periods.append({"symbol": symbol, "shares": shares, "start": holding_start_day[symbol], "end": final_end_day})
        completed_holding_days.append(float((final_end_day - holding_start_day[symbol]).days))

    market_calendar = [bar.timestamp.astimezone(timezone.utc) for bar in spy_bars if bar.timestamp.astimezone(timezone.utc) >= backtest_start_exec_day]
    dsf_series = daily_equity_series(holdings_periods, cash_periods, close_maps, market_calendar)
    spy_series = benchmark_series(spy_bars, backtest_start_exec_day, INITIAL_CAPITAL)

    aligned = pd.concat([dsf_series, spy_series], axis=1).dropna()
    dsf_series = aligned.iloc[:, 0]
    spy_series = aligned.iloc[:, 1]

    dsf_ret = daily_returns(dsf_series)
    spy_ret = daily_returns(spy_series)
    dsf_mdd, _ = max_drawdown(dsf_series)
    spy_mdd, _ = max_drawdown(spy_series)

    avg_equity = float(dsf_series.mean()) if not dsf_series.empty else 0.0
    turnover = (total_traded_notional / avg_equity) if avg_equity > 0.0 else 0.0

    dsf_final = float(dsf_series.iloc[-1]) if not dsf_series.empty else INITIAL_CAPITAL
    spy_final = float(spy_series.iloc[-1]) if not spy_series.empty else INITIAL_CAPITAL

    dsf_total_return = total_return(dsf_series)
    spy_total_return = total_return(spy_series)
    dsf_cagr = cagr(dsf_series)
    spy_cagr = cagr(spy_series)

    final_verdict = "DSF primitive backtest does not beat SPY"
    if dsf_total_return > spy_total_return:
        if abs(dsf_mdd) <= abs(spy_mdd) and annualized_volatility(dsf_ret) <= annualized_volatility(spy_ret):
            final_verdict = "DSF primitive backtest beats SPY on return and acceptable risk"
        else:
            final_verdict = "DSF primitive backtest beats SPY on return but with worse risk"

    stamp = utc_stamp()
    summary_json = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_summary_{stamp}.json"
    summary_md = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_summary_{stamp}.md"
    equity_csv = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_equity_{stamp}.csv"
    equity_json = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_equity_{stamp}.json"
    trades_csv = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_trades_{stamp}.csv"
    trades_json = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_trades_{stamp}.json"
    monthly_json = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_monthly_{stamp}.json"
    annual_json = RUNTIME_ROOT / f"dsf_frozen_primitive_backtest_vs_spy_annual_{stamp}.json"

    trade_rows = [
        {
            "signal_timestamp_utc": tr.signal_timestamp_utc,
            "execution_timestamp_utc": tr.execution_timestamp_utc,
            "symbol": tr.symbol,
            "action": tr.action,
            "shares_delta": tr.shares_delta,
            "execution_open": tr.execution_open,
            "notional": tr.notional,
            "slippage_cost": tr.slippage_cost,
            "portfolio_equity_at_open": tr.portfolio_equity_at_open,
            "decision_at_signal": tr.decision_at_signal,
        }
        for tr in trade_records
    ]

    equity_rows = [
        {
            "date": idx.isoformat(),
            "dsf_equity": float(dsf_series.loc[idx]),
            "spy_equity": float(spy_series.loc[idx]),
        }
        for idx in dsf_series.index
    ]

    monthly_payload = {
        "dsf": monthly_return_table(dsf_series),
        "spy": monthly_return_table(spy_series),
    }
    annual_payload = {
        "dsf": annual_return_table(dsf_series),
        "spy": annual_return_table(spy_series),
    }

    summary = {
        "generated_at_utc": utc_now_iso(),
        "archive_db_path": str(ARCHIVE_DB),
        "primitive_runner_path": str(PRIMITIVE_RUNNER),
        "initial_capital": INITIAL_CAPITAL,
        "slippage_bps_per_trade": SLIPPAGE_BPS_PER_TRADE,
        "slippage_basis": "10 bps per executed trade, equivalent to 20 bps round-trip, aligned to the repo's existing 0.20% round-trip backtest cost precedent.",
        "snapshot_timestamps": timestamps,
        "signal_rows_scored": signal_rows_scored,
        "ever_accumulate_symbol_count": len(ever_accumulate_symbols),
        "candidate_counts_by_snapshot": counts_by_ts,
        "backtest_start_execution_day_utc": backtest_start_exec_day.isoformat().replace("+00:00", "Z"),
        "backtest_end_valuation_day_utc": final_end_day.isoformat().replace("+00:00", "Z"),
        "dsf": {
            "final_account_value": dsf_final,
            "total_return": dsf_total_return,
            "cagr": dsf_cagr,
            "max_drawdown": dsf_mdd,
            "volatility": annualized_volatility(dsf_ret),
            "turnover": turnover,
            "turnover_definition": "gross traded notional divided by average daily portfolio equity over the backtest window",
            "total_trade_count": len(trade_rows),
            "average_holding_period_days": (sum(completed_holding_days) / len(completed_holding_days)) if completed_holding_days else 0.0,
        },
        "spy": {
            "final_account_value": spy_final,
            "total_return": spy_total_return,
            "cagr": spy_cagr,
            "max_drawdown": spy_mdd,
            "volatility": annualized_volatility(spy_ret),
        },
        "lift": {
            "total_return_difference": dsf_total_return - spy_total_return,
            "cagr_difference": dsf_cagr - spy_cagr,
            "final_wealth_ratio": (dsf_final / spy_final) if spy_final > 0.0 else None,
        },
        "evaluated_snapshot_count": len(timestamps),
        "dropped_or_unscored_rows": 0,
        "equity_curve_csv": str(equity_csv),
        "equity_curve_json": str(equity_json),
        "trade_log_csv": str(trades_csv),
        "trade_log_json": str(trades_json),
        "monthly_returns_json": str(monthly_json),
        "annual_returns_json": str(annual_json),
        "final_verdict": final_verdict,
    }

    _json_dump(summary_json, summary)
    summary_md.write_text(markdown_summary(summary), encoding="utf-8")
    _csv_dump(equity_csv, equity_rows)
    _json_dump(equity_json, equity_rows)
    _csv_dump(trades_csv, trade_rows)
    _json_dump(trades_json, trade_rows)
    _json_dump(monthly_json, monthly_payload)
    _json_dump(annual_json, annual_payload)

    run_slack(summary_json)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
