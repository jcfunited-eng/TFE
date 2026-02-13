import streamlit as st
import pandas as pd

from uf_snapshot_cache import load_snapshot_with_prices
from uf_snapshot_cache import refresh_snapshot_for_symbols  # stub, local only
from uf_decision_surface import rank_top_buys

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="TFE – UF Recommendations", page_icon="📈")
st.title("📈 Tao Financial Engine — UF-Core Market Recommendations")

# ---------------------------------------------------------------------------
# Load UF snapshot (rows + prices)
# ---------------------------------------------------------------------------

rows = load_snapshot_with_prices()

if not rows:
    st.warning(
        "No UF snapshot found. Ensure `uf_snapshot.json` exists and that "
        "`data/cache/price_snapshot.json` has been created with prices. "
        "You can run your UF-core + price refresh script, then reload."
    )
    st.stop()

total_symbols = len(rows)
st.info(f"UF snapshot loaded for **{total_symbols}** symbols (all treated as stocks).")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

asset_type = st.selectbox("Asset type", ["Stocks"], index=0)

col_min, col_max = st.columns(2)
with col_min:
    min_price = st.number_input("Min price", min_value=0.01, value=0.01, step=0.5)
with col_max:
    max_price = st.number_input("Max price", min_value=0.01, value=50.0, step=1.0)

# Admin controls (still local; no network)
st.subheader("Admin Snapshot Controls (UF + local cache)")
if st.button("🔁 Re-load UF snapshot from disk"):
    # No network, just re-read files
    rows = load_snapshot_with_prices()
    st.success(f"Reloaded UF snapshot for {len(rows)} symbols.")
    st.stop()

# ---------------------------------------------------------------------------
# Hot Picks – Top 5 BUY under $30
# ---------------------------------------------------------------------------

st.subheader("🔥 Hot Picks — Top 5 BUY under $30")

if st.button("▶ RUN Hot Picks (Top 5 BUY under $30)"):
    hot = rank_top_buys(
        rows,
        min_price=0.01,
        max_price=30.0,
        asset_type=asset_type,
        top_n=5,
    )

    if not hot:
        st.warning("No BUY candidates under $30 for this asset type.")
    else:
        df_hot = pd.DataFrame(hot)
        # nice column order
        display_cols = [
            "ticker",
            "price",
            "UF_action",
            "score",
            "opportunity",
            "risk",
            "confidence",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
        ]
        display_cols = [c for c in display_cols if c in df_hot.columns]
        st.dataframe(df_hot[display_cols], use_container_width=True)

# ---------------------------------------------------------------------------
# Top 10 BUY in band
# ---------------------------------------------------------------------------

st.subheader("📊 Top 10 BUY Recommendations in Price Band")

if st.button("▶ RUN Top 10 BUY in Band"):
    top = rank_top_buys(
        rows,
        min_price=min_price,
        max_price=max_price,
        asset_type=asset_type,
        top_n=10,
    )

    if not top:
        st.warning("No BUY candidates in this price band for this asset type.")
    else:
        df_top = pd.DataTable(top) if False else pd.DataFrame(top)  # keep simple
        display_cols = [
            "ticker",
            "price",
            "UF_action",
            "score",
            "opportunity",
            "risk",
            "confidence",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
        ]
        display_cols = [c for c in df_top.columns if c in display_cols]
        st.dataframe(df_top[display_cols], use_container_width=True)
