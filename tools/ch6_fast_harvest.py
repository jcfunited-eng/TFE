"""CH6 fast-harvest paper channel.

CH6 owns its book and entry scan. Its entry has two layers, and the page
must never claim more:
  1. a reduced event projection — completed daily up-spike of at least 8%,
     volume at least three times the prior 20-session mean, price at least
     $5, and an explicit same-day ``gband=0`` herd reading (missing herd
     coverage is unknown and is refused);
  2. the reading (tools/ch_entry_reading, laws_version v2-20260819) —
     every surviving candidate's whole life through the canonical v2
     chain, verdict by the laws in force (desk floor, fillability,
     suicide-pill ban, sound structure — Joseph's), full reading filed in
     docs/readings/. No structural entry law is in force: two candidates
     (the charging-vehicle conjunction, the extinction-presence law) were
     falsified on the filed decade record and retired. Rule 10 governs.

HOLDINGS GOVERNANCE: once per day at the first poll after the open, every
open position is re-read whole-life; a position refused by a structure law
in force (suicide-pill ban, sound structure) or that has become unreadable
is cut at the first available mark. A book does not hold what it cannot
read. Transient read errors never cut.

An open short is anomaly-cut at the first observed mark 20% or more against
entry. A winner arms at +5%, tracks its best observed gain, and harvests after
giving back more than one percentage point. The end-of-day sweep banks any
position at +2% or better (Joseph's fast-cash law, 2026-08-19). The
completed-close five-session backstop is shared with CH3. Marks and daily gaps can cross trigger levels; 20% is a
trigger, not a guaranteed realized-loss ceiling — the realized bound per
position is the slice times the worst overnight gap, not 20%.

After an anomaly cut, the refutation remains active until a later completed
daily close returns to or below the original entry. A cut symbol cannot be
shorted again on the same bar that refuted it.
"""

from __future__ import annotations

import fcntl
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

from tools.ch_desk import calendar_days, carry_costs  # noqa: E402
from tools.ch_short_refutation import has_unreset_refutation  # noqa: E402


ENGINE = "ch6_fast_harvest_v3"
EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
# Joseph 2026-08-20 (final): $2,500 is the highest you need to go —
# tiny per-name risk, wide spread, selection quality over size. Up to
# thirty entities a night as supply allows, capped by the fillability
# law (1% of normal-day money) and by cash.
SLICE_TARGET_USD = 2_500.0
MAX_ENTRIES_PER_NIGHT = 30
SLICE_FLOOR_USD = 2_000.0
START_DATE = "2026-08-07"
CASH0 = 100_000.0
HARVEST_PCT = 5.0   # intraday arm level (trail unchanged)
SWEEP_PCT = 2.0     # Joseph's fast-cash law: end-of-day bank at 2%+
                    # — switched ON per the filed coupled decision
                    # (ch6_fast_cash_laws.json): it pays when cash binds,
                    # and with dozens of positions working, cash binds.
                    
GIVEBACK_PP = 1.0
ANOMALY_STOP_PCT = 20.0
HOLD_SESSIONS = 5
# Joe 2026-09-23: the entry moves to the CLOSE of the spike day. Receipt in
# docs/CH6_ENTRY_TIMING_20260923.md — 111 of 122 live fills landed below
# the spike-day close (mean -1.06%, 15 of them 2%+ below) against a 2%
# bank; same exits, short at the decided close: +$2,790 vs -$534. The
# filed decade study (ch6_fast_cash_laws, close entry) pays +$31/+$39 per
# $2,500 at 74% W; the live next-morning book was break-even. The two
# rules this sets aside are Joseph's 08-20 "decide tonight, purchase
# tomorrow" and 08-21 "a stock on the rise is never entered". His word:
# "the rules ... are to help with trade and timing so if one of them
# blocks a sound strategy we don't have to enforce it."
# GRADE (declared before the first fill): 20 closed at-close entries.
# FAILS if average P&L per closed trade <= $0 or fewer than 60% bank ->
# ENTRY_AT_CLOSE goes back to False (next-morning staging returns).
# CONTROL: every at-close position records the next session's first mark
# and whether the old rule would have filled there (control_next_morning).
ENTRY_AT_CLOSE = True
CLOSE_ENTRY_STORE_MAX_LAG_SESSIONS = 5   # MINE: trailing volume, normal-day
                                          # money, herd and readings all come
                                          # from the store; older than this,
                                          # refuse the day loudly

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
    book.setdefault("save_seq", 0)
    book["engine"] = ENGINE
    return book


