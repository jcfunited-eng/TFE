import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Correct imports
from utils import (
    UP_COLOR,
    DOWN_COLOR,
    PLOTLY_TEMPLATE,
    history_range,        # FINAL correct wrapper
    latest_price,         # wrapper around engine.latest_price_single
)

from engine import (
    get_history_with_indicators,
)


# =========================================================
# PAGE HEADER
# =========================================================
st.title("🔍 Ticker Lookup — Multi-Chart Insight")

ticker = st.text_input(
    "Enter ticker (AAPL, BTC-USD, VTI, ^GSPC):",
    "AAPL"
).upper().strip()

if not ticker:
    st.stop()


# =========================================================
# LATEST PRICE
# =========================================================
try:
    price = latest_price(ticker)
    if price is not None:
        st.metric("Last Price", f"{price:.4f}")
except Exception:
    st.write("")   # silent fail


# =========================================================
# DATE RANGE SELECTOR
# =========================================================
range_choice = st.selectbox(
    "Date Range",
    ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "MAX"],
    index=3  # default = 6M
)

period, interval = history_range(range_choice)


# =========================================================
# LOAD HISTORY + INDICATORS
# =========================================================
df, ind = get_history_with_indicators(ticker, period, interval)

if df.empty or ind == {}:
    st.error("Unable to load historical data.")
    st.stop()

close = ind["close"]


# =========================================================
# PRICE CHART
# =========================================================
st.subheader("📈 Price & Trend")

fig_price = go.Figure()

fig_price.add_trace(go.Candlestick(
    x=df.index,
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    increasing_line_color=UP_COLOR,
    decreasing_line_color=DOWN_COLOR,
))

# SMA/EMA overlays
fig_price.add_trace(go.Scatter(
    x=df.index, y=ind["sma_20"],
    name="SMA 20",
    line=dict(color="#FFD700")
))

fig_price.add_trace(go.Scatter(
    x=df.index, y=ind["ema_20"],
    name="EMA 20",
    line=dict(color="#40a9e2")
))

fig_price.update_layout(template=PLOTLY_TEMPLATE)
st.plotly_chart(fig_price, width="stretch")


# =========================================================
# MOMENTUM
# =========================================================
st.subheader("📊 Momentum")

fig_mom = go.Figure()
fig_mom.add_trace(go.Scatter(
    x=df.index, y=ind["momentum_10"],
    name="Momentum",
    line=dict(color="#40a9e2")
))
fig_mom.update_layout(template=PLOTLY_TEMPLATE)
st.plotly_chart(fig_mom, width="stretch")


# =========================================================
# RSI
# =========================================================
st.subheader("📉 RSI (14)")

rsi = ind["rsi_14"]
fig_rsi = go.Figure()

fig_rsi.add_trace(go.Scatter(
    x=df.index, y=rsi,
    name="RSI",
    line=dict(color="#40a9e2")
))

fig_rsi.add_hline(y=70, line_color="red", line_dash="dot")
fig_rsi.add_hline(y=30, line_color="green", line_dash="dot")

fig_rsi.update_layout(template=PLOTLY_TEMPLATE)
st.plotly_chart(fig_rsi, width="stretch")


# =========================================================
# MACD
# =========================================================
st.subheader("📉 MACD")

fig_macd = go.Figure()

fig_macd.add_trace(go.Scatter(
    x=df.index, y=ind["macd_line"],
    name="MACD Line",
    line=dict(color="#40a9e2")
))

fig_macd.add_trace(go.Scatter(
    x=df.index, y=ind["macd_signal"],
    name="MACD Signal",
    line=dict(color="#AAAAAA", dash="dot")
))

fig_macd.update_layout(template=PLOTLY_TEMPLATE)
st.plotly_chart(fig_macd, width="stretch")
