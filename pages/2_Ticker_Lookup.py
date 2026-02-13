import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from datetime import datetime, timedelta

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan

# ============================================================
# LOCAL INDICATOR COMPUTATION
# ============================================================

def compute_indicators(df: pd.DataFrame) -> dict:
    ind = {}

    # SMA 20
    ind["sma_20"] = df["close"].rolling(20).mean()

    # EMA 20
    ind["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()

    # Momentum 10
    ind["momentum_10"] = df["close"].diff(10)

    # RSI 14
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    rs = up.rolling(14).mean() / down.rolling(14).mean()
    ind["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    ind["macd_line"] = ema12 - ema26
    ind["macd_signal"] = ind["macd_line"].ewm(span=9, adjust=False).mean()

    return ind


# ============================================================
# DATE RANGE MAPPING
# ============================================================

RANGE_MAP = {
    "1D": 1,
    "5D": 5,
    "1M": 30,
    "6M": 180,
    "YTD": None,  # special handling
    "1Y": 365,
    "5Y": 1825,
    "MAX": None,  # special handling
}


def get_date_range(choice: str):
    today = datetime.utcnow()
    if choice == "YTD":
        return datetime(today.year, 1, 1), today
    if choice == "MAX":
        # 20 years of data
        return today - timedelta(days=365 * 20), today

    days = RANGE_MAP[choice]
    return today - timedelta(days=days), today


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🔍 Ticker Lookup — Multi-Chart Insight")

ticker = st.text_input(
    "Enter ticker (AAPL, BTC-USD, VTI, SPY):",
    "AAPL"
).upper().strip()

if not ticker:
    st.stop()

# Unified Market Data backend
mds = get_unified_market_data()


# ============================================================
# SNAPSHOT / LAST PRICE
# ============================================================

snap = mds.get_snapshot(ticker)
if snap.last_price is not None:
    st.metric(
        "Last Price",
        f"{snap.last_price:.4f}",
        delta=f"{snap.day_change:.4f}" if snap.day_change else None,
    )
else:
    st.metric("Last Price", "N/A")


# ============================================================
# DATE RANGE → Massive History Request
# ============================================================

range_choice = st.selectbox(
    "Date Range",
    ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "MAX"],
    index=2
)

start, end = get_date_range(range_choice)

req = HistoryRequest(
    ticker=ticker,
    multiplier=1,
    timespan=Timespan.DAY,
    start=start,
    end=end,
    adjusted=True,
)

hist = mds.get_history(req)

if not hist.bars:
    st.error("Unable to load historical data.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame([
    {
        "time": b.t,
        "open": b.o,
        "high": b.h,
        "low": b.l,
        "close": b.c,
        "volume": b.v,
    }
    for b in hist.bars
])

df.set_index("time", inplace=True)
df.sort_index(inplace=True)


# ============================================================
# INDICATORS
# ============================================================

ind = compute_indicators(df)


# ============================================================
# PRICE / CANDLE CHART
# ============================================================

st.subheader("📈 Price & Trend")

fig_price = go.Figure()

fig_price.add_trace(go.Candlestick(
    x=df.index,
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    increasing_line_color="#00C805",
    decreasing_line_color="#FF3400",
    name="Price",
))

fig_price.add_trace(go.Scatter(
    x=df.index,
    y=ind["sma_20"],
    name="SMA 20",
    line=dict(color="#FFD700"),
))

fig_price.add_trace(go.Scatter(
    x=df.index,
    y=ind["ema_20"],
    name="EMA 20",
    line=dict(color="#40a9e2"),
))

fig_price.update_layout(template="plotly_dark")
st.plotly_chart(fig_price, use_container_width=True)


# ============================================================
# MOMENTUM
# ============================================================

st.subheader("📊 Momentum (10-day)")

fig_mom = go.Figure()
fig_mom.add_trace(go.Scatter(
    x=df.index,
    y=ind["momentum_10"],
    name="Momentum",
    line=dict(color="#40a9e2"),
))
fig_mom.update_layout(template="plotly_dark")

st.plotly_chart(fig_mom, use_container_width=True)


# ============================================================
# RSI
# ============================================================

st.subheader("📉 RSI (14)")

fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(
    x=df.index,
    y=ind["rsi_14"],
    name="RSI",
    line=dict(color="#40a9e2"),
))

fig_rsi.add_hline(y=70, line_color="red", line_dash="dot")
fig_rsi.add_hline(y=30, line_color="green", line_dash="dot")

fig_rsi.update_layout(template="plotly_dark")

st.plotly_chart(fig_rsi, use_container_width=True)


# ============================================================
# MACD
# ============================================================

st.subheader("📉 MACD")

fig_macd = go.Figure()
fig_macd.add_trace(go.Scatter(
    x=df.index,
    y=ind["macd_line"],
    name="MACD Line",
    line=dict(color="#40a9e2"),
))
fig_macd.add_trace(go.Scatter(
    x=df.index,
    y=ind["macd_signal"],
    name="Signal Line",
    line=dict(color="#AAAAAA", dash="dot"),
))

fig_macd.update_layout(template="plotly_dark")

st.plotly_chart(fig_macd, use_container_width=True)