def save_book(book: dict[str, object]) -> None:
    """Persist the book — REFUSING stale lineages.

    2026-08-20 receipt: a writer holding a pre-open copy of the book
    saved it at 14:27 UTC, silently discarding the morning's fills,
    cuts and harvests; the next poll re-executed all of them at new
    prices (duplicate BULL/MRNA cuts, double fills of four stages).
    Guard: every save carries a monotonic save_seq. A writer whose
    loaded save_seq is older than the book now on disk lost the race
    long ago — its save is REFUSED and logged, never applied. The
    check and replace sit under an exclusive flock so two live
    writers serialize instead of interleaving one shared tmp file
    (the tmp is also pid-suffixed for the same reason)."""
    book["engine"] = ENGINE
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    BOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = BOOK_PATH.with_suffix(".lock")
    with lock_path.open("w") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
        disk_seq = 0
        if BOOK_PATH.exists():
            try:
                with BOOK_PATH.open("r", encoding="utf-8") as handle:
                    disk_seq = int(json.load(handle).get("save_seq", 0))
            except Exception:  # noqa: BLE001 — torn book: allow the write
                disk_seq = 0
        loaded_seq = int(book.get("save_seq", 0))
        if disk_seq > loaded_seq:
            print(f"[ch6 book] STALE WRITE REFUSED (pid {os.getpid()}): "
                  f"disk save_seq {disk_seq} > loaded {loaded_seq} — this "
                  "process holds an outdated lineage; its changes are NOT "
                  "saved. Reload the book and redo the work on fresh state.")
            return
        book["save_seq"] = disk_seq + 1
        temporary = BOOK_PATH.with_suffix(f"{BOOK_PATH.suffix}.tmp{os.getpid()}")
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


def herd_coverage_universe(sessions: int = 10) -> set:
    herd = pd.read_parquet(HERD, columns=["sym", "date"])
    recent = sorted(herd["date"].astype(int).unique())[-sessions:]
    return set(herd.loc[herd["date"].astype(int).isin(recent), "sym"].astype(str))


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
    _days = calendar_days(str(position.get("entry_date", now)), now)
    pnl = round(pnl - carry_costs(float(position.get("notional", 0.0)),
                                  float(position.get("normal_day_dollars", 0.0)),
                                  _days), 2)
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
            "entry_mode": position.get("entry_mode", "next_morning"),
            "control_next_morning": position.get("control_next_morning"),
        }
    )
    del positions(book)[symbol]
    print(f"  {reason} {symbol} @{price:.2f} ret {result_pct:+.2f}% pnl ${pnl:+,.2f}")


def _fall_never_began(symbol: str, entry_date: str, latest: str) -> bool:
    """True when the daily lanes show ZERO structural damage since
    entry — no channel death, no dead-channel reading — so the fall
    the reading claimed never started. Fail-open to False: a missing
    or stale lane never cuts anything."""
    try:
        lane = ROOT / "artifacts" / "ch4_uf" / "population_lanes" / f"{symbol}.parquet"
        lf = pd.read_parquet(lane, columns=["date", "URF", "extinction"])
        tail = lf[(lf["date"].astype(str) > entry_date)
                  & (lf["date"].astype(str) <= latest)]
        if len(tail) < 2:
            return False
        return (float(tail["extinction"].sum()) == 0
                and int((tail["URF"].astype(float) <= 0).sum()) == 0)
    except Exception:  # noqa: BLE001 — absent evidence never cuts
        return False


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
        latest_s = latest.strftime("%Y-%m-%d")
        pending = position.get("rules_cut_pending")
        # a pending cut may only settle at a completed close that
        # POSTDATES the decision — never at the prior session's price
        # (review defect 1: stale-price exits). The poll path executes
        # at live marks without this guard.
        if pending and latest_s >= str(position.get("rules_cut_marked",
                                                    "9999-12-31")):
            close_position(book, symbol, position, mark, str(pending), now)
            settled += 1
            continue
        gain = 100 * (mark / float(position["entry_px"]) - 1) * int(position["side"])
        if gain <= -ANOMALY_STOP_PCT:
            close_position(book, symbol, position, mark, "ANOMALY-CUT", now)
            settled += 1
        elif age >= 2 and gain <= 0 and _fall_never_began(symbol,
                str(position.get("entry_date", "")), latest_s):
            # QUIET-CUT (armed 2026-09-01, receipts 2026-08-28: cuts
            # losses ~20% per losing trade in BOTH halves of the year).
            # Two completed sessions with no structural damage arriving
            # and price at or above entry: the claimed fall never
            # began — the reading was wrong; take the small bill now
            # instead of day five's.
            close_position(book, symbol, position,
                           mark, "QUIET-CUT (fall never began)", now)
            settled += 1
        elif gain >= SWEEP_PCT:
            # the day-end sweep's backstop (2026-08-31 receipt: the
            # 3:55 sweep silently skipped 8 positions that finished
            # +2.2% to +3.6% — quotes missing at sweep time, no print).
            # Joseph's fast-cash law applied at the completed close:
            # any position whose close shows the bank-level gain banks
            # at that close, whether or not the live sweep saw it.
            close_position(book, symbol, position, mark, "HARVEST", now)
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
    herd_covered = herd_coverage_universe()
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
        normal_day_dollars = float(np.median(closes[-21:-1] * volumes[-21:-1]))
        volume_mean = float(np.mean(volumes[-21:-1]))
        if gain < EVENT_GAIN or volume_mean <= 0 or volumes[-1] < VOL_MULT * volume_mean:
            continue

        gband = herd_state.get(str(symbol))
        covered = str(symbol) in herd_covered
        if covered:
            if gband is None:
                unknown_herd += 1
                continue
            if gband != 0:
                continue
        elif gband is not None and gband != 0:
            continue
        # outside the covered universe: uncovered by construction — eligible
        _hist = rows
        if any(str(c.get("symbol", c.get("sym", ""))) == str(symbol) for c in anomaly_cuts):
            _hist = market[market["Symbol"] == symbol].sort_values("Date")
        if has_unreset_refutation(
            symbol=str(symbol),
            candidate_day=latest_s,
            anomaly_cuts=anomaly_cuts,
            history_days=_hist["Date"].tolist(),
            history_closes=_hist["Close"].tolist(),
        ):
            active_refutations += 1
            continue
        events.append(
            {
                "symbol": str(symbol),
                "gain": round(gain, 1),
                "normal_day_dollars": normal_day_dollars,
                "close": float(closes[-1]),
                "dollar_vol": float(volumes[-1] * closes[-1]),
            }
        )
    events.sort(key=lambda event: -float(event["dollar_vol"]))
    return events, unknown_herd, active_refutations


