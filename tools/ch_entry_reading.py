"""
ch_entry_reading.py — the reading and the laws, layered honestly
=================================================================

Rebuilt 2026-08-19 (laws_version v2-20260819) after the review that
found the v1 gate was a fitted checklist wearing the kernel's name:
the chain ran, but the verdict came from threshold conjunctions tuned
to eight specimens — the exact flattening Rule 2 forbids.

WHAT RUNS (Rule 1): every candidate's whole life at 45-minute
resolution through the canonical v2 chain (tools/ch4_uf_kernel_v2).
The COMPLETE reading — desk facts plus the Rule-4 phase objects
(push, deaths, buzz, channel, crest) — is FILED with every verdict in
docs/readings/. The reading is the assessment; no law below claims to
summarize it (Rule 2).

LAWS IN FORCE (first refusal wins; provenance on every one):
  1. fail-closed          [custody]   no data, short life (< ~6 months
     of readings), or any error: the unreadable is never traded.
  2. desk floor           [Joseph's]  no-borrow class (thin name,
     violent pump), uptick restriction (fell 10%+ intraday),
     halt-prone tape (2+ violent reopens today).
  3. fillability          [Joseph's]  a $2k slice must hide inside 1%
     of the normal day's traded money.
  4. suicide-pill ban     [Joseph's, verbatim 2026-08-19] destroyed
     shell, lifetime peak >= 1000x today's price: never traded. Cost
     priced and accepted by Joseph (refuses occasional winners).
  5. sound structure      [Joseph's principle; constants on record]
     never short a sound company (life >= 2y, price >= half lifetime
     peak, crush < 4). Its decade cost/save replay is OWED and will
     be filed; the principle stands on Joseph's word meanwhile.
  ALLOW otherwise: Rule 10 governs — caps, cut line, session clock
     and the premarket pass are the protection; the reading rides
     along, filed, earning or losing authority on the record.

RETIRED LAWS (falsified on the filed record — never re-arm silently):
  - "charging vehicle" conjunction (v1: crush>=4 & floor clean &
    loading). FALSIFIED by artifacts/ch4_uf/ch3_vehicle_refusal.json:
    in the confirm half the refused class carried 291.3 fade/100ev vs
    138.7 kept — it refused the richest supply — while the kept class
    still held the worst event (-594%). False protection.
  - LAW E extinction-presence (declared+falsified 2026-08-19,
    artifacts/ch4_uf/ch6_extinction_presence_law.json): sign FLIPPED
    across the 2021/2022 boundary (derive: never-died +133.7 vs died
    -27.6; confirm: reversed). Does not enter force. The flip itself
    is an epoch observation, filed for Joseph.

Verdicts are filed once per symbol per day and shared by both
channels; only fail-closed (transient) readings are retried.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402

READINGS_DIR = ROOT / "docs" / "readings"
CACHE_DIR = ROOT / "artifacts" / "ch4_uf" / "entry_reading_cache"
LAWS_VERSION = "v3-20260819"
MIN_READINGS = 1100         # ~6 months of 9/day — else fail closed
FETCH_START = "2000-01-01"  # whole life: a peak before 2021 is still the peak


def _key() -> str:
    for ln in open(ROOT / ".env"):
        if ln.startswith("MASSIVE_API_KEY"):
            return ln.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("MASSIVE_API_KEY missing")


def _fetch(symbol: str, start: str, end: str, key: str) -> list:
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/45/minute/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    bars = []
    while url:
        d = json.load(urllib.request.urlopen(url, timeout=60))
        bars.extend(d.get("results", []))
        nxt = d.get("next_url")
        url = f"{nxt}&apiKey={key}" if nxt else None
        time.sleep(0.2)
    return bars


def _bars(symbol: str) -> list:
    """Whole-life bars, cached per symbol and topped up incrementally.
    Cache writes are atomic (tmp + replace) and an unreadable cache
    self-heals by refetching — a torn write must never fail-close a
    symbol forever."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache = CACHE_DIR / f"{symbol}.json"
    key = _key()
    bars = []
    if cache.exists():
        try:
            bars = json.load(open(cache))
        except Exception:  # noqa: BLE001 — torn cache: refetch, never wedge
            bars = []

    def _day(b: dict) -> str:
        return datetime.fromtimestamp(
            b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    dirty = False
    if bars:
        # Always rebuild the tail from the final cached DAY (a same-day
        # cache must not freeze the spike-day facts — review defect 4),
        # keeping only completed prior days; then verify the adjusted
        # price BASIS on an overlap bar before extending. A corporate
        # action (reverse split) re-bases the whole history at fetch
        # time; a cache stitched across bases silently erodes the
        # suicide-pill ban in exactly the class it exists for (review
        # defect 3). Basis mismatch -> discard cache, refetch the life.
        tail_day = _day(bars[-1])
        keep = [b for b in bars if _day(b) < tail_day]
        if keep:
            fetch_from = _day(keep[-1])
            fresh = _fetch(symbol, fetch_from, today, key)
            last_t = keep[-1]["t"]
            overlap = [b for b in fresh if b["t"] == last_t]
            same_basis = bool(overlap) and float(keep[-1]["c"]) > 0 and abs(
                float(overlap[0]["c"]) / float(keep[-1]["c"]) - 1) < 1e-6
            if same_basis:
                keep.extend(b for b in fresh if b["t"] > last_t)
                bars = keep
            else:
                bars = _fetch(symbol, FETCH_START, today, key)
        else:
            bars = _fetch(symbol, FETCH_START, today, key)
        dirty = True
    else:
        bars = _fetch(symbol, FETCH_START, today, key)
        dirty = True
    if dirty:
        tmp = cache.with_suffix(f".json.tmp{os.getpid()}")
        json.dump(bars, open(tmp, "w"))
        os.replace(tmp, cache)
    for stale in CACHE_DIR.glob(f"{symbol}_2*.json"):  # old per-day caches
        stale.unlink(missing_ok=True)
    return bars


def _refuse(symbol: str, law: str, provenance: str, rule: str,
            facts: dict | None = None) -> dict:
    out = {"symbol": symbol, "verdict": "REFUSE", "law": law,
           "provenance": provenance, "rule": rule,
           "laws_version": LAWS_VERSION}
    if facts is not None:
        out["facts"] = facts
    return out


def read_symbol(symbol: str, as_of: str | None = None) -> dict:
    """Whole-life reading + layered verdict. Fails closed on anything.

    The returned dict always carries the full facts (the reading) when
    the chain ran; `law` names which law in force decided a REFUSE.
    `as_of` (YYYY-MM-DD) truncates the life to that completed day — for
    receipts at a past decision instant, never for live verdicts.
    """
    try:
        bars = _bars(symbol)
        rows = []
        for b in bars:
            dt = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc)
            off = 4 if 3 < dt.month < 11 else 5
            et = dt - timedelta(hours=off)
            hm = et.hour * 60 + et.minute
            if 9 * 60 + 30 <= hm < 16 * 60 and et.weekday() < 5:
                day = et.strftime("%Y-%m-%d")
                if as_of is not None and day > as_of:
                    continue
                rows.append((dt, float(b["c"]), float(b["v"]), day))
        if len(rows) < MIN_READINGS:
            out = _refuse(symbol, "fail-closed", "custody",
                          f"insufficient life ({len(rows)} readings): "
                          "the unreadable is never traded")
            out["readings"] = len(rows)
            return out
        states = replay_symbol_v2(
            np.array([r[0] for r in rows]),
            np.array([r[1] for r in rows]),
            np.array([r[2] for r in rows]), warmup=60)
        c = np.array([r[1] for r in rows])
        R = np.array([s.URF if s is not None else np.nan for s in states])
        D = np.array([s.D_k if s is not None else 0 for s in states])
        REV = np.array([s.Rev_k if s is not None else 0 for s in states])
        ext = np.array([1 if (s is not None and s.extinction) else 0
                        for s in states])
        T = len(rows) - 1
        yrs = T / 2260
        peak = float(c[:T].max())
        crush = peak / c[T] if c[T] > 0 else 999999.0
        deaths_life = int(ext.sum())
        deaths_yr = float(deaths_life) / max(0.1, yrs)
        deaths_2wk = int(ext[T - 90:T].sum())
        deaths_prior_2wk = int(ext[T - 180:T - 90].sum())
        push_up = float((D[T - 45:T + 1] == 1).mean())
        # standing push: run length of the current D_k sign at T
        d_now = int(D[T])
        push_run = 0
        for i in range(T, -1, -1):
            if int(D[i]) == d_now:
                push_run += 1
            else:
                break
        rev_recent = int(REV[T - 45:T + 1].sum())
        W_alive = min(256, T - 60)
        alive = (R[T - W_alive + 1:T + 1] > 0).astype(float)
        b_health = float(alive.mean() * 2 - 1)
        day_closes: dict[str, float] = {}
        for i, r in enumerate(rows):
            day_closes[r[3]] = c[i]
        last6 = list(day_closes.values())[-6:]
        up_sessions = sum(1 for a, b2 in zip(last6, last6[1:]) if b2 > a)
        dw = D[T - 63:T + 1]
        lock = abs(int((dw == 1).sum()) - int((dw == -1).sum())) / max(
            1, int((dw == 1).sum()) + int((dw == -1).sum()))
        vv = np.array([r[2] for r in rows], dtype=float)
        dollar = c * vv
        day_dollar: dict[str, float] = {}
        for i, r in enumerate(rows):
            day_dollar[r[3]] = day_dollar.get(r[3], 0.0) + dollar[i]
        dvals = list(day_dollar.values())
        med20_dollar = float(np.median(dvals[-21:-1])) if len(dvals) >= 21 else 0.0

        day_list = sorted(day_dollar.keys())
        spike_gain = 0.0
        day_low_vs_prior = 1.0
        halt_jumps = 0
        crest_off_high = 0.0
        if len(day_list) >= 2:
            prior_day, spike_day = day_list[-2], day_list[-1]
            prior_close = None
            spike_prices = []
            for i, r in enumerate(rows):
                if r[3] == prior_day:
                    prior_close = c[i]
                elif r[3] == spike_day:
                    spike_prices.append(c[i])
            if prior_close and spike_prices:
                spike_gain = 100 * (spike_prices[-1] / prior_close - 1)
                day_low_vs_prior = min(spike_prices) / prior_close
                day_high = max(spike_prices)
                crest_off_high = 100 * (1 - spike_prices[-1] / day_high) \
                    if day_high > 0 else 0.0
                for a2, b2 in zip(spike_prices, spike_prices[1:]):
                    if a2 > 0 and abs(b2 / a2 - 1) >= 0.15:
                        halt_jumps += 1

        facts = {
            # desk facts
            "normal_day_dollars": round(med20_dollar),
            "life_years": round(yrs, 1), "price": round(float(c[T]), 3),
            "life_peak": round(peak, 2), "crush": round(crush, 1),
            "spike_gain_pct": round(spike_gain, 1),
            "halt_jumps": halt_jumps,
            # Rule-4 phase objects (the reading; no law below uses a
            # fitted boundary on these — they file, they do not veto)
            "push_now": d_now, "push_run": push_run,
            "push_up_week": round(push_up, 2),
            "up_sessions_of_5": up_sessions,
            "deaths_life": deaths_life,
            "deaths_per_year": round(deaths_yr),
            "deaths_2wk": deaths_2wk,
            "deaths_prior_2wk": deaths_prior_2wk,
            "buzz_rev_recent": rev_recent,
            "B_health": round(b_health, 2), "L_lock": round(lock, 2),
            "crest_off_high_pct": round(crest_off_high, 1),
        }

        # ---- laws in force, first refusal wins ----
        if med20_dollar < 500_000 and spike_gain >= 50:
            return _refuse(symbol, "desk-floor", "Joseph",
                           "no-borrow class (thin name, "
                           f"+{spike_gain:.0f}% pump): nothing to locate",
                           facts)
        if day_low_vs_prior <= 0.90:
            return _refuse(symbol, "desk-floor", "Joseph",
                           "uptick restriction active (fell 10%+ "
                           "intraday): fills degrade", facts)
        if halt_jumps >= 2:
            return _refuse(symbol, "desk-floor", "Joseph",
                           f"halt-prone ({halt_jumps} violent reopens "
                           "today): stops cannot protect", facts)
        if med20_dollar < 200_000:
            return _refuse(symbol, "fillability", "Joseph",
                           f"normal day trades ${med20_dollar:,.0f}; "
                           "a $2k slice cannot hide", facts)
        if med20_dollar >= 100_000_000:
            return _refuse(symbol, "poison-pill", "Joseph",
                           f"too big to pump (${med20_dollar/1e6:,.0f}M "
                           "normal day): a spike in a giant is repricing "
                           "on news, not a crowd pump — never a harvest "
                           "short (decade receipt: fade dead-to-negative "
                           "above $100M in both halves)", facts)
        if crush >= 1000:
            return _refuse(symbol, "suicide-pill-ban", "Joseph",
                           f"destroyed shell (lifetime peak {crush:,.0f}x "
                           "today's price): never traded", facts)
        if yrs >= 2 and c[T] >= 0.5 * peak and crush < 4:
            return _refuse(symbol, "sound-structure", "Joseph",
                           "sound structure, never a short "
                           "(cost replay owed, principle stands)", facts)
        return {"symbol": symbol, "verdict": "ALLOW",
                "law": "none-in-force",
                "provenance": "Rule 10",
                "rule": "no law in force refuses; caps, cut line, clock "
                        "and premarket pass govern; reading filed",
                "laws_version": LAWS_VERSION, "facts": facts}
    except Exception as err:  # noqa: BLE001 — fail closed, always
        return _refuse(symbol, "fail-closed", "custody",
                       f"{type(err).__name__}: {err}")


