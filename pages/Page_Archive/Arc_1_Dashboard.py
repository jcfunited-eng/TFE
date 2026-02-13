import streamlit as st
import pandas as pd

from engine import get_portfolio_and_prices

st.title("📊 Dashboard")

try:
    positions, tickers, latest, snapshot = get_portfolio_and_prices()
except Exception:
    st.error("Unable to load portfolio.")
    st.stop()

# -----------------------------------
# Portfolio Overview
# -----------------------------------

st.subheader("Portfolio Overview")

col1, col2, col3 = st.columns(3)
col1.metric("Total Value", f"${snapshot.total_value:,.2f}")
col2.metric("Unrealized P/L", f"{snapshot.unrealized_pl:,.2f}")
col3.metric("Diversification Score", f"{snapshot.diversification_score:.2f}")

# -----------------------------------
# Latest Prices
# -----------------------------------

st.subheader("Latest Prices")

price_rows = []
for t in tickers:
    price_rows.append({"Ticker": t, "Price": latest.get(t, None)})

df_prices = pd.DataFrame(price_rows)

st.dataframe(df_prices, use_container_width=True)

# -----------------------------------
# Portfolio Weights
# -----------------------------------

st.subheader("Portfolio Weights")

weight_rows = []
for t in tickers:
    weight_rows.append({"Ticker": t, "Weight": snapshot.weights.get(t, 0)})

df_weights = pd.DataFrame(weight_rows)

st.dataframe(df_weights, use_container_width=True)
