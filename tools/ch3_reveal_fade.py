"""CH3 reveal-fade shadow channel.

This is a paper-only L5 experiment. It does not evaluate the complete joint
field. The entry projection is deliberately named here: a completed daily
up-spike of at least 8%, volume at least three times the preceding 20-session
mean, price at least $5, and an explicit same-day herd reading of ``gband=0``.
Absence of a herd row is unknown and is refused; it is not evidence of calm.

Positions harvest at the first completed close at or below 95% of entry, are
anomaly-cut at the first completed close at or above 120% of entry, and have a
five-session time backstop. A completed-close trigger cannot cap an overnight
gap at 20%; the recorded exit remains the first observable completed close.

After an anomaly cut, the refutation remains active until a later completed
daily close returns to or below the original entry. The cut bar cannot be
immediately re-entered as a fresh short.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ch_short_refutation import has_unreset_refutation


ROOT = Path(__file__).resolve().parents[1]
_HERD_COVERAGE: set = set()
ENTRIES_HALT_FILE = ROOT / 'HALT_CH3_ENTRIES'  # Joseph protective halt 2026-08-18: file present = no new positions; exits unaffected
STORE = ROOT / "ch4_live_store.parquet"
TAIL = ROOT / "ch3_supply_tail.parquet"
HERD = ROOT / "artifacts" / "ch4_uf" / "herd_state_live.parquet"
LOG_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch3_shadow_log.json"

ENGINE = "ch3_reveal_fade_v4"
ENGINE_FAMILY = "ch3_reveal_fade"
EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
HOLD_SESSIONS = 5
CASH0 = 100_000.0
GROSS_MULT = 2.0
HARVEST_X = 0.95
MAX_EVENT_FRAC = 0.10
ANOMALY_STOP_PCT = 20.0


def load_log() -> dict[str, object]:
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("CH3 book must be one JSON object")
        log = raw
    else:
        log = {"finds": [], "days": {}}
    log.setdefault("finds", [])
    log.setdefault("days", {})
    log.setdefault("book", {"cash": CASH0, "start": CASH0})
    log["engine"] = ENGINE
    return log


def save_log(log: dict[str, object]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = LOG_PATH.with_suffix(LOG_PATH.suffix + ".tmp")
    body = json.dumps(log, indent=1) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, LOG_PATH)


def load_market() -> tuple[pd.DataFrame, np.ndarray, pd.Timestamp]:
    roster = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    roster["Date"] = pd.to_datetime(roster["Date"])
    days = np.array(sorted(roster["Date"].unique()))
    if not len(days):
        raise RuntimeError("CH3 roster store has no completed daily bars")
    latest = pd.Timestamp(days[-1])

    market = roster
    covered_universe = set(roster["Symbol"].unique())
    if TAIL.exists():
        tail = pd.read_parquet(TAIL, columns=["Date", "Symbol", "Close", "Volume"])
        tail["Date"] = pd.to_datetime(tail["Date"])
        refreshed = set(roster.loc[roster["Date"] == latest, "Symbol"])
        tail = tail[~tail["Symbol"].isin(refreshed) & (tail["Date"] <= latest)]
        market = pd.concat([roster[roster["Symbol"].isin(refreshed)], tail], ignore_index=True)
    market.attrs["covered_universe"] = covered_universe
    return market, days, latest


def herd_coverage_universe(sessions: int = 10) -> set:
    """Names the herd system has published in the recent window. A name
    outside this set is uncovered BY CONSTRUCTION (the herd system does
    not track it); a name inside it with a missing row today is a data
    gap and fails closed."""
    herd = pd.read_parquet(HERD, columns=["sym", "date"])
    recent = sorted(herd["date"].astype(int).unique())[-sessions:]
    return set(herd.loc[herd["date"].astype(int).isin(recent), "sym"].astype(str))


def explicit_low_herd(latest: pd.Timestamp) -> dict[str, int]:
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    hday = int(latest.strftime("%Y%m%d"))
    state = {
        str(symbol): int(gband)
        for symbol, day, gband in zip(herd["sym"], herd["date"].astype(int), herd["gband"])
        if int(day) == hday
    }
    if not state:
        raise RuntimeError(f"CH3 herd state is not published for {latest.date()}")
    return state


def settle_open_positions(
    *,
    log: dict[str, object],
    market: pd.DataFrame,
    days: np.ndarray,
    latest: pd.Timestamp,
    now: str,
) -> int:
    latest_s = latest.strftime("%Y-%m-%d")
    day_index = {pd.Timestamp(day).strftime("%Y-%m-%d"): index for index, day in enumerate(days)}
    latest_prices = dict(market.loc[market["Date"] == latest, ["Symbol", "Close"]].values)
    finds = log["finds"]
    book = log["book"]
    if not isinstance(finds, list) or not isinstance(book, dict):
        raise ValueError("CH3 book schema is invalid")

    settled = 0
    for finding in finds:
        if not isinstance(finding, dict):
            continue
        if finding.get("status") != "OPEN" or not str(finding.get("engine", "")).startswith(ENGINE_FAMILY):
            continue
        entry_index = day_index.get(str(finding.get("date", "")))
        latest_index = day_index.get(latest_s)
        if entry_index is None or latest_index is None or latest_index - entry_index < 1:
            continue
        raw_price = latest_prices.get(finding.get("symbol"))
        if raw_price is None:
            continue
        exit_price = float(raw_price)
        entry_price = float(finding["entry_px"])
        harvest = exit_price <= HARVEST_X * entry_price
        anomaly = exit_price >= (1 + ANOMALY_STOP_PCT / 100) * entry_price
        if not harvest and not anomaly and latest_index - entry_index < HOLD_SESSIONS:
            continue
        short_return = 100 * (1 - exit_price / entry_price)
        notional = float(finding["notional"])
        pnl = round(notional * short_return / 100, 2)
        book["cash"] = round(float(book["cash"]) + notional + pnl, 2)
        reason = "HARVEST" if harvest else ("ANOMALY-CUT" if anomaly else "TIME")
        finding.update(
            status=reason,
            resolved=now,
            ret_pct=round(short_return, 2),
            pnl=pnl,
            exit_px=exit_price,
        )
        settled += 1
    return settled


def candidate_events(
    *,
    market: pd.DataFrame,
    days: np.ndarray,
    latest: pd.Timestamp,
    herd_state: dict[str, int],
    anomaly_cuts: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int, int]:
    global _HERD_COVERAGE
    _HERD_COVERAGE = herd_coverage_universe()
    events: list[dict[str, object]] = []
    refused_unknown_herd = 0
    refused_refutation = 0
    recent = market[market["Date"].isin(days[-25:])]
    latest_s = latest.strftime("%Y-%m-%d")

    for symbol, rows in recent.groupby("Symbol"):
        rows = rows.sort_values("Date")
        closes = rows["Close"].to_numpy(dtype=float)
        volumes = rows["Volume"].to_numpy(dtype=float)
        if len(closes) < 22 or pd.Timestamp(rows["Date"].iloc[-1]) != latest:
            continue
        if closes[-1] < PRICE_FLOOR or closes[-2] <= 0:
            continue
        gain = 100 * (closes[-1] / closes[-2] - 1)
        normal_day_dollars = float(np.median(closes[-21:-1] * volumes[-21:-1]))
        volume_mean = float(np.mean(volumes[-21:-1]))
        if gain < EVENT_GAIN or volume_mean <= 0 or volumes[-1] < VOL_MULT * volume_mean:
            continue

        gband = herd_state.get(str(symbol))
        covered = str(symbol) in _HERD_COVERAGE
        if covered:
            # a covered name with no herd row is a DATA GAP: fail closed
            if gband is None:
                refused_unknown_herd += 1
                continue
            if gband != 0:
                continue
        elif gband is not None and gband != 0:
            continue
        # outside the covered universe: uncovered by construction — the
        # measured core supply (2026-08-13 restatement). Eligible.
        if has_unreset_refutation(
            symbol=str(symbol),
            candidate_day=latest_s,
            anomaly_cuts=anomaly_cuts,
            history_days=rows["Date"].tolist(),
            history_closes=rows["Close"].tolist(),
        ):
            refused_refutation += 1
            continue

        with np.errstate(divide="ignore", invalid="ignore"):
            log_returns = np.diff(np.log(np.maximum(closes, 1e-12)))
        noise = float(np.std(log_returns[-21:-1]))
        if noise <= 1e-9 or not np.isfinite(log_returns[-1]):
            continue
        displacement = float(abs(log_returns[-1]) / noise)
        events.append(
            {
                "symbol": str(symbol),
                "gain": round(gain, 1),
                "close": float(closes[-1]),
                "z": round(displacement, 2),
                "herd": "low",
                "normal_day_dollars": normal_day_dollars,
                "dollar_vol": float(volumes[-1] * closes[-1]),
            }
        )
    events.sort(key=lambda event: -float(event["dollar_vol"]))
    return events, refused_unknown_herd, refused_refutation


def main() -> None:
    dry = "DRY" in [argument.upper() for argument in sys.argv[1:]]
    now = datetime.now(timezone.utc).isoformat()
    market, days, latest = load_market()
    latest_s = latest.strftime("%Y-%m-%d")
    log = load_log()
    settled = settle_open_positions(log=log, market=market, days=days, latest=latest, now=now)

    try:
        herd_state = explicit_low_herd(latest)
    except RuntimeError as error:
        print(f"[reveal-fade] {error}; settled {settled}; entries refused")
        if not dry:
            save_log(log)
        return

    finds = log["finds"]
    book = log["book"]
    days_record = log["days"]
    if not isinstance(finds, list) or not isinstance(book, dict) or not isinstance(days_record, dict):
        raise ValueError("CH3 book schema is invalid")
    cuts = [finding for finding in finds if isinstance(finding, dict) and finding.get("status") == "ANOMALY-CUT"]
    events, refused_unknown, refused_refutation = candidate_events(
        market=market,
        days=days,
        latest=latest,
        herd_state=herd_state,
        anomaly_cuts=cuts,
    )

    held = {str(finding.get("symbol")) for finding in finds if isinstance(finding, dict) and finding.get("status") == "OPEN"}
    take = [event for event in events if str(event["symbol"]) not in held]
    if ENTRIES_HALT_FILE.exists():
        print("[reveal-fade] ENTRIES HALTED (protective) — settlements only")
        take = []
    if take:
        from ch_entry_reading import gate as _entry_gate
        _verdicts = _entry_gate([str(e["symbol"]) for e in take], "CH3")
        take = [e for e in take
                if _verdicts.get(str(e["symbol"]), {}).get("verdict") == "ALLOW"]
    floor_cash = -(GROSS_MULT - 1.0) * CASH0
    budget = max(0.0, float(book["cash"]) - floor_cash)
    zsum = sum(float(event["z"]) for event in take) or 1.0
    opened = 0
    for event in take:
        allocation = min(budget * float(event["z"]) / zsum, MAX_EVENT_FRAC * CASH0)
        # fillability (Joseph 2026-08-19): never exceed 1% of the name's
        # normal-day traded money — an order that cannot hide is fiction
        normal_day = float(event.get("normal_day_dollars", 0.0))
        if normal_day > 0:
            allocation = min(allocation, 0.01 * normal_day)
        shares = int(allocation // float(event["close"]))
        if shares < 1:
            continue
        notional = round(shares * round(float(event["close"]), 4), 2)
        if float(book["cash"]) - notional < floor_cash and not dry:
            continue
        if dry:
            print(
                f"  WOULD SHORT {shares} {event['symbol']} @ {event['close']} "
                f"(+{event['gain']}% day, z {event['z']}, explicit herd-low)"
            )
            opened += 1
            continue
        book["cash"] = round(float(book["cash"]) - notional, 2)
        finds.append(
            {
                "engine": ENGINE,
                "date": latest_s,
                "found_at": now,
                "symbol": event["symbol"],
                "side": -1,
                "entry_px": round(float(event["close"]), 4),
                "shares": shares,
                "target_pct": None,
                "target_px": None,
                "bound_pct": None,
                "notional": notional,
                "day_chg_pct": event["gain"],
                "z": event["z"],
                "catalyst": "REVEAL/herd-low-explicit",
                "status": "OPEN",
            }
        )
        held.add(str(event["symbol"]))
        opened += 1

    if not dry:
        resolved_today = [
            finding
            for finding in finds
            if isinstance(finding, dict)
            and str(finding.get("resolved", ""))[:10] == now[:10]
            and finding.get("status") in ("TIME", "HARVEST", "ANOMALY-CUT")
        ]
        wins = sum(1 for finding in resolved_today if float(finding.get("pnl", 0)) > 0)
        days_record[latest_s] = {
            "finds": opened,
            "hits": wins,
            "hit_rate_pct": round(100 * wins / len(resolved_today), 1) if resolved_today else None,
            "mean_ret_pct": round(float(np.mean([float(finding["ret_pct"]) for finding in resolved_today])), 2)
            if resolved_today
            else None,
            "pnl_usd": round(sum(float(finding.get("pnl", 0)) for finding in resolved_today), 2),
            "book_value": float(book["cash"])
            + sum(float(finding["notional"]) for finding in finds if isinstance(finding, dict) and finding.get("status") == "OPEN"),
            "refused_unknown_herd": refused_unknown,
            "refused_unreset_refutation": refused_refutation,
        }
        save_log(log)

    print(
        f"[reveal-fade] {latest_s}: eligible {len(events)}, opened {opened}, settled {settled}, "
        f"refused unknown-herd {refused_unknown}, refused refutation {refused_refutation}, "
        f"cash ${float(book['cash']):,.2f}" + (" (DRY)" if dry else "")
    )


if __name__ == "__main__":
    main()
