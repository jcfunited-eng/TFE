"""Store refresh: a symbol with no bar on the overlap day is verified on its
OWN last stored bar (2026-09-29). Before this, five thin names that skipped
2026-09-25 (BYFC, DGZ, ELTK, STG, UCIB) refused the whole refresh.

Run: python3 -m pytest tests/test_ch4_store_refresh_uncovered.py -q
"""
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ch4_store_refresh import assemble  # noqa: E402

D = dt.date
SESSIONS = [D(2026, 9, 23), D(2026, 9, 24), D(2026, 9, 25), D(2026, 9, 28)]
ROSTER = {"AAA", "THIN"}


def store():
    rows = [
        (pd.Timestamp("2026-09-23"), "AAA", 10.0, 1000.0),
        (pd.Timestamp("2026-09-24"), "AAA", 10.5, 1100.0),
        (pd.Timestamp("2026-09-25"), "AAA", 11.0, 1200.0),
        # THIN traded 09-23 and 09-24, skipped the overlap day 09-25
        (pd.Timestamp("2026-09-23"), "THIN", 2.0, 50.0),
        (pd.Timestamp("2026-09-24"), "THIN", 2.1, 60.0),
    ]
    return pd.DataFrame(rows, columns=["Date", "Symbol", "Close", "Volume"])


def grouped(day, key):
    return {
        "2026-09-25": [{"T": "AAA", "c": 11.0, "v": 1200.0}],
        "2026-09-28": [{"T": "AAA", "c": 11.2, "v": 900.0}, {"T": "THIN", "c": 2.3, "v": 70.0}],
    }[day]


def test_without_a_symbol_fetcher_the_old_refusal_stands():
    with pytest.raises(RuntimeError, match="no verified adjustment overlap for: THIN"):
        assemble(store(), ROSTER, SESSIONS, "k", fetch=grouped)


def test_same_basis_is_verified_on_its_own_last_bar_and_appends():
    def history(symbol, start, end, key):
        assert (symbol, start, end) == ("THIN", "2026-09-24", "2026-09-24")
        return [(pd.Timestamp("2026-09-24"), "THIN", 2.1, 60.0)]
    out, receipt = assemble(store(), ROSTER, SESSIONS, "k", fetch=grouped, fetch_symbol=history)
    assert receipt["verified_on_own_last_bar"] == ["THIN"]
    assert receipt["rebased_symbols"] == []
    thin = out[out.Symbol == "THIN"].sort_values("Date")
    assert list(thin.Close) == [2.0, 2.1, 2.3]
    assert receipt["added_rows"] == 2


def test_rebased_symbol_has_its_history_replaced():
    calls = []

    def history(symbol, start, end, key):
        calls.append((start, end))
        if start == end:                      # the probe: provider shows a 10:1 re-basing
            return [(pd.Timestamp("2026-09-24"), "THIN", 21.0, 6.0)]
        return [(pd.Timestamp("2026-09-23"), "THIN", 20.0, 5.0),
                (pd.Timestamp("2026-09-24"), "THIN", 21.0, 6.0)]
    out, receipt = assemble(store(), ROSTER, SESSIONS, "k", fetch=grouped, fetch_symbol=history)
    assert receipt["rebased_symbols"] == ["THIN"]
    assert calls == [("2026-09-24", "2026-09-24"), ("2026-09-23", "2026-09-24")]
    thin = out[out.Symbol == "THIN"].sort_values("Date")
    assert list(thin.Close) == [20.0, 21.0, 2.3]
    aaa = out[out.Symbol == "AAA"].sort_values("Date")
    assert list(aaa.Close) == [10.0, 10.5, 11.0, 11.2]   # untouched symbol unchanged


def test_no_provider_bar_on_its_last_day_still_refuses():
    with pytest.raises(RuntimeError, match="provider has no bar on its last stored day"):
        assemble(store(), ROSTER, SESSIONS, "k", fetch=grouped,
                 fetch_symbol=lambda *a: [])
