"""CH6 +2% intraday bank (Joseph 2026-10-06): "sell if over 2% (fast cash
grab) — it is not too early." A short that shows +2% during the day arms;
it banks when it falls back to max(+2%, best - 1 point). Shorts: side -1,
a price BELOW entry is a gain.

Run: python3 -m pytest tests/test_ch6_two_percent_bank.py -q
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools.ch6_fast_harvest as h  # noqa: E402


def _run(monkeypatch, path, peak=0.0, armed=False):
    """Feed one short (entry $100) a sequence of poll marks; return the
    close reason and gain, or None if still open."""
    today = datetime.now(timezone.utc).isoformat()[:10]
    book = {"cash": 0.0, "closed": [], "staged_entries": [], "last_governed": today,
            "positions": {"TST": {"side": -1, "entry_px": 100.0, "shares": 10,
                                   "notional": 1000.0, "armed": armed,
                                   "peak_gain_pct": peak, "entry_date": "2026-10-01"}}}
    closed = {}
    monkeypatch.setattr(h, "load_book", lambda: book)
    monkeypatch.setattr(h, "save_book", lambda b: None)
    def fake_close(b, sym, pos, price, reason, now):
        closed["r"] = (reason, round(100 * (1 - price / 100.0), 3))
        b["positions"].pop(sym)
    monkeypatch.setattr(h, "close_position", fake_close)
    for price in path:
        monkeypatch.setattr(h, "_live_marks", lambda syms, p=price: ({"TST": p}, []))
        h.evaluate_live_marks("poll")
        if closed:
            return closed["r"]
    return None


def test_touch_three_then_reverse_banks_at_two(monkeypatch):
    # +3% at noon, then the stock turns: banks at the +2% floor, not a cut
    r = _run(monkeypatch, [99.0, 97.0, 97.5, 98.0])
    assert r == ("HARVEST", 2.0)


def test_under_two_never_arms(monkeypatch):
    assert _run(monkeypatch, [99.0, 98.2, 99.5, 101.0]) is None


def test_big_run_still_trails_one_point(monkeypatch):
    # +6% best: holds through +5.5%, banks at +5% (best - 1 point)
    r = _run(monkeypatch, [97.0, 94.0, 94.5, 95.0])
    assert r == ("HARVEST", 5.0)


def test_old_peak_does_not_dump_a_position_now_below_two(monkeypatch):
    # recorded best +2.5% from before the change, unarmed, now +0.5%: holds
    assert _run(monkeypatch, [99.5], peak=2.5, armed=False) is None


def test_constants():
    assert h.SWEEP_PCT == 2.0 and h.GIVEBACK_PP == 1.0


# ── 2026-10-06 second fix: early cuts retired (replay receipt in the tool) ──
def test_early_cuts_retired():
    assert h.QUIET_CUT_ENABLED is False
    assert h.SOUND_STRUCTURE_HOLDING_CUT_ENABLED is False


def test_sound_structure_no_longer_cuts_a_held_short(monkeypatch, tmp_path):
    import pandas as pd
    import tools.ch_entry_reading as er
    dates = pd.date_range("2022-01-03", periods=900, freq="B")
    market = pd.DataFrame({"Date": dates, "Symbol": "TST", "Close": 100.0, "Volume": 1e6})
    book = {"positions": {"TST": {"side": -1, "entry_px": 100.0}}}
    monkeypatch.setattr(h, "load_market", lambda: (market, list(dates), dates[-1]))
    monkeypatch.setattr(er, "READINGS_DIR", tmp_path)
    monkeypatch.setattr(er, "_file_sheet", lambda path, sheet: None)
    marked, clean = h.govern(book)
    assert marked == 0 and clean
    assert "rules_cut_pending" not in book["positions"]["TST"]


def test_anomaly_cut_still_fires(monkeypatch):
    # a short 20% against entry is still cut at once
    assert _run(monkeypatch, [120.5]) == ("ANOMALY-CUT", -20.5)
