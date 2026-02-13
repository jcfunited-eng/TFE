import streamlit as st
import pandas as pd

from engine import (
    get_portfolio_and_prices,
    get_history_with_indicators,
)

from utils import (
    latest_price,
)


# =====================================================
# PAGE HEADER
# =====================================================
st.title("💡 Portfolio Insights")


# =====================================================
# LOAD PORTFOLIO + PRICES
# =====================================================
try:
    positions, tickers, latest, snapshot = get_portfolio_and_prices()
except Exception:
    st.error("Unable to load portfolio data.")
    st.stop()


# =====================================================
# SUMMARY METRICS
# =====================================================
col1, col2, col3 = st.columns(3)

col1.metric("Total Value", f"${snapshot.total_value:,.2f}")
col2.metric("Unrealized P/L", f"${snapshot.unrealized_pl:,.2f}")
col3.metric("P/L %", f"{snapshot.unrealized_pl_pct:.2f}%")


# =====================================================
# DIVERSIFICATION SUMMARY
# =====================================================
st.subheader("🌐 Diversification Overview")

# Diversification score = entropy-like measure of weights
weights = snapshot.weights  # dict {ticker: weight}

if weights:
    # Convert to DF for display
    div_df = pd.DataFrame(
        [{"Ticker": t, "Weight %": w * 100} for t, w in weights.items()]
    ).sort_values("Weight %", ascending=False)

    st.dataframe(div_df, width="stretch")
else:
    st.info("No diversification data available.")


# =====================================================
# RISK METRICS PER ASSET
# =====================================================
st.subheader("⚠️ Risk Metrics Per Asset")

rows = []

for t in tickers:
    df, ind = get_history_with_indicators(t)

    if df.empty or ind == {}:
        continue

    close = ind["close"]
    last_price = float(close.iloc[-1])

    # Trend
    if len(close) > 20:
        trend20 = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
        trend20_pct = round(trend20 * 100, 2)
    else:
        trend20_pct = None

    sharpe = float(ind.get("sharpe", 0.0))
    vol = float(ind.get("volatility", 0.2))
    max_dd = float(ind.get("max_dd", 0.0))

    rows.append({
        "Ticker": t,
        "Last Price": round(last_price, 2),
        "Trend20d %": trend20_pct,
        "Sharpe": round(sharpe, 2),
        "Volatility": round(vol, 2),
        "Max Drawdown %": round(max_dd * 100, 2),
    })

if rows:
    risk_df = pd.DataFrame(rows).sort_values("Volatility")
    st.dataframe(risk_df, width="stretch")
else:
    st.info("No risk data available for any assets.")


# =====================================================
# PORTFOLIO WEIGHTS CHART
# =====================================================
st.subheader("📊 Allocation Breakdown")

try:
    import plotly.express as px

    fig = px.pie(
        div_df,
        names="Ticker",
        values="Weight %",
        title="Portfolio Allocation",
    )
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, width="stretch")

except Exception:
    st.info("Unable to generate allocation chart.")
