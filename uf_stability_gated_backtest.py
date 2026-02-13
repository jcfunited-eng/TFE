import numpy as np
import pandas as pd
from datetime import date, timedelta

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan

from uf_core.uf_structural_engine import compute_uf_structural_state


# ---------------- CONFIG ----------------
SYMBOLS = [
    "F", "AAPL", "AAL", "AAT", "ABL",
    "ABTS", "EQIX", "NOC", "AFJK",
    "NCPL", "TWG", "YAAS"
]

LOOKBACK_YEARS = 5
FORWARD_HORIZON = 5
STABILITY_THRESHOLD = 0.6
# ---------------------------------------


def load_history(symbol):
    mds = get_unified_market_data()

    end = date.today()
    start = end - timedelta(days=LOOKBACK_YEARS * 365)

    req = HistoryRequest(
        symbol=symbol,
        start=start,
        end=end,
        timespan=Timespan.DAY,
        limit=5000,
    )

    hist = mds.get_history(req)
    if hist is None or not hist.bars:
        return None

    ts = [b.timestamp for b in hist.bars]
    px = [b.close for b in hist.bars]

    return pd.Series(px, index=pd.to_datetime(ts)).sort_index()


def run_symbol(symbol):
    series = load_history(symbol)
    if series is None or len(series) < FORWARD_HORIZON + 20:
        return None

    n_bars = len(series)
    evals = 0
    trades = 0
    hits = 0
    returns = []
    long_returns = []
    short_returns = []

    for i in range(20, n_bars - FORWARD_HORIZON):
        window = series.iloc[:i]
        future_price = series.iloc[i + FORWARD_HORIZON]
        current_price = series.iloc[i]

        state = compute_uf_structural_state(window)

        evals += 1

        if state.stability_score < STABILITY_THRESHOLD:
            continue  # LISTENING GATE ONLY

        D = state.decision_vector[0]
        if D == 0:
            continue

        trades += 1
        ret = (future_price / current_price) - 1.0

        if D > 0:
            returns.append(ret)
            long_returns.append(ret)
            if ret > 0:
                hits += 1
        else:
            returns.append(-ret)
            short_returns.append(-ret)
            if ret < 0:
                hits += 1

    hit_rate = hits / trades if trades > 0 else 0.0
    avg_tr = np.mean(returns) if returns else 0.0
    long_tr = np.mean(long_returns) if long_returns else 0.0
    short_tr = np.mean(short_returns) if short_returns else 0.0

    return {
        "symbol": symbol,
        "n_bars": n_bars,
        "evals": evals,
        "trades": trades,
        "hit": hit_rate,
        "avg_tr": avg_tr,
        "long_tr": long_tr,
        "short_tr": short_tr,
    }


def main():
    results = []
    print(
        "UF-Core DSF forward backtest "
        "(stability-gated listening, NO Hardening/Safemode)"
    )
    print(
        f"Symbols: {', '.join(SYMBOLS)} | "
        f"stability >= {STABILITY_THRESHOLD} | "
        f"horizon={FORWARD_HORIZON} bars"
    )
    print("-" * 120)

    for sym in SYMBOLS:
        r = run_symbol(sym)
        if r is None:
            continue
        results.append(r)
        print(
            f"{r['symbol']:6s} "
            f"n_bars={r['n_bars']:4d} "
            f"evals={r['evals']:4d} "
            f"trades={r['trades']:4d} "
            f"hit={r['hit']:.3f} "
            f"avg_tr={r['avg_tr']:.4f} "
            f"long_tr={r['long_tr']:.4f} "
            f"short_tr={r['short_tr']:.4f}"
        )

    if results:
        all_trades = sum(r["trades"] for r in results)
        weighted_hit = (
            sum(r["hit"] * r["trades"] for r in results) / all_trades
            if all_trades > 0 else 0.0
        )
        avg_return = np.mean(
            [r["avg_tr"] for r in results if r["trades"] > 0]
        )

        print("-" * 120)
        print(
            f"ALL trades={all_trades} "
            f"hit={weighted_hit:.3f} "
            f"avg_tr={avg_return:.4f}"
        )


if __name__ == "__main__":
    main()
