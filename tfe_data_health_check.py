"""
tfe_data_health_check.py
---------------------------------------------
Live diagnostic test for Massive + Alpaca market data backends.

This script:
    - Instantiates the primary Massive backend
    - Instantiates the secondary Alpaca backend
    - Runs a battery of real API calls against both providers
    - Prints unfiltered results (Success / Failure + error details)

This is NOT a unit test.
This is a real connectivity & data-availability test.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from tfe_market_data_factory import get_market_data_service
from massive_market_data_service import MassiveMarketDataService
from alpaca_market_data_service import AlpacaMarketDataService
from tfe_market_data_service import HistoryRequest, Timespan


# ============================================================
# Test targets
# ============================================================

TEST_TICKERS = ["AAPL", "SPY", "QQQ", "BTC-USD"]


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70 + "\n")


def test_last_price(backend, ticker: str) -> None:
    print(f"Testing last price for {ticker}...")
    try:
        price = backend.get_last_price(ticker)
        print(f"  Last price: {price}")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_snapshot(backend, ticker: str) -> None:
    print(f"Testing snapshot for {ticker}...")
    try:
        snap = backend.get_snapshot(ticker)
        print("  Snapshot:", snap)
    except Exception as e:
        print(f"  ERROR: {e}")


def test_history(backend, ticker: str) -> None:
    print(f"Testing history for {ticker}...")

    end = datetime.utcnow()
    start = end - timedelta(days=5)

    req = HistoryRequest(
        ticker=ticker,
        multiplier=1,
        timespan=Timespan.DAY,
        start=start,
        end=end,
        adjusted=True,
    )

    try:
        result = backend.get_history(req)
        print(f"  Bars returned: {len(result.bars)}")
        if result.bars:
            first = result.bars[0]
            last = result.bars[-1]
            print(f"  First bar: {first}")
            print(f"  Last bar:  {last}")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_ticker_info(backend, ticker: str) -> None:
    print(f"Testing ticker info for {ticker}...")
    try:
        info = backend.get_ticker_info(ticker)
        print("  Info:", info)
    except Exception as e:
        print(f"  ERROR: {e}")


def test_validation(backend) -> None:
    print("Testing ticker validation...")
    try:
        valid = backend.validate_tickers(TEST_TICKERS)
        print("  Valid tickers:", valid)
    except Exception as e:
        print(f"  ERROR: {e}")


# ============================================================
# Main
# ============================================================

def main() -> None:

    # ---------------------------
    # 1. Massive backend (primary)
    # ---------------------------
    print_header("PRIMARY BACKEND: MASSIVE.COM")
    massive = MassiveMarketDataService()

    print("Provider:", massive.provider_name())
    print("Health:", massive.last_health_check())
    print()

    for t in TEST_TICKERS:
        test_last_price(massive, t)
        test_snapshot(massive, t)
        test_history(massive, t)
        test_ticker_info(massive, t)
        print()

    test_validation(massive)

    # ---------------------------
    # 2. Alpaca backend (secondary)
    # ---------------------------
    print_header("SECONDARY BACKEND: ALPACA")
    alpaca = AlpacaMarketDataService()

    print("Provider:", alpaca.provider_name())
    print("Health:", alpaca.last_health_check())
    print()

    for t in TEST_TICKERS:
        test_last_price(alpaca, t)
        test_snapshot(alpaca, t)
        test_history(alpaca, t)
        test_ticker_info(alpaca, t)
        print()

    test_validation(alpaca)

    # ---------------------------
    # Summary
    # ---------------------------
    print_header("DATA HEALTH CHECK COMPLETE")
    print("Review the above logs for failures or missing data.")
    print("Massive is expected to provide richer history + metadata.")
    print("Alpaca is expected to provide snapshots + bars.")
    print()


if __name__ == "__main__":
    main()