def close_entry_door(px, vol_today, prev_close, vol_mean20):
    """The engine's door read from the day so far (~15:50 ET), on the same
    three conditions qualifying_events applies to a completed close:
    gain >= EVENT_GAIN over the prior close, volume >= VOL_MULT x the
    trailing-20 mean, price >= PRICE_FLOOR. Returns the gain (percent) when
    the door opens, None when it does not or an input is unusable."""
    try:
        px = float(px)
        vol = float(vol_today)
        prev = float(prev_close)
        mean = float(vol_mean20)
    except (TypeError, ValueError):
        return None
    if not all(np.isfinite(x) for x in (px, vol, prev, mean)):
        return None
    if px < PRICE_FLOOR or prev <= 0 or mean <= 0:
        return None
    gain = 100 * (px / prev - 1)
    if gain < EVENT_GAIN or vol < VOL_MULT * mean:
        return None
    return gain


def _market_snapshot() -> dict:
    """ONE call for the whole market: every ticker's price now, volume so
    far today and prior close (Massive full-market snapshot; 13,247
    tickers in about a second on 2026-09-23)."""
    import urllib.request
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY", "")
    if not key:
        for line in open(ROOT / ".env"):
            if line.startswith("MASSIVE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise RuntimeError("no MASSIVE_API_KEY for the market snapshot")
    url = ("https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/"
           f"tickers?apiKey={key}")
    payload = json.load(urllib.request.urlopen(url, timeout=60))
    out: dict[str, dict] = {}
    for t in payload.get("tickers") or []:
        day = t.get("day") or {}
        mn = t.get("min") or {}
        prev = t.get("prevDay") or {}
        out[str(t.get("ticker", ""))] = {
            "px": float(mn.get("c") or day.get("c") or 0.0),
            "vol": float(day.get("v") or 0.0),
            "prev_close": float(prev.get("c") or 0.0),
        }
    return out


def _gate_and_rank(events: list) -> tuple[list, int, bool]:
    """The entry reading and Joseph's cherry-pick ranking, shared by the
    nightly hunt and the at-close entry. Returns (events, refused_by_reading,
    deferred). deferred=True means the readings are not current: the day's
    entry decision must NOT be concluded on them."""
    if not events:
        return events, 0, False
    from tools.ch_entry_reading import gate as _entry_gate
    _verdicts = _entry_gate([str(e["symbol"]) for e in events], "CH6")
    # the kernel readings lag the store for ~40 min after the
    # nightly close refresh; a transient STALE/ERROR judgment must
    # DEFER the day's entry decision, never conclude it — same
    # semantics as the herd-not-published path
    if any(v.get("structure_verdict") in ("STALE", "ERROR")
           for v in _verdicts.values()):
        return events, 0, True
    pre_reading = len(events)
    events = [e for e in events
              if _verdicts.get(str(e["symbol"]), {}).get("verdict") == "ALLOW"]
    refused_reading = pre_reading - len(events)
    if len(events) > 1:
        # Joseph's cherry-pick law 2026-08-19: harvests are not
        # equal — rank the night's candidates by their structure's
        # decade record, conservative half, dollars per 100 events;
        # tiebreak favors interior structures (no avoid cell within
        # one fact-step).
        _census = json.load(open(
            ROOT / "artifacts" / "ch6_harvest" /
            "ch6_structure_census.json"))
        _money = {e2["config"]: min(e2["derive"]["money_per_100ev"],
                                    e2["confirm"]["money_per_100ev"])
                  for e2 in _census["PAY_both_halves"]}
        _avoid = [a["config"].split()
                  for a in _census["AVOID_both_halves"]]

        def _interior(cfg: str) -> int:
            toks = cfg.split()
            return 0 if any(
                sum(1 for x, y in zip(toks, a) if x != y) == 1
                for a in _avoid) else 1

        def _rank(ev0: dict) -> tuple:
            cfg = str(_verdicts.get(str(ev0["symbol"]), {})
                      .get("structure", ""))
            return (_money.get(cfg, -1e9), _interior(cfg))

        events.sort(key=_rank, reverse=True)
        dropped = events[MAX_ENTRIES_PER_NIGHT:]
        events = events[:MAX_ENTRIES_PER_NIGHT]
        for ev0 in dropped:
            print(f"  RANKED OUT {ev0['symbol']}: weaker structure "
                  "than the day's best-ranked — cherry-pick law")
    return events, refused_reading, False


def hunt(dry: bool = False) -> None:
    book = load_book()
    stale_stages = list(book.get("staged_entries") or []) if ENTRY_AT_CLOSE else []
    if stale_stages:
        # one entry instant (Joe 2026-09-23): no next-morning fills. Stages
        # left from before the switch stayed "valid" because the store had
        # not advanced past their decision day (six filled on 2026-09-23 off
        # 09-18 decisions). Cleared here, loudly, before anything else.
        print(f"[ch6 hunt] clearing {len(stale_stages)} next-morning stage(s) "
              f"({', '.join(str(s.get('symbol')) for s in stale_stages)}) — "
              "entry is at the close now")
        book["staged_entries"] = []
        if not dry:
            save_book(book)
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

    cuts = [trade for trade in closed(book) if str(trade.get("reason", "")).upper().startswith("ANOMALY-CUT")]
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
    if ENTRY_AT_CLOSE and events:
        # one entry instant, not two: the spike day's events were already
        # decided at the close by hunt_at_close (Joe 2026-09-23); the
        # nightly pass stages nothing for the next morning
        print(f"[ch6 hunt] {len(events)} completed-close events noted; entry "
              "is at the close of the spike day now — nothing staged")
        events = []
    events, refused_reading, deferred = _gate_and_rank(events)
    if deferred:
        print("[ch6 hunt] kernel readings not current yet — entry "
              "decision deferred, no day stamp")
        if settled and not dry:
            save_book(book)
        return

    # Joseph 2026-08-20: decide on tonight's close, PURCHASE at the next
    # session's prints. Decisions stage here; fills happen at the first
    # live mark after the next open (poll path), at prices that actually
    # existed to be sold short. No cash moves at staging.
    opened = 0
    staged: list[dict] = []
    for event in events:
        symbol = str(event["symbol"])
        if symbol in positions(book):
            continue
        normal_day = float(event.get("normal_day_dollars", 0.0))
        # fail CLOSED on unknown liquidity: without a finite positive
        # normal-day figure the 1% law cannot be applied, so no entry
        if not (np.isfinite(normal_day) and normal_day > 0):
            print(f"  REFUSE {symbol}: normal-day money unknown "
                  f"({normal_day!r}) — the fillability law cannot size it")
            continue
        if 0.01 * normal_day < SLICE_FLOOR_USD:
            print(f"  REFUSE {symbol}: 1% of its normal day "
                  f"(${normal_day:,.0f}) cannot absorb even the "
                  f"${SLICE_FLOOR_USD:,.0f} floor — unfillable")
            continue
        entry = {"symbol": symbol, "decided_date": latest_s,
                 "decided_close": round(float(event["close"]), 4),
                 "decided_at": now,
                 "normal_day_dollars": normal_day}
        if dry:
            print(f"  WOULD STAGE {symbol} @ close {event['close']} "
                  f"(+{event['gain']}% day) for the next session's open")
            opened += 1
            continue
        staged.append(entry)
        print(f"  STAGED {symbol} @ close {event['close']} "
              f"(+{event['gain']}% day) — fills at the next open")
        opened += 1
    if not dry:
        book["staged_entries"] = staged  # each night restates its own

    if not dry:
        book["last_hunted"] = latest_s
        book["last_hunt_custody"] = {
            "completed_close": latest_s,
            "eligible": len(events),
            "opened": opened,
            "settled": settled,
            "refused_unknown_herd": unknown_herd,
            "refused_unreset_refutation": active_refutations,
            "refused_by_reading": refused_reading,
        }
        save_book(book)
    print(
        f"[ch6 hunt] {latest_s}: eligible {len(events)}, opened {opened}, settled {settled}, "
        f"refused unknown-herd {unknown_herd}, refused refutation {active_refutations}, "
        f"open {len(positions(book))}, cash ${float(book['cash']):,.2f}" + (" (DRY)" if dry else "")
    )


def hunt_at_close(dry: bool = False) -> None:
    """Joe 2026-09-23: decide ~15:50 ET on the day so far, and be short at
    the close of the spike day — not the next morning after the overnight
    drop. Door, herd, refutation, reading gate, cherry-pick ranking, sizing
    and fillability law are the engine's own; only the instant moves. Runs
    once per session (book stamp); exits are untouched."""
    book = load_book()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    if book.get("last_close_entry") == today:
        print(f"[ch6 close-entry] {today} already run; no duplicate entry")
        return
    if ENTRIES_HALT_FILE.exists():
        print("[ch6 close-entry] ENTRIES HALTED (protective) — nothing opens")
        return
    market, days, latest = load_market()
    latest_s = latest.strftime("%Y-%m-%d")
    lag = len(pd.bdate_range(latest, pd.Timestamp(today))) - 1
    if lag > CLOSE_ENTRY_STORE_MAX_LAG_SESSIONS:
        print(f"[ch6 close-entry] store's last completed close is {latest_s}, "
              f"{lag} sessions old — trailing volume, normal-day money, herd "
              "and readings would be stale; REFUSED, no day stamp")
        return
    try:
        herd_state = explicit_herd(latest)
    except RuntimeError as error:
        print(f"[ch6 close-entry] {error}; entries refused")
        return
    try:
        snap = _market_snapshot()
    except Exception as error:  # noqa: BLE001 — loud; the window retries once
        print(f"[ch6 close-entry] market snapshot failed "
              f"({type(error).__name__}: {error}) — nothing opens, no day stamp")
        return

    recent = market[market["Date"].isin(days[-21:])]
    cuts = [trade for trade in closed(book)
            if str(trade.get("reason", "")).upper().startswith("ANOMALY-CUT")]
    herd_covered = herd_coverage_universe()
    events: list[dict] = []
    screened = unknown_herd = active_refutations = 0
    for symbol, rows in recent.groupby("Symbol"):
        rows = rows.sort_values("Date")
        if len(rows) < 20 or pd.Timestamp(rows["Date"].iloc[-1]) != latest:
            continue
        s = snap.get(str(symbol))
        if not s:
            continue
        closes = rows["Close"].to_numpy(dtype=float)
        volumes = rows["Volume"].to_numpy(dtype=float)
        # the prior close comes from the feed (yesterday's actual close); the
        # store's last close stands in only when the feed has none
        prev_close = s["prev_close"] if s["prev_close"] > 0 else float(closes[-1])
        gain = close_entry_door(s["px"], s["vol"], prev_close, float(np.mean(volumes[-20:])))
        if gain is None:
            continue
        screened += 1
        gband = herd_state.get(str(symbol))
        covered = str(symbol) in herd_covered
        if covered:
            if gband is None:
                unknown_herd += 1
                continue
            if gband != 0:
                continue
        elif gband is not None and gband != 0:
            continue
        _hist = rows
        if any(str(c.get("symbol", c.get("sym", ""))) == str(symbol) for c in cuts):
            _hist = market[market["Symbol"] == symbol].sort_values("Date")
        if has_unreset_refutation(
            symbol=str(symbol),
            candidate_day=today,
            anomaly_cuts=cuts,
            history_days=_hist["Date"].tolist(),
            history_closes=_hist["Close"].tolist(),
        ):
            active_refutations += 1
            continue
        events.append({
            "symbol": str(symbol),
            "gain": round(gain, 1),
            "normal_day_dollars": float(np.median(closes[-20:] * volumes[-20:])),
            "close": float(s["px"]),
            "dollar_vol": float(s["vol"] * s["px"]),
        })
    events.sort(key=lambda event: -float(event["dollar_vol"]))

    events, refused_reading, deferred = _gate_and_rank(events)
    if deferred:
        print("[ch6 close-entry] kernel readings not current — entry decision "
              "deferred, no day stamp")
        return

    opened = 0
    for event in events:
        symbol = str(event["symbol"])
        if symbol in positions(book):
            continue
        normal_day = float(event.get("normal_day_dollars", 0.0))
        if not (np.isfinite(normal_day) and normal_day > 0):
            print(f"  REFUSE {symbol}: normal-day money unknown "
                  f"({normal_day!r}) — the fillability law cannot size it")
            continue
        if 0.01 * normal_day < SLICE_FLOOR_USD:
            print(f"  REFUSE {symbol}: 1% of its normal day "
                  f"(${normal_day:,.0f}) cannot absorb even the "
                  f"${SLICE_FLOOR_USD:,.0f} floor — unfillable")
            continue
        price = float(event["close"])
        slice_usd = min(SLICE_TARGET_USD, float(book["cash"]), 0.01 * normal_day)
        if slice_usd < SLICE_FLOOR_USD:
            print(f"  REFUSE {symbol}: cash or fillability below the floor")
            continue
        shares = int(slice_usd // price)
        if shares < 1:
            print(f"  REFUSE {symbol}: price ${price:.2f} exceeds the slice")
            continue
        if dry:
            print(f"  WOULD FILL SHORT {shares} {symbol} @ {price:.4f} at the close "
                  f"(+{event['gain']}% day)")
            opened += 1
            continue
        notional = round(shares * round(price, 4), 2)
        book["cash"] = round(float(book["cash"]) - notional, 2)
        positions(book)[symbol] = {
            "engine": ENGINE, "entry_date": today, "opened_at": now,
            "side": -1, "entry_px": round(price, 4), "shares": shares,
            "notional": notional, "armed": False, "peak_gain_pct": 0.0,
            "decided_date": today, "decided_close": round(price, 4),
            "normal_day_dollars": normal_day,
            "entry_mode": "at_close", "control_next_morning": None,
        }
        print(f"  FILLED SHORT {shares} {symbol} @ {price:.4f} AT THE CLOSE "
              f"(+{event['gain']}% day)")
        opened += 1

    if not dry:
        book["last_close_entry"] = today
        book["last_close_entry_custody"] = {
            "session": today, "store_close": latest_s, "screened": screened,
            "eligible": len(events), "opened": opened,
            "refused_unknown_herd": unknown_herd,
            "refused_unreset_refutation": active_refutations,
            "refused_by_reading": refused_reading,
        }
        save_book(book)
    print(f"[ch6 close-entry] {today}: door {screened}, eligible {len(events)}, "
          f"opened {opened}, refused unknown-herd {unknown_herd}, refutation "
          f"{active_refutations}, reading {refused_reading}, open "
          f"{len(positions(book))}, cash ${float(book['cash']):,.2f}"
          + (" (DRY)" if dry else ""))


def govern(book: dict[str, object]) -> tuple[int, bool]:
    """Daily holdings governance from the nightly store — no downloads,
    no chain replay. The two laws that can cut a HELD position
    (suicide-pill ban, sound structure — Joseph's) need only completed
    daily closes, which are already on disk. The whole-life fine
    reading runs once, at entry, where the money decision is made.
    Marks refusals for cut at the next available mark (poll executes
    at live quotes; settle only at a close that postdates the mark);
    files the facts sheet. Returns (marked, clean)."""
    from tools.ch_entry_reading import READINGS_DIR, _file_sheet

    symbols = sorted(positions(book))
    if not symbols:
        return 0, True
    market, days, latest = load_market()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sheet: dict[str, dict] = {}
    marked = 0
    for symbol in symbols:
        position = positions(book)[symbol]
        rows = market[market["Symbol"] == symbol].sort_values("Date")
        closes = rows["Close"].to_numpy(dtype=float)
        if len(closes) < 2 or closes[-1] <= 0:
            print(f"  GOVERN {symbol}: no usable store history — kept, "
                  "reported")
            sheet[symbol] = {"symbol": symbol, "verdict": "UNPRICED",
                             "rule": "no usable store history"}
            continue
        life_years = (rows["Date"].iloc[-1] - rows["Date"].iloc[0]).days / 365.25
        peak = float(closes[:-1].max())
        price = float(closes[-1])
        crush = peak / price
        facts = {"life_years": round(life_years, 1), "price": round(price, 3),
                 "store_peak": round(peak, 2), "crush": round(crush, 1),
                 "as_of_close": str(rows["Date"].iloc[-1].date())}
        reason = None
        if crush >= 1000:
            reason = "RULES-CUT suicide-pill-ban"
        elif life_years >= 2 and price >= 0.5 * peak and crush < 4:
            reason = "RULES-CUT sound-structure"
        sheet[symbol] = {"symbol": symbol,
                         "verdict": "CUT" if reason else "HOLD",
                         "rule": reason or "no law in force refuses",
                         "facts": facts}
        if reason:
            if position.get("rules_cut_pending") != reason:
                position["rules_cut_pending"] = reason
                position["rules_cut_marked"] = today
                print(f"  GOVERN {symbol}: {reason} — cut at next available mark")
            marked += 1
        elif str(position.get("rules_cut_pending", "")).startswith(
                ("RULES-CUT suicide-pill-ban", "RULES-CUT sound-structure")):
            # govern may clear ONLY its own verdicts — a pending cut
            # ordered by Joseph or another law is never erased here
            # (Rule 11 finding D5)
            del position["rules_cut_pending"]
            position.pop("rules_cut_marked", None)
    READINGS_DIR.mkdir(parents=True, exist_ok=True)
    _file_sheet(READINGS_DIR / f"CH6_HOLDINGS_READING_{today}.json", sheet)
    return marked, True


def _live_marks(symbols: list) -> tuple[dict, list]:
    """Price every symbol or say so loudly: per-symbol snapshot first,
    then ONE batched latest-trade call for whatever the snapshot could
    not price (thin names often have no minute/day bar early in the
    session — the batched trade feed priced 32/32 premarket while the
    snapshot returned empty for two of them)."""
    from tools.ch3_shadow_hunter import last_price

    marks: dict[str, float] = {}
    retry: list[str] = []
    for symbol in symbols:
        try:
            price = float(last_price(symbol))
        except Exception:  # noqa: BLE001 — fall through to the batch
            retry.append(symbol)
            continue
        if np.isfinite(price) and price > 0:
            marks[symbol] = price
        else:
            retry.append(symbol)
    failures: list[str] = []
    if retry:
        try:
            from tools.ch_premarket_cut import latest_marks
            fallback = latest_marks(retry)
        except Exception as error:  # noqa: BLE001 — whole batch failed
            return marks, [f"{s}:{type(error).__name__}" for s in retry]
        for symbol in retry:
            price = fallback.get(symbol)
            if price and np.isfinite(price) and price > 0:
                marks[symbol] = float(price)
            else:
                failures.append(f"{symbol}:no-mark")
    return marks, failures


def _timestamped_marks(symbols: list) -> dict:
    """Fill marks must be prints from TODAY'S session — a fill law that
    says 'the next session's prints' cannot fill on premarket or
    prior-session prices (Rule 11 finding D3). Batched latest trades
    with timestamps; only trades at/after today's 13:30 UTC count."""
    if not symbols:
        return {}
    import urllib.request
    keys = {}
    for line in open(ROOT / ".env"):
        for name in ("ALPACA_API_KEY", "ALPACA_API_SECRET_KEY"):
            if line.startswith(f"{name}="):
                keys[name] = line.split("=", 1)[1].strip().strip('"')
    if len(keys) != 2:
        return {}
    session_open = datetime.now(timezone.utc).strftime("%Y-%m-%dT13:30:00Z")
    marks: dict[str, float] = {}
    wanted = sorted(set(str(s).upper() for s in symbols))
    for start in range(0, len(wanted), 100):
        chunk = wanted[start:start + 100]
        req = urllib.request.Request(
            "https://data.alpaca.markets/v2/stocks/trades/latest"
            f"?feed=iex&symbols={','.join(chunk)}",
            headers={"APCA-API-KEY-ID": keys["ALPACA_API_KEY"],
                     "APCA-API-SECRET-KEY": keys["ALPACA_API_SECRET_KEY"]})
        try:
            payload = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as error:  # noqa: BLE001 — loud, fills retry
            print(f"[ch6 fill] quote feed failed ({type(error).__name__}) "
                  "— staged fills retry next poll")
            return {}
        for sym, trade in (payload.get("trades") or {}).items():
            price = float(trade.get("p", 0.0))
            stamp = str(trade.get("t", ""))
            if price > 0 and stamp >= session_open:
                marks[sym] = price
    return marks


def evaluate_live_marks(action: str) -> None:
    book = load_book()
    now = datetime.now(timezone.utc).isoformat()
    staged = list(book.get("staged_entries") or [])
    quote_symbols = sorted(set(list(positions(book))
                               + [str(s["symbol"]) for s in staged]))
    marks, quote_failures = _live_marks(quote_symbols)

    # fills: decisions staged at a PRIOR session's close purchase here,
    # at the first live mark of the next session — prices that actually
    # existed (Joseph 2026-08-20: decide tonight, purchase tomorrow)
    if action == "poll" and staged and ENTRY_AT_CLOSE:
        # one entry instant (Joe 2026-09-23): the next-morning fill path is
        # closed. Anything still staged is dropped, loudly, never filled.
        print(f"[ch6 fill] {len(staged)} next-morning stage(s) dropped "
              f"({', '.join(str(s.get('symbol')) for s in staged)}) — entry "
              "is at the close now")
        book["staged_entries"] = []
        staged = []
    if action == "poll" and staged:
        remaining = []
        halted = ENTRIES_HALT_FILE.exists()
        if halted:
            print("[ch6 fill] ENTRIES HALTED (protective) — staged fills "
                  "held, nothing opens")
        # a stage is valid ONLY for the first session after its decision:
        # once the store carries a newer close, the reading is old news
        # and the stage expires (Rule 11 finding D4)
        store_latest = str(pd.read_parquet(
            STORE, columns=["Date"])["Date"].max())[:10]
        fill_marks = _timestamped_marks(
            [str(s["symbol"]) for s in staged]) if not halted else {}
        for entry in staged:
            symbol = str(entry["symbol"])
            if halted:
                remaining.append(entry)
                continue
            if str(entry.get("decided_date", "")) >= now[:10]:
                remaining.append(entry)  # never fill the decision session
                continue
            if str(entry.get("decided_date", "")) != store_latest:
                print(f"  STAGE EXPIRE {symbol}: decided "
                      f"{entry.get('decided_date')} is no longer the "
                      "latest close — the reading is stale")
                continue
            if symbol in positions(book):
                continue
            price = fill_marks.get(symbol)
            if price is None:
                remaining.append(entry)  # no in-session mark yet — retry
                continue
            # Joseph's rule 2026-08-21 ("the don't-be-an-idiot rule"):
            # a stock on the rise is never entered. A short is bought
            # only at or below the price it was picked at; above it,
            # the stage holds and retries — it fills only if the price
            # comes back down within its valid session, else expires.
            if price > float(entry["decided_close"]):
                print(f"  HOLD {symbol}: {price} above the picked price "
                      f"{entry['decided_close']} — rising stocks are "
                      "never entered (Joseph 2026-08-21)")
                remaining.append(entry)
                continue
            slice_usd = min(SLICE_TARGET_USD, float(book["cash"]),
                            0.01 * float(entry["normal_day_dollars"]))
            if slice_usd < SLICE_FLOOR_USD:
                # cash can free up later in the session (a harvest, a
                # cut) — held stages retry each poll and expire with
                # their session, exactly as the law text says
                print(f"  STAGE HELD {symbol}: cash or fillability below "
                      "the floor right now — retries this session")
                remaining.append(entry)
                continue
            shares = int(slice_usd // price)
            if shares < 1:
                print(f"  STAGE HELD {symbol}: price ${price:.2f} exceeds "
                      "the slice right now — retries this session")
                remaining.append(entry)
                continue
            notional = round(shares * round(price, 4), 2)
            book["cash"] = round(float(book["cash"]) - notional, 2)
            positions(book)[symbol] = {
                "engine": ENGINE, "entry_date": now[:10], "opened_at": now,
                "side": -1, "entry_px": round(price, 4), "shares": shares,
                "notional": notional, "armed": False, "peak_gain_pct": 0.0,
                "decided_date": str(entry["decided_date"]),
                "decided_close": float(entry["decided_close"]),
                "normal_day_dollars": float(entry["normal_day_dollars"]),
            }
            print(f"  FILLED SHORT {shares} {symbol} @ {price:.4f} "
                  f"(decided {entry['decided_date']} @ "
                  f"{entry['decided_close']})")
        book["staged_entries"] = remaining

    # CONTROL for the at-close entry (Joe 2026-09-23): on the next session,
    # record the first live mark and whether the old rule ("next morning, at
    # or below the decided close") would have filled there. Read only —
    # nothing trades on it. Filed into the closed record with the trade.
    if action == "poll":
        for symbol, position in positions(book).items():
            if (position.get("entry_mode") == "at_close"
                    and position.get("control_next_morning") is None
                    and str(position.get("entry_date", "")) < now[:10]):
                price = marks.get(symbol)
                if price is None:
                    continue
                decided = float(position["decided_close"])
                position["control_next_morning"] = {
                    "date": now[:10], "mark": round(float(price), 4),
                    "gap_pct": round(100 * (float(price) / decided - 1), 3),
                    "old_rule_would_fill": bool(price <= decided),
                }
                print(f"  CONTROL {symbol}: next-morning mark {price:.4f} vs "
                      f"close entry {decided:.4f} ({100 * (price / decided - 1):+.2f}%)")

    for symbol in sorted(list(positions(book))):
        position = positions(book)[symbol]
        price = marks.get(symbol)
        if price is None:
            # a skipped position must be LOUD (2026-08-31: the 3:55
            # sweep silently skipped 8 bankable winners on missing
            # quotes; the close-settle backstop now catches them, but
            # silence is never allowed to hide the miss again)
            print(f"  NO QUOTE {symbol}: unpriced this pass — skipped "
                  f"({action})")
            continue
        pending = position.get("rules_cut_pending")
        if pending:
            close_position(book, symbol, position, price, str(pending), now)
            continue
        gain = 100 * (price / float(position["entry_px"]) - 1) * int(position["side"])
        if gain <= -ANOMALY_STOP_PCT:
            close_position(book, symbol, position, price, "ANOMALY-CUT", now)
            continue
        if action == "sweep":
            if gain >= SWEEP_PCT:
                close_position(book, symbol, position, price, "HARVEST", now)
            continue

        if gain > float(position.get("peak_gain_pct", 0.0)):
            position["peak_gain_pct"] = round(gain, 3)
        if not position.get("armed") and gain >= HARVEST_PCT:
            position["armed"] = True
            print(f"  ARMED {symbol} at {gain:+.2f}%")
        if position.get("armed") and float(position["peak_gain_pct"]) - gain > GIVEBACK_PP:
            close_position(book, symbol, position, price, "HARVEST", now)

    # governance AFTER the mark checks: the first poll of the day must
    # never leave positions unwatched while whole-life reads grind;
    # cuts marked here execute at the next poll or completed close
    if action == "poll" and book.get("last_governed") != now[:10]:
        try:
            _marked, _clean = govern(book)
            if _clean:
                book["last_governed"] = now[:10]
        except Exception as error:  # noqa: BLE001 — loud; retried next poll
            print(f"[ch6 govern] READ PASS FAILED ({type(error).__name__}: "
                  f"{error}) — holdings ungoverned, retrying next poll")

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


def close_entry() -> None:
    hunt_at_close()


def close_entry_dry() -> None:
    hunt_at_close(dry=True)


COMMANDS: dict[str, Callable[[], None]] = {
    "hunt": hunt,
    "poll": poll,
    "sweep": sweep,
    "close_entry": close_entry,          # Joe 2026-09-23: short at the close of the spike day
    "close_entry_dry": close_entry_dry,  # same read, nothing opens, nothing stamped
}


if __name__ == "__main__":
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "poll"
    if command not in COMMANDS:
        raise SystemExit(f"unknown CH6 command: {command}")
    COMMANDS[command]()
