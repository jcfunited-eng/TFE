#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
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
from uf_core.uf_structural_engine import compute_structural_state
from unified_market_data_service import get_unified_market_data


RUNTIME_ROOT = REPO_ROOT / "backups" / "runtime"
SNAPSHOT_CSV = RUNTIME_ROOT / "canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv"
ARCHIVE_DB = RUNTIME_ROOT / "dsf_historical_full_surface_snapshot_archive_v2.sqlite"
PRIMITIVE_RUNNER = REPO_ROOT / "tools" / "run_dsf_full_field_sortable_v3_rationalized.py"
NOTE_PATH = REPO_ROOT / "DSF_CLEAN_WALKFORWARD_REPLAY_WITH_SYMBOL_MEMORY_V1.md"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"

INITIAL_CAPITAL = 100_000.0
SLIPPAGE_BPS_PER_TRADE = 10.0
SLIPPAGE_RATE = SLIPPAGE_BPS_PER_TRADE / 10000.0
MEMORY_WARMUP_BARS = 252
OUTCOME_H = 5
FETCH_BUFFER_DAYS = 550


@dataclass
class SymbolReplayData:
    symbol: str
    raw_history_bars: list[Bar]
    replay_calendar: list[datetime]
    adjusted_bars: list[Bar]


@dataclass
class SymbolMemoryCard:
    symbol: str
    warmup_bars: int
    carry_threshold: float
    n_protected: int
    n_contested: int
    n_rupture: int
    n_continue: int
    n_bend: int
    n_reversal: int
    n_reversal_success: int
    n_reversal_eval: int
    n_contested_up: int
    n_contested_eval: int
    n_carry_success: int
    n_carry_eval: int
    profile: str
    reversal_reliability: float
    contested_up_rate: float
    carry_reliability: float


@dataclass
class TradeRecord:
    lane: str
    signal_date_utc: str
    execution_date_utc: str
    symbol: str
    action: str
    shares_delta: float
    execution_open: float
    notional: float
    slippage_cost: float
    reserve_state: str
    motion_state: str
    geometry_family: str
    signal_decision: str


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


