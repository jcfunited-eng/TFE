import streamlit as st
import pandas as pd

from uf_snapshot_cache import (
    load_snapshot_raw,
    refresh_snapshot_full,
    refresh_filtered_snapshot,
)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _asset_label_to_key(label: str) -> str:
    """Map UI label -> internal asset_type key."""
    if label == "Stocks":
        return "stock"
    if label == "ETFs":
        return "etf"
    if label == "Crypto":
        return "crypto"
    return "stock"


def _score_row(row: pd.Series) -> float:
    """
    UF decision-surface style score.

    Uses structural fields only:
        score = 0.4 * S_UF + 0.3 * R_UF + 0.4 * opportunity - 0.2 * risk
    """
    s = float(row.get("S_UF", 0.0))
    r = float(row.get("R_UF", 0.0))
    opp = float(row.get("opportunity", 0.0))
    risk = float(row.get("risk", 0.0))
    return 0.4 * s + 0.3 * r + 0.4 * opp - 0.2 * risk


# -------------------------------------------------------------------
# Page
# -------------------------------------------------------------------

st.set_page_config(layout="wide")

rows = load_snapshot_raw()
if not rows:
    st.error("No UF snapshot found. Run an admin refresh to build the snapshot.")
    st.stop()

df = pd.DataFrame(rows)
if "ticker" not in df.columns:
    st.error("UF snapshot format is invalid (no 'ticker' column).")
    st.stop()

df["ticker"] = df["ticker"].astype(str).str.upper()
df = df.sort_values("ticker").reset_index(drop=True)

st.title("Tao Financial Engine — UF-Core Market Recommendations")

st.info(f"UF snapshot loaded for {len(df)} symbols (all treated as snapshot-only, no live calls).")

# Ensure optional columns exist
for col in ["asset_type", "price", "S_UF", "R_UF", "stability_score", "max_dd", "opportunity", "risk"]:
    if col not in df.columns:
        df[col] = 0.0
df["asset_type"] = df["asset_type"].astype(str).str.lower()

# -------------------------------------------------------------------
# Controls
# -------------------------------------------------------------------

asset_label = st.selectbox("Asset type", ["Stocks", "ETFs", "Crypto"], index=0)
asset_key = _asset_label_to_key(asset_label)

col_min, col_max = st.columns(2)
with col_min:
    min_price = st.number_input("Min price", value=100.0, min_value=0.0, step=1.0)
with col_max:
    max_price = st.number_input("Max price", value=200.0, min_value=0.0, step=1.0)

st.markdown("### Admin Snapshot Controls (UF + local cache)")

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("🔁 Re-load UF snapshot from disk"):
        st.experimental_rerun()

with c2:
    if st.button("⚙️ Rebuild FULL UF snapshot (stocks + ETFs, network)"):
        with st.spinner("Rebuilding full UF snapshot from Massive/Alpaca + UF-Core…"):
            refresh_snapshot_full(("stock", "etf"))
        st.success("Full UF snapshot rebuilt. Reloading.")
        st.experimental_rerun()

with c3:
    if st.button("⚙️ Refresh current price band + asset type (network)"):
        with st.spinner("Refreshing current band via UF-Core…"):
            refresh_filtered_snapshot(asset_key, float(min_price), float(max_price))
        st.success("Band refreshed. Reloading.")
        st.experimental_rerun()

# -------------------------------------------------------------------
# Filtering + scoring
# -------------------------------------------------------------------

band = df[
    (df["asset_type"] == asset_key)
    & (df["price"] >= float(min_price))
    & (df["price"] <= float(max_price))
].copy()

if band.empty:
    st.warning("No symbols in this asset type / price band. Try adjusting the filters.")
else:
    band["score"] = band.apply(_score_row, axis=1)
    band = band.sort_values("score", ascending=False).reset_index(drop=True)

# -------------------------------------------------------------------
# Hot picks (< $30)
# -------------------------------------------------------------------

st.markdown("## 🔥 Hot Picks — Top 5 BUY under $30")

hot_band = df[
    (df["asset_type"] == asset_key)
    & (df["price"] < 30.0)
].copy()

if hot_band.empty:
    st.info("No symbols under $30 for this asset type in the snapshot.")
else:
    hot_band["score"] = hot_band.apply(_score_row, axis=1)
    # CORRECT PANDAS ARGUMENT: ascending, not "descending"
    hot_band = hot_band.sort_values("score", ascending=False).head(5)

    if st.button("▶ RUN Hot Picks (Top 5 BUY under $30)"):
        st.dataframe(
            hot_band[
                [
                    "ticker",
                    "asset_type",
                    "price",
                    "regime",
                    "S_UF",
                    "R_UF",
                    "stability_score",
                    "max_dd",
                    "opportunity",
                    "risk",
                    "score",
                ]
            ],
            use_container_width=True,
        )

# -------------------------------------------------------------------
# Top 10 in band
# -------------------------------------------------------------------

st.markdown("## 📊 Top 10 BUY Recommendations in Price Band")

if st.button("▶ RUN Top 10 BUY in Band"):
    if band.empty:
        st.warning("No candidates in this band.")
    else:
        top10 = band.head(10)
        display_cols = [
            "ticker",
            "asset_type",
            "price",
            "regime",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
            "opportunity",
            "risk",
            "score",
        ]
        st.dataframe(top10[display_cols], use_container_width=True)

# -------------------------------------------------------------------
# Optional debug
# -------------------------------------------------------------------

with st.expander("🔬 UF snapshot debug (optional)"):
    st.write("Columns:", list(df.columns))
    st.write("Asset-type counts:", df["asset_type"].value_counts().to_dict())
