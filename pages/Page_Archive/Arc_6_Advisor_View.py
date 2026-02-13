import streamlit as st
import pandas as pd

from engine import (
    get_portfolio_and_prices,
    get_history_with_indicators,
)

from utils import latest_price


# =====================================================
# PAGE HEADER
# =====================================================
st.title("🧠 Advisor View — Smart Portfolio Guidance")

try:
    positions, tickers, latest, snapshot = get_portfolio_and_prices()
except Exception:
    st.error("Unable to load portfolio for Advisor View.")
    st.stop()


# =====================================================
# ANALYZE EACH ASSET
# =====================================================
def analyze_ticker(ticker: str):
    """
    Returns a dict of:
    - ticker
    - price
    - trend20
    - risk (volatility)
    - max_dd
    - action
    """
    df, ind = get_history_with_indicators(ticker)

    if df.empty or ind == {}:
        return None

    close = ind["close"]
    price = float(close.iloc[-1])

    # Trend (20d)
    if len(close) > 20:
        trend20 = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
        trend20_pct = round(trend20 * 100, 2)
    else:
        trend20_pct = None

    vol = float(ind.get("volatility", 0.2))
    max_dd = float(ind.get("max_dd", 0.0)) * 100  # convert to %
    sharpe = float(ind.get("sharpe", 0.0))

    # Simplified decision logic
    if trend20 is not None and trend20 > 0.03 and sharpe > 0.5:
        action = "BUY"
    elif trend20 is not None and trend20 < -0.03:
        action = "REDUCE"
    else:
        action = "HOLD"

    return {
        "ticker": ticker,
        "price": round(price, 2),
        "trend": trend20_pct,
        "volatility": round(vol, 2),
        "max_dd": round(max_dd, 2),
        "action": action,
    }


rows = []

for t in tickers:
    result = analyze_ticker(t)
    if result is not None:
        rows.append(result)


if not rows:
    st.error("Advisor View could not analyze any assets.")
    st.stop()


advisor_df = pd.DataFrame(rows).sort_values("ticker")


# =====================================================
# DISPLAY TABLE
# =====================================================
st.subheader("📋 Advisor Summary Table")

st.dataframe(
    advisor_df[
        ["ticker", "price", "trend", "volatility", "max_dd", "action"]
    ],
    width="stretch"
)


# =====================================================
# STRATEGIC NOTES
# =====================================================
st.subheader("📝 Strategic Guidance")

st.write("""
This guidance is based on:

- 20-day trend momentum  
- Sharpe ratio (risk-adjusted performance)  
- Volatility  
- Max drawdown profile  

The Advisor View is designed as a helpful smart-summary, not a substitute for professional guidance.
""")