# laws whose refusal of a HELD position also cuts it (deterministic
# structure laws only — desk-floor/fillability describe the entry day's
# tape and do not govern an already-open position; transient fail-closed
# errors never cut anything)
HOLDING_CUT_LAWS = {"suicide-pill-ban", "sound-structure"}
UNREADABLE_RULE_PREFIX = "insufficient life"


def _todays_sheets(day: str) -> dict:
    """Verdicts already filed today by EITHER channel."""
    merged = {}
    for sheet in sorted(READINGS_DIR.glob(f"*_ENTRY_READINGS_{day}.json")):
        try:
            merged.update(json.load(open(sheet)))
        except Exception:  # noqa: BLE001 — a bad sheet never blocks reading
            continue
    return merged


def _file_sheet(sheet_path: Path, out: dict) -> None:
    existing = {}
    if sheet_path.exists():
        try:
            existing = json.load(open(sheet_path))
        except Exception:  # noqa: BLE001 — a corrupt sheet never blocks entries
            existing = {}
    existing.update(out)
    tmp = sheet_path.with_suffix(f".json.tmp{os.getpid()}")
    json.dump(existing, open(tmp, "w"), indent=1)
    os.replace(tmp, sheet_path)


_STRUCT_CACHE: dict = {}


def _structural_authority(symbol: str) -> tuple[str | None, str, str]:
    """The assessment INSIDE the decision (Joseph 2026-08-19: no entry
    the kernel hasn't read and judged). Returns (refusal_rule_or_None,
    structure_config, structure_verdict).

    - Outside the validated universe, or lane not current through the
      store's latest close: REFUSE — the engines do not trade what the
      perception cannot read. This is the pond every catastrophe came
      from (WETO, IPST, TNON, BULL, MRNA).
    - Joint structure in the census AVOID list (negative or tail-heavy
      in BOTH decade halves): REFUSE.
    - ONLY structures on the census PAYING list pass (Joseph: avoidance
      governs this channel; the undecided middle is avoided, not
      gambled). Everything else refuses.
    """
    import pandas as pd

    if not _STRUCT_CACHE:
        universe = pd.read_csv(
            ROOT / "artifacts" / "ch4_uf" / "population_universe_20260819.csv")
        census = json.load(open(
            ROOT / "artifacts" / "ch4_uf" / "ch4_joint_structure_census.json"))
        store = pd.read_parquet(
            ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol"])
        latest = store["Date"].max()
        _STRUCT_CACHE.update(
            universe=set(universe["Symbol"].astype(str)),
            pay={e["config"] for e in census["PAY_both_halves"]},
            avoid={e["config"] for e in census["AVOID_both_halves"]},
            store_latest=str(latest)[:10],
            store_latest_symbols=set(
                store.loc[store["Date"] == latest, "Symbol"].astype(str)))
    if symbol not in _STRUCT_CACHE["universe"]:
        return ("outside the readable universe: the perception has no "
                "lane here and the engines do not trade blind", "", "UNREAD")
    if symbol not in _STRUCT_CACHE["store_latest_symbols"]:
        # a lane can be written out-of-band; currency is only trusted
        # when the canonical store itself carries the entity today
        return ("no store row at the latest close: the canonical store "
                "does not carry this entity today", "", "STALE")
    lane_path = ROOT / "artifacts" / "ch4_uf" / "population_lanes" / f"{symbol}.parquet"
    if not lane_path.exists():
        return ("no perception lane on disk", "", "UNREAD")
    from tools.ch4_joint_structure_census import build_lane, facts_at
    lf = pd.read_parquet(lane_path)
    if str(lf["date"].iloc[-1]) != _STRUCT_CACHE["store_latest"]:
        return ("perception lane lags the store: no verdict on stale "
                "readings", "", "STALE")
    fx = facts_at(build_lane(lf), len(lf) - 1)
    if fx is None:
        return ("life too short for the joint structure", "", "UNREAD")
    cfg = " ".join(fx[k] for k in ("deaths", "slope", "channel", "push",
                                   "buzz", "strain", "lock", "depth"))
    if cfg in _STRUCT_CACHE["avoid"]:
        return (f"avoid structure [{cfg}] — negative or tail-heavy in "
                "both decade halves", cfg, "AVOID")
    if cfg not in _STRUCT_CACHE["pay"]:
        # Joseph 2026-08-19: avoidance governs this channel — the
        # harvest enters ONLY structures with the proven paying record;
        # the undecided middle is avoided, not gambled
        return (f"structure [{cfg}] has no proven paying record — "
                "avoided per the channel's governing law", cfg, "UNDECIDED")
    return (None, cfg, "PAY")


def gate(symbols: list, channel: str) -> dict:
    """Read every candidate, file the sheet, return {sym: verdict-dict}.
    Verdicts already filed today are reused; only fail-closed errors
    (transient by nature) are read again. Laws v3: the structural
    authority runs INSIDE the gate — desk laws first, then the
    perception's judgment; both must pass."""
    READINGS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    done = _todays_sheets(day)
    out = {}
    for s in symbols:
        s = str(s)
        prior = done.get(s)
        if prior and prior.get("laws_version") == LAWS_VERSION \
                and prior.get("law") != "fail-closed":
            out[s] = prior
            continue
        verdict = read_symbol(s)
        if verdict.get("verdict") == "ALLOW":
            try:
                refusal, cfg, struct = _structural_authority(s)
            except Exception as err:  # noqa: BLE001 — fail closed
                refusal, cfg, struct = (
                    f"structural authority unavailable "
                    f"({type(err).__name__}: {err})", "", "ERROR")
            verdict["structure"] = cfg
            verdict["structure_verdict"] = struct
            if refusal is not None:
                verdict["verdict"] = "REFUSE"
                # STALE and ERROR are TRANSIENT (readings lag the
                # store during the nightly pass; a mid-replace read
                # can fail) — filed as fail-closed so the same-day
                # reuse rule retries them. AVOID/UNDECIDED/UNREAD are
                # the day's real judgment and stay locked.
                verdict["law"] = ("fail-closed"
                                  if struct in ("STALE", "ERROR")
                                  else "structural-authority")
                verdict["provenance"] = ("custody"
                                         if struct in ("STALE", "ERROR")
                                         else "Joseph + decade census")
                verdict["rule"] = refusal
        out[s] = verdict
    _file_sheet(READINGS_DIR / f"{channel}_ENTRY_READINGS_{day}.json", out)
    for s, v in out.items():
        print(f"  [reading] {s}: {v['verdict']} — {v['rule']}")
    return out


def read_holdings(symbols: list, channel: str) -> dict:
    """Daily holdings governance reading: file the sheet, return
    {sym: verdict-dict}. A held position is cut by its engine when a
    law in HOLDING_CUT_LAWS refuses it, or when it is unreadable
    (deterministic insufficient-life — a book does not hold what it
    cannot read). Transient errors cut nothing and are reported."""
    READINGS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {str(s): read_symbol(str(s)) for s in symbols}
    _file_sheet(READINGS_DIR / f"{channel}_HOLDINGS_READING_{day}.json", out)
    for s, v in out.items():
        print(f"  [holding] {s}: {v['verdict']} — {v['rule']}")
    return out


def holding_cut_reason(verdict: dict) -> str | None:
    """Return the cut reason for a held position, or None to keep.
    Structure laws only — the unreadable (insufficient-life) case is
    governed by the engine's own two-day rule, because for a holding
    that once proved readable it can also be a data regression."""
    if verdict.get("verdict") != "REFUSE":
        return None
    law = str(verdict.get("law", ""))
    if law in HOLDING_CUT_LAWS:
        return f"RULES-CUT {law}"
    return None