def _load_primitive_module():
    spec = importlib.util.spec_from_file_location("frozen_primitive_module", PRIMITIVE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load primitive runner: {PRIMITIVE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRIMITIVE = _load_primitive_module()


def load_universe_symbols(limit: int | None) -> list[str]:
    if not SNAPSHOT_CSV.exists():
        raise RuntimeError(f"missing snapshot csv: {SNAPSHOT_CSV}")
    with SNAPSHOT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if "symbol" not in (reader.fieldnames or []):
            raise RuntimeError(f"snapshot csv missing symbol field: {SNAPSHOT_CSV}")
        symbols = [str(row["symbol"]).strip().upper() for row in reader if str(row.get("symbol") or "").strip()]
    symbols = sorted(dict.fromkeys(symbols))
    if limit is not None:
        symbols = symbols[:limit]
    return symbols


def replay_anchor_timestamp() -> datetime:
    if not ARCHIVE_DB.exists():
        raise RuntimeError(f"missing archive db: {ARCHIVE_DB}")
    conn = sqlite3.connect(ARCHIVE_DB)
    row = conn.execute("SELECT MIN(snapshot_timestamp_utc) FROM snapshot_runs").fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("archive db has no snapshot runs")
    return parse_utc(str(row[0]))


def fetch_symbol_bars(symbol: str, start: datetime, end: datetime, adjusted: bool) -> list[Bar]:
    client = get_unified_market_data()
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=adjusted,
        limit=None,
    )
    result = client.get_history(req)
    bars = list(getattr(result, "bars", []) or [])
    return sorted(bars, key=lambda bar: bar.timestamp.astimezone(timezone.utc))


def bar_map(bars: list[Bar]) -> dict[datetime, Bar]:
    return {bar.timestamp.astimezone(timezone.utc): bar for bar in bars}


def compute_replay_calendar() -> tuple[list[datetime], list[datetime], datetime, datetime]:
    anchor = replay_anchor_timestamp()
    raw_spy = fetch_symbol_bars("SPY", anchor - timedelta(days=FETCH_BUFFER_DAYS), datetime.now(timezone.utc), adjusted=False)
    adj_spy = fetch_symbol_bars("SPY", anchor - timedelta(days=FETCH_BUFFER_DAYS), datetime.now(timezone.utc), adjusted=True)
    if not raw_spy or not adj_spy:
        raise RuntimeError("missing vendor-direct SPY bars for replay calendar")
    raw_dates = {bar.timestamp.astimezone(timezone.utc) for bar in raw_spy}
    adj_dates = {bar.timestamp.astimezone(timezone.utc) for bar in adj_spy}
    spy_dates = sorted(raw_dates & adj_dates)
    if anchor not in spy_dates:
        later = [d for d in spy_dates if d >= anchor]
        if not later:
            raise RuntimeError(f"SPY calendar has no date at or after anchor {anchor.isoformat()}")
        anchor = later[0]
    anchor_index = spy_dates.index(anchor)
    if anchor_index < MEMORY_WARMUP_BARS:
        raise RuntimeError(
            f"SPY calendar lacks {MEMORY_WARMUP_BARS} warm-up bars before anchor {anchor.isoformat()}"
        )
    warmup_start = spy_dates[anchor_index - MEMORY_WARMUP_BARS]
    full_calendar = spy_dates[anchor_index - MEMORY_WARMUP_BARS :]
    replay_calendar = spy_dates[anchor_index:]
    return full_calendar, replay_calendar, warmup_start, anchor


def align_symbol_to_calendar(symbol: str, raw_bars: list[Bar], adjusted_bars: list[Bar], calendar: list[datetime]) -> SymbolReplayData:
    raw = bar_map(raw_bars)
    adj = bar_map(adjusted_bars)
    missing_raw = [day for day in calendar if day not in raw]
    missing_adj = [day for day in calendar if day not in adj]
    if missing_raw:
        raise RuntimeError(f"{symbol} missing raw bars on {len(missing_raw)} replay dates")
    if missing_adj:
        raise RuntimeError(f"{symbol} missing adjusted bars on {len(missing_adj)} replay dates")
    earliest_required = calendar[0]
    raw_history = [bar for bar in raw_bars if bar.timestamp.astimezone(timezone.utc) <= calendar[-1]]
    if not any(bar.timestamp.astimezone(timezone.utc) < earliest_required for bar in raw_history):
        raise RuntimeError(f"{symbol} lacks prior raw history before warm-up start")
    return SymbolReplayData(
        symbol=symbol,
        raw_history_bars=raw_history,
        replay_calendar=list(calendar),
        adjusted_bars=[adj[day] for day in calendar],
    )


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def sign3(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def frozen_primitive_decision(fields: dict[str, float]) -> dict[str, Any]:
    m_hat = PRIMITIVE.clip(float(fields["M_k"]), -1.0, 1.0)
    s = float(fields["S_UF"]) - float(fields["U_star_k"])
    r = float(fields["R_UF"]) - float(fields["U_star_k"])
    core = min(max(s, 0.0), max(r, 0.0))
    edge = max(max(s, 0.0), max(r, 0.0)) - core
    live = core + PRIMITIVE.RATIONALIZED_PARAMS["beta"] * edge
    contested = (1.0 - PRIMITIVE.RATIONALIZED_PARAMS["beta"]) * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(-max(s, r), 0.0)

    d_nonadverse = (1.0 + float(fields["D_k"])) / 2.0
    d_adverse = max(-float(fields["D_k"]), 0.0)
    m_continue = (1.0 + m_hat) / 2.0
    m_bend = (1.0 - m_hat) / 2.0

    motion = (
        PRIMITIVE.RATIONALIZED_PARAMS["motion_weight"] * (d_nonadverse ** PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])
        + (1.0 - PRIMITIVE.RATIONALIZED_PARAMS["motion_weight"]) * (m_continue ** PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])
    ) ** (1.0 / PRIMITIVE.RATIONALIZED_PARAMS["motion_power"])

    adverse_break = d_adverse * m_bend
    reversal_break = float(fields["R_rev_k"]) * ((1.0 - balance) ** PRIMITIVE.RATIONALIZED_PARAMS["reversal_balance_power"])
    carry_break = (-float(fields["B_k"])) * float(fields["R_rev_k"]) * ((1.0 - balance) ** PRIMITIVE.RATIONALIZED_PARAMS["carry_balance_power"]) * (1.0 - adverse_break)
    burden = (
        PRIMITIVE.RATIONALIZED_PARAMS["burden_scale"]
        * (float(fields["C_k"]) / (1.0 + float(fields["C_k"])))
        * (float(fields["P_k"]) / (1.0 + float(fields["P_k"])))
    )
    break_agreement = max(adverse_break, reversal_break, carry_break)

    accumulate_basin = live * motion * (1.0 - float(fields["R_rev_k"])) * (1.0 - adverse_break) * (1.0 - burden)
    hold_basin = contested * (1.0 - break_agreement) + live * float(fields["R_rev_k"]) * balance + live * (1.0 - float(fields["R_rev_k"])) * (
        (1.0 - motion) * (1.0 - adverse_break) + motion * burden
    )
    avoid_basin = rupture + (live + contested) * break_agreement
    decision = PRIMITIVE.decide(accumulate_basin, hold_basin, avoid_basin)
    return {
        "decision": decision,
        "Accumulate_basin": accumulate_basin,
        "Hold_basin": hold_basin,
        "Avoid_basin": avoid_basin,
        "core": core,
        "edge": edge,
        "rupture_mag": rupture,
        "m_hat": m_hat,
    }


def reserve_state(core: float, edge: float, rupture_mag: float) -> str:
    if rupture_mag > 0.0:
        return "rupture"
    if edge > core:
        return "contested"
    return "protected"


def motion_state(d_k: float, m_hat: float, r_rev_k: float) -> str:
    if r_rev_k > 0.0:
        return "reversal"
    if d_k >= 0.0 and m_hat >= 0.0:
        return "continue"
    return "bend"


def memory_profile(card: SymbolMemoryCard, protected_freq: float, rupture_freq: float, reversal_freq: float) -> str:
    if rupture_freq >= 0.20 or (reversal_freq >= 0.15 and card.reversal_reliability >= 0.60):
        return "defensive"
    if protected_freq >= 0.45 and card.contested_up_rate >= 0.55 and card.carry_reliability >= 0.55:
        return "permissive"
    return "standard"


