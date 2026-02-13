"""
3_Recommendations.py

Streamlit UI for:
- Loading UF snapshot from disk
- Filtering recommendations by price + asset type
- Triggering FULL UF rebuild (stocks + ETFs + index + crypto)
- NO st.experimental_rerun (removed by Streamlit)

This version matches the corrected data and snapshot layers.
"""

from __future__ import annotations

import streamlit as st
from typing import List, Dict, Any

from uf_snapshot_cache import (
    load_snapshot,
    load_filtered_snapshot,
    refresh_snapshot_full,
)

# ------------------------------------------------------------
# Page header
# ------------------------------------------------------------
st.title("Tao Financial Engine — UF-Core Market Recommendations")

snapshot_rows = load_snapshot()
st.subheader(
    f"UF snapshot loaded for {len(snapshot_rows)} symbols "
    f"(snapshot-only, no live calls)."
)

# ------------------------------------------------------------
# User controls
# ------------------------------------------------------------
asset_type = st.selectbox(
    "Asset type",
    ["Stocks", "ETFs", "Index", "Crypto"],
    index=0,
)

min_price = st.number_input("Min price", value=0.0)
max_price = st.number_input("Max price", value=100000.0)

asset_type_map = {
    "Stocks": ("stock",),
    "ETFs": ("etf",),
    "Index": ("index",),
    "Crypto": ("crypto",),
}

selected_types = asset_type_map.get(asset_type, ("stock",))


# ------------------------------------------------------------
# Admin Controls
# ------------------------------------------------------------
st.markdown("### Admin Snapshot Controls (UF + local cache)")

col1, col2 = st.columns(2)

with col1:
    if st.button("Re-load UF snapshot from disk"):
        st.success("Snapshot reloaded. Scroll down to view results.")

with col2:
    if st.button("Rebuild FULL UF snapshot (stocks + ETFs + index + crypto)"):
        st.info("Running rebuild… this may take time.")
        refresh_snapshot_full(("stock", "etf", "index", "crypto"))
        st.success("Full UF snapshot rebuilt.")
        st.write("Please manually refresh the page (F5).")


# ------------------------------------------------------------
# Filtering logic
# ------------------------------------------------------------
filtered_rows = load_filtered_snapshot(
    min_price=min_price,
    max_price=max_price,
    asset_types=selected_types,
)

st.markdown(f"### Filtered results ({len(filtered_rows)} symbols)")

# ------------------------------------------------------------
# Display table
# ------------------------------------------------------------
if filtered_rows:
    show_cols = [
        "ticker",
        "asset_type",
        "price",
        "regime",
        "S_UF",
        "R_UF",
        "stability_score",
        "max_dd",
    ]

    def safe_row(r: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for c in show_cols:
            out[c] = r.get(c)
        return out

    table = [safe_row(r) for r in filtered_rows]
    st.dataframe(table, use_container_width=True)
else:
    st.info("No symbols matched the filter.")
