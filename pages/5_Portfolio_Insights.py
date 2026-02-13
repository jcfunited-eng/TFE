import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from datetime import datetime, timedelta

from tfe_portfolio_api import get_portfolio_df, get_portfolio_valuation
from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan


# ============================================================
# INDICATORS
# ============================================================

def compute_indicators(df: pd.DataFrame) -> dict:
    ind = {}

    close = df["close"]

    # Trend20d
    if len(close) > 20:
        ind["trend20d_pct"] = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] * 100
    else:
        ind["trend20d_pct"] = 0.0

    # RSI
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    rs = up.rolling(14).mean() / down.rolling(14).mean()
    ind["rsi"] = (100 - (100 / (1 + rs))).iloc[-1] if len(rs.dropna()) else 50.0

    # Sharpe
    ret = close.pct_change().dropna()
    if len(ret) > 2 and ret.std() != 0:
        ind["sharpe"] = (ret.mean() / ret.std()) * np.sqrt(252)
    else:
        ind["sharpe"] = 0.0

    # Volatility
    if len(ret) > 2:
        ind["volatility"] = ret.std() * np.sqrt(252)
    else:
        ind["volatility"] = 0.0

    # Max drawdown
    cumulative = (1 + ret).cumprod()
    peak = cumulative.cummax()
    dd = (cumulative - peak) / peak
    ind["max_dd"] = dd.min() if len(dd) else 0.0

    return ind


# ============================================================
# PAGE HEADER
# ============================================================

st.title("💡 Portfolio Insights")

df = get_portfolio_df()
if df.empty:
    st.error("Your portfolio is empty.")
    st.stop()

valuation = get_portfolio_valuation()
mds = get_unified_market_data()


# ============================================================
# TOP METRICS
# ============================================================

c1, c2, c3 = st.columns(3)
c1.metric("Total Value", f"${valuation.total_value:,.2f}")
c2.metric("Unrealized P/L", f"${valuation.unrealized_pl:,.2f}")
c3.metric("P/L %", f"{valuation.pl_pct:,.2f}%")


# ============================================================
# DIVERSIFICATION TABLE
# ============================================================

st.subheader("🌐 Diversification Overview")

weights_df = pd.DataFrame({
    "Ticker": list(valuation.weights.keys()),
    "Weight %": [round(v * 100, 2) for v in valuation.weights.values()],
})

st.dataframe(weights_df, width="stretch")


# ============================================================
# RISK METRICS PER ASSET
# ============================================================

st.subheader("⚠ Risk Metrics Per Asset")

risk_rows = []

start = datetime.utcnow() - timedelta(days=365 * 2)
end = datetime.utcnow()

for p in valuation.positions:
    ticker = p.ticker

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
        continue

    df_hist = pd.DataFrame([
        {"time": b.t, "close": b.c}
        for b in hist.bars
    ])
    df_hist.set_index("time", inplace=True)
    df_hist.sort_index(inplace=True)

    if df_hist.empty:
        continue

    ind = compute_indicators(df_hist)

    risk_rows.append({
        "Ticker": ticker,
        "Trend20d %": round(ind["trend20d_pct"], 2),
        "RSI (14)": round(ind["rsi"], 1),
        "Sharpe": round(ind["sharpe"], 2),
        "Volatility": round(ind["volatility"], 2),
        "Max DD": round(ind["max_dd"], 2),
    })

if risk_rows:
    st.dataframe(pd.DataFrame(risk_rows), width="stretch")
else:
    st.info("No risk data available.")


# ============================================================
# ALLOCATION BREAKDOWN
# ============================================================

st.subheader("📊 Allocation Breakdown")

fig = go.Figure(
    data=[go.Pie(
        labels=list(valuation.weights.keys()),
        values=[v * 100 for v in valuation.weights.values()],
        hole=0.4,
    )]
)

fig.update_layout(template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)