def build_symbol_replay(symbol_data: SymbolReplayData) -> dict[str, Any]:
    symbol = symbol_data.symbol
    if len(symbol_data.replay_calendar) != len(symbol_data.adjusted_bars):
        raise RuntimeError(f"{symbol} calendar/adjusted alignment length mismatch")
    if len(symbol_data.replay_calendar) < MEMORY_WARMUP_BARS + 2:
        raise RuntimeError(f"{symbol} has insufficient aligned bars for memory and execution")

    states: list[dict[str, Any]] = []
    raw_history = sorted(symbol_data.raw_history_bars, key=lambda bar: bar.timestamp.astimezone(timezone.utc))
    raw_idx = 0
    for idx, day in enumerate(symbol_data.replay_calendar):
        while raw_idx < len(raw_history) and raw_history[raw_idx].timestamp.astimezone(timezone.utc) <= day:
            raw_idx += 1
        raw_prefix = raw_history[:raw_idx]
        if not raw_prefix:
            raise RuntimeError(f"{symbol} has no raw prefix by replay day {day.isoformat()}")
        try:
            state = compute_structural_state(symbol, raw_prefix)
        except Exception as exc:
            raise RuntimeError(f"{symbol} structural rebuild failed at bar {idx}: {exc}") from exc
        missing_fields = [
            field
            for field in ["S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"]
            if state.get(field) is None
        ]
        if missing_fields:
            raise RuntimeError(f"{symbol} structural rebuild returned missing fields at bar {idx}: {missing_fields}")
        extracted = {
            "date": day,
            "S_UF": float(state["S_UF"]),
            "R_UF": float(state["R_UF"]),
            "D_k": float(state["D_k"]),
            "M_k": float(state["M_k"]),
            "R_rev_k": float(state["R_rev_k"]),
            "U_star_k": float(state["U_star_k"]),
            "C_k": float(state["C_k"]),
            "P_k": float(state["P_k"]),
            "B_k": float(state["B_k"]),
            "bar_count": int(state.get("bar_count") or (idx + 1)),
        }
        primitive = frozen_primitive_decision(extracted)
        s = extracted["S_UF"] - extracted["U_star_k"]
        r = extracted["R_UF"] - extracted["U_star_k"]
        core = primitive["core"]
        edge = primitive["edge"]
        rupture_mag = primitive["rupture_mag"]
        m_hat = primitive["m_hat"]
        extracted.update(
            {
                "s": s,
                "r": r,
                "core": core,
                "edge": edge,
                "rupture_mag": rupture_mag,
                "M_hat": m_hat,
                "reserve_state": reserve_state(core, edge, rupture_mag),
                "motion_state": motion_state(extracted["D_k"], m_hat, extracted["R_rev_k"]),
                "primitive_decision": primitive["decision"],
                "Accumulate_basin": primitive["Accumulate_basin"],
                "Hold_basin": primitive["Hold_basin"],
                "Avoid_basin": primitive["Avoid_basin"],
            }
        )
        states.append(extracted)

    carry_threshold = float(median([-state["B_k"] for state in states[:MEMORY_WARMUP_BARS]]))

    counts = Counter()
    reversal_success = 0
    reversal_eval = 0
    contested_up = 0
    contested_eval = 0
    carry_success = 0
    carry_eval = 0

    adj_closes = [float(bar.close) for bar in symbol_data.adjusted_bars]

    for idx in range(MEMORY_WARMUP_BARS):
        state = states[idx]
        counts[f"reserve_{state['reserve_state']}"] += 1
        counts[f"motion_{state['motion_state']}"] += 1

        future_exists_in_warmup = idx + OUTCOME_H < MEMORY_WARMUP_BARS
        if future_exists_in_warmup:
            fwd_ret_5 = adj_closes[idx + OUTCOME_H] / adj_closes[idx] - 1.0
            fwd_sign = sign3(fwd_ret_5)
        else:
            fwd_sign = None

        if state["motion_state"] == "reversal" and state["D_k"] != 0.0 and future_exists_in_warmup:
            reversal_eval += 1
            if fwd_sign == -sign3(state["D_k"]):
                reversal_success += 1

        if state["reserve_state"] == "contested" and future_exists_in_warmup:
            contested_eval += 1
            if fwd_sign is not None and fwd_sign > 0:
                contested_up += 1

        if (-state["B_k"]) >= carry_threshold and state["motion_state"] == "continue" and future_exists_in_warmup:
            carry_eval += 1
            if fwd_sign is not None and fwd_sign > 0:
                carry_success += 1

    reversal_reliability = (reversal_success + 1.0) / (reversal_eval + 2.0)
    contested_up_rate = (contested_up + 1.0) / (contested_eval + 2.0)
    carry_reliability = (carry_success + 1.0) / (carry_eval + 2.0)

    temp_card = SymbolMemoryCard(
        symbol=symbol,
        warmup_bars=MEMORY_WARMUP_BARS,
        carry_threshold=carry_threshold,
        n_protected=int(counts["reserve_protected"]),
        n_contested=int(counts["reserve_contested"]),
        n_rupture=int(counts["reserve_rupture"]),
        n_continue=int(counts["motion_continue"]),
        n_bend=int(counts["motion_bend"]),
        n_reversal=int(counts["motion_reversal"]),
        n_reversal_success=int(reversal_success),
        n_reversal_eval=int(reversal_eval),
        n_contested_up=int(contested_up),
        n_contested_eval=int(contested_eval),
        n_carry_success=int(carry_success),
        n_carry_eval=int(carry_eval),
        profile="standard",
        reversal_reliability=float(reversal_reliability),
        contested_up_rate=float(contested_up_rate),
        carry_reliability=float(carry_reliability),
    )
    protected_freq = temp_card.n_protected / float(MEMORY_WARMUP_BARS)
    rupture_freq = temp_card.n_rupture / float(MEMORY_WARMUP_BARS)
    reversal_freq = temp_card.n_reversal / float(MEMORY_WARMUP_BARS)
    card = SymbolMemoryCard(**{**temp_card.__dict__, "profile": memory_profile(temp_card, protected_freq, rupture_freq, reversal_freq)})

    signal_rows: list[dict[str, Any]] = []
    for idx in range(MEMORY_WARMUP_BARS, len(states) - 1):
        state = states[idx]
        primitive_decision = state["primitive_decision"]
        final_decision = primitive_decision
        if primitive_decision == "Accumulate":
            if card.profile == "permissive":
                final_decision = "Accumulate"
            elif card.profile == "standard":
                if state["reserve_state"] == "protected" and state["R_rev_k"] == 0.0:
                    final_decision = "Accumulate"
                else:
                    final_decision = "Hold"
            else:
                if state["reserve_state"] == "protected" and state["motion_state"] == "continue" and state["R_rev_k"] == 0.0:
                    final_decision = "Accumulate"
                else:
                    final_decision = "Hold"

        fwd_ret_5 = None
        truth_label = None
        if idx + OUTCOME_H < len(symbol_data.adjusted_bars):
            fwd_ret_5 = float(symbol_data.adjusted_bars[idx + OUTCOME_H].close / symbol_data.adjusted_bars[idx].close - 1.0)
            sign = sign3(fwd_ret_5)
            truth_label = "Accumulate" if sign > 0 else ("Avoid" if sign < 0 else "Hold")

        signal_rows.append(
            {
                "symbol": symbol,
                "signal_date_utc": state["date"].isoformat().replace("+00:00", "Z"),
                "execution_date_utc": symbol_data.adjusted_bars[idx + 1].timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "primitive_decision": primitive_decision,
                "memory_decision": final_decision,
                "truth_label_h5": truth_label,
                "fwd_ret_5": fwd_ret_5,
                "reserve_state": state["reserve_state"],
                "motion_state": state["motion_state"],
                "geometry_family": f"{state['reserve_state']}|{state['motion_state']}",
                "S_UF": state["S_UF"],
                "R_UF": state["R_UF"],
                "D_k": state["D_k"],
                "M_k": state["M_k"],
                "M_hat": state["M_hat"],
                "R_rev_k": state["R_rev_k"],
                "U_star_k": state["U_star_k"],
                "C_k": state["C_k"],
                "P_k": state["P_k"],
                "B_k": state["B_k"],
            }
        )

    return {
        "memory_card": card.__dict__,
        "signal_rows": signal_rows,
    }


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


