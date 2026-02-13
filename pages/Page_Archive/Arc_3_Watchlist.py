import streamlit as st
import pandas as pd

from engine import get_history_with_indicators
from utils import latest_price


# =====================================================
# PAGE HEADER
# =====================================================
st.title("📈 Watchlist — Market Overview")


# =====================================================
# LOAD WATCHLIST
# =====================================================
try:
    df_watch = pd.read_csv("watchlist.csv")
except Exception:
    st.error("Could not load watchlist.csv.")
    st.stop()

# Normalize column names
df_watch.columns = [c.strip() for c in df_watch.columns]


# Detect ticker column name
if "Ticker" in df_watch.columns:
    tickers = list(df_watch["Ticker"])
elif "ticker" in df_watch.columns:
    tickers = list(df_watch["ticker"])
else:
    st.error("watchlist.csv must contain a column named 'Ticker' or 'ticker'.")
    st.stop()

if not tickers:
    st.info("Your watchlist is empty.")
    st.stop()


# =====================================================
# GATHER DATA FOR EACH TICKER
# =====================================================
rows = []

for t in tickers:
    try:
        df, ind = get_history_with_indicators(t)

        if df.empty or ind == {}:
            continue

        close = ind["close"]
        last_price = float(close.iloc[-1])

        # Trend 20d
        if len(close) > 20:
            trend20 = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
            trend20_pct = round(trend20 * 100, 2)
        else:
            trend20_pct = None

        # RSI
        rsi_series = ind.get("rsi_14", None)
        rsi_val = float(rsi_series.iloc[-1]) if rsi_series is not None else None
        rsi_disp = round(rsi_val, 1) if rsi_val is not None else None

        # Sharpe and Vol
        sharpe = float(ind.get("sharpe", 0.0))
        vol = float(ind.get("volatility", 0.2))

        # Asset Type
        if "-USD" in t:
            a_type = "crypto"
        elif t in ["VTI","VOO","QQQ","IWM"]:
            a_type = "etf"
        elif t.startswith("^"):
            a_type = "index"
        else:
            a_type = "equity"

        rows.append({
            "Ticker": t,
            "Asset Type": a_type,
            "Last Price": round(last_price, 2),
            "Trend20d %": trend20_pct,
            "RSI (14)": rsi_disp,
            "Sharpe": round(sharpe, 2),
            "Volatility": round(vol, 2),
        })

    except Exception:
        continue


# =====================================================
# OUTPUT TABLE
# =====================================================
if not rows:
    st.error("No market data available for watchlist tickers.")
    st.stop()

watch_df = pd.DataFrame(rows).sort_values("Ticker")

st.dataframe(
    watch_df,
    width="stretch"
)
