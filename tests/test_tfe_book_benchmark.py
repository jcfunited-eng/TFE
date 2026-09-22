import pandas as pd
import pytest

from tools.tfe_book_benchmark import measure


def fixture():
    book = {"start": 1000, "cash": 899, "positions": {
        "B": {"entry_date": "2026-09-02", "entry_px": 10, "shares": 10,
              "notional": 100, "side": -1}}, "closed": [
        {"symbol": "A", "entry_date": "2026-09-02", "exit_at": "2026-09-04",
         "entry_px": 10, "exit_px": 10.1, "shares": 10, "side": 1, "pnl": -1}]}
    bars = pd.DataFrame([
        (d, s, p) for d, prices in [
            ("2026-09-01", {"SPY": 100}),
            ("2026-09-02", {"SPY": 101, "A": 10, "B": 10}),
            ("2026-09-03", {"SPY": 102, "A": 5, "B": 12}),
            ("2026-09-04", {"SPY": 103, "B": 9})]
        for s, p in prices.items()], columns=["Date", "Symbol", "Close"])
    return book, bars


def test_quiet_days_open_shorts_and_net_wins():
    book, bars = fixture()
    result = measure(book, bars, "2026-09-01", "2026-09-04")
    assert [p["equity"] for p in result["curve"]] == [1000, 1000, 930, 1009]
    assert result["win_rate_pct"] == 0  # price gain was smaller than costs
    assert result["strategy_return_pct"] == pytest.approx(.9)
    assert result["lift_percentage_points"] == pytest.approx(-2.1)
    assert result["max_drawdown_pct"] == pytest.approx(-7)


def test_missing_mark_refuses_instead_of_hiding_loss():
    book, bars = fixture()
    bars = bars[~((bars.Symbol == "A") & (bars.Date == "2026-09-03"))]
    with pytest.raises(ValueError, match="missing held-position mark"):
        measure(book, bars, "2026-09-01", "2026-09-04")


def test_cash_mismatch_refuses_partial_ledger():
    book, bars = fixture()
    book["cash"] += 1
    with pytest.raises(ValueError, match="cash reconciliation"):
        measure(book, bars, "2026-09-01", "2026-09-04")


def test_duplicate_prices_refuse():
    book, bars = fixture()
    with pytest.raises(ValueError, match="duplicate source bars"):
        measure(book, pd.concat([bars, bars.iloc[:1]]), "2026-09-01", "2026-09-04")


def test_no_shifted_benchmark_endpoint():
    book, bars = fixture()
    with pytest.raises(ValueError, match="exact valuation endpoints"):
        measure(book, bars, "2026-08-31", "2026-09-04")


def test_prior_trades_cannot_be_rebased_without_starting_equity():
    book, bars = fixture()
    with pytest.raises(ValueError, match="entry outside"):
        measure(book, bars, "2026-09-02", "2026-09-04")
