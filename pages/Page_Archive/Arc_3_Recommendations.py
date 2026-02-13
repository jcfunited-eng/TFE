import streamlit as st
import pandas as pd

from utils import (
    latest_price,
)

from engine import (
    get_portfolio_and_prices,
    get_history_with_indicators,
)


# =====================================================
# PAGE HEADER
# =====================================================
st.title("⭐ Market Recommendations — Buy / Hold / Reduce")

# Load user portfolio + prices
try:
    positions, tickers, latest, snapshot = get_portfolio_and_prices()
except Exception:
    st.error("Unable to load market data.")
    st.stop()

# Market universe includes user tickers + major assets
universe = list(set(tickers + [
    "AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA",
    "VTI","VOO","QQQ","IWM",
    "JPM","UNH","HD","XOM","CVX","BAC","KO","PEP","NFLX",
    "BTC-USD","ETH-USD"
]))

results = []


# =====================================================
# PROCESS EACH TICKER
# =====================================================
for t in universe:
    try:
        df, ind = get_history_with_indicators(t)

        # Skip if no data
        if df.empty or ind == {}:
            continue

        close = ind["close"]
        price = float(close.iloc[-1])

        # --- Trend 20d ---
        if len(close) > 20:
            trend20 = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
        else:
            trend20 = 0.0

        # --- RSI ---
        rsi_series = ind.get("rsi_14", None)
        rsi = float(rsi_series.iloc[-1]) if rsi_series is not None else 50.0

        # --- Sharpe / Vol ---
        sharpe = float(ind.get("sharpe", 0.0))
        vol = float(ind.get("volatility", 0.2))

        # =====================================================
        # MULTI-FACTOR SCORE
        # =====================================================
        score = 0
        if trend20 > 0.05: score += 2
        if trend20 < -0.05: score -= 2
        if rsi < 30: score += 2
        if rsi > 70: score -= 2
        if sharpe > 1.0: score += 1
        if sharpe < 0.3: score -= 1
        score -= vol

        # Decision
        if score >= 2:
            decision = "BUY"
        elif score <= -2:
            decision = "REDUCE"
        else:
            decision = "HOLD"

        # Asset type
        if "-USD" in t:
            asset_type = "crypto"
        elif t in ["VTI","VOO","QQQ","IWM"]:
            asset_type = "etf"
        elif t.startswith("^"):
            asset_type = "index"
        else:
            asset_type = "equity"

        results.append({
            "Ticker": t,
            "Asset Type": asset_type,
            "Price": round(price, 2),
            "Trend20d %": round(trend20 * 100, 2),
            "RSI": round(rsi, 1),
            "Sharpe": round(sharpe, 2),
            "Volatility": round(vol, 2),
            "Decision": decision,
            "Score": round(score, 2),
        })

    except Exception:
        continue


# =====================================================
# CREATE RESULTS DF
# =====================================================
if len(results) == 0:
    st.error("No recommendations could be generated.")
    st.stop()

recs_df = pd.DataFrame(results).sort_values("Score", ascending=False)


# =====================================================
# 🔥 HOT PICKS — BEST UNDER $30
# =====================================================
st.subheader("🔥 HOT PICKS — Promising Under $30")

hot_results = []

for asset in ["equity", "etf", "index", "crypto"]:
    subset = recs_df[
        (recs_df["Asset Type"] == asset) &
        (recs_df["Price"] < 30) &
        (recs_df["Decision"] == "BUY")
    ]
    top3 = subset.head(3)
    if not top3.empty:
        hot_results.append((asset.upper(), top3))

if not hot_results:
    st.info("No strong BUY-rated sub-$30 candidates today.")
else:
    for label, df_hot in hot_results:
        st.write(f"### {label} — Top Picks Under $30")
        st.dataframe(
            df_hot[["Ticker","Price","Score","Trend20d %","RSI","Sharpe"]],
            width="stretch"
        )


# =====================================================
# ⭐ RECOMMENDATIONS BY PRICE TIER
# =====================================================
st.subheader("🟦 Recommendations by Price Tier")

tier_choice = st.selectbox(
    "Select Tier:",
    ["Low Price Tier", "Mid Price Tier", "High Price Tier"]
)

# Categorize tiers by price distribution
q30 = recs_df["Price"].quantile(0.30)
q70 = recs_df["Price"].quantile(0.70)

def classify_tier(p):
    if p <= q30: return "Low Price Tier"
    if p <= q70: return "Mid Price Tier"
    return "High Price Tier"

recs_df["Tier"] = recs_df["Price"].apply(classify_tier)

tier_df = recs_df[recs_df["Tier"] == tier_choice]

if tier_df.empty:
    st.info("No recommendations available for this tier.")
else:
    st.dataframe(
        tier_df[[
            "Ticker","Asset Type","Price","Tier",
            "Trend20d %","RSI","Sharpe","Volatility","Decision","Score"
        ]],
        width="stretch"
    )
