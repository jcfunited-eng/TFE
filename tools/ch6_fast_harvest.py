"""CH6 fast-harvest paper channel.

CH6 owns its book and entry scan. Its reduced entry projection requires a
completed daily up-spike of at least 8%, volume at least three times the prior
20-session mean, price at least $5, and an explicit same-day ``gband=0`` herd
reading. Missing herd coverage is unknown and is refused.

An open short is anomaly-cut at the first observed mark 20% or more against
entry. A winner arms at +5%, tracks its best observed gain, and harvests after
giving back more than one percentage point. The end-of-day sweep harvests any
position still at +5% or better. The completed-close five-session backstop is
shared with CH3. Marks and daily gaps can cross trigger levels; 20% is a
trigger, not a guaranteed realized-loss ceiling.

After an anomaly cut, the refutation remains active until a later completed
daily close returns to or below the original entry. A cut symbol cannot be
shorted again on the same bar that refuted it.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENTRIES_HALT_FILE = ROOT / 'HALT_CH6_ENTRIES'  # Joseph protective halt 2026-08-18: file present = no new positions; exits unaffected
sys.path.insert(0, str(ROOT))

from tools.ch_short_refutation import has_unreset_refutation  # noqa: E402


ENGINE = "ch6_fast_harvest_v3"
EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
SLICE_USD = 2_000.0
MAX_NEW_PER_DAY = 10_000  # Joseph 2026-08-18: same buys as CH3 — the rules gate (ch_entry_reading) now guards entries, so the arbitrary cap that took WETO and missed SPAI on 08-14 is retired
START_DATE = "2026-08-07"
CASH0 = 100_000.0
HARVEST_PCT = 5.0
GIVEBACK_PP = 1.0
ANOMALY_STOP_PCT = 20.0
HOLD_SESSIONS = 5

STORE = ROOT / "ch4_live_store.parquet"
TAIL = ROOT / "ch3_supply_tail.parquet"
HERD = ROOT / "artifacts" / "ch4_uf" / "herd_state_live.parquet"
BOOK_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch6_book.json"


def load_book() -> dict[str, object]:
    if BOOK_PATH.exists():
        with BOOK_PATH.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("CH6 book must be one JSON object")
        book = raw
    else:
        book = {"engine": ENGINE, "cash": CASH0, "start": CASH0, "positions": {}, "closed": []}
    book.setdefault("positions", {})
    book.setdefault("closed", [])
    book.setdefault("cash", CASH0)
    book.setdefault("start", CASH0)
    book["engine"] = ENGINE
    return book


def save_book(book: dict[str, object]) -> None:
    book["engine"] = ENGINE
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    BOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = BOOK_PATH.with_suffix(BOOK_PATH.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(book, indent=1) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, BOOK_PATH)


def load_market() -> tuple[pd.DataFrame, list[pd.Timestamp], pd.Timestamp]:
    roster = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    roster["Date"] = pd.to_datetime(roster["Date"])
    days = [pd.Timestamp(day) for day in sorted(roster["Date"].unique())]
    if not days:
        raise RuntimeError("CH6 roster store has no completed daily bars")
    latest = days[-1]

    market = roster
    if TAIL.exists():
        tail = pd.read_parquet(TAIL, columns=["Date", "Symbol", "Close", "Volume"])
        tail["Date"] = pd.to_datetime(tail["Date"])
        refreshed = set(roster.loc[roster["Date"] == latest, "Symbol"])
        tail = tail[~tail["Symbol"].isin(refreshed) & (tail["Date"] <= latest)]
        market = pd.concat([roster[roster["Symbol"].isin(refreshed)], tail], ignore_index=True)
    return market, days, latest


def explicit_herd(latest: pd.Timestamp) -> dict[str, int]:
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    hday = int(latest.strftime("%Y%m%d"))
    state = {
        str(symbol): int(gband)
        for symbol, day, gband in zip(herd["sym"], herd["date"].astype(int), herd["gband"])
        if int(day) == hday
    }
    if not state:
        raise RuntimeError(f"CH6 herd state is not published for {latest.date()}")
    return state


def positions(book: dict[str, object]) -> dict[str, dict[str, object]]:
    raw = book.get("positions")
    if not isinstance(raw, dict):
        raise ValueError("CH6 positions must be one object")
    return raw  # type: ignore[return-value]


def closed(book: dict[str, object]) -> list[dict[str, object]]:
    raw = book.get("closed")
    if not isinstance(raw, list):
        raise ValueError("CH6 closed record must be one list")
    return raw  # type: ignore[return-value]


def close_position(
    book: dict[str, object],
    symbol: str,
    position: dict[str, object],
    price: float,
    reason: str,
    now: str,
) -> None:
    entry = float(position["entry_px"])
    side = int(position["side"])
    shares = int(position["shares"])
    result_pct = 100 * (price / entry - 1) * side
    pnl = round(shares * (price - entry) * side, 2)
    book["cash"] = round(float(book["cash"]) + float(position["notional"]) + pnl, 2)
    closed(book).append(
        {
            "symbol": symbol,
            "side": side,
            "shares": shares,
            "entry_px": entry,
            "exit_px": round(price, 4),
            "entry_date": position["entry_date"],
            "exit_at": now,
            "ret_pct": round(result_pct, 2),
            "pnl": pnl,
            "reason": reason,
            "peak_gain_pct": position.get("peak_gain_pct", 0.0),
        }
    )
    del positions(book)[symbol]
    print(f"  {reason} {symbol} @{price:.2f} ret {result_pct:+.2f}% pnl ${pnl:+,.2f}")


def settle_completed_closes(
    *,
    book: dict[str, object],
    market: pd.DataFrame,
    days: list[pd.Timestamp],
    latest: pd.Timestamp,
    now: str,
) -> int:
    day_index = {day.strftime("%Y-%m-%d"): index for index, day in enumerate(days)}
    latest_prices = dict(market.loc[market["Date"] == latest, ["Symbol", "Close"]].values)
    settled = 0
    for symbol in sorted(list(positions(book))):
        position = positions(book)[symbol]
        entry_index = day_index.get(str(position.get("entry_date", "")))
        price = latest_prices.get(symbol)
        if entry_index is None or price is None:
            continue
        age = len(days) - 1 - entry_index
        if age < 1:
            continue
        mark = float(price)
        gain = 100 * (mark / float(position["entry_px"]) - 1) * int(position["side"])
        if gain <= -ANOMALY_STOP_PCT:
            close_position(book, symbol, position, mark, "ANOMALY-CUT", now)
            settled += 1
        elif age >= HOLD_SESSIONS:
            close_position(book, symbol, position, mark, "TIME", now)
            settled += 1
    return settled


def qualifying_events(
    *,
    market: pd.DataFrame,
    days: list[pd.Timestamp],
    latest: pd.Timestamp,
    herd_state: dict[str, int],
    anomaly_cuts: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int, int]:
    recent = market[market["Date"].isin(days[-25:])]
    events: list[dict[str, object]] = []
    unknown_herd = 0
    active_refutations = 0
    latest_s = latest.strftime("%Y-%m-%d")

    for symbol, rows in recent.groupby("Symbol"):
        rows = rows.sort_values("Date")
        closes = rows["Close"].to_numpy(dtype=float)
        volumes = rows["Volume"].to_numpy(dtype=float)
        if len(closes) < 21 or pd.Timestamp(rows["Date"].iloc[-1]) != latest:
            continue
        if closes[-1] < PRICE_FLOOR or closes[-2] <= 0:
            continue
        gain = 100 * (closes[-1] / closes[-2] - 1)
        volume_mean = float(np.mean(volumes[-21:-1]))
        if gain < EVENT_GAIN or volume_mean <= 0 or volumes[-1] < VOL_MULT * volume_mean:
            continue

        gband = herd_state.get(str(symbol))
        if gband is None:
            unknown_herd += 1
            continue
        if gband != 0:
            continue
        if has_unreset_refutation(
            symbol=str(symbol),
            candidate_day=latest_s,
            anomaly_cuts=anomaly_cuts,
            history_days=rows["Date"].tolist(),
            history_closes=rows["Close"].tolist(),
        ):
            active_refutations += 1
            continue
        events.append(
            {
                "symbol": str(symbol),
                "gain": round(gain, 1),
                "close": float(closes[-1]),
                "dollar_vol": float(volumes[-1] * closes[-1]),
            }
        )
    events.sort(key=lambda event: -float(event["dollar_vol"]))
    return events, unknown_herd, active_refutations


def sync() -> None:
    raise SystemExit("ch6 sync is removed; CH6 owns its entry scan (use: hunt)")


def hunt(dry: bool = False) -> None:
    book = load_book()
    market, days, latest = load_market()
    latest_s = latest.strftime("%Y-%m-%d")
    if latest_s < START_DATE:
        print(f"[ch6 hunt] latest completed close {latest_s} precedes {START_DATE}")
        return

    now = datetime.now(timezone.utc).isoformat()
    settled = settle_completed_closes(book=book, market=market, days=days, latest=latest, now=now)
    if book.get("last_hunted") == latest_s:
        if settled and not dry:
            save_book(book)
        print(f"[ch6 hunt] {latest_s} already processed; settled {settled}; no duplicate entry")
        return

    try:
        herd_state = explicit_herd(latest)
    except RuntimeError as error:
        print(f"[ch6 hunt] {error}; settled {settled}; entries refused")
        if settled and not dry:
            save_book(book)
        return

    cuts = [trade for trade in closed(book) if str(trade.get("reason", "")).upper() == "ANOMALY-CUT"]
    events, unknown_herd, active_refutations = qualifying_events(
        market=market,
        days=days,
        latest=latest,
        herd_state=herd_state,
        anomaly_cuts=cuts,
    )

    if ENTRIES_HALT_FILE.exists():

        print('[ch6 hunt] ENTRIES HALTED (protective) — settlements only')

        events = []


    if events and not ENTRIES_HALT_FILE.exists():
        from ch_entry_reading import gate as _entry_gate
        _verdicts = _entry_gate([str(e["symbol"]) for e in events], "CH6")
        events = [e for e in events
                  if _verdicts.get(str(e["symbol"]), {}).get("verdict") == "ALLOW"]

    opened = 0
    for event in events:
        if opened >= MAX_NEW_PER_DAY:
            break
        symbol = str(event["symbol"])
        if symbol in positions(book) or float(book["cash"]) < SLICE_USD:
            continue
        shares = int(SLICE_USD // float(event["close"]))
        if shares < 1:
            continue
        notional = round(shares * round(float(event["close"]), 4), 2)
        if dry:
            print(f"  WOULD SHORT {shares} {symbol} @ {event['close']} (+{event['gain']}% day, explicit herd-low)")
            opened += 1
            continue
        book["cash"] = round(float(book["cash"]) - notional, 2)
        positions(book)[symbol] = {
            "engine": ENGINE,
            "entry_date": latest_s,
            "opened_at": now,
            "side": -1,
            "entry_px": round(float(event["close"]), 4),
            "shares": shares,
            "notional": notional,
            "armed": False,
            "peak_gain_pct": 0.0,
        }
        opened += 1
        print(f"  SHORT {shares} {symbol} @ {event['close']} (+{event['gain']}% day, explicit herd-low)")

    if not dry:
        book["last_hunted"] = latest_s
        book["last_hunt_custody"] = {
            "completed_close": latest_s,
            "eligible": len(events),
            "opened": opened,
            "settled": settled,
            "refused_unknown_herd": unknown_herd,
            "refused_unreset_refutation": active_refutations,
        }
        save_book(book)
    print(
        f"[ch6 hunt] {latest_s}: eligible {len(events)}, opened {opened}, settled {settled}, "
        f"refused unknown-herd {unknown_herd}, refused refutation {active_refutations}, "
        f"open {len(positions(book))}, cash ${float(book['cash']):,.2f}" + (" (DRY)" if dry else "")
    )


def evaluate_live_marks(action: str) -> None:
    from tools.ch3_shadow_hunter import last_price

    book = load_book()
    now = datetime.now(timezone.utc).isoformat()
    quote_failures: list[str] = []
    for symbol in sorted(list(positions(book))):
        position = positions(book)[symbol]
        try:
            price = float(last_price(symbol))
        except Exception as error:  # noqa: BLE001 - each missing mark is reported below
            quote_failures.append(f"{symbol}:{type(error).__name__}")
            continue
        if not np.isfinite(price) or price <= 0:
            quote_failures.append(f"{symbol}:invalid-mark")
            continue
        gain = 100 * (price / float(position["entry_px"]) - 1) * int(position["side"])
        if gain <= -ANOMALY_STOP_PCT:
            close_position(book, symbol, position, price, "ANOMALY-CUT", now)
            continue
        if action == "sweep":
            if gain >= HARVEST_PCT:
                close_position(book, symbol, position, price, "HARVEST", now)
            continue

        if gain > float(position.get("peak_gain_pct", 0.0)):
            position["peak_gain_pct"] = round(gain, 3)
        if not position.get("armed") and gain >= HARVEST_PCT:
            position["armed"] = True
            print(f"  ARMED {symbol} at {gain:+.2f}%")
        if position.get("armed") and float(position["peak_gain_pct"]) - gain > GIVEBACK_PP:
            close_position(book, symbol, position, price, "HARVEST", now)

    save_book(book)
    if quote_failures:
        print(f"[ch6 {action}] quote failures {len(quote_failures)}: {', '.join(quote_failures)}")
    armed = sum(1 for position in positions(book).values() if position.get("armed"))
    print(
        f"[ch6 {action}] open {len(positions(book))} armed {armed} "
        f"closed {len(closed(book))} cash ${float(book['cash']):,.2f}"
    )


def poll() -> None:
    evaluate_live_marks("poll")


def sweep() -> None:
    evaluate_live_marks("sweep")


COMMANDS: dict[str, Callable[[], None]] = {
    "hunt": hunt,
    "poll": poll,
    "sweep": sweep,
    "sync": sync,
}


if __name__ == "__main__":
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "poll"
    if command not in COMMANDS:
        raise SystemExit(f"unknown CH6 command: {command}")
    COMMANDS[command]()