def total_return(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first <= 0.0:
        return 0.0
    return last / first - 1.0


def cagr(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first <= 0.0 or last <= 0.0:
        return 0.0
    days = max(1.0, float((series.index[-1] - series.index[0]).days))
    return (last / first) ** (365.25 / days) - 1.0


def run_active_lane(
    lane_name: str,
    calendar: list[datetime],
    signal_map: dict[str, dict[str, dict[str, Any]]],
    adjusted_maps: dict[str, dict[datetime, Bar]],
) -> dict[str, Any]:
    current_cash = INITIAL_CAPITAL
    holdings: dict[str, float] = {}
    holding_start_day: dict[str, datetime] = {}
    trade_records: list[TradeRecord] = []
    total_traded_notional = 0.0
    completed_holding_days: list[float] = []
    equity_rows: list[dict[str, Any]] = []
    if len(calendar) < MEMORY_WARMUP_BARS + 2:
        raise RuntimeError("calendar too short for active lane replay")

    replay_dates = calendar[MEMORY_WARMUP_BARS:]
    first_exec_day = replay_dates[1]

    for exec_idx in range(1, len(replay_dates)):
        signal_day = replay_dates[exec_idx - 1]
        exec_day = replay_dates[exec_idx]
        decisions = signal_map[signal_day.isoformat().replace("+00:00", "Z")]
        held_symbols = sorted(holdings.keys())
        hold_symbols = sorted(symbol for symbol in held_symbols if decisions[symbol][lane_name] == "Hold")
        accumulate_symbols = sorted(symbol for symbol, row in decisions.items() if row[lane_name] == "Accumulate")
        target_symbols = sorted(set(hold_symbols) | set(accumulate_symbols))
        needed = sorted(set(held_symbols) | set(target_symbols))

        open_prices: dict[str, float] = {}
        close_prices: dict[str, float] = {}
        for symbol in needed:
            bar = adjusted_maps[symbol][exec_day]
            if bar.open <= 0.0 or bar.close <= 0.0:
                raise RuntimeError(f"nonpositive adjusted price for {symbol} on {exec_day.isoformat()}")
            open_prices[symbol] = float(bar.open)
            close_prices[symbol] = float(bar.close)
        for symbol in holdings:
            if symbol not in close_prices:
                close_prices[symbol] = float(adjusted_maps[symbol][exec_day].close)
        for symbol in target_symbols:
            if symbol not in close_prices:
                close_prices[symbol] = float(adjusted_maps[symbol][exec_day].close)

        open_equity = current_cash + sum(float(holdings[s]) * open_prices[s] for s in held_symbols)
        current_values = {symbol: float(holdings[symbol]) * open_prices[symbol] for symbol in held_symbols}
        target_value = solve_target_value(open_equity, current_values, target_symbols)

        trade_cost_total = 0.0
        next_holdings: dict[str, float] = {}
        for symbol in sorted(set(held_symbols) | set(target_symbols)):
            price = open_prices[symbol]
            current_shares = float(holdings.get(symbol, 0.0))
            desired_value = target_value if symbol in target_symbols else 0.0
            desired_shares = desired_value / price if price > 0.0 else 0.0
            delta_shares = desired_shares - current_shares
            notional = abs(delta_shares) * price
            trade_cost = notional * SLIPPAGE_RATE
            trade_cost_total += trade_cost
            if abs(delta_shares) > 1e-12:
                total_traded_notional += notional
                row = decisions[symbol]
                trade_records.append(
                    TradeRecord(
                        lane=lane_name,
                        signal_date_utc=signal_day.isoformat().replace("+00:00", "Z"),
                        execution_date_utc=exec_day.isoformat().replace("+00:00", "Z"),
                        symbol=symbol,
                        action="BUY" if delta_shares > 0 else "SELL",
                        shares_delta=float(delta_shares),
                        execution_open=float(price),
                        notional=float(notional),
                        slippage_cost=float(trade_cost),
                        reserve_state=str(row["reserve_state"]),
                        motion_state=str(row["motion_state"]),
                        geometry_family=str(row["geometry_family"]),
                        signal_decision=str(row[lane_name]),
                    )
                )
            if desired_shares > 1e-12:
                next_holdings[symbol] = desired_shares
            if current_shares > 1e-12 and desired_shares <= 1e-12:
                start_day = holding_start_day.pop(symbol)
                completed_holding_days.append(float((exec_day - start_day).days))

        current_cash = max(0.0, open_equity - target_value * float(len(target_symbols)) - trade_cost_total)
        for symbol in target_symbols:
            if symbol not in holding_start_day:
                holding_start_day[symbol] = exec_day
        holdings = next_holdings

        close_equity = current_cash + sum(float(holdings[s]) * float(adjusted_maps[s][exec_day].close) for s in holdings)
        equity_rows.append(
            {
                "date_utc": exec_day.isoformat().replace("+00:00", "Z"),
                "lane": lane_name,
                "equity": float(close_equity),
                "cash": float(current_cash),
                "position_count": len(holdings),
            }
        )

    if not equity_rows:
        raise RuntimeError(f"{lane_name} produced no replay equity rows")

    for symbol, start_day in holding_start_day.items():
        completed_holding_days.append(float((replay_dates[-1] - start_day).days))

    series = pd.Series(
        [row["equity"] for row in equity_rows],
        index=pd.to_datetime([row["date_utc"] for row in equity_rows], utc=True),
        name=lane_name,
    )
    returns = daily_returns(series)
    avg_equity = float(series.mean()) if not series.empty else 0.0
    turnover = float(total_traded_notional / avg_equity) if avg_equity > 0.0 else 0.0
    max_dd, _dd_days = max_drawdown(series)
    return {
        "lane": lane_name,
        "equity_rows": equity_rows,
        "trade_rows": [record.__dict__ for record in trade_records],
        "metrics": {
            "final_account_value": float(series.iloc[-1]),
            "total_return": float(total_return(series)),
            "cagr": float(cagr(series)),
            "max_drawdown": float(max_dd),
            "volatility": float(annualized_volatility(returns)),
            "turnover": float(turnover),
            "trade_count": len(trade_records),
            "average_holding_period_days": float(sum(completed_holding_days) / len(completed_holding_days)) if completed_holding_days else 0.0,
        },
        "monthly_returns": monthly_return_table(series),
        "annual_returns": annual_return_table(series),
    }


def run_spy_benchmark(calendar: list[datetime], spy_adjusted: list[Bar]) -> dict[str, Any]:
    replay_dates = calendar[MEMORY_WARMUP_BARS:]
    first_exec_day = replay_dates[1]
    spy_map = bar_map(spy_adjusted)
    entry_open = float(spy_map[first_exec_day].open)
    shares = (INITIAL_CAPITAL * (1.0 - SLIPPAGE_RATE)) / entry_open
    equity_rows = []
    for day in replay_dates[1:]:
        close_equity = shares * float(spy_map[day].close)
        equity_rows.append({"date_utc": day.isoformat().replace("+00:00", "Z"), "lane": "spy_buy_and_hold", "equity": close_equity})
    series = pd.Series(
        [row["equity"] for row in equity_rows],
        index=pd.to_datetime([row["date_utc"] for row in equity_rows], utc=True),
        name="spy_buy_and_hold",
    )
    returns = daily_returns(series)
    max_dd, _dd_days = max_drawdown(series)
    return {
        "lane": "spy_buy_and_hold",
        "equity_rows": equity_rows,
        "metrics": {
            "final_account_value": float(series.iloc[-1]),
            "total_return": float(total_return(series)),
            "cagr": float(cagr(series)),
            "max_drawdown": float(max_dd),
            "volatility": float(annualized_volatility(returns)),
            "turnover": 0.0,
            "trade_count": 1,
            "average_holding_period_days": float((replay_dates[-1] - first_exec_day).days),
        },
        "monthly_returns": monthly_return_table(series),
        "annual_returns": annual_return_table(series),
    }


def run_equal_weight_universe_benchmark(calendar: list[datetime], kept_symbols: list[str], adjusted_maps: dict[str, dict[datetime, Bar]]) -> dict[str, Any]:
    replay_dates = calendar[MEMORY_WARMUP_BARS:]
    first_exec_day = replay_dates[1]
    if not kept_symbols:
        raise RuntimeError("no kept symbols for equal-weight universe benchmark")
    entry_value_per_symbol = INITIAL_CAPITAL / float(len(kept_symbols))
    shares: dict[str, float] = {}
    for symbol in kept_symbols:
        open_price = float(adjusted_maps[symbol][first_exec_day].open)
        shares[symbol] = (entry_value_per_symbol * (1.0 - SLIPPAGE_RATE)) / open_price
    equity_rows = []
    for day in replay_dates[1:]:
        equity = sum(float(shares[s]) * float(adjusted_maps[s][day].close) for s in kept_symbols)
        equity_rows.append({"date_utc": day.isoformat().replace("+00:00", "Z"), "lane": "equal_weight_same_tradable_universe", "equity": equity})
    series = pd.Series(
        [row["equity"] for row in equity_rows],
        index=pd.to_datetime([row["date_utc"] for row in equity_rows], utc=True),
        name="equal_weight_same_tradable_universe",
    )
    returns = daily_returns(series)
    max_dd, _dd_days = max_drawdown(series)
    return {
        "lane": "equal_weight_same_tradable_universe",
        "equity_rows": equity_rows,
        "metrics": {
            "final_account_value": float(series.iloc[-1]),
            "total_return": float(total_return(series)),
            "cagr": float(cagr(series)),
            "max_drawdown": float(max_dd),
            "volatility": float(annualized_volatility(returns)),
            "turnover": 0.0,
            "trade_count": len(kept_symbols),
            "average_holding_period_days": float((replay_dates[-1] - first_exec_day).days),
        },
        "monthly_returns": monthly_return_table(series),
        "annual_returns": annual_return_table(series),
    }


def geometry_contribution_table(signal_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for lane in ["primitive_only", "primitive_plus_symbol_memory"]:
        for row in signal_rows:
            decision = row["primitive_decision"] if lane == "primitive_only" else row["memory_decision"]
            if decision != "Accumulate" or row["fwd_ret_5"] is None:
                continue
            key = (lane, str(row["geometry_family"]))
            bucket = grouped.setdefault(
                key,
                {"lane": lane, "geometry_family": str(row["geometry_family"]), "count": 0, "sum_fwd_ret_5": 0.0, "mean_fwd_ret_5": 0.0},
            )
            bucket["count"] += 1
            bucket["sum_fwd_ret_5"] += float(row["fwd_ret_5"])
    out = []
    for key in sorted(grouped.keys()):
        bucket = grouped[key]
        bucket["mean_fwd_ret_5"] = bucket["sum_fwd_ret_5"] / float(bucket["count"])
        out.append(bucket)
    return out


def false_decision_counts(signal_rows: list[dict[str, Any]], lane: str) -> dict[str, int]:
    counts = {"false_accumulate": 0, "false_hold": 0, "false_avoid": 0}
    for row in signal_rows:
        truth = row["truth_label_h5"]
        if truth is None:
            continue
        decision = row["primitive_decision"] if lane == "primitive_only" else row["memory_decision"]
        if decision == "Accumulate" and truth != "Accumulate":
            counts["false_accumulate"] += 1
        elif decision == "Hold" and truth != "Hold":
            counts["false_hold"] += 1
        elif decision == "Avoid" and truth != "Avoid":
            counts["false_avoid"] += 1
    return counts


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# DSF Clean Walk-Forward Replay With Symbol Memory V1",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- verdict: `{summary['final_verdict']}`",
        f"- replay_start_anchor_utc: `{summary['replay_start_anchor_utc']}`",
        f"- replay_calendar_start_utc: `{summary['replay_calendar_start_utc']}`",
        f"- replay_calendar_end_utc: `{summary['replay_calendar_end_utc']}`",
        f"- kept_symbols: `{summary['kept_symbol_count']}`",
        f"- excluded_symbols: `{summary['excluded_symbol_count']}`",
        f"- slippage_bps_per_trade: `{summary['slippage_bps_per_trade']}`",
        "",
        "## Lane Metrics",
        "",
    ]
    for lane in ["primitive_only", "primitive_plus_symbol_memory", "spy_buy_and_hold", "equal_weight_same_tradable_universe"]:
        metrics = summary["lanes"][lane]["metrics"]
        lines.extend(
            [
                f"### {lane}",
                f"- final_account_value: `{metrics['final_account_value']}`",
                f"- total_return: `{metrics['total_return']}`",
                f"- cagr: `{metrics['cagr']}`",
                f"- max_drawdown: `{metrics['max_drawdown']}`",
                f"- volatility: `{metrics['volatility']}`",
                f"- turnover: `{metrics['turnover']}`",
                f"- trade_count: `{metrics['trade_count']}`",
                f"- average_holding_period_days: `{metrics['average_holding_period_days']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Ablation",
            "",
            f"- return_improved: `{summary['ablation']['return_improved']}`",
            f"- drawdown_improved: `{summary['ablation']['drawdown_improved']}`",
            f"- false_accumulate_delta: `{summary['ablation']['false_accumulate_delta']}`",
            f"- false_hold_delta: `{summary['ablation']['false_hold_delta']}`",
            f"- false_avoid_delta: `{summary['ablation']['false_avoid_delta']}`",
            "",
        ]
    )
    return "\n".join(lines)


def notify_slack(message: str) -> None:
    if not SLACK_SCRIPT.exists():
        return
    subprocess.run([str(SLACK_SCRIPT), message], cwd=str(REPO_ROOT), check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean vendor-direct walk-forward DSF replay with symbol memory v1.")
    parser.add_argument("--max-symbols", type=int, default=None)
    parser.add_argument("--fetch-workers", type=int, default=8)
    args = parser.parse_args()

    stamp = utc_stamp()
    generated_at = utc_now_iso()

    universe_symbols = load_universe_symbols(args.max_symbols)
    full_calendar, replay_calendar, warmup_start, replay_anchor = compute_replay_calendar()
    replay_end = replay_calendar[-1]

    spy_adjusted = fetch_symbol_bars("SPY", warmup_start - timedelta(days=7), replay_end, adjusted=True)
    spy_adjusted_map = bar_map(spy_adjusted)
    if any(day not in spy_adjusted_map for day in replay_calendar):
        raise RuntimeError("SPY adjusted benchmark bars do not cover replay calendar")

    fetch_start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    fetch_end = replay_end

    def _fetch_symbol(symbol: str) -> tuple[str, Any]:
        try:
            raw_bars = fetch_symbol_bars(symbol, fetch_start, fetch_end, adjusted=False)
            adjusted_bars = fetch_symbol_bars(symbol, fetch_start, fetch_end, adjusted=True)
            return symbol, (raw_bars, adjusted_bars)
        except Exception as exc:
            return symbol, exc

    fetched: dict[str, tuple[list[Bar], list[Bar]]] = {}
    excluded_reasons: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(args.fetch_workers))) as pool:
        futures = [pool.submit(_fetch_symbol, symbol) for symbol in universe_symbols]
        for idx, future in enumerate(as_completed(futures), start=1):
            symbol, result = future.result()
            if isinstance(result, Exception):
                excluded_reasons[symbol] = f"vendor_fetch_failed: {result}"
            else:
                fetched[symbol] = result
            if idx % 100 == 0 or idx == len(universe_symbols):
                print(f"[fetch] {idx}/{len(universe_symbols)}")

    kept_symbols: list[str] = []
    adjusted_maps: dict[str, dict[datetime, Bar]] = {}
    aligned_symbols: dict[str, SymbolReplayData] = {}
    required_calendar = list(full_calendar)

    for symbol in universe_symbols:
        if symbol not in fetched:
            continue
        raw_bars, adjusted_bars = fetched[symbol]
        try:
            aligned = align_symbol_to_calendar(symbol, raw_bars, adjusted_bars, required_calendar)
        except Exception as exc:
            excluded_reasons[symbol] = str(exc)
            continue
        aligned_symbols[symbol] = aligned
        adjusted_maps[symbol] = bar_map(aligned.adjusted_bars)
        kept_symbols.append(symbol)

    if not kept_symbols:
        notify_slack("Codex blocked: clean DSF walk-forward replay has no replay-kept symbols after strict vendor alignment.")
        raise RuntimeError("clean replay blocked by missing vendor-direct history / rebuild path")

    symbol_memory_cards: list[dict[str, Any]] = []
    signal_rows: list[dict[str, Any]] = []
    signal_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    rebuilt_symbols: list[str] = []
    for idx, symbol in enumerate(kept_symbols, start=1):
        try:
            built = build_symbol_replay(aligned_symbols[symbol])
        except Exception as exc:
            excluded_reasons[symbol] = f"rebuild_failed: {exc}"
            continue
        symbol_memory_cards.append(built["memory_card"])
        rebuilt_symbols.append(symbol)
        for row in built["signal_rows"]:
            signal_rows.append(row)
            signal_map[row["signal_date_utc"]][symbol] = row
        if idx % 100 == 0 or idx == len(kept_symbols):
            print(f"[rebuild] {idx}/{len(kept_symbols)}")

    kept_symbols = rebuilt_symbols
    adjusted_maps = {symbol: adjusted_maps[symbol] for symbol in kept_symbols}
    if not kept_symbols:
        notify_slack("Codex blocked: clean DSF walk-forward replay lost all symbols during strict rebuild.")
        raise RuntimeError("clean replay blocked by missing vendor-direct history / rebuild path")

    primitive_lane = run_active_lane("primitive_decision", required_calendar, signal_map, adjusted_maps)
    memory_lane = run_active_lane("memory_decision", required_calendar, signal_map, adjusted_maps)
    spy_lane = run_spy_benchmark(required_calendar, spy_adjusted)
    universe_lane = run_equal_weight_universe_benchmark(required_calendar, kept_symbols, adjusted_maps)

    false_primitive = false_decision_counts(signal_rows, "primitive_only")
    false_memory = false_decision_counts(signal_rows, "primitive_plus_symbol_memory")
    geometry_table = geometry_contribution_table(signal_rows)

    ablation = {
        "primitive_only_final_account_value": primitive_lane["metrics"]["final_account_value"],
        "primitive_plus_symbol_memory_final_account_value": memory_lane["metrics"]["final_account_value"],
        "return_improved": memory_lane["metrics"]["total_return"] > primitive_lane["metrics"]["total_return"],
        "drawdown_improved": memory_lane["metrics"]["max_drawdown"] > primitive_lane["metrics"]["max_drawdown"],
        "false_accumulate_delta": false_memory["false_accumulate"] - false_primitive["false_accumulate"],
        "false_hold_delta": false_memory["false_hold"] - false_primitive["false_hold"],
        "false_avoid_delta": false_memory["false_avoid"] - false_primitive["false_avoid"],
        "primitive_only_false_counts": false_primitive,
        "primitive_plus_symbol_memory_false_counts": false_memory,
    }

    final_verdict = (
        "clean replay built; symbol_memory_v1 improves DSF"
        if ablation["return_improved"] or ablation["drawdown_improved"]
        else "clean replay built; symbol_memory_v1 does not improve DSF"
    )

    summary = {
        "generated_at_utc": generated_at,
        "note_path": str(NOTE_PATH),
        "snapshot_csv": str(SNAPSHOT_CSV),
        "archive_db": str(ARCHIVE_DB),
        "primitive_runner": str(PRIMITIVE_RUNNER),
        "replay_start_anchor_utc": replay_anchor.isoformat().replace("+00:00", "Z"),
        "replay_calendar_start_utc": replay_calendar[0].isoformat().replace("+00:00", "Z"),
        "replay_calendar_end_utc": replay_calendar[-1].isoformat().replace("+00:00", "Z"),
        "slippage_bps_per_trade": SLIPPAGE_BPS_PER_TRADE,
        "kept_symbol_count": len(kept_symbols),
        "excluded_symbol_count": len(excluded_reasons),
        "lanes": {
            "primitive_only": {"metrics": primitive_lane["metrics"]},
            "primitive_plus_symbol_memory": {"metrics": memory_lane["metrics"]},
            "spy_buy_and_hold": {"metrics": spy_lane["metrics"]},
            "equal_weight_same_tradable_universe": {"metrics": universe_lane["metrics"]},
        },
        "required_diagnostics": {
            "symbol_memory_v1_improved_return": ablation["return_improved"],
            "symbol_memory_v1_improved_drawdown": ablation["drawdown_improved"],
            "symbol_memory_v1_mostly_reduced_false_accumulate": ablation["false_accumulate_delta"] < 0,
            "symbol_memory_v1_mostly_reduced_false_hold": ablation["false_hold_delta"] < 0,
            "symbol_memory_v1_mostly_reduced_false_avoid": ablation["false_avoid_delta"] < 0,
        },
        "ablation": ablation,
        "final_verdict": final_verdict,
    }

    summary_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_summary_{stamp}.json"
    summary_md = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_summary_{stamp}.md"
    equity_csv = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_equity_{stamp}.csv"
    equity_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_equity_{stamp}.json"
    trades_csv = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_trades_{stamp}.csv"
    trades_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_trades_{stamp}.json"
    memory_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_memory_{stamp}.json"
    geometry_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_geometry_{stamp}.json"
    ablation_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_ablation_{stamp}.json"
    excluded_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_excluded_{stamp}.json"
    monthly_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_monthly_{stamp}.json"
    annual_json = RUNTIME_ROOT / f"dsf_clean_walkforward_replay_with_symbol_memory_v1_annual_{stamp}.json"

    equity_rows = primitive_lane["equity_rows"] + memory_lane["equity_rows"] + spy_lane["equity_rows"] + universe_lane["equity_rows"]
    trade_rows = primitive_lane["trade_rows"] + memory_lane["trade_rows"]
    monthly = {
        "primitive_only": primitive_lane["monthly_returns"],
        "primitive_plus_symbol_memory": memory_lane["monthly_returns"],
        "spy_buy_and_hold": spy_lane["monthly_returns"],
        "equal_weight_same_tradable_universe": universe_lane["monthly_returns"],
    }
    annual = {
        "primitive_only": primitive_lane["annual_returns"],
        "primitive_plus_symbol_memory": memory_lane["annual_returns"],
        "spy_buy_and_hold": spy_lane["annual_returns"],
        "equal_weight_same_tradable_universe": universe_lane["annual_returns"],
    }

    summary.update(
        {
            "summary_json": str(summary_json),
            "summary_md": str(summary_md),
            "equity_curve_csv": str(equity_csv),
            "equity_curve_json": str(equity_json),
            "trade_log_csv": str(trades_csv),
            "trade_log_json": str(trades_json),
            "symbol_memory_v1_json": str(memory_json),
            "geometry_contribution_json": str(geometry_json),
            "ablation_json": str(ablation_json),
            "excluded_symbols_json": str(excluded_json),
            "monthly_returns_json": str(monthly_json),
            "annual_returns_json": str(annual_json),
        }
    )

    _json_dump(summary_json, summary)
    summary_md.write_text(markdown_summary(summary), encoding="utf-8")
    _csv_dump(equity_csv, equity_rows)
    _json_dump(equity_json, equity_rows)
    _csv_dump(trades_csv, trade_rows)
    _json_dump(trades_json, trade_rows)
    _json_dump(memory_json, symbol_memory_cards)
    _json_dump(geometry_json, geometry_table)
    _json_dump(ablation_json, ablation)
    _json_dump(excluded_json, excluded_reasons)
    _json_dump(monthly_json, monthly)
    _json_dump(annual_json, annual)

    notify_slack(f"Codex completed clean DSF walk-forward replay with symbol_memory_v1. Verdict: {final_verdict}.")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
